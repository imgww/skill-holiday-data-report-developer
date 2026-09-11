#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_workspace.py — 初始化/读取 holiday-data-fetch 采集工作区

用法:
    python init_workspace.py --output-dir <目录> --year <年份> --holiday <节假日> [--region 全国] [--force]

行为:
  - 若主文件 holiday-data-fetch.json 不存在: 创建含 meta 的空工作区(仅 meta, items=[])
  - 若已存在: 读取并打印归集状态(rounds/counts/updated_at), 提示续采, 不覆盖
  - --force: 重建空工作区(慎用, 会清空现有归集)
  - 节假日校验: 春节/端午/五一/暑期/中秋/十一
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MAIN_FILE = "holiday-data-fetch.json"
HOLIDAYS = ["春节", "端午", "五一", "暑期", "中秋", "十一"]
HOLIDAY_SEQ = {"春节": "CH", "端午": "DW", "五一": "WY", "暑期": "SH", "中秋": "MQ", "十一": "SY"}


def empty_workspace(year, holiday, region, today):
    return {
        "schema": "holiday-data-fetch-v1",
        "meta": {
            "year": year,
            "holiday": holiday,
            "region": region,
            "created_at": today,
            "updated_at": today,
            "rounds": [],
            "caliber_version": "holiday-data-report-caliber-v2.1",
            "holiday_config_version": "holiday-keywords-v1.0",
            "merge_notes": [],
            "counts": {"L1": 0, "L2": 0, "snapshots": 0},
        },
        "items": [],
    }


def main():
    ap = argparse.ArgumentParser(description="holiday-data-fetch 工作区初始化")
    ap.add_argument("--output-dir", required=True, help="输出目录")
    ap.add_argument("--year", type=int, required=True, help="目标年度, 如 2026")
    ap.add_argument("--holiday", required=True, choices=HOLIDAYS, help="节假日")
    ap.add_argument("--region", default="全国", help="地域, 默认全国")
    ap.add_argument("--force", action="store_true", help="重建空工作区(清空现有归集)")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    main_path = out_dir / MAIN_FILE
    today = date.today().isoformat()

    if main_path.exists() and not args.force:
        with main_path.open("r", encoding="utf-8-sig") as f:
            ws = json.load(f)
        m = ws.get("meta", {})
        print(f"[状态] 工作区已存在: {main_path}")
        print(f"  year={m.get('year')} holiday={m.get('holiday')} region={m.get('region')}")
        print(f"  rounds={m.get('rounds')} counts={m.get('counts')} updated_at={m.get('updated_at')}")
        print(f"  提示: 续采模式, 新轮次写入 round_{today}-R{len(m.get('rounds', [])) + 1}.json 后调用 merge_rounds.py 归集")
        return 0

    ws = empty_workspace(args.year, args.holiday, args.region, today)
    # 写入中文节假日序号到 meta, 供 id 生成
    ws["meta"]["holiday_seq"] = HOLIDAY_SEQ[args.holiday]
    with main_path.open("w", encoding="utf-8") as f:
        json.dump(ws, f, ensure_ascii=False, indent=2)
    print(f"[新建] 工作区已创建: {main_path}")
    print(f"  year={args.year} holiday={args.holiday} region={args.region}")
    print(f"  schema={ws['schema']} counts={ws['meta']['counts']}")
    print("  下一步: 按 holiday-keywords.md 展开检索词, 多轮检索, 每轮产物写 round_{date}-R{n}.json, 再 merge_rounds.py 归集")
    return 0


if __name__ == "__main__":
    sys.exit(main())

