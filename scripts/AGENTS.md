# scripts

长期复用工具目录。只放会重复使用的工具；一次性脚本与实验代码放 `temp/`。

## 1. 环境

- PATH 中的 `python` 是 Windows Store 零字节存根（退出码 9009），统一通过 `conda` 的绝对路径调用：

```powershell
& "$env:USERPROFILE\anaconda3\Scripts\conda.exe" run -n myenv --no-capture-output python scripts\<工具>.py
```

- `--no-capture-output` 必须保留，否则中文输出按控制台代码页解码会乱码。
- 需要机器可读输出时先设置 `$env:PYTHONIOENCODING = 'utf-8'`。
- 串口工具运行前关闭 Mission Planner 与 QGroundControl，或要求用户释放串口。

## 2. 当前工具

- `ubx_probe.py`：直连 u-blox，读 MON-VER、CFG-GNSS、NAV-RELPOSNED；`--selftest` 无硬件自测。
- `ports-probe.py`：探测串口链路（MAVLink / SLCAN / 静默），`--out` 指定机架目录内的 Markdown 报告文件；`--selftest` 自测；`--poke` 会先发 GCS 心跳，默认关闭。
- `localize-images.py`：下载 URL 转换产物的远程图片到 `images/`，改写 `full.md`、`main.html`、`content_list.json` 的引用；`--dry-run` 预览。
- `clean-markdown.py`：清洗 MinerU 产物：删除与 `full.md` 等价的 `MinerU_markdown_*.md` 副本，还原目录与标题层级，覆盖前校验正文不丢失；`--dry-run` 预览。

常用用法：

```powershell
$py = "$env:USERPROFILE\anaconda3\Scripts\conda.exe"
& $py run -n myenv --no-capture-output python scripts\ubx_probe.py --port COM6 --baud 460800
& $py run -n myenv --no-capture-output python scripts\ports-probe.py --all --seconds 5 --out data\frame_2026_10_16_01\2026_10_16_1703_ports-probe.md
& $py run -n myenv --no-capture-output python scripts\localize-images.py --dry-run docs\hardware\CUAV
& $py run -n myenv --no-capture-output python scripts\clean-markdown.py --dry-run docs\hardware\SIYI
```

## 3. 约定

- 写盘工具必须显式指定输出路径；不改原始数据与 `docs/hardware` 原始产物。
- 脚本输出数据与事实，不输出判断、建议或结论。
- 仅 `localize-images.py` 联网，其余脚本离线运行。
- 新增长期工具：提供 `--help`、`--dry-run` 或 `--selftest`。