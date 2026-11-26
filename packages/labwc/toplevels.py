# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Print "<identifier> <app-id>" for every toplevel the compositor lists through
# ext-foreign-toplevel-list-v1. The identifier is what grim -T takes to capture
# one window (ext-image-copy-capture with a foreign toplevel source).
# Used by packages/labwc/test.sh.
from pywayland.client import Display
from pywayland.protocol.ext_foreign_toplevel_list_v1 import (
    ExtForeignToplevelListV1,
)

toplevels = []


def on_toplevel(_list, handle):
    entry = {"identifier": None, "app_id": ""}
    toplevels.append(entry)
    handle.dispatcher["identifier"] = lambda _h, value: entry.update(identifier=value)
    handle.dispatcher["app_id"] = lambda _h, value: entry.update(app_id=value)


def on_global(registry, name, interface, version):
    if interface == ExtForeignToplevelListV1.name:
        toplevel_list = registry.bind(name, ExtForeignToplevelListV1, 1)
        toplevel_list.dispatcher["toplevel"] = on_toplevel
        found.append(toplevel_list)


found = []
display = Display()
display.connect()
registry = display.get_registry()
registry.dispatcher["global"] = on_global
display.roundtrip()  # globals
if not found:
    raise SystemExit("ext_foreign_toplevel_list_v1 is not advertised")
display.roundtrip()  # toplevels
display.roundtrip()  # their identifiers and app ids
for entry in toplevels:
    print(entry["identifier"], entry["app_id"])
display.disconnect()
