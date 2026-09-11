---
name: consumption-data-report
description: "Generates a complete holiday consumption data report deliverable set for any year and any Chinese holiday (Spring Festival, Dragon Boat, May Day, Summer Vacation, Mid-Autumn, National Day): a structured dataset (CSV), an Economist/FT newspaper-style single-file HTML report, a data provenance document, and a landing page that serves as a portal linking to all three. Uses a five-stage pipeline: data collection, quality assessment, data output, report generation, and delivery. Use when the user requests consumption data reports for any Chinese holiday period."
agent_created: true
---

# Consumption Data Report (节假日消费数据报告)

## Overview

This skill produces a **four-deliverable package** (四件套) for holiday consumption data reports,
with data verification built in *before* the report is written -- never after:

1. **消费数据集** -- structured dataset file (CSV) where every data point carries its source metadata
2. **消费数据报告** -- single-file HTML report in Economist/FT newspaper style
3. **数据真实性说明** -- single-file HTML provenance document, tracing every figure to its source with clickable URLs
4. **首页 (index.html)** -- single-file HTML landing page that serves as a portal, featuring report headline, provenance introduction, and CSV preview with links to all three deliverables; designed for EdgeOne deployment

Core methodology: **data first, report last** (先建数据集后出报告). Any data problem is caught
before the report exists, so the report never needs rework for sourcing reasons.

## When to Use

Trigger when the user asks to produce a holiday consumption / travel spending data report
for **any year** and **any Chinese holiday**, including:

| 节假日 | 典型时间范围 | 假期天数 |
| --- | --- | --- |
| 春节假期 | 除夕至初七 | 约 8 天 |
| 端午假期 | 端午前后 | 3 天 |
| 五一假期 | 5 月 1 日前后 | 5 天 |
| 暑假 | 7-8 月 | 约 62 天 |
| 中秋假期 | 中秋前后 | 3 天 |
| 十一假期 | 10 月 1-7 日 | 7 天 |

Also use when the user asks to *re-run* the pipeline for a new year/holiday combination.
节假日配置详见 `references/holiday-config.md`.

## Deliverables (四件套)

| # | 交付物 | 格式 | 用途 |
| --- | --- | --- | --- |
| 1 | 数据集（如 `2026年暑假消费数据集.csv`） | CSV | 数据台账,每条数据含来源元数据 |
| 2 | 数据报告（`消费数据报告.html`） | 单文件 HTML | 面向读者阅读,经济学人/FT 风格 |
| 3 | 数据真实性说明（`数据真实性说明.html`） | 单文件 HTML | 逐条溯源与质量声明 |
| 4 | 首页（`index.html`） | 单文件 HTML | 门户入口,收录三件套精华,可发布到 EdgeOne |

## Analysis Framework (分析主题框架)

**方法论原则：提示词固化的是分析框架,不是分析结论。**

### 固定分析维度 (8 项,采集前确定,构成报告栏目骨架)

1. **游客画像**：出游人次、客群结构、出行方式与时长变化
2. **景区数据**：门票政策、限流预约、热门景区接待量
3. **目的地**：国内热门城市与县域、出境目的地、入境客源国
4. **酒店**：入住率、RevPAR、各档次价格表现
5. **旅行社**：订单量、产品结构（跟团/小团/定制）
6. **旅游行业平台**：携程、去哪儿、同程、飞猪、途牛等（以数据可获取性为准,不强制全覆盖）
7. **交通出行**：铁路、民航、公路、水路的客运量与同比
8. **政策与宏观**：促消费政策、免签政策、社零与出行宏观数据

### 探索性主题 (1 项,具体项目由数据决定)

**热门新消费**：不预设具体业态清单。入选标准（须同时满足）：
- 出现可量化的显著增长（A/B 级来源：同比增速、人次、交易额等）
- 至少 2 个独立来源交叉印证
- 具备消费带动效应或社会关注度
- 数据不足的候选项目不得强行写入报告
- 阶段二基于数据集圈定入选项目清单,阶段四报告栏目依此搭建

