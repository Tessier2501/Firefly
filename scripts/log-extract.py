"""从 Mission Planner 遥测日志（.tlog / .rlog）提取固件身份、参数与关键时间序列。"""

from __future__ import annotations

import argparse
import io
import json
import struct
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

try:
    from pymavlink import mavutil
except ImportError as exc:  # 本机 PATH 里的 python 是 Store 存根，必须用 conda myenv
    raise SystemExit(
        "缺少 pymavlink，用 conda myenv 运行：conda run -n myenv --no-capture-output python scripts/log-extract.py"
    ) from exc

TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parent

MAV_MODE_FLAG_SAFETY_ARMED = 0x80
FW_TYPE_NAMES = {0: "dev", 64: "beta", 128: "rc", 192: "alpha", 255: "official"}


def resolve_cli_path(value: str | Path) -> Path:
    """解析命令行路径：相对路径以仓库根为基准。"""
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def decode_sw_version(value: int) -> str:
    major = (value >> 24) & 0xFF
    minor = (value >> 16) & 0xFF
    patch = (value >> 8) & 0xFF
    fw_type = value & 0xFF
    return f"{major}.{minor}.{patch} ({FW_TYPE_NAMES.get(fw_type, fw_type)})"


def open_log(path: Path):
    """返回 (连接, 是否带时间戳)。

    .tlog 每帧前有 8 字节大端时间戳；.rlog 是无时间戳的 MAVLink 裸流
    （首帧前有 16 字节头），必须用 notimestamps=True 读取。
    """
    mavutil.set_dialect("ardupilotmega")
    head = path.open("rb").read(16)
    timestamped = len(head) >= 9 and head[8] in (0xFD, 0xFE)
    # 直接用 mavlogfile：mavlink_connection 会把含冒号的绝对路径当成 UDP 地址。
    conn = mavutil.mavlogfile(str(path), notimestamps=not timestamped)
    return conn, timestamped


@dataclass
class LogData:
    path: str
    timestamped: bool
    duration_s: float | None = None
    messages: Counter = field(default_factory=Counter)
    params: dict[str, float] = field(default_factory=dict)
    param_count: int | None = None
    firmware: str = ""
    board_version: int | None = None
    modes: list[tuple[float | None, int]] = field(default_factory=list)
    arm_events: list[tuple[float | None, bool]] = field(default_factory=list)
    gps: dict[str, list[tuple[int, int, int]]] = field(default_factory=dict)
    battery: list[tuple[int, int]] = field(default_factory=list)
    rc: dict[int, tuple[int, int]] = field(default_factory=dict)
    servo: dict[int, tuple[int, int]] = field(default_factory=dict)
    statustext: list[tuple[float | None, str]] = field(default_factory=list)


def _bump(store: dict[int, tuple[int, int]], key: int, value: int) -> None:
    lo, hi = store.get(key, (value, value))
    store[key] = (min(lo, value), max(hi, value))


def extract(path: Path) -> LogData:
    conn, timestamped = open_log(path)
    data = LogData(path=str(path), timestamped=timestamped)
    t0: float | None = None
    last_mode: int | None = None
    last_armed: bool | None = None

    while True:
        msg = conn.recv_match()
        if msg is None:
            break
        msg_type = msg.get_type()
        data.messages[msg_type] += 1

        rel: float | None = None
        if timestamped:
            if t0 is None:
                t0 = msg._timestamp
            rel = round(msg._timestamp - t0, 1)
            data.duration_s = rel

        if msg_type == "PARAM_VALUE":
            param_id = msg.param_id
            if isinstance(param_id, bytes):
                param_id = param_id.decode(errors="ignore")
            data.params[param_id.rstrip("\x00")] = msg.param_value
            data.param_count = msg.param_count
        elif msg_type == "AUTOPILOT_VERSION":
            data.firmware = decode_sw_version(msg.flight_sw_version)
            data.board_version = msg.board_version
        elif msg_type == "STATUSTEXT":
            text = msg.text
            if isinstance(text, bytes):
                text = text.decode(errors="ignore")
            data.statustext.append((rel, text.rstrip("\x00")))
        elif msg_type == "HEARTBEAT" and msg.get_srcComponent() == 1:
            armed = bool(msg.base_mode & MAV_MODE_FLAG_SAFETY_ARMED)
            if armed != last_armed:
                data.arm_events.append((rel, armed))
                last_armed = armed
            if msg.custom_mode != last_mode:
                data.modes.append((rel, msg.custom_mode))
                last_mode = msg.custom_mode
        elif msg_type in ("GPS_RAW_INT", "GPS2_RAW"):
            key = "gps1" if msg_type == "GPS_RAW_INT" else "gps2"
            data.gps.setdefault(key, []).append(
                (msg.fix_type, msg.satellites_visible, msg.eph)
            )
        elif msg_type == "SYS_STATUS":
            data.battery.append((msg.voltage_battery, msg.current_battery))
        elif msg_type == "RC_CHANNELS":
            for channel in range(1, 9):
                _bump(data.rc, channel, getattr(msg, f"chan{channel}_raw", 0))
        elif msg_type == "SERVO_OUTPUT_RAW":
            for channel in range(1, 17):
                _bump(data.servo, channel, getattr(msg, f"servo{channel}_raw", 0))

    conn.close()
    return data


def _fmt_time(rel: float | None) -> str:
    return "-" if rel is None else f"{rel:.1f}s"


