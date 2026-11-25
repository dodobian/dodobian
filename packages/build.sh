#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Build one of our Debian packages in a clean debian:forky container, check it, and test that it
# installs and purges cleanly in a second clean container.
# Usage: packages/build.sh <package>        e.g. packages/build.sh dodobian-theme
# Output: build/<package>/ (.deb, .dsc and source tarballs, .changes, .buildinfo, lintian.txt).
# Needs docker; installs nothing on the host. Any failed check fails the build.
#
# Two kinds of package:
#   packages/<package>/debian/  our own package, built from this directory
#   packages/<package>/series   a Debian package rebuilt with our patches: the source comes from
#                               the archive, the patches listed in series are added to its quilt
#                               stack, and the version gets "+dodobian<N>" (N from the file revision).
#                               That sorts above the same Debian revision only: a newer Debian
#                               revision (-2, an NMU, a stable update) sorts above ours and replaces
#                               it on upgrade, so every new Debian revision has to be rebuilt.
#                               Extra Build-Depends our patches need go in build-depends.
#
# Checks:
#   - theme files are not stale against brand/palette.json (brand/tools/theme.py --check)
#   - own packages: every *.xml passes xmllint, every *.json passes jq (strict JSON: no comments)
#   - lintian finds no errors (warnings and info are reported, not fatal)
#   - the binary packages install, remove and purge in a clean container, leaving no files behind
#   - packages/<package>/test.sh, if there is one, passes in that container after install
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
# Pinned to a multi-arch index digest (amd64 and arm64), so every build starts from the same image.
# Refresh: docker buildx imagetools inspect debian:forky
image=${DODOBIAN_BUILD_IMAGE:-debian:forky@sha256:f3671d5a279b1ae356c7318ce6cdb84c600c2063d708ee97d3cce607bebfb85a}

# Theme files are generated from brand/palette.json: refuse to build from stale or hand-edited ones.
python3 "$root/brand/tools/theme.py" --check

echo "--- build"
docker run --rm -v "$root:/src:ro" -v "$out:/out" -e PKG="$pkg" -e KIND="$kind" \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" "$image" sh -euc '
    export DEBIAN_FRONTEND=noninteractive
    if [ "$KIND" = patched ]; then
      sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/debian.sources
    fi
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends build-essential debhelper lintian \
      libxml2-utils jq >/dev/null
    mkdir -p /work && cd /work
    if [ "$KIND" = own ]; then
      cp -a "/src/packages/$PKG" "/work/$PKG"
      cd "/work/$PKG"
      if [ -f brand.list ]; then
        mkdir -p brand
        grep -v "^#" brand.list | while read -r f; do [ -n "$f" ] && cp "/src/brand/$f" brand/; done
      fi
      # A broken config starts silently at login, so it must not build.
      bad=0
      for f in $(find . -name "*.xml" -not -path "./debian/*" | sort); do
        xmllint --noout "$f" || { echo "invalid XML: $f" >&2; bad=1; }
      done
      for f in $(find . -name "*.json" -not -path "./debian/*" | sort); do
        jq empty "$f" || { echo "invalid JSON: $f" >&2; bad=1; }
      done
      [ "$bad" = 0 ]
    else
      apt-get install -y -qq --no-install-recommends dpkg-dev >/dev/null
      apt-get source -qq "$PKG" >/dev/null
      cd "$(find /work -mindepth 1 -maxdepth 1 -type d | head -n1)"
      # Our patches may need more than the Debian package builds with.
      if [ -f "/src/packages/$PKG/build-depends" ]; then
        extra=$(grep -v -e "^#" -e "^$" "/src/packages/$PKG/build-depends" | paste -sd, -)
        sed -i "0,/^Build-Depends:/s//Build-Depends: $extra,/" debian/control
      fi
      # From the local source, so the added Build-Depends count too.
      apt-get build-dep -y -qq ./ >/dev/null
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
    # Source and binaries: a rebuilt GPL package has to ship the source of what we changed.
    # -sa lists the upstream tarball in .changes even though the revision is not the first one.
    dpkg-buildpackage -us -uc -sa
    # Only what this build produced: the files listed in .changes (not the archive source it started from).
    ch=$(ls /work/*.changes)
    cp "$ch" /out/
    sed -n "/^Files:/,/^[^ ]/{/^ /p}" "$ch" | awk "{print \$5}" | while read -r f; do cp "/work/$f" /out/; done
    chmod -R a+rX /out
    rc=0
    setpriv --reuid=nobody --regid=nogroup --clear-groups \
      lintian --info --display-info --pedantic --fail-on error /out/*.changes > /out/lintian.txt 2>&1 \
      || rc=$?
    chown -R "$HOST_UID:$HOST_GID" /out
    exit "$rc"
  ' || { rc=$?; [ -f "$out/lintian.txt" ] && { echo "--- lintian"; cat "$out/lintian.txt"; }; exit "$rc"; }
ls -l "$out"
echo "--- lintian"; cat "$out/lintian.txt"

# Install, remove and purge in a clean container. Debug symbols are left out.
# A package may bring its own test, packages/<package>/test.sh, run after install and before purge.
# /dev/udmabuf, when the docker host has it, lets a test render with software GLES2 (llvmpipe).
echo "--- install test"
dev=
if docker run --rm --device /dev/udmabuf "$image" true >/dev/null 2>&1; then dev="--device /dev/udmabuf"; fi
# shellcheck disable=SC2086 # $dev is empty or one option and its argument
docker run --rm $dev -v "$out:/out:ro" -v "$dir:/pkg:ro" "$image" sh -euc '
  export DEBIAN_FRONTEND=noninteractive
  debs=$(ls /out/*.deb | grep -v -- "-dbgsym_")
  names=$(for d in $debs; do dpkg-deb -f "$d" Package; done)
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends $debs >/dev/null
  if [ -f /pkg/test.sh ]; then echo "--- package test"; sh -eu /pkg/test.sh; fi
  for n in $names; do dpkg-query -L "$n"; done | sort -u > /tmp/files
  apt-get remove -y -qq $names >/dev/null
  # dpkg, not apt: a package without conffiles is forgotten on remove and apt can no longer find it.
  dpkg --purge $names >/dev/null
  left=$(for n in $names; do dpkg-query -W -f="\${Package} \${Status}\n" "$n" 2>/dev/null; done | grep -v "not-installed" || true)
  [ -z "$left" ] || { echo "still known to dpkg after purge:"; echo "$left"; exit 1; }
  stray=0
  while read -r f; do
    if [ -e "$f" ] && [ ! -d "$f" ]; then echo "left behind: $f"; stray=1; fi
  done < /tmp/files
  [ "$stray" = 0 ]
  echo "installed, removed and purged:" $names
'
