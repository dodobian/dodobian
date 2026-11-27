# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Test of patch 0004 (workspaces per output, dynamic workspaces). Run by test.sh after the
# SceneFX checks, with its environment (headless, software GLES2). Labwc runs twice on two
# headless outputs of 1280x720, side by side:
#   1. <desktops perOutput="yes" dynamic="yes">: foot windows a (left output), b (right) and c;
#      after every step the workspace groups as clients see them (workspaces.py, ext-workspace-v1)
#      and the workspace of every window (labwc's scene dump, scene-views.py) are compared with
#      what is expected: workspaces are added and removed only on request (AddDesktop,
#      RemoveDesktop, GoToDesktop right of an occupied last workspace, create_workspace and
#      remove from a client) and stay while empty, they never wrap, switching one output leaves
#      the other alone, a new window lands on the current workspace of its output, MoveToOutput
#      takes a window to the other output's current workspace, and an output switched off hands
#      its windows to the remaining one.
#   2. Without the options: one workspace group spans both outputs, as in stock Labwc.
# Exit status 0 when every check passes.
here=$(cd "$(dirname "$0")" && pwd)
run=$(mktemp -d)
mkdir -p "$run/config"
export WLR_HEADLESS_OUTPUTS=2 RUN="$run" HERE="$here"

cat > "$run/scenario.sh" <<'EOF'
exec > "$RUN/out" 2>&1
ws() { python3 -I "$HERE/workspaces.py" | tr '\n' '|' | sed 's/|$//'; }
views() {
	n=$(wc -c < "$RUN/log"); wtype -M alt -k F12 -m alt; sleep 0.8
	tail -c +$((n + 1)) "$RUN/log" | python3 -I "$HERE/scene-views.py"
}
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: expected '$2', got '$3'"; fi; }
windows() {
	i=0
	while [ "$(python3 -I "$HERE/toplevels.py" 2>/dev/null | wc -l)" -ne "$1" ] && [ $i -lt 40 ]; do
		sleep 0.25; i=$((i + 1))
	done
	sleep 0.5
}
term() { foot -o colors-dark.background=3060c0 --app-id "$1" sh -c 'sleep 600' 2>/dev/null & }
key() { wtype "$@"; sleep 0.4; }

wlr-randr --output HEADLESS-1 --pos 0,0 --output HEADLESS-2 --pos 1280,0
sleep 0.5
if [ "$MODE" = stock ]; then
	check "one group for both outputs" "HEADLESS-1,HEADLESS-2: *1 2 3 4" "$(ws)"
	key -M ctrl -M alt -k Right -m alt -m ctrl
	check "GoToDesktop switches both" "HEADLESS-1,HEADLESS-2: 1 *2 3 4" "$(ws)"
	echo DONE; labwc --exit; exit
