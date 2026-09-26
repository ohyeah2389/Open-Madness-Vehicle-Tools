"""pitcontroller.bin text roundtrip."""
from __future__ import annotations

import struct

from q02 import build, cstr, f32, fmt_f32, i32, parse, q

SCALARS = (
    (0x00, "f", "unknown_0"), (0x04, "f", "unknown_4"), (0x08, "i", "unknown_8"),
    (0x0C, "f", "unknown_12"), (0x10, "f", "unknown_16"), (0x14, "f", "unknown_20"),
    (0x18, "f", "unknown_24"), (0x20, "f", "unknown_32"), (0x28, "f", "unknown_40"),
    (0x2C, "f", "unknown_44"), (0x30, "f", "unknown_48"), (0x34, "f", "unknown_52"),
    (0x38, "f", "unknown_56"), (0x3C, "i", "unknown_60"), (0x40, "f", "unknown_64"),
    (0x44, "f", "unknown_68"), (0x48, "f", "unknown_72"), (0x4C, "f", "unknown_76"),
    (0x50, "f", "unknown_80"), (0x54, "f", "unknown_84"), (0x58, "f", "unknown_88"),
    (0x5C, "f", "unknown_92"), (0x60, "f", "unknown_96"), (0x64, "f", "unknown_100"),
    (0x68, "f", "unknown_104"), (0x6C, "f", "unknown_108"), (0x74, "f", "unknown_116"),
    (0x78, "f", "unknown_120"), (0x7C, "f", "unknown_124"), (0x80, "i", "unknown_128"),
)
NAMES = b"JackGT\x00GTWheelChange\x00"
OFFSETS = struct.pack("<qqqq", 0x88, 0, 0x98, 7)
FOOTER = bytes.fromhex("0300000000a0771a010046509d8b3bce0100505079cc95e00d004350")


def _str(data: bytes, off: int) -> str:
    ptr = q(data, off)
    return cstr(data, ptr) if ptr else ""


def unpack_bytes(raw: bytes) -> str:
    version, ident, secs = parse(raw)
    if version != 5:
        raise ValueError(f"unsupported pitcontroller version {version}")
    data = secs[1]
    count = q(data, 0xC8)
    outfits = q(data, 0xC0)
    helmets = q(data, 0xD0)
    lines = ["[pitcontroller]", f"id = {ident.hex()}"]
    for off, typ, name in SCALARS:
        value = fmt_f32(f32(data, off)) if typ == "f" else str(i32(data, off))
        lines.append(f"{name} = {value}")
    lines += [f"pitstop = {_str(data, 0xD8)}", f"crew = {_str(data, 0xE0)}", "", "; id model", "[outfits]"]
    lines += [f"{_str(data, outfits + i * 24)} = {_str(data, outfits + i * 24 + 16)}" for i in range(count)]
    lines += ["", "[helmets]"]
    lines += [f"{_str(data, helmets + i * 24)} = {_str(data, helmets + i * 24 + 16)}" for i in range(count)]
    return "\n".join(lines) + "\n"


def _parse(text: str) -> dict:
    meta: dict[str, str] = {}
    blocks: dict[str, list[tuple[str, str]]] = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if section in (None, "pitcontroller"):
            meta[key] = value
        if section:
            blocks.setdefault(section, []).append((key, value))
    meta["_blocks"] = blocks
    return meta


def pack_bytes(text: str) -> bytes:
    spec = _parse(text)
    outfits = spec["_blocks"].get("outfits", [])
    helmets = spec["_blocks"].get("helmets", [])
    n = len(outfits)
    if len(helmets) != n:
        raise ValueError(f"{n} outfits but {len(helmets)} helmets")
    string_base = 0xE8 + n * 48
    pool = bytearray()
    found: dict[str, int] = {}

    def add(label: str) -> int:
        if not label:
            return 0
        if label not in found:
            found[label] = string_base + len(pool)
            pool.extend(label.encode("latin-1") + b"\x00")
        return found[label]

    pak, crew = add(spec.get("pitstop", "")), add(spec.get("crew", ""))
    outfit_at = [(add(name), add(path)) for name, path in outfits]
    helmet_at = [(add(name), add(path)) for name, path in helmets]

    data = bytearray(string_base + len(pool))
    for off, typ, name in SCALARS:
        if typ == "f":
            struct.pack_into("<f", data, off, float(spec.get(name, "0")))
        else:
            struct.pack_into("<i", data, off, int(spec.get(name, "0")))
    struct.pack_into("<II", data, 0x88, 0xCE7C0800, 0)
    struct.pack_into("<II", data, 0x98, 0xFE58AE1B, 0)
    struct.pack_into("<qqqqqq", data, 0xA0, 7, 1, 0xD8, n, 0xE8, n)
    helmets_at = 0xE8 + n * 24
    struct.pack_into("<q", data, 0xD0, helmets_at)
    struct.pack_into("<qq", data, 0xD8, pak, crew)
    for i, (name_at, path_at) in enumerate(outfit_at):
        struct.pack_into("<qqq", data, 0xE8 + i * 24, name_at, 0, path_at)
    for i, (name_at, path_at) in enumerate(helmet_at):
        struct.pack_into("<qqq", data, helmets_at + i * 24, name_at, 0, path_at)
    data[string_base:] = pool

    slots = [0xB0, 0xC0, 0xD0, 0xD8, 0xE0]
    for base, recs in ((0xE8, outfit_at), (helmets_at, helmet_at)):
        for i, (name_at, path_at) in enumerate(recs):
            if name_at:
                slots.append(base + i * 24)
            if path_at:
                slots.append(base + i * 24 + 16)
    dmap = b"".join(struct.pack("<q", off) for off in slots)
    return build(5, bytes.fromhex(spec.get("id", "00" * 8)), [
        (1, bytes(data)), (16, dmap), (50, NAMES), (51, OFFSETS), (80, FOOTER),
    ])
