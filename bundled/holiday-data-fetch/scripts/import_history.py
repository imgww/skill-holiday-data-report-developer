#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_history.py — 历史数据导入器（v1.2 新增）

将历史版数据导入主工作区 JSON，作为"存量基线"（观测批次=H{n}）叠加，防"越采越少"。

支持输入：
  - 历史版 CSV（22 字段：`*消费数据集*.csv` / `节假日消费数据集_总览.csv`）
  - v1.0 / v1.1 JSON（`holiday-data-fetch.json`，schema=holiday-data-fetch-v1）
  - L2 现象素材库 JSON（schema=phenomena-library-v1）
  - 目录（自动扫描上述文件，跳过 round_*.json 中间产物）

用法：
    python import_history.py --workspace <主JSON> --source <历史文件或目录> [--batch H1] [--dry-run] [--keep-snapshots]

流程：
    1. 格式识别（CSV / v1.0/v1.1 JSON / 现象素材库 JSON）
    2. 质量过滤（剔除 待核 / 数值类型污染 / 无URL / 非目标年度节假日）
    3. 格式归一化 + 字段补齐（数值类型/单位粒度/数据性质/地域粒度 归一，缺字段补默认）
    4. 批次标注（数据来源=历史导入, 观测批次=H{n}, round=历史导入, 采集时间=导入时刻）
    5. 分层同一性判定（L1–L5，见 _merge_core.py）合并进主 JSON
    6. 输出导入报告（读取/过滤/归一化/去重/新增/关联 条数）
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime
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

# 合法数值类型（v1.1 收敛为 4 类 + 复合）
VALID_VALUE_TYPE = {"水平值", "增长率", "指数", "定性", "复合"}
VALUE_TYPE_NORM = {"复合值": "复合", "增速": "增长率", "倍数": "增长率", "占比": "水平值", "区间": "定性"}
# 明确的单位粒度污染值（应归一到 单位 或置 "—"）
GRANULARITY_POLLUTION = {"水平值", "增长率", "定性", "复合", "总量", "全国总量", "总计", "清单", "日均",
                         "日度", "比率", "%增长", "倍数", "%占比", "占比", "日均量", "指数", "水平(计数)",
                         "水平(区间)", "指数(2019=100)", "元(单价)", "元(单房收益)"}
GRANULARITY_FROM_UNIT = {"亿人次": "人次", "万人次": "人次", "人次": "人次", "亿元": "亿元", "万亿元": "亿元",
                         "万元": "亿元", "%": "百分比", "百分比": "百分比", "元": "元", "元/间夜": "元/间夜",
                         "间夜": "间夜", "元/人次": "人均trip", "元/人天": "人均day", "辆次": "辆次",
                         "万场": "场次", "亿公里": "公里", "万列": "列", "亿笔": "笔"}

# 历史版主题别名 → 统一主题白名单（R2：消除双写）
THEME_NORM = {
    "酒店": "酒店住宿", "平台": "平台渠道", "交通": "交通出行",
    "景区数据": "景区目的地", "目的地": "景区目的地", "景区": "景区目的地",
    "政策宏观": "消费宏观", "政策与宏观": "消费宏观", "跨境": "消费宏观",
    "旅游行业平台": "平台渠道", "热门新消费": "新消费",
    "跨年可比": "总体", "预测台账": "总体", "前瞻预测": "总体",
}


def detect_format(path):
    """返回 ('csv_l1' | 'json_fetch' | 'json_l2' | None)"""
    if path.suffix.lower() == ".csv":
        return "csv_l1"
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


def _norm_caliber(cal):
    """口径类型去重净化 + 历史版本别名归一：
    '官方营业性(不含自驾),官方营业性(不含自驾)' → 取首段
    实测→官方总量, 平台披露→平台自披露（2023 系历史错版 schema）"""
    cal = _norm_text(cal)
    if "," in cal:
        parts = [p.strip() for p in cal.split(",")]
        seen = []
        for p in parts:
            if p and p not in seen:
                seen.append(p)
        cal = seen[0] if seen else cal
    return CALIBER_ALIAS.get(cal, cal)


CALIBER_ALIAS = {"实测": "官方总量", "平台披露": "平台自披露", "官方边检": "官方总量"}


