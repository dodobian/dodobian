# Dodobian

A classic desktop, grown on Debian. GNOME 2 in spirit, mouse first, floating windows,
with the calm polish of a modern desktop: rounded windows, soft shadows, a little motion.

Built on Debian (Forky now, Stable once Forky is released) with Labwc, Waybar and our own
packages on top. The mascot is the dodo, a bird that lived only on Mauritius.

> Dodobian is not affiliated with Debian. Debian is a registered trademark owned by
> Software in the Public Interest, Inc.

## Layout

| Path | What |
|---|---|
| `brand/` | logo, palette "Mauritius", wallpapers, generators |
| `labwc/` | our patches for Labwc (scenefx: rounded corners, shadows; later animations) |
| `packages/` | our Debian packages: session, theme, panel and menu configs |
| `site/` | dodobian.org |
| `docs/` | how to build and install, design decisions |

Status: early prototype. Nothing here is ready to install.

Rules for changes: see `CONTRIBUTING.md`.

## License

Copyright (C) 2026 The Dodobian authors (see `AUTHORS`).

Dodobian is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 2
of the License, or (at your option) any later version. See `LICENSE`.
SPDX-License-Identifier: `GPL-2.0-or-later`

Patches to Labwc in `labwc/` follow Labwc's own licence, GPL-2.0-only.
The Baloo 2 font in `brand/fonts/` is third-party work under the SIL Open Font License 1.1
(`brand/fonts/OFL.txt`).

The name "Dodobian" and the dodo logo identify this project. The licence covers the files,
not the name: please do not present another product as Dodobian or as endorsed by it.
