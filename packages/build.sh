#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Build one of our Debian packages in a clean debian:forky container and run lintian.
# Usage: packages/build.sh <package>        e.g. packages/build.sh dodobian-theme
# Output: build/<package>/ (.deb, .changes, .buildinfo, lintian.txt). Needs docker; installs nothing on the host.
#
# Two kinds of package:
#   packages/<package>/debian/  our own package, built from this directory
#   packages/<package>/series   a Debian package rebuilt with our patches: the source comes from
#                               the archive, the patches listed in series are added to its quilt
#                               stack, and the version gets "+dodobian<N>" (N from the file revision)
#                               so that it sorts above Debian's
set -eu
pkg=${1:?usage: packages/build.sh <package>}
root=$(cd "$(dirname "$0")/.." && pwd)
dir="$root/packages/$pkg"
if [ -d "$dir/debian" ]; then kind=own
elif [ -f "$dir/series" ]; then kind=patched
else echo "no such package: $pkg" >&2; exit 1
fi
out="$root/build/$pkg"
rm -rf "$out" && mkdir -p "$out"
image=${DODOBIAN_BUILD_IMAGE:-debian:forky}

# Theme files are generated from brand/palette.json: refuse to build from stale or hand-edited ones.
python3 "$root/brand/tools/theme.py" --check

docker run --rm -v "$root:/src:ro" -v "$out:/out" -e PKG="$pkg" -e KIND="$kind" \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" "$image" sh -euc '
    export DEBIAN_FRONTEND=noninteractive
    if [ "$KIND" = patched ]; then
      sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/debian.sources
    fi
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends build-essential debhelper lintian >/dev/null
    mkdir -p /work && cd /work
    if [ "$KIND" = own ]; then
      cp -a "/src/packages/$PKG" "/work/$PKG"
      cd "/work/$PKG"
      if [ -f brand.list ]; then
        mkdir -p brand
        grep -v "^#" brand.list | while read -r f; do [ -n "$f" ] && cp "/src/brand/$f" brand/; done
      fi
    else
      apt-get install -y -qq --no-install-recommends dpkg-dev >/dev/null
      apt-get source -qq "$PKG" >/dev/null
      apt-get build-dep -y -qq "$PKG" >/dev/null
      cd "$(find /work -mindepth 1 -maxdepth 1 -type d | head -n1)"
      mkdir -p debian/patches && touch debian/patches/series
      grep -v -e "^#" -e "^$" "/src/packages/$PKG/series" | while read -r p; do
        cp "/src/packages/$PKG/patches/$p" debian/patches/
        echo "$p" >> debian/patches/series
      done
      rev=$(cat "/src/packages/$PKG/revision" 2>/dev/null || echo 1)
      src=$(dpkg-parsechangelog -S Source); ver=$(dpkg-parsechangelog -S Version)
      { printf "%s (%s+dodobian%s) unstable; urgency=medium\n\n" "$src" "$ver" "$rev"
        grep -v -e "^#" -e "^$" "/src/packages/$PKG/series" | sed "s/^/  * Dodobian patch: /"
        printf "\n -- dmitrax <4255553+dmitrax@users.noreply.github.com>  %s\n\n" "$(date -R)"
        cat debian/changelog; } > debian/changelog.new
      mv debian/changelog.new debian/changelog
    fi
    dpkg-buildpackage -b -us -uc
    cp /work/*.deb /work/*.changes /work/*.buildinfo /out/
    chmod -R a+rX /out && setpriv --reuid=nobody --regid=nogroup --clear-groups lintian --info --display-info --pedantic /out/*.changes > /out/lintian.txt 2>&1 || true
    chown -R "$HOST_UID:$HOST_GID" /out
  '
ls -l "$out"
echo "--- lintian"; cat "$out/lintian.txt"
