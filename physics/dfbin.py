"""ShCB physics container (*.*bin) text roundtrip for Madness Engine games."""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from typing import Literal

MAGIC = b"ShCB"
VERSION = 0x53DD0FE6
STREAM_ID = 0x1010BABA
TEXT_ID = 0x55864952  # lookup3("Text")
_TEXT_KEY = b"".join(
    struct.pack("<I", (d + 0x7D9D5BB8) & 0xFFFFFFFF)
    for d in (0xF09A10DD, 0xB8C6C578, 0xB992FDA9, 0xE7D308BE, 0xD5DE13B3, 0xCAD9119C, 0xA6C018B9, 0xD362F098)
)[1:30]
_HASH_NAME = re.compile(r"^h_([0-9a-fA-F]{8})$")
_HEX_NAME = re.compile(r"^0x([0-9a-fA-F]{1,8})$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NUM = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?")
_NAMES_PATH = Path(__file__).with_name("names.json")
_NAMES: dict[int, str] | None = None


def u32(b: bytes, off: int) -> int:
    return int.from_bytes(b[off : off + 4], "little")


def p32(v: int) -> bytes:
    return (v & 0xFFFFFFFF).to_bytes(4, "little")


def _mix(a: int, b: int, c: int) -> tuple[int, int, int]:
    a = (a - c - b) & 0xFFFFFFFF
    a ^= c >> 13
    b = (b - a - c) & 0xFFFFFFFF
    b ^= (a << 8) & 0xFFFFFFFF
    c = (c - b - a) & 0xFFFFFFFF
    c ^= b >> 13
    a = (a - c - b) & 0xFFFFFFFF
    a ^= c >> 12
    b = (b - a - c) & 0xFFFFFFFF
    b ^= (a << 16) & 0xFFFFFFFF
    c = (c - b - a) & 0xFFFFFFFF
    c ^= b >> 5
    a = (a - c - b) & 0xFFFFFFFF
    a ^= c >> 3
    b = (b - a - c) & 0xFFFFFFFF
    b ^= (a << 10) & 0xFFFFFFFF
    c = (c - b - a) & 0xFFFFFFFF
    c ^= b >> 15
    return a, b, c


def lookup3(data: bytes) -> int:
    data = data.upper()
    a = b = 0x9E3779B9
    c = 0
    i, n = 0, len(data)
    while n - i >= 12:
        a = (a + int.from_bytes(data[i : i + 4], "big")) & 0xFFFFFFFF
        b = (b + int.from_bytes(data[i + 4 : i + 8], "big")) & 0xFFFFFFFF
        c = (c + int.from_bytes(data[i + 8 : i + 12], "big")) & 0xFFFFFFFF
        a, b, c = _mix(a, b, c)
        i += 12
    c = (c + n) & 0xFFFFFFFF
    tail = data[i:]
    if len(tail) >= 11:
        c = (c + (tail[10] << 24)) & 0xFFFFFFFF
    if len(tail) >= 10:
        c = (c + (tail[9] << 16)) & 0xFFFFFFFF
    if len(tail) >= 9:
        c = (c + (tail[8] << 8)) & 0xFFFFFFFF
    if len(tail) >= 8:
        b = (b + (tail[7] << 24)) & 0xFFFFFFFF
    if len(tail) >= 7:
        b = (b + (tail[6] << 16)) & 0xFFFFFFFF
    if len(tail) >= 6:
        b = (b + (tail[5] << 8)) & 0xFFFFFFFF
    if len(tail) >= 5:
        b = (b + tail[4]) & 0xFFFFFFFF
    if len(tail) >= 4:
        a = (a + (tail[3] << 24)) & 0xFFFFFFFF
    if len(tail) >= 3:
        a = (a + (tail[2] << 16)) & 0xFFFFFFFF
    if len(tail) >= 2:
        a = (a + (tail[1] << 8)) & 0xFFFFFFFF
    if len(tail) >= 1:
        a = (a + tail[0]) & 0xFFFFFFFF
    return _mix(a, b, c)[2]


def hash_name(name: str) -> int:
    m = _HASH_NAME.match(name) or _HEX_NAME.match(name)
    if m:
        return int(m.group(1), 16)
    return lookup3(name.encode("latin-1"))


