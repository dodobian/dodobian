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
version, N from `revision`. That sorts above the same Debian revision only: a newer Debian revision
(`-2`, an NMU, a stable update) sorts above ours and replaces it on upgrade, so every new Debian
revision has to be rebuilt. A patch that no longer applies fails the build.

Builds in a clean `debian:forky` container (Docker, pinned by digest), source and binaries, and leaves
the result in `build/<package>/`. Nothing is installed on the host. Files a package takes from the
top-level `brand/` directory are listed in its `brand.list`.

Any failed check fails the build:

- every `*.xml` in our own packages passes `xmllint`, every `*.json` passes `jq` (strict JSON, so no
  comments: a broken config would otherwise start silently at login);
- `lintian` finds no errors (warnings and info are printed, not fatal);
- the binary packages install, remove and purge in a second clean container, leaving no files behind.

The labwc theme and the Waybar style are generated from `brand/palette.json` by
`brand/tools/theme.py`: edit their `.in` templates, not the files themselves. `build.sh` refuses
to build when they are stale.

Install paths follow one rule: distribution defaults in `/usr/share`, never `/etc/skel`, and
maintainer scripts never touch `$HOME`. A user's own `~/.config` always wins.

## CI

`.github/workflows/packages.yml` runs `build.sh` for every package on each push to `main` and each pull
request: architecture `all` packages on amd64, the others on amd64 and arm64. A weekly run rebuilds
the patched Debian packages against the current archive source, so a new Debian revision or a patch
that no longer applies turns the run red. The results (`.deb`, `.dsc`, `lintian.txt`) are kept as
run artifacts for 14 days. CI signs and publishes nothing. A new package is one more line in the
workflow's matrix. GitHub pauses scheduled runs after 60 days without activity in the repository;
re-enable the workflow if that happens.
