"""cockpit.bin text roundtrip."""
from __future__ import annotations

import struct

from q02 import FOOTER, build, cstr, f32, fmt_f32, i32, parse, q, u32

GAUGE_HASH = {
    "eGauge_Speed": 0xEC9A4833,
    "eGauge_Tach": 0x8B5EFC1C,
    "eGauge_OilPressure": 0x1187F940,
    "eGauge_OilTemp": 0xC96591A9,
    "eGauge_WaterTemp": 0x76ABC2C7,
    "eGauge_FuelPressure": 0xD3EF3798,
    "eGauge_FuelLevel": 0x1CDE7624,
    "eGauge_RedLine": 0x3FC3E001,
    "eGauge_Battery": 0xCFC8C0DD,
    "eGauge_Boost": 0xD522EC49,
    "eGauge_Power": 0x158A4CF2,
}
CONTROLS = [
    "CDPlayer", "Traction", "Lights", "HazardLights", "FogLights", "Ignition",
    "Start", "ABS", "DSC", "Window", "Wiper", "Indicator",
]
MOTEC = [
    "SpeedBar", "RPMBar", "FuelLevel", "OilPressure", "OilTemp", "WaterTemp",
    "TurboBoost", "KersBar", "Unknown1", "Unknown2", "Power", "Torque",
]
# offset, type, name (note: looks right from some test unpacks, but may be somewhat inaccurate)
FIELDS = [
    (132, "f", "camera_bias"),
    (172, "f", "head_scale"),
    (176, "i", "speed_units"),
    (180, "i", "pressure_units"),
    (184, "i", "temp_units"),
    (188, "i", "unknown_188"),
    (200, "i", "unknown_200"),
    (204, "i", "unknown_204"),
    (208, "f", "redline_wait"),
    (212, "f", "redline"),
    (216, "i", "unknown_216"),
    (220, "f", "unknown_220"),
    (224, "f", "unknown_224"),
    (228, "f", "unknown_228"),
    (232, "f", "paddle_delay"),
    (236, "f", "paddle_time"),
    (240, "f", "paddle_rot"),
    (244, "f", "stick_delay"),
    (248, "f", "stick_time"),
    (252, "i", "gear_stick"),
    (256, "f", "gear_lateral_rot"),
    (260, "f", "gear_fore_aft"),
    (264, "f", "reverse_delay"),
    (268, "f", "reverse_time"),
    (272, "f", "reverse_rot"),
    (276, "f", "handbrake_rot"),
    (280, "f", "window_rot"),
    (284, "i", "odometer_decimals"),
    (288, "i", "unknown_288"),
    (292, "f", "exposure"),
    (296, "i", "unknown_296"),
    (300, "i", "unknown_300"),
]
CAMERAS = (("cockpit_camera", 136), ("rear_camera", 148), ("shotgun_camera", 160))
def _show_str(data: bytes, ptr: int) -> str:
    if not ptr:
        return ""
    text = cstr(data, ptr)
    return '""' if text == "" else text


def _name(names: list[str], index: int, prefix: str) -> str:
    return names[index] if index < len(names) else f"{prefix}_{index}"


def _floats(data: bytes, off: int, count: int) -> list[float]:
    return [f32(data, off + i * 4) for i in range(count)]


