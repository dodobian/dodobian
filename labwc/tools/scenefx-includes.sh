#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Generate labwc/patches/0001-scenefx-scene-header.patch for a Labwc source tree.
# Usage: labwc/tools/scenefx-includes.sh <labwc source> > labwc/patches/0001-scenefx-scene-header.patch
#   <labwc source> is a git work tree with no local changes, checked out at the Labwc release
#   the patch is for. The tree is left as it was.
#
# libscenefx exports the wlroots scene-graph API (wlr_scene_*) with extra node types, so every
# Labwc file that uses the scene graph has to include SceneFX's header instead of the wlroots one.
# The change is mechanical: on a new Labwc release, regenerate the patch instead of editing it.
set -eu
src=${1:?usage: labwc/tools/scenefx-includes.sh <labwc source>}
cd "$src"
git diff --quiet || { echo "scenefx-includes: $src has local changes" >&2; exit 1; }

old='#include <wlr/types/wlr_scene.h>'
new='#include <scenefx/types/wlr_scene.h>'
files=$(git grep -l -F "$old" -- '*.c' '*.h' || true)
[ -n "$files" ] || { echo "scenefx-includes: no file includes the wlroots scene header" >&2; exit 1; }

version=$(sed -n "s/^ *version: '\([^']*\)'.*/\1/p" meson.build | head -n1)
cat <<EOF
Description: Include the SceneFX scene-graph header instead of the wlroots one
 Dodobian renders Labwc's scene graph through SceneFX, for rounded corners and
 soft shadows. libscenefx exports the same wlr_scene_* API as wlroots, with
 extra node types, so every file that uses the scene graph must see the
 SceneFX header. Mechanical: generated for Labwc $version by
 labwc/tools/scenefx-includes.sh in the Dodobian repository.
 .
 Upstream Labwc declined SceneFX (labwc/labwc pull request 3751), so this is
 carried downstream. The approach follows grigio/labwc (labwc-blur).
Author: The Dodobian authors
Origin: vendor, https://github.com/dodobian/dodobian/tree/main/labwc
Forwarded: not-needed
---
EOF

# Portable in-place edit (GNU and BSD sed differ on -i).
for f in $files; do
	sed "s|$old|$new|" "$f" > "$f.scenefx" && mv "$f.scenefx" "$f"
done
git diff
git checkout -q -- .
