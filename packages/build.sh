#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Build one of our Debian packages in a clean debian:forky container and run lintian.
# Usage: packages/build.sh <package>        e.g. packages/build.sh dodobian-theme
# Output: build/<package>/ (.deb, .changes, .buildinfo, lintian.txt). Needs docker; installs nothing on the host.
set -eu
pkg=${1:?usage: packages/build.sh <package>}
root=$(cd "$(dirname "$0")/.." && pwd)
[ -d "$root/packages/$pkg/debian" ] || { echo "no such package: $pkg" >&2; exit 1; }
out="$root/build/$pkg"
rm -rf "$out" && mkdir -p "$out"
image=${DODOBIAN_BUILD_IMAGE:-debian:forky}

# Theme files are generated from brand/palette.json: refuse to build from stale or hand-edited ones.
python3 "$root/brand/tools/theme.py" --check

docker run --rm -v "$root:/src:ro" -v "$out:/out" -e PKG="$pkg" -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  "$image" sh -euc '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends build-essential debhelper lintian >/dev/null
    mkdir -p /work && cp -a "/src/packages/$PKG" "/work/$PKG"
    cd "/work/$PKG"
    if [ -f brand.list ]; then
      mkdir -p brand
      grep -v "^#" brand.list | while read -r f; do [ -n "$f" ] && cp "/src/brand/$f" brand/; done
    fi
    dpkg-buildpackage -b -us -uc
    cp /work/*.deb /work/*.changes /work/*.buildinfo /out/
    chmod -R a+rX /out && setpriv --reuid=nobody --regid=nogroup --clear-groups lintian --info --display-info --pedantic /out/*.changes > /out/lintian.txt 2>&1 || true
    chown -R "$HOST_UID:$HOST_GID" /out
  '
ls -l "$out"
echo "--- lintian"; cat "$out/lintian.txt"