## Five-Stage Workflow (五阶段工作流程)

### 阶段一：数据采集 (Data Collection)

1. 确定目标参数：**【目标年度】**与**【节假日】**,查阅 `references/holiday-config.md` 获取该节假日的日期范围、检索关键词矩阵、主要数据源优先级。
2. 围绕 9 大主题建立检索关键词矩阵,逐主题联网检索（不少于 8 轮）。
3. 探索性主题采用**开放式检索**：检索词用"[节假日]新消费热点/[节假日]消费新业态/[节假日]新兴消费"等宽泛表述,**禁止预置**具体业态关键词——业态必须在检索结果中涌现,而非在检索词中预设。
4. 每轮检索记录《采集日志》,字段：
   `检索关键词 | 检索时间 | 标题 | 来源机构 | 报告/资料名 | 发布时间 | URL | 内容摘要`
5. 来源优先级：A 级（政府公告/官方统计/权威通讯社通稿）> B 级（权威媒体转引机构数据）> C 级（企业自我披露/券商研报）> D 级（弱溯源）。
6. **旧闻剔除**：核对发布时间,凡非目标年度/节假日口径的数据一律不入库。
7. **口径冲突暂存**：同一指标出现多个口径时全部记录,不急于取舍。
8. 阶段产出：《数据采集日志》。

详细规则见 `references/development-prompt.md` 阶段一。

### 阶段二：数据整理与质量评估 (Data Cleaning & QA)

1. 数据质量快检：去重、缺失率、类型规范、数值单位统一。
2. **逐条分级**：为每个数据点评估并标注可信度等级 A/B/C/D。
3. 口径冲突处理：官方口径优先；无法判定主次时**并列说明**。
4. 弱溯源处理：找不到直接出处的数据点降级为 D 级,标注"弱溯源",附最接近的佐证口径。
5. 推算指标单列：测算/推算值单独标记"测算",与实测数据分栏,不得混同。
6. 探索性主题圈定：基于已分级数据集,按入选标准筛选业态,确定"热门新消费"项目清单。
7. 阶段产出：《数据集》(CSV),字段：
   `主题 | 数据点 | 数值 | 单位 | 来源机构 | 报告/资料名 | 发布时间 | 可信度等级 | URL | 备注`

### 阶段三：数据输出 (Data Output)

基于数据集生成《数据真实性说明》,包含五部件：
1. **引言**：采集与核实方法、数据局限（时点口径差异、转述性概括、推算标注）
2. **可信度分级标准**：A/B/C/D 定义与图例
3. **台账差异与修正声明**：与原稿/不同口径的差异逐条列出并更正
4. **逐条溯源表**：数据点 | 来源机构 | 发布时间 | 等级 | 可点击 URL
5. **全量来源机构清单**

无公开 URL 的（券商研报付费资料等）如实标注,并给出替代验证路径。

### 阶段四：报告生成 (Report Generation)

1. **仅从《数据集》取数**：报告中每个数字必须在数据集中有对应条目。
2. 依据数据集梳理叙事主线（建议判断方向：结构叙事取代规模叙事）。
3. 排版与风格：严格按 `references/style-guide.md` 执行;可直接套用 `assets/report-template.html` 骨架。
4. 技术约束：全部 CSS/JS 内联、无外链、无 emoji、简体中文、响应式。
5. 仅推算指标标注"测算";页脚注明来源机构与报告年份。
6. 阶段产出：`消费数据报告.html`。

### 阶段五：成果交付 (Delivery)

1. 四件套齐备：数据集 + 数据报告 + 数据真实性说明 + **首页**。
2. **首页生成**：
   - 套用 `assets/landing-page-template.html` 骨架
   - 卡片一：摘录数据报告的**头条部分**（大标题 + standfirst + 首段正文）,链接指向 `消费数据报告.html`
   - 卡片二：摘录数据真实性说明的**引言部分**（方法说明 + 数据局限声明）,链接指向 `数据真实性说明.html`
   - 卡片三：数据集 CSV **前 5 行**以表格形式预览,链接指向 CSV 文件下载
   - 首页文件名固定为 `index.html`（EdgeOne 默认入口）
   - 技术约束同报告：全部 CSS/JS 内联、无外链、无 emoji、简体中文、响应式
3. **一致性校验**：报告所有数字 <-> 数据集 <-> 真实性说明一一对应,首页链接全部可达,缺失即返工。
4. 目录结构：
   ```
   报告目录/
   ├── index.html                  # 首页（EdgeOne 默认入口）
   ├── 消费数据报告.html             # 完整报告
   ├── 数据真实性说明.html            # 真实性说明
   ├── [年度][节假日]消费数据集.csv    # 数据集
   └── overview.md                  # 交付说明
   ```
5. 交付说明：各文件用途、使用方法、数据等级分布概览。
6. **EdgeOne 发布说明**（如用户需要）：首页 index.html 为 EdgeOne 部署入口,部署后读者通过首页访问三件套全部资源。

## Format & Delivery Rules (格式分工,硬性)

- **面向读者阅读的成果**（首页、数据报告、数据真实性说明） -> **单文件 HTML**
- **面向报告开发者的文档**（开发提示词、说明文档） -> **Markdown (.md),不产出 HTML 版**
- 数据集 -> **CSV**（便于程序化消费与下载）
- 本技能所有阶段性规则文档均为 md,仅供执行者（AI/开发者）参考,不交付给读者。

## Quality Red Lines (质量红线,不可逾越)

1. **不编造数据**：无来源的数据一律不得进入报告
2. **每条数据可溯源**：来源于互联网公开数据的必须附可点击 URL
3. **推算指标必须标注"测算"**
4. **口径冲突必须并列说明**,不得擅自合并或二选一
5. **交付前必须完成"数据 <-> 来源"全量对照校验**
6. **框架与结论分离**：固定维度可预置;探索性主题的具体项目必须由数据决定,采集前不得固化业态清单

## Resources

- `references/development-prompt.md` -- 完整开发提示词（v3.0）：五阶段操作细则、角色定位、质量红线,可按年度/节假日替换参数后作为独立提示词提交
- `references/holiday-config.md` -- 节假日配置表：六类节假日的日期范围、检索关键词矩阵、主要数据源、报告特点
- `references/templates.md` -- 采集日志、数据集、真实性说明、首页的结构模板与字段规范
- `references/style-guide.md` -- 经济学人/FT 排版规范：CSS 变量、字体、颜色、组件清单（含首页组件）
- `assets/report-template.html` -- 经济学人风格单文件 HTML 报告骨架模板（含全部内联 CSS）,复制后填充内容即可
- `assets/landing-page-template.html` -- 经济学人风格单文件 HTML 首页骨架模板,含三卡片入口结构,复制后填充内容即可
- `assets/icon.jpg` -- 技能图标（1024x1024 JPG,体积<5MB）,简洁大气：折叠报刊文档+递增柱形图+圆形核验徽章
- `assets/icon.svg` -- 上述图标的 256x256 SVG 矢量源文件,便于后续修改

## Usage Notes

- 年度可变：将提示词/模板中的【目标年度】替换为目标年份即可复用。
- 节假日可变：将【节假日】替换为目标节假日即可复用。查阅 `references/holiday-config.md` 获取该节假日的检索关键词与数据源。
- 若用户只要四件套中的某几件,可按需裁剪,但报告取数仍须来自数据集。
- 交付后用 present_files 打开 HTML 文件（首页、报告与真实性说明）供读者预览;数据集与说明文档以卡片列出。
- 若用户需要发布到 EdgeOne：将整个报告目录作为静态站点部署,首页 `index.html` 自动作为默认入口。
