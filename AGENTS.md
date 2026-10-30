# Firefly

Firefly 是用于无人设备调试的工作区。

## 1. 目录结构

```text
Firefly/
|-- AGENTS.md         操作规范：交接、规范，记忆协议
|-- data/             调试过程中搜集到的数据和分析产物
|   |-- frame_<ID>    数据按机架单独存放
|   `-- ...
|-- docs/             文档
|   |-- software/     飞控文档，形式为 git submodule
|   `-- hardware/     硬件文档
|-- scripts/          长期复用工具
`-- temp/             一次性脚本、临时记录等物的暂存区
```

## 2. 工作区规范

### 2.1 目录职责

- 各子目录规则见其 `AGENTS.md`；子目录中的操作规范以其 `AGENTS.md` 为准。
- 数据布局见 `data/AGENTS.md`，文档与子模组规则见 `docs/AGENTS.md`，常用工具见 `scripts/AGENTS.md`，暂存区见 `temp/AGENTS.md`。

### 2.2 Git 操作

- 禁止 `git clean -fdx` / `git clean -fX`。
- 禁止 `git add -A` / `git checkout -- .`。

### 2.3 Python 环境

- Python 工具统一使用 conda 环境 `myenv`，环境由 Freeside 管理；需要安装新包时读取 Freeside 规范。
- Python 统一使用 `%USERPROFILE%\anaconda3\envs\myenv\python.exe`；PATH 上的 `python` 是 Windows Store 占位。

## 2.4. 行为约束

- 评估时，所有假设的失败模式，都必须对应真实生产环境中，可真实产生的问题。
- 只存在于假设中，或依赖极端前提条件，非真实生产环境中可产生的失败模式，不予考虑。
