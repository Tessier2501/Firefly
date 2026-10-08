"""UBX 轮询探针: 直连 u-blox 模块, 读固件版本 / 星座配置 / 移动基线相对解.

模块上电后 (USB 或 USB-TTL 接 UART) 直接问它本人, 不经过飞控与 u-center:
  python .\\ubx_probe.py --port COM7 --baud 460800        # MON-VER + CFG-GNSS
  python .\\ubx_probe.py --port COM7 --poll relposned     # NAV-RELPOSNED (需 base+rover 成对工作)
  python .\\ubx_probe.py --selftest                       # 无硬件自测解析路径
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field

SYNC = b"\xb5\x62"

CLS_NAV, ID_RELPOSNED = 0x01, 0x3C
CLS_CFG, ID_CFG_GNSS = 0x06, 0x3E
CLS_MON, ID_MON_VER = 0x0A, 0x04

GNSS_NAMES = {
    0: "GPS", 1: "SBAS", 2: "Galileo", 3: "BeiDou", 4: "IMES",
    5: "QZSS", 6: "GLONASS", 7: "NavIC",
}
CARR_SOLN = {0: "none", 1: "float", 2: "fixed"}
RELPOSNED_FLAGS = {
    0: "gnssFixOK", 1: "diffSoln", 2: "relPosValid", 3: "carrSoln_lo", 4: "carrSoln_hi",
    5: "isMoving", 6: "refPosMiss", 7: "refObsMiss", 8: "relPosHeadingValid", 9: "relPosNormalized",
}


def ubx_frame(cls: int, mid: int, payload: bytes = b"") -> bytes:
    """组一帧 UBX (含 Fletcher 校验)."""
    body = bytes([cls, mid]) + len(payload).to_bytes(2, "little") + payload
    ck_a = ck_b = 0
    for byte in body:
        ck_a = (ck_a + byte) & 0xFF
        ck_b = (ck_b + ck_a) & 0xFF
    return SYNC + body + bytes([ck_a, ck_b])


def parse_frames(buf: bytes) -> list[tuple[int, int, bytes]]:
    """从字节流里切出所有校验通过的 UBX 帧, 返回 (cls, mid, payload)."""
    out: list[tuple[int, int, bytes]] = []
    i = 0
    while True:
        start = buf.find(SYNC, i)
        if start < 0 or start + 8 > len(buf):
            return out
        cls, mid = buf[start + 2], buf[start + 3]
        length = int.from_bytes(buf[start + 4:start + 6], "little")
        end = start + 6 + length + 2
        if end > len(buf):
            return out
        body = buf[start + 2:start + 6 + length]
        ck_a = ck_b = 0
        for byte in body:
            ck_a = (ck_a + byte) & 0xFF
            ck_b = (ck_b + ck_a) & 0xFF
        if (ck_a, ck_b) == (buf[end - 2], buf[end - 1]):
            out.append((cls, mid, buf[start + 6:start + 6 + length]))
        i = end


def _text(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


@dataclass
class MonVer:
    """MON-VER: 软件/硬件版本与全部扩展串 (HPG 版本藏在扩展里)."""

    sw_version: str
    hw_version: str
    extensions: list[str] = field(default_factory=list)

    @property
    def firmware(self) -> str:
        """从扩展串里挑出 FWVER/HPG 那一条, 挑不到返回空串."""
        for ext in self.extensions:
            if ext.upper().startswith("FWVER") or "HPG" in ext.upper():
                return ext
        return ""


def parse_mon_ver(payload: bytes) -> MonVer:
    """解析 MON-VER 载荷: 30 字节软件版本 + 10 字节硬件版本 + N x 30 字节扩展."""
    if len(payload) < 40:
        raise ValueError(f"MON-VER 载荷过短: {len(payload)} 字节")
    sw = _text(payload[0:30])
    hw = _text(payload[30:40])
    exts = [_text(payload[o:o + 30]) for o in range(40, len(payload) - 29, 30)]
    return MonVer(sw, hw, [e for e in exts if e])


def parse_cfg_gnss(payload: bytes) -> list[tuple[int, bool, int]]:
    """解析 CFG-GNSS: 返回 [(gnssId, 是否使能, 通道数)]."""
    if len(payload) < 4:
        raise ValueError("CFG-GNSS 载荷过短")
    count = payload[3]
    out: list[tuple[int, bool, int]] = []
    for n in range(count):
        off = 4 + n * 8
        if off + 8 > len(payload):
            break
        gnss_id = payload[off]
        max_ch = payload[off + 2]
        enable = bool(payload[off + 4] & 0x01)
        out.append((gnss_id, enable, max_ch))
    return out


@dataclass
class RelPosNed:
    """NAV-RELPOSNED: 移动基线相对解 (航向来自这里)."""

    version: int
    ref_station_id: int
    rel_pos_n: float
    rel_pos_e: float
    rel_pos_d: float
    rel_pos_length: float
    rel_pos_heading: float
    acc_heading: float
    flags: int

    def flag(self, bit: int) -> bool:
        return bool(self.flags & (1 << bit))

    @property
    def carr_soln(self) -> str:
        code = ((self.flags >> 3) & 0x03)
        return CARR_SOLN.get(code, f"?{code}")


def parse_relposned(payload: bytes) -> RelPosNed:
    """解析 NAV-RELPOSNED version 1 (F9P 实测 64 字节).

    字段偏移 (按实测 hex 逐字节核对): relPosN/E/D=8/12/16, relPosLength=20, relPosHeading=24,
    reserved2=28, relPosHPN/E/D/Length=32..35 (各 1 字节), accN/E/D/Length=36..51,
    accHeading=**52**, flags=**56**, reserved3=60.
    """
    if len(payload) < 64:
        raise ValueError(f"NAV-RELPOSNED 载荷 {len(payload)} 字节, 期望 >= 64 (version 1)")
    def i4(off: int) -> int:
        return int.from_bytes(payload[off:off + 4], "little", signed=True)
    def u4(off: int) -> int:
        return int.from_bytes(payload[off:off + 4], "little", signed=False)
    return RelPosNed(
        version=payload[0],
        ref_station_id=payload[1],
        rel_pos_n=i4(8) * 0.01,
        rel_pos_e=i4(12) * 0.01,
        rel_pos_d=i4(16) * 0.01,
        rel_pos_length=i4(20) * 0.01,
        rel_pos_heading=i4(24) * 1e-5,
        acc_heading=u4(52) * 1e-5,
        flags=u4(56),
    )


def poll(port: str, baud: int, cls: int, mid: int, timeout: float) -> bytes | None:
    """发一次轮询并等回应, 返回载荷; 超时返回 None."""
    import serial  # 延迟导入: 没装 pyserial 时只有这里会报错

    with serial.Serial(port, baud, timeout=0.2) as ser:
        ser.reset_input_buffer()
        ser.write(ubx_frame(cls, mid))
        deadline = time.monotonic() + timeout
        buf = bytearray()
        while time.monotonic() < deadline:
            chunk = ser.read(2048)
            if chunk:
                buf.extend(chunk)
                for c, i, payload in parse_frames(bytes(buf)):
                    if (c, i) == (cls, mid):
                        return payload
        return None


def report(port: str, baud: int, timeout: float, want_relposned: bool) -> int:
    """连模块跑一轮检查, 打印结果; 返回进程退出码."""
    print(f"端口 {port} @ {baud}, 超时 {timeout:.1f}s")
    payload = poll(port, baud, CLS_MON, ID_MON_VER, timeout)
    if payload is None:
        print("MON-VER 无回应. 依次检查: 模块是否上电 (灯) / 波特率 (460800 -> 38400) / "
              "TX-RX 是否交叉 / GND 是否接 / 端口是否被别的程序占用")
        return 2
    ver = parse_mon_ver(payload)
    print(f"  SW : {ver.sw_version}")
    print(f"  HW : {ver.hw_version}")
    for ext in ver.extensions:
        print(f"  扩展: {ext}")
    fw = ver.firmware
    print(f"  >>> HPG 固件行: {fw if fw else '未在扩展串里找到 FWVER/HPG'}")
    if fw:
        digits = [int(x) for x in fw.replace("=", " ").replace(".", " ").split() if x.isdigit()]
        if len(digits) >= 2 and (digits[0], digits[1]) < (1, 30):
            print(f"  >>> 判定: 版本疑似低于 1.30, 移动基线不可靠 -> 建议升级到 HPG 1.32")
        elif digits:
            print(f"  >>> 判定: 版本 {digits[0]}.{digits[1]} (要求 >= 1.30, 推荐 1.32)")

    payload = poll(port, baud, CLS_CFG, ID_CFG_GNSS, timeout)
    if payload is None:
        print("CFG-GNSS 无回应 (不影响主判定)")
    else:
        print("星座配置:")
        for gnss_id, enable, max_ch in parse_cfg_gnss(payload):
            print(f"  {GNSS_NAMES.get(gnss_id, gnss_id):8s} {'使能' if enable else '关闭'}  通道 {max_ch}")

    if want_relposned:
        payload = poll(port, baud, CLS_NAV, ID_RELPOSNED, timeout)
        if payload is None:
            print("NAV-RELPOSNED 无回应 (需 base 已向 rover 提供 RTCM 且已成对工作)")
        else:
            rp = parse_relposned(payload)
            print("NAV-RELPOSNED:")
            print(f"  基线 N/E/D = {rp.rel_pos_n:+.3f} / {rp.rel_pos_e:+.3f} / {rp.rel_pos_d:+.3f} m")
            print(f"  长度 {rp.rel_pos_length:.3f} m, 航向 {rp.rel_pos_heading:+.2f} 度 (精度 {rp.acc_heading:.2f} 度)")
            print(f"  carrSoln={rp.carr_soln}, relPosValid={rp.flag(2)}, headingValid={rp.flag(8)}, "
                  f"gnssFixOK={rp.flag(0)}, diffSoln={rp.flag(1)}")
    return 0


def selftest() -> int:
    """用合成帧自测组帧/切帧/解析三条路径, 返回 0 表示通过."""
    ext = [b"FWVER=HPG 1.32".ljust(30, b"\x00"), b"PROTVER=27.11".ljust(30, b"\x00")]
    payload = b"EXT CORE 1.00 (f10c36)".ljust(30, b"\x00") + b"00190000".ljust(10, b"\x00") + b"".join(ext)
    frame = ubx_frame(CLS_MON, ID_MON_VER, payload)
    gnss_payload = bytes([0, 0, 0, 2]) + bytes([0, 0, 8, 0, 1, 0, 0, 0]) + bytes([6, 0, 14, 0, 1, 0, 0, 0])
    frames = parse_frames(frame + ubx_frame(CLS_CFG, ID_CFG_GNSS, gnss_payload))
    assert len(frames) == 2, frames
    ver = parse_mon_ver(frames[0][2])
    assert ver.hw_version == "00190000", ver
    assert ver.firmware == "FWVER=HPG 1.32", ver.firmware
    gnss = parse_cfg_gnss(frames[1][2])
    assert gnss == [(0, True, 8), (6, True, 14)], gnss
    rp_payload = bytearray(64)
    rp_payload[0] = 1
    rp_payload[8:12] = (12).to_bytes(4, "little", signed=True)      # N 0.12 m
    rp_payload[12:16] = (43).to_bytes(4, "little", signed=True)     # E 0.43 m
    rp_payload[24:28] = (7400000).to_bytes(4, "little", signed=True)  # 74 度
    rp_payload[52:56] = (100).to_bytes(4, "little")                   # accHeading 0.001 度
    rp_payload[56:60] = (0b1_0001_0111).to_bytes(4, "little")         # fixOK+diffSoln+relPosValid+headingValid+carrSoln=fixed
    rp = parse_relposned(bytes(rp_payload))
    assert abs(rp.rel_pos_e - 0.43) < 1e-9 and abs(rp.rel_pos_heading - 74.0) < 1e-9, rp
    assert rp.carr_soln == "fixed" and rp.flag(2) and rp.flag(8), rp
    assert abs(rp.acc_heading - 0.001) < 1e-9, rp
    try:
        parse_relposned(bytes(40))
    except ValueError:
        pass
    else:
        raise AssertionError("短载荷应报错 (不足 64 字节)")
    print("selftest 通过: 组帧 / 切帧 / MON-VER / CFG-GNSS / RELPOSNED 解析均正常")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="UBX 轮询探针 (固件版本 / 星座 / 移动基线相对解)")
    ap.add_argument("--port", help="串口号, 如 COM7")
    ap.add_argument("--baud", type=int, default=460800, help="波特率 (默认 460800; UART 出厂默认 38400)")
    ap.add_argument("--timeout", type=float, default=2.0, help="每次轮询等待秒数")
    ap.add_argument("--poll", choices=("mon-ver", "gnss", "relposned", "all"), default="all")
    ap.add_argument("--selftest", action="store_true", help="无硬件自测")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.port:
        ap.error("需要 --port (或 --selftest)")
    try:
        return report(args.port, args.baud, args.timeout, args.poll in ("relposned", "all"))
    except Exception as exc:  # 串口打不开/无权限等: 明确报错并给出退出码
        print(f"失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("提示: 端口是否存在看设备管理器 -> 端口(COM 和 LPT); 被占用则先关掉 MP / u-center", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
