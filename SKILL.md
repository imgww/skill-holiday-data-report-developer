---
name: holiday-data-report
description: "Generates holiday consumption data report packages for any year and any Chinese holiday (Spring Festival, Dragon Boat, May Day, Summer Vacation, Mid-Autumn, National Day), at either the NATIONAL (全国) or CITY (城市) dimension. National mode writes into a fixed `holiday-data-reports/` tree: the data side holds `data_set/{year}_{holiday}/` with `holiday-data-fetch.json` as SSOT plus `采集日志.csv` and on-demand `snapshots/`; the report side holds `data_report/{year}_{holiday}/` with `消费数据报告.html`, `数据真实性说明.html` and `index.html`. Derived CSV and material-library views are not delivered separately — they are computed from the SSOT on demand. It uses a five-stage pipeline with a 22-field caliber dictionary and a continuity/forecast framework. City mode adds a 30-field city layer that reconciles (勾稽) to the national SSOT dataset, with inline-SVG visualizations. Before any collection, the skill resolves three parameters — [年份] (defaults to current year), [节日] (defaults to the festival of the current date), [地域] (defaults to 全国; a named city triggers city mode) — and proactively prompts the user when any cannot be derived. Collection is delegated to the holiday-data-fetch skill, which is **bundled inside this package** at `bundled/holiday-data-fetch/` so a standalone report install still runs. Stage one is a four-step D1-D4 pipeline: D1 probes **AtomGit** for half-match directories (year series + holiday series) and sparse-checks out only `holiday-data-fetch.json` + `采集日志.csv` (never `snapshots/`); D2 ensures fetch is installed (running a terminology self-check after any fresh install); D3 falls back to the bundled copy; D4 dispatches rounds — a full match means 3 incremental rounds with the baseline as history input, no full match means 5 web-search rounds. A hit never skips fetch, it only reduces rounds. Gated by the three contracts; this skill owns parameter resolution, analysis, and delivery. Use when the user requests a Chinese-holiday consumption/spending data report, nationally or for a specific city."
version: 4.1.0
author: workbuddy
agent_created: true
---

# Consumption Data Report (节假日消费数据报告)

## Overview

Produces a **holiday consumption data report package** for Chinese holiday consumption data (verification precedes the report):

**数据侧**（`data_set/{年份}_{节假日}/`）
1. `holiday-data-fetch.json` -- **SSOT**，schema/meta/items，`layer` ∈ L1/L2 统一。
2. `采集日志.csv` -- 阶段一检索与采集记录。
3. `snapshots/` -- 原文快照，按需单点补拉，供逐条溯源。

**报告侧**（`data_report/{年份}_{节假日}/`）
4. `消费数据报告.html` -- 单文件 HTML，Economist/FT 风格。
5. `数据真实性说明.html` -- 单文件 HTML，逐条溯源与质量声明。
6. `index.html` -- 门户入口，可发布到静态托管。

> **不再单独交付** `消费数据集.csv` 与 `现象素材库.json`：二者为 SSOT 派生视图，需要时按 `references/data-architecture.md` 从 SSOT 现算。

Core principle: **data first, report last** (先建数据集后出报告).

> 版本沿革与变更说明见 `CHANGELOG.md`；本文件只载现行规则，不含历史叙事。

## Parameter Resolution (参数确认 · 必先于一切采集)

动手采集/写报告**之前**必须确定 **[年份][节日][地域]**，驱动后续全部检索、口径与交付形态。

1. **从用户对话提取**三项；用户明确给出则直接使用（如"2026 五一 成都消费报告"）。
2. **默认值**（用户未提供时）：
   - **[年份]** → 当前系统日期年份
   - **[地域]** → 默认 `全国`；给出城市名则进入城市模式
   - **[节日]** → 用户明确则采用；否则取当前日期所在节假日（依据 `holiday-config.md` 日期范围）
