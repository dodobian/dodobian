#!/usr/bin/env python3
"""Фирменная спираль Dodobian: одна кривая для «d», хвоста и спиннера.

Запуск: python3 brand/tools/swirl.py  (только стандартная библиотека)
Результат: brand/svg/swirl.svg, brand/svg/dmark-swirl.svg, brand/svg/spinner.svg
Образец формы: спирали из brand/art/gpt-swirl-sheet.png
"""
from math import cos, sin, pi
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "svg"

LIME, CREAM, FLAME, NIGHT = "#A6D608", "#F3E7C9", "#E8553A", "#0E2620"


def spiral_band(cx, cy, r_out, turns=2.15, w_out=0.30, w_in=0.06, start=-0.5 * pi, ccw=True, n=260):
    """Сужающаяся лента по архимедовой спирали от внешнего радиуса к центру.

    r_out  внешний радиус средней линии
    w_out  ширина ленты снаружи, доля от r_out; w_in внутри
    start  угол начала (снаружи), ccw: закручивается против часовой
    """
    th_max = turns * 2 * pi
    k = r_out / th_max  # r = k * t, t от th_max до ~0.35 оборота
    t_min = 0.38 * 2 * pi
    pts_o, pts_i = [], []
    sgn = 1 if ccw else -1
    for i in range(n + 1):
        t = th_max - (th_max - t_min) * i / n
        r = k * t
        a = start + sgn * (th_max - t)
        f = max(0.0, (t - t_min) / (th_max - t_min))
        w = r_out * (w_in + (w_out - w_in) * f ** 0.9)
        ux, uy = cos(a), sin(a)
        px, py = cx + r * ux, cy + r * uy
        pts_o.append((px + ux * w / 2, py + uy * w / 2))
        pts_i.append((px - ux * w / 2, py - uy * w / 2))
    # Скруглённый кончик в центре
    ex, ey = pts_o[-1]
    ix, iy = pts_i[-1]
    tip_r = ((ex - ix) ** 2 + (ey - iy) ** 2) ** 0.5 / 2
    d = "M%.2f,%.2f " % pts_o[0]
    d += " ".join("L%.2f,%.2f" % p for p in pts_o[1:])
    d += " A%.2f,%.2f 0 0 1 %.2f,%.2f " % (tip_r, tip_r, ix, iy)
    d += " ".join("L%.2f,%.2f" % p for p in reversed(pts_i))
    # Скруглённый внешний торец
    ox, oy = pts_o[0]
    sx, sy = pts_i[0]
    end_r = ((ox - sx) ** 2 + (oy - sy) ** 2) ** 0.5 / 2
    d += " A%.2f,%.2f 0 0 1 %.2f,%.2f Z" % (end_r, end_r, ox, oy)
    return d


def swirl_svg(size=64, body=LIME, band=CREAM):
    c = size / 2
    R = size * 0.47
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
            f'<circle cx="{c}" cy="{c}" r="{R:.2f}" fill="{body}"/>'
            f'<path d="{spiral_band(c, c, R * 0.78, w_out=0.36)}" fill="{band}"/></svg>')


def dmark_svg():
    # Красная основа: чаша + ножка. Кремовая линия идёт по ножке вниз и без шва
    # переходит в спираль чаши: точка стыка = внешний конец спирали (угол 0, справа).
    bowl_cx, bowl_cy, bowl_r = 26, 40, 21
    r_out, w = 14.5, 6.0
    join_x = bowl_cx + r_out
    base = (f'<circle cx="{bowl_cx}" cy="{bowl_cy}" r="{bowl_r}" fill="{FLAME}"/>'
            f'<rect x="{join_x - 8.5:.2f}" y="3" width="17" height="58" rx="8.5" fill="{FLAME}"/>')
    stem = f'<rect x="{join_x - w / 2:.2f}" y="10" width="{w}" height="{bowl_cy - 10 + 1.5}" rx="{w / 2}" fill="{CREAM}"/>'
    swirl = f'<path d="{spiral_band(bowl_cx, bowl_cy, r_out, turns=2.0, w_out=w / r_out, start=0.0)}" fill="{CREAM}"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">{base}{stem}{swirl}</svg>'


def spinner_svg():
    inner = swirl_svg().split(">", 1)[1].rsplit("</svg>", 1)[0]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
            f'<g>{inner}<animateTransform attributeName="transform" type="rotate" from="0 32 32" to="-360 32 32" dur="1.4s" repeatCount="indefinite"/></g></svg>')


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / "swirl.svg").write_text(swirl_svg())
    (OUT / "dmark-swirl.svg").write_text(dmark_svg())
    (OUT / "spinner.svg").write_text(spinner_svg())
    for f in ("swirl.svg", "dmark-swirl.svg", "spinner.svg"):
        print(f, (OUT / f).stat().st_size)
