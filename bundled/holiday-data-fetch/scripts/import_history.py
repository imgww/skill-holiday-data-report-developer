#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_history.py — 历史数据导入器（v1.2 新增，v1.3 收敛为纯 JSON 输入）

将历史版数据导入主工作区 JSON，作为"存量基线"（观测批次=H{n}）叠加，防"越采越少"。

支持输入（v1.3 起只认 JSON，不再消费任何 CSV）：
  - 现行 / v1.1 / v1.0 `holiday-data-fetch.json`（schema=holiday-data-fetch-v1）
  - L2 现象素材库 JSON（schema=phenomena-library-v1，仅旧版遗留文件的输入兜底）
  - 目录（自动扫描上述 JSON，跳过 round_*.json 中间产物）

> v1.3 说明：SSOT `holiday-data-fetch.json` 是唯一数据出口，本技能不再产出
> 也不再消费 `消费数据集.csv` 一类 22 字段 CSV 派生视图。历史基线一律来自
> 历史目录下的 `holiday-data-fetch.json`（见 holiday-data-report 阶段一 D1 稀疏检出）。

用法：
    python import_history.py --workspace <主JSON> --source <历史文件或目录> [--batch H1] [--dry-run] [--keep-snapshots]

流程：
    1. 格式识别（v1.0/v1.1 JSON / 现象素材库 JSON）
    2. 质量过滤（剔除 待核 / 数值类型污染 / 无URL / 非目标年度节假日）
    3. 格式归一化 + 字段补齐（数值类型/单位粒度/数据性质/地域粒度 归一，缺字段补默认）
    4. 批次标注（数据来源=历史导入, 观测批次=H{n}, round=历史导入, 采集时间=导入时刻）
    5. 分层同一性判定（L1–L5，见 _merge_core.py）合并进主 JSON
    6. 输出导入报告（读取/过滤/归一化/去重/新增/关联 条数）
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---- 常量 ----
HOLIDAY_SEQ = {"春节": "CH", "端午": "DW", "五一": "WY", "暑期": "SH", "中秋": "MQ", "十一": "SY"}
PROVINCE_NAMES = ["广东", "浙江", "江苏", "四川", "山东", "河南", "湖北", "湖南", "福建", "安徽",
                  "河北", "陕西", "云南", "贵州", "辽宁", "吉林", "黑龙江", "山西", "江西", "广西",
                  "海南", "重庆", "北京", "上海", "天津", "内蒙古", "新疆", "西藏", "宁夏", "甘肃", "青海"]
CITY_NAMES = ["北京", "上海", "广州", "成都", "重庆", "杭州", "西安", "武汉", "南京", "深圳",
              "长沙", "郑州", "青岛", "天津", "苏州", "三亚", "厦门", "昆明", "哈尔滨", "长春"]

# 历史版主题别名 → 统一主题白名单（R2：消除双写）
THEME_NORM = {
    "酒店": "酒店住宿", "平台": "平台渠道", "交通": "交通出行",
    "景区数据": "景区目的地", "目的地": "景区目的地", "景区": "景区目的地",
    "政策宏观": "消费宏观", "政策与宏观": "消费宏观", "跨境": "消费宏观",
    "旅游行业平台": "平台渠道", "热门新消费": "新消费",
    "跨年可比": "总体", "预测台账": "总体", "前瞻预测": "总体",
}


