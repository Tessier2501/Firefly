# Firefly

Windows 端的无人机调试工作区, 同时收录 ArduPilot 生态的本地文档镜像.

## 目录约定

| 路径 | 用途 | 详细约定 |
|---|---|---|
| `docs/` | 文档镜像: ArduPilot Wiki (含 Mission Planner), QGroundControl, MAVLink 与 MAVLink Devguide 四个 git submodule | `docs/AGENTS.md` |
| `scripts/` | 长期使用和维护的工具 | `scripts/AGENTS.md` |
| `temp/` | 非长期内容: 一次性脚本, 临时输出, 试验数据, 临时下载 | `temp/AGENTS.md` |
| 仓库根 | 只保留 `README.md`, `.gitmodules`, `.clinerules/` 等仓库级文件 | - |

其他目录 (例如案例归档) 按需后续建立, 不预先创建空目录.

## 环境

Python 统一使用 conda 环境 `myenv`, 由 Freeside 管理, 本仓库不维护依赖清单. 串口与硬件工具的使用方式见 `scripts/AGENTS.md`.

## 约定

- 文档材料只进 `docs/`, 长期工具只进 `scripts/`, 一次性与临时内容只进 `temp/`.
- `docs/` 内是第三方镜像, 不做本地修改; 检索规则见 `.clinerules/01-doc-retrieval.md`.
- 子模组版本以 `git submodule status` 为准.

## 快速校验

```powershell
git submodule status    # 四行都应以空格开头
```