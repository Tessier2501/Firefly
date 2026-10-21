"""针对性遥测诊断：从 Mission Planner 日志提取健康位、参数变更、GPS、磁罗盘、航向时间线。"""

from __future__ import annotations

import argparse
import contextlib
import io
import math
import struct
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

try:
    from pymavlink import mavutil
except ImportError as exc:  # 本机 PATH 里的 python 是 Store 存根，必须用 conda myenv
    raise SystemExit(
        "缺少 pymavlink，用 conda myenv 运行：conda run -n myenv --no-capture-output "
        "python scripts/telemetry-check.py"
    ) from exc

TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parent

mavutil.set_dialect("ardupilotmega")

SENSOR_NAMES = {
    value: name.replace("MAV_SYS_STATUS_SENSOR_", "")
    for value, name in sorted(
        (getattr(mavutil.mavlink, name), name)
        for name in dir(mavutil.mavlink)
        if name.startswith("MAV_SYS_STATUS_SENSOR_") and not name.endswith("_ENUM_END")
    )
}

MAG_STREAMS = ("RAW_IMU", "SCALED_IMU2", "SCALED_IMU3")


def resolve_cli_path(value: str | Path) -> Path:
    """解析命令行路径：相对路径以仓库根为基准。"""
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def open_log(path: Path):
    """返回 (连接, 是否带时间戳)。.rlog 是无时间戳的 MAVLink 裸流。"""
    mavutil.set_dialect("ardupilotmega")
    head = path.open("rb").read(16)
    timestamped = len(head) >= 9 and head[8] in (0xFD, 0xFE)
    conn = mavutil.mavlogfile(str(path), notimestamps=not timestamped)
    return conn, timestamped


def sensor_names(mask: int) -> str:
    """把传感器位掩码转成名字列表。"""
    parts = [SENSOR_NAMES[bit] for bit in sorted(SENSOR_NAMES) if mask & bit]
    return ",".join(parts) if parts else "-"


def fmt_time(rel: float | None) -> str:
    return "-" if rel is None else f"{rel:7.1f}s"


def _param_name(value) -> str:
    if isinstance(value, bytes):
        value = value.decode(errors="ignore")
    return value.rstrip("\x00")


@dataclass
class Telemetry:
    path: str
    timestamped: bool
    duration: float | None = None
    health: list[tuple[float | None, int, int]] = field(default_factory=list)
    param_sets: list[tuple[float | None, str, float]] = field(default_factory=list)
    param_changes: list[tuple[float | None, str, float, float]] = field(default_factory=list)
    gps: dict[str, list[tuple[float | None, int, int, int, int, int, int]]] = field(default_factory=dict)
    mag: dict[str, list[tuple[float | None, int, int, int]]] = field(default_factory=dict)
    yaw_samples: list[tuple[float | None, float | None, float | None, float | None]] = field(
        default_factory=list
    )


def collect(path: Path, interval: float) -> Telemetry:
    """单遍解析日志，收集各诊断视图需要的序列。"""
    conn, timestamped = open_log(path)
    data = Telemetry(path=str(path), timestamped=timestamped)
    t0: float | None = None
    seen_params: dict[str, float] = {}
    step = max(interval, 0.5)
    next_sample = 0.0
    last_yaw: float | None = None
    last_gyro_z: float | None = None
    last_mag: dict[str, tuple[int, int, int]] = {}

    while True:
        msg = conn.recv_match()
        if msg is None:
            break
        rel: float | None = None
        if timestamped:
            if t0 is None:
                t0 = msg._timestamp
            rel = round(msg._timestamp - t0, 2)
            data.duration = rel
        msg_type = msg.get_type()

        if msg_type == "SYS_STATUS":
            data.health.append(
                (
                    rel,
                    int(msg.onboard_control_sensors_present),
                    int(msg.onboard_control_sensors_health),
                )
            )
        elif msg_type == "PARAM_SET":
            data.param_sets.append((rel, _param_name(msg.param_id), msg.param_value))
        elif msg_type == "PARAM_VALUE":
            name = _param_name(msg.param_id)
            old = seen_params.get(name)
            if old is None:
                seen_params[name] = msg.param_value
            elif abs(old - msg.param_value) > 1e-9:
                data.param_changes.append((rel, name, old, msg.param_value))
                seen_params[name] = msg.param_value
        elif msg_type in ("GPS_RAW_INT", "GPS2_RAW"):
            key = "gps1" if msg_type == "GPS_RAW_INT" else "gps2"
            data.gps.setdefault(key, []).append(
                (rel, msg.fix_type, msg.satellites_visible, msg.eph, msg.lat, msg.lon, msg.alt)
            )
        elif msg_type in MAG_STREAMS:
            last_mag[msg_type] = (msg.xmag, msg.ymag, msg.zmag)
            data.mag.setdefault(msg_type, []).append((rel, msg.xmag, msg.ymag, msg.zmag))
            if msg_type == "RAW_IMU":
                last_gyro_z = msg.zgyro
        elif msg_type == "ATTITUDE":
            last_yaw = math.degrees(msg.yaw)

        if timestamped and rel is not None and rel >= next_sample:
            heading: float | None = None
            for stream in MAG_STREAMS:
                xmag, ymag, _ = last_mag.get(stream, (0, 0, 0))
                if any((xmag, ymag)):
                    heading = math.degrees(math.atan2(ymag, xmag))
                    break
            data.yaw_samples.append((rel, last_yaw, heading, last_gyro_z))
            next_sample += step

    conn.close()
    return data


