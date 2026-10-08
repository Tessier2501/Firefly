"""只读探测串口链路: 判定某个 COM 口上是 MAVLink (飞控) 还是 SLCAN/其它.

背景: CUAV V5+ 的 USB 复合设备对每个飞控暴露两个 CDC 口 (Windows 命名为
`ArduPilot MAVLink` 与 `ArduPilot SLCAN`). 排查"连不上"时, 需要确认
(a) 哪个口真的在吐 MAVLink 心跳, (b) 是否必须断言 DTR 才会开始输出.

本脚本只读取, 不向端口写入任何数据.

用法:
    python ports-probe.py --list
    python ports-probe.py --all --seconds 5
    python ports-probe.py --ports COM6,COM7 --seconds 5 --dtr
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# MAVLink 2 方言 (v20) 必须在导入 pymavlink 之前选定, 否则消息的扩展字段不可见
# (与 parse_tlog.py 同因: v10 方言里 SERVO_OUTPUT_RAW 没有 9-16 路).
os.environ.setdefault("MAVLINK20", "1")

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:  # pragma: no cover - 环境缺失时必须显式失败
    raise SystemExit(
        "缺少 pyserial, 请先在本环境安装: python -m pip install pyserial"
    ) from exc

UAV_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = UAV_ROOT / "analysis" / "port_probe.md"
TOOL_DIR = Path(__file__).resolve().parent


def resolve_cli_path(value: str | Path) -> Path:
    """解析命令行路径: 相对路径以 tools 目录为基准, 不随当前工作目录变化."""
    path = Path(value)
    return path.resolve() if path.is_absolute() else (TOOL_DIR / path).resolve()

MAVLINK_STX_V1 = 0xFE
MAVLINK_STX_V2 = 0xFD
PRINTABLE_MIN = 32
PRINTABLE_MAX = 126


@dataclass
class PortInfo:
    """系统上的一个串口."""

    device: str
    description: str
    hwid: str


@dataclass
class ProbeResult:
    """一个端口的探测结果."""

    device: str
    description: str
    dtr: bool
    opened: bool = False
    error: str = ""
    raw_bytes: int = 0
    v1_markers: int = 0
    v2_markers: int = 0
    decoded_total: int = 0
    bad_bytes: int = 0
    decode_error: str = ""
    decoded_types: Dict[str, int] = field(default_factory=dict)
    heartbeats: List[str] = field(default_factory=list)
    first_bytes_hex: str = ""
    text_sample: str = ""
    sent_bytes: int = 0
    fb_markers: int = 0

    @property
    def verdict(self) -> str:
        """给出人类可读的判定.

        注意: "解码失败"与"收到 HEARTBEAT"必须分开报告. 旧版把解码异常文本塞进
        heartbeats 列表, 于是任何解不开的口都被误判为 "MAVLink 飞控" (2026-09-21 踩过).
        """
        if not self.opened:
            return f"打开失败: {self.error}"
        if self.raw_bytes == 0:
            return "静默 (读不到任何字节)"
        if self.heartbeats:
            suffix = f", 坏字节 {self.bad_bytes}" if self.bad_bytes else ""
            return f"MAVLink 飞控 (收到 HEARTBEAT{suffix})"
        if self.decode_error:
            return f"收到 {self.raw_bytes} 字节, 解析报错: {self.decode_error}"
        if self.decoded_total > 0:
            return f"MAVLink 流量 (解码 {self.decoded_total} 条, 但无 HEARTBEAT)"
        return f"收到 {self.raw_bytes} 字节, 但解不出 MAVLink (坏字节 {self.bad_bytes})"


def list_serial_ports() -> List[PortInfo]:
    """列出当前系统上的串口."""
    return [
        PortInfo(device=item.device, description=item.description or "", hwid=item.hwid or "")
        for item in list_ports.comports()
    ]


def decode_mavlink(raw: bytes) -> Tuple[int, int, str, Dict[str, int], List[str]]:
    """逐字节解码, 返回 (解码条数, 坏字节数, 最后一条错误, 类型计数, 心跳描述).

    两条 pymavlink 行为必须遵守 (2026-09-21 实测, 否则解码恒为 0):
    1. `parse_char()` 一次只"输入"一个字节, 完整消息要用**空串**再调一次把它取出来;
    2. 非法起始字节会抛 MAVError, 且坏字节**仍留在内部缓冲**里 -- 不手动清空,
       解析器会永久卡在它上面, 后面的好帧再也解不出来.

    逐字节(而不是 `parse_buffer`)也是为了第 2 点: 现场串口流里常常夹着非 MAVLink 数据.
    """
    from pymavlink import mavutil

    parser = mavutil.mavlink.MAVLink(None)
    types: Dict[str, int] = {}
    heartbeats: List[str] = []
    total = 0
    bad = 0
    error = ""

    def handle(message: object) -> None:
        """统计一条已解出的消息."""
        nonlocal total
        message_type = message.get_type()
        if message_type == "BAD_DATA":
            return
        total += 1
        types[message_type] = types.get(message_type, 0) + 1
        if message_type != "HEARTBEAT":
            return
        armed = bool(
            int(getattr(message, "base_mode", 0))
            & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        )
        heartbeats.append(
            f"sysid={message.get_srcSystem()} compid={message.get_srcComponent()}"
            f" type={getattr(message, 'type', -1)}"
            f" autopilot={getattr(message, 'autopilot', -1)} armed={armed}"
        )

    for byte in raw:
        try:
            message = parser.parse_char(bytes([byte]))
        except Exception as exc:  # 坏字节: 记账, 清缓冲, 继续吃后面的数据
            bad += 1
            error = f"{type(exc).__name__}: {exc}"
            # 只清 buf: 实测再动 buf_len/buf_index 会让解析器错位, 反而解不出后续好帧.
            # 另外坏字节数只是下界 -- 连续坏字节里只有第一个会报错; 关键是后续好帧仍能解出.
            parser.buf = bytearray()
            continue
        while message is not None:
            handle(message)
            message = parser.parse_char(b"")
    return total, bad, error, types, heartbeats


def build_poke_frames() -> List[bytes]:
    """构造用于唤醒飞控的 GCS 帧 (MAVLink2 与 MAVLink1 各一版心跳 + 一次能力查询).

    动机: QGC 能"踹门"而只读探测唤不醒飞控, 差别就在于 QGC 会**主动发**心跳.
    这里只复刻这一步, 不改任何参数、不做任何设置.
    """
    from pymavlink import mavutil

    sender = mavutil.mavlink.MAVLink(None, srcSystem=255, srcComponent=190)
    heartbeat = sender.heartbeat_encode(
        mavutil.mavlink.MAV_TYPE_GCS,
        mavutil.mavlink.MAV_AUTOPILOT_INVALID,
        0,
        0,
        mavutil.mavlink.MAV_STATE_ACTIVE,
    )
    frames = [
        heartbeat.pack(sender),
        heartbeat.pack(sender, force_mavlink1=True),  # 再补一版 MAVLink1: 飞控可能只对其中一种领情
    ]
    frames.append(
        sender.command_long_encode(
            255,
            190,
            mavutil.mavlink.MAV_CMD_REQUEST_AUTOPILOT_CAPABILITIES,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
        ).pack(sender)
    )
    return frames


def probe_port(
    info: PortInfo,
    seconds: float,
    baud: int,
    dtr: bool,
    poke_frames: Optional[List[bytes]] = None,
) -> ProbeResult:
    """打开端口读取若干秒, 返回探测结果.

    默认**只读** (不向端口写任何数据). 只有显式给出 poke_frames (`--poke`) 时才会先写几个帧 --
    因为飞控的 USB CDC 可能只在"主机发过数据"之后才开始正常输出 MAVLink.
    """
    result = ProbeResult(device=info.device, description=info.description, dtr=dtr)
    try:
        handle = serial.Serial(
            info.device, baudrate=baud, timeout=0.2, rtscts=False, dsrdtr=False
        )
    except serial.SerialException as exc:
        result.error = str(exc)
        return result
    try:
        result.opened = True
        handle.dtr = dtr
        handle.rts = False
        if poke_frames:
            for frame in poke_frames:
                handle.write(frame)
                handle.flush()
                result.sent_bytes += len(frame)
                time.sleep(0.2)
            time.sleep(0.5)  # 给飞控一点反应时间
        deadline = time.monotonic() + seconds
        chunks: List[bytes] = []
        while time.monotonic() < deadline:
            chunk = handle.read(4096)
            if chunk:
                chunks.append(chunk)
    finally:
        handle.close()
    raw = b"".join(chunks)
    result.raw_bytes = len(raw)
    result.v1_markers = raw.count(bytes([MAVLINK_STX_V1]))
    result.v2_markers = raw.count(bytes([MAVLINK_STX_V2]))
    result.first_bytes_hex = raw[:32].hex(" ")
    result.fb_markers = raw.count(bytes([0xFB]))
    result.text_sample = "".join(
        chr(byte) for byte in raw[:160] if PRINTABLE_MIN <= byte <= PRINTABLE_MAX
    )
    if raw:
        total, bad, error, types, heartbeats = decode_mavlink(raw)
        result.decoded_total = total
        result.bad_bytes = bad
        result.decode_error = error
        result.decoded_types = types
        result.heartbeats = heartbeats
    return result


def render_result(result: ProbeResult) -> List[str]:
    """渲染一个端口的探测结果."""
    types = ", ".join(
        f"{name}x{count}"
        for name, count in sorted(
            result.decoded_types.items(), key=lambda item: -item[1]
        )[:8]
    )
    lines = [
        f"- `{result.device}` ({result.description or '无描述'}) DTR={result.dtr}",
        f"  - 判定: {result.verdict}",
        f"  - 原始字节 {result.raw_bytes}, 0xFE 标记 {result.v1_markers},"
        f" 0xFD 标记 {result.v2_markers}, 解码 {result.decoded_total} 条,"
        f" 坏字节 {result.bad_bytes}",
    ]
    if result.first_bytes_hex:
        lines.append(f"  - 头 32 字节: {result.first_bytes_hex}")
    if result.sent_bytes:
        lines.append(f"  - 已发送 {result.sent_bytes} 字节 (--poke 的 GCS 心跳与能力查询)")
    if result.fb_markers:
        lines.append(f"  - 0xFB 起始字节 {result.fb_markers} 个")
    if types:
        lines.append(f"  - 解码到的类型: {types}")
    for item in result.heartbeats[:5]:
        lines.append(f"  - HEARTBEAT: {item}")
    if result.text_sample:
        lines.append(f"  - 可打印样本: {result.text_sample!r}")
    return lines


def selftest() -> int:
    """自测: 用合成的 MAVLink 帧验证解码与判定逻辑 (不打开任何串口).

    回归点: 旧版把"解码异常"当成"收到心跳", 于是任何口都被判成 MAVLink 飞控.
    """
    from pymavlink import mavutil

    sender = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=1)
    frame = sender.heartbeat_encode(2, 3, 0, 0, 0).pack(sender)
    total, bad, _error, types, heartbeats = decode_mavlink(frame)
    total_bad, bad_bad, _e, _t, _h = decode_mavlink(b"\xff\xff" + frame + frame)
    checks = [
        ("纯 MAVLink 帧解出 1 条", total == 1),
        ("HEARTBEAT 被识别", len(heartbeats) == 1 and types.get("HEARTBEAT") == 1),
        ("坏字节之后连解两帧 (证明没卡死)", total_bad == 2),
        (f"坏字节被计数 (下界, 实测 {bad_bad})", bad_bad >= 1 and bad == 0),
        ("空数据不报错", decode_mavlink(b"")[0] == 0),
    ]
    ok = True
    for label, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'}: {label}")
        ok = ok and passed
    poke = build_poke_frames()
    starts = [frame[:1].hex() for frame in poke]
    poke_ok = (
        len(poke) >= 2
        and all(start in ("fd", "fe") for start in starts)
        and decode_mavlink(poke[0])[0] == 1
    )
    print(f"  {'PASS' if poke_ok else 'FAIL'}: --poke 帧可用 (起始字节 {starts})")
    ok = ok and poke_ok
    broken = ProbeResult(
        device="X", description="", dtr=True, opened=True, raw_bytes=10, bad_bytes=10
    )
    errored = ProbeResult(
        device="X",
        description="",
        dtr=True,
        opened=True,
        raw_bytes=10,
        bad_bytes=10,
        decode_error="MAVError: invalid MAVLink prefix",
    )
    verdict_ok = "飞控" not in broken.verdict and "飞控" not in errored.verdict
    print(f"  {'PASS' if verdict_ok else 'FAIL'}: 解不出 MAVLink 时不得判成飞控")
    ok = ok and verdict_ok
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    """命令行入口: 列出或探测串口, 并写出 Markdown 报告."""
    parser = argparse.ArgumentParser(
        description="只读探测串口链路 (MAVLink / SLCAN / 静默)."
    )
    parser.add_argument("--list", action="store_true", help="只列出串口")
    parser.add_argument("--ports", default="", help="逗号分隔的端口名列表")
    parser.add_argument("--all", action="store_true", help="探测全部串口")
    parser.add_argument("--seconds", type=float, default=5.0, help="每个端口读取的秒数")
    parser.add_argument("--baud", type=int, default=115200, help="打开端口用的波特率")
    parser.add_argument("--dtr", dest="dtr", action="store_true", help="打开后断言 DTR (默认)")
    parser.add_argument("--no-dtr", dest="dtr", action="store_false", help="打开后不断言 DTR")
    parser.set_defaults(dtr=True)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Markdown 输出路径")
    parser.add_argument(
        "--selftest", action="store_true", help="用合成 MAVLink 帧自测解码与判定 (不碰串口)"
    )
    parser.add_argument(
        "--poke",
        action="store_true",
        help="先向端口发送 GCS 心跳再读 (会写口; 用于唤醒只读探测唤不醒的飞控)",
    )
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    available = list_serial_ports()
    if args.list:
        print("当前串口:")
        for info in available:
            print(f"  {info.device}: {info.description} | {info.hwid}")
        if not available:
            print("  (没有发现任何串口)")
        return 0

    if args.all:
        targets = available
        if not targets:
            raise SystemExit("没有发现任何串口, 请先插上飞控再跑; 或先用 --list 确认")
    else:
        wanted = [name.strip() for name in args.ports.split(",") if name.strip()]
        if not wanted:
            raise SystemExit("请用 --ports COMx,COMy 指定端口, 或用 --all / --list")
        by_device = {item.device.upper(): item for item in available}
        missing = [name for name in wanted if name.upper() not in by_device]
        if missing:
            print(f"警告: 以下端口当前不存在, 已跳过: {', '.join(missing)}")
        targets = [
            by_device[name.upper()] for name in wanted if name.upper() in by_device
        ]
        if not targets:
            raise SystemExit(
                "指定的端口都不存在. 当前串口: "
                + (", ".join(item.device for item in available) or "无")
            )

    poke_frames = build_poke_frames() if args.poke else None
    results: List[ProbeResult] = []
    for info in targets:
        print(
            f"探测 {info.device} ({args.seconds:g}s, DTR={args.dtr}"
            f"{', 先发 GCS 心跳' if poke_frames else ''}) ..."
        )
        result = probe_port(info, args.seconds, args.baud, args.dtr, poke_frames)
        results.append(result)
        print(f"  -> {result.verdict}")

    out_path = resolve_cli_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    if not out_path.exists():
        lines.extend([
            "# 串口探测结果",
            "",
            "每次运行追加一节, 最新一次在文件末尾 (便于对比 DTR 开/关等不同条件).",
            "",
        ])
    lines.extend([
        f"## 运行 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- 读取时长: {args.seconds:g}s/口, DTR={args.dtr}, 波特率 {args.baud}"
        " (USB CDC 下波特率不影响通信)",
        f"- poke: {'开启 (每个口先发 GCS 心跳与能力查询)' if args.poke else '关闭 (只读)'}",
        "- 当前串口:",
    ])
    for info in available:
        lines.append(f"  - `{info.device}`: {info.description} | {info.hwid}")
    if not available:
        lines.append("  - (无)")
    lines.append("")
    lines.append("- 探测结果:")
    for result in results:
        lines.extend(render_result(result))
    lines.append("")
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"已追加: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
