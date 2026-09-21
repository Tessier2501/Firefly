# Firefly

ArduPilot 生态的**本地文档镜像**: 把 ArduPilot, Mission Planner, QGroundControl, MAVLink 四套文档以 git submodule 形式挂在同一个仓库下, 供离线查阅与检索.

## 结构

四个子模组直接位于仓库根目录:

| 路径 | 上游仓库 | 内容 | 检出范围 |
|---|---|---|---|
| `ardupilot_wiki/` | `ArduPilot/ardupilot_wiki` | ArduPilot 与 Mission Planner 的文档源 (reStructuredText + Sphinx) | **全量** |
| `qgroundcontrol/` | `mavlink/qgroundcontrol` | QGroundControl 用户指南, 开发者指南与实现源码 (Markdown + VuePress + QML/C++) | `docs src test tools cmake deploy custom-example` |
| `mavlink-devguide/` | `mavlink/mavlink-devguide` | MAVLink 开发者指南 (Markdown + VitePress) | **全量** |
| `mavlink/` | `mavlink/mavlink` | MAVLink 协议定义 XML 与生成工具 | **全量** |

`ardupilot_wiki`, `mavlink-devguide`, `mavlink` 三个子模组是**完整检出**; `qgroundcontrol` 保留上表列出的稀疏范围. 四个子模组都是**完整克隆**, 因此子模组内 `git log`, `git blame` 可用.

**版本状态以 `git submodule status` 为准**, 不要以本文件为准.

## 常用操作

### 升级到上游最新

```powershell
git submodule update --remote
git submodule status                     # 核对新的提交号
git add . ; git commit -m "chore: bump doc submodules"
```

`--remote` 会取 `.gitmodules` 里记录的分支 (此处为 `master`) 的最新提交. 升级结果作为一次提交留在本仓库, 可 diff, 可回滚.

### 校验

```powershell
git submodule status
```

四行都应以**空格**开头: `-` 表示未初始化, `+` 表示工作区提交与记录不一致, 两者都不应出现.

```powershell
git -C qgroundcontrol sparse-checkout list                  # 应列出上表的路径
git -C qgroundcontrol rev-parse --is-shallow-repository     # 应为 false
```

## 范围声明

**有意包含**: Mission Planner 文档 (`planner/`) 与 APM Planner 2 文档 (`planner2/`), 跨机型页 (`common/`), ArduPilot 四个机型与 Blimp 的文档 (`copter/` `plane/` `rover/` `sub/` `blimp/`), `antennatracker/`, `mavproxy/`, 开发者文档 (`dev/`), ArduPilot 首页 (`ardupilot/`), 文档构建工具 (`scripts/`, Sphinx 扩展所在, 构建 wiki 文档必需) 与全部配图 (`images/`); QGroundControl 的用户指南与开发者指南, 实现源码与测试, 构建与打包工具 (`src/` `test/` `tools/` `cmake/` `deploy/` `custom-example/`); MAVLink 开发者指南 (含 `zh/ko`), 协议定义 XML, 组件元数据与生成工具.

**有意不包含**:

| 未包含 | 原因 |
|---|---|
| `qgroundcontrol/resources/`, `translations/`, `android/` | 与文档无关的资源, 翻译与平台工程文件, 检索时排除 |
| `mavlink/pymavlink/` | 嵌套子模组, 本镜像不需要; 需要时 `git -C mavlink submodule update --init pymavlink` |
| MissionPlanner 源码仓库 | 文档在 `ardupilot_wiki/planner/`, 源码对查阅文档无必要 |
| 站点构建产物 (HTML) | 可由已收录的 `scripts/` 与 VitePress 现场构建 |

检索顺序与噪声排除规则见 `.clinerules/01-doc-retrieval.md` (agent 在本仓库工作时自动生效).

## 附: 制造商文档

当飞控程序文档与硬件制造商文档冲突时, 以制造商文档为准. 通过以下链接访问制造商文档:

| 制造商 | 中文文档 | 英文文档 |
|---|---|---|
| CUAV | [中文](https://doc.cuav.net/) | [英文](https://doc.cuav.net/en/) |
| SIYI | [中文](https://www.siyi.biz/zh/download/) | [英文](https://www.siyi.biz/en/download/) |
| FLYCOLOR | [中文](https://cn.fly-color.net/index.php?c=category&id=4) | [英文](https://en.fly-color.net/index.php?c=category&id=4) |
| SUNNYSKY | [中文](http://www.rcsunnysky.com/Download/index.html) | [英文](http://en.rcsunnysky.com/Download/index.html) |

如有需求, 请求用户下载所需文档到本地.
