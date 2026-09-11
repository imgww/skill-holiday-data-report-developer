# 经济学人/FT 财经报刊排版规范（Style Guide）

报告、真实性说明与首页均遵循本规范。直接套用对应骨架模板可省去大部分样式工作。

## 设计语言

- **底色**：米白浅暖底（`--paper:#F5EFE2`）,不用纯白
- **文字**：深褐墨色（`--ink:#211C14`）,次级 `--ink2:#4B4436`,弱化 `--ink3:#7A715F`
- **主色**：暗红（`--red:#8C1F28`）,点缀色 `--red2:#A83A45`
- **辅助**：描金（`--gold:#A3803F`）,分隔线 `--line:#C8BBA0`
- **字体**：`--font-stack` = Georgia, "Noto Serif SC", "Songti SC", "STSong", "SimSun", serif（衬线正文/标题）；`--ui-stack` = system-ui, "Microsoft YaHei", "PingFang SC" 等（UI/导航/表格）；`--mono` 等宽（代码）
- **行高** 1.66,正文 15px,页面最大宽度 1180px（--max）
- **明暗双主题**：`[data-theme="dark"]` 显式暗色；`@media (prefers-color-scheme:dark)` 无 JS 自动暗色；`[data-theme="light"]` 可覆盖系统偏好。AI 生成时直接套用 `report-template.html` 令牌即可，勿手动改写颜色。

## CSS 变量（统一以 :root 定义，与 report-template.html 同步）

```css
:root{
  --paper:#F5EFE2;  --paper2:#EFE6D2;  --paper3:#EAE0C9;  --paper-glass:rgba(245,239,226,.92);
  --ink:#211C14;    --ink2:#4B4436;    --ink3:#7A715F;
  --red:#8C1F28;    --red2:#A83A45;    --red-soft:#F3D4D6;
  --line:#C8BBA0;   --gold:#A3803F;    --gold-soft:#F0E4CD;
  --green:#2E6B3E;  --blue:#1F4E5F;    --blue2:#2E7C92;   --night:#171511;
  --shadow:0 6px 22px rgba(33,28,20,.16);
  --max:1180px; --bar-h:50px;
  --font-stack:Georgia,"Noto Serif SC","Songti SC","STSong","SimSun",serif;
  --ui-stack:system-ui,-apple-system,"Microsoft YaHei","PingFang SC",sans-serif;
  --mono:"SFMono-Regular",Consolas,"Courier New",monospace;
}
```

## 报告组件清单

| 组件 | 规格 |
| --- | --- |
| 报头（masthead） | 顶部双线 4px + 细线 1px;kicker 暗红 12px 字距 6px;标题 clamp(34px,5.6vw,60px) 字重 900;副题 14px 字距 4px;红色三线 rule 88px |
| 滚动条（ticker） | 顶部数据速览,红色 `<b>` 强调,底线分隔 |
| 头条（lead） | 大标题 clamp(24px,3.4vw,38px);standfirst 左红边 4px;正文两栏 column-count:2,column-rule:1px solid var(--line) |
| 首字下沉（dropcap） | `.dropcap::first-letter{float:left;font-size:3.6em;line-height:0.82;color:var(--red)}` |
| 数字带（fig-strip） | 上下 3px 双线,6 栏;数字 clamp(20px,2.2vw,30px) 暗红 900;标签 11.5px 字距 1px |
| 栏目标题 | `.section-head::before` 红条 34x3px;标题衬线加粗 |
| 来源注记 | `.src` 11.5px 斜体 ink3,机构名 `<b>` 暗红 |
| 纵向延续与前瞻 | 框架第二部分(v3.3 新增),6 子节(2.1–2.6);子标题 `h4` 17px 加粗,左 3px 红边 |
| 预测卡（forecast-card） | 上 3px 双线红边 + 1px 线框,paper2 底;`.fc-row` 弹性行(标签/数值/区间三栏);`.fc-note` 内含置信度徽章 |
| 偏差卡（deviation-card） | 预测复盘表容器,1px 线框 + paper2 底,`.dc-head` 暗红 13px 字距 2px |
| 拐点判据（inflection） | 左 4px 描金边 + paper3 底,14px ink2,用于 2.6 中长期趋势可观测预警 |
| 置信度徽章（conf-badge） | 三色小徽章:高=暗红/中=描金/低=ink3;`高/中/低` 对应预测卡置信度 |
| 表格 | 细线 1px solid var(--line),表头暗红或双线;数字 tabular-nums |
| 页脚 | 顶部双线,注明来源机构与报告年份、测算声明 |

