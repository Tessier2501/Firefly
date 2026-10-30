# scripts

长期复用工具目录。只放会重复使用的工具；一次性脚本与实验代码放 `temp/`。

## 1. 环境

- PATH 中的 `python` 是 Windows Store 零字节存根（退出码 9009），统一通过 `conda` 的绝对路径调用：

```powershell
& "$env:USERPROFILE\anaconda3\Scripts\conda.exe" run -n myenv --no-capture-output python scripts\<工具>.py
```

- `--no-capture-output` 必须保留，否则中文输出按控制台代码页解码会乱码。
- 输出经管道或重定向时设置 `$env:PYTHONIOENCODING = 'utf-8'`；脚本写文件用 `open(..., encoding='utf-8')`。
- `conda run ... python -c "<多行>"` 会报 NotImplementedError；多行逻辑写成 .py 文件执行。
- 本机为 Windows PowerShell 5.1：重定向写文件用 `Out-File -Encoding utf8`，读回用 `Get-Content -Encoding utf8`；脚本写文件由 Python 直接写 UTF-8。
- 串口工具运行前关闭 Mission Planner 与 QGroundControl，或要求用户释放串口。

## 2. 当前工具

- `ubx_probe.py`：直连 u-blox，读 MON-VER、CFG-GNSS、NAV-RELPOSNED；`--selftest` 无硬件自测。
- `ports-probe.py`：探测串口链路，`--out` 指定机架目录内的 Markdown 报告文件；`--poke` 会先发 GCS 心跳，默认关闭；`--selftest` 自测。
- `localize-images.py`：下载 URL 转换产物的远程图片到 `images/`，改写 `full.md`、`main.html`、`content_list.json` 的引用；`clean-markdown.py` 内部会先调用它再删除 JSON，单独运行须在清洗之前；`--dry-run` 预览。
- `clean-markdown.py`：清洗转换产物：删除与 `full.md` 等价的 `MinerU_markdown_*.md` 副本，还原目录与标题层级，把 HTML 表展开为 2 空格缩进的多行，URL 产物先本地化远程图片，最后删除转换中间 JSON（`content_list`、`content_list_v2`、`model`、`block_list`、`layout`）；`--dry-run` 预览。
- `log-extract.py`：从 Mission Planner 日志提取固件身份、参数、模式与解锁事件、GPS/电池/RC/舵机量程、STATUSTEXT；`--selftest` 自测。
- `telemetry-check.py`：针对 Mission Planner 日志的时序诊断：传感器健康位变化（`--health`）、参数写入/变化时间线（`--param-changes`）、GPS fix/星数/eph 变化与首个定位（`--gps`）、磁数据统计（`--mag`）、航向/磁航向/陀螺采样（`--yaw`）、全部视图（`--all`）；`--interval` 调航向采样间隔；`--selftest` 自测。

常用用法：

```powershell
$py = "$env:USERPROFILE\anaconda3\Scripts\conda.exe"
& $py run -n myenv --no-capture-output python scripts\ubx_probe.py --port COM6 --baud 460800
& $py run -n myenv --no-capture-output python scripts\ports-probe.py --all --seconds 5 --out data\frame_2026_10_16_01\2026_10_16_1703_ports-probe.md
& $py run -n myenv --no-capture-output python scripts\localize-images.py --dry-run docs\hardware\CUAV
& $py run -n myenv --no-capture-output python scripts\clean-markdown.py --dry-run docs\hardware\SIYI
& $py run -n myenv --no-capture-output python scripts\log-extract.py "data\frame_2026_10_16_01\2026-10-13 16-34-01.tlog" --params-csv temp\params.csv
& $py run -n myenv --no-capture-output python scripts\telemetry-check.py "data\frame_2026_10_16_01\2026-10-21 15-53-08.tlog" --health --gps --mag
```

## 3. 约定

- 脚本输出数据与事实，不输出判断、建议或结论。
- 写盘工具必须显式指定输出路径；不改原始数据与 `docs/hardware` 原始产物。
- 新增长期工具：提供 `--help`、`--dry-run` 或 `--selftest`。