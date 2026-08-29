"""Shared parsing for decoded Madness physics text."""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

_KV = re.compile(r"^([A-Za-z_][\w:]*)\s*=\s*(.*)$")
_FOLDERS = {
    "chassis": ("chassis", ".cdf"),
    "engine": ("engines", ".edf"),
    "gearbox": ("gearbox", ".gdf"),
    "suspension": ("suspension", ".sdf"),
    "tyre": ("tyres", ".hdt"),
}


def strip(line: str) -> str:
    in_str, depth, i = False, 0, 0
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
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def nums(raw: str) -> list[float]:
    s = raw.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    return [float(p) for p in s.split(",") if p.strip()]


def parse_file(path: Path) -> tuple[dict[str, str], dict[str, list[dict[str, str]]]]:
    """Return (top-level kv, section -> list of block dicts)."""
    meta, sections, cur, block = {}, defaultdict(list), None, {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = strip(raw).strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            if cur is not None:
                sections[cur].append(block)
            cur, block = line[1:-1], {}
            continue
        m = _KV.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip('"')
        if cur is None:
            meta[key] = val
        else:
            block.setdefault(key, [])
            block[key].append(val)
    if cur is not None:
        sections[cur].append(block)
    return meta, dict(sections)


def kv_rows(path: Path, name: str) -> list[list[float]]:
    """All tuples/scalars for a key, ignoring section."""
    out = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = strip(raw).strip()
        m = _KV.match(line)
        if m and m.group(1) == name:
            out.append(nums(m.group(2)))
    return out


def first_kv(path: Path, name: str, default=None):
    rows = kv_rows(path, name)
    if not rows:
        return default
    row = rows[0]
    return row[0] if len(row) == 1 else row


def physics_root(vdf: Path) -> Path:
    parent = vdf.resolve().parent
    return parent.parent if parent.name.lower() == "vehicles" else parent


def find_asset(root: Path, kind: str, name: str) -> Path | None:
    folder, ext = _FOLDERS[kind]
    d = root / folder
    if not d.is_dir() or not name:
        return None
    want = name.lower()
    hits = [p for p in d.iterdir() if p.is_file() and p.stem.lower() == want and p.suffix.lower() == ext]
    return hits[0] if hits else None


def lookup_paths(vdf: Path) -> dict[str, Path | None]:
    meta, secs = parse_file(vdf)
    lookups = {}
    for block in secs.get("lookups", [{}]):
        lookups.update({k: v[0] for k, v in block.items()})
    lookups.update({k: v for k, v in meta.items() if k in _FOLDERS})
    root = physics_root(vdf)
    return {kind: find_asset(root, kind, lookups[kind]) for kind in _FOLDERS if kind in lookups}


def wheel_geo(vdf: Path) -> dict[str, dict[str, float]]:
    _, secs = parse_file(vdf)
    kv = {}
    for block in secs.get("wheel_tire", [{}]):
        for k, vs in block.items():
            kv[k] = float(vs[0])
    if not kv:
        kv = {k: float(v) for k, v in parse_file(vdf)[0].items() if k.endswith("_m")}
    corners = {}
    for c in ("fl", "fr", "rl", "rr"):
        corners[c] = {
            "pos": (kv.get(f"{c}_lateral_offset_m", 0.0), kv.get(f"{c}_vertical_offset_m", 0.0), kv.get(f"{c}_fore_aft_offset_m", 0.0)),
            "width": kv.get(f"{c}_tyre_width_m", 0.2),
            "height": kv.get(f"{c}_tyre_height_m", 0.6),
        }
    return corners


def interp1(xs: list[float], ys: list[float], x: float) -> float:
    import numpy as np

    if len(xs) == 1:
        return ys[0]
    return float(np.interp(x, xs, ys))


def redline(edf: Path | None) -> float:
    if edf is None:
        return 8000.0
    rng = first_kv(edf, "RevLimitRange")
    setting = first_kv(edf, "RevLimitSetting", 0) or 0
    if rng is None:
        return 8000.0
    if not isinstance(rng, list):
        return float(rng)
    lo, step, steps = (rng + [0, 0, 0])[:3]
    if steps:
        return lo + setting * (step if step else 0)
    return lo


def idle_rpm(edf: Path | None) -> float:
    if edf is None:
        return 0.0
    v = first_kv(edf, "IdleRPMLogic")
    if v is None:
        return 0.0
    return v[0] if isinstance(v, list) else v
