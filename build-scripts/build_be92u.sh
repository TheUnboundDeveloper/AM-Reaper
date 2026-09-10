#!/bin/bash
# Reaper build launcher -- RT-BE92U (BCM6765, tri-band 2.4/5/6 GHz, 96765GW profile)
# Builds in the git WORKTREE /home/reaper/port/rt-be92u (canon stays on be96u-only).
# Flow:  (worktree on rt-be92u) ; bump+commit version.conf there ; build_be92u.sh [ship]
#
# RETIRED from the build roster after v3.1.2 (owner, 2026-09-10): upstream Merlin
# has taken this model on. It is off the CI matrix, off cut_fleet's port list and
# out of refresh_manifest's model list, and its intended replacement is the
# GT-BE19000.
#
# This file is KEPT rather than deleted because the model's source is dormant,
# not gone, and because the cold-tree libtool pins below were expensive to find
# (2026-08-23, after four failed CI runs) and exist nowhere else in a form
# specific to this target. Set REAPER_BUILD_RETIRED=1 to build it anyway.

case "${1:-}" in
  -h|--help) sed -n "2,4 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac

if [ "${REAPER_BUILD_RETIRED:-0}" != "1" ]; then
  cat >&2 <<'EOF'
RT-BE92U is retired from the build roster (owner, 2026-09-10 - Merlin has taken
this model on). Its source, branch, worktree and overlay are intentionally left
in place, so this is a roster decision, not a broken tree.

To build it anyway:  REAPER_BUILD_RETIRED=1 build-scripts/build_be92u.sh [ship]

To bring it back properly, re-add RT-BE92U to:
  .github/workflows/public-build.yml   the model choice list, both matrices,
                                       and the two MODELS= lists
  build-scripts/cut_fleet.sh           the MODELS roster
and drop the RT-BE92U case in release.yml if it should stop being a prerelease.
EOF
  exit 3
fi
export REAPER_TREE=/home/reaper/port/rt-be92u
export REAPER_TDIR=$REAPER_TREE/release/src-rt-5.04behnd.4916/targets/96765GW
# COLD-TREE LIBTOOL PINS (same as build-scripts/ci/build_one.sh). A worktree is a
# cold tree: the samba crypto chain (zlib/gmp/nettle/gnutls) is configured fresh
# under the vendor make env, where libtool's GNU-ld probe answers "no" and
# archive_cmds ends up EMPTY -> libgmp is never linked, only symlinked, and
# `make install` dies on `cannot stat .libs/libgmp.so.10.4.1`. Hit on the first
# RT-BE92U build (2026-08-23) exactly as in CI runs #1-#4. The warm canon tree
# never reconfigures the chain, which is why local builds never saw it.
export lt_cv_sys_max_cmd_len="${lt_cv_sys_max_cmd_len:-1572864}"
_tc="$(ls -d /opt/toolchains/crosstools-arm_softfp-gcc-10.3*/usr/bin 2>/dev/null | head -1)"
[ -x "$_tc/arm-buildroot-linux-gnueabi-ld" ] && export lt_cv_path_LD="${lt_cv_path_LD:-$_tc/arm-buildroot-linux-gnueabi-ld}"
export lt_cv_prog_gnu_ld="${lt_cv_prog_gnu_ld:-yes}"
echo "libtool LD pin: lt_cv_path_LD=${lt_cv_path_LD:-<unset>} lt_cv_prog_gnu_ld=$lt_cv_prog_gnu_ld"
BRANCH=rt-be92u
TARGET=rt-be92u
PREFIX=RT-BE92U
VARIANTS="${VARIANTS:-MCP noMCP}"
STORAGE="${STORAGE:-nand}"
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
