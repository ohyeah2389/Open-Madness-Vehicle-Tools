"""Convert Madness Engine ShCB physics *.*bin files to editable text."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dfbin import unpack_file


def main() -> None:
    ap = argparse.ArgumentParser(description="Unpack ShCB physics *.*bin to text")
    ap.add_argument("input", type=Path, help="Input *.cdfbin / *.edfbin / *.sdfbin / ...")
    ap.add_argument("output", nargs="?", type=Path, help="Output text path (default: strip 'bin')")
    ns = ap.parse_args()
    out = unpack_file(ns.input, ns.output)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
