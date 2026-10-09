# scripts

长期使用和维护的工具目录. 只放会重复使用的工具; 一次性脚本与实验代码放 `temp/`.

## 环境

- Python 统一使用 conda 环境 `myenv`, 由 Freeside 管理, 本目录不维护依赖清单.
- Windows 下用 `python` 调用; 需要机器可读输出时先设置 `$env:PYTHONIOENCODING = 'utf-8'`, myenv 默认 stdout 为 GBK.
- 串口工具运行前先关闭 Mission Planner 与 QGroundControl, 避免端口被占用.

## 现有工具

| 工具 | 用途 | 离线自测 |
|---|---|---|
| `ubx_probe.py` | 直连 u-blox 模块: MON-VER 固件版本 (真版本在扩展串的 `FWVER=HPG x.y`), CFG-GNSS 星座配置, NAV-RELPOSNED 移动基线相对解 | `python scripts\ubx_probe.py --selftest` |
| `ports-probe.py` | 串口链路只读探测: 判断 COM 口上是 MAVLink 飞控还是其它设备, 只有收到 HEARTBEAT 才算通 | `python scripts\ports-probe.py --selftest` |
| `localize-images.py` | 把 URL 转换产物的远程图片下载到 `images/` 并改写 `full.md` / `main.html` / `content_list.json` 的引用 | `python scripts\localize-images.py --selftest` |

常用用法:

```powershell
python scripts\ubx_probe.py --port COM6 --baud 460800
python scripts\ubx_probe.py --port COM6 --poll relposned
python scripts\ports-probe.py --list
python scripts\ports-probe.py --all --seconds 5
python scripts\localize-images.py docs\hardware\CUAV
python scripts\localize-images.py --dry-run docs\hardware\CUAV
```