# CHANGELOG · holiday-data-report

> 本文件记录**版本沿革与变更说明**，供人阅读与交接。
> `SKILL.md` 只承载**现行规则**，不含历史叙事；查阅"某个规则什么时候改的、为什么改"请看这里。

---

## 一、文档定位

| 文件 | 职责 | 是否含历史 |
|---|---|---|
| `SKILL.md` | **现行规则**：参数解析、D1–D4 采集流水线、五阶段工作流、门禁、资源索引 | ❌ 不含 |
| `logs/CHANGELOG.md`（本文件） | **版本沿革**：各版本变更、已知缺口 | ✅ |
| `references/development-prompt.md` | v1.3.6 五阶段操作细则存档（采集细则已由 fetch 承接） | 历史存档 |

**铁律**：新增能力时只改 `SKILL.md` 的规则正文，不在其中写"本次新增了 X"；变更说明一律写进本文件。
理由：历史叙事会随版本堆积，最终让规则正文无法辨认哪条是现行要求（1.4.1 之前的 SKILL.md 已出现此问题）。

---

## 二、版本号规则

统一使用**三位** `x.y.z`（如 `1.5.0`）；历史遗留的两位版本号 `X.Y` 一律转换为 `1.X.Y`（如 `3.6` → `1.3.6`）。
版本号只此一套，`SKILL.md` frontmatter 即权威值。

---

## 三、版本沿革

| 版本 | commit | 日期 | 主题 | 状态 |
|---|---|---|---|---|
| 1.5.0 | `626e3c4` | 2026-09-15 | 阶段一 D1–D4 采集流水线 | **开发中（未发版）** |
| 1.4.1 | `d2ae007` | 2026-09-11（tag） | 分拆框架重构（减法） | 已发布 |
| 1.4.0 | `5c66b0b` | 2026-09-11（tag） | 模板样式变更 | 已发布 |
| 1.3.8 | `d61e8fb` | 2026-09-11（tag） | 调用节日 MCP | 已发布 |
| 1.3.7 | `9fcd08d` | 2026-09-11（tag） | 完整五阶段 | 已发布 |
| 1.0.0 | `6ccbef8` | 2026-09-11（tag） | 起点版本 | 已发布 |

> tag 日期均为仓库重建后的打标日期，不代表实际开发日期。
> 真实开发节点见 commit message 内的日期（如 `v1.3.7 20260817`、`v1.4.0 20260903`）。

---

## 四、变更详情

### 1.5.0（开发中）

未发版。以下为已提交至主干的变更，按时间倒序。

#### `ffcad18` · 2026-09-15 · fix(D1)：git 可用性三级退避

**来源于一次真实调用故障**（`@skill:holiday-data-report` 生成 2026 年暑期数据报告）。

- **现象**：执行环境 shell 的 PATH 整体损坏（`dirname` / `cd` / `head` / `ls` 均 `command not found`），
  agent 据此判定「atomgit 稀疏克隆不可执行 → 无全命中」，D4 退回 **5 轮联网**；
  用户中途取消，交付树只留下两个空目录。
- **真因**：`git` 命令找不到 ≠ git 不可用。实测 `PortableGit 2.55.0` 完好、
  `ls-remote https://atomgit.com/g_ww/holiday_data` rc=0（HEAD `3fe1d52`）；
  用 Python `subprocess` 直连 `git.exe` 绝对路径执行 D1，**7 格全部命中且校验通过**：
  `2026_暑期` L1=287 / `2025_暑期` 123 / `2024_暑期` 100 / `2023_暑期` 121 /
  `2026_春节` 241 / `2026_端午` 137 / `2026_五一` 155；未命中 `2022_暑期`、`2026_中秋`、`2026_十一`。
- **误判代价**：丢掉 287 行当期基线 + 1164 行纵向历史，且多跑 2 轮全量联网检索。

