# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Package test, run by packages/build.sh after install (as root, in a clean debian:forky container).
# The whole session runs once, headless, with two outputs and a user session.conf:
#   - every script passes dash -n, and no monitor name ships in the package;
#   - dodo-session starts labwc (the archive's: pixman, no GPU) with our layers, and labwc
#     reports no error from its config, menu or actions;
#   - the login-time files are valid: the xfdesktop wallpaper defaults (XML, one entry per output);
#     the panel wrapper starts Waybar with the Dodo panel;
#   - the session log says labwc exited cleanly, warns that this labwc is not our build, and
#     ignores the old pinned= key.
apt-get install -y -qq --no-install-recommends libxml2-utils >/dev/null

echo "scripts"
for f in /usr/bin/dodo-session /usr/libexec/dodo-session/* /usr/share/dodo-session/common.sh; do dash -n "$f"; done
names=$(dpkg -L dodo-session | while read -r f; do [ -f "$f" ] && grep -lE "Virtual-[0-9]|DP-[0-9]|HDMI-[A-Z]-[0-9]" "$f"; done || true)
[ -z "$names" ] || { echo "monitor names in: $names"; exit 1; }

run=$(mktemp -d)
mkdir -p "$run/xdg" "$run/home/.config/dodo" "$run/home/.config/labwc" "$run/shim" "$run/snap"
chmod 700 "$run/xdg"
printf 'primary = HEADLESS-2\npinned = HEADLESS-1\n' > "$run/home/.config/dodo/session.conf"
# Waybar is not started: a stand-in records the arguments the wrapper hands it.
printf '#!/bin/sh\necho "$@" > %s/snap/waybar-args\n' "$run" > "$run/shim/waybar"
chmod 755 "$run/shim/waybar"
# The user's autostart (read after ours): run the panel wrapper, keep the login-time layer, leave.
cat > "$run/home/.config/labwc/autostart" <<EOF
sleep 2
PATH=$run/shim:\$PATH DODO_SESSION=1 /usr/libexec/dodo-session/waybar
cp -r "\$XDG_RUNTIME_DIR/dodo" $run/snap/
labwc --exit
EOF

echo "session"
rc=0
env -i HOME="$run/home" PATH=/usr/bin:/bin XDG_RUNTIME_DIR="$run/xdg" LANG=C.UTF-8 \
	WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=2 WLR_RENDERER=pixman WLR_NO_HARDWARE_CURSORS=1 \
	timeout 60 dodo-session || rc=$?
log="$run/home/.local/state/dodo-session.log"
cat "$log"
[ "$rc" = 0 ] || { echo "dodo-session exited with $rc"; exit 1; }
grep -q "labwc exited with 0" "$log"
grep -q "warning: labwc .* is not a Dodobian build" "$log"
grep -q "ignoring pinned=" "$log"
if grep -E '\[ERROR\] \[[^]]*src/(config|menu|action)' "$log"; then
	echo "labwc found errors in the Dodo config"; exit 1
fi
[ ! -e "$run/xdg/dodo" ] || { echo "runtime layer left behind"; exit 1; }

echo "login-time files"
s="$run/snap/dodo"
[ ! -e "$s/xdg/labwc" ] || { echo "a login-time labwc layer is back"; exit 1; }
x="$s/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"
xmllint --noout "$x"
[ "$(grep -c 'name="monitorHEADLESS-[12]"' "$x")" = 2 ]
grep -q -- "-c /usr/share/dodo/waybar/config.json" "$run/snap/waybar-args"
echo "terminal"
t=$(env -i HOME="$run/home" PATH=/usr/bin:/bin XDG_CONFIG_DIRS=/usr/share/dodo/xdg:/etc/xdg xdg-terminal-exec --print-id)
[ "$t" = xfce4-terminal.desktop ] || { echo "default terminal is $t"; exit 1; }
echo "session test: ok"