def hash_section(inner: str) -> int:
    m = _HASH_NAME.match(inner) or _HEX_NAME.match(inner)
    if m:
        return int(m.group(1), 16)
    return lookup3((inner if inner.endswith(":") else f"[{inner}]").encode("latin-1"))


def load_names() -> dict[int, str]:
    global _NAMES
    if _NAMES is None:
        raw = json.loads(_NAMES_PATH.read_text(encoding="utf-8")) if _NAMES_PATH.is_file() else []
        _NAMES = {lookup3(n.encode("latin-1")): n for n in raw}
    return _NAMES


def rc4(data: bytes, key: bytes = _TEXT_KEY) -> bytes:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray(len(data))
    for n, b in enumerate(data):
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out[n] = b ^ s[(s[i] + s[j]) & 0xFF]
    return bytes(out)


def parse_container(data: bytes) -> tuple[list[tuple[int, bytes]], int]:
    if data[:4] != MAGIC:
        raise ValueError(f"not an ShCB file (magic={data[:4]!r})")
    n = int.from_bytes(data[0xC:0xE], "little")
    ver = u32(data, 4)
    chunks = []
    for i in range(n):
        off = 0x10 + i * 12
        cid, clen, coff = u32(data, off), u32(data, off + 4), u32(data, off + 8)
        chunks.append((cid, data[coff : coff + clen]))
    return chunks, ver


def build_container(chunks: list[tuple[int, bytes]], version: int = VERSION) -> bytes:
    n = len(chunks)
    table = 0x10 + n * 12
    out = bytearray(table)
    out[0:4] = MAGIC
    out[4:8] = p32(version)
    out[12:14] = n.to_bytes(2, "little")
    pos = table
    for i, (cid, blob) in enumerate(chunks):
        e = 0x10 + i * 12
        out[e : e + 4] = p32(cid)
        out[e + 4 : e + 8] = p32(len(blob))
        out[e + 8 : e + 12] = p32(pos)
        out.extend(blob)
        pos += len(blob)
    out[8:12] = p32(len(out))
    return bytes(out)


def _size2(t: int) -> int:
    return (1, 4, 4, 8)[t]


def packed_size(ptr: bytes) -> int:
    if not ptr:
        return 0
    n = ptr[0] & 0x0F
    extra = (max(0, n - 2) + 3) >> 2
    tb = 1 + extra
    types = [(ptr[0] >> 4) & 3]
    if n > 1:
        types.append((ptr[0] >> 6) & 3)
    idx = 2
    for bi in range(1, tb):
        b = ptr[bi]
        for slot in range(4):
            if idx >= n:
                break
            types.append((b >> (slot * 2)) & 3)
            idx += 1
    return tb + sum(_size2(t) for t in types[:n])


def decode_packed(ptr: bytes) -> list[tuple[int, object]]:
    n = ptr[0] & 0x0F
    if n == 0:
        return []
    extra = (max(0, n - 2) + 3) >> 2
    tb = 1 + extra
    types = [(ptr[0] >> 4) & 3]
    if n > 1:
        types.append((ptr[0] >> 6) & 3)
    idx = 2
    for bi in range(1, tb):
        b = ptr[bi]
        for slot in range(4):
            if idx >= n:
                break
            types.append((b >> (slot * 2)) & 3)
            idx += 1
    types = types[:n]
    p = tb
    out = []
    for t in types:
        sz = _size2(t)
        out.append((t, _dec_s(t, ptr[p : p + sz])))
        p += sz
    return out


def encode_packed(elems: list[tuple[int, bytes]]) -> bytes:
    n = len(elems)
    types = [t for t, _ in elems]
    b0 = n & 0x0F
    if n:
        b0 |= (types[0] & 3) << 4
    if n > 1:
        b0 |= (types[1] & 3) << 6
    out = bytearray([b0])
    rem = types[2:]
    for i in range(0, len(rem), 4):
        byte = 0
        for slot, t in enumerate(rem[i : i + 4]):
            byte |= (t & 3) << (slot * 2)
        out.append(byte)
    for _, raw in elems:
        out.extend(raw)
    return bytes(out)


