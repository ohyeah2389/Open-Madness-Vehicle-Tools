"""Unpack Madness Engine vehicle physics binaries to editable text."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from csdbin import MAGIC as CSD_MAGIC
from csdbin import unpack_file as unpack_csd
from dfbin import MAGIC as SHCB_MAGIC
from dfbin import unpack_file as unpack_dfbin
from vdfm import MAGIC as VDFM_MAGIC
from vdfm import unpack_file as unpack_vdfm


def main() -> None:
    ap = argparse.ArgumentParser(description="Unpack ShCB *.*bin, VDFM .vdfm, or CSDBIN .csdbin to text")
    ap.add_argument("input", type=Path, help="Input *.cdfbin / *.edfbin / *.vdfm / *.csdbin / ...")
    ap.add_argument("output", nargs="?", type=Path, help="Output text path")
    ns = ap.parse_args()
    magic = ns.input.read_bytes()[:4]
    if magic == SHCB_MAGIC:
        out = unpack_dfbin(ns.input, ns.output)
    elif magic == VDFM_MAGIC:
        out = unpack_vdfm(ns.input, ns.output)
    elif magic == CSD_MAGIC:
        out = unpack_csd(ns.input, ns.output)
    else:
        raise SystemExit(f"unknown physics container: {ns.input}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
