# brand

| Path | What |
|---|---|
| `svg/emblem.svg` | main logo, 48 px and up (login screen, About, splash, site) |
| `svg/dmark.svg` | D mark, 32–64 px, first letter of the wordmark "D·odobian" |
| `svg/dmark-small.svg` | simplified D, 16–24 px (panel, tray), drawn by hand |
| `svg/dmark-swirl.svg` | spiral "d", secondary mark |
| `svg/wordmark-light.svg`, `svg/wordmark-dark.svg` | the wordmark "D·odobian": D mark + Baloo 2 ExtraBold as outlines; palm text for light backgrounds, light palm `#4CA874` for dark |
| `svg/swirl.svg`, `svg/spinner.svg` | the brand swirl and the loading spinner (same curve) |
| `art/` | wallpaper and the GPT source sheets the marks were traced from |
| `tools/trace.py` | traces `emblem.svg` and `dmark.svg` from the GPT sheet, recolors the hibiscus, snaps to the palette |
| `tools/swirl.py` | builds the swirl marks from one formula (stdlib only) |
| `tools/wordmark.py` | builds the wordmark from the font's own metrics: D from baseline to the "d" ascender, outlined in the text colour, font spacing and kerning (needs `fonttools`, `uharfbuzz`) |
| `fonts/` | Baloo 2 ExtraBold, Latin subset, SIL OFL 1.1 (`fonts/OFL.txt`); only the wordmark tool uses it |
| `tools/export.py` | renders `png/`: the organisation avatar and icon sizes of the marks (needs `rsvg-convert`) |
| `png/` | generated rasters: `avatar-1024.png` (D mark, transparent), emblem 48–256, D mark 32–64, small D 16–24 |
| `pages/` | design drafts: palette and logo pages |

Palette "Mauritius": jungle `#0E2620`, palm `#1F6B45`, sage `#9DB8A0`, lime `#A6D608`,
lagoon `#1FB5A8`, deep lagoon `#0E6E73`, flamboyant `#E8553A`, sand `#F3E7C9`, mango `#FFB347`.

Art from GPT image generation; vector marks traced and drawn from it. Licence: GPL-2.0-or-later,
like the rest of the repository. The name and the logo are the project's identity: see the
License section of the top-level README.
