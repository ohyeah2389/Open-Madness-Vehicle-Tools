"""Q02 VDFM vehicle definition text roundtrip for Madness Engine games."""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path

MAGIC = b"Q\x02\x01\x04"
_HDR4 = b"\x00\x00\x01\x04"
_FP_HASH = 0xEF28B55F
_DATA_SIZE = {14: 416, 16: 440, 17: 448}
_WHEEL_BASE = {14: 0x58, 16: 0x68, 17: 0x68}
_LOOKUPS = {
    "chassis": 0x08,
    "engine": 0x18,
    "clutches": 0x20,
    "turbo": 0x28,
    "config": 0x30,
    "failure_model": 0x38,
    "gearbox": 0x40,
    "suspension": 0x48,
    "collision": 0x50,
    "tyre": 0x58,
    "kers_hybrid": 0xB8,
    "push_to_pass": 0xC8,
    "boost_config": 0xF8,
    "turbo_config": 0x108,
}
_LOOKUP_ALIASES = {"body": 0x30, "boost": 0xC8}
_OFF_TO_LOOKUP = {off: name for name, off in _LOOKUPS.items()}
_WHEEL_REL = (
    ("fl_lateral_offset_m", 0x00),
    ("fl_vertical_offset_m", 0x04),
    ("fl_fore_aft_offset_m", 0x08),
    ("fr_lateral_offset_m", 0x0C),
    ("fr_vertical_offset_m", 0x10),
    ("fr_fore_aft_offset_m", 0x14),
    ("rl_lateral_offset_m", 0x18),
    ("rl_vertical_offset_m", 0x1C),
    ("rl_fore_aft_offset_m", 0x20),
    ("rr_lateral_offset_m", 0x24),
    ("rr_vertical_offset_m", 0x28),
    ("rr_fore_aft_offset_m", 0x2C),
    ("fl_tyre_width_m", 0x30),
    ("fl_tyre_height_m", 0x34),
    ("fr_tyre_width_m", 0x38),
    ("fr_tyre_height_m", 0x3C),
    ("rl_tyre_width_m", 0x40),
    ("rl_tyre_height_m", 0x44),
    ("rr_tyre_width_m", 0x48),
    ("rr_tyre_height_m", 0x4C),
)
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_OFF_KEY = re.compile(r"^off_([0-9a-fA-F]{4})$")
_LOOKUP_KEY = re.compile(r"^lookup_0x([0-9a-fA-F]+)$", re.I)


def u32(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off : off + 4], "little")


def p32(v: int) -> bytes:
    return (v & 0xFFFFFFFF).to_bytes(4, "little")


def pad16(n: int) -> int:
    return (16 - n % 16) % 16


def fmt_f32(x: float) -> str:
    x = struct.unpack("<f", struct.pack("<f", x))[0]
    for prec in range(8, 18):
        s = format(x, f".{prec}g")
        if "." not in s and "e" not in s.lower():
            s += ".0"
        y = struct.unpack("<f", struct.pack("<f", float(s)))[0]
        if struct.pack("<f", y) == struct.pack("<f", x):
            return s
    return format(x, ".17g")


def fmt_slot(raw: bytes) -> str:
    i = int.from_bytes(raw, "little")
    if i == 0xFFFFFFFF:
        return "-1"
    if i < 0x10000:
        return str(i)
    return fmt_f32(struct.unpack("<f", raw)[0])


def parse_slot(s: str) -> bytes:
    if re.search(r"[.eE]", s):
        return struct.pack("<f", float(s))
    v = int(s, 10)
    return struct.pack("<i" if v < 0 else "<I", v)


def fmt_str(s: str) -> str:
    return s if _IDENT.fullmatch(s) else json.dumps(s)


def parse_str(s: str) -> str:
    return json.loads(s) if s[:1] in "\"'" else s


def _cstr(pool: bytes, off: int) -> str:
    end = pool.find(b"\x00", off)
    return pool[off : end if end >= 0 else None].decode("latin-1")


def parse_container(raw: bytes) -> tuple[bytes, dict[int, bytes]]:
    if raw[:4] != MAGIC:
        raise ValueError("not a VDFM (Q02) file")
    nsec, extra_n = raw[3], raw[4]
    recs = []
    off = 0x10
    for _ in range(nsec):
        recs.append((u32(raw, off), raw[off + 4], raw[off + 5]))
        off += 8
    cur = extra_n + (nsec + 2) * 8
    secs: dict[int, bytes] = {}
    for size, typ, pad in recs:
        secs[typ] = raw[cur : cur + size]
        cur += size + pad
    return raw[8:16], secs


