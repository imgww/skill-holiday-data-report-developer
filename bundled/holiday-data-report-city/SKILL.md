---
name: holiday-data-report-city
description: "City-dimension extension of holiday-data-report. Produces a city/regional profile of Chinese holiday consumption data for any year and any Chinese holiday, built on the national SSOT: city rows written into the same `holiday-data-fetch.json` (22 inherited national fields + 8 city fields, distinguished by the `地域粒度` field rather than a separate file), each linked to a national indicator key; an Economist/FT-style single-file HTML report with inline-SVG visualizations (rankings, regional distribution, share donuts, divergence bars), a data provenance document, and a landing page. Reconciliation is mandatory and comes in two forms — additive indicators close to the national total (Σ ≤ 100% plus an undisclosed residual), flow indicators use an upper-bound multiple (1.5–2.5× normal, > 3× blocks). Hard blocks: R-CITY-1 share over 100% / abnormal multiple, R-CITY-2 caliber drift, R-CITY-3 orphan city row with no national linkage, R-CITY-4 fabricated residual. Delivered by holiday-data-report when [地域] resolves to a concrete city. Use when the user requests a city or regional breakdown of holiday consumption data."
version: 1.5.0
author: workbuddy
agent_created: true
---

# Consumption Data Report · City（节假日消费数据报告 · 城市视角）

## Overview

在 `holiday-data-report` 的**全国 SSOT 之上**叠加城市/区域空间剖面，产出以城市为核心的图文报告。

**核心定位三句话**
1. **继承不重造**：全国总量、口径字典、节假日配置、五阶段方法论继承自 `holiday-data-report`；本技能只增量定义城市维度。
2. **勾稽不脱钩**：城市数据不是另一套数字，而是全国数据集的**空间剖面**。每条必须勾稽到某全国指标键，可比口径下与全国总量闭合或给出可解释倍数。
3. **图文要可读**：内联 SVG 可视化（排名条 / 区域分布 / 占比环 / 对比发散条），图表与数据表双轨。

## 依赖关系（必读）

| 项目 | 处理方式 |
|---|---|
| 全国 22 字段口径字典 | 引用父技能 `references/caliber-dictionary.md`，本技能**不复制** |
| 全国 A–J 数据源矩阵 | 引用父技能 `references/holiday-config.md`；城市增量见 `references/holiday-config-city.md` |
| 全国数据集（SSOT） | **勾稽基准**：`holiday-data-reports/data_set/{年份}_{节假日}/holiday-data-fetch.json` 中 `地域粒度=全国` 的行；城市行写入同一文件，**引用不重造** |
| 五阶段方法论 | 沿用父技能；城市增量见 `references/development-prompt-city.md` 与下方「五阶段增量」 |
| 设计系统与模板 | 沿用父技能 `style-guide.md` + `report-template.html`；图表规范见 `references/style-guide-viz.md` |

> 本技能随父技能内置于 `bundled/holiday-data-report-city/`，随包可用、无需单独安装。
> 若运行环境未安装父技能，本技能 `references/` 已含城市增量全部规则，
> 全国 22 字段要点在 `caliber-dictionary-city.md` 中摘要引用，可降级独立作业；
> 但**勾稽基准仍需全国数据**——无全国 SSOT 时城市报告不成立。

## Parameter Resolution

解析 **[年份][节日][城市]**，规则同父技能：年份默认当前年，节日取当前日期所在节假日，无法推导则**主动询问**用户。
地域解析为**具体城市**时由本技能承接；`全国` 或 `全国+城市` 由父技能先出全国 SSOT，再交接本技能。

## When to Use

用户要求**城市/区域视角**的节假日消费数据时触发：「哪个城市[节假日]最火」「[节假日]城市消费排名/区域分布」「从城市看[节假日]消费结构」，或在已生成全国报告后补充城市剖面。适用节假日：春节 / 端午 / 五一 / 暑期 / 中秋 / 十一。

### 不适用场景

继承父技能全部边界（非中国节假日、无公开来源、秒级实时、非消费主题、需原创调研、跨境对比）。城市增量边界：

1. **仅有城市、无全国勾稽**：城市行无法关联任何全国指标键（触发 R-CITY-3）——城市报告**必须以全国 SSOT 为基准**，不得孤立成"城市榜"。
2. **纯平台城市榜营销稿**：以携程/同程等 C 级平台榜为主、不标"平台自身口径，非全市场"、不与全国勾稽 → 明确降级或拒做。
3. **跨城随意相加**：把不同边界的城市接待量与全国出游人次直接加总 → 违反勾稽铁律，禁止。

## Deliverables

落点与父技能同构，城市层落在同一棵双子树下：

```
holiday-data-reports/
├── data_set/{年份}_{节假日}/
│   ├── holiday-data-fetch.json    # 全国行（地域粒度=全国）+ 城市行（地域粒度=城市）★ 同一 SSOT
│   └── 采集日志.csv
└── data_report/{年份}_{节假日}/
    ├── 城市消费数据报告.html
    ├── 数据真实性说明.html
    └── index.html
```

| 交付物 | 位置 | 用途 |
|---|---|---|
| **城市行**（30 字段） | `data_set/{年份}_{节假日}/holiday-data-fetch.json` | 与全国行**同一 SSOT**：`layer=L1` 且 `地域粒度`=城市/县域全称；22 字段继承 + 8 城市增量 |
| 城市现象素材 | 同上（`layer=L2`） | 城市榜单/热点/定性素材，入正文标"现象级/定性素材" |
| （勾稽基准）全国行 | 同上（`地域粒度=全国`） | 来自父技能，本技能**引用不重造** |
| `城市消费数据报告.html` | `data_report/` | 含勾稽总表与可视化 |
| `数据真实性说明.html` | `data_report/` | 逐条溯源 + 勾稽校验与覆盖率声明 |
| `index.html` | `data_report/` | 门户入口 |