def _dec_s(t: int, b: bytes):
    if t == 0:
        return struct.unpack("<b", b[:1])[0]
    if t == 1:
        return struct.unpack("<i", b[:4])[0]
    if t == 2:
        return struct.unpack("<f", b[:4])[0]
    if t == 3:
        return struct.unpack("<d", b[:8])[0]
    return None


def value_size(t: int, ptr: bytes) -> int | None:
    return {0: 1, 1: 4, 2: 4, 3: 8, 6: 1, 7: 2, 8: 0, 9: 0, 10: 12, 11: 16, 12: 0, 13: 0, 14: 8, 15: 0}.get(
        t, packed_size(ptr) if t in (4, 5) else None
    )


def record_len(payload: bytes, pos: int) -> int | None:
    h = payload[pos]
    count, enc = h & 0x0F, (h >> 5) & 3
    if enc == 3:
        return 5
    if enc == 1:
        sz = value_size(count, payload[pos + 5 :])
        return None if sz is None else 5 + sz
    if enc == 2:
        nb = (count + 1) >> 1
        p = pos + 1 + nb
        for i in range(count):
            b = payload[pos + 1 + (i >> 1)]
            t = (b & 0x0F) if (i & 1) == 0 else ((b >> 4) & 0x0F)
            sz = value_size(t, payload[p + 4 :])
            if sz is None:
                return None
            p += 4 + sz
        return p - pos
    if enc == 0:
        body = payload[pos + 1 :]
        types = [((body[i >> 2] >> ((i & 3) * 2)) & 3) for i in range(count)]
        return 1 + ((count + 3) >> 2) + sum(_size2(t) for t in types)
    return None


def decode_enc0(body: bytes, count: int) -> list[tuple[int, object]]:
    types = [((body[i >> 2] >> ((i & 3) * 2)) & 3) for i in range(count)]
    p = (count + 3) >> 2
    out = []
    for t in types:
        sz = _size2(t)
        out.append((t, _dec_s(t, body[p : p + sz])))
        p += sz
    return out


def encode_enc0(elems: list[tuple[int, bytes]]) -> bytes:
    n = len(elems)
    tb = bytearray((n + 3) >> 2)
    for i, (t, _) in enumerate(elems):
        tb[i >> 2] |= (t & 3) << ((i & 3) * 2)
    out = bytearray(tb)
    for _, raw in elems:
        out.extend(raw)
    return bytes(out)


def _hdr(enc: int, count: int, bit7: int = 0) -> bytes:
    return bytes([((bit7 & 1) << 7) | ((enc & 3) << 5) | (count & 0x0F)])


def parse_stream(payload: bytes) -> list[dict]:
    recs, pos = [], 0
    while pos < len(payload):
        rlen = record_len(payload, pos)
        if rlen is None or rlen <= 0 or pos + rlen > len(payload):
            raise ValueError(f"unparsed tail at 0x{pos:x}")
        rec = payload[pos : pos + rlen]
        h, enc, count, bit7 = rec[0], (rec[0] >> 5) & 3, rec[0] & 0x0F, rec[0] >> 7
        if enc == 3:
            recs.append({"kind": "sec", "id": u32(rec, 1), "bit7": bit7})
        elif enc == 1:
            recs.append({"kind": "params", "items": [(u32(rec, 1), count, rec[5:])], "bit7": bit7})
        elif enc == 2:
            nb = (count + 1) >> 1
            p, items = 1 + nb, []
            for i in range(count):
                b = rec[1 + (i >> 1)]
                t = (b & 0x0F) if (i & 1) == 0 else ((b >> 4) & 0x0F)
                sz = value_size(t, rec[p + 4 :])
                assert sz is not None
                items.append((u32(rec, p), t, rec[p + 4 : p + 4 + sz]))
                p += 4 + sz
            recs.append({"kind": "params", "items": items, "bit7": bit7})
        else:
            recs.append({"kind": "enc0", "vals": decode_enc0(rec[1:], count)})
        pos += rlen
    return recs


