# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 The Dodobian authors
#
# The container side of run.sh (see there): build probe.c, run the cases, look into the crashes.
# Arguments: cases (default: all). The repository is at /src (read-only), results go to /out.
export DEBIAN_FRONTEND=noninteractive
out=/out
sum=$out/summary.txt
apt-get update -qq
apt-get install -y -qq --no-install-recommends build-essential pkg-config libscenefx-0.5-dev \
	libwlroots-0.20-dev libwayland-dev libegl-dev libgles-dev libdrm-dev libpixman-1-dev \
	libgl1-mesa-dri libegl-mesa0 >/dev/null

# Our SceneFX Labwc renders the same way: GLES2 forced to software, which is llvmpipe here.
export WLR_RENDERER=gles2 WLR_RENDERER_FORCE_SOFTWARE=1
mkdir -p /tmp/probe && cd /tmp/probe || exit 1
# libscenefx first: it exports the same wlr_scene_* symbols as wlroots (as in labwc/patches/0002).
# shellcheck disable=SC2046 # pkg-config prints a list of options
cc -std=c11 -g -O1 -Wall -Wextra -Werror -DWLR_USE_UNSTABLE -o probe /src/labwc/tools/llvmpipe-probe/probe.c \
	$(pkg-config --cflags --libs scenefx-0.5 wlroots-0.20 wayland-server egl glesv2 libdrm pixman-1)

cases=${*:-$(./probe --list)}
multiarch=$(gcc -print-multiarch)
gallium=$(readlink -f /usr/lib/"$multiarch"/libgallium-*.so)
mesa=$(dpkg-query -W -f '${Version}' libgl1-mesa-dri)
llvm=$(ldd "$gallium" | sed -n 's/^[[:space:]]*\(libLLVM[^ ]*\).*/\1/p')
{
	echo "arch:   $(uname -m)"
	echo "cpu:    $(sed -n -e 's/^model name[[:space:]]*: //p' -e 's/^Model name[[:space:]]*: //p' /proc/cpuinfo | head -n1)"
	echo "flags:  $(grep -o -w -E 'avx512f|avx2|avx|sse4_1|asimd' /proc/cpuinfo | sort -u | tr '\n' ' ')"
	echo "mesa:   $mesa ($(basename "$gallium"), $llvm)"
	echo "env:    $(env | grep -E '^(LP_|GALLIUM_|GALLIVM_|MESA_|LIBGL_)' | tr '\n' ' ')"
	echo "device: $([ -e /dev/udmabuf ] && echo /dev/udmabuf || echo 'no /dev/udmabuf: scene:*, wlr:*, *-dmabuf* skipped')"
	echo
} > "$sum"

# run <case> <file stem>: exit status of the probe (124 timeout, 128+N killed by signal N)
run() {
	rc=0
	timeout 60 ./probe "$1" "$out/$2.ppm" > "$out/$2.log" 2>&1 || rc=$?
	return "$rc"
}

crashed=
errors=0
for c in $cases; do
	stem=$(echo "$c" | tr ':' '_')
	case "$c" in
	scene:*|wlr:*|*-dmabuf*) [ -e /dev/udmabuf ] || { printf '%-30s skipped\n' "$c" >> "$sum"; continue; } ;;
	esac
	rc=0
	run "$c" "$stem" || rc=$?
	case "$rc" in
	0) res=ok ;;
	2) res="error: $(grep '^probe:' "$out/$stem.log" | tail -n1)"; errors=$((errors + 1)) ;;
	124) res="timeout (60 s)"; crashed="$crashed $c" ;;
	*)
		if [ "$rc" -gt 128 ]; then res="CRASHED: $(kill -l $((rc - 128)) 2>/dev/null || echo "signal $((rc - 128))")"
		else res="exit $rc"; errors=$((errors + 1)); fi
		crashed="$crashed $c" ;;
	esac
	printf '%-30s %s\n' "$c" "$res" >> "$sum"
done

# Each crashed case again: under gdb with debug symbols, threaded (the crashing rasterizer thread
# and its JIT code) and with LP_NUM_THREADS=0 (llvmpipe rasterizes in the calling thread, so the
# stack shows which GL call led there); then once with GALLIVM_DEBUG to keep the LLVM IR.
if [ -n "$crashed" ]; then
	# shellcheck source=/dev/null
	. /etc/os-release
	printf 'Types: deb\nURIs: http://deb.debian.org/debian-debug\nSuites: %s-debug\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\n' \
		"$VERSION_CODENAME" > /etc/apt/sources.list.d/debug.sources
	apt-get update -qq
	apt-get install -y -qq --no-install-recommends gdb libc6-dbg >/dev/null
	# Debug symbols of the libraries in the crash path, by the packages that ship them.
	for lib in "$gallium" /usr/lib/"$multiarch"/libscenefx-0.5.so /usr/lib/"$multiarch"/libwlroots-0.20.so \
		/usr/lib/"$multiarch"/libEGL_mesa.so.0; do
		p=$(dpkg -S "$(readlink -f "$lib")" | cut -d: -f1)
		apt-get install -y -qq --no-install-recommends "$p-dbgsym" >/dev/null 2>&1 \
			|| echo "(no debug symbols: $p-dbgsym)" >> "$sum"
	done
	for c in $crashed; do
		stem=$(echo "$c" | tr ':' '_')
		for threads in default 0; do
			(
				echo "=== $c, LP_NUM_THREADS=$threads"
				[ "$threads" = default ] || export LP_NUM_THREADS="$threads"
				# The crashing thread's stack and code, then where the main thread was.
				# shellcheck disable=SC2016 # $pc is for gdb
				timeout 300 gdb --batch -ex run -ex 'bt 40' -ex 'x/12i $pc' -ex 'info threads' \
					-ex 'thread apply 1 bt 25' --args ./probe "$c" 2>&1 \
					| grep -v -E '^\[(New|Thread .* exited)' || true
			) >> "$out/$stem.gdb.txt"
		done
		GALLIVM_DEBUG=ir,asm timeout 120 ./probe "$c" > "$out/$stem.ir.txt" 2>&1 || true
	done
	{ echo; echo "backtraces: <case>.gdb.txt, LLVM IR and assembly: <case>.ir.txt"; } >> "$sum"
fi

chown -R "$HOST_UID:$HOST_GID" "$out"
cat "$sum"
[ "$errors" = 0 ]