> **不另建城市数据集 CSV**：城市行写入父技能 SSOT，随 F5 一并沉淀至上游；派生视图不单独交付。

## 勾稽铁律（本技能核心）

**先判可加性，再算勾稽。** 指标分两类：

| 类别 | 代表指标 | 勾稽方式 |
|---|---|---|
| **可加指标**（属地归属、无跨城重复） | 旅游总花费、商务部社零、离岛免税、酒店 RevPAR/间夜、平台 GMV | **闭合勾稽**：Σ城市 + 未披露残差 ≡ 全国，占比合计 ≤ 100% |
| **流量指标**（到访口径，跨城重复为常态） | 出游人次/接待量、跨区域人员流动量、铁/民/水客运量、地铁与景区客流 | **上限勾稽**：呈现「倍数 = Σ城市 ÷ 全国」，1.5–2.5× 为正常，占比可 > 100% |

**五铁律**
1. **同口径才可比**：两端须「指标口径类型 + 口径版本 + 统计窗口 + 假期天数」四元一致，否则标 `勾稽状态=口径差异`，禁止相加。
2. **占比规则分家族**：可加指标合计 > 100% + 容差 → R-CITY-1；流量指标倍数 > 3× → R-CITY-1。未披露残差必须显式列「其他/未披露」行（D 级、`数据性质=推算`）。
3. **缺失不臆造**：全国有数、城市无分城市披露 → 只以测算行兜底，不编造各城市值。
4. **覆盖率声明**（仅可加指标）：须给出「已披露合计 + 未披露残差 = 100%」；覆盖率 < 40% 时城市排名降级为"局部样本，非全域排名"。
5. **排名仅在同口径城市间有效**：排名表须注明口径版本与可比城市集合；流量指标排名标"到访口径/含跨城重复"。

**阻断清单**：R-CITY-1（占比超 100% / 倍数 > 3×）、R-CITY-2（口径漂移，不得入占比链）、R-CITY-3（城市行无 `关联全国指标`，条目无效）、R-CITY-4（用虚构值填满残差）。完整定义与枚举见 `references/caliber-dictionary-city.md` 第〇节。

## 五阶段增量（【城市】标记步骤）

沿用父技能五阶段，以下为城市增量：

- **阶段一**：读全国行（`地域粒度=全国`）锁定勾稽基准 → 依 `holiday-config-city.md` 定城市集合（约 40 城基线）与七大区域分组 → 城市组合词并入 fetch 的 F1 检索矩阵，**由 fetch 执行采集**（城市层无上游基线 → 联网 5 轮）→ 平台榜记 C 级并标"平台自身口径，非全市场"。
- **阶段二**：城市行写入 SSOT（`layer=L1` + `地域粒度`=城市名，后 8 字段见 `caliber-dictionary-city.md` 第一节）→ 每条须有 `关联全国指标`（R-CITY-3）→ 判可加性后算占比/倍数 → 建「其他/未披露」测算行 → R-CITY-1~4 全过。
- **阶段三**：真实性说明增加「勾稽校验与覆盖率声明」节；溯源表按「全国指标 → 城市行」分组，附 `城市|区域|占比|勾稽状态`。
- **阶段四**：套 `assets/report-template-city.html`，**必含**勾稽总表 + 排名图 C1 + 区域图 C2 + 对比图 C3，分区域各栏 ≥1 图；图表取自 `assets/chart-kit.html`。
- **阶段五**：城市交付物齐备 + **三方勾稽校验**（SSOT 城市行 ↔ SSOT 全国行 ↔ 真实性说明）。

## Resources

### 本技能
- `references/caliber-dictionary-city.md` -- 城市增量口径 + 勾稽关系（第〇节：可加性分类、五铁律、R-CITY-1~4、30 字段）
- `references/holiday-config-city.md` -- 城市级数据源矩阵与检索词、覆盖率预期
- `references/templates-city.md` -- 城市台账/勾稽校验表/报告/真实性说明/可视化组件模板
- `references/style-guide-viz.md` -- 图表选型、配色、口径标注、SVG 组件约定
- `references/development-prompt-city.md` -- 城市版五阶段操作细则
- `assets/report-template-city.html` / `assets/landing-page-template-city.html` / `assets/chart-kit.html` -- 模板与图表片段

### 父技能（引用，不复制）
- `holiday-data-report` 的 `references/caliber-dictionary.md`、`holiday-config.md`、`style-guide.md`、`templates.md`、`development-prompt.md`

## Usage Notes

- **前置条件**：地域=城市时，先确认全国 SSOT 已存在（本次已生成或用户已提供）。缺失则先走父技能全国流程，本技能不重造总量。
- **采集由 fetch 承担**：城市组合检索词并入 fetch 的 F1 检索矩阵，本技能不自行检索；城市层无上游基线可复用 → 联网 5 轮。
- **零虚构**：城市值缺失只做测算占位行，禁止编造；残差行一律 `数据性质=推算` + D 级。
- **平台榜纪律**：携程/同程/美团城市榜一律 C 级 + 备注"平台自身口径，非全市场"，不得替代官方城市接待量。
- **预览**：交付后打开城市报告、真实性说明与 `index.html` 供读者预览。
