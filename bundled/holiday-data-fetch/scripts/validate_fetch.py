#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_fetch.py — 采集门禁自检 + 导出兼容 (v1.2)

用法:
    python validate_fetch.py --workspace <主JSON> [--min-rows 35] [--check-snapshots]
    python validate_fetch.py --workspace <主JSON> --export-csv --out <目录>
    python validate_fetch.py --workspace <主JSON> --export-l2 --out <目录>

校验项 (对齐 references/collection-log.md 与 holiday-keywords.md v1.2):
  1. 字段完整性: L1 必备 22 字段 / L2 必备字段; 可信度纪律
  2. 行数门禁分档: 基础线(春节/十一≥35, 五一/端午/独立中秋≥25, 暑期≥30)
                   丰富线(春节/十一≥60, 五一/端午/独立中秋≥45, 暑期≥55)
  3. 全源覆盖: A(官方)+B(行业)+C(平台) 必采, E(支付)或F(舆情) 至少一组; B≥2机构/C≥3平台/地方政务≥3省市
  4. 可信度纪律: 推算/测算/弱溯源/定性 必须 D 级; 推算行占比 ≤30%
                 官方权威机构「预计」可标 A/B/C（不强制 D，见 R1 口径澄清）
  5. 指标维度覆盖度: 10 核心维度 ≥7 PASS, 5-6 WARN, <5 FAIL
  6. 地域粒度分布: 全国级 >70% WARN; 枚举白名单(主题/地域粒度) 双写 WARN (R2)
  7. 快照校验 (--check-snapshots): JSON 中 snapshot 非"未存"的文件必须真实存在
     历史导入行(快照=未存-历史导入)单独统计, 不计入本轮快照覆盖率
  8. 丰富度评分 (0-100): 行数30(仅计本轮) + 维度30 + 地域20 + 来源20
  9. 观测序列化统计 (v1.2): 本轮新增占比<40% WARN; 预计/实测对照未回填 WARN; 同源同载体重复率 WARN

导出:
  --export-csv : 筛 layer=L1, 导出标准 22 字段 CSV
  --export-l2  : 筛 layer=L2, 导出现象素材库 JSON
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

L1_FIELDS = ["主题", "数据点", "数值", "单位", "单位粒度", "统计起止日", "统计窗口", "口径版本",
             "指标口径类型", "口径类型", "数据性质", "基期", "假期天数", "数值类型", "采集日期",
             "缺口标记", "来源机构", "报告/资料名", "发布时间", "可信度等级", "URL", "备注"]
L2_REQUIRED = ["现象标签", "主题归属", "现象描述", "素材类型", "来源机构", "来源URL", "采集日期"]
MIN_ROWS = {"春节": 35, "十一": 35, "五一": 25, "端午": 25, "中秋": 25, "暑期": 30}
RICH_ROWS = {"春节": 60, "十一": 60, "五一": 45, "端午": 45, "中秋": 45, "暑期": 55}

# 主题/地域粒度枚举白名单 (R2 修复; 覆盖 v1.1 实际产出 13 种)
THEME_WHITELIST = {"总体", "交通出行", "景区目的地", "酒店住宿", "平台渠道", "旅行社",
                   "消费宏观", "游客画像", "新消费", "支付交易", "出入境", "派生指标", "分省/分市"}
THEME_DEPRECATED = {"支付": "支付交易", "酒店": "酒店住宿", "平台": "平台渠道", "交通": "交通出行",
                    "景区级数据": "景区目的地", "景区数据": "景区目的地"}
REGION_WHITELIST = {"全国", "省级", "城市级", "景区商圈级", "跨区域"}
REGION_DEPRECATED = {"景区级": "景区商圈级"}

