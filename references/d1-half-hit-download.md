# D1 · 半命中下载规程（Half-Hit Download）

> 本文件承载**阶段一 D1 的完整操作规程**。`SKILL.md` 只保留定位与三条硬门禁。
> 上游仓库 `https://atomgit.com/g_ww/holiday_data`；产物落 `holiday-data-reports/data_set/{年份}_{节假日}/`。

## 第 0 步 · git 可用性前置（不可跳过）

按 **探测 → 安装 → 降级** 执行：

1. **探测**：`git --version` → 绝对路径直连 → Python `subprocess` 调该绝对路径（绕开损坏的 shell PATH）。
   - Windows：`%USERPROFILE%\.workbuddy\binaries\PortableGit\versions\*\cmd\git.exe`（**`cmd\` 非 `bin\`**）、`C:\Program Files\Git\cmd\git.exe`、`where git`
   - macOS/Linux：`which git`
2. **安装**（探测三级全失败才执行）；装后按第 1 步的**绝对路径**复验 rc=0 —— 新装 git 通常尚未进 PATH。
   - Windows：环境自带二进制安装能力 → `winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity`（绝对路径 `C:\Users\<用户>\AppData\Local\Microsoft\WindowsApps\winget.exe`）→ 下载 Git for Windows 便携版解压至 `~/.workbuddy/binaries/PortableGit/versions/<ver>/`，取 `cmd\git.exe`
   - macOS：`xcode-select --install` → `brew install git`
   - Linux：`apt-get install -y git` / `yum install -y git` / `apk add git`
3. **降级**：安装仍失败 → 判"无全命中"，D4 走 5 轮联网，并在采集日志与「数据真实性说明」写明
   `D1 未执行：git 不可用（探测 + 安装均失败：<原因>）`。

> shell PATH 可能整体损坏（`dirname` / `cd` / `head` 报 `command not found`），此时 `git` 看似不可用但可执行文件完好。
> 误判代价：D4 由 **3 轮增量**退回 **5 轮联网**。

## 1. 解析与系列构造

解析 [年份] Y、[节日] F、[地域]，构造**两个半命中系列**并取并集（交叉格只计一次）：

- **纵向系列** `{y}_{F}`，y ∈ [Y−4, Y]（回溯**不超过 5 年**）
- **横向系列** `{Y}_{f}`，f ∈ 六节日
- `{Y}_{F}` 同时属于两系列 → 去重后只下载一次

## 2. 存在性探针（逐目录，不下载 blob）

`git ls-tree --name-only "HEAD:{目录}"` 返回含 `holiday-data-fetch.json` = 该格存在。

## 3. 稀疏检出

检出至 `holiday-data-reports/data_set/{年份}_{节假日}/`，**只拉两个文件**：`holiday-data-fetch.json` + `采集日志.csv`；
**禁拉 `snapshots/`**（每条记录自带 `snapshot` 相对路径，按需单点补拉）。

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

## 4. 拉取后强制校验（不可省）

逐目录断言「两文件均存在 且 L1 行数 > 0」，不满足即判该格未命中。

> **退出码 0 不得当作成功**：目录名写错时 `sparse-checkout` 仍返回 0、工作区为空、零警告——本流程最危险的静默失败点。

**产出**：半命中数据集（可为空）+ 命中/未命中清单（须写入采集日志）。
