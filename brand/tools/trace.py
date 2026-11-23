#!/usr/bin/env python3
"""Traces the Dodobian marks from the GPT sheet into SVG.

Run:    python brand/tools/trace.py  (needs pillow and vtracer; vtracer 0.6 on Python 3.14 takes positional arguments only)
Source: brand/art/gpt-logo-sheet-hibiscus.png (the hibiscus is lime there; recoloured to red).
Output: brand/svg/*.svg and intermediate PNGs in brand/svg/work/.
"""
from pathlib import Path
import re
from PIL import Image, ImageFilter, ImageChops
import vtracer

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "art" / "gpt-logo-sheet-hibiscus.png"
OUT = ROOT / "svg"
WORK = OUT / "work"

# Brand palette: every colour in a mark is snapped to these.
PALETTE = {
    "white": (0xFF, 0xFF, 0xFF),
    "palm": (0x1F, 0x6B, 0x45),
    "lime": (0xA6, 0xD6, 0x08),
    "lagoon": (0x1F, 0xB5, 0xA8),
    "night": (0x0E, 0x26, 0x20),
    "flame": (0xE8, 0x55, 0x3A),
    "flame_deep": (0xB5, 0x3A, 0x24),
}

# Sheet cells (x0, y0, x1, y1) and the flower box inside each cell.
CELLS = {
    "emblem": {"box": (36, 181, 360, 529), "flower": (10, 30, 140, 185), "sticker": True},
    "dmark": {"box": (746, 185, 1056, 525), "flower": (30, 50, 135, 170)},
}


def nearest(rgb, names):
    return min(names, key=lambda n: sum((a - b) ** 2 for a, b in zip(rgb, PALETTE[n])))


def prepare(name, spec, scale=3):
    im = Image.open(SRC).convert("RGB").crop(spec["box"])
    w, h = im.size
    im = im.resize((w * scale, h * scale), Image.LANCZOS)
    px = im.load()
    W, H = im.size
    fx0, fy0, fx1, fy1 = [v * scale for v in spec["flower"]]

    # Mask of the lime inside the flower box, closed morphologically: the flower silhouette.
    mask = Image.new("L", im.size, 0)
    mp = mask.load()
    for y in range(fy0, fy1):
        for x in range(fx0, fx1):
            if nearest(px[x, y], ["white", "palm", "lime", "lagoon", "night"]) == "lime":
                mp[x, y] = 255
    closed = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
    cp = closed.load()

    base = ["white", "palm", "lime", "lagoon", "night"]
    for y in range(H):
        for x in range(W):
            n = nearest(px[x, y], base)
            if cp[x, y] and fx0 <= x < fx1 and fy0 <= y < fy1:
                n = "flame" if n == "lime" else ("flame_deep" if n in ("palm", "night") else n)
            px[x, y] = PALETTE[n]
    # Make the white cell background connected to the edge transparent. So that the fill does not leak
    # into the white face through the gap under the beak, seal the silhouette by closing the mask first.
    from PIL import ImageDraw
    subj = Image.new("L", im.size, 0)
    sp = subj.load()
    for y in range(H):
        for x in range(W):
            if px[x, y] != PALETTE["white"]:
                sp[x, y] = 255
    if spec.get("sticker"):
        # Even white sticker outline: blurring the mask and thresholding gives a rounded contour wider than the silhouette.
        sealed = subj.filter(ImageFilter.GaussianBlur(14)).point(lambda v: 255 if v > 25 else 0)
        sealed = sealed.filter(ImageFilter.GaussianBlur(4)).point(lambda v: 255 if v > 127 else 0)
        inside = sealed.load()
        rgba = im.convert("RGBA")
        ap = rgba.load()
        for y in range(H):
            for x in range(W):
                if not inside[x, y]:
                    ap[x, y] = (0, 0, 0, 0)
        WORK.mkdir(parents=True, exist_ok=True)
        p = WORK / f"{name}-prepared.png"
        rgba.save(p)
        return p
    sealed = subj.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.MinFilter(31))
    sealed = Image.merge("RGB", (sealed, sealed, sealed))
    ImageDraw.floodfill(sealed, (1, 1), (255, 0, 255), thresh=10)
    fp = sealed.load()
    rgba = im.convert("RGBA")
    ap = rgba.load()
    for y in range(H):
        for x in range(W):
            if fp[x, y] == (255, 0, 255) and px[x, y] == PALETTE["white"]:
                ap[x, y] = (0, 0, 0, 0)
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / f"{name}-prepared.png"
    rgba.save(p)
    return p


def trace(png, out):
    # Positional only: on Python 3.14 vtracer 0.6 crashes (SIGSEGV) on any keyword argument.
    # Order: colormode, hierarchical, mode, filter_speckle, color_precision, layer_difference,
    # corner_threshold, length_threshold, max_iterations, splice_threshold, path_precision.
    vtracer.convert_image_to_svg_py(
        str(png), str(out),
        "color", "stacked", "spline", 12, 8, 8, 60, 4.0, 10, 45, 2,
    )
    svg = out.read_text()
    # Snap path colours to the palette (vtracer shifts values slightly).
    def fix(m):
        hx = m.group(1)
        rgb = tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))
        n = nearest(rgb, list(PALETTE))
        return 'fill="#%02X%02X%02X"' % PALETTE[n]
    svg = re.sub(r'fill="#([0-9A-Fa-f]{6})"', fix, svg)
    out.write_text(svg)
    return svg.count("<path")


def crop_viewbox(png, svg_path, pad=4):
    """viewBox at the edge of the opaque drawing: a mark without margins, so it sits in a line like a letter."""
    x0, y0, x1, y1 = Image.open(png).getchannel("A").getbbox()
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    svg = svg_path.read_text()
    svg = re.sub(r'<svg version="1.1" xmlns="http://www.w3.org/2000/svg"[^>]*>',
                 f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" width="{w}" height="{h}">', svg, count=1)
    svg_path.write_text(svg)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, spec in CELLS.items():
        png = prepare(name, spec)
        n = trace(png, OUT / f"{name}.svg")
        crop_viewbox(png, OUT / f"{name}.svg")
        print(name, "paths:", n, "size:", (OUT / f"{name}.svg").stat().st_size)
