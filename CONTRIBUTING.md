# Contributing to Dodobian

Dodobian is a Debian distribution built around Dodo, a classic desktop: Labwc and Waybar with our
own packages on top, a patch stack for Labwc (scenefx: rounded corners and soft shadows, later
animations), and the brand. Everything lives in this one repository.

## Layout

| Path | What |
|---|---|
| `brand/` | logo, palette, wallpapers and the generators that produce them |
| `labwc/` | patches on top of upstream Labwc tags, one file per patch with a "why" header |
| `packages/` | sources of our Debian packages |
| `site/` | the website |
| `docs/` | public documentation |
| `.github/workflows/` | CI |

## Rules

- **This repository is public.** Do not commit research notes, session logs, machine details
  (disk serials, hostnames, IP addresses, home paths), server details, e-mail addresses or secrets.
  Working notes live outside the repository.
- **Licence.** New files are GPL-2.0-or-later, `Copyright (C) <year> The Dodobian authors`.
  Patches in `labwc/` modify Labwc and follow its licence, GPL-2.0-only.
- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/):
  `<type>[optional scope]: <description>`, in English, imperative mood, lowercase, no trailing period.
  Commit with an address you are happy to publish; a GitHub noreply address works.
- **Language.** Code, comments, file names and commit messages are in English.
- **Names.** Dodo is the desktop, Dodobian the distribution. Whatever could run on another
  distribution carries the desktop's name: packages `dodo-*`, commands, `/usr/share/dodo`,
  `/etc/dodo`, `DODO_*` variables. Only what belongs to Debian packaging and our archive is
  `dodobian-*`: the metapackage, the archive keyring, the installer, and the `+dodobian<N>`
  rebuilds of Debian packages.
- **Generated files** are regenerated from their tools in `brand/tools/`, never edited by hand.
- **Configs ship as Debian packages**, so `apt upgrade` updates them. No `git clone` installers.
