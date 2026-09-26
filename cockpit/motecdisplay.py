"""motecdisplay.bin text roundtrip."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "physics"))
from dfbin import lookup3

from q02 import build, cstr, f32, fmt_f32, parse, q

_FOOT = {
    2: bytes.fromhex("02000000e2b9a0110100d01c56af107d0200d03c"),
    3: bytes.fromhex("03000000e2b9a0110100d01cca902f980100d02c56af107d0200d03c"),
    4: bytes.fromhex("04000000e2b9a0110100d01cca902f980100d02cb275f36f01109a4856af107d0200d03c"),
}


def _elem(data: bytes, names: bytes, off: int) -> str:
    return cstr(names, q(data, off + 8))


def unpack_bytes(raw: bytes) -> str:
    version, ident, secs = parse(raw)
    if version != 5:
        raise ValueError(f"unsupported motecdisplay version {version}")
    data, names = secs[1], secs[50]
    illum = q(data, 56)
    pages = [_elem(data, names, q(data, 72) + i * 16) for i in range(q(data, 64))]
    widgets = []
    base, count = q(data, 88), q(data, 80)
    for i in range(count):
        at = base + i * 32
        widgets.append((_elem(data, names, at), f32(data, at + 16), f32(data, at + 20), q(data, at + 24)))
    lines = [
        "[motecdisplay]",
        f"id = {ident.hex()}",
        f"screen = {cstr(data, q(data, 0))}",
        f"light = {cstr(data, q(data, 8))}",
        f"{cstr(data, q(data, illum))} = {fmt_f32(f32(data, illum + 8))}",
        f"states = {_elem(data, names, 16)} {_elem(data, names, 32)}",
        f"pages = {' '.join(pages)}",
    ]
    if widgets:
        lines += ["", "; min max flag", "[widgets]"]
        lines += [f"{name} = {fmt_f32(lo)} {fmt_f32(hi)} {flag}" for name, lo, hi, flag in widgets]
    return "\n".join(lines) + "\n"


def _parse(text: str) -> dict:
    meta: dict[str, str] = {}
    blocks: dict[str, list[tuple[str, str]]] = {}
    bare: dict[str, list[str]] = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line:
            bare.setdefault(section or "", []).append(line)
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if section in (None, "motecdisplay"):
            meta[key] = value
        if section:
            blocks.setdefault(section, []).append((key, value))
    meta["_blocks"] = blocks
    meta["_bare"] = bare
    return meta


def _record(name: str, name_at: int) -> bytes:
    return struct.pack("<Ii q", lookup3(name.encode("latin-1")), 0, name_at)


def pack_bytes(text: str) -> bytes:
    spec = _parse(text)
    states = spec.get("states", "").split() or spec["_bare"].get("states", ["ON", "OFF"])
    pages = spec.get("pages", "").split() or spec["_bare"].get("pages", [])
    widgets = []
    for name, value in spec["_blocks"].get("widgets", []):
        lo, hi, flag = value.split()
        widgets.append((name, float(lo), float(hi), int(flag)))
    param = "globalSelfIlluminationFactor"
    param_value = 0.5
    for key, value in spec.items():
        if not key.startswith("_") and key not in ("format", "id", "screen", "light", "states", "pages"):
            param, param_value = key, float(value)

    names = bytearray()
    located: list[tuple[str, int]] = []

    def add_name(label: str) -> int:
        at = len(names)
        names.extend(label.encode("latin-1") + b"\x00")
        located.append((label, at))
        return at

    for label in (*states, *pages, *(name for name, *_ in widgets)):
        add_name(label)
    pool = bytearray()

    def add_pool(label: str) -> int:
        at = len(pool)
        pool.extend(label.encode("latin-1") + b"\x00")
        return at

    screen_at = add_pool(spec.get("screen", "_LCD"))
    light_at = add_pool(spec.get("light", "_LCD_LIGHT"))
    param_at = add_pool(param)

    data = bytearray(112)
    page_at = 112
    page_names = located[len(states) : len(states) + len(pages)]
    data.extend(b"".join(_record(label, at) for label, at in page_names))
    widget_at = len(data)
    widget_names = located[len(states) + len(pages) :]
    for (name, lo, hi, flag), (_, at) in zip(widgets, widget_names):
        data.extend(_record(name, at) + struct.pack("<ffq", lo, hi, flag))
    pool_at = len(data)
    data.extend(pool)

    def put(off: int, value: int) -> None:
        struct.pack_into("<q", data, off, value)

    put(0, pool_at + screen_at)
    put(8, pool_at + light_at)
    data[16:32] = _record(states[0], located[0][1])
    data[32:48] = _record(states[1], located[1][1])
    put(48, 1)
    put(56, 96)
    put(64, len(pages))
    put(72, page_at if pages else 0)
    put(80, len(widgets))
    put(88, widget_at if widgets else 0)
    put(96, pool_at + param_at)
    struct.pack_into("<f", data, 104, param_value)

    slots = [0, 8, 56]
    if pages:
        slots.append(72)
    if widgets:
        slots.append(88)
    slots.append(96)
    dmap = b"".join(struct.pack("<q", off) for off in slots)
    offs = [(16, located[0][1]), (32, located[1][1])]
    offs += [(page_at + i * 16, at) for i, (_, at) in enumerate(page_names)]
    offs += [(widget_at + i * 32, at) for i, (_, at) in enumerate(widget_names)]
    offset_blob = b"".join(struct.pack("<qq", data_at, name_at) for data_at, name_at in offs)
    kind = 4 if widgets else 3 if pages else 2
    return build(5, bytes.fromhex(spec.get("id", "00" * 8)), [
        (1, bytes(data)), (16, dmap), (50, bytes(names)), (51, offset_blob), (80, _FOOT[kind]),
    ])
