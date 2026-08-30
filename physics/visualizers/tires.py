"""Legacy HDT slipcurves"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import nums, strip

_NAME = re.compile(r'^(?:name|Name)\s*=\s*"?([^"\s]+)"?', re.I)
_STEP = re.compile(r"^Step\s*=\s*([\d.eE+-]+)", re.I)
_VALS = re.compile(r"^vals\s*=\s*\((.*)\)", re.I)


def parse_slipcurves(text: str) -> dict[str, dict]:
    curves, i, lines = {}, 0, text.splitlines()
    while i < len(lines):
        if not re.match(r"\[SLIPCURVE\]", lines[i].strip(), re.I):
            i += 1
            continue
        i += 1
        name, step, data, in_data = f"curve{len(curves)}", 0.1, [], False
        while i < len(lines):
            raw = lines[i]
            line = strip(raw).strip()
            if line.startswith("[") and not re.match(r"\[DATA", line, re.I):
                break
            if m := _NAME.match(line):
                name = m.group(1)
            elif m := _STEP.match(line):
                step = float(m.group(1))
            elif m := _VALS.match(line):
                data += nums(f"({m.group(1)})")
            elif re.match(r"^\[DATA", line, re.I) or re.match(r"^Data\s*:", line, re.I):
                in_data = True
            elif in_data:
                if not line or line.startswith("["):
                    in_data = False
                    if line.startswith("["):
                        break
                else:
                    data += [float(x) for x in line.split()]
            i += 1
        if data:
            curves[name] = {"step": step, "data": data}
    return curves


def main() -> None:
    p = argparse.ArgumentParser(description="Plot legacy HDT slipcurves (AMS2 or Shift2 text).")
    p.add_argument("hdt", type=Path, help="Decoded .hdt or Shift2 plaintext .hdt")
    p.add_argument("-o", "--output", type=Path)
    args = p.parse_args()
    if not args.hdt.is_file():
        sys.exit(f"not a file: {args.hdt}")
    curves = parse_slipcurves(args.hdt.read_text(encoding="utf-8", errors="replace"))
    if not curves:
        sys.exit(f"no [SLIPCURVE] in {args.hdt}")
    fig, ax = plt.subplots(figsize=(10, 6))
    for name, c in curves.items():
        x = np.arange(len(c["data"])) * c["step"]
        ax.plot(x, c["data"], lw=2, label=name)
    ax.set_xlabel("Slip")
    ax.set_ylabel("Friction coefficient")
    ax.set_title(args.hdt.stem)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    fig.tight_layout()
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Wrote {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