3. **缺失处理（关键）**：[节日] 无法获取且当前日期不在任何节假日窗口 → **必须主动提示用户**，不得臆造。用 `AskUserQuestion` 或自然语言确认三项，并给出建议默认值；仅当三项全部明确才进入阶段一。
4. **回显确认**：进入采集前一句话回显解析结果（如"将为您生成 **[2026][十一][全国]** 消费数据报告"），给用户一次纠正机会。

### 地域路由
- `全国` → 全国五阶段 → `data_report/{年份}_{节假日}/` 三份 HTML。
- 具体城市 → 先确保全国 SSOT 存在，再叠加 30 字段城市层 → 城市模式交付（引用全国数据集，不重造）。详见「城市维度扩展」与 `references/*-city.md`。
- 全国 + 城市 → 先全国后城市，共用同一 SSOT。

## When to Use

Trigger when the user asks for a holiday consumption / travel spending data report for **any year** and **any Chinese holiday**, including 春节 / 端午 / 五一 / 暑期 / 中秋 / 十一。也用于按新年/新节假日**重跑**管线。节假日日期范围与天数详见 `references/holiday-config.md`。

### 不适用场景
非中国节假日、无公开来源、需秒级实时、非消费主题、需原创调研/抽样、跨境全球对比——即"数据可溯源 + 中国节假日 + 消费主题 + 周期性产出"四要素任一不满足即不适用；明确告知用户并建议改用其他方案。

## Deliverables (按地域分两套)

交付根目录固定为 **`holiday-data-reports/`**，数据与报告分置两棵子树：

```
holiday-data-reports/
├── data_set/{年份}_{节假日}/
│   ├── holiday-data-fetch.json     # SSOT（fetch 产出，L1+L2 统一）
│   ├── 采集日志.csv                 # 阶段一检索记录（fetch 产出）
│   └── snapshots/                  # 原文快照（fetch 产出，按需单点补拉）
└── data_report/{年份}_{节假日}/
    ├── index.html                  # 门户入口
    ├── 消费数据报告.html            # 经济学人/FT 风格
    └── 数据真实性说明.html          # 逐条溯源与质量声明
```

### 全国模式

| 交付物 | 位置 | 用途 |
| --- | --- | --- |
| `holiday-data-fetch.json` | `data_set/` | 唯一事实来源（SSOT） |
| `采集日志.csv` | `data_set/` | 采集过程留痕 |
| `snapshots/` | `data_set/` | 原文快照，溯源证据 |
| `消费数据报告.html` | `data_report/` | 经济学人/FT 风格 |
| `数据真实性说明.html` | `data_report/` | 逐条溯源与质量声明 |
| `index.html` | `data_report/` | 门户入口，可发布到静态托管 |

> **双轨原则**：L1/L2 分栏呈现、不混同；L2 入正文须标"现象级/定性素材"。详见 `references/data-architecture.md`。

> **可选交付物 · 跨年纵向专题报告**：从 SSOT 聚合产出（框架见 `templates.md` 第 7 节），历史年份数据从 `data_set/{年份}_{节假日}/` 按 `historical-data-source.md` 适配。

### 城市模式

在全国模式交付基础上，叠加 30 字段城市层：城市数据集（30 字段，落在 `data_set/`）、城市消费数据报告（含勾稽总表与可视化）、数据真实性说明（含勾稽校验与覆盖率声明）、首页 `index.html`。
**（勾稽基准）全国数据集**来自全国模式，城市层**引用不重造**。

## Analysis Framework

**方法论原则：固化的是分析框架，不是分析结论。** 口径裁决 / 叙事批判 / 节日属性语义完整方法见 `references/analysis-methodology.md`（六节骨架）；本节只列栏目骨架。

### 固定分析维度（8 项 · 必采骨架）
缺失须标"本期暂无公开数据"，不得留白或编凑。