# 口径类型 -> 全源组
CALIBER_TO_SOURCE = {
    "官方总量": "A", "官方跨区域(含自驾)": "A", "官方营业性(不含自驾)": "A", "官方重点监测": "A", "官方边检": "A",
    "实测": "A",  # 2023 系历史错版别名
    "行业协会计": "B", "平台自披露": "C", "平台披露": "C",  # 2023 系历史错版别名
}
PLATFORM_HINTS = ["携程", "同程", "飞猪", "途牛", "美团", "滴滴", "高德", "抖音", "京东", "天猫", "去哪儿", "马蜂窝", "大众点评"]
PAYMENT_HINTS = ["银联", "网联", "支付宝", "微信支付"]
SENTIMENT_HINTS = ["微博", "小红书", "抖音", "知乎", "黑猫"]
REGION_HINTS = ["文旅厅", "商务局", "省政府", "市政府", "政府网"]
PROVINCE_NAMES = ["广东", "浙江", "江苏", "四川", "山东", "河南", "湖北", "湖南", "福建", "安徽", "河北", "陕西", "云南", "贵州", "辽宁"]
CITY_NAMES = ["北京", "上海", "广州", "成都", "重庆", "杭州", "西安", "武汉", "南京", "深圳", "长沙", "郑州", "青岛", "天津", "苏州"]

# L1 同一性键（与 _merge_core.py 一致，用于观测重复率检查）
L1_IDENTITY = ("URL", "报告/资料名", "数据点", "口径版本", "统计窗口", "数据性质")
L1_SEMI = ("URL", "报告/资料名", "数据点", "口径版本", "统计窗口")


def is_history(it):
    return (str(it.get("数据来源", "")) == "历史导入"
            or str(it.get("观测批次", "")).startswith("H")
            or str(it.get("round", "")) == "历史导入")


def check_fields(items):
    problems = []
    for i, it in enumerate(items):
        layer = it.get("layer")
        if layer == "L1":
            # 备注为可空自由文本(口径字典第22字段), 不纳入必填检查
            missing = [f for f in L1_FIELDS if f != "备注" and (f not in it or it[f] in (None, ""))]
            if missing:
                problems.append(f"第{i}条(L1) 缺字段: {missing}")
            # 可信度纪律: 推算/测算/弱溯源/定性(非定量) 强制 D; 机构实测复合指标(如 STR RevPAR)按实测等级
            # v1.2 口径: 官方权威机构「预计」可标 A/B/C (R1 修复, 不强制 D)
            dforce = (
                it.get("数据性质") == "推算"
                or it.get("口径类型") in ("测算", "弱溯源")
                or it.get("数值类型") == "定性"
            )
            if dforce and it.get("可信度等级") != "D":
                problems.append(f"第{i}条(L1) 推算/测算/弱溯源/定性 但等级={it.get('可信度等级')}, 须强制 D")
            # 推算行应填推算依据或备注
            if it.get("数据性质") in ("推算", "预计") and not it.get("推算依据") and not it.get("备注"):
                problems.append(f"第{i}条(L1) 推算/预计行缺推算依据或备注")
        elif layer == "L2":
            missing = [f for f in L2_REQUIRED if f not in it or it[f] in (None, "")]
            if missing:
                problems.append(f"第{i}条(L2) 缺字段: {missing}")
    return problems


def check_enum_whitelist(items):
    """R2: 主题/地域粒度枚举白名单校验（废弃写法 WARN）"""
    warns = []
    for i, it in enumerate(items):
        if it.get("layer") != "L1":
            continue
        theme = str(it.get("主题", ""))
        if theme and theme not in THEME_WHITELIST:
            target = THEME_DEPRECATED.get(theme)
            if target:
                warns.append(f"第{i}条 主题 '{theme}' 为废弃写法, 应统一 '{target}'")
            else:
                warns.append(f"第{i}条 主题 '{theme}' 不在白名单 {sorted(THEME_WHITELIST)}")
        rg = str(it.get("地域粒度", ""))
        base = rg.split("(")[0] if "(" in rg else rg
        if base and base not in REGION_WHITELIST:
            target = REGION_DEPRECATED.get(base)
            if target:
                warns.append(f"第{i}条 地域粒度 '{base}' 为废弃写法, 应统一 '{target}'")
            else:
                warns.append(f"第{i}条 地域粒度 '{base}' 不在白名单 {sorted(REGION_WHITELIST)}")
    return warns


