#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_holiday_terms.py — 节日术语自检 + 自动补丁（Term Guard）

为什么需要这个脚本
-------------------
2026-09-11 实测：AtomGit 上的 holiday-data-fetch 安装包存在「半改名」问题——
SKILL.md 已改为「暑期」，但 references/ 与 scripts/ 仍是「暑假」。
后果极其隐蔽：

    HOLIDAYS 含「暑假」 → 构造目录 2026_暑假
    上游只有 2026_暑期   → 命中 0
    git sparse-checkout → 退出码 0、零警告（静默失败）

即：看起来采到了基线，实际一条数据都没有，报告照着空气写。
这是「零虚构」纪律下最危险的一类故障——它不说自己失败了。

因此 D2（从 AtomGit 安装 fetch）之后必须跑一次本脚本。

用法
----
    python scripts/verify_holiday_terms.py <skill_dir>              # 只检查
    python scripts/verify_holiday_terms.py <skill_dir> --fix        # 检查并自动补丁
    python scripts/verify_holiday_terms.py <skill_dir> --json       # 机器可读输出
    python scripts/verify_holiday_terms.py <skill_dir> --fix --json # 补丁 + 机器可读

退出码
------
    0 = 通过（无问题，或 --fix 后全部修复成功）
    1 = 存在问题（未加 --fix，或 --fix 后仍有残留）
    2 = 用法错误 / 目标路径不是合法 SKILL 包

检查分两层
----------
    L1 文本术语扫描：.md/.py/.html/.json/.yaml/.yml/.txt/.csv 中的旧称
    L2 枚举构造检查：scripts 中 HOLIDAYS / HOLIDAY_SEQ 的中文键是否与规范名一致
                    （L2 才是致命层——它直接决定构造出的 AtomGit 目录名）

设计边界
--------
    * 只自动修复「有明确依据」的替换（暑假→暑期）。
    * 别名（国庆/元旦 等）仅提示，不自动改——依据不足时宁可不动。
    * 「暑运」（交通部制度名，62 天）是保护词，绝不替换；修复后须数量不变。
    * 未改动的文件不重写（避免无意义 diff）。