1. **游客画像** — 出游人次、客群结构、出行方式与时长变化
2. **景区数据** — 门票政策、限流预约、接待量；必采子项：二消结构拆解、承载率与限流方式、文博/演艺细分；客流增速 vs 二消增速背离须做悖论分析
3. **目的地** — 国内热门城市与县域、出境目的地、入境客源国（边检口径）
4. **酒店** — RevPAR/ADR/OCC 三件套（必填）；必采子项：渠道结构（OTA/直营/会员 + 佣金率侵蚀）
5. **旅行社** — 订单量、产品结构（跟团/小团/定制）
6. **旅游行业平台** — 携程、去哪儿、同程、飞猪、途牛等；C 级平台增速须标"该平台自身口径,非全市场"
7. **交通出行** — 铁路、民航、公路、水路客运量与同比；必采子项：公路"跨区域人员流动量"与公共客运量分列、城市交通、购票提前期
8. **政策与宏观** — 促消费政策、免签政策、社零与出行宏观；旅游总花费与商务部社零分列不可相加

### 探索性主题（1 项 · 由数据决定）
**热门新消费**：不预设业态清单。入选标准（**同时满足**，可机器校验）：① 量化显著性（同比 ≥30% 或绝对规模可观）；② ≥2 个独立机构来源交叉印证（数据集同主题项目互链；仅 1 源降级"待核实"）；③ 平台 C 级约束；④ 阶段二在 SSOT **显式圈定**入选行（未圈定者阶段四不得凭印象自建章节）；⑤ 具备消费带动效应或社会关注度。

## Continuity Methodology

> 机制底座：所有预测须进**预测台账**（`数据性质=预计` + `缺口标记=预判待回填` + `预测ID`），下一报告期回填核验（详见 `caliber-dictionary.md` 第六节与 `templates.md` 第 5/6 节）。

### 延续性四问（每期报告必答）

1. **去年同期回顾（YoY）** — 核心指标先 per-day 或可比天数折算（春节 7/8/8/9 天、十一 8/7/8/7 天漂移）；判读"增量来自天数/口径"还是"真实增长"。
2. **本年上期回顾** — 本节假日 vs 本年已发生节假日，观察年内消费节奏、增速收敛斜率。
3. **上一周期预测复盘** — 逐条「预测值→实测值→偏差%→归因→判语」；偏差 > ±10% 标**失准**并分三类归因（口径效应/外生变量/方法偏差），不美化、不选择性引用。
4. **下一节假日前瞻 + 中长期趋势** — 给下一节假日预测（中心值+区间+置信度+口径效应提示，**不得当实测**）；并给 3–12 月结构性判断，附**拐点判据**与置信度分级。

### 纵向数据来源

- **去年同期 / 本年上期**：从 `data_set/{年份}_{节假日}/` 读往年 SSOT，经 `audit_caliber.py` 校验后取可比行（须 per-day 折算）。
- **历史纵向基线**：D1 稀疏检出至 `holiday-data-reports/data_set/`（上游 `https://atomgit.com/g_ww/holiday_data`；只取 `holiday-data-fetch.json` + `采集日志.csv`）；阶段二按 `references/historical-data-source.md` 做 **17→22 适配 + canon 规范化 + 枚举归一**。离线/拉取失败时降级为首期基线标注。
- **MCP 交叉验证**：`holiday-data-mcp`（`compare_across_years`/`get_data_point_detail`）作为取数交叉验证通道，不替代 fetch/基线（详见 `references/mcp-retrieval-layer.md`）。
- **跨年可比元组铁律**：`(节假日, canon(数据点), 口径类型, 地域scope)` 四元一致且覆盖 ≥2 年才可比；否则标「单年/不可比」。首期无历史时优雅降级，不编造。

---

## City Dimension Extension (地域=城市时启用)

> 当参数确认解析出**具体城市**时，在全国 SSOT 之上叠加城市层。城市数据是全国数据集的**空间剖面**，每条必须勾稽到某全国指标键。细则在 `references/*-city.md` 与 `assets/*-city.html` / `assets/chart-kit.html`。