def check_source_coverage(items):
    groups = set()
    orgs = []
    for it in items:
        if it.get("layer") == "L1":
            c = it.get("口径类型", "")
            if c in CALIBER_TO_SOURCE:
                groups.add(CALIBER_TO_SOURCE[c])
            orgs.append(str(it.get("来源机构", "")))
    joined = " ".join(orgs)
    if any(h in joined for h in PLATFORM_HINTS):
        groups.add("C")
    if any(h in joined for h in PAYMENT_HINTS):
        groups.add("E")
    if any(h in joined for h in SENTIMENT_HINTS):
        groups.add("F")

    org_set = set(orgs)
    b_orgs = [o for o in org_set if any(k in o for k in ["研究院", "协会", "证券", "STR", "中金", "国泰", "华创", "万联", "信达", "中银", "中邮", "中信"])]
    c_orgs = [o for o in org_set if any(h in o for h in PLATFORM_HINTS)]
    region_orgs = [o for o in org_set if any(h in o for h in REGION_HINTS) or any(p in o for p in PROVINCE_NAMES) or any(c in o for c in CITY_NAMES)]
    if b_orgs:
        groups.add("B")  # 行业机构由机构名识别补充（历史导入数据适用）

    notes = []
    if not {"A", "B", "C"} <= groups:
        notes.append(f"全源覆盖缺口: 当前组={sorted(groups)}, 须含 A+B+C")
    if not ({"E", "F"} & groups):
        notes.append(f"全源覆盖缺口: E(支付)或F(舆情) 至少一组, 当前组={sorted(groups)}")
    if len(b_orgs) < 2:
        notes.append(f"来源深度缺口: B 组机构 {len(b_orgs)} < 2 (当前: {b_orgs})")
    if len(c_orgs) < 3:
        notes.append(f"来源深度缺口: C 组平台 {len(c_orgs)} < 3 (当前: {c_orgs})")
    if len(region_orgs) < 3:
        notes.append(f"来源深度缺口: 地方政务/省市 {len(region_orgs)} < 3 (当前: {region_orgs})")
    return groups, notes, org_set


def check_dimension_coverage(items):
    """10 核心维度覆盖度检测"""
    dims = {"出游人次": False, "旅游收入": False, "交通客运": False, "消费/社零": False,
            "支付交易": False, "出入境": False, "分省/分市": False, "酒店/住宿": False,
            "景区/目的地": False, "派生指标": False}
    orgs = []
    for it in items:
        if it.get("layer") != "L1":
            continue
        t = str(it.get("主题", ""))
        dp = str(it.get("数据点", ""))
        cal = str(it.get("指标口径类型", ""))
        org = str(it.get("来源机构", ""))
        orgs.append(org)
        nat = str(it.get("数据性质", ""))
        rg = str(it.get("地域粒度", ""))

        if t == "总体" and ("人次" in dp or "出游" in dp):
            dims["出游人次"] = True
        if t == "总体" and ("收入" in dp or "花费" in dp or "消费总额" in dp or cal == "旅游总花费"):
            dims["旅游收入"] = True
        if t == "交通出行" and ("客运" in dp or "铁路" in dp or "民航" in dp or "公路" in dp or "水路" in dp or "流动" in dp):
            dims["交通客运"] = True
        if t == "消费宏观" and ("社零" in dp or "零售" in dp or "消费总额" in dp or "餐饮" in dp or "销售" in dp):
            dims["消费/社零"] = True
        if any(h in org for h in PAYMENT_HINTS) or cal == "支付清算额" or t == "支付交易":
            dims["支付交易"] = True
        if "出入境" in dp or "出境" in dp or "入境" in dp or "口岸" in cal:
            dims["出入境"] = True
        if rg.startswith("省级") or rg.startswith("城市级"):
            dims["分省/分市"] = True
        if t == "酒店住宿":
            dims["酒店/住宿"] = True
        if t == "景区目的地":
            dims["景区/目的地"] = True
        if nat in ("推算", "预计") or any(k in dp for k in ["客单价", "人均", "日均", "等效", "恢复度"]):
            dims["派生指标"] = True
    covered = [k for k, v in dims.items() if v]
    return dims, covered


def check_region_distribution(items):
    from collections import Counter
    counter = Counter()
    for it in items:
        if it.get("layer") == "L1":
            rg = str(it.get("地域粒度", ""))
            key = rg.split("(")[0] if "(" in rg else rg
            counter[key] += 1
    total = sum(counter.values())
    national = counter.get("全国", 0)
    ratio = (national / total * 100) if total else 0
    fine = sum(v for k, v in counter.items() if k.startswith("省级") or k.startswith("城市级") or k.startswith("景区"))
    fine_ratio = (fine / total * 100) if total else 0
    return counter, ratio, fine_ratio


