"""Unpack a cockpit.bin, motecdisplay.bin, or pitcontroller.bin to editable INI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cockpit_bin import unpack_bytes as unpack_cockpit
from motecdisplay import unpack_bytes as unpack_motec
from pitcontroller import unpack_bytes as unpack_pit


def output_path(src: Path, dest: Path | None) -> Path:
    if dest:
        return dest
    return src.with_suffix(".ini") if src.suffix.lower() == ".bin" else src.with_name(src.name + ".ini")


def unpack_file(src: Path, dest: Path | None = None) -> Path:
    raw = src.read_bytes()

    # somewhat sketchy heuristic
    if b"Container" in raw:
        text = unpack_cockpit(raw)
    elif b"JackGT" in raw:
        text = unpack_pit(raw)
    else:
        text = unpack_motec(raw)

    out = output_path(src, dest)
    out.write_text(text, encoding="utf-8", newline="\n")

    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Unpack cockpit.bin, motecdisplay.bin, or pitcontroller.bin to INI")
    ap.add_argument("input", type=Path)
    ap.add_argument("output", nargs="?", type=Path)
    ns = ap.parse_args()
    print(f"wrote {unpack_file(ns.input, ns.output)}")


if __name__ == "__main__":
    main()
