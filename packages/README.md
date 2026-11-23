# packages

Sources of our Debian packages. Configs ship as `.deb`, so `apt upgrade` updates them.

| Package | Arch | What |
|---|---|---|
| `dodobian-theme` | all | labwc theme "Dodobian", Waybar style, wallpaper, marks for the panel |

Planned: `dodobian-session` (session, labwc and Waybar defaults, units), `dodobian-desktop` (metapackage).

## Build

```sh
packages/build.sh dodobian-theme
```

Builds in a clean `debian:forky` container (Docker), runs `lintian`, and leaves the result in
`build/<package>/`. Nothing is installed on the host. Files a package takes from the top-level
`brand/` directory are listed in its `brand.list`.

Install paths follow one rule: distribution defaults in `/usr/share`, never `/etc/skel`, and
maintainer scripts never touch `$HOME`. A user's own `~/.config` always wins.