def check_observation_metrics(items):
    """v1.2: 预测/实测对照 + 观测重复率 + 本轮新增占比"""
    l1 = [i for i in items if i.get("layer") == "L1"]
    n_total = len(items)
    n_history = sum(1 for i in items if is_history(i))
    n_current = n_total - n_history

    pred = [i for i in l1 if i.get("数据性质") == "预计"]
    actual = [i for i in l1 if i.get("数据性质") == "实际"]
    linked = [i for i in l1 if i.get("观测关联")]

    # 预测-实测对照: 对每个预计行, 检查是否有同半键实测行
    semi_of = lambda it: tuple(str(it.get(k, "")) for k in L1_SEMI)
    actual_by_semi = {}
    for a in actual:
        actual_by_semi.setdefault(semi_of(a), []).append(a)
    pred_with_actual = 0
    pred_unlinked = []
    for p in pred:
        mates = actual_by_semi.get(semi_of(p), [])
        if mates:
            pred_with_actual += 1
            if not p.get("观测关联"):
                pred_unlinked.append(f"{p.get('id', '?')}({p.get('数据点', '')})")
    # 观测重复率: 同源同载体（含数据性质）全一致 >1 条 → 重复
    from collections import Counter as _C
    idc = _C(tuple(str(i.get(k, "")) for k in L1_IDENTITY) for i in l1)
    dup_keys = {k: v for k, v in idc.items() if v > 1}
    dup_n = sum(v - 1 for v in dup_keys.values())

    return {
        "n_total": n_total, "n_history": n_history, "n_current": n_current,
        "pred": len(pred), "actual": len(actual), "linked": len(linked),
        "pred_with_actual": pred_with_actual, "pred_unlinked": pred_unlinked,
        "dup_n": dup_n, "dup_keys": dup_keys,
    }


def check_snapshots(items, ws_root):
    missing = []
    for it in items:
        snap = it.get("snapshot", "")
        if snap and not str(snap).startswith("未存"):
            if not (ws_root / snap).exists():  # v1.1 修复: 用工作区根目录拼接
                missing.append(f"{it.get('id')}: 快照缺失 {snap}")
    return missing


def richness_score(current_rows, min_rows, rich_rows, dims_covered, region_dist, n_orgs):
    """丰富度评分 0-100: 行数30(仅计本轮新增) + 维度30 + 地域20 + 来源20"""
    # 行数 (30): 仅计本轮采集行（历史导入不计入，防导入刷分）
    if current_rows >= rich_rows:
        score_rows = 30
    elif current_rows >= min_rows:
        score_rows = 18
    else:
        score_rows = max(0, int(current_rows / min_rows * 18))
    # 维度 (30): 10 维每维 3
    score_dims = len(dims_covered) * 3
    # 地域 (20): 全国/省级/城市级/景区商圈级 每级 5
    present_levels = sum(1 for k in ("全国", "省级", "城市级", "景区") if any(str(lv).startswith(k) for lv in region_dist))
    score_region = present_levels * 5
    # 来源 (20): ≥30 满分, ≥15 得 10, <15 得 5
    score_src = 20 if n_orgs >= 30 else (10 if n_orgs >= 15 else 5)
    return min(100, score_rows + score_dims + score_region + score_src)


def export_csv(items, out_path):
    l1 = [i for i in items if i.get("layer") == "L1"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=L1_FIELDS, extrasaction="ignore")
        w.writeheader()
        for it in l1:
            w.writerow({k: it.get(k, "") for k in L1_FIELDS})
    return len(l1)


