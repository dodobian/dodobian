# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# Shared by the dodo-session scripts (sourced, not run).

DODO_LIB=/usr/libexec/dodo-session
DODO_DEFAULTS=/usr/share/dodo

# Timestamped line in the session log (the scripts send stderr there).
say() {
	printf '%s %s: %s\n' "$(date +%H:%M:%S)" "${0##*/}" "$*" >&2
}

# Value of a key in session.conf: the machine file first, the user's file wins.
# Lines are "key = value"; "#" starts a comment line. The files are read, never sourced.
conf_get() {
	for f in /etc/dodo/session.conf "${XDG_CONFIG_HOME:-$HOME/.config}/dodo/session.conf"; do
		[ -r "$f" ] && sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*\([^[:space:]]*\)[[:space:]]*$/\1/p" "$f"
	done | tail -n 1
}

# Output names go into generated XML and JSON: letters, digits and - _ . only
# (a comma separates names in a list).
valid_outputs() {
	case $1 in
	*[!A-Za-z0-9._,-]*) return 1 ;;
	esac
	return 0
}

# The runtime layer: generated at login, first in XDG_CONFIG_DIRS.
runtime_dir() {
	printf '%s/dodo' "${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is not set}"
}