def encode_stream(recs: list[dict]) -> bytes:
    out = bytearray()
    seen_br = False
    seen_params = False
    for rec in recs:
        kind = rec["kind"]
        if kind == "sec":
            inner = rec.get("inner") or ""
            bit7 = rec.get("bit7")
            if bit7 is None:
                if inner.endswith(":"):
                    bit7 = 0
                else:
                    bit7 = 1 if (seen_br or seen_params) else 0
                    seen_br = True
            elif not inner.endswith(":"):
                seen_br = True
            out += _hdr(3, 0, bit7) + p32(rec["id"])
        elif kind == "enc0":
            seen_params = True
            elems = rec["elems"]
            out += _hdr(0, len(elems)) + encode_enc0(elems)
        else:
            seen_params = True
            items = rec["items"]
            bit7 = rec.get("bit7") or 0
            if len(items) == 1:
                pid, t, raw = items[0]
                out += _hdr(1, t, bit7) + p32(pid) + raw
            else:
                n = len(items)
                nb = (n + 1) >> 1
                nib = bytearray(nb)
                for i, (_, t, _) in enumerate(items):
                    if i & 1:
                        nib[i >> 1] |= (t & 0x0F) << 4
                    else:
                        nib[i >> 1] |= t & 0x0F
                body = bytearray(_hdr(2, n, bit7) + bytes(nib))
                for pid, _, raw in items:
                    body += p32(pid) + raw
                out += body
    return bytes(out)


def pool_lookup(blob: bytes, off: int) -> str:
    if off < 0 or off >= len(blob):
        return ""
    end = blob.find(b"\x00", off)
    raw = blob[off:] if end < 0 else blob[off:end]
    return raw.decode("latin-1")


def build_pool(strings: list[str]) -> tuple[bytes, list[int]]:
    pool = bytearray()
    seen: dict[str, int] = {}
    offs = []
    for s in strings:
        if s in seen:
            offs.append(seen[s])
            continue
        if s == "" and pool and pool[-1] == 0:
            seen[s] = len(pool) - 1
        else:
            seen[s] = len(pool)
            pool.extend(s.encode("latin-1"))
            pool.append(0)
        offs.append(seen[s])
    return bytes(pool), offs


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


def fmt_f64(x: float) -> str:
    s = format(x, ".17g")
    if "." not in s and "e" not in s.lower():
        s += ".0"
    return s


def fmt_scalar(t: int, raw: bytes, pool: bytes) -> str:
    if t in (4, 5):
        return "(" + ", ".join(fmt_elem(tt, v) for tt, v in decode_packed(raw)) + ")"
    if t == 0:
        return str(struct.unpack("<b", raw[:1])[0])
    if t == 1:
        return str(struct.unpack("<i", raw[:4])[0])
    if t == 2:
        return fmt_f32(struct.unpack("<f", raw[:4])[0])
    if t == 3:
        return fmt_f64(struct.unpack("<d", raw[:8])[0])
    if t == 6:
        return fmt_str(pool_lookup(pool, raw[0] if raw else 0))
    if t == 7:
        off = int.from_bytes(raw[:2], "little") if len(raw) >= 2 else 0
        return fmt_str(pool_lookup(pool, off))
    if t == 8:
        return "0"
    if t == 10:
        return "(" + ", ".join(fmt_f32(x) for x in struct.unpack("<fff", raw[:12])) + ")"
    if t == 11:
        return "(" + ", ".join(fmt_f32(x) for x in struct.unpack("<ffff", raw[:16])) + ")"
    if t == 14:
        return fmt_f64(struct.unpack("<d", raw[:8])[0])
    return "0" if not raw else raw.hex()


def fmt_elem(t2: int, v) -> str:
    if t2 in (0, 1):
        return str(int(v))
    if t2 == 3:
        return fmt_f64(float(v))
    return fmt_f32(float(v))


def fmt_str(s: str) -> str:
    return s if _IDENT.fullmatch(s) else json.dumps(s)


def param_label(pid: int, names: dict[int, str]) -> str:
    return names.get(pid) or f"h_{pid:08x}"


def section_label(sid: int, names: dict[int, str]) -> str:
    mapped = names.get(sid)
    if not mapped:
        return f"[h_{sid:08x}]"
    return mapped if mapped.startswith("[") else f"[{mapped}]"


