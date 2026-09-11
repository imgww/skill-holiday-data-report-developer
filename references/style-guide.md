# 经济学人/FT 财经报刊排版规范（Style Guide）

报告、真实性说明与首页均遵循本规范。直接套用对应骨架模板可省去大部分样式工作。

## 设计语言

- **底色**：米白浅暖底（`--paper:#F5EFE2`）,不用纯白
- **文字**：深褐墨色（`--ink:#211C14`）,次级 `--ink2:#4B4436`,弱化 `--ink3:#7A715F`
- **主色**：暗红（`--red:#8C1F28`）,点缀色 `--red2:#A83A45`
- **辅助**：描金（`--gold:#A3803F`）,分隔线 `--line:#C8BBA0`
- **字体**：Georgia, "Times New Roman", "Songti SC", "STSong", "SimSun", serif（衬线）
- **行高** 1.62,正文 15px,页面最大宽度 1120px

## CSS 变量（统一以 :root 定义）

```css
:root{
  --paper:#F5EFE2;  --paper2:#EFE6D2;  --paper3:#EAE0C9;
  --ink:#211C14;    --ink2:#4B4436;    --ink3:#7A715F;
  --red:#8C1F28;    --red2:#A83A45;
  --line:#C8BBA0;   --gold:#A3803F;
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
| 表格 | 细线 1px solid var(--line),表头暗红或双线;数字 tabular-nums |
| 页脚 | 顶部双线,注明来源机构与报告年份、测算声明 |

## 首页组件清单

| 组件 | 规格 |
| --- | --- |
| 报头（masthead） | 同报告报头,标题改为"[年度][节假日]消费数据报告"门户标识 |
| 简介条（intro-bar） | 报头下方一行,概述四件套内容,暗红色字 13px |
| 卡片网格（card-grid） | 3 列 grid,间距 24px;窄屏降为单列纵向堆叠 |
| 卡片（card） | 背景 var(--paper2),圆角 4px,上下 3px 双线边框;内边距 28px 24px |
| 卡片标题（card-head） | 暗红衬线 18px 加粗,左红条 3px 内嵌 |
| 卡片预览正文（card-body） | 15px 正文,2-3 段摘录,行高 1.62,颜色 ink2 |
| 卡片链接按钮（card-cta） | 暗红底白字,padding 10px 22px,衬线字体 14px,hover 变深红;圆角 2px |
| CSV 预览表（csv-preview） | 同报告表格样式,但缩小至 12px;水平滚动 overflow-x:auto |
| 页脚 | 同报告页脚,增加 EdgeOne 部署提示 |

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