**核心定位三句话**：① 继承不重造（全国总量、口径字典、五阶段方法论继承；城市只增量定义字段、数据源、勾稽规则）；② 勾稽不脱钩（每条 `关联全国指标` 指向全国 SSOT 某行；可加指标用闭合勾稽（占比 ≤100% + 未披露残差），流量指标用上限勾稽（倍数 1.5–2.5× 正常，> 3× 触发阻断））；③ 图文要可读（大量内联 SVG 可视化，图表与数据表双轨）。

**五阶段增量**（【城市】标记步骤）：阶段一 读全国+城市矩阵；阶段二 强制 30 字段 + `关联全国指标` + 勾稽 R-CITY-1~4；阶段三 真实性说明加「勾稽校验与覆盖率声明」；阶段四 套用 `report-template-city.html`，必含勾稽总表 + 排名图 + 区域图 + 对比图；阶段五 城市交付物齐备 + **三方勾稽校验**（城市 ↔ 全国 SSOT ↔ 真实性说明）。**勾稽五铁律**详见 `references/caliber-dictionary-city.md`。

---

## Five-Stage Workflow

### 阶段一：数据采集（D1 下载 → D2/D3 备妥 fetch → D4 分派轮数）

> 采集为 **D1–D4 四步流水线**。
> **命中 AtomGit 也调用 fetch**，只是把联网轮数从 **5 轮降为 3 轮增量**——不存在"命中即跳过采集"的分支。
> fetch **随包整合**于 `bundled/holiday-data-fetch/`（单点安装 report 即可运行）。

#### D1 · 半命中下载（不依赖 fetch，先于一切执行）

1. 解析 [年份] Y、[节日] F、[地域]。

2. 构造**两个半命中系列**并取并集（交叉格只计一次）：
   - **纵向系列** `{y}_{F}`，y ∈ [Y−4, Y]（回溯**不超过 5 年**）
   - **横向系列** `{Y}_{f}`，f ∈ 六节日
   - `{Y}_{F}` 同时属于两系列 → 去重后只下载一次

3. **存在性探针**（逐目录，不下载 blob）：
   `git ls-tree --name-only "HEAD:{目录}"` 返回含 `holiday-data-fetch.json` = 该格存在。

4. **稀疏检出**至用户本地工作空间 `holiday-data-reports/data_set/{年份}_{节假日}/`，
   **只拉两个文件**：`holiday-data-fetch.json` + `采集日志.csv`；**禁拉 `snapshots/`**（每条记录自带 `snapshot` 相对路径，按需单点补拉）。

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://atomgit.com/g_ww/holiday_data holiday-data-reports/data_set
cd holiday-data-reports/data_set

# 逐格判定存在性（不下载 blob）
git ls-tree --name-only "HEAD:{Y}_{F}"

# 只拉两个文件（路径必须带前导斜杠）
git sparse-checkout init --no-cone
git sparse-checkout set --no-cone \
  "/{Y}_{F}/holiday-data-fetch.json"   "/{Y}_{F}/采集日志.csv" \
  "/{Y-1}_{F}/holiday-data-fetch.json" "/{Y-1}_{F}/采集日志.csv" \
  "/{Y}_{f1}/holiday-data-fetch.json"  "/{Y}_{f1}/采集日志.csv"
```

   > 坑 1：`--sparse` **必须在 clone 时声明**，事后补加会报 `unable to read sha1 file`。
   > 坑 2：必须 `init --no-cone` 且路径带**前导斜杠**，否则 cone 模式把 `snapshots/` 一起拉下。
   > 坑 3：**只用 `set` 全量重列，禁用 `add`**——实测 `add` 在此 Git 版本下静默失效；且 `set` 是覆盖式，重列时漏项会把上次已拉文件移走。

5. **拉取后强制校验（不可省）**：逐目录断言「两文件均存在 且 L1 行数 > 0」，不满足即判该格未命中。
   > **退出码 0 不得当作成功**：目录名写错时 `sparse-checkout` 仍返回 0、工作区为空、零警告——本流程最危险的静默失败点。

**产出**：半命中数据集（可为空）+ 命中/未命中清单（须写入采集日志）。

#### D2 · 备妥 SKILL holiday-data-fetch

1. 检测本地是否已安装：存在 `~/.workbuddy/skills/holiday-data-fetch/SKILL.md` → 直接启动，跳到第 3 步。
2. 未安装 → 从 AtomGit 安装：
   `git clone --depth 1 https://atomgit.com/g_ww/holiday-data-fetch.git <skills 目录>/holiday-data-fetch`
