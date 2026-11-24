# packages

Sources of our Debian packages. Configs ship as `.deb`, so `apt upgrade` updates them.

| Package | Arch | What |
|---|---|---|
| `dodobian-theme` | all | labwc theme "Dodobian", Waybar style, wallpaper, marks for the panel |
| `libxfce4windowing` | any | Debian's package rebuilt with our patches: the session can name the primary monitor (`XFW_PRIMARY_MONITOR`) |

Planned: `dodobian-session` (session, labwc and Waybar defaults, units), `dodobian-desktop` (metapackage).

## Build

```sh
packages/build.sh dodobian-theme
```

A directory with `debian/` is our own package. A directory with `series` is a Debian package rebuilt
with our patches: `build.sh` fetches the source from the archive, adds the patches listed in `series`
(from `patches/`, each with a header saying why) to its quilt stack, and appends `+dodobian<N>` to the
version, N from `revision`, so it sorts above Debian's. A patch that no longer applies fails the build.

Builds in a clean `debian:forky` container (Docker), runs `lintian`, and leaves the result in
`build/<package>/`. Nothing is installed on the host. Files a package takes from the top-level
`brand/` directory are listed in its `brand.list`.

The labwc theme and the Waybar style are generated from `brand/palette.json` by
`brand/tools/theme.py`: edit their `.in` templates, not the files themselves. `build.sh` refuses
to build when they are stale.

Install paths follow one rule: distribution defaults in `/usr/share`, never `/etc/skel`, and
maintainer scripts never touch `$HOME`. A user's own `~/.config` always wins.
