"""Repack editable physics text into Madness Engine ShCB *.*bin files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dfbin import pack_file


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack physics text to ShCB *.*bin")
    ap.add_argument("input", type=Path, help="Input text (*.cdf / *.edf / *.sdf / ...)")
    ap.add_argument("output", nargs="?", type=Path, help="Output *.*bin path (default: add 'bin')")
    ns = ap.parse_args()
    out = pack_file(ns.input, ns.output)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