3. **装完必跑术语自检 + 自动补丁（不可省）**：

```bash
python scripts/verify_holiday_terms.py <fetch 目录> --fix
```

   > 自检分两层：L1 文本术语、L2 枚举构造（决定目录名）。退出码 0=通过 / 1=有问题 / 2=路径非法。

#### D3 · 降级到内置 fetch

D2 安装失败（网络 / 权限 / 仓库不可达）→ 启动内置 `bundled/holiday-data-fetch/`。
内置副本与安装版同源，出厂已通过术语自检。

#### D4 · 全命中判定与轮数分派

**全命中** = `holiday-data-reports/data_set/{Y}_{F}/` 存在 **且** D1 第 5 步校验通过。

| 判定 | 喂给 fetch 的输入 | 采集动作 |
|---|---|---|
| **有全命中** | `holiday-data-reports/data_set/` 作为**历史版本** | 启动 **增量 3 轮**（F1→F2 循环 3 次）：在历史版本基础上补采本期缺口，不重采已有条目 |
| **无全命中** | 半命中集（若有）仅作参考上下文 | **联网搜索 5 轮**（F1→F2 循环 5 次） |

> **轮数定义**：轮数 = **F1（检索矩阵）→ F2（并行采集）的循环次数**，不是新增阶段编号，不与 F0–F5 混淆。

无论哪条路径，fetch 均执行完整 **F0→F1→F2→F3→F4→F5**；差异只在 F1→F2 的循环次数与是否以历史版本为输入。
F0 历史数据询问**必须执行**（有全命中时，由 D1 产出的 `holiday-data-reports/data_set/` 直接作为答案，须在报告中显式声明）。

#### 门禁验收（report 只验契约，见 `references/contracts.md`）

- [ ] 契约一：L1 22 字段齐全，口径可在 `caliber-dictionary.md` 追溯
- [ ] 契约二：L2 素材条条含 URL（唯一删除条件：无 URL 纯臆测）
- [ ] 契约三：预测台账（若有）预测 ID 唯一、数据点已 canon 规范化
- [ ] 覆盖矩阵已查（fetch `coverage-matrix.md`；缺失则先建）
- [ ] **本轮数据源已声明**：命中目录清单 + commit + `source=atomgit` / `source=web`
- [ ] **fetch 术语自检已通过**（D2 第 3 步，退出码 0）

通过 → 阶段二；不通过 → 退回 fetch 补采（F2/F3 增量）。

可选交叉验证：`holiday-data-mcp`（`compare_across_years` / `query_data_points`）作为核验通道，不替代 fetch。

### 阶段二：数据整理与质量评估

要点：① 去重/缺失/类型/单位四类快检；② **逐条分级 A/B/C/D + 强制填 22 字段口径元数据**（不可在 caliber-dictionary 追溯则退回）；③ 口径冲突：官方优先，无法判定主次并列说明；④ 弱溯源降 D；⑤ **推算/派生值强制规则**：`数据性质=推算` 或 `口径类型∈{测算,弱溯源}` 或 `数值类型≠水平值` → 强制 D 级、禁入 B 级，与实测分栏；⑥ **人均口径**：per-trip vs per-day 不得混称"人均"；⑦ **跨年/调休天数折算**：必附 per-day 等效值；⑧ 探索性主题基于已分级数据集在 SSOT **显式圈定**入选行；⑨ **纵向数据归集**：读去年同期/本年上期/上期预测台账，per-day 折算，历史补齐读 `holiday-data-reports/data_set/` 做 17→22 适配 + canon 规范化；⑩ **预测入账**：`数据性质=预计`+`缺口标记=预判待回填`+`预测ID` 单独成行。

