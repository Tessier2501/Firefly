# Firefly

ArduPilot 生态的**本地文档镜像**：把 ArduPilot、Mission Planner、QGroundControl、MAVLink 四套文档以 git submodule 形式挂在同一个仓库下，供离线查阅与检索。

## 结构

四个子模组直接位于仓库根目录：

| 路径 | 上游仓库 | 内容 | 稀疏范围 |
|---|---|---|---|
| `ardupilot_wiki/` | `ArduPilot/ardupilot_wiki` | ArduPilot 与 Mission Planner 的文档源（reStructuredText + Sphinx） | `planner common images copter plane rover sub dev blimp antennatracker mavproxy misc scripts ardupilot` |
| `qgroundcontrol/` | `mavlink/qgroundcontrol` | QGroundControl 用户指南与开发者指南（Markdown + VitePress） | `docs` |
| `mavlink-devguide/` | `mavlink/mavlink-devguide` | MAVLink 开发者指南（Markdown + VitePress） | 全量 |
| `mavlink/` | `mavlink/mavlink` | MAVLink 协议定义 XML 与生成工具 | `message_definitions doc` |

四个上游仓库都远大于所需内容，**稀疏检出（sparse-checkout）在这里的作用是限定范围**：让本地只出现上述文档，而不是整个仓库（例如 QGC 的 `src/`、wiki 的 `planner2/` 与站点装饰目录）。四个子模组都是**完整克隆（带历史）**，因此子模组内 `git log`、`git blame` 可用。

**版本状态以 `git submodule status` 为准**，不要以本文件为准。

## 常用操作

### 升级到上游最新

```powershell
git submodule update --remote
git submodule status                     # 核对新的提交号
git add . ; git commit -m "chore: bump doc submodules"
```

`--remote` 会取 `.gitmodules` 里记录的分支（此处为 `master`）的最新提交。升级结果作为一次提交留在本仓库，可 diff、可回滚。

### 在另一台机器上取回

```powershell
git clone <本仓库地址> Firefly
cd Firefly
git submodule update --init
```

- **不要用 `--recurse-submodules`**：它会连同 `mavlink/pymavlink` 一起克隆（那是 `mavlink` 内部的嵌套子模组，本镜像不需要）。`git submodule update --init` 不带 `--recursive`，只初始化顶层这四个。
- **稀疏范围不会被克隆过程保留**（git 的限制：`.gitmodules` 里没有存放稀疏路径的位置），克隆后需重新施加：

```powershell
git -C ardupilot_wiki sparse-checkout set planner common images copter plane rover sub dev blimp antennatracker mavproxy misc scripts ardupilot
git -C qgroundcontrol sparse-checkout set docs
git -C mavlink        sparse-checkout set message_definitions doc
```

`mavlink-devguide` 不设稀疏，无需处理。

### 校验

```powershell
git submodule status
```

四行都应以**空格**开头：`-` 表示未初始化，`+` 表示工作区提交与记录不一致，两者都不应出现。

```powershell
git -C ardupilot_wiki sparse-checkout list                  # 应列出上表的路径
git -C ardupilot_wiki rev-parse --is-shallow-repository     # 应为 false
```

## 范围声明

**有意包含**：ArduPilot 各机型文档（`copter` `plane` `rover` `sub` `blimp`）、`antennatracker`、`mavproxy`、开发者文档（`dev`）、ArduPilot 首页、Mission Planner 文档及其跨机型依赖页与配图、QGroundControl 用户与开发者指南（含 `zh/ko/tr` 翻译与图片）、MAVLink 开发者指南（含 `zh/ko`）与协议定义 XML。

**有意不包含**，以及原因：

| 未包含 | 原因 |
|---|---|
| `qgroundcontrol/src/` | 本轮范围只到文档。**注意**：QGC 开发者指南有相当篇幅在讲源码，因此该指南的可追溯性是不完整的 |
| `ardupilot_wiki/planner2/` | 是 **APM Planner 2**（另一款 GCS）的文档，不属 ArduPilot + Mission Planner 范围；需要时一条命令即可加入稀疏集 |
| `ardupilot_wiki/frontend/`、`logos/` | 文档站点的静态前端与图片标识，不是文档内容 |
| `mavlink/pymavlink/` | MAVLink 的生成器与 Python 绑定；本镜像只要协议定义与文档，需要时 `git -C mavlink submodule update --init pymavlink` |
| MissionPlanner 源码仓库 | 它的文档并不在源码仓库里（在 `ardupilot_wiki/planner/`），源码对查阅文档无必要 |
| 站点构建产物（HTML） | 构建产物是派生物，原件已完整；需要网页版时用已收录的 `scripts/` 与 VitePress 现场构建 |
| 检索索引 / 向量库 | 未做，且与镜像形态无关，可随时在此之上追加 |

## 附：当前钉住版本与体量

重建后实测（2026-09-21）。`钉住提交` 是四个子模组记录的上游提交，**权威来源仍是 `git submodule status`**。

| 子模组 | 钉住提交 | 工作区 | 工作区体积 | 本地 `.git` 体积 |
|---|---|---|---|---|
| `ardupilot_wiki` | `e550458ed4f4a73ef4030efa766622aba219984a` | 5,322 文件 | 762.62 MB | 1,335.11 MB |
| `qgroundcontrol` | `6f1f4368de08fe093291c63ac7f012c797aaf3c4` | 1,051 文件 | 24.58 MB | 546.15 MB |
| `mavlink-devguide` | `e27e862fb9ec5d185dc84ad5496fbc94a897304f` | 362 文件 | 11.63 MB | 16.72 MB |
| `mavlink` | `3203f89c510337c0088244735c6a5056c52b5a28` | 36 文件 | 1.21 MB | 15.34 MB |
| **合计** | | **6,771 文件** | **800.04 MB** | **1,913.31 MB** |

四个子模组都是**完整克隆**（`is-shallow=false`），提交数分别为 10,070 / 21,892 / 2,126 / 3,821。`.git` 体积主要来自完整历史，换来的是子模组内 `git log`、`git blame`、`git bisect` 可用。
