#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_collection_log.py — 从 holiday-data-fetch.json 自动生成标准格式采集日志 (v1.2)

用法:
    python gen_collection_log.py --workspace <主JSON> [--out <目录>]

输出:
    <workspace目录>/采集日志.csv
    列: 检索关键词 | 检索时间 | 标题 | 来源机构 | 报告/资料名 | 发布时间 | URL | 内容摘要 | 快照路径 | 层(layer) | 状态 | 观测批次 | 同源复用

v1.2 新增:
  - 观测批次列: 本轮 R1/R2…, 历史导入 H1/H2… (R5/导入批次可追溯)
  - 同源复用列: 快照文件被 ≥2 条引用时标 "是-共{n}条" (R5 修复)
  - 历史导入行状态标 "历史导入"
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

LOG_FIELDS = ["检索关键词", "检索时间", "标题", "来源机构", "报告/资料名", "发布时间", "URL", "内容摘要", "快照路径", "层(layer)", "状态", "观测批次", "同源复用"]


def to_row(it, snap_counter):
    layer = it.get("layer", "")
    if layer == "L1":
        url = it.get("URL", "")
        title = str(it.get("数据点", "")) + (f" = {it.get('数值', '')}{it.get('单位', '')}" if it.get("数值") else "")
        src_org = it.get("来源机构", "")
        report = it.get("报告/资料名", "")
        pub = it.get("发布时间", "")
        digest = it.get("内容摘录", "")
    else:
        url = it.get("来源URL", "")
        title = str(it.get("现象描述", ""))
        src_org = it.get("来源机构", "")
        report = ""
        pub = ""
        digest = it.get("内容摘录", "")
    snap = it.get("snapshot", "")
    if str(it.get("数据来源", "")) == "历史导入":
        status = "历史导入"
    elif str(snap).startswith("未存"):
        status = f"入库{layer}-快照未存"
    else:
        status = "入库" + layer
    # 同源复用
    if snap and not str(snap).startswith("未存"):
        reuse = f"是-共{snap_counter.get(snap, 1)}条" if snap_counter.get(snap, 1) > 1 else "否"
    else:
        reuse = "否"
    return {
        "检索关键词": it.get("keywords", ""),
        "检索时间": it.get("round", ""),
        "标题": title,
        "来源机构": src_org,
        "报告/资料名": report,
        "发布时间": pub,
        "URL": url,
        "内容摘要": digest,
        "快照路径": snap,
        "层(layer)": layer,
        "状态": status,
        "观测批次": it.get("观测批次", ""),
        "同源复用": reuse,
    }


def main():
    ap = argparse.ArgumentParser(description="自动生成标准采集日志 CSV (v1.2)")
    ap.add_argument("--workspace", required=True, help="主 JSON 路径")
    ap.add_argument("--out", default=None, help="输出目录 (默认 workspace 同目录)")
    args = ap.parse_args()

    ws_path = Path(args.workspace)
    if not ws_path.exists():
        print(f"[错误] 主 JSON 不存在: {ws_path}")
        return 1
    with ws_path.open("r", encoding="utf-8-sig") as f:
        ws = json.load(f)
    if not isinstance(ws, dict) or "items" not in ws:
        print(f"[错误] 主 JSON 结构不完整 (缺 items)")
        return 1
    items = ws["items"]
    if not items:
        print("[错误] 无条目, 无法生成采集日志")
        return 1

    # 快照引用计数（同源复用）
    snap_counter = Counter()
    for it in items:
        snap = it.get("snapshot", "")
        if snap and not str(snap).startswith("未存"):
            snap_counter[snap] += 1

    out_dir = Path(args.out) if args.out else ws_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "采集日志.csv"

    rows = [to_row(it, snap_counter) for it in items]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    l1 = sum(1 for it in items if it.get("layer") == "L1")
    l2 = sum(1 for it in items if it.get("layer") == "L2")
    hist = sum(1 for it in items if it.get("数据来源") == "历史导入")
    reused = sum(1 for c in snap_counter.values() if c > 1)
    print(f"[生成] 采集日志: {out_path}")
    print(f"  共 {len(rows)} 行 (L1={l1}, L2={l2}, 历史导入={hist})")
    print(f"  同源复用快照文件: {reused} 个 (被 ≥2 条引用)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