**阶段门禁 Checklist**：① 每个数据点 A/B/C/D 已标，推算/测算/弱溯源/非水平值者**全部 D 级**（无推算值混入 B）；② 22 字段口径元数据可在 caliber-dictionary 追溯；③ 口径冲突已处理（官方优先/并列说明）；弱溯源已降 D；④ 人均口径合规；跨年天数变动已附 per-day 等效值；⑤ 探索性主题入选项目已在 SSOT 显式圈定（≥2 独立机构 URL 互链）；⑥ 纵向数据已归集；⑦ 本期预测已入账；⑧ L2 现象素材已产出（含 URL），拟升 L1 现象已在备注标记。

### 阶段三：数据输出（《数据真实性说明》）

六部件：① 引言（采集/核实方法、数据局限）；② 可信度分级标准（A/B/C/D 定义与图例）；③ 台账差异与修正声明（与原稿/不同口径的差异逐条列出并更正）；④ 逐条溯源表（数据点 | 来源机构 | 发布时间 | 等级 | 可点击 URL）；⑤ 预测复盘与回填声明（偏差 > ±10% 诚实标"失准"）；⑥ 全量来源机构清单 + **L2 现象素材清单**（声明"现象级素材,非统计口径"）。无公开 URL 的（如券商付费研报）如实标注并给替代验证路径。

**阶段门禁 Checklist**：六部件齐备；每条数据含可点击 URL 或可溯源声明；溯源表等级与数据集 A/B/C/D 一一对应；预测复盘诚实呈现（含三类归因）；L2 现象素材清单已列。

### 阶段四：报告生成

1. **仅从数据集取数**：每个数字（含纵向对比、预测点位）必须在数据集或预测台账有对应条目；本期现象/榜单/定性素材从 L2 取数，标"现象级/定性素材"。
2. **报告框架 v2（四部分）**：
   - 第一部分 · 导语与核心结论：标题 + standfirst + 首段 + 关键数字带（6 卡）
   - 第二部分 · 纵向延续与前瞻：2.1 口径裁决 → 2.2 去年同期回顾（per-day 折算） → 2.3 本年上期回顾 → 2.4 上一周期预测复盘 → 2.5 下一节假日前瞻（预测卡+置信度） → 2.6 中长期趋势预判（拐点判据+置信度分级）
   - 第三部分 · 分主题深度分析：8 固定维度 + 1 探索性（栏目依阶段二圈定清单）；本期现象/热门新消费以 L2 素材为素材，与 L1 统计叙事分栏呈现
   - 第四部分 · 口径与数据质量声明（摘要，详细见真实性说明）
3. 排版与风格：严格按 `references/style-guide.md`；可直接套用 `assets/report-template.html`。
4. 技术约束：CSS/JS 内联、无外链、无 emoji、简体中文、响应式。
5. **页面形态（硬性）**：无吸顶 `header.appbar`；明暗切换按钮置于报头右端；只保留本节假日消费数据相关内容。
6. 测算/预计标注：`数据性质=推算` 标"测算（D 级）"；`数据性质=预计` 用预测卡标置信度，不得混入实测栏。
7. 产出：`消费数据报告.html`。

**阶段门禁 Checklist**：① 报告每个数字均在数据集/预测台账有对应条目（无无源数字）；② 框架为 v2 四部分；纵向延续与前瞻六子节齐备；对比已 per-day 折算；③ 上一周期预测复盘诚实呈现（失准标出且含三类归因）；④ 下一节假日前瞻用预测卡标置信度，未当实测；⑤ 规模叙事"创新高"已按口径字典折算；人均口径合规；⑥ 探索性主题栏目依阶段二圈定清单搭建，未凭印象自建章节；⑦ 排版符合 `style-guide.md`；无吸顶导航；内容整洁。

