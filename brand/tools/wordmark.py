#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
"""The Dodobian wordmark: the D mark as the first letter, then "odobian" in Baloo 2 ExtraBold, as outlines.

Run:    python3 brand/tools/wordmark.py   (needs fonttools and uharfbuzz: pip install fonttools uharfbuzz)
Font:   brand/fonts/Baloo2-ExtraBold.ttf (SIL OFL 1.1, see brand/fonts/OFL.txt)
Output: brand/svg/wordmark-light.svg   palm text, for light backgrounds
        brand/svg/wordmark-dark.svg    light palm text, for dark backgrounds

Alignment, all in the font's own units:
- the baseline is y = 0; the D mark, its outline included, spans exactly from the baseline to the top
  of the "d" ascender, so the D stands as tall as "d" and "b";
- the D mark is outlined in the text colour. On light backgrounds the outline merges with the green D;
  on dark ones it lifts the D off the background. One rule for both themes;
- the gap after the D and the kerning are the font's: "Dodobian" is shaped with HarfBuzz and the mark
  takes the place of the font's own "D", keeping the font's spacing between "D" and "o".
"""
import re
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

BRAND = Path(__file__).resolve().parents[1]
FONT = BRAND / "fonts" / "Baloo2-ExtraBold.ttf"
MARK = BRAND / "svg" / "dmark.svg"

WORD = "Dodobian"
OUTLINE = 0.045  # outline width around the D, as a fraction of the ascender height
VARIANTS = {"light": "#1F6B45", "dark": "#4CA874"}  # palm, and palm lightened for dark backgrounds


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def shape(font_bytes: bytes, text: str):
    face = hb.Face(font_bytes)
    hbfont = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})
    pen_x, out = 0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((info.codepoint, pen_x + pos.x_offset, pos.y_offset))
        pen_x += pos.x_advance
    return out


def bounds(glyphset, name):
    pen = BoundsPen(glyphset)
    glyphset[name].draw(pen)
    return pen.bounds  # (xMin, yMin, xMax, yMax) or None for blank glyphs


def main() -> None:
    font_bytes = FONT.read_bytes()
    font = TTFont(FONT)
    glyphset = font.getGlyphSet()
    order = font.getGlyphOrder()
    cmap = font.getBestCmap()

    asc = bounds(glyphset, cmap[ord("d")])[3]  # top of the "d" ascender
    r = OUTLINE * asc

    shaped = shape(font_bytes, WORD)
    d_gid, d_x, _ = shaped[0]
    d_box = bounds(glyphset, order[d_gid])
    first_x = shaped[1][1]  # pen position of "o" after the font's own "D"
    gap = first_x - (d_x + d_box[2])  # the font's own room between the D's ink and "o"

    # The mark: its viewBox is trimmed to the ink. Outline included, it fills [0, asc] in height.
    mark_svg = MARK.read_text()
    vx, vy, vw, vh = (float(v) for v in re.search(r'viewBox="([^"]+)"', mark_svg).group(1).split())
    scale = (asc - 2 * r) / vh  # font units per mark unit
    rm = r / scale  # outline width in mark units
    mark_w = vw * scale + 2 * r
    body = re.sub(r"<\?xml[^>]*\?>|<!--.*?-->|</?svg[^>]*>", "", mark_svg, flags=re.S).strip()
    silhouette = re.search(r"<path[^>]*/>", body).group(0)  # the first layer is the solid green D

    # Glyphs of "odobian", shifted so they follow the mark at the font's distance.
    shift = mark_w + gap - first_x
    xmin, xmax, ymin, ymax = 0.0, mark_w, 0.0, asc
    glyphs = []
    for gid, x, y in shaped[1:]:
        name = order[gid]
        box = bounds(glyphset, name)
        if box is None:
            continue
        gx = x + shift
        xmin, xmax = min(xmin, gx + box[0]), max(xmax, gx + box[2])
        ymin, ymax = min(ymin, y + box[1]), max(ymax, y + box[3])
        glyphs.append((name, gx, y))

    width, height = xmax - xmin, ymax - ymin

    def glyph_paths():
        out = []
        for name, gx, gy in glyphs:
            pen = SVGPathPen(glyphset)
            # font units, y up  ->  SVG, y down, origin at the top-left of the ink box
            glyphset[name].draw(TransformPen(pen, (1, 0, 0, -1, gx - xmin, ymax - gy)))
            out.append(pen.getCommands())
        return " ".join(out)

    letters = glyph_paths()
    mark_y = ymax - asc  # top of the outlined mark in SVG coordinates
    for variant, colour in VARIANTS.items():
        outline = re.sub(r'fill="[^"]*"', f'fill="{colour}"', silhouette, count=1).replace(
            "/>",
            f' stroke="{colour}" stroke-width="{fmt(2 * rm)}" stroke-linejoin="round"/>',
        )
        doc = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(width)} {fmt(height)}" '
            f'width="{fmt(width / 10)}" height="{fmt(height / 10)}">\n'
            f"<title>Dodobian</title>\n"
            f'<svg x="{fmt(-xmin)}" y="{fmt(mark_y)}" width="{fmt(mark_w)}" height="{fmt(asc)}" '
            f'viewBox="{fmt(vx - rm)} {fmt(vy - rm)} {fmt(vw + 2 * rm)} {fmt(vh + 2 * rm)}">\n'
            f"{outline}\n{body}\n</svg>\n"
            f'<path fill="{colour}" d="{letters}"/>\n'
            f"</svg>\n"
        )
        out = BRAND / "svg" / f"wordmark-{variant}.svg"
        out.write_text(doc)
        print(out.relative_to(BRAND.parent))


if __name__ == "__main__":
    main()
