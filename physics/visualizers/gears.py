from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import _KV, first_kv, idle_rpm, lookup_paths, nums, redline, strip, wheel_geo


def cog_ratio(pair: list[float]) -> float:
    return pair[1] / pair[0] if pair[0] else 0.0


def gdf_cogs(path: Path) -> tuple[list[list[float]], list[list[float]], list[float]]:
    section, primaries, finals, bevel = None, [], [], [1.0, 1.0]
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = strip(raw).strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        m = _KV.match(line)
        if not m:
            continue
        key, pair = m.group(1), nums(m.group(2))
        if key == "bevel":
            bevel = pair
        elif key == "ratio" and len(pair) >= 2:
            (primaries if section == "GEAR_RATIOS" else finals).append(pair)
    return primaries, finals, bevel


def setting(path: Path, name: str, default: int = 0) -> int:
    v = first_kv(path, name, default)
    if v is None:
        return default
    return int(v if not isinstance(v, list) else v[0])


def main() -> None:
    p = argparse.ArgumentParser(description="Plot selected gears vs unused GDF ratios, in km/h.")
    p.add_argument("vdf", nargs="?", type=Path, help="Decoded .vdf (looks up gearbox, chassis, engine)")
    p.add_argument("--vdf", dest="vdf_opt", type=Path)
    p.add_argument("--gdf", type=Path)
    p.add_argument("--cdf", type=Path)
    p.add_argument("--edf", type=Path)
    p.add_argument("-o", "--output", type=Path)
    args = p.parse_args()
    vdf = args.vdf_opt or args.vdf
    gdf, cdf, edf = args.gdf, args.cdf, args.edf
    if vdf:
        found = lookup_paths(vdf)
        gdf = gdf or found.get("gearbox")
        cdf = cdf or found.get("chassis")
        edf = edf or found.get("engine")
    if not gdf or not gdf.is_file() or not cdf or not cdf.is_file():
        sys.exit("need decoded .gdf and .cdf (pass a .vdf or --gdf/--cdf)")
    primaries, finals, bevel = gdf_cogs(gdf)
    if not primaries:
        sys.exit(f"no gear ratios in {gdf}")
    n_fwd = setting(cdf, "ForwardGears", len(primaries))
    selected = []
    for i in range(1, n_fwd + 1):
        idx = setting(cdf, f"Gear{i}Setting", i - 1)
        if 0 <= idx < len(primaries):
            selected.append((i, idx, primaries[idx]))
    used = {idx for _, idx, _ in selected}
    fd_i = setting(cdf, "FinalDriveSetting", 0)
    final = finals[fd_i] if finals and 0 <= fd_i < len(finals) else (finals[0] if finals else [1.0, 1.0])
    overall_final = cog_ratio(bevel) * cog_ratio(final)
    radius = 0.32
    if vdf and vdf.is_file():
        hs = [w["height"] / 2 for w in wheel_geo(vdf).values()]
        if hs:
            radius = float(np.mean(hs))
    lo, hi = idle_rpm(edf), redline(edf)
    rpms = np.linspace(max(lo, 500), hi, 80)

    def speed_kmh(overall: float):
        return (rpms / overall) / 60.0 * 2 * np.pi * radius * 3.6

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    cmap = plt.colormaps["tab10"]
    for i, _, pair in selected:
        ax.plot(speed_kmh(cog_ratio(pair) * overall_final), rpms, color=cmap((i - 1) % 10), lw=2.0, label=f"{i}  {pair[0]:.0f}/{pair[1]:.0f}")
    unused = False
    for idx, pair in enumerate(primaries):
        if idx in used:
            continue
        ax.plot(speed_kmh(cog_ratio(pair) * overall_final), rpms, color="#cfd2d6", lw=1.0, zorder=0)
        unused = True
    ax.set_xlabel("Groundspeed (km/h)")
    ax.set_ylabel("Engine RPM")
    ax.set_title(f"{gdf.stem}  final {final[0]:.0f}/{final[1]:.0f}  bevel {bevel[0]:.0f}/{bevel[1]:.0f}")
    ax.grid(True, alpha=0.28)
    handles, labels = ax.get_legend_handles_labels()
    if unused:
        handles.append(Line2D([0], [0], color="#cfd2d6", lw=1.0, label="Unused ratio"))
        labels.append("Unused ratio")
    ax.legend(handles, labels, loc="best", fontsize=8, ncol=2)
    fig.tight_layout()
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Wrote {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
