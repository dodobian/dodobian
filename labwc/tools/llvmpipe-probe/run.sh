#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Run probe.c case by case on Mesa llvmpipe in a clean debian:forky container and report which
# cases crash. Used by .github/workflows/llvmpipe-probe.yml; runs the same locally (docker/colima).
# Usage: labwc/tools/llvmpipe-probe/run.sh [NAME=VALUE ...] [case ...]
#   NAME=VALUE   environment for llvmpipe, e.g. LP_NATIVE_VECTOR_WIDTH=128 (any number)
#   case         a case from "probe --list", e.g. scene:cursor gl:tex-stencil; default: all
# Output: build/llvmpipe-probe/ (summary.txt; for each case its log and frame; for a crashed case
# backtraces with Mesa debug symbols and the LLVM IR llvmpipe generated).
# Exit status: 0 when every case ran (crashed or not), 1 when the probe did not build or a case
# could not be set up. A crash is a finding, not a failure of this script.
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd)
out="$root/build/llvmpipe-probe"
rm -rf "$out" && mkdir -p "$out"
# The same pinned image as packages/build.sh.
# shellcheck disable=SC2016 # a literal ${ in the sed pattern
image=$(sed -n 's/^image=\${DODOBIAN_BUILD_IMAGE:-\(.*\)}$/\1/p' "$root/packages/build.sh")
image=${DODOBIAN_BUILD_IMAGE:-$image}
[ -n "$image" ] || { echo "no image in packages/build.sh" >&2; exit 1; }

envs=
cases=
for a in "$@"; do
	case "$a" in
	*=*)
		echo "${a%%=*}" | grep -qE '^[A-Z][A-Z0-9_]*$' || { echo "bad variable: $a" >&2; exit 1; }
		envs="$envs -e $a" ;;
	scene:*|gl:*)
		echo "$a" | grep -qE '^[a-z]+:[a-z0-9-]+$' || { echo "bad case: $a" >&2; exit 1; }
		cases="$cases $a" ;;
	*) echo "neither NAME=VALUE nor a case: $a" >&2; exit 1 ;;
	esac
done

# /dev/udmabuf, when the docker host has it, gives wlroots buffers to render into; without it
# only the gl:* cases can run.
dev=
if docker run --rm --device /dev/udmabuf "$image" true >/dev/null 2>&1; then dev="--device /dev/udmabuf"; fi
# shellcheck disable=SC2086 # $dev and $envs are option lists, $cases a word list
docker run --rm $dev $envs -v "$root:/src:ro" -v "$out:/out" \
	-e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" "$image" \
	sh -eu /src/labwc/tools/llvmpipe-probe/inside.sh $cases