"""

import argparse
import io
import json
import os
import re
import sys

# ---------------------------------------------------------------- 规则表

# 规范名（与 AtomGit 上游目录名 [年份]_[节日] 一致，2026-09-11 起）
CANON_HOLIDAYS = ["春节", "端午", "五一", "暑期", "中秋", "十一"]

# 自动补丁规则：(旧词, 新词, 依据)
AUTO_FIX_RULES = [
    ("暑假", "暑期", "AtomGit 上游 2026-09-11 起目录为 [年份]_暑期；"
                     "holiday-config.md 属性卡「暑期（制度名，官方全用）/ 暑假（口语学制名）」"),
]

# 保护词：出现即视为合法，禁止被任何规则改写
PROTECTED = ["暑运"]

# 仅提示、不自动改（依据不足）
WARN_ONLY_ALIAS = {
    "国庆": "十一",
    "元旦": "春节",
}

SCAN_EXT = (".md", ".py", ".html", ".json", ".yaml", ".yml", ".txt", ".csv")
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

# 跳过自身：本文件的 docstring / 规则表内含「暑假」反例，属规则定义而非违规用法
SKIP_FILES = {"verify_holiday_terms.py"}

# 历史记述文档：logs/CHANGELOG.md 记录版本沿革，必然引用旧称（如「v1.5.0 将暑假更名为暑期」），
# 逐行加豁免标记既啰嗦又损害可读性，故按文件豁免——但输出中显式列出豁免内容，不静默放过。
HISTORY_DOCS = {"CHANGELOG.md", "README.md"}

# 行级豁免标记：有意保留的旧称（反例说明、用词规范中的旧称条目）须显式标注，
# 禁止静默放过——写 `<!-- term-allow -->` 表示"此处为已登记豁免"。
ALLOW_MARK = "term-allow"


# ---------------------------------------------------------------- 工具

def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.lower().endswith(SCAN_EXT):
                yield os.path.join(dirpath, fn)


def read_text(path):
    """读文本；非 UTF-8 一律跳过并返回 None（不猜编码，避免改坏二进制）。"""
    try:
        return io.open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        return None


def count_term(text, term):
    return text.count(term)


# ---------------------------------------------------------------- L1 文本扫描

def scan_text(root):
    """返回 (findings, fixable_files, waived)
    findings: [{file, line, old, new, text}]
    fixable_files: {path: (orig_text, n_fixes)}
    waived: [{file, count}]  历史记述文档中被引用的旧称（显式列出，不静默放过）
    """
    findings = []
    fixable = {}
    waived = []
    for path in iter_files(root):
        base = os.path.basename(path)
        if base in SKIP_FILES:
            continue
        text = read_text(path)
        if text is None:
            continue
        rel = os.path.relpath(path, root)
        if base in HISTORY_DOCS:
            n = sum(text.count(old) for old, _new, _why in AUTO_FIX_RULES)
            if n:
                waived.append({"file": rel, "count": n})
            continue
        hits = 0
        for old, new, _why in AUTO_FIX_RULES:
            if old not in text:
                continue
            for i, line in enumerate(text.split("\n")):
                if old not in line:
                    continue
                if ALLOW_MARK in line:
                    continue  # 已登记豁免（反例说明 / 用词规范旧称条目）
                findings.append({
                    "file": rel, "line": i + 1, "old": old, "new": new,
                    "text": line.strip()[:160],
                })
                hits += line.count(old)
        if hits:
            fixable[path] = (text, hits)
    return findings, fixable, waived


def apply_text_fixes(fixable):
    """执行替换，返回 (patched_files, failures)"""
    patched, failures = [], []
    for path, (text, _n) in fixable.items():
        # 保护词计数（修复前后须一致）
        before = {p: text.count(p) for p in PROTECTED}
        new = text
        for old, nw, _why in AUTO_FIX_RULES:
            new = new.replace(old, nw)
        # 保护词校验
        for p, c in before.items():
            if new.count(p) != c:
                failures.append((path, "保护词「%s」数量被改变：%d -> %d" % (p, c, new.count(p))))
                continue
        # 防呆：不应出现叠词
        if "暑暑期" in new:
            failures.append((path, "替换后出现异常叠词「暑暑期」"))
            continue
        try:
            io.open(path, "w", encoding="utf-8", newline="").write(new)
            patched.append(path)
        except OSError as e:
            failures.append((path, "写入失败: %s" % e))
    return patched, failures


# ---------------------------------------------------------------- L2 枚举构造检查

RE_HOLIDAYS = re.compile(r"HOLIDAYS\s*=\s*\[([^\]]*)\]")
RE_SEQ = re.compile(r"HOLIDAY_SEQ\s*=\s*\{([^}]*)\}")


def scan_enums(root):
    """检查 scripts/ 中 HOLIDAYS / HOLIDAY_SEQ 的中文键。
    返回 (issues, enums)
    issues: [{file, line, kind, found, expected}]
    """
    issues, enums = [], {}
    sdir = os.path.join(root, "scripts")
    if not os.path.isdir(sdir):
        return issues, enums

    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(sdir, fn)
        text = read_text(path)
        if text is None:
            continue
        for i, line in enumerate(text.split("\n")):
            m = RE_HOLIDAYS.search(line)
            if m:
                vals = re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1))
                vals = [a or b for a, b in vals]
                enums.setdefault(fn, {})["HOLIDAYS"] = vals
                bad = [v for v in vals if v not in CANON_HOLIDAYS]
                if bad:
                    issues.append({
                        "file": "scripts/" + fn, "line": i + 1, "kind": "HOLIDAYS",
                        "found": bad,
                        "expected": [AUTO_FIX_RULES[0][1] if v == AUTO_FIX_RULES[0][0] else v
                                     for v in bad],
                    })
            m = RE_SEQ.search(line)
            if m:
                keys = re.findall(r'"([^"]+)"\s*:|\'([^\']+)\'\s*:', m.group(1))
                keys = [a or b for a, b in keys]
                enums.setdefault(fn, {})["HOLIDAY_SEQ"] = keys
                bad = [k for k in keys if k not in CANON_HOLIDAYS]
                if bad:
                    issues.append({
                        "file": "scripts/" + fn, "line": i + 1, "kind": "HOLIDAY_SEQ",
                        "found": bad,
                        "expected": [AUTO_FIX_RULES[0][1] if k == AUTO_FIX_RULES[0][0] else k
                                     for k in bad],
                    })
    return issues, enums


# ---------------------------------------------------------------- 别名提示

def scan_alias(root):
    warns = []
    for path in iter_files(root):
        text = read_text(path)
        if text is None:
            continue
        rel = os.path.relpath(path, root)
        for alias, canon in WARN_ONLY_ALIAS.items():
            if alias in text:
                warns.append({"file": rel, "alias": alias, "canon": canon,
                              "count": text.count(alias)})
    return warns


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(
        description="节日术语自检 + 自动补丁（D2 安装 fetch 后必跑）")
    ap.add_argument("skill_dir", help="待检查的 SKILL 包目录")
    ap.add_argument("--fix", action="store_true", help="自动修复有依据的旧称")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    root = args.skill_dir
    if not os.path.isdir(root):
        sys.stderr.write("[ERROR] 目录不存在: %s\n" % root)
        return 2
    if not os.path.isfile(os.path.join(root, "SKILL.md")):
        sys.stderr.write("[ERROR] 不是合法 SKILL 包（缺少 SKILL.md）: %s\n" % root)
        return 2

    findings, fixable, waived = scan_text(root)
    enum_issues, enums = scan_enums(root)
    alias_warns = scan_alias(root)

    patched, failures = [], []
    if args.fix and fixable:
        patched, failures = apply_text_fixes(fixable)
        # 修复后重扫，确认归零
        findings2, _, waived = scan_text(root)
        enum_issues, enums = scan_enums(root)
    else:
        findings2 = findings

    ok = (not findings2) and (not enum_issues) and (not failures)

    if args.json:
        print(json.dumps({
            "skill_dir": root,
            "before": {"text_hits": sum(1 for _ in findings), "enum_issues": enum_issues},
            "after": {"text_hits": len(findings2), "enum_issues": enum_issues},
            "patched_files": [os.path.relpath(p, root) for p in patched],
            "failures": [{"file": f, "reason": r} for f, r in failures],
            "alias_warnings": alias_warns,
            "waived_history_docs": waived,
            "enums": enums,
            "ok": ok,
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    # 人类可读输出
    print("=" * 68)
    print("节日术语自检  ·  %s" % root)
    print("=" * 68)

    if findings:
        nfiles_before = len({f["file"] for f in findings})
        nhits_before = sum(v[1] for v in fixable.values())
        if args.fix:
            print("\n[L1] 文本旧称：修复前 %d 行 / %d 处（%d 个文件）→ 修复后 %d 处"
                  % (len(findings), nhits_before, nfiles_before, len(findings2)))
        else:
            print("\n[L1] 文本旧称 %d 行 / %d 处（%d 个文件）："
                  % (len(findings), nhits_before, nfiles_before))
        byf = {}
        for f in findings:
            byf.setdefault(f["file"], []).append(f)
        for fn in sorted(byf):
            print("  %s  (%d 处)" % (fn, len(byf[fn])))
            for f in byf[fn][:6]:
                print("      L%-4d %s → %s   %s" % (f["line"], f["old"], f["new"], f["text"][:70]))
            if len(byf[fn]) > 6:
                print("      … 另 %d 处" % (len(byf[fn]) - 6))
    else:
        print("\n[L1] 文本旧称：无")

    if waived:
        print("\n[L1-豁免] 历史记述文档 %d 个（记录版本沿革必然引用旧称，显式登记不静默放过）："
              % len(waived))
        for w in waived:
            print("  %s  (%d 处)" % (w["file"], w["count"]))

    if enum_issues:
        print("\n[L2] 枚举构造（致命层 · 直接决定 AtomGit 目录名）：")
        for e in enum_issues:
            print("  ✗ %s:%d  %s  含非规范值 %s" % (e["file"], e["line"], e["kind"], e["found"]))
            print("      构造结果示例：2026_%s  → 上游无此目录 → 命中 0 且不报错"
                  % e["found"][0])
    else:
        print("\n[L2] 枚举构造：全部为规范名 %s" % "/".join(CANON_HOLIDAYS))

    if alias_warns:
        print("\n[别名提示] 仅提示，未自动修改（依据不足）：")
        for w in alias_warns[:8]:
            print("  · %s  含「%s」%d 处（候选规范名「%s」，需人工确认）"
                  % (w["file"], w["alias"], w["count"], w["canon"]))

    if args.fix:
        print("\n[补丁] 已修复 %d 个文件" % len(patched))
        for p in patched:
            print("  ✓ %s" % os.path.relpath(p, root))
        if failures:
            print("\n[补丁失败]")
            for f, r in failures:
                print("  ✗ %s : %s" % (os.path.relpath(f, root), r))

    print("\n" + "-" * 68)
    if ok:
        print("PASS  · 术语一致，可安全用于 AtomGit 目录构造")
        return 0
    else:
        print("FAIL  · 存在不一致%s" % ("（加 --fix 可自动修复文本层）"
                                        if not args.fix else "（仍有残留，需人工处理）"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