**改动**
- `SKILL.md` D1 新增**第 0 步「git 可用性前置（不可跳过）」**：① `git --version`
  ② 绝对路径直连（`%USERPROFILE%\.workbuddy\binaries\PortableGit\versions\*\cmd\git.exe` / `where git` / `which git`）
  ③ Python `subprocess` 调绝对路径绕开 shell；**三级全失败**才允许判无全命中，
  且须在采集日志与「数据真实性说明」写明 `D1 未执行：git 不可用（已尝试三级退避）`。
- `references/anti-patterns.md` 新增**第 15 条**「shell 报 `command not found` 就判 D1 不可执行」（v1.1.0 → **v1.2.0**）。
- `SKILL.md` 反模式索引同步：14 → **15 条**，最关键 5 → **6 条**（新增⑥ git 误判）。

**顺带实测**：按三级退避把 2026 暑期半命中集落盘至 `D:\AISpace\01-projects\holiday-data-reports\data_set\`
（7 目录 × 2 文件，0 快照混入，L1 均 > 0）。**下次重跑该任务即可走 D4 全命中分支（3 轮增量）**。

#### `66326e5` · 2026-09-15 · `CHANGELOG.md` 迁入 `logs/`

包根目录只留现行规则与可执行资产，历史沿革类文档统一归入 `logs/`。

- `git mv CHANGELOG.md → logs/CHANGELOG.md`（git 记为 rename，相似度 99%，历史不丢）；
- `SKILL.md` 两处引用同步为 `logs/CHANGELOG.md`（L29 顶部提示、L292 Resources 索引）；
- `logs/CHANGELOG.md` 文档定位表自引用同步；
- `scripts/verify_holiday_terms.py` 注释补路径（`HISTORY_DOCS` 按 **basename** 匹配，
  故搬迁后豁免仍生效，实测输出 `logs\CHANGELOG.md (11 处)`，逻辑无需改动）；
- CHANGELOG 内历史条目（L81/96/170/173）保留原写法——记录的是当时改了哪些文件，不改写历史。
- 校验：术语自检 report + city 双 PASS；工作区干净。

#### `9a976f5` · 2026-09-15 · 数据源描述统一为 `holiday-data-fetch.json`

变更 4 的收尾清理：全仓不再出现 `消费数据集.csv` / `现象素材库.json` 等派生视图描述，
数据源一律表述为 SSOT `holiday-data-fetch.json`。

- `SKILL.md` description 删除派生视图说明句；
- `references/templates.md` 第 2 节示例由 CSV 改为 `items[layer=L1]` JSON；
  第 5 节预测台账由「可单列 `预测台账.csv`」改为 SSOT 内 `数据性质=预计` + `缺口标记=预判待回填` 行表达；
- `data-architecture.md` / `contracts.md` / `development-prompt.md` 等同步去 CSV 世界观残留。
- 保留：`采集日志.csv`（fetch 真实产物文件名）、`csv-preview` 等 CSS 类名、
  `bundled/holiday-data-fetch/` 内历史导入器相关表述（上游副本，同步即覆盖）。
- 校验：术语自检 report + city 双 PASS；禁词（消费数据集 / 现象素材库）清零。

#### `fe77439` · 2026-09-15 · 版本号体系：原 `X.Y` 一律转为 `1.X.Y`

规则：历史遗留的两位版本号 `X.Y` 统一转换为 `1.X.Y`（如 `v3.6` → `v1.3.6`、`v4.1` → `v1.4.1`）。
**共替换 150 处 / 23 文件**；写入「二、版本号规则」。

**① 转换映射表**（13 个两位版本）

| 原 | 现 | 原 | 现 | 原 | 现 |
|---|---|---|---|---|---|
| v1.0 | v1.1.0 | v2.2 | v1.2.2 | v3.6 | v1.3.6 |
| v1.1 | v1.1.1 | v3.2 | v1.3.2 | v3.7 | v1.3.7 |
| v1.2 | v1.1.2 | v3.3 | v1.3.3 | v3.8 | v1.3.8 |
| v2.0 | v1.2.0 | v3.4 | v1.3.4 | v4.0 | v1.4.0 |
| v2.1 | v1.2.1 | v3.5 | v1.3.5 | v4.1 | v1.4.1 |
| — | — | — | — | v4.2 | v1.4.2 |

**② 覆盖范围**（report 本体 + city 随包技能）

- `SKILL.md`（Resources 各 references 版本标注 9 处）、`CHANGELOG.md`、
  `references/` 全 13 份、`assets/` 3 份模板、`bundled/holiday-data-report-city/` 6 份。
- 设计系统版本同步：报告/首页/真实性说明/城市版模板 `v4.0` → **`v1.4.0`**，首页增补 `v4.1` → **`v1.4.1`**。
- 交叉引用一并同步：city references 内引用父技能的《口径字典 v1.2.2》《节假日配置 v1.2.0》
  《开发提示词 v1.3.6》保持一致；city 与 report 两侧 `SKILL.md` 表述无漂移。

**③ 按裁决不改动的两类**

- **`bundled/holiday-data-fetch/`（约 130 处 v1.0/v1.1/v1.2）**：上游 atomgit 完整副本，
  同步时会被覆盖，且 fetch 有独立版本体系（v1.2 = fetch 技能版本），改动既无效又产生冲突 diff。
- **JSON 数据字段值**：`holiday-data-report-caliber-v2.1`、`holiday-keywords-v1.2/v1.1/v1.0`
  共 8 处保持原值——这些字符串会写入 `holiday-data-fetch.json`，
  上游 2023–2026 历史基线全是旧值，改动会导致新产出数据与历史数据对不上。

**④ 校验**：术语自检 report + city **双 PASS**；范围内两位版本号残留 0
（仅 CHANGELOG 版本号规则例句「`v3.6` → `v1.3.6`」按语义保留）；三处旧三位写法
（`v3.6.0` ×2、`4.1.0` ×1）一并统一为 `v1.3.6` / `1.4.1`。

#### `e8ad0ab` · 2026-09-15 · city references 对齐新架构（SSOT 化）

5 份 city references 由 2026-08-19 的**旧 CSV 世界观**对齐到 report 现行 SSOT 体系（承接 `94e0c19` 待办项）。

**① 城市行并入 SSOT（核心结构决策）**

- 城市数据**不再另建文件**：直接写入父技能 SSOT `holiday-data-fetch.json` 的 `items[]`，
  判据 `layer=L1` 且 `地域粒度` ≠ `全国`；全国行 `地域粒度=全国` 即为勾稽基准，同文件内闭合。
- **字段 23「城市」改为复用 SSOT 现有字段「`地域粒度`」**（全国行填 `全国`，城市行填城市/县域全称），
  不新增同义字段；城市增量仍为 8 字段，总数仍 22+8=30。
- 决策依据：`地域粒度` 本就是 SSOT L1 的既有治理字段；且历史基线上游只沉淀 `holiday-data-fetch.json`
  这一个文件——独立城市文件无法随 F5 沉淀，city 的「城市排名跨年漂移」纵向模块也就无从复用历史。
- 城市层 L2 素材（榜单/定性句/平台城市榜热点）同样入 SSOT（`layer=L2`），入正文标"现象级/定性素材"。

**② 采集交 fetch，city 不再自行检索**

- `development-prompt-city` 阶段一重写：城市组合词并入 fetch 的 **F1 检索矩阵**，由 fetch 执行；
  城市层无上游基线可复用 → **联网 5 轮**；产出为 SSOT `items[]` 新记录 + `采集日志.csv` 留痕。
- `holiday-config-city` 第四节标题改为「喂给 fetch」，门禁增「fetch 已备妥且矩阵已并入 F1」。

**③ 模板与示例 JSON 化**

- `templates-city` §1 CSV 示例 → **SSOT JSON 示例**（城市行 / 残差行 / L2 素材三段）；
  §6 预测台账 CSV → 并入 SSOT 的 `数据性质=预计` 行（`预测ID` 等元数据记 `备注`）。
- 勾稽校验提示由「扫描 CSV」改为「扫描 SSOT `layer=L1` 且 `地域粒度`≠`全国` 的记录」。

**④ 引用与版本号更正**

- 父技能版本引用：`holiday-config.md` v1.1.2 → **v1.2.0**、`development-prompt.md` v1.3.3 → **v1.3.6**、
  口径字典 v1.2.0 → **v1.2.2**（均按父技能文件实际版本核对）。
- city assets 指向：可视化规范与模板由 `report-template.html` → **`report-template-city.html`**；
  城市数示例 36 → **40**（与 `holiday-config-city.md` 一致）。
- 文档版本三位化并升级：caliber-dictionary-city / holiday-config-city / templates-city → **v1.2.0**，
  style-guide-viz / development-prompt-city → **v1.1.0**。
- 同步 city 与 report 的 `SKILL.md`：「城市层台账」→「SSOT 城市行」；
  三方勾稽统一为「SSOT 城市行 ↔ SSOT 全国行 ↔ 真实性说明」。

**⑤ 实测**：术语自检 report + city **双 PASS**；city 代码块围栏平衡（SKILL 2 / templates 6）；
「城市数据集」残留 6 处均为否定句（"不另建城市数据集 CSV/文件"）或版本沿革说明，属预期。

#### `94e0c19` · 2026-09-15 · 城市维度分拆为随包技能 `holiday-data-report-city`

**① 分拆方式**（参考 fetch bundled 模式；用户裁决：只建 bundled 副本 · 通用层引用不复制 · version 1.5.0）

- **新建** `bundled/holiday-data-report-city/`：`SKILL.md`（116 行）+ 5 份 city references + 3 份 city 模板，共 9 文件。
- **搬迁**（`git mv`，保留重命名历史）：`references/*-city.md` 5 份 → city `references/`；
  `assets/chart-kit.html` / `report-template-city.html` / `landing-page-template-city.html` → city `assets/`。
  report 根下城市残留 **0**。
- **city 通用层引用 report、不复制**：22 字段口径字典 / holiday-config / style-guide / templates 一律指向父技能；
  city `SKILL.md` 显式声明依赖与降级路径（未安装父技能时按 `caliber-dictionary-city.md` 摘要作业，
  但**勾稽基准仍需全国 SSOT**）。
- **命名统一**：city references 内旧名 `consumption-data-city-report` → `holiday-data-report-city`、
  `consumption-data-report` → `holiday-data-report`（5 文件 10 处，残留 0）。

**② report `SKILL.md` 由「城市正文」改为「城市路由」**

- 删「City Dimension Extension」整节（核心定位三句话 + 五阶段增量 + 勾稽细则），替换为**「城市模式路由」C1–C3**：
  **C1** 启动 bundled city → **C2** 前置校验全国 SSOT 存在 → **C3** 交接并回归三方勾稽。
- `frontmatter description`、地域路由、Deliverables 城市模式小节、
  Resources（原「城市维度增量」→「随包技能」）、Usage Notes 全部改为交接描述。
- **report 保留的责任**：产出全国 SSOT 作为勾稽基准 + 城市层回归后复核三方勾稽。

**③ 实测**：术语自检 report 与 city 目录**双 PASS**；report `SKILL.md` 330 行；
city 引用全部收敛在 city 包内，父技能无空指针引用。

**④ 上述待办已由 `e8ad0ab` 完成**：city references 已对齐 SSOT 体系（城市行并入 `holiday-data-fetch.json`、
采集交 fetch、模板 JSON 化、父技能版本引用更正），本条保留仅为记录分拆当时的状态。

#### `43e54db` · 2026-09-15 · 版本号体系：废弃双轨，统一三位

- `SKILL.md` frontmatter `version` **1.4.1 → 1.5.0**：旧 4.x / 5.x 体系作废，全仓只保留包版本一套。
- CHANGELOG：删「二、版本号双轨映射」（含双轨对应表、历史错位警示、发版四处核对），
  改为「二、版本号规则」三行；变更详情各节标题去掉「（内部 x.y.z ·）」；
  `v3.6` → `v1.3.6`；维护约定第 2 条简化为「更新 frontmatter 版本号后打 tag」。
- **未动**：references 与 bundled 内的文档版本号（本次范围限定 `SKILL.md` + CHANGELOG）。

#### `a66d2ab` · 2026-09-15 · SKILL.md 精简：去解释性叙事 + CSV→SSOT 一致性修正

**① 删除不影响执行的解释性叙事**（−39 / +20 行）

- **D2 术语自检的「原因 / 后果」两条**：上游半改名典故、`2026_暑假` → 命中 0 的推演链全部删除，
  只留规则本体「装完必跑自检」与两层检查、退出码。
- **阶段一「依据：半命中集厚度不足（2024 暑期 100 条…）」**删除 → 只留结论
  「命中 AtomGit 也调用 fetch，5 轮降 3 轮，不存在命中即跳过的分支」。
- 其余删除：Continuity 理念句（"单期报告是快照，系列报告才是资产"）、分析维度
  "专家评估补全"来源说明、双轨原则的 L1/L2 职能描述、纵向系列"上游最早 2023，故实际多为 4 年"、
  禁拉快照"占全仓体积 98%"、D3"仍建议跑一次 --fix"、覆盖率矩阵的括号补充、
  **阶段五重复目录树**（改为引用「Deliverables · 交付根目录」）。
- 随 `2026_暑假` 例句一并删除 `<!-- term-allow -->` 豁免标记 **2 处**：SKILL.md 现已无「暑假」字样，
  自检对该文件无需豁免（脚本豁免机制本身保留，供其他文档使用）。

**② 一致性修正（变更 4 的遗留）**

- 「在 CSV **显式圈定**入选行」×3 → 「在 SSOT 显式圈定」
  （探索性主题入选标准④、阶段二要点⑧、阶段二门禁⑤）。
- 纵向数据来源「读往年 CSV」→「从 `data_set/{年份}_{节假日}/` 读往年 SSOT」。
- 阶段四「以 L2 素材库为素材」→「以 L2 素材为素材」。
- Usage Notes 笔误「**域名**为城市时」→「**地域**为城市时」。

**③ 刻意保留**：坑 1/2/3（sparse-checkout 操作纪律）、「退出码 0 不得当作成功」静默失败警告、
F1→F2 轮数定义、三契约门禁清单、城市勾稽阈值——均为可执行约束，不是叙事。

**实测**：代码块围栏 6（3 块平衡）；「暑假」0 处；`term-allow` 0 处；
CSV 残留 3 处均为"派生视图不单独交付"或引用 `contracts.md` 原名，属预期。

#### `4452c83` · 2026-09-15 · 交付形态重构（用户变更 3/4/5）

**① 变更 3 · 废止「四件套」表述**

`SKILL.md` 不再出现「四件套 / 城市五件套」。交付物改按**数据侧 3 项 + 报告侧 3 项**描述。

- 删除位置：Overview、Deliverables（改为双子树结构表）、地域路由、Usage Notes 按需裁剪、
  `frontmatter description`（原文 `four-deliverable set`，已重写）。
- references 同步：`faq.md` Q5、`style-guide.md` 简介条、`templates.md` 首页结构、
  `templates-city.md`、`development-prompt-city.md`（五件套 → 城市交付物）。
- bundled 与安装版 fetch `SKILL.md` 2 处同步（"完整报告四件套" → "完整报告交付物"）。
- **保留**：`RevPAR/ADR/OCC 三件套`、间夜三件套等**指标组合**表述——与交付物无关，不改。

**② 变更 4 · `消费数据集.csv` / `现象素材库.json` 不再单独交付**

> 原则：二者均为 `holiday-data-fetch.json`（SSOT）的**派生视图**，需要时现算，**不落盘为独立交付物**。

- `SKILL.md`：Overview 增加显式「不再单独交付」声明；阶段五交付物清单删除二者；
  `Format & Delivery Rules` 改为"CSV / 素材库等派生视图不单独交付"。
- `data-architecture.md`：目录结构删掉 CSV 与素材库两行；派生视图规则加"也不单独交付"。
- **assets 4 个 HTML 模板**：CSV 下载链接改为跨子树指向 SSOT
  （`../../data_set/{年份}_{节假日}/holiday-data-fetch.json`），并去掉 `download` 属性。
  首页卡片三由「CSV 前 5 行预览」改为「数据预览」，来源标注改 SSOT。
- fetch 的 `validate_fetch.py --export-csv` **能力保留**（可选导出），但在 fetch `SKILL.md`
  加注"不作为独立交付物，仅供人工核查或临时分析"。

**③ 变更 5 · 目录结构改为 `holiday-data-reports/` 双子树**

```
holiday-data-reports/
├── data_set/{年份}_{节假日}/
│   ├── holiday-data-fetch.json     # SSOT
│   ├── 采集日志.csv
│   └── snapshots/                  # 按需单点补拉
└── data_report/{年份}_{节假日}/
    ├── index.html
    ├── 消费数据报告.html
    └── 数据真实性说明.html
```

- **取代**旧落点 `data_set/holiday_data/`（即 2026-09-15 变更 1）与旧 `data/{年份}/{节假日}/` 单树。
- 路径迁移 **45 处**（`SKILL.md` 6 + references 39），`data_set/holiday_data` 残留 **0**。
- **解读说明**：用户给出的树中 `snapshots/` / `holiday-data-fetch.json` / `采集日志.csv`
  与 `data_set/{年份}_{节假日}/` 同为 `|--` 缩进（平级）；实际采用**归属于
  `data_set/{年份}_{节假日}/`** 的解读——否则全仓只有一份快照与一个 JSON，无法分年分节，
  且与 AtomGit 上游每目录三件套的结构不符。**如与预期不符请指出。**
- `development-prompt.md` 为 v1.3.6 历史存档，正文未改写；其 v1.5.0 说明块已同步新路径与交付形态。

**实测**：D1 按新结构端到端 PASS（7 格命中 / 14 文件 / 0 快照混入 / 3.7 MB）；
5 个 HTML 模板标签平衡校验全 OK；术语自检 report + bundled 均 PASS。

#### `626e3c4` · 2026-09-15 · 阶段一重构：D1–D4 采集流水线 + 术语自检脚本 + 路径/仓库变更

**① 阶段一重写为 D1–D4 四步流水线**（取代上一版的 A/B 双线分支）

| 步骤 | 内容 |
|---|---|
| **D1** | 半命中下载：纵向 `{y}_{节日}`（y ∈ [Y−4, Y]）∪ 横向 `{Y}_{节日}`，取并集；探针 `git ls-tree`；稀疏检出只取 `holiday-data-fetch.json` + `采集日志.csv`，**禁拉 `snapshots/`**；拉取后强制校验「两文件存在且 L1 > 0」 |
| **D2** | 备妥 fetch：本地已装则启动；否则从 atomgit 安装，**装完必跑术语自检 `--fix`** |
| **D3** | 降级：安装失败则启动内置 `bundled/holiday-data-fetch/` |
| **D4** | 轮数分派：**有全命中 → 增量 3 轮**；**无全命中 → 联网 5 轮** |

- **推翻上一版设计**：上一版（共识 2）为"命中 AtomGit 则不调用 fetch 采集"，本版改为**命中也调 fetch，仅降轮数**。
  依据：半命中集厚度普遍不足（实测 2024 暑期 100 条 L1、2023 暑期 121 条，均低于门禁），纯消费基线撑不起一份报告。由用户裁决采纳（读法甲）。
- **轮数定义**：轮数 = F1（检索矩阵）→ F2（并行采集）的**循环次数**，不是新增阶段编号，不与 F0–F5 混淆。

**② 新增 `scripts/verify_holiday_terms.py`**（report 侧首个脚本）

- 两层检查：L1 文本术语、L2 枚举构造（致命层，直接决定目录名）。
- `--fix` 自动补丁；`--json` 机器可读；退出码 0=通过 / 1=有问题 / 2=路径非法。
- 保护词「暑运」不替换；有意保留的旧称须显式写 `<!-- term-allow -->` 登记，禁止静默放过。
- **实测**：远端 fetch 包至今仍是半改名（`HOLIDAYS` 含「暑假」→ 构造 `2026_暑假` → 上游只有 `2026_暑期` → 命中 0 且不报错）。检出 3 处枚举问题，`--fix` 后转 PASS，6 个脚本 `py_compile` 通过。

**③ 路径与仓库变更（用户指定）**

| 项 | 变更前 | 变更后 | 处数 |
|---|---|---|---|
| 基线落点 | `dataset\holiday-data-reports\` | `data_set\holiday_data\` | 48 |
| AtomGit 数据仓 | `atomgit.com/g_ww/holiday_data_reports` | `atomgit.com/g_ww/holiday_data` | 11 |
| 旧基线路径 | `.baseline-cache/`（散落 7 文件） | 统一并入 `holiday-data-reports/data_set/` | 20 |

> **后续已被 `4452c83` 取代**：基线落点现统一为 `holiday-data-reports/data_set/{年份}_{节假日}/`
> （见上方变更 5）。表中保留当时的目标值以记录演进过程。

- ⚠️ **旧仓 `holiday_data_reports` 已被删除**（`git ls-remote` 返回 403）。此项为**必须项**，非优化。
- fetch 安装源 `g_ww/holiday-data-fetch` 不受影响，仍可达。

**④ D1 端到端实测**：命中 7 格（2023–2026 暑期 + 2026 春节/五一/端午）、未命中 3 格（2022 暑期、2026 中秋、2026 十一）；14 文件、0 快照混入、3.7 MB、L1=1164 / 7 格全非空。

#### `8f8d89f` · 2026-09-11 · 共识 2：fetch 随包整合（后由 `626e3c4` 调整为 D1–D4）

- **物理整合**：`holiday-data-fetch` 完整副本置于 `bundled/holiday-data-fetch/`（244 KB / 12 文件）。
- **条件分支**（本版设计，已被下一版推翻）：原为"命中则不触发 fetch 采集能力"的 A/B 双线，现由 D4 的"命中也调、降为 3 轮"取代。

#### `e1da1dd` · 2026-09-11 · 术语统一：暑假 → 暑期

- 依据 ①：AtomGit 上游 2026-09-11 15:44 `7cb8758`「优化一些目录」将 4 个 `*_暑假` 目录更名为 `*_暑期`（`暑假` 现命中 0）。
- 依据 ②：`holiday-config.md` 属性卡原载「暑期（制度名，官方全用）/ 暑假（口语学制名）」。
- 改动：report 工作包 30 处（9 文件）+ fetch 安装版 21 处（7 文件，含 `HOLIDAY_SEQ` / `MIN_ROWS` 脚本字典）。
- 保护：「暑运」（交通部制度名，62 天）4 处未替换；`holiday-config.md` 保留 1 处旧称说明并标注弃用。
- 实测：请求 `2026 暑期` → 命中 7 目录 / L1=1164 / `seq=SH`，端到端 PASS。

---

### 1.4.1（`d2ae007`）

**减法重构 · 架构分拆**。交付物形态不变，非 breaking change。

1. **分层分拆**：采集细则（检索矩阵 / 同源双录 / 基线拉取 / 来源分级）完全移交 `holiday-data-fetch`；本技能阶段一收缩为「调用 + 门禁验收」（只验契约、不验过程）；资产沉淀（atomgit 回推）归位 fetch F5。
2. **契约显式化**：新增 `references/contracts.md` 三契约（L1 CSV / L2 素材库 / 纵向台账），验收从「查过程」改为「契约测试」。
3. **参数化配置**：`holiday-config.md` 升级为三张结构化配置（属性卡 / 口径地图 / 锚点日历），十一/中秋 `merge_mode` 显式化。
4. **分析内核重建**：新增 `references/analysis-methodology.md`（六节骨架），口径裁决 / 叙事批判 / 节日属性语义三合一沉淀。
5. **体量**：`SKILL.md` 540 → 238 行（方案目标 300，超额完成）；`FAQ` 12 条、`anti-patterns` 14 条从正文抽出为独立 reference。

**遗留缺陷（v1.5.0 承接）**：

- 阶段一门禁已引用 `fetch/references/coverage-matrix.md`，但**该文件在 fetch 侧不存在**——空指针门禁，永远无法勾选。
- `_meta.json` 在此版提交时被删除，工作包只剩 `.git / SKILL.md / assets / references`。

### 1.4.0（`19b1936`）

模板样式变更。`SKILL.md` 540 行 / 68,258 字节，references 13 份、assets 7 份（新增 `verification-template.html`）。

### 1.3.8（`47b54ef`）

调用节日 MCP（`holiday-data-mcp`）。此版本是 SkillHub 安装包的实际内容。

### 1.3.7（`14400b1`）

完整五阶段。此版因体积移除内置基线快照，是后续"快照规范断层"的起点。

### 1.0.0（`d8690d3`）

起点版本（2026-08-14）。8 文件 / 175 行 / 10 字段。原生具备：A/B/C/D 可信度分级、质量红线 6 条、五阶段、四件套、9 主题、URL 溯源。
**不具备**：快照、L1/L2 分层、勾稽、基线、MCP、`scripts/`。

---

## 五、已知缺口与待办

| # | 缺口 | 状态 |
|---|---|---|
| 1 | 中秋基线**全期 0 个目录**（六节日配置 vs 五节日基线，结构性缺口） | 待裁决：并入十一 / 独立采集 / 标为结构性缺口 |
| 2 | `2026_十一` 上游不存在，本地镜像有 7 行（4 行待核）→ 该格数据**未回推上游** | 待闭环 |
| 3 | 待核 116 行（暑假 + 十一占 63%） | 待裁决是否分批清理 |
| 4 | fetch 侧 `coverage-matrix.md` 仍缺失，report 门禁空转 | v1.5.0 W1 待建 |
| 5 | fetch 安装版 `_meta.json` 为 1.2.0，`SKILL.md` 无 `version` 字段 | 待裁决是否同期升 1.3.0 |
| 6 | 远端 fetch 包仍是半改名状态 | 每次 D2 安装后必跑 `--fix` 兜底 |

---

## 六、维护约定

1. **每次变更**：改 `SKILL.md` 规则正文 → 在本文件追加一条变更记录（日期 + commit + 改了什么 + 为什么）。
2. **发版**：更新 `SKILL.md` frontmatter 版本号，然后打 tag。
3. **不写历史**：`SKILL.md` 中禁止出现「本次新增」「vX.Y 起改为」「从 A 改为 B」等变更叙事；只写现行要求。
4. **有意保留的旧称/反例**：必须在行尾写 `<!-- term-allow -->`，否则 `verify_holiday_terms.py` 会判 FAIL。

---

_本文件随 v1.5.0 建立（2026-09-15）。此前版本的变更说明散落在 `SKILL.md` 与研讨文档中，已在此归集。_
