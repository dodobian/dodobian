# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Pixel checks for packages/labwc/test.sh, on binary PPM files from grim -t ppm. The test draws
# blue windows (title, border and terminal background all one blue) on a white background.
#
#   check-shot.py screen <screen.ppm> <windows>
#       Finds the windows as blue areas, left to right, and checks for each one that:
#       - all four corners are rounded: the pixel 2 px inside each corner of its outline is not blue
#         (Labwc without patch 0003 leaves the bottom corners of a decorated window square, and
#         every corner of a client-side decorated one);
#       - it is not cut: the pixel 2 px inside the middle of each side is blue;
#       - it casts a soft shadow: just below it the background is darker than white, far below
#         it is white again.
#   check-shot.py capture <window.ppm> <width> <height>
#       A window capture (grim -T): the expected size, a blue centre, and rounded corners (the
#       transparent corners come out black, grim writes no alpha channel).
import sys


def read_ppm(path):
    with open(path, "rb") as f:
        data = f.read()
    fields = []
    pos = 0
    while len(fields) < 4:
        while data[pos : pos + 1].isspace():
            pos += 1
        if data[pos : pos + 1] == b"#":
            pos = data.index(b"\n", pos) + 1
            continue
        end = pos
        while not data[end : end + 1].isspace():
            end += 1
        fields.append(data[pos:end])
        pos = end
    pos += 1  # the single whitespace after maxval
    if fields[0] != b"P6" or int(fields[3]) != 255:
        raise SystemExit(f"{path}: not an 8-bit binary PPM")
    width, height = int(fields[1]), int(fields[2])
    return width, height, data[pos : pos + width * height * 3]


class Image:
    def __init__(self, path):
        self.path = path
        self.width, self.height, self.data = read_ppm(path)

    def rgb(self, x, y):
        i = (y * self.width + x) * 3
        return tuple(self.data[i : i + 3])

    def blue(self, x, y):
        r, g, b = self.rgb(x, y)
        return b - r > 60

    def luma(self, x, y):
        r, g, b = self.rgb(x, y)
        return (299 * r + 587 * g + 114 * b) // 1000


failures = []


def check(ok, what):
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        failures.append(what)


def windows(img):
    """Bounding boxes of the blue areas, left to right (columns without blue separate them)."""
    columns = [any(img.blue(x, y) for y in range(img.height)) for x in range(img.width)]
    boxes = []
    x = 0
    while x < img.width:
        if not columns[x]:
            x += 1
            continue
        x0 = x
        while x < img.width and columns[x]:
            x += 1
        x1 = x - 1
        rows = [y for y in range(img.height) if any(img.blue(c, y) for c in range(x0, x1 + 1))]
        boxes.append((x0, rows[0], x1, rows[-1]))
    return boxes


def check_corners(img, name, x0, y0, x1, y1, inset=2):
    for label, x, y in (
        ("top left", x0 + inset, y0 + inset),
        ("top right", x1 - inset, y0 + inset),
        ("bottom right", x1 - inset, y1 - inset),
        ("bottom left", x0 + inset, y1 - inset),
    ):
        check(not img.blue(x, y), f"{name}: {label} corner rounded, pixel {img.rgb(x, y)}")
    mx, my = (x0 + x1) // 2, (y0 + y1) // 2
    for label, x, y in (
        ("top", mx, y0 + inset),
        ("right", x1 - inset, my),
        ("bottom", mx, y1 - inset),
        ("left", x0 + inset, my),
    ):
        check(img.blue(x, y), f"{name}: {label} side not cut, pixel {img.rgb(x, y)}")


def screen(path, expected):
    img = Image(path)
    boxes = windows(img)
    check(len(boxes) == expected, f"{path}: {expected} windows found ({boxes})")
    for n, (x0, y0, x1, y1) in enumerate(boxes, 1):
        name = f"window {n} at {x0},{y0} size {x1 - x0 + 1}x{y1 - y0 + 1}"
        check_corners(img, name, x0, y0, x1, y1)
        mx = (x0 + x1) // 2
        near, far = y1 + 6, min(y1 + 150, img.height - 1)
        check(img.luma(mx, near) < 240, f"{name}: shadow below, luma {img.luma(mx, near)}")
        check(img.luma(mx, far) >= 250, f"{name}: white far below, luma {img.luma(mx, far)}")


def capture(path, width, height):
    img = Image(path)
    check((img.width, img.height) == (width, height),
          f"{path}: size {img.width}x{img.height}, expected {width}x{height}")
    if failures:
        return
    check(img.blue(width // 2, height // 2), f"{path}: blue centre {img.rgb(width // 2, height // 2)}")
    # The window outline inside the capture: client-side decorations may add transparent margins.
    boxes = windows(img)
    check(len(boxes) == 1, f"{path}: one window ({boxes})")
    if len(boxes) == 1:
        check_corners(img, path, *boxes[0])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "screen" and len(sys.argv) == 4:
        screen(sys.argv[2], int(sys.argv[3]))
    elif mode == "capture" and len(sys.argv) == 5:
        capture(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    else:
        raise SystemExit(__doc__ or "usage: check-shot.py screen|capture ...")
    sys.exit(1 if failures else 0)
