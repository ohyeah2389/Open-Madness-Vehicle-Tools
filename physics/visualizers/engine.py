from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import interp1, kv_rows, lookup_paths, redline

BOOST_TH = (0.0, 25.0, 50.0, 75.0, 100.0)


def torque_tables(edf: Path) -> list[list[tuple[float, float, float]]]:
    tables, cur = [], []
    for row in kv_rows(edf, "RPMTorque"):
        if len(row) < 2:
            continue
        rpm, zero = row[0], row[1]
        full = row[2] if len(row) > 2 else zero
        if cur and rpm < cur[-1][0]:
            tables.append(cur)
            cur = []
        cur.append((rpm, zero, full))
    if cur:
        tables.append(cur)
    return tables


def boost_table(edf: Path) -> list[tuple[float, tuple[float, ...]]] | None:
    rows = []
    for row in kv_rows(edf, "RPMBoost"):
        if len(row) >= 6:
            rows.append((row[0], tuple(row[1:6])))
    return rows or None


def boost_at(table, rpm: float, throttle: float) -> float:
    xs = [r[0] for r in table]
    cols = [[r[1][i] for r in table] for i in range(5)]
    knots = [interp1(xs, c, rpm) for c in cols]
    return interp1(list(BOOST_TH), knots, throttle)


def throttle_map(edf: Path) -> dict[float, list[tuple[float, float]]]:
    by_mode: dict[int, list[tuple[float, float, float]]] = defaultdict(list)
    for row in kv_rows(edf, "VThrottleGear"):
        if len(row) != 4:
            continue
        by_mode[int(row[0])].append((row[1], row[2], row[3]))
    if not by_mode:
        return {}
    mode = max(by_mode, key=lambda m: len(by_mode[m]))
    by_th: dict[float, list[tuple[float, float]]] = defaultdict(list)
    for th, pct, load in by_mode[mode]:
        by_th[th].append((pct, load))
    return {th: sorted(pts) for th, pts in by_th.items()}


def load_at(curve: list[tuple[float, float]], pct: float) -> float:
    return interp1([p[0] for p in curve], [p[1] for p in curve], pct)


def blend(zero, full, load):
    return zero + load * (full - zero)


def main() -> None:
    p = argparse.ArgumentParser(description="Plot engine torque (load envelope, throttle, boost).")
    p.add_argument("path", type=Path, help="Decoded .edf, or .vdf to look up the engine")
    p.add_argument("-o", "--output", type=Path)
    args = p.parse_args()
    path = args.path.resolve()
    edf = lookup_paths(path).get("engine") if path.suffix.lower() == ".vdf" else path
    if not edf or not edf.is_file():
        sys.exit(f"no engine file for {path}")
    tables = torque_tables(edf)
    if not tables:
        sys.exit(f"no RPMTorque in {edf}")
    rows = max(tables, key=len)
    rpm = np.array([r[0] for r in rows])
    zero = np.array([r[1] for r in rows])
    full = np.array([r[2] for r in rows])
    boost = boost_table(edf)
    tmap = throttle_map(edf)
    limit = redline(edf)
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.fill_between(rpm, zero, full, color="#ced4da", alpha=0.45, zorder=0)
    ax.plot(rpm, zero, color="#495057", lw=2.2, label="Zero load", zorder=4)
    ax.plot(rpm, full, color="#111", lw=2.2, label="Full load", zorder=4)
    if boost:
        ax.plot(rpm, [full[i] * boost_at(boost, rpm[i], 100) for i in range(len(rpm))], color="#111", lw=2.0, ls="--", label="Full load (boosted)", zorder=4)
    cmap = plt.colormaps["turbo"]
    throttles = sorted(t for t in tmap if 0 < t < 100)
    for th in throttles:
        curve = tmap[th]
        y = [blend(zero[i], full[i], load_at(curve, 100 * rpm[i] / limit if limit else 0)) for i in range(len(rpm))]
        color = cmap(th / 100)
        ax.plot(rpm, y, color=color, lw=0.95, alpha=0.85, zorder=3)
        if boost:
            yb = [y[i] * boost_at(boost, rpm[i], th) for i in range(len(rpm))]
            if max(abs(yb[i] - y[i]) for i in range(len(rpm))) > 1e-3:
                ax.plot(rpm, yb, color=color, lw=0.95, ls="--", alpha=0.75, zorder=2)
    ax.axvline(limit, color="#adb5bd", lw=0.8, ls=":")
    ax.set_xlabel("Engine RPM")
    ax.set_ylabel("Torque (Nm)")
    ax.set_title(edf.stem)
    ax.grid(True, alpha=0.28)
    handles = [
        Line2D([0], [0], color="#495057", lw=2.2, label="Zero load"),
        Line2D([0], [0], color="#111", lw=2.2, label="Full load"),
    ]
    if boost:
        handles.append(Line2D([0], [0], color="#111", lw=2, ls="--", label="Boosted"))
    for th in (25, 50, 75):
        if th in tmap:
            handles.append(Line2D([0], [0], color=cmap(th / 100), lw=1.6, label=f"{th:.0f}% throttle"))
    ax.legend(handles=handles, loc="best", fontsize=8)
    fig.tight_layout()
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Wrote {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