def view_health(data: Telemetry) -> None:
    previous: int | None = None
    for rel, present, health in data.health:
        if health == previous:
            continue
        print(f"{fmt_time(rel)} health=0x{health:08x} unhealthy={sensor_names(present & ~health)}")
        previous = health
    if not data.health:
        print("（无 SYS_STATUS）")


def view_param_changes(data: Telemetry) -> None:
    for rel, name, value in data.param_sets:
        print(f"{fmt_time(rel)} PARAM_SET    {name} = {value:g}")
    for rel, name, old, new in data.param_changes:
        print(f"{fmt_time(rel)} PARAM_CHANGE {name}: {old:g} -> {new:g}")
    if not data.param_sets and not data.param_changes:
        print("（无 PARAM_SET 或参数变化）")


def view_gps(data: Telemetry) -> None:
    for key in ("gps1", "gps2"):
        samples = data.gps.get(key) or []
        if not samples:
            continue
        print(f"[{key}] 样本 {len(samples)}")
        last_fix: int | None = None
        for rel, fix, sats, eph, _lat, _lon, _alt in samples:
            if fix != last_fix:
                print(f"{fmt_time(rel)} fix_type={fix} sats={sats} eph={eph}")
                last_fix = fix
        sats = [s for _, _, s, _, _, _, _ in samples if s != 255]
        eph = [e for _, _, _, e, _, _, _ in samples if e < 65535]
        if sats:
            print(f"  sats max={max(sats)}")
        if eph:
            print(f"  eph min={min(eph)} cm")
        first_3d = next((s for s in samples if s[1] == 3), None)
        if first_3d:
            rel, _fix, _sats, eph, lat, lon, alt = first_3d
            print(
                f"  first 3D fix: {fmt_time(rel)} lat={lat / 1e7:.7f} lon={lon / 1e7:.7f} "
                f"alt={alt / 1000:.1f} m eph={eph} cm"
            )


def view_mag(data: Telemetry) -> None:
    found = False
    for stream in MAG_STREAMS:
        samples = data.mag.get(stream) or []
        if not samples:
            continue
        found = True
        nonzero = [sample for sample in samples if any(sample[1:])]
        print(f"[{stream}] n={len(samples)} nonzero={len(nonzero)}")
        if not nonzero:
            continue
        for axis, label in ((1, "x"), (2, "y"), (3, "z")):
            values = [sample[axis] for sample in nonzero]
            print(f"  {label}: {min(values)}..{max(values)}")
        field = [math.sqrt(sample[1] ** 2 + sample[2] ** 2 + sample[3] ** 2) for sample in nonzero]
        print(f"  |B|: {min(field):.1f}..{max(field):.1f} mean={sum(field) / len(field):.1f}")
        headings = [math.degrees(math.atan2(sample[2], sample[1])) for sample in nonzero]
        print(f"  atan2(y,x): range={max(headings) - min(headings):.1f} deg")
    if not found:
        print("（无磁数据）")


def view_yaw(data: Telemetry) -> None:
    if not data.timestamped:
        print("（无时间戳日志，跳过航向采样；该视图需要 .tlog）")
        return
    for rel, yaw, heading, gyro_z in data.yaw_samples:
        yaw_text = "-" if yaw is None else f"{yaw:7.1f}"
        heading_text = "-" if heading is None else f"{heading:7.1f}"
        gyro_text = "-" if gyro_z is None else f"{gyro_z:6.0f}"
        print(f"{fmt_time(rel)} yaw={yaw_text} mag_heading={heading_text} gyro_z={gyro_text}")


