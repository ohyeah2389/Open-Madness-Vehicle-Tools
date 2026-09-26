"""Pack cockpit, motecdisplay, or pitcontroller INI back to a binary."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cockpit_bin import pack_bytes as pack_cockpit
from motecdisplay import pack_bytes as pack_motec
from pitcontroller import pack_bytes as pack_pit


def output_path(src: Path, dest: Path | None) -> Path:
    if dest:
        return dest
    return src.with_suffix(".bin") if src.suffix.lower() == ".ini" else src.with_name(src.name + ".bin")


def pack_file(src: Path, dest: Path | None = None) -> Path:
    text = src.read_text(encoding="utf-8")
    head = text.lstrip()
    if head.startswith("[motecdisplay]") or head.startswith("format = motecdisplay"):
        raw = pack_motec(text)
    elif head.startswith("[pitcontroller]"):
        raw = pack_pit(text)
    else:
        raw = pack_cockpit(text)
    out = output_path(src, dest)
    out.write_bytes(raw)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack cockpit, motecdisplay, or pitcontroller INI to a binary")
    ap.add_argument("input", type=Path)
    ap.add_argument("output", nargs="?", type=Path)
    ns = ap.parse_args()
    print(f"wrote {pack_file(ns.input, ns.output)}")


if __name__ == "__main__":
    main()