def to_text(recs: list[dict], pool: bytes, names: dict[int, str]) -> str:
    lines: list[str] = []
    for rec in recs:
        if rec["kind"] == "sec":
            if lines:
                lines.append("")
            lines.append(section_label(rec["id"], names))
        elif rec["kind"] == "enc0":
            lines.extend(fmt_elem(t, v) for t, v in rec["vals"])
        else:
            if rec.get("bit7") and lines and lines[-1] != "":
                lines.append("")
            for pid, t, raw in rec["items"]:
                name = param_label(pid, names)
                lines.append(f"{name}={fmt_scalar(t, raw, pool)}" + ("  # t=3" if t == 3 else ""))
    return "\n".join(lines) + ("\n" if lines else "")


def _strip_comment(line: str) -> tuple[str, str]:
    in_str = False
    depth = 0
    i = 0
    while i < len(line):
        c = line[i]
        if in_str:
            if c == "\\" and i + 1 < len(line):
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and (c == "#" or line.startswith("//", i)):
            return line[:i].rstrip(), line[i:]
        i += 1
    return line, ""


def _parse_num(tok: str) -> tuple[str, int | float]:
    if re.search(r"[.eE]", tok):
        return "f", float(tok)
    return "i", int(tok, 10)


def _infer_elem(kind: str, v) -> tuple[int, bytes]:
    if kind == "i":
        iv = int(v)
        if -128 <= iv <= 127:
            return 0, struct.pack("<b", iv)
        return 1, struct.pack("<i", iv)
    return 2, struct.pack("<f", float(v))


def _parse_tuple(s: str, i: int) -> tuple[list[tuple[str, int | float]], int]:
    assert s[i] == "("
    i += 1
    elems = []
    while i < len(s):
        while i < len(s) and s[i] in " \t,":
            i += 1
        if i < len(s) and s[i] == ")":
            return elems, i + 1
        m = _NUM.match(s, i)
        if not m:
            raise ValueError(f"bad packed value at {s[i:i+20]!r}")
        elems.append(_parse_num(m.group()))
        i = m.end()
    raise ValueError("unclosed packed value")


def _parse_string(s: str, i: int) -> tuple[str, int]:
    if s[i] == '"':
        i += 1
        out = []
        while i < len(s):
            c = s[i]
            if c == "\\":
                out.append(s[i + 1] if i + 1 < len(s) else "")
                i += 2
                continue
            if c == '"':
                return "".join(out), i + 1
            out.append(c)
            i += 1
        raise ValueError("unclosed string")
    j = i
    while j < len(s) and not s[j].isspace():
        j += 1
    return s[i:j], j


_Val = (
    tuple[Literal["flag"], int]
    | tuple[Literal["pack"], list[tuple[str, int | float]]]
    | tuple[Literal["str"], str]
    | tuple[Literal["num"], tuple[str, int | float]]
)


def _parse_value(s: str, i: int) -> tuple[_Val, int]:
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s):
        return ("flag", 0), i
    if s[i] == "(":
        elems, i = _parse_tuple(s, i)
        return ("pack", elems), i
    if s[i] == '"':
        text, i = _parse_string(s, i)
        return ("str", text), i
    m = _NUM.match(s, i)
    if m:
        end = m.end()
        if end >= len(s) or not (s[end].isalnum() or s[end] == "_"):
            return ("num", _parse_num(m.group())), end
    text, i = _parse_string(s, i)
    return ("str", text), i


def _parse_assignments(s: str) -> list[tuple[str, _Val]]:
    items = []
    i, n = 0, len(s)
    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break
        depth, in_str, eq = 0, False, -1
        j = i
        while j < n:
            c = s[j]
            if in_str:
                if c == "\\" and j + 1 < n:
                    j += 2
                    continue
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "=" and depth == 0:
                eq = j
                break
            j += 1
        if eq < 0:
            name = s[i:].strip()
            if name:
                items.append((name, ("flag", 0)))
            break
        name = s[i:eq].strip()
        val, i = _parse_value(s, eq + 1)
        items.append((name, val))
    return items


