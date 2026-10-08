# docs

## 目录结构

```text
docs/
|-- software/
|   |-- ardupilot_wiki/
|   |-- qgroundcontrol/
|   |-- mavlink-devguide/
|   `-- mavlink/
|-- hardware/
|   |-- CUAV/
|   |-- FLYCOLOR/
|   |-- SIYI/
|   `-- SUNNYSKY/
`-- AGENTS.md
```

## software

四个 git submodule, 只读参考区; 不要在子模组内做本地修改. 路径与命令均以仓库根为基准.

| 路径 | 上游仓库 | 内容 | 检出范围 |
|---|---|---|---|
| `docs/software/ardupilot_wiki/` | `ArduPilot/ardupilot_wiki` | ArduPilot 与 Mission Planner 的文档源 (reStructuredText + Sphinx) | **全量** |
| `docs/software/qgroundcontrol/` | `mavlink/qgroundcontrol` | QGroundControl 用户指南, 开发者指南与实现源码 (Markdown + VuePress + QML/C++) | `docs src test tools cmake deploy custom-example` |
| `docs/software/mavlink-devguide/` | `mavlink/mavlink-devguide` | MAVLink 开发者指南 (Markdown + VitePress) | **全量** |
| `docs/software/mavlink/` | `mavlink/mavlink` | MAVLink 协议定义 XML 与生成工具 | **全量** |

`ardupilot_wiki`, `mavlink-devguide`, `mavlink` 为完整检出, `qgroundcontrol` 为稀疏检出; 四个子模组都是完整克隆, 子模组内 `git log`, `git blame` 可用.

### 版本与校验

版本状态以 `git submodule status` 为准, 不要以任何文档为准.

```powershell
git submodule status                                                  # 四行都应以空格开头: - 未初始化, + 与记录不一致, 两者都不应出现
git -C docs/software/qgroundcontrol sparse-checkout list              # 应列出上表的稀疏路径
git -C docs/software/qgroundcontrol rev-parse --is-shallow-repository # 应为 false
```

### 升级

```powershell
git submodule update --remote
git submodule status
git add . ; git commit -m "chore: bump doc submodules"
```

`--remote` 取 `.gitmodules` 记录的分支 (均为 `master`) 的最新提交; 升级结果作为一次提交留在本仓库, 可 diff, 可回滚.

### 检索规则

- 顺序固定: 官方文档 -> 协议定义 -> 源码实现; 回答里区分文档结论与源码验证结论.
- 默认排除 `images/`, `assets/`, `logos/`, `frontend/`, `.github/`, `test/`, `translations/`, `resources/` 以及翻译目录中的 `ko/`; 中文问题优先 `zh/`, 英文问题优先 `en/`.
- 引用本地文件前必须实际打开确认; 文档里的交叉引用若指向本地路径, 该路径必须真实存在.

### 范围

**有意包含**: Mission Planner 文档 (`planner/`) 与 APM Planner 2 文档 (`planner2/`), 跨机型页 (`common/`), ArduPilot 四个机型与 Blimp 的文档 (`copter/` `plane/` `rover/` `sub/` `blimp/`), `antennatracker/`, `mavproxy/`, 开发者文档 (`dev/`), ArduPilot 首页 (`ardupilot/`), 文档构建工具 (`scripts/` 与 Sphinx 扩展) 与全部配图 (`images/`); QGroundControl 的用户指南与开发者指南, 实现源码与测试, 构建与打包工具 (`src/` `test/` `tools/` `cmake/` `deploy/` `custom-example/`); MAVLink 开发者指南 (含 `zh/ko`), 协议定义 XML, 组件元数据与生成工具.

**有意不包含**: `docs/software/qgroundcontrol/` 下的 `resources/`, `translations/`, `android/`; `docs/software/mavlink/pymavlink/` (嵌套子模组, 需要时 `git -C docs/software/mavlink submodule update --init pymavlink`); MissionPlanner 源码仓库 (文档在 `docs/software/ardupilot_wiki/planner/`); 站点构建产物 (HTML).

## hardware

硬件资料按厂商放在 `docs/hardware/<厂商>/` (本目录不入 Git, 只在本机维护). 本地内容为 MinerU 的转换产物, 目录形如 `<原文件名>.pdf-<uuid>/`:

```text
<原文件名>.pdf-<uuid>/
|-- full.md                    正文 (主读)
|-- images/                    图片
|-- layout.json                版面结构
|-- block_list.json            块列表
|-- *_content_list.json        内容列表
|-- *_content_list_v2.json     内容列表 (按页)
|-- *_model.json               模型输出
|-- MinerU_markdown_*.md       客户端导出的 Markdown, 与 full.md 同源
`-- *_origin.pdf               原始 PDF, 只留存不解析
```

### 读取规则

- 先读 `full.md`; 图片是正文的一部分, 接口/接线/尺寸等内容直接看 `images/`, 不要因为正文没写就当缺失.
- `*_origin.pdf` **不解析**: 只作留存与人工溯源, 任何 agent 都不得用脚本或工具解析它.
- `layout.json`, `block_list.json`, `*_content_list*.json`, `*_model.json` 在需要结构化定位时备用, 不替代正文阅读.
- `MinerU_markdown_*.md` 与 `full.md` 同源, 二选一即可.

### 回退规则

本地没有对应文档时, 下表网页只作回退说明, 用于向用户指明缺哪份文档:

| 制造商 | 中文文档 | 英文文档 |
|---|---|---|
| CUAV | [中文](https://doc.cuav.net/) | [英文](https://doc.cuav.net/en/) |
| SIYI | [中文](https://www.siyi.biz/zh/download/) | [英文](https://www.siyi.biz/en/download/) |
| FLYCOLOR | [中文](https://cn.fly-color.net/index.php?c=category&id=4) | [英文](https://en.fly-color.net/index.php?c=category&id=4) |
| SUNNYSKY | [中文](http://www.rcsunnysky.com/Download/index.html) | [英文](http://en.rcsunnysky.com/Download/index.html) |

- 回退时禁止自行下载, 抓取或读取网页与 PDF; 需要时告知用户, 由用户按标准转换流程处理.
- 飞控程序文档与硬件制造商文档冲突时, 以制造商文档为准.
