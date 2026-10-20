# data

调试数据与分析产物，按机架独立存放；除 `AGENTS.md` 外不纳入 git。

## 1. 结构

```text
data/
|-- AGENTS.md
`-- frame_<ID>/
    |-- notes.md    分析笔记
    `-- ...         原始数据和分析产物
```

- 机架 ID 格式为 `<YYYY_MM_DD>_<NN>`：格式无实际意义，仅视为标识符。
- ID 定下后不修改，不关联机上设备；飞控、电调、图传等按序列号 / UID 区分。
- 原始采集只增不改；分析产物可重新生成；分析笔记中过时或无用信息果断删除。
- 分析产物的命名规范为 `<YYYY_MM_DD_HHMM>_<主题>.md`。

## 2. 日志采集

- Mission Planner：`%USERPROFILE%\Documents\Mission Planner\config.xml` 的 `<logdirectory>`（默认 `%USERPROFILE%\Documents\Mission Planner\logs`），产出 `.tlog` / `.rlog`。
- QGroundControl：`%APPDATA%\QGroundControl\QGroundControl.ini` 的 `[General] savePath`；遥测 `.tlog` 在 `<savePath>\Telemetry`，应用日志 `AppLog.log` 在 `<savePath>\Logs`。
- 采集时仅复制，不改工具目录中的原文件。
- 文件按需采集，非必要不全量，采集后不重命名。
- 不采集缩略图（`.tlog.jpg`）等派生文件。
