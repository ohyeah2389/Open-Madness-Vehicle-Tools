"""Pack editable physics text into Madness Engine binaries."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dfbin import pack_file as pack_dfbin
from vdfm import pack_file as pack_vdfm


def _is_vdfm_text(text: str) -> bool:
    head = text.lstrip()
    return head.startswith("id") or head.startswith("schema") or "[lookups]" in text[:4000]


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack physics text to ShCB *.*bin or VDFM .vdfm")
    ap.add_argument("input", type=Path, help="Input text (*.cdf / *.edf / *.vdf / ...)")
    ap.add_argument("output", nargs="?", type=Path, help="Output binary path")
    ns = ap.parse_args()
    text = ns.input.read_text(encoding="utf-8")
    out = pack_vdfm(ns.input, ns.output) if _is_vdfm_text(text) else pack_dfbin(ns.input, ns.output)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
