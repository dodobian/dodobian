# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Test of our Labwc patches (labwc/patches/0001-0004). Run by packages/build.sh inside the
# install-test container, after our labwc is installed.
#   1. labwc links libscenefx-0.5, ahead of wlroots (they export the same wlr_scene_* symbols).
#   2. With /dev/udmabuf: labwc starts headless on software GLES2 (Mesa llvmpipe) with two foot
#      windows on a white background, one with server-side decorations and one with client-side
#      ones, then
#      - grim captures the screen, and check-shot.py checks that both windows have all four corners
#        rounded, are not cut and cast a soft shadow (patch 0003);
#      - toplevels.py lists the windows (ext-foreign-toplevel-list), grim -T captures each one
#        (ext-image-copy-capture with a toplevel source), and check-shot.py checks the size and
#        the rounded corners of each capture;
#      - labwc exits cleanly;
#      - workspaces.sh checks workspaces per output and dynamic workspaces (patch 0004).
#      Without the device this part is skipped, and says so.
#   Screenshots go to /test-out when packages/build.sh provides it (build/labwc/test/, also in the
#   CI artifacts).
#
# Software cursor (WLR_NO_HARDWARE_CURSORS=1): on the headless backend wlroots would draw the cursor
# into a "hardware" cursor buffer of its own, 10x16 from the udmabuf allocator, whose stride is
# width * 4 = 40 bytes; llvmpipe on x86 reads colour rows with aligned 16-byte loads and crashes on
# it (Mesa 26.1.6, wlroots 0.20.2; arm64 tolerates the unaligned rows). Not SceneFX: wlroots' own
# renderer crashes the same way. Found with labwc/tools/llvmpipe-probe (wlr:cursor-hw,
# gl:tex-small-dmabuf). A software cursor is drawn into the frame instead, so grim sees it too.
#
# Window sizes are multiples of 4: a window capture renders into a udmabuf buffer of exactly the
# window's size, and llvmpipe writes it in 4x4 tiles, past the end of the buffer when the height is
# not a multiple of 4. It crashes when that runs over the last page (stock Labwc as well, on amd64
# and arm64). The decorated window captures as its content, 440x300; foot adds an invisible 5 px
# resize border around its client-side decorations, so the other window, 442x302, captures as
# 452x312.
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
apt-get install -y -qq --no-install-recommends libgl1-mesa-dri libegl-mesa0 grim file foot swaybg \
	python3-pywayland fonts-dejavu-core wtype wlr-randr >/dev/null

here=$(dirname "$0")
run=$(mktemp -d)
mkdir "$run/config" "$run/xdg" "$run/shots"
chmod 700 "$run/xdg"
export XDG_RUNTIME_DIR="$run/xdg" WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=1 WLR_RENDERER=gles2 \
	WLR_RENDERER_FORCE_SOFTWARE=1 WLR_NO_HARDWARE_CURSORS=1 LANG=C.UTF-8

cat > "$run/config/rc.xml" <<'EOF'
<?xml version="1.0"?>
<labwc_config>
  <core><decoration>server</decoration></core>
  <theme><cornerRadius>12</cornerRadius><dropShadows>yes</dropShadows></theme>
  <windowRules>
    <windowRule identifier="ssd-win">
      <action name="MoveTo" x="120" y="140"/>
      <action name="ResizeTo" width="440" height="300"/>
    </windowRule>
    <windowRule identifier="csd-win">
      <action name="MoveTo" x="700" y="140"/>
      <action name="ResizeTo" width="442" height="302"/>
    </windowRule>
  </windowRules>
</labwc_config>
EOF
# One blue for title, border and terminal background, so a window is one blue area.
cat > "$run/config/themerc-override" <<'EOF'
border.width: 2
window.active.title.bg.color: #3060c0
window.inactive.title.bg.color: #3060c0
window.active.border.color: #3060c0
window.inactive.border.color: #3060c0
window.active.shadow.size: 30
window.inactive.shadow.size: 30
window.active.shadow.color: #000000a0
window.inactive.shadow.color: #000000a0
window.active.shadow.offset.y: 8
window.inactive.shadow.offset.y: 8
EOF
cat > "$run/startup.sh" <<EOF
swaybg -c '#ffffff' &
foot -o resize-by-cells=no -o colors-dark.background=3060c0 --app-id ssd-win sh -c 'sleep 120' &
foot -o resize-by-cells=no -o colors-dark.background=3060c0 -o csd.preferred=client \
	-o csd.color=ff3060c0 --app-id csd-win sh -c 'sleep 120' &
# Wait for both windows, then for them to be placed and drawn.
i=0
while [ "\$(python3 -I $here/toplevels.py 2>/dev/null | wc -l)" -lt 2 ] && [ \$i -lt 40 ]; do
	sleep 0.5; i=\$((i + 1))
done
sleep 2
grim -t ppm $run/shots/screen.ppm
grim $run/shots/screen.png
python3 -I $here/toplevels.py > $run/shots/toplevels.txt
while read -r id app; do grim -t ppm -T "\$id" $run/shots/\$app.ppm; done < $run/shots/toplevels.txt
labwc --exit
EOF

# headless: start labwc once; exit status 0 only for a clean run with the SceneFX renderer and
# all screenshots.
headless() {
	rm -f "$run/shots/"*
	rc=0
	timeout 90 labwc -d -C "$run/config" -s "sh $run/startup.sh" > "$run/log" 2>&1 || rc=$?
	renderer=$(grep -o 'GL renderer: .*' "$run/log" | head -n1)
	[ -d /test-out ] && cp "$run/shots/"* /test-out/ 2>/dev/null
	[ "$rc" = 0 ] && grep -q 'Creating scenefx FX renderer' "$run/log" \
		&& file "$run/shots/screen.png" 2>/dev/null | grep -q 'PNG image' \
		&& [ -s "$run/shots/ssd-win.ppm" ] && [ -s "$run/shots/csd-win.ppm" ]
}

if headless; then
	echo "headless run: $(file -b "$run/shots/screen.png") ($renderer)"
	echo "--- screenshot checks"
	ok=0
	python3 -I "$here/check-shot.py" screen "$run/shots/screen.ppm" 2 || ok=1
	python3 -I "$here/check-shot.py" capture "$run/shots/ssd-win.ppm" 440 300 || ok=1
	python3 -I "$here/check-shot.py" capture "$run/shots/csd-win.ppm" 452 312 || ok=1
	sh "$here/workspaces.sh" || ok=1
	exit "$ok"
fi

set +e # from here on, report as much as possible
echo "headless run failed (exit $rc), screenshots: $(ls "$run/shots" | tr '\n' ' ')"
echo "last lines of the labwc log:"
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
	--args labwc -C "$run/config" -s "sh $run/startup.sh" 2>&1 | grep -v -E '^\[(New|Thread)' | tail -n 80
exit 1
