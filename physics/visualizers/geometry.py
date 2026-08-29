from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _util import first_kv, lookup_paths, nums, parse_file, wheel_geo

SKIP_BODIES = {"fuel_tank", "driver_head"}


def parse_sdf(path: Path):
    _, secs = parse_file(path)
    bodies, bars, hinges = {}, [], []
    for b in secs.get("BODY", []):
        name = (b.get("name") or [""])[0]
        pos = nums((b.get("pos") or ["0,0,0"])[0])
        if len(pos) == 3:
            bodies[name] = tuple(pos)
    for b in secs.get("BAR", []):
        pos, neg = b.get("pos"), b.get("neg")
        if pos and neg:
            pv, nv = nums(pos[0]), nums(neg[0])
            if len(pv) == 3 and len(nv) == 3:
                bars.append((tuple(pv), tuple(nv), (b.get("name") or [""])[0]))
    for b in secs.get("JOINT&HINGE", []):
        axis = nums((b.get("axis") or ["0,0,0"])[0])
        pb = (b.get("posbody") or [""])[0]
        if len(axis) == 3:
            hinges.append((pb, tuple(axis)))
    return bodies, bars, hinges


def undertray(cdf: Path) -> list[tuple[float, float, float]]:
    pts = []
    for i in range(11):
        row = first_kv(cdf, f"Undertray{i:02d}")
        if row and len(row) == 3 and any(abs(v) > 1e-8 for v in row):
            pts.append((i, tuple(row)))
    return pts


def wheel_wires(center, radius, half_w, n=14):
    th = np.linspace(0, 2 * np.pi, n)
    y, z = radius * np.cos(th), radius * np.sin(th)
    x0, x1 = center[0] - half_w, center[0] + half_w
    rings = [np.column_stack([np.full(n, x), center[1] + y, center[2] + z]) for x in (x0, x1)]
    spokes = [np.array([[x0, center[1] + y[i], center[2] + z[i]], [x1, center[1] + y[i], center[2] + z[i]]]) for i in range(0, n, max(1, n // 8))]
    return rings, spokes


def set_equal(ax, pts):
    pts = np.asarray(pts)
    c, r = (pts.max(0) + pts.min(0)) / 2, (pts.max(0) - pts.min(0)).max() / 2 or 1
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect([1, 1, 1])


def main() -> None:
    p = argparse.ArgumentParser(description="Plot SDF suspension + CDF undertray + VDF wheels.")
    p.add_argument("vdf", nargs="?", type=Path, help="Decoded .vdf (auto-finds .sdf and .cdf)")
    p.add_argument("--vdf", dest="vdf_opt", type=Path, help="Decoded .vdf (when not positional)")
    p.add_argument("--sdf", type=Path)
    p.add_argument("--cdf", type=Path)
    p.add_argument("-o", "--output", type=Path)
    args = p.parse_args()
    vdf = args.vdf_opt or args.vdf
    sdf, cdf = args.sdf, args.cdf
    if vdf:
        found = lookup_paths(vdf)
        sdf = sdf or found.get("suspension")
        cdf = cdf or found.get("chassis")
    if not sdf or not sdf.is_file():
        sys.exit("need a decoded .sdf (pass --sdf or a .vdf with suspension=)")
    bodies, bars, hinges = parse_sdf(sdf)
    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")
    pts = []
    for pos, neg, _ in bars:
        ax.plot(*zip(pos, neg), color="#2a9d8f", lw=1.6, alpha=0.9)
        pts += [pos, neg]
    for name, pos in bodies.items():
        skip = name.lower() in SKIP_BODIES
        ax.scatter(*pos, s=18 if skip else 36, c="#264653" if not skip else "#aaa", zorder=5)
        pts.append(pos)
    for pb, axis in hinges:
        origin = bodies.get(pb)
        if not origin:
            continue
        a = np.array(axis, float)
        n = np.linalg.norm(a) or 1
        d = 0.12 * a / n
        ax.plot(*zip(origin - d, origin + d), color="#9b5de5", lw=1.2)
    if cdf and cdf.is_file():
        tray = undertray(cdf)
        by_i = {i: xyz for i, xyz in tray}
        for _, xyz in tray:
            ax.scatter(*xyz, s=28, c="#e76f51", zorder=6)
            pts.append(xyz)
        loops = ((0, 2, 3, 1), (4, 6, 7, 5), (8, 0, 1, 9), (0, 4, 6, 2), (1, 5, 7, 3))
        for loop in loops:
            verts = [by_i[i] for i in loop if i in by_i]
            if len(verts) >= 3:
                ax.add_collection3d(Poly3DCollection([verts], facecolor="#e76f51", alpha=0.18, edgecolor="#e76f51", linewidth=0.8))
                pts += verts
    if vdf and vdf.is_file():
        for spec in wheel_geo(vdf).values():
            rings, spokes = wheel_wires(spec["pos"], spec["height"] / 2, spec["width"] / 2)
            for ring in rings:
                ax.plot(ring[:, 0], ring[:, 1], ring[:, 2], color="#1d3557", lw=1.1)
                pts += list(map(tuple, ring))
            for sp in spokes:
                ax.plot(sp[:, 0], sp[:, 1], sp[:, 2], color="#1d3557", lw=0.7, alpha=0.7)
    if not pts:
        sys.exit(f"no geometry in {sdf}")
    set_equal(ax, pts)
    ax.set_xlabel("X lateral (m)")
    ax.set_ylabel("Y vertical (m)")
    ax.set_zlabel("Z fore-aft (m)")
    ax.view_init(elev=22, azim=-110, vertical_axis="y")
    ax.set_title(vdf.stem if vdf else sdf.stem)
    fig.tight_layout()
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Wrote {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