fi
key -M alt -k F1 -m alt
check "start" "HEADLESS-1: *1|HEADLESS-2: *1" "$(ws)"
key -M ctrl -M alt -k Right -m alt -m ctrl
check "right of an empty last workspace: nothing" "HEADLESS-1: *1|HEADLESS-2: *1" "$(ws)"
key -M alt -k a -m alt
check "AddDesktop without a window, and go there" "HEADLESS-1: 1 *2|HEADLESS-2: *1" "$(ws)"
key -M alt -k s -m alt
check "AddDesktop follow=no" "HEADLESS-1: 1 *2 3|HEADLESS-2: *1" "$(ws)"
key -M ctrl -M alt -k Left -m alt -m ctrl
check "empty workspaces stay" "HEADLESS-1: *1 2 3|HEADLESS-2: *1" "$(ws)"
term a; windows 1
term b; windows 2
check "no workspace appears for a window" "HEADLESS-1: *1 2 3|HEADLESS-2: *1" "$(ws)"
check "a and b on their outputs" "a=HEADLESS-1/1 b=HEADLESS-2/1" "$(views)"
python3 -I "$HERE/workspaces.py" HEADLESS-1 2; sleep 0.3
check "switching the left output leaves the right one" "HEADLESS-1: 1 *2 3|HEADLESS-2: *1" "$(ws)"
term c; c=$!; windows 3
check "c on the left output's current workspace" "a=HEADLESS-1/1 b=HEADLESS-2/1 c=HEADLESS-1/2" "$(views)"
key -M alt -k r -m alt
check "RemoveDesktop: renamed, the left neighbour is current" "HEADLESS-1: *1 2|HEADLESS-2: *1" "$(ws)"
check "RemoveDesktop: c goes to the left neighbour" "a=HEADLESS-1/1 b=HEADLESS-2/1 c=HEADLESS-1/1" "$(views)"
kill "$c"; windows 2
python3 -I "$HERE/workspaces.py" HEADLESS-2 +; sleep 0.3
check "create_workspace from a client" "HEADLESS-1: *1 2|HEADLESS-2: *1 2" "$(ws)"
python3 -I "$HERE/workspaces.py" HEADLESS-1 2 remove; sleep 0.3
check "remove from a client" "HEADLESS-1: *1|HEADLESS-2: *1 2" "$(ws)"
key -M alt -k F2 -m alt; key -M ctrl -M alt -k Right -m alt -m ctrl
check "GoToDesktop on the right output" "HEADLESS-1: *1|HEADLESS-2: 1 *2" "$(ws)"
key -M ctrl -M alt -k Left -m alt -m ctrl; key -M ctrl -M alt -k Left -m alt -m ctrl
check "left of the first workspace: no wrap" "HEADLESS-1: *1|HEADLESS-2: *1 2" "$(ws)"
python3 -I "$HERE/workspaces.py" HEADLESS-2 2 remove; sleep 0.3
key -M ctrl -M alt -k Right -m alt -m ctrl
check "right of an occupied last workspace: a new one" "HEADLESS-1: *1|HEADLESS-2: 1 *2" "$(ws)"
key -M ctrl -M alt -k Left -m alt -m ctrl; key -M alt -k F1 -m alt
key -M alt -k r -m alt
check "the only workspace stays" "HEADLESS-1: *1|HEADLESS-2: *1 2" "$(ws)"
key -M alt -k F3 -m alt; sleep 0.3
check "MoveToOutput: a on the right output" "a=HEADLESS-2/1 b=HEADLESS-2/1" "$(views)"
wlr-randr --output HEADLESS-2 --off; sleep 1
check "right output off: its windows move left" "a=HEADLESS-1/1 b=HEADLESS-1/1" "$(views)"
check "right output off: its group is gone" "HEADLESS-1: *1" "$(ws)"
wlr-randr --output HEADLESS-2 --on --pos 1280,0; sleep 1
check "right output back: a group again" "HEADLESS-2" "$(ws | tr '|' '\n' | sed -n 's/^\(HEADLESS-2\):.*/\1/p')"
echo DONE
labwc --exit
EOF

result=0
for MODE in per-output stock; do
	if [ "$MODE" = stock ]; then
		desktops='<desktops number="4" prefix="" popupTime="0"/>'
	else
		desktops='<desktops perOutput="yes" dynamic="yes" prefix="" popupTime="0"/>'
	fi
	cat > "$run/config/rc.xml" <<EOF
<?xml version="1.0"?>
<labwc_config>
  $desktops
  <keyboard>
    <keybind key="C-A-Right"><action name="GoToDesktop" to="right" wrap="yes"/></keybind>
    <keybind key="C-A-Left"><action name="GoToDesktop" to="left" wrap="yes"/></keybind>
    <keybind key="A-F1"><action name="FocusOutput" output="HEADLESS-1"/></keybind>
    <keybind key="A-F2"><action name="FocusOutput" output="HEADLESS-2"/></keybind>
    <keybind key="A-F3"><action name="MoveToOutput" output="HEADLESS-2"/></keybind>
    <keybind key="A-a"><action name="AddDesktop"/></keybind>
    <keybind key="A-s"><action name="AddDesktop" follow="no"/></keybind>
    <keybind key="A-r"><action name="RemoveDesktop"/></keybind>
    <keybind key="A-F12"><action name="Debug"/></keybind>
  </keyboard>
  <windowRules>
    <windowRule identifier="a"><action name="MoveTo" x="100" y="100"/></windowRule>
    <windowRule identifier="b"><action name="MoveTo" x="1380" y="100"/></windowRule>
    <windowRule identifier="c"><action name="MoveTo" x="600" y="100"/></windowRule>
  </windowRules>
</labwc_config>
EOF
	rm -f "$run/out"
	rc=0
	MODE=$MODE timeout 90 stdbuf -o0 labwc -C "$run/config" -s "sh $run/scenario.sh" > "$run/log" 2>&1 || rc=$?
	echo "--- workspaces, $MODE"
	cat "$run/out"
	if [ "$rc" != 0 ] || ! grep -q '^DONE' "$run/out" || grep -q '^FAIL' "$run/out"; then
		echo "workspaces test failed ($MODE, labwc exit $rc); last lines of the labwc log:"
		grep -v -e '^ ' -e '^$' "$run/log" | tail -n 20
		result=1
	fi
done
exit $result
