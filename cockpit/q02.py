"""Q02 section container."""
from __future__ import annotations

import struct

MAGIC = {3: bytes.fromhex("5102010308000104"), 5: bytes.fromhex("5102010508000104")}
FOOTER = bytes.fromhex("020000005cb30e5107005643cf72d3e503004342")


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def i32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<i", buf, off)[0]


def f32(buf: bytes, off: int) -> float:
    return struct.unpack_from("<f", buf, off)[0]


def q(buf: bytes, off: int) -> int:
    return struct.unpack_from("<q", buf, off)[0]


def cstr(buf: bytes, off: int) -> str:
    end = buf.find(b"\x00", off)
    return buf[off: end if end >= 0 else None].decode("latin-1")


def fmt_f32(x: float) -> str:
    x = struct.unpack("<f", struct.pack("<f", x))[0]
    for prec in range(8, 18):
        s = format(x, f".{prec}g")
        if "." not in s and "e" not in s.lower():
            s += ".0"
        if struct.pack("<f", float(s)) == struct.pack("<f", x):
            return s
    return format(x, ".17g")


def pad16(n: int) -> int:
    return (16 - n % 16) % 16


def parse(raw: bytes) -> tuple[int, bytes, dict[int, bytes]]:
    if raw[:3] != b"Q\x02\x01" or raw[3] not in MAGIC:
        raise ValueError("not a Q02 v3/v5 container")
    version = raw[3]
    nsec = version
    recs = []
    off = 0x10
    for _ in range(nsec):
        size, meta = struct.unpack_from("<II", raw, off)
        recs.append((size, meta & 0xFF, (meta >> 8) & 0xFF))
        off += 8
    body = raw[4] + (nsec + 2) * 8
    secs: dict[int, bytes] = {}
    for size, typ, pad in recs:
        secs[typ] = raw[body : body + size]
        body += size + pad
    if body != len(raw):
        raise ValueError(f"container size {body} != file size {len(raw)}")
    return version, raw[8:16], secs


def build(version: int, ident: bytes, sections: list[tuple[int, bytes]]) -> bytes:
    recs = bytearray()
    body = bytearray()
    for typ, blob in sections:
        pad = pad16(len(blob))
        recs += struct.pack("<I", len(blob)) + bytes((typ, pad, 0, 0))
        body += blob + b"\x00" * pad
    if len(recs) != version * 8:
        raise ValueError(f"version {version} needs {version} sections, got {len(sections)}")
    return MAGIC[version] + ident + recs + b"\x00" * 8 + body