def unpack_bytes(raw: bytes) -> str:
    version, ident, secs = parse(raw)
    data, names = secs[1], secs.get(50, b"")
    lines = [
        "[cockpit]",
        f"version = {version}",
        f"id = {ident.hex()}",
        f"gear_shifter = {_show_str(data, q(data, 0))}",
        f"model = {_show_str(data, q(data, 16))}",
        f"display = {_show_str(data, q(data, 24))}",
    ]
    for name, off in CAMERAS:
        lines.append(f"{name} = {' '.join(fmt_f32(f32(data, off + i * 4)) for i in range(3))}")
    lines.append("; gear_stick: 0 paddle, 2 H, 3 sequential")
    for off, typ, name in FIELDS:
        value = fmt_f32(f32(data, off)) if typ == "f" else str(i32(data, off))
        lines.append(f"{name} = {value}")
    rpm_n, rpm_at = q(data, 80), q(data, 88)
    if rpm_n:
        lines.append(f"rpm_leds = {' '.join(fmt_f32(v) for v in _floats(data, rpm_at, rpm_n))}")

    gauges = []
    count, start = q(data, 32), q(data, 40)
    for i in range(count):
        at = start + i * 40
        lim, link = i32(data, at + 32), i32(data, at + 24)
        nums = [fmt_f32(f32(data, at + 16))]
        nums += [fmt_f32(f32(data, lim + j * 4)) for j in range(link * 2)]
        gauges.append((cstr(names, i32(data, at + 8)), " ".join(nums)))
    if gauges:
        lines += ["", "; min, then limit pairs", "[gauges]"]
        lines += [f"{name} = {vals}" for name, vals in gauges]

    gears = []
    count, start = q(data, 48), q(data, 56)
    for i in range(count):
        at = start + i * 48
        label = "gear" if u32(data, at) == 0 else cstr(names, i32(data, at + 8))
        nums = [fmt_f32(f32(data, at + o)) for o in (16, 20, 24, 32, 36, 40)]
        nums.insert(3, str(i32(data, at + 28)))
        gears.append((label, " ".join(nums)))
    if gears:
        lines += ["", "; a b c kind d e f", "[gear_gauges]"]
        lines += [f"{name} = {vals}" for name, vals in gears]

    def named_block(title: str, values: list[float]) -> None:
        if not values:
            return
        lines.append("")
        lines.append(f"[{title}]")
        for i, value in enumerate(values):
            lines.append(f"{_name(CONTROLS, i, title)} = {fmt_f32(value)}")

    rot_n, rot_at = q(data, 64), q(data, 72)
    named_block("rotation", _floats(data, rot_at, rot_n) if rot_n else [])
    named_block("translation", _floats(data, rot_at + rot_n * 4, rot_n) if rot_n else [])
    motec_n, motec_at = q(data, 96), q(data, 104)
    if motec_n:
        lines += ["", "[motec]"]
        for i, value in enumerate(_floats(data, motec_at, motec_n)):
            lines.append(f"{_name(MOTEC, i, 'motec')} = {fmt_f32(value)}")
    range_n, range_at = q(data, 112), q(data, 120)
    if range_n:
        lines += ["", "; min max", "[ranges]"]
        for i in range(range_n):
            lo, hi = f32(data, range_at + i * 8), f32(data, range_at + i * 8 + 4)
            lines.append(f"{_name(MOTEC, i, 'range')} = {fmt_f32(lo)} {fmt_f32(hi)}")
    return "\n".join(lines) + "\n"


def _section(text: str) -> dict:
    meta: dict[str, str] = {}
    blocks: dict[str, list[tuple[str, str]]] = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            blocks.setdefault(section, [])
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if section in (None, "cockpit"):
            meta[key] = value
        if section:
            blocks[section].append((key, value))
    meta["_blocks"] = blocks
    return meta


def _num(value: str, typ: str):
    return float(value) if typ == "f" else int(value)