def parse_text(text: str) -> list[dict]:
    recs = []
    pending_blank = False
    for raw in text.splitlines():
        line, comment = _strip_comment(raw)
        line = line.strip()
        if not line:
            pending_blank = True
            continue
        t_over = None
        tm = re.search(r"t\s*=\s*(\d+)", comment)
        if tm:
            t_over = int(tm.group(1))
        if line.startswith("[") and line.endswith("]"):
            inner = line[1:-1]
            recs.append({"kind": "sec", "id": hash_section(inner), "inner": inner})
            pending_blank = False
            continue
        if "=" not in line and all(_NUM.fullmatch(tok) for tok in line.split()):
            elems = [_infer_elem(*_parse_num(tok)) for tok in line.split()]
            recs.append({"kind": "enc0", "elems": elems})
            pending_blank = False
            continue
        items = []
        for name, val in _parse_assignments(line):
            pid = hash_name(name)
            if val[0] == "flag" or (val[0] == "num" and val[1] == ("i", 0) and t_over is None):
                items.append((pid, 8, b""))
            elif val[0] == "pack":
                packed = encode_packed([_infer_elem(k, v) for k, v in val[1]])
                items.append((pid, t_over or 4, packed))
            elif val[0] == "str":
                items.append((pid, 6, val[1]))
            else:
                nk, nv = val[1]
                t = t_over if t_over is not None else (2 if nk == "f" else (0 if -128 <= int(nv) <= 127 else 1))
                if t in (4, 5):
                    items.append((pid, t, encode_packed([_infer_elem(nk, nv)])))
                elif t in (6, 7):
                    items.append((pid, t, str(nv)))
                elif t == 8:
                    items.append((pid, 8, b""))
                elif t == 3:
                    items.append((pid, 3, struct.pack("<d", float(nv))))
                elif t == 2:
                    items.append((pid, 2, struct.pack("<f", float(nv))))
                elif t == 1:
                    items.append((pid, 1, struct.pack("<i", int(nv))))
                else:
                    items.append((pid, 0, struct.pack("<b", int(nv))))
        recs.append({"kind": "params", "items": items, "bit7": 1 if pending_blank else 0})
        pending_blank = False
    return recs


def _bind_strings(recs: list[dict]) -> tuple[list[dict], bytes]:
    order = []
    for rec in recs:
        if rec["kind"] != "params":
            continue
        new = []
        for pid, t, raw in rec["items"]:
            if t in (6, 7) and isinstance(raw, str):
                order.append(raw)
                new.append((pid, t, raw))
            else:
                new.append((pid, t, raw))
        rec["items"] = new
    pool, offs = build_pool(order)
    it = iter(offs)
    for rec in recs:
        if rec["kind"] != "params":
            continue
        bound = []
        for pid, t, raw in rec["items"]:
            if t in (6, 7) and isinstance(raw, str):
                off = next(it)
                if off <= 255:
                    bound.append((pid, 6, bytes([off])))
                else:
                    bound.append((pid, 7, off.to_bytes(2, "little")))
            else:
                bound.append((pid, t, raw))
        rec["items"] = bound
    return recs, pool


def unpack_bytes(data: bytes) -> str:
    chunks, _ = parse_container(data)
    stream = pool = b""
    for cid, blob in chunks:
        if cid == STREAM_ID:
            stream = blob
        elif cid == TEXT_ID:
            pool = rc4(blob)
    return to_text(parse_stream(stream), pool, load_names())


def pack_bytes(text: str, version: int = VERSION) -> bytes:
    recs, pool = _bind_strings(parse_text(text))
    chunks = [(STREAM_ID, encode_stream(recs))]
    if pool:
        chunks.append((TEXT_ID, rc4(pool)))
    return build_container(chunks, version)


def bin_to_text_path(path: Path) -> Path:
    suf = path.suffix
    if suf.lower().endswith("bin") and len(suf) > 4:
        return path.with_suffix(suf[:-3])
    return path.with_suffix(path.suffix + ".txt")


def text_to_bin_path(path: Path) -> Path:
    suf = path.suffix
    if suf and not suf.lower().endswith("bin"):
        return path.with_suffix(suf + "bin")
    return path.with_suffix(path.suffix + ".bin")


def unpack_file(src: Path, dst: Path | None = None) -> Path:
    src = Path(src)
    dst = Path(dst) if dst else bin_to_text_path(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(unpack_bytes(src.read_bytes()), encoding="utf-8")
    return dst


def pack_file(src: Path, dst: Path | None = None) -> Path:
    src = Path(src)
    dst = Path(dst) if dst else text_to_bin_path(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(pack_bytes(src.read_text(encoding="utf-8")))
    return dst
