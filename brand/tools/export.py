#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
"""Raster exports of the Dodobian marks.

Run:    python3 brand/tools/export.py   (stdlib + the rsvg-convert binary from librsvg)
Output: brand/png/avatar-1024.png        organisation avatar: D mark, transparent, square (reads at 20-40 px)
        brand/png/emblem-<N>.png         emblem, 48-256 px, transparent
        brand/png/dmark-<N>.png          D mark, 32-64 px, transparent
        brand/png/dmark-small-<N>.png    simplified D, 16-24 px, transparent
"""
import re
import subprocess
from pathlib import Path

BRAND = Path(__file__).resolve().parents[1]
SVG, PNG = BRAND / "svg", BRAND / "png"

AVATAR, AVATAR_FILL = 1024, 0.80  # the mark takes 80% of the side: room for GitHub's rounded mask
AVATAR_BG = None  # transparent: the D itself is the avatar on light and dark pages; a colour like "#F3E7C9" adds a tile
AVATAR_MARK = "dmark"  # the emblem blurs at the 20-40 px GitHub mostly shows; the D mark is drawn for it

SIZES = {
    "emblem": (48, 64, 128, 256),
    "dmark": (32, 48, 64),
    "dmark-small": (16, 24),
}


def render(svg_text: str, out: Path, width: int, height: int) -> None:
    subprocess.run(
        ["rsvg-convert", "-w", str(width), "-h", str(height), "-o", str(out)],
        input=svg_text.encode(), check=True,
    )


def nested(svg_text: str, x: float, y: float, w: float, h: float) -> str:
    """Turn a standalone SVG into a nested <svg> placed at x, y with size w x h."""
    body = re.sub(r"<\?xml[^>]*\?>|<!--.*?-->", "", svg_text, flags=re.S).strip()

    def root(m):
        attrs = re.sub(r'\s(width|height|x|y)="[^"]*"', "", m.group(1))
        return f'<svg{attrs} x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet">'

    return re.sub(r"<svg(\s[^>]*)>", root, body, count=1)


def avatar() -> None:
    side = AVATAR
    inner = side * AVATAR_FILL
    off = (side - inner) / 2
    mark = (SVG / f"{AVATAR_MARK}.svg").read_text()
    doc = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" width="{side}" height="{side}">'
        + (f'<rect width="{side}" height="{side}" fill="{AVATAR_BG}"/>' if AVATAR_BG else "")
        + f"{nested(mark, off, off, inner, inner)}</svg>"
    )
    render(doc, PNG / f"avatar-{side}.png", side, side)


def icons() -> None:
    for name, sizes in SIZES.items():
        src = (SVG / f"{name}.svg").read_text()
        vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', src).group(1).split()]
        aspect = vb[2] / vb[3]
        for n in sizes:
            # fit the longer side into n, keep the aspect ratio
            w, h = (n, round(n / aspect)) if aspect >= 1 else (round(n * aspect), n)
            render(src, PNG / f"{name}-{n}.png", w, h)


if __name__ == "__main__":
    PNG.mkdir(exist_ok=True)
    avatar()
    icons()
    for p in sorted(PNG.glob("*.png")):
        print(p.relative_to(BRAND.parent))