def export_l2(items, out_path, meta):
    l2 = [i for i in items if i.get("layer") == "L2"]
    lib = {
        "schema": "phenomena-library-v1",
        "year": meta.get("year"),
        "holiday": meta.get("holiday"),
        "region": meta.get("region"),
        "collected_at": meta.get("updated_at"),
        "items": l2,
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    return len(l2)


def main():
    ap = argparse.ArgumentParser(description="采集门禁自检 + 导出 (v1.2)")
    ap.add_argument("--workspace", required=True, help="主 JSON 路径")
    ap.add_argument("--min-rows", type=int, default=None, help="覆盖基础线")
    ap.add_argument("--check-snapshots", action="store_true", help="校验快照文件存在性")
    ap.add_argument("--export-csv", action="store_true", help="导出 L1 为 22 字段 CSV")
    ap.add_argument("--export-l2", action="store_true", help="导出 L2 为现象素材库 JSON")
    ap.add_argument("--out", default=".", help="导出目录 (默认当前目录)")
    args = ap.parse_args()

    ws_path = Path(args.workspace)
    if not ws_path.exists():
        print(f"[错误] 主 JSON 不存在: {ws_path}")
        return 1
    with ws_path.open("r", encoding="utf-8-sig") as f:
        ws = json.load(f)
    if not isinstance(ws, dict) or "meta" not in ws or "items" not in ws:
        print(f"[错误] 主 JSON 结构不完整: 需含 meta 与 items (应由 init_workspace.py 创建/续采)")
        return 1
    meta = ws["meta"]
    items = ws["items"]

    holiday = meta.get("holiday", "")
    min_rows = args.min_rows or MIN_ROWS.get(holiday, 25)
    rich_rows = RICH_ROWS.get(holiday, min_rows * 2)
    l1_count = sum(1 for i in items if i.get("layer") == "L1")
    l2_count = sum(1 for i in items if i.get("layer") == "L2")
    total = len(items)

    print(f"=== 门禁自检: {meta.get('year')} {holiday} ({meta.get('region')}) ===")
    print(f"  条目总数={total} (L1={l1_count}, L2={l2_count})  基础线={min_rows} 丰富线={rich_rows}")

    ok = True
    # 0 观测序列化统计 (v1.2)
    obs = check_observation_metrics(items)
    print(f"  [INFO] 观测: 本轮新增 {obs['n_current']} / 历史导入 {obs['n_history']} | "
          f"预计 {obs['pred']} / 实测 {obs['actual']} / 已回填对照 {obs['linked']}")
    if obs["n_history"] > 0:
        cur_ratio = obs["n_current"] / obs["n_total"] * 100 if obs["n_total"] else 0
        if cur_ratio < 40:
            print(f"  [WARN] 本轮新增占比 {cur_ratio:.0f}% < 40%, 历史导入占比过高, 防采集偷懒")
        else:
            print(f"  [INFO] 本轮新增占比 {cur_ratio:.0f}% (目标 ≥40%)")
    if obs["pred_unlinked"]:
        print(f"  [WARN] {len(obs['pred_unlinked'])} 条预计行已存在同键实测但未回填观测关联: {obs['pred_unlinked'][:3]}")
    if obs["dup_n"] > 0:
        print(f"  [WARN] 同源同载体重复 {obs['dup_n']} 条 (L1 去重未生效), 首例键: {list(obs['dup_keys'].keys())[0]}")

    # 1 行数分档（历史导入计入总量达标；本轮新增占比另行统计防偷懒）
    if total >= rich_rows:
        print(f"  [丰富] 行数 {total} ≥ 丰富线 {rich_rows} (本轮 {obs['n_current']} / 历史导入 {obs['n_history']})")
    elif total >= min_rows:
        print(f"  [基础] 行数 {total} 达标(基础线 {min_rows}), 未达丰富线 {rich_rows} (本轮 {obs['n_current']} / 历史导入 {obs['n_history']})")
    else:
        print(f"  [FAIL] 行数 {total} < 基础线 {min_rows} (本轮 {obs['n_current']} / 历史导入 {obs['n_history']})")
        ok = False

    # 2 字段
    probs = check_fields(items)
    if probs:
        print(f"  [FAIL] 字段/等级问题 {len(probs)} 条, 首条: {probs[0]}")
        ok = False
    else:
        print("  [PASS] 字段完整性 & 可信度纪律")

    # 2b 枚举白名单 (R2)
    enum_warns = check_enum_whitelist(items)
    if enum_warns:
        print(f"  [WARN] 枚举白名单 {len(enum_warns)} 处, 首处: {enum_warns[0]} (见 json-schema.md 三·B)")
    else:
        print("  [PASS] 主题/地域粒度枚举白名单")

    # 3 全源 + 来源深度
    groups, gnotes, org_set = check_source_coverage(items)
    print(f"  [INFO] 全源组覆盖: {sorted(groups)} | 来源机构去重={len(org_set)}")
    for n in gnotes:
        print(f"  [WARN] {n}")
    if any("缺口" in n for n in gnotes):
        ok = False

    # 4 指标维度覆盖
    dims, covered = check_dimension_coverage(items)
    nd = len(covered)
    if nd >= 7:
        print(f"  [PASS] 指标维度覆盖 {nd}/10: {covered}")
    elif nd >= 5:
        print(f"  [WARN] 指标维度覆盖 {nd}/10 (5-6 需声明缺口): 缺 {sorted(set(dims)-set(covered))}")
    else:
        print(f"  [FAIL] 指标维度覆盖 {nd}/10 (<5): 缺 {sorted(set(dims)-set(covered))}")
        ok = False

    # 5 地域粒度
    rdist, nratio, fratio = check_region_distribution(items)
    print(f"  [INFO] 地域粒度分布: {dict(rdist)} | 全国级占比={nratio:.0f}% | 省+市+景区占比={fratio:.0f}%")
    if nratio > 70:
        print(f"  [WARN] 全国级占比 {nratio:.0f}% > 70%, 细粒度数据不足")

    # 6 推算占比
    est = sum(1 for i in items if i.get("layer") == "L1" and i.get("数据性质") in ("推算", "预计"))
    est_ratio = est / total * 100 if total else 0
    print(f"  [INFO] 推算/预计行={est} ({est_ratio:.0f}%)  ≤30% 约束: {'PASS' if est_ratio <= 30 else 'FAIL'}")
    if est_ratio > 30:
        print("  [FAIL] 推算/预计行占比超过 30%")
        ok = False

    # 7 快照 (v1.2: 历史导入行单独统计, 不计入本轮覆盖率)
    if args.check_snapshots:
        missing = check_snapshots(items, ws_path.parent)
        round_entries = [i for i in items if not is_history(i)]
        total_url = sum(1 for i in round_entries if i.get("snapshot") and not str(i.get("snapshot", "")).startswith("未存"))
        total_entries = sum(1 for i in round_entries if i.get("URL") or i.get("来源URL"))
        hist_entries = [i for i in items if is_history(i)]
        hist_no_snap = sum(1 for i in hist_entries if str(i.get("snapshot", "")).startswith("未存"))
        if total_entries:
            coverage = total_url / total_entries * 100
            print(f"  [INFO] 本轮快照覆盖率={coverage:.0f}% ({total_url}/{total_entries})  目标≥80% | 历史导入行 {len(hist_entries)} 条(快照未存 {hist_no_snap})单独计")
        else:
            coverage = None
            print(f"  [INFO] 本轮无采集条目, 快照覆盖率不适用 | 历史导入行 {len(hist_entries)} 条(快照未存 {hist_no_snap})单独计")
        if missing:
            print(f"  [FAIL] {len(missing)} 个快照文件缺失, 首例: {missing[0]}")
            ok = False
        elif coverage is not None and coverage < 80:
            print("  [WARN] 本轮快照覆盖率低于 80%, 需在交付说明声明缺口")

    # 8 丰富度评分 (行数仅计本轮)
    score = richness_score(obs["n_current"], min_rows, rich_rows, covered, list(rdist.keys()), len(org_set))
    print(f"  [INFO] 丰富度评分={score}/100 (本轮行数+维度+地域+来源; 历史导入不计行数分)")

    # 9 导出
    if args.export_csv:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        n = export_csv(items, out_dir / f"{meta.get('year')}{holiday}消费数据集.csv")
        print(f"  [导出] L1 -> {out_dir / (str(meta.get('year')) + holiday + '消费数据集.csv')} ({n} 行 22 字段)")
    if args.export_l2:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        n = export_l2(items, out_dir / "现象素材库.json", meta)
        print(f"  [导出] L2 -> {out_dir / '现象素材库.json'} ({n} 条)")

    print("=== 结论:", "PASS" if ok else "FAIL (见上方缺口) ===")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())

