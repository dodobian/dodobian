# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Test of the SceneFX patches (labwc/patches/0001, 0002). Run by packages/build.sh inside the
# install-test container, after our labwc is installed.
#   1. labwc links libscenefx-0.5, ahead of wlroots (they export the same wlr_scene_* symbols).
#   2. With /dev/udmabuf: labwc starts headless on software GLES2 (llvmpipe), draws a frame that
#      grim can capture, and exits cleanly. Without the device this part is skipped, and says so.
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq --no-install-recommends binutils >/dev/null

libs=$(readelf -d /usr/bin/labwc | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')
first=$(echo "$libs" | grep -E '^lib(scenefx|wlroots)' | head -n1)
case "$first" in
libscenefx-0.5*) echo "links $first ahead of wlroots" ;;
*) echo "labwc does not link libscenefx-0.5 ahead of wlroots:"; echo "$libs"; exit 1 ;;
esac

if [ ! -e /dev/udmabuf ]; then
	echo "headless run skipped: no /dev/udmabuf in this container"
	exit 0
fi
apt-get install -y -qq --no-install-recommends libgl1-mesa-dri libegl-mesa0 grim file >/dev/null

run=$(mktemp -d)
mkdir "$run/config" "$run/xdg"
chmod 700 "$run/xdg"
export XDG_RUNTIME_DIR="$run/xdg" WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=1 WLR_RENDERER=gles2 \
	WLR_RENDERER_FORCE_SOFTWARE=1
startup="sh -c 'sleep 2; grim $run/shot.png; labwc --exit'"
rc=0
timeout 60 labwc -d -C "$run/config" -s "$startup" > "$run/log" 2>&1 || rc=$?
if [ "$rc" != 0 ] || ! grep -q 'Creating scenefx FX renderer' "$run/log" \
	|| ! file "$run/shot.png" 2>/dev/null | grep -q 'PNG image'; then
	set +e # from here on, report as much as possible
	echo "headless run failed (exit $rc), last lines of the labwc log:"
	tail -n 40 "$run/log"
	# Run it again under gdb, with debug symbols of labwc (built next to it) and SceneFX.
	echo "--- backtrace"
	. /etc/os-release
	echo "Types: deb
URIs: http://deb.debian.org/debian-debug
Suites: $VERSION_CODENAME-debug
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg" > /etc/apt/sources.list.d/debug.sources
	apt-get update -qq
	apt-get install -y -qq --no-install-recommends gdb >/dev/null
	ls /out/labwc-dbgsym_*.deb >/dev/null 2>&1 && apt-get install -y -qq /out/labwc-dbgsym_*.deb >/dev/null
	apt-get install -y -qq libscenefx-0.5-dbgsym >/dev/null 2>&1 || echo "(no SceneFX debug symbols)"
	timeout 120 gdb --batch -ex run -ex 'bt full' \
		--args labwc -C "$run/config" -s "$startup" 2>&1 | grep -v -E '^\[(New|Thread)' | tail -n 80
	exit 1
fi
echo "headless run: $(file -b "$run/shot.png")"