def pack_bytes(text: str) -> bytes:
    spec = _section(text)
    version = int(spec.get("version", 5))
    data = bytearray(304)
    for off, typ, name in FIELDS:
        if name not in spec:
            continue
        struct.pack_into("<f" if typ == "f" else "<i", data, off, _num(spec[name], typ))
    for name, off in CAMERAS:
        for i, part in enumerate(spec.get(name, "0 0 0").split()):
            struct.pack_into("<f", data, off + i * 4, float(part))

    blocks = spec["_blocks"]
    names = bytearray()
    name_of: dict[str, int] = {}

    def intern(label: str) -> int:
        if label not in name_of:
            name_of[label] = len(names)
            names.extend(label.encode("latin-1") + b"\x00")
        return name_of[label]

    gauges = []
    for label, value in blocks.get("gauges", []):
        nums = [float(p) for p in value.split()]
        intern(label)
        gauges.append((label, nums[0], list(zip(nums[1::2], nums[2::2]))))
    gears = []
    for label, value in blocks.get("gear_gauges", []):
        parts = value.split()
        if label != "gear":
            intern(label)
        gears.append((label, [float(p) for p in parts[:3]], int(parts[3]), [float(p) for p in parts[4:]]))

    def rows(title: str) -> list[float]:
        return [float(value) for _, value in blocks.get(title, [])]

    rotation, translation = rows("rotation"), rows("translation")
    rpm = [float(p) for p in spec.get("rpm_leds", "").split()]
    motec = rows("motec")
    ranges = [tuple(float(p) for p in value.split()) for _, value in blocks.get("ranges", [])]

    pos = 304

    def add(blob: bytes) -> int:
        nonlocal pos
        at = pos
        data.extend(blob)
        pos += len(blob)
        return at

    gauge_at = []
    for label, lo, pairs in gauges:
        rec = bytearray(40)
        struct.pack_into("<I", rec, 0, GAUGE_HASH[label])
        struct.pack_into("<i", rec, 8, intern(label))
        struct.pack_into("<f", rec, 16, lo)
        struct.pack_into("<i", rec, 24, len(pairs))
        gauge_at.append(add(rec))
    gear_at = 0
    for i, (label, early, kind, late) in enumerate(gears):
        rec = bytearray(48 if i < len(gears) - 1 else 44)
        if label != "gear":
            struct.pack_into("<I", rec, 0, GAUGE_HASH[label])
            struct.pack_into("<i", rec, 8, intern(label))
        for n, value in enumerate(early):
            struct.pack_into("<f", rec, 16 + n * 4, value)
        struct.pack_into("<i", rec, 28, kind)
        for n, value in enumerate(late):
            struct.pack_into("<f", rec, 32 + n * 4, value)
        at = add(rec)
        gear_at = gear_at or at
    rot_at = add(struct.pack("<" + "f" * len(rotation), *rotation)) if rotation else 0
    if translation:
        add(struct.pack("<" + "f" * len(translation), *translation))
    rpm_at = add(struct.pack("<" + "f" * len(rpm), *rpm)) if rpm else 0
    motec_at = add(struct.pack("<" + "f" * len(motec), *motec)) if motec else 0
    range_at = add(b"".join(struct.pack("<ff", lo, hi) for lo, hi in ranges)) if ranges else 0
    if gauges:
        limit_at = pos
        for _, _, pairs in gauges:
            for lo, hi in pairs:
                add(struct.pack("<ff", lo, hi))
        cursor = limit_at
        for at, (_, _, pairs) in zip(gauge_at, gauges):
            struct.pack_into("<i", data, at + 32, cursor)
            cursor += len(pairs) * 8

    def add_str(text: str) -> int:
        if text == '""':
            return add(b"\x00")
        return add(text.encode("latin-1") + b"\x00") if text else 0

    shifter = add_str(spec.get("gear_shifter", ""))
    container = add_str("Container")
    model = add_str(spec.get("model", ""))
    display = add_str(spec.get("display", ""))

    def put(off: int, value: int) -> None:
        struct.pack_into("<q", data, off, value)

    put(0, shifter)
    put(8, container)
    put(16, model)
    put(24, display)
    put(32, len(gauges))
    put(40, gauge_at[0] if gauges else 0)
    put(48, len(gears))
    put(56, gear_at)
    put(64, len(rotation))
    put(72, rot_at)
    put(80, len(rpm))
    put(88, rpm_at)
    put(96, len(motec))
    put(104, motec_at)
    put(112, len(ranges))
    put(120, range_at)

    slots = [off for off, ptr in (
        (0, shifter), (8, container), (16, model), (24, display),
        (40, gauge_at[0] if gauges else 0), (56, gear_at), (72, rot_at),
        (88, rpm_at), (104, motec_at), (120, range_at),
    ) if ptr]
    slots += [at + 32 for at in gauge_at]
    dmap = b"".join(struct.pack("<q", off) for off in slots)
    entries = [(at, label) for at, (label, *_) in zip(gauge_at, gauges)]
    entries += [(gear_at + i * 48, label) for i, (label, *_) in enumerate(gears) if label != "gear"]
    offs = b"".join(struct.pack("<qq", at, intern(label)) for at, label in entries)
    sections = [(1, bytes(data)), (16, dmap)]
    if version == 5:
        sections += [(50, bytes(names)), (51, offs)]
    sections.append((80, FOOTER))
    return build(version, bytes.fromhex(spec.get("id", "00" * 8)), sections)
