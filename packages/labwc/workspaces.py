# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# ext-workspace-v1 client for packages/labwc/workspaces.sh.
#   workspaces.py              print one line per workspace group, sorted:
#                              "OUTPUT[,OUTPUT]: 1 *2 3" (* marks the active workspace)
#   workspaces.py OUTPUT NAME  activate workspace NAME of the group on OUTPUT
#   workspaces.py OUTPUT NAME remove
#                              remove workspace NAME of the group on OUTPUT
#   workspaces.py OUTPUT +     add a workspace to the group on OUTPUT
import sys

from pywayland.client import Display
from pywayland.protocol.ext_workspace_v1 import ExtWorkspaceManagerV1
from pywayland.protocol.wayland import WlOutput

outputs = {}
groups = []
workspaces = {}
managers = []


def on_group(_manager, handle):
    group = {"handle": handle, "outputs": [], "workspaces": []}
    groups.append(group)
    handle.dispatcher["output_enter"] = lambda _h, o: group["outputs"].append(o)
    handle.dispatcher["output_leave"] = lambda _h, o: group["outputs"].remove(o)
    handle.dispatcher["workspace_enter"] = lambda _h, w: group["workspaces"].append(w)
    handle.dispatcher["workspace_leave"] = lambda _h, w: group["workspaces"].remove(w)
    handle.dispatcher["removed"] = lambda _h: groups.remove(group)


def on_workspace(_manager, handle):
    entry = {"name": "?", "active": False}
    workspaces[handle] = entry
    handle.dispatcher["name"] = lambda _h, name: entry.update(name=name)
    handle.dispatcher["state"] = lambda _h, state: entry.update(active=bool(state & 1))


def on_global(registry, name, interface, version):
    if interface == "wl_output":
        output = registry.bind(name, WlOutput, 4)
        output.dispatcher["name"] = lambda proxy, value: outputs.__setitem__(proxy, value)
    elif interface == ExtWorkspaceManagerV1.name:
        manager = registry.bind(name, ExtWorkspaceManagerV1, 1)
        manager.dispatcher["workspace_group"] = on_group
        manager.dispatcher["workspace"] = on_workspace
        managers.append(manager)


def label(group):
    return ",".join(sorted(outputs.get(o, "?") for o in group["outputs"])) or "-"


display = Display()
display.connect()
display.get_registry().dispatcher["global"] = on_global
for _ in range(4):
    display.roundtrip()
if not managers:
    raise SystemExit("ext_workspace_manager_v1 is not advertised")

status = 0
if len(sys.argv) in (3, 4):
    wanted_output, wanted_name = sys.argv[1:3]
    remove = sys.argv[3:] == ["remove"]
    status = f"no workspace {wanted_name} on {wanted_output}"
    for group in groups:
        if wanted_output not in label(group).split(","):
            continue
        if wanted_name == "+":
            group["handle"].create_workspace("")
            status = 0
        for handle in group["workspaces"]:
            if workspaces[handle]["name"] == wanted_name:
                handle.remove() if remove else handle.activate()
                status = 0
    if status == 0:
        managers[0].commit()
        display.roundtrip()
else:
    for group in sorted(groups, key=label):
        names = [("*" if workspaces[w]["active"] else "") + workspaces[w]["name"]
                 for w in group["workspaces"]]
        print(label(group) + ": " + " ".join(names))
display.disconnect()
sys.exit(status)