def _norm_value_type(vt):
    vt = _norm_text(vt)
    if vt in VALUE_TYPE_NORM:
        return VALUE_TYPE_NORM[vt]
    return vt if vt in VALID_VALUE_TYPE else ""


def _norm_granularity(unit_gran, unit):
    ug = _norm_text(unit_gran)
    if ug and ug not in GRANULARITY_POLLUTION and ug != "":
        # 已是合理粒度（含 / 或常见单位词）
        return ug
    # 从单位推断
    if unit in GRANULARITY_FROM_UNIT:
        return GRANULARITY_FROM_UNIT[unit]
    if unit and unit.endswith("人次"):
        return "人次"
    if unit and unit.endswith("亿元"):
        return "亿元"
    if unit == "%" or unit == "百分比":
        return "百分比"
    return "—"


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


def _norm_nature(nature, value_type):
    n = _norm_text(nature)
    if n == "定性":
        # 定性观察归为实际（数值类型=定性 强制 D）
        return "实际"
    if n in ("实际", "预计", "推算"):
        return n
    if n in ("无(水平值)", ""):
        return "实际"
    return n


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


def csv_to_items(path, target_year, target_holiday, region):
    """历史版 22 字段 CSV → 归一化 L1 条目列表 + (read, filtered)"""
    items = []
    read = 0
    filtered = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            read += 1
            row = {k: _norm_text(v) for k, v in raw.items()}
            problem = quality_problem(row, target_year, target_holiday)
            if problem:
                filtered.append((row.get("数据点", ""), problem))
                continue
            region_guess = _infer_region(row.get("数据点", ""), row.get("来源机构", ""))
            theme = row.get("主题", "")
            theme = THEME_NORM.get(theme, theme)
            gap = row.get("缺口标记", "空") or "空"
            note = row.get("备注", "")
            if row.get("数据性质") == "预计" and gap == "空":
                gap = "预判待回填"
            if not note:
                note = "历史导入"
            it = {
                "layer": "L1",
                "主题": theme,
                "数据点": row.get("数据点", ""),
                "数值": row.get("数值", ""),
                "单位": row.get("单位", ""),
                "单位粒度": _norm_granularity(row.get("单位粒度", ""), row.get("单位", "")),
                "统计起止日": row.get("统计起止日", ""),
                "统计窗口": row.get("统计窗口", ""),
                "口径版本": row.get("口径版本", ""),
                "指标口径类型": row.get("指标口径类型", ""),
                "口径类型": _norm_caliber(row.get("口径类型", "")),
                "数据性质": _norm_nature(row.get("数据性质", ""), row.get("数值类型", "")),
                "基期": row.get("基期", "—") or "—",
                "假期天数": row.get("假期天数", ""),
                "数值类型": _norm_value_type(row.get("数值类型", "")),
                "采集日期": row.get("采集日期", "") or datetime.now().strftime("%Y-%m-%d"),
                "缺口标记": gap,
                "来源机构": row.get("来源机构", ""),
                "报告/资料名": row.get("报告/资料名", ""),
                "发布时间": row.get("发布时间", ""),
                "可信度等级": row.get("可信度等级", "D"),
                "URL": row.get("URL", ""),
                "备注": note,
                "内容摘录": row.get("备注", ""),
                "地域粒度": region_guess,
            }
            # 推算行补推算依据（备注含公式时）
            if it["数据性质"] == "推算" and not it.get("推算依据"):
                it["推算依据"] = ""
            # 可信度纪律: 推算/测算/弱溯源/定性 强制 D（与 v1.1 门禁一致，历史脏等级降级）
            if (it["数据性质"] == "推算" or it["口径类型"] in ("测算", "弱溯源") or it["数值类型"] == "定性"):
                it["可信度等级"] = "D"
            items.append(it)
    return items, read, filtered


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
    """返回待导入文件列表（目录自动扫描）"""
    src = Path(source)
    if src.is_file():
        return [src]
    if src.is_dir():
        files = []
        for f in sorted(src.rglob("*")):
            if f.suffix.lower() in (".csv", ".json"):
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
    region = meta.get("region", "全国")

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
        if fmt == "csv_l1":
            items, read, filtered = csv_to_items(src, year, holiday, region)
        elif fmt == "json_fetch":
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