## 首页组件清单

> 首页（`landing-page-template.html`）与报告同属 v4 设计系统：明暗双主题、1180px、全部内联、无外链、无 emoji。
> **v4.0 形态变更**：已移除吸顶导航 `header.appbar`，首页与报告均自报头开篇，明暗切换按钮移至报头右端；便于整体嵌入任意主页框架，亦不再依赖外部门户导航。

| 组件 | 规格 |
| --- | --- |
| 面包屑（breadcrumb） | 首页 / 年度 / 本页;同目录相对路径;纯单页可整段删除 |
| 报头（masthead） | 同报告报头,标题改为"[年度][节假日]消费数据报告"门户标识 |
| 简介条（intro-bar） | 报头下方一行,概述四件套内容,暗红色字 13px |
| 连续性高亮条（continuity-bar） | 可选;上下 3px 双线 + paper3 底,左暗红标签 CONTINUITY + 文案 + 右暗红实心按钮,链接跨年纵向专题;无纵向专题时整段删除 |
| 卡片网格（card-grid） | 3 列 grid,间距 24px;≤900px 降为单列纵向堆叠;flex 子项 min-width:0 防溢出 |
| 卡片（card） | 背景 var(--paper2),上下 3px 双线边框,顶 60px 红条;内边距 28px 24px;无圆角 |
| 卡片标题（card-head） | 暗红衬线 18px 加粗 + 圆形描红图标 + 右置 tag 标签 |
| 卡片预览正文（card-body） | 14.5px 正文,摘录 2-3 段,行高 1.68,颜色 ink2;含 lead-title / standfirst / src-note |
| 卡片链接按钮（card-cta） | 暗红底白字,padding 11px 22px,UI 字体 14px,hover 变深红;圆角 2px |
| CSV 预览表（csv-preview） | 同报告表格样式,缩小至 11.5px;水平滚动 overflow-x:auto;徽章 a=绿/b=蓝/c=金/d=灰 |
| 页脚导航（footer-nav） | 顶部 4px 双线;三列网格（返回/本门户文件/跨年专题）+ 回顶按钮 |
| 页脚 | 同报告页脚,注明生成日期与来源机构 |
| 浮动回顶（back-top-float） | 固定右下圆形暗红按钮,含刘海安全区;打印/移动端可达性一致 |

## 首页卡片响应式规则

```css
.card-grid{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:24px;
}
@media (max-width:900px){
  .card-grid{grid-template-columns:1fr;}
}
```

## 技术约束（硬性,报告与首页通用）

1. 全部 CSS/JS 内联于单文件 HTML,无任何外链（不引用 CDN、外部字体、外部图片）
2. 无 emoji;图表用内联 SVG 或 CSS 绘制
3. 简体中文
4. 响应式：窄屏单栏（grid 降级、column-count 归 1、数字带换行、卡片纵向堆叠）
5. 页脚必须注明：来源机构 + 报告年份 + 测算声明

## 数据呈现约定

- 涨跌色（如涉及股市/价格走势）：中国惯例 **涨红跌绿**
- 金额默认 ¥(CNY)
- 推算值后加"（测算）"并弱化显示
- 每条数据旁或页脚附来源机构名;报告正文中的关键数字应可对应到《数据真实性说明》溯源表