def print_summary(data: LogData) -> None:
    print(f"log: {data.path}")
    print(f"format: {'tlog' if data.timestamped else 'raw (无时间戳)'}")
    if data.duration_s is not None:
        print(f"duration: {data.duration_s:.1f} s")
    print(f"messages: {sum(data.messages.values())}")
    print(f"params: {len(data.params)}/{data.param_count if data.param_count is not None else '?'}")
    print(f"firmware: {data.firmware or '-'}")
    if data.board_version is not None:
        print(f"board_version: 0x{data.board_version:08x}")

    print("modes:")
    for rel, mode in data.modes:
        print(f"  {_fmt_time(rel)} mode={mode}")
    print("arm events:")
    for rel, armed in data.arm_events:
        print(f"  {_fmt_time(rel)} {'armed' if armed else 'disarmed'}")

    for key in ("gps1", "gps2"):
        samples = data.gps.get(key)
        if not samples:
            continue
        fixes = Counter(fix for fix, _, _ in samples)
        sats = [sats for _, sats, _ in samples]
        eph = [eph for _, _, eph in samples]
        print(
            f"{key}: fix={dict(sorted(fixes.items()))} "
            f"sats={min(sats)}..{max(sats)} eph={min(eph)}..{max(eph)}"
        )
    if data.battery:
        volts = [v for v, _ in data.battery]
        currents = [c for _, c in data.battery]
        print(f"battery: voltage={min(volts)}..{max(volts)} mV current={min(currents)}..{max(currents)} cA")
    for name, ranges in (("rc", data.rc), ("servo", data.servo)):
        parts = [f"{ch}:{lo}..{hi}" for ch, (lo, hi) in sorted(ranges.items()) if hi > 0]
        if parts:
            print(f"{name}: " + " ".join(parts))

    print("statustext:")
    for rel, text in data.statustext:
        print(f"  {_fmt_time(rel)} {text}")


def write_params_csv(data: LogData, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("param,value\n")
        for name in sorted(data.params):
            handle.write(f"{name},{data.params[name]}\n")


def write_json(data: LogData, path: Path) -> None:
    payload = {
        "path": data.path,
        "timestamped": data.timestamped,
        "duration_s": data.duration_s,
        "messages": dict(data.messages),
        "params": data.params,
        "param_count": data.param_count,
        "firmware": data.firmware,
        "board_version": data.board_version,
        "modes": data.modes,
        "arm_events": data.arm_events,
        "gps": data.gps,
        "battery": data.battery,
        "rc": data.rc,
        "servo": data.servo,
        "statustext": data.statustext,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)


def selftest() -> int:
    """用合成日志自测 .tlog 与 .rlog 两条读取路径，返回 0 表示通过."""
    from pymavlink.dialects.v20 import ardupilotmega as mavlink2

    frames: list[bytes] = []
    for build in (
        lambda m: m.heartbeat_send(
            mavlink2.MAV_TYPE_QUADROTOR,
            mavlink2.MAV_AUTOPILOT_ARDUPILOTMEGA,
            0,
            81,
            3,
        ),
        lambda m: m.param_value_send(b"TEST_PARAM", 1.5, 9, 1, 0),
        lambda m: m.autopilot_version_send(
            0,
            0x040701FF,
            0,
            0,
            0x00320000,
            [0] * 8,
            [0] * 8,
            [0] * 8,
            0,
            0,
            0,
            [0] * 18,
        ),
    ):
        buffer = io.BytesIO()
        build(mavlink2.MAVLink(buffer, srcSystem=1, srcComponent=1))
        frames.append(buffer.getvalue())

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "selftest.rlog"
        raw_path.write_bytes(b"\x00" * 16 + b"".join(frames))
        tlog_path = Path(tmp) / "selftest.tlog"
        tlog_path.write_bytes(
            b"".join(
                struct.pack(">Q", 1_700_000_000_000_000 + index * 100_000) + frame
                for index, frame in enumerate(frames)
            )
        )
        for path, expected_timestamped in ((raw_path, False), (tlog_path, True)):
            data = extract(path)
            assert data.timestamped == expected_timestamped, (path, data.timestamped)
            assert data.params.get("TEST_PARAM") == 1.5, data.params
            assert data.param_count == 1, data.param_count
            assert data.messages["HEARTBEAT"] == 1, data.messages
            assert data.firmware == "4.7.1 (official)", data.firmware

    print("selftest 通过：.tlog / .rlog 自动识别与参数、心跳、固件版本解析正常")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="从 Mission Planner 遥测日志提取固件身份、参数与关键时间序列"
    )
    parser.add_argument("log", nargs="?", help="日志路径（.tlog 带时间戳 / .rlog 无时间戳）")
    parser.add_argument("--params-csv", help="参数表输出 CSV 路径")
    parser.add_argument("--json", dest="json_out", help="完整提取结果输出 JSON 路径")
    parser.add_argument("--selftest", action="store_true", help="用合成日志自测（不读文件）")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.log:
        parser.error("需要日志路径（或 --selftest）")

    try:
        data = extract(resolve_cli_path(args.log))
    except Exception as exc:
        print(f"失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print_summary(data)
    if args.params_csv:
        path = resolve_cli_path(args.params_csv)
        write_params_csv(data, path)
        print(f"参数已写入 {path}")
    if args.json_out:
        path = resolve_cli_path(args.json_out)
        write_json(data, path)
        print(f"结果已写入 {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
