#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_rounds.py — 增量归集: 将新采集轮次合并进主 JSON（v1.2 分层同一性判定）

用法:
    python merge_rounds.py --workspace <主JSON> --round-file <新轮次JSON> [--round-id R2]

规则（v1.2，对齐 references/collection-log.md 与 _merge_core.py）:
  - L1 去重键: (URL, 报告/资料名, 数据点, 口径版本, 统计窗口, 数据性质) 全一致 → 去重
  - L2 去重键: (现象描述, 来源机构, 来源URL)
  - L2 同源异性质: 半键一致但 数据性质 不同（预计 vs 实际）→ 并存 + 观测关联自动回填
  - L3 异源 / L4 异口径: 全部保留（不同观测）
  - L5 跨批次历史导入: 本轮命中历史行 → 本轮优先更新, 历史值入备注
  - 同键同值: 保留首见; 同键不同值(同本轮): 冲突暂存(双保留 + 备注"双口径/冲突")
  - id 追加: 新条目按 {年}-{节序号}-{层}-{3位流水} 分配, 已存在 id 不改写
  - 更新 meta: updated_at/rounds/counts/merge_notes; 原子写回
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

from _merge_core import layered_merge, now_str

REQUIRED_LAYER_FIELDS = {"L1": ["layer", "主题", "数据点", "数值", "单位", "来源机构", "URL", "可信度等级", "数值类型", "数据性质", "口径类型", "采集日期"],
                         "L2": ["layer", "现象标签", "主题归属", "现象描述", "素材类型", "来源机构", "来源URL", "采集日期"]}


def main():
    ap = argparse.ArgumentParser(description="增量归集: 合并新轮次到主 JSON (v1.2)")
    ap.add_argument("--workspace", required=True, help="主 JSON 路径")
    ap.add_argument("--round-file", required=True, help="新轮次 JSON 路径")
    ap.add_argument("--round-id", default=None, help="轮次 ID, 如 2026-08-27-R2; 缺省自动生成")
    args = ap.parse_args()

    ws_path = Path(args.workspace)
    rf_path = Path(args.round_file)
    if not ws_path.exists():
        print(f"[错误] 主 JSON 不存在: {ws_path} (先运行 init_workspace.py)")
        return 1
    if not rf_path.exists():
        print(f"[错误] 轮次 JSON 不存在: {rf_path}")
        return 1

    with ws_path.open("r", encoding="utf-8-sig") as f:
        ws = json.load(f)
    with rf_path.open("r", encoding="utf-8-sig") as f:
        round_data = json.load(f)

    meta = ws["meta"]
    today = date.today().isoformat()
    round_id = args.round_id or f"{today}-R{len(meta.get('rounds', [])) + 1}"

    # 校验轮次条目字段
    bad = [i for i in round_data.get("items", []) if i.get("layer") not in ("L1", "L2")]
    if bad:
        print(f"[错误] 轮次含非法 layer 条目 {len(bad)} 条 (layer 必须为 L1/L2)")
        return 1
    missing = []
    for i in round_data.get("items", []):
        req = REQUIRED_LAYER_FIELDS.get(i.get("layer"), [])
        for k in req:
            if k not in i or i[k] in (None, ""):
                missing.append(f"{i.get('id', '?')} 缺字段 {k}")
    if missing:
        print(f"[错误] 轮次条目字段不完整: 首例 {missing[0]}")
        return 1

    # 已存在 id 索引
    meta.setdefault("_all_ids", [])
    if not meta["_all_ids"]:
        meta["_all_ids"].extend({"id": it.get("id", ""), "layer": it.get("layer", "")} for it in ws.get("items", []))

    # 轮次条目补批次标注
    when = now_str()
    for it in round_data.get("items", []):
        it.setdefault("采集时间", when)
        it.setdefault("观测批次", round_id.split("-")[-1] if "-" in round_id else round_id)
        it.setdefault("数据来源", "本轮采集")
        it.setdefault("round", round_id)

    # 分层合并（本轮）
    added, deduped, conflicts, linked = layered_merge(
        ws, round_data.get("items", []),
        batch_label=round_id, batch_kind="round", when=when,
        all_ids=meta["_all_ids"],
    )

    # 更新 meta
    if round_id not in meta["rounds"]:
        meta["rounds"].append(round_id)
    meta["updated_at"] = today
    meta["counts"]["L1"] = sum(1 for i in ws["items"] if i.get("layer") == "L1")
    meta["counts"]["L2"] = sum(1 for i in ws["items"] if i.get("layer") == "L2")
    meta["counts"]["snapshots"] = sum(1 for i in ws["items"] if i.get("snapshot") and not str(i.get("snapshot", "")).startswith("未存"))
    meta["counts"]["history_imported"] = sum(1 for i in ws["items"] if i.get("数据来源") == "历史导入")
    merge_note = f"{round_id}: 新增 {added} 条, 去重 {deduped} 条, 冲突 {conflicts} 条, 观测关联 {linked} 对"
    meta["merge_notes"].append(merge_note)

    # 原子写回
    tmp = ws_path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(ws, f, ensure_ascii=False, indent=2)
    tmp.replace(ws_path)

    print(f"[归集完成] round={round_id}")
    print(f"  新增 {added} 条, 去重 {deduped} 条, 冲突暂存/更新 {conflicts} 条, 观测关联 {linked} 对")
    print(f"  当前计数: L1={meta['counts']['L1']} L2={meta['counts']['L2']} snapshots={meta['counts']['snapshots']} history={meta['counts'].get('history_imported', 0)}")
    print(f"  rounds={meta['rounds']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

