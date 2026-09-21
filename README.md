# Firefly

ArduPilot 生态的**本地文档镜像**：把 ArduPilot、Mission Planner、QGroundControl、MAVLink 四套文档以 git submodule 形式挂在同一个仓库下，供离线查阅与检索。

## 结构

四个子模组直接位于仓库根目录：

| 路径 | 上游仓库 | 内容 | 检出范围 |
|---|---|---|---|
| `ardupilot_wiki/` | `ArduPilot/ardupilot_wiki` | ArduPilot 与 Mission Planner 的文档源（reStructuredText + Sphinx） | **全量**（`planner` `planner2` `common` `copter` `plane` `rover` `sub` `dev` `blimp` `antennatracker` `mavproxy` `misc` `scripts` `frontend` `logos` `images` 等） |
| `qgroundcontrol/` | `mavlink/qgroundcontrol` | QGroundControl 用户指南、开发者指南与实现源码（Markdown + VuePress + QML/C++） | 稀疏：`docs src test tools cmake deploy custom-example` |
| `mavlink-devguide/` | `mavlink/mavlink-devguide` | MAVLink 开发者指南（Markdown + VitePress） | **全量** |
| `mavlink/` | `mavlink/mavlink` | MAVLink 协议定义 XML 与生成工具 | **全量** |

`ardupilot_wiki`、`mavlink-devguide`、`mavlink` 三个子模组是**完整检出**。只有 `qgroundcontrol` 保留稀疏范围：它 5,492 项里绝大部分是与文档无关的资源、翻译与平台工程文件（`resources/` `translations/` `android/`），而开发者指南会引用的实现与构建目录（`src/` `test/` `tools/` `cmake/` `deploy/` `custom-example/`）已全部收入。四个子模组都是**完整克隆（带历史）**，因此子模组内 `git log`、`git blame` 可用。

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
git -C qgroundcontrol sparse-checkout set docs src test tools cmake deploy custom-example
```

其余三个子模组（`ardupilot_wiki`、`mavlink-devguide`、`mavlink`）是完整检出，无需处理。

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

**有意包含**：Mission Planner 文档（`planner/`）与 APM Planner 2 文档（`planner2/`）、跨机型页（`common/`）、ArduPilot 四个机型与 Blimp 的文档（`copter/` `plane/` `rover/` `sub/` `blimp/`）、`antennatracker/`、`mavproxy/`、开发者文档（`dev/`）、ArduPilot 首页（`ardupilot/`）、文档构建工具（`scripts/`，Sphinx 扩展所在，构建 wiki 文档必需）与全部配图（`images/`）；QGroundControl 的用户指南与开发者指南、实现源码与测试、构建与打包工具（`src/` `test/` `tools/` `cmake/` `deploy/` `custom-example/`）；MAVLink 开发者指南（含 `zh/ko`）、协议定义 XML、组件元数据与生成工具。

各子模组内还包含与文档无关的上游文件（CI 配置、站点前端 `frontend/`、图标 `logos/` 等），这是「完整检出」的必然结果，不另行剔除。

**有意不包含**，以及原因：

| 未包含 | 原因 |
|---|---|
| `qgroundcontrol/resources/`、`translations/`、`android/` | 开发者指南对三者的引用次数实测为 **0**（扫描 44 个 md 文件），故不收；其中 `resources/` 有 417 项 |
| `mavlink/pymavlink/` | 嵌套子模组（生成器与 Python 绑定）。开发者指南对它的 79 处提及全部是外链与安装/运行命令，**没有一处要求本地存在该目录**；需要时 `git -C mavlink submodule update --init pymavlink` |
| MissionPlanner 源码仓库 | 它的文档并不在源码仓库里（在 `ardupilot_wiki/planner/`），源码对查阅文档无必要 |
| 站点构建产物（HTML） | 构建产物是派生物，原件已完整；需要网页版时用已收录的 `scripts/` 与 VitePress 现场构建 |
| 检索索引 / 向量库 | 未做，且与镜像形态无关，可随时在此之上追加 |

检索顺序与噪声排除规则见 `.clinerules/01-doc-retrieval.md`（agent 在本仓库工作时自动生效）。

## 附：当前钉住版本与体量

重建后实测（2026-09-21）。`钉住提交` 是四个子模组记录的上游提交，**权威来源仍是 `git submodule status`**。

| 子模组 | 钉住提交 | 工作区 | 工作区体积 | 本地 `.git` 体积 |
|---|---|---|---|---|
| `ardupilot_wiki` | `e550458ed4f4a73ef4030efa766622aba219984a` | 5,532 文件 | 779.85 MB | 1,335.11 MB |
| `qgroundcontrol` | `6f1f4368de08fe093291c63ac7f012c797aaf3c4` | 4,717 文件 | 74.56 MB | 546.15 MB |
| `mavlink-devguide` | `e27e862fb9ec5d185dc84ad5496fbc94a897304f` | 362 文件 | 11.63 MB | 16.72 MB |
| `mavlink` | `3203f89c510337c0088244735c6a5056c52b5a28` | 66 文件 | 1.39 MB | 15.34 MB |
| **合计** | | **10,677 文件** | **867.43 MB** | **1,913.31 MB** |

四个子模组都是**完整克隆**（`is-shallow=false`），提交数分别为 10,070 / 21,892 / 2,126 / 3,821。`.git` 体积主要来自完整历史，换来的是子模组内 `git log`、`git blame`、`git bisect` 可用。
