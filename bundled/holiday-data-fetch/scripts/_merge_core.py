#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_merge_core.py — 分层同一性判定核心（v1.2 新增）

被 merge_rounds.py 与 import_history.py 复用。实现《数据同一性分层判定》L1–L5：

    L1 同源同载体重采  : URL+报告/资料名+数据点+口径版本+统计窗口+数据性质 全一致 → 去重
    L2 同源异性质并存  : 半键一致但数据性质不同（预计 vs 实际）→ 并存 + 观测关联回填
    L3 异源并存        : 数据点+口径一致但 URL/来源机构不同 → 全部保留
    L4 异口径并存      : 数据点一致但口径版本/统计窗口不同 → 全部保留
    L5 跨批次历史导入  : 历史导入 vs 本轮采集 键一致但批次不同 → 本轮优先，历史值入备注

合并规则（精确同一性命中时，按批次性质分派）：
  - 同值 → 去重；若本轮命中历史行，原位提升为本轮（备注"历史重复，已去重"）
  - 异值且同为本轮 → 冲突暂存（双保留 + 备注"双口径/冲突"）
  - 异值且跨批次（历史 vs 本轮）→ 本轮优先：更新值，历史值入备注"历史值:xxx(H批次)"
"""
from datetime import datetime

# L1 同一性键（完整）与半键（不含数据性质）
L1_IDENTITY = ("URL", "报告/资料名", "数据点", "口径版本", "统计窗口", "数据性质")
L1_SEMI = ("URL", "报告/资料名", "数据点", "口径版本", "统计窗口")
# L2 去重键
L2_KEY = ("现象描述", "来源机构", "来源URL")


def l1_identity(it):
    return tuple(str(it.get(k, "")) for k in L1_IDENTITY)


def l1_semi(it):
    return tuple(str(it.get(k, "")) for k in L1_SEMI)


def l2_key(it):
    return tuple(str(it.get(k, "")) for k in L2_KEY)


def is_historical(it):
    """历史导入行判定"""
    if str(it.get("数据来源", "")) == "历史导入":
        return True
    if str(it.get("观测批次", "")).startswith("H"):
        return True
    if str(it.get("round", "")) == "历史导入":
        return True
    return False


def batch_of(it):
    """观测批次码，如 R1 / H1"""
    return str(it.get("观测批次", "") or "")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _append_note(it, text):
    note = str(it.get("备注", "") or "")
    if note:
        it["备注"] = note + "；" + text
    else:
        it["备注"] = text


def _link_observation(a, b):
    """建立预测-实测对照关联（双向）"""
    if a.get("数据性质") == "预计" and b.get("数据性质") == "实际":
        pred, act = a, b
    elif b.get("数据性质") == "预计" and a.get("数据性质") == "实际":
        pred, act = b, a
    else:
        return False
    pred["观测关联"] = f"对照:实测{act.get('id', '')}"
    act["观测关联"] = f"对照:预测{pred.get('id', '')}"
    if pred.get("缺口标记") == "预判待回填":
        pred["缺口标记"] = "空"
    return True


def layered_merge(ws, new_items, batch_label, batch_kind, when=None, all_ids=None):
    """按 L1–L5 分层判定将 new_items 合并进工作区 ws。

    参数:
        ws         : 主工作区 dict（含 meta/items），会被原地修改
        new_items  : 待合并条目列表（应已含 id/round/观测批次/采集时间 等）
        batch_label: 批次标签，如 "2026-08-28-R2"（本轮）或 "H1"（历史导入）
        batch_kind : "round"（本轮采集）或 "history"（历史导入）
        when       : 采集时间（缺省取当前时刻）
        all_ids    : 可选 id 索引列表（用于分配 id）；缺省从 ws["meta"]["_all_ids"] 读取

    返回: (added, deduped, conflicts, linked)
        added    : 新增条目数
        deduped  : 去重条目数（同一观测重复采集/导入）
        conflicts: 冲突暂存条目数（同键异值双保留）
        linked   : 建立观测关联的对数
    """
    meta = ws.setdefault("meta", {})
    if all_ids is None:
        all_ids = meta.setdefault("_all_ids", [])
        if not all_ids:
            all_ids.extend({"id": it.get("id", ""), "layer": it.get("layer", "")} for it in ws.get("items", []))
            meta["_all_ids"] = all_ids
    items = ws["items"]
    when = when or now_str()

    # 建立索引
    exact_index = {}   # l1_identity -> [item, ...]（L1）
    semi_index = {}    # l1_semi -> [item, ...]（L1）
    l2_index = {}      # l2_key -> item（L2）
    for it in items:
        if it.get("layer") == "L1":
            exact_index.setdefault(l1_identity(it), []).append(it)
            semi_index.setdefault(l1_semi(it), []).append(it)
        else:
            l2_index.setdefault(l2_key(it), it)

    added = deduped = conflicts = linked = 0

    def next_id(layer):
        seq = meta.get("holiday_seq", "SY")
        year = meta.get("year", 2026)
        prefix = f"{year}-{seq}-{layer}-"
        nums = [int(i["id"].rsplit("-", 1)[-1]) for i in all_ids if i.get("id", "").startswith(prefix)]
        n = max(nums) + 1 if nums else 1
        return f"{prefix}{n:03d}"

    def register(it):
        nonlocal added
        it.setdefault("id", next_id(it.get("layer", "L1")))
        it.setdefault("round", batch_label)
        it.setdefault("观测批次", batch_label)
        it.setdefault("采集时间", when)
        items.append(it)
        all_ids.append({"id": it["id"], "layer": it.get("layer", "")})
        if it.get("layer") == "L1":
            exact_index.setdefault(l1_identity(it), []).append(it)
            semi_index.setdefault(l1_semi(it), []).append(it)
        else:
            l2_index.setdefault(l2_key(it), it)
        added += 1
        return it

    for it in new_items:
        layer = it.get("layer")
        if layer == "L2":
            key = l2_key(it)
            if key in l2_index:
                deduped += 1
                continue
            register(it)
            continue

        # L1
        ident = l1_identity(it)
        matches = exact_index.get(ident, [])
        if matches:
            old = matches[0]
            old_val = str(old.get("数值", ""))
            new_val = str(it.get("数值", ""))
            old_batch = batch_of(old)
            if old_val == new_val:
                # 同值：去重
                if batch_kind == "round" and is_historical(old):
                    # 本轮命中历史行 → 原位提升为本轮（保留本轮来源）
                    old["round"] = batch_label
                    old["观测批次"] = batch_label
                    old["采集时间"] = when
                    old["数据来源"] = "本轮采集"
                    _append_note(old, "历史重复，已去重")
                deduped += 1
            else:
                if batch_kind == "round" and is_historical(old):
                    # L5 跨批次：本轮优先更新，历史值入备注
                    _append_note(old, f"历史值:{old_val}({old_batch}批次)")
                    old["数值"] = it.get("数值", old_val)
                    old["单位"] = it.get("单位", old.get("单位", ""))
                    old["观测批次"] = batch_label
                    old["round"] = batch_label
                    old["采集时间"] = when
                    old["数据来源"] = "本轮采集"
                    for k in ("内容摘录", "发布时间", "备注"):
                        if it.get(k):
                            old[k] = it[k]
                    conflicts += 1
                elif batch_kind == "history" and not is_historical(old):
                    # 本轮已存在，历史导入不覆盖，历史值入备注
                    _append_note(old, f"历史值:{new_val}({batch_label}批次)")
                    deduped += 1
                elif batch_kind == "history" and is_historical(old):
                    # 历史重复导入：保留首见，异值入备注
                    if old_batch != batch_label:
                        _append_note(old, f"历史值:{new_val}({batch_label}批次)")
                    deduped += 1
                else:
                    # 同为本轮：冲突暂存，双保留
                    new_it = register(it)
                    _append_note(new_it, "双口径/冲突")
                    _append_note(old, "双口径/冲突")
                    conflicts += 1
            continue

        # 无精确命中：查半键（同源异性质）
        semi = l1_semi(it)
        semi_matches = semi_index.get(semi, [])
        coexisted = False
        for cand in semi_matches:
            if cand.get("数据性质") != it.get("数据性质"):
                # 同源异性质 → 并存
                new_it = register(it)
                if _link_observation(cand, new_it):
                    linked += 1
                coexisted = True
                break
        if coexisted:
            continue

        # L3 异源 / L4 异口径 / L5 键不一致 → 新观测
        register(it)

    return added, deduped, conflicts, linked