def selftest() -> int:
    """用合成 .tlog/.rlog 自测解析与各视图，返回 0 表示通过."""
    mavutil.set_dialect("ardupilotmega")
    mav = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
    frames: list[tuple[float, bytes]] = []

    def add(rel: float, frame) -> None:
        frames.append((rel, frame.pack(mav)))

    add(0.0, mav.heartbeat_encode(2, 3, 0, 0, 4))
    add(0.0, mav.sys_status_encode(0x3F, 0x3F, 0x2B, 100, 0, -1, -1, 0, 0, 0, 0, 0, 0))
    add(1.0, mav.gps_raw_int_encode(0, 0, 0, 0, 0, 65535, 65535, 0, 0, 0))
    add(
        2.0,
        mav.gps_raw_int_encode(
            0, 3, 30_028_791, 119_971_677, 17_520, 200, 300, 0, 0, 9
        ),
    )
    add(2.0, mav.param_value_encode(b"PARAM_A", 1.0, 9, 1, 0))
    add(3.0, mav.param_value_encode(b"PARAM_A", 2.0, 9, 1, 0))
    add(3.0, mav.param_set_encode(1, 1, b"PARAM_B", 5.0, 9))
    add(4.0, mav.attitude_encode(4_000, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0))
    add(4.0, mav.raw_imu_encode(4_000_000, 0, 0, -1000, 0, 0, 10, 100, 200, 400))
    add(5.0, mav.sys_status_encode(0x3F, 0x3F, 0x3F, 100, 0, -1, -1, 0, 0, 0, 0, 0, 0))

    tlog_bytes = b"".join(
        struct.pack(">Q", 1_700_000_000_000_000 + int(rel * 1_000_000)) + frame
        for rel, frame in frames
    )
    rlog_bytes = b"\x00" * 16 + b"".join(frame for _, frame in frames)

    with tempfile.TemporaryDirectory() as tmp:
        tlog = Path(tmp) / "selftest.tlog"
        tlog.write_bytes(tlog_bytes)
        data = collect(tlog, interval=5.0)
        assert data.timestamped
        assert len(data.health) == 2, data.health
        first = data.health[0]
        assert first[1] & ~first[2] & 4, "3D_MAG 应为不健康"
        assert [(change[1], change[3]) for change in data.param_changes] == [("PARAM_A", 2.0)], (
            data.param_changes
        )
        assert data.param_sets and data.param_sets[0][1] == "PARAM_B"
        assert data.gps["gps1"][-1][1] == 3
        assert data.mag["RAW_IMU"], data.mag
        assert data.yaw_samples, data.yaw_samples

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            view_health(data)
            view_param_changes(data)
            view_gps(data)
            view_mag(data)
            view_yaw(data)
        text = out.getvalue()
        for expected in ("3D_MAG", "PARAM_CHANGE", "fix_type=3", "first 3D fix", "|B|", "yaw="):
            assert expected in text, (expected, text)

        rlog = Path(tmp) / "selftest.rlog"
        rlog.write_bytes(rlog_bytes)
        raw = collect(rlog, interval=5.0)
        assert not raw.timestamped
        assert raw.health and raw.gps["gps1"][-1][1] == 3

    print("selftest 通过：.tlog/.rlog 识别、健康位/参数变更/GPS/磁数据/航向采样解析正常")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="针对性遥测诊断：健康位、参数变更、GPS、磁罗盘、航向时间线"
    )
    parser.add_argument("log", nargs="?", help="日志路径（.tlog 带时间戳 / .rlog 无时间戳）")
    parser.add_argument("--health", action="store_true", help="SYS_STATUS 传感器健康位变化")
    parser.add_argument("--param-changes", action="store_true", help="PARAM_SET 与参数值变化时间线")
    parser.add_argument("--gps", action="store_true", help="GPS fix/星数/eph 变化与首个 3D fix")
    parser.add_argument("--mag", action="store_true", help="RAW_IMU/SCALED_IMU2/3 磁数据统计")
    parser.add_argument("--yaw", action="store_true", help="航向/磁航向/陀螺 Z 采样时间线")
    parser.add_argument("--all", action="store_true", help="输出全部诊断视图")
    parser.add_argument("--interval", type=float, default=5.0, help="航向视图采样间隔（秒，默认 5）")
    parser.add_argument("--selftest", action="store_true", help="用合成日志自测（不读文件）")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.log:
        parser.error("需要日志路径（或 --selftest）")

    views = []
    if args.all or args.health:
        views.append(view_health)
    if args.all or args.param_changes:
        views.append(view_param_changes)
    if args.all or args.gps:
        views.append(view_gps)
    if args.all or args.mag:
        views.append(view_mag)
    if args.all or args.yaw:
        views.append(view_yaw)
    if not views:
        parser.error("至少指定一个诊断项：--health/--param-changes/--gps/--mag/--yaw/--all")

    try:
        data = collect(resolve_cli_path(args.log), args.interval)
    except Exception as exc:  # 日志读取失败：明确报错并给出退出码
        print(f"失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"log: {data.path}")
    print(f"format: {'tlog' if data.timestamped else 'raw (无时间戳)'}")
    if data.duration is not None:
        print(f"duration: {data.duration:.1f} s")
    for view in views:
        print()
        print(f"## {view.__name__[5:]}")
        view(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
