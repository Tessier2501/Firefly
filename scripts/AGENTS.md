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

常用用法:

```powershell
python scripts\ubx_probe.py --port COM6 --baud 460800
python scripts\ubx_probe.py --port COM6 --poll relposned
python scripts\ports-probe.py --list
python scripts\ports-probe.py --all --seconds 5
```

## 使用注意

- `ports-probe.py` 默认只读; 只有显式 `--poke` 才会向端口写 GCS 心跳.
- 移动基线 (GPS for Yaw) 需要 u-blox HPG >= 1.30, 推荐 1.32; 版本不足时的现象是 RTK 定位正常但 `GPS2_RAW.yaw` 恒 65535.
- 脚本内的目录默认值沿用原 UAV 调试工作区的相对结构, 暂不调整, 待后续评估. 例如 `ports-probe.py` 的默认 `--out` 现在解析为仓库根的 `analysis/port_probe.md`, 需要写到别处时显式传 `--out`.

## 约定

- 新增或修改工具后必须跑一遍 `--selftest`; 没有自测入口的能力不进入本目录.
- 硬件相关逻辑与解析逻辑分离, 保证无硬件时可自测; 失败即报错, 不静默继续.
- 新增工具先用单文件实现; 需要共享代码时再评估, 不预先抽象.