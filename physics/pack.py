"""Pack editable physics text into Madness Engine binaries."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from csdbin import pack_file as pack_csd
from dfbin import pack_file as pack_dfbin
from vdfm import pack_file as pack_vdfm


def _is_csd_text(text: str) -> bool:
    head = text[:2000]
    return "sound_class" in head or "[links]" in head


def _is_vdfm_text(text: str) -> bool:
    head = text.lstrip()
    return head.startswith("id") or head.startswith("schema") or "[lookups]" in text[:4000]


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack physics text to ShCB *.*bin, VDFM .vdfm, or CSDBIN .csdbin")
    ap.add_argument("input", type=Path, help="Input text (*.cdf / *.edf / *.vdf / *.csd / ...)")
    ap.add_argument("output", nargs="?", type=Path, help="Output binary path")
    ns = ap.parse_args()
    text = ns.input.read_text(encoding="utf-8")
    if _is_csd_text(text):
        out = pack_csd(ns.input, ns.output)
    elif _is_vdfm_text(text):
        out = pack_vdfm(ns.input, ns.output)
    else:
        out = pack_dfbin(ns.input, ns.output)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