def build_container(extra: bytes, data: bytes, pool: bytes, dmap: bytes) -> bytes:
    fp = p32(1) + p32(_FP_HASH) + p32({416: 14, 440: 16, 448: 17}[len(data)])
    blobs = ((1, data), (0x30, pool), (0x31, dmap), (0x50, fp))
    recs = bytearray()
    body = bytearray()
    for typ, blob in blobs:
        recs += p32(len(blob)) + bytes((typ, pad16(len(blob)), 0, 0))
        body += blob + b"\x00" * pad16(len(blob))
    return MAGIC + _HDR4 + extra[:8] + bytes(recs) + bytes(body)


def wheel_map(schema: int) -> dict[str, int]:
    base = _WHEEL_BASE[schema]
    return {name: base + rel for name, rel in _WHEEL_REL}


def unpack_bytes(raw: bytes) -> str:
    extra, secs = parse_container(raw)
    data, pool, dmap, fp = secs[1], secs[0x30], secs[0x31], secs[0x50]
    schema = u32(fp, 8)
    if schema not in _DATA_SIZE or len(data) != _DATA_SIZE[schema]:
        raise ValueError(f"unsupported VDFM schema {schema} data={len(data)}")
    tokens = [u32(dmap, i) for i in range(0, len(dmap), 8)]
    lines = [f"id = {extra.hex()}", f"schema = {schema}", "", "[lookups]"]
    for off in tokens:
        name = _OFF_TO_LOOKUP.get(off) or f"lookup_0x{off:x}"
        lines.append(f"{name} = {fmt_str(_cstr(pool, u32(data, off)))}")
    wheels = wheel_map(schema)
    lines += ["", "[wheel_tire]"]
    lines += [f"{name} = {fmt_f32(struct.unpack_from('<f', data, off)[0])}" for name, off in wheels.items()]
    skip = {o for off in tokens for o in (off, off + 4)} | set(wheels.values())
    fields = []
    for off in range(0, len(data), 4):
        if off in skip or data[off : off + 4] == b"\x00\x00\x00\x00":
            continue
        fields.append(f"off_{off:04x} = {fmt_slot(data[off : off + 4])}")
    if fields:
        lines += ["", "[fields]", *fields]
    return "\n".join(lines) + "\n"


def _parse_text(text: str) -> dict:
    meta, section, kv = {}, None, {"lookups": {}, "wheel_tire": {}, "fields": {}}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if section in kv:
            kv[section][key] = value
        else:
            meta[key] = value
    return {**meta, **kv}


def pack_bytes(text: str) -> bytes:
    t = _parse_text(text)
    schema = int(t.get("schema", 16))
    size = _DATA_SIZE.get(schema)
    if size is None:
        raise ValueError(f"unsupported schema {schema}")
    data = bytearray(size)
    wheels = wheel_map(schema)
    for name, value in t["fields"].items():
        m = _OFF_KEY.match(name)
        if not m:
            raise ValueError(f"unknown field {name}")
        off = int(m.group(1), 16)
        slot = parse_slot(value)
        data[off : off + len(slot)] = slot
    for name, value in t["wheel_tire"].items():
        off = wheels.get(name)
        if off is None:
            raise ValueError(f"unknown wheel field {name}")
        struct.pack_into("<f", data, off, float(value))
    lookups: list[tuple[int, str]] = []
    for name, value in t["lookups"].items():
        m = _LOOKUP_KEY.match(name)
        off = int(m.group(1), 16) if m else _LOOKUPS.get(name) or _LOOKUP_ALIASES.get(name)
        if off is None:
            raise ValueError(f"unknown lookup {name}")
        lookups.append((off, parse_str(value)))
    pool, offsets = bytearray(), {}
    for off, value in sorted(lookups):
        if value not in offsets:
            offsets[value] = len(pool)
            pool += value.encode("latin-1") + b"\x00"
        struct.pack_into("<I", data, off, offsets[value])
    dmap = b"".join(p32(off) + p32(0) for off, _ in sorted(lookups))
    extra = bytes.fromhex(t["id"]) if t.get("id") else hashlib.md5((lookups[0][1] if lookups else "vehicle").encode("latin-1")).digest()[:8]
    if len(extra) != 8:
        raise ValueError("id must be 8 bytes (16 hex chars)")
    return build_container(extra, bytes(data), bytes(pool), dmap)


def unpack_file(src: Path, dst: Path | None = None) -> Path:
    src = Path(src)
    dst = Path(dst) if dst else src.with_suffix(".vdf")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(unpack_bytes(src.read_bytes()), encoding="utf-8")
    return dst


def pack_file(src: Path, dst: Path | None = None) -> Path:
    src = Path(src)
    dst = Path(dst) if dst else src.with_suffix(".vdfm")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(pack_bytes(src.read_text(encoding="utf-8")))
    return dst