### 阶段五：成果交付

1. **交付物齐备**：数据侧 `holiday-data-fetch.json` + `采集日志.csv` + `snapshots/`；报告侧 `消费数据报告.html` + `数据真实性说明.html` + `index.html`。
2. **首页生成**：套用 `assets/landing-page-template.html`；卡片一（报告头条）、卡片二（真实性说明引言）、卡片三（数据概览）；连续性高亮条（可选）；文件名固定 `index.html`。
3. **一致性校验**：报告 ↔ SSOT ↔ 真实性说明 三向对照，首页链接全部可达，缺失即返工。
4. **目录结构**：同「Deliverables · 交付根目录」，与历史基线库同构。
   > 资产沉淀（`holiday-data-fetch.json` 同步至 atomgit 上游）由 **fetch F5** 完成，report 不执行回推。
5. 交付说明：各文件用途、使用方法、数据等级分布概览（含 L1/L2 数量）。

**阶段门禁 Checklist**：① 交付物齐备（数据侧 3 项 + 报告侧 3 项）；② 首页三卡片链接全部可达；连续性高亮条（若有）指向正确；③ 三向对照校验通过（报告 ↔ SSOT ↔ 真实性说明）；④ 预测台账闭环：本期预测已入账，供下期回填；⑤ 分年分节目录已落盘，交付说明登记 L1/L2/快照数量；⑥ 任务未越过"不适用场景"边界。

## Format & Delivery Rules

- **面向读者阅读**（首页、数据报告、数据真实性说明）→ **单文件 HTML**
- **面向开发者文档**（开发提示词、说明文档）→ **Markdown (.md)**
- **数据集** → **`holiday-data-fetch.json`（SSOT）**，CSV / 素材库等派生视图**不单独交付**，需要时从 SSOT 现算
- 所有阶段性规则文档均为 md，仅供执行者参考，不交付给读者。

## Anti-Patterns · 反模式索引

完整 14 条反模式（含后果与修正步骤）见 `references/anti-patterns.md`。**最关键 5 条**：① 编造数据 → D 级弱溯源或剔除；② 推算当实测 → 测算标记并分栏；③ 口径冲突擅自二选一 → 官方优先/无法判定并列说明；④ 跳过全量对照校验 → 强制三向对照；⑤ 预测无台账 → 凡预测必入账，偏差 > ±10% 标"失准"并三类归因。

## FAQ · 常见问题索引

12 条 FAQ（含单一弱来源 / 假期跨年 / 口径冲突 / 探索性主题 / 预测复盘 / 历史基线 / 双轨架构等）见 `references/faq.md`。

## Resources

### 本包说明
- `CHANGELOG.md` -- **版本沿革与变更说明**：版本号双轨映射、各版本变更、已知缺口。规则正文不含历史叙事，查阅"何时改的/为何改"看这里

### 脚本与随包依赖
- `scripts/verify_holiday_terms.py` -- **术语自检 + 自动补丁**：D2 安装 fetch 后**必跑**。用法 `python scripts/verify_holiday_terms.py <fetch 目录> --fix`（`--json` 机器可读）；退出码 0=通过 / 1=有问题 / 2=路径非法。保护词「暑运」不替换
- `bundled/holiday-data-fetch/` -- **随包整合的采集技能**（12 文件）：D2 未安装时的安装来源（atomgit `g_ww/holiday-data-fetch`），D3 降级时的内置兜底

### 三契约与分析内核
- `references/contracts.md` -- **三契约 v1.0**：L1 CSV / L2 素材库 / 纵向台账 schema + 验收标准 + 分工红线；report 只验契约不验过程
- `references/analysis-methodology.md` -- **分析内核 v1.0**：口径地图 / 叙事批判 / 报告层三变量 / 节日属性语义 / 三层操作 / 分析输出模板 六节骨架
- `references/faq.md` -- **FAQ v1.0**：12 条常见问答（单一弱来源 / 假期跨年 / 口径冲突 / 探索性主题 / 预测复盘 / 历史基线 / 双轨架构等）
- `references/anti-patterns.md` -- **反模式 v1.0**：14 条不可逾越反模式