def detect_format(path):
    """返回 ('json_fetch' | 'json_l2' | None)。v1.3 起不再识别 CSV。"""
    if path.suffix.lower() == ".json":
        try:
            with path.open("r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception:
            return None
        if isinstance(data, dict):
            if data.get("schema") == "holiday-data-fetch-v1":
                return "json_fetch"
            if data.get("schema") == "phenomena-library-v1" or "现象标签" in str(data.get("items", [])[:2000]):
                return "json_l2"
    return None


def _norm_text(v):
    if v is None:
        return ""
    return str(v).strip()


def _infer_region(data_point, org):
    text = f"{data_point} {org}"
    for prov in PROVINCE_NAMES:
        if prov in text:
            return f"省级({prov})"
    for city in CITY_NAMES:
        if city in text:
            return f"城市级({city})"
    if "景区" in text or "景点" in text or "商圈" in text:
        return "景区商圈级"
    return "全国"


def quality_problem(row, target_year, target_holiday):
    """返回过滤原因；无则返回 None。row 为 dict（统一字段）"""
    # 非目标年度/节假日
    y = _norm_text(row.get("年份") or row.get("year"))
    h = _norm_text(row.get("节日") or row.get("holiday"))
    if y and str(y) != str(target_year):
        return f"年度不符({y})"
    if h and h != target_holiday:
        return f"节假日不符({h})"
    # 待核
    if "待核" in _norm_text(row.get("口径类型")):
        return "待核"
    # 无 URL
    url = _norm_text(row.get("URL") or row.get("来源URL"))
    if not url or url.startswith("无") or url == "无公开来源":
        return "无URL"
    # 数值类型污染
    vt = _norm_text(row.get("数值类型"))
    if vt in ("5", "40天(春运)", "春节销售季"):
        return f"数值类型污染({vt})"
    return None


def json_fetch_to_items(path, target_year, target_holiday, keep_snapshots):
    """v1.0/v1.1 JSON → 条目列表（L1+L2），仅取目标年度节假日"""
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    meta = data.get("meta", {})
    src_year = meta.get("year")
    src_holiday = meta.get("holiday")
    items = []
    read = 0
    filtered = []
    if src_year is not None and str(src_year) != str(target_year):
        return items, read, [(path.name, f"年度不符({src_year})")]
    if src_holiday and src_holiday != target_holiday:
        return items, read, [(path.name, f"节假日不符({src_holiday})")]
    for it in data.get("items", []):
        read += 1
        problem = quality_problem(it, target_year, target_holiday)
        if problem:
            filtered.append((it.get("数据点") or it.get("现象描述", ""), problem))
            continue
        new_it = dict(it)
        new_it.pop("id", None)  # 重新分配 id，避免跨文件冲突
        new_it["观测批次"] = ""  # 由导入器统一标注
        new_it["round"] = "历史导入"
        new_it["数据来源"] = "历史导入"
        new_it["采集时间"] = ""
        if not keep_snapshots:
            new_it["snapshot"] = "未存-历史导入"
        if new_it.get("layer") == "L1":
            new_it["主题"] = THEME_NORM.get(new_it.get("主题", ""), new_it.get("主题", ""))
            new_it["地域粒度"] = new_it.get("地域粒度") or _infer_region(new_it.get("数据点", ""), new_it.get("来源机构", ""))
            if new_it.get("数据性质") == "预计" and str(new_it.get("缺口标记", "")) in ("", "空"):
                new_it["缺口标记"] = "预判待回填"
            if (new_it.get("数据性质") == "推算" or new_it.get("口径类型") in ("测算", "弱溯源") or new_it.get("数值类型") == "定性"):
                new_it["可信度等级"] = "D"
        if not new_it.get("备注"):
            new_it["备注"] = "历史导入"
        items.append(new_it)
    return items, read, filtered


def json_l2_to_items(path, target_year, target_holiday):
    """现象素材库 JSON → L2 条目列表"""
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    y = data.get("year")
    h = data.get("holiday")
    items = []
    filtered = []
    if y is not None and str(y) != str(target_year):
        return items, 0, [(path.name, f"年度不符({y})")]
    if h and h != target_holiday:
        return items, 0, [(path.name, f"节假日不符({h})")]
    read = 0
    for it in data.get("items", []):
        read += 1
        if not (it.get("来源URL") or it.get("URL")):
            filtered.append((it.get("现象描述", ""), "无URL"))
            continue
        new_it = dict(it)
        new_it["layer"] = "L2"
        new_it.pop("id", None)
        new_it["观测批次"] = ""
        new_it["round"] = "历史导入"
        new_it["数据来源"] = "历史导入"
        new_it["采集时间"] = ""
        new_it["snapshot"] = "未存-历史导入"
        items.append(new_it)
    return items, read, filtered


def collect_sources(source):
    """返回待导入文件列表（目录自动扫描 JSON；v1.3 起不再扫 CSV）"""
    src = Path(source)
    if src.is_file():
        return [src]
    if src.is_dir():
        files = []
        for f in sorted(src.rglob("*")):
            if f.suffix.lower() in (".json",):
                name = f.name
                if name.startswith("round_") or name.startswith("采集日志"):
                    continue  # 跳过中间产物
                files.append(f)
        return files
    return []


def copy_snapshot_files(source_path, ws_root):
    """若源 JSON 旁有 snapshots/，复制到工作区（保留可追溯快照）"""
    src_snap = source_path.parent / "snapshots"
    if not src_snap.is_dir():
        return 0
    dst_snap = ws_root / "snapshots"
    dst_snap.mkdir(parents=True, exist_ok=True)
    copied = 0
    for sf in src_snap.glob("*"):
        if sf.is_file() and not (dst_snap / sf.name).exists():
            try:
                sf.replace(dst_snap / sf.name)
                copied += 1
            except Exception:
                pass
    return copied


def main():
    ap = argparse.ArgumentParser(description="历史数据导入器（v1.2）")
    ap.add_argument("--workspace", required=True, help="主 JSON 路径")
    ap.add_argument("--source", required=True, help="历史数据文件或目录")
    ap.add_argument("--batch", default=None, help="观测批次码，如 H1；缺省自动取下一个 H 批次")
    ap.add_argument("--dry-run", action="store_true", help="只输出导入报告，不写回")
    ap.add_argument("--keep-snapshots", action="store_true", help="导入 v1.0/v1.1 JSON 时保留原快照路径并复制快照文件")
    args = ap.parse_args()

    from _merge_core import layered_merge, now_str, batch_of

    ws_path = Path(args.workspace)
    if not ws_path.exists():
        print(f"[错误] 主 JSON 不存在: {ws_path} (先运行 init_workspace.py)")
        return 1
    with ws_path.open("r", encoding="utf-8-sig") as f:
        ws = json.load(f)
    meta = ws["meta"]
    year = meta.get("year")
    holiday = meta.get("holiday", "")

    # 批次码
    used = [batch_of(i) for i in ws.get("items", [])]
    h_nums = [int(b[1:]) for b in used if str(b).startswith("H") and b[1:].isdigit()]
    batch = args.batch or f"H{max(h_nums, default=0) + 1}"
    if not str(batch).startswith("H"):
        print(f"[错误] 历史导入批次码必须以 H 开头: {batch}")
        return 1

    sources = collect_sources(args.source)
    if not sources:
        print(f"[错误] 未找到可导入的历史数据: {args.source}")
        return 1

    when = now_str()
    total_read = total_filtered = total_added = total_dedup = total_conflict = total_linked = 0
    filter_breakdown = {}
    imported_files = []
    ws_items = ws["items"]
    existing = list(ws_items)

    for src in sources:
        fmt = detect_format(src)
        if fmt is None:
            continue
        if fmt == "json_fetch":
            items, read, filtered = json_fetch_to_items(src, year, holiday, args.keep_snapshots)
            if args.keep_snapshots:
                copied = copy_snapshot_files(src, ws_path.parent)
                if copied:
                    print(f"  [快照] 复制 {copied} 个快照文件 <- {src.parent / 'snapshots'}")
        else:  # json_l2
            items, read, filtered = json_l2_to_items(src, year, holiday)
        total_read += read
        total_filtered += len(filtered)
        for _, reason in filtered:
            filter_breakdown[reason] = filter_breakdown.get(reason, 0) + 1
        if not items:
            continue

        # 批次标注
        for it in items:
            it["观测批次"] = batch
            it["round"] = "历史导入"
            it["数据来源"] = "历史导入"
            it["采集时间"] = it.get("采集时间") or when
            it["snapshot"] = it.get("snapshot") or "未存-历史导入"
            it["keywords"] = it.get("keywords", "") or "历史导入"

        # 分层合并（dry-run 用副本）
        target = ws if not args.dry_run else {"meta": dict(meta), "items": list(existing)}
        added, dedup, conflict, linked = layered_merge(
            target, items, batch_label=batch, batch_kind="history", when=when,
            all_ids=list(meta.get("_all_ids", [])) if not args.dry_run else None,
        )
        total_added += added
        total_dedup += dedup
        total_conflict += conflict
        total_linked += linked
        imported_files.append(src.name)

    # 写回（非 dry-run）
    if not args.dry_run:
        meta["merge_notes"].append(f"{batch}: 历史导入 {total_added} 条, 过滤 {total_filtered} 条, 去重 {total_dedup} 条, 冲突更新 {total_conflict} 条, 关联 {total_linked} 对")
        meta["history_imports"] = meta.get("history_imports", [])
        meta["history_imports"].append({
            "batch": batch, "source": str(args.source), "files": imported_files,
            "read": total_read, "filtered": total_filtered, "imported": total_added,
            "at": when,
        })
        meta["counts"]["L1"] = sum(1 for i in ws["items"] if i.get("layer") == "L1")
        meta["counts"]["L2"] = sum(1 for i in ws["items"] if i.get("layer") == "L2")
        meta["counts"]["history_imported"] = sum(1 for i in ws["items"] if i.get("数据来源") == "历史导入")
        tmp = ws_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(ws, f, ensure_ascii=False, indent=2)
        tmp.replace(ws_path)

    # 导入报告
    print(f"=== 历史导入报告 (batch={batch}) ===")
    print(f"  来源: {args.source}")
    for n in imported_files:
        print(f"    - {n}")
    print(f"  读取: {total_read} 条")
    if total_filtered:
        detail = ", ".join(f"{k}:{v}" for k, v in sorted(filter_breakdown.items(), key=lambda x: -x[1]))
        print(f"  过滤: {total_filtered} 条 ({detail})")
    else:
        print("  过滤: 0 条")
    print(f"  合并: 新增 {total_added} / 去重 {total_dedup} / 冲突更新 {total_conflict} / 观测关联 {total_linked} 对")
    print(f"  模式: {'DRY-RUN（未写回）' if args.dry_run else '已写回'}")
    print(f"  当前计数: L1={meta['counts'].get('L1', 0)} L2={meta['counts'].get('L2', 0)} history={meta['counts'].get('history_imported', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

