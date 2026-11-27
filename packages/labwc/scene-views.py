# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Read labwc's scene dump (the Debug action) from stdin and print "app=workspace" for every
# window, sorted, e.g. "a=HEADLESS-1/1 b=HEADLESS-2/1". Per-output workspaces are named
# OUTPUT/NAME in the dump (patch 0004). Used by packages/labwc/workspaces.sh.
import re
import sys

workspace, views = None, {}
for line in sys.stdin:
    match = re.match(r" {6}\+-- (\S.*?) {2,}-?\d+ +-?\d+ +\[", line)
    if match:
        workspace = match.group(1)
    match = re.search(r"\+-- view \((\w+)\)", line)
    if match:
        views[match.group(1)] = workspace
print(" ".join(f"{app}={ws}" for app, ws in sorted(views.items())))