### 配置 / 口径 / 数据架构
- `references/caliber-dictionary.md` -- **口径字典 v2.2（强制）**：22 字段 schema 权威（契约一）、统一主题字典(9类)、指标口径字典、口径类型取值表、预测台账与缺口标记
- `references/holiday-config.md` -- **节假日配置 v2.0**：属性卡 / 口径地图 / 锚点日历三张结构化配置 + 全源 A-J 矩阵 + R10 门禁 + merge_mode 结构字段
- `references/historical-data-source.md` -- 历史纵向基线 v1.2：atomgit 仓库唯一权威源、17→22 适配器、canon 规范化、R13–R15 质量规则
- `references/data-architecture.md` -- 数据架构 v2.0：L1/L2 双轨统一 JSON 模型、分年分节持久化、现象→指标升级通道
- `references/mcp-retrieval-layer.md` -- MCP 实时检索层 v1.0：6 工具与阶段映射、调用纪律、离线降级

### 模板与排版
- `references/templates.md` -- 采集日志、数据集 22 字段 schema、真实性说明、首页结构、预测台账模板、纵向六子节模板、跨年专题模板
- `references/style-guide.md` -- 经济学人/FT 排版规范（CSS 变量、字体、组件清单）
- `references/development-prompt.md` -- 完整开发提示词存档：五阶段操作细则，可按年度/节假日替换参数后独立提交（采集细则已由 fetch 承接）
- `assets/report-template.html` / `assets/landing-page-template.html` / `assets/verification-template.html` -- 报告/首页/真实性说明 HTML 骨架
- `assets/icon.jpg` / `assets/icon.svg` -- 技能图标

### 城市维度增量（地域=城市时引用）
- `references/caliber-dictionary-city.md` / `references/templates-city.md` / `references/holiday-config-city.md` / `references/style-guide-viz.md` / `references/development-prompt-city.md`
- `assets/report-template-city.html` / `assets/landing-page-template-city.html` / `assets/chart-kit.html`

## Usage Notes

- **参数确认优先**：运行前先按「Parameter Resolution」解析 [年份][节日][地域]；任一无法默认（尤其节日）则主动提示用户，绝不臆造。
- **D1–D4 采集流水线**（阶段一）：**D1** 半命中下载至用户本地工作空间 `holiday-data-reports/data_set/`（只取 `holiday-data-fetch.json` + `采集日志.csv`，禁拉 `snapshots/`）→ **D2** 备妥 fetch（本地已装则启动；否则从 atomgit 安装，**装完必跑术语自检 `--fix`**）→ **D3** 安装失败则降级内置 `bundled/holiday-data-fetch/` → **D4** 全命中判定：**有全命中 → 增量 3 轮（以该目录为历史版本输入）；无全命中 → 联网 5 轮**。
  > **命中也调 fetch，只降轮数、不跳采集**。
- **年度可变 / 节假日可变**：将【目标年度】【节假日】替换即可复用；查阅 `holiday-config.md` 获取该节假日的属性卡/口径地图/锚点日历。
- **城市模式须先有全国 SSOT**：地域为城市时，确保本次已生成或用户已提供对应全国数据集。
- **按需裁剪**：用户只要交付物中的某几件时可裁剪（如只要报告 HTML），但报告取数仍须来自 `holiday-data-fetch.json`。
- **预览**：交付后用 `present_files` 打开 HTML 文件（首页、报告与真实性说明）供读者预览；数据集与说明文档以卡片列出。
- **静态托管**：若需发布到静态托管平台，将整个报告目录作为静态站点部署，首页 `index.html` 自动作为默认入口。