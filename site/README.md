# site

Source of [dodobian.org](https://dodobian.org): one static page in English (`/`) and Russian (`/ru/`).
The page is a Dodo Desktop: a dark glass panel, light windows in the Dodo Labwc theme and the lagoon
wallpaper behind them. The windows can be dragged, minimized and maximized; nothing animates.

| Path | What |
|---|---|
| `build.py` | builds the site into `public/`: pages, images from `brand/`, `robots.txt`, `sitemap.xml` |
| `text/en.json` | English texts |
| `ru/text.json` | Russian texts: translations live under `site/<lang>/` |
| `assets/fonts/` | Nunito (latin and cyrillic subsets), SIL OFL 1.1 (`assets/fonts/OFL.txt`) |

Build with `python3 site/build.py` (needs ImageMagick 7 and `rsvg-convert`). `public/` is generated and
not committed. To publish, upload the whole of `public/` to the web root with
`rsync -rt --delete --chmod=D755,F644`; `--delete` makes the server match the build exactly.

No external fonts, scripts or counters. Russian browsers are sent to `/ru/` once, unless the visitor
has picked a language with the EN/RU switch; crawlers are left alone and find both pages by `hreflang`.
