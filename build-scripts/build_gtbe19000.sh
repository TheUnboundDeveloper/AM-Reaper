#!/bin/bash
# Reaper build launcher -- GT-BE19000 (ROG Rapture, non-AI SKU; tri-band 2.4/5/6 GHz, BCM4916 / 96813GW)
# Builds in the git WORKTREE /home/reaper/port/gt-be19000 (canon stays on be96u-only).
# Flow:  (worktree on gt-be19000) ; bump+commit version.conf there ; build_gtbe19000.sh [ship]
#
# Onboarded 2026-09-10 from the ASUS GPL 102_39274 drop. Same silicon, profile
# and NAND layout as the RT-BE96U (only the GT-BE19000AI SKU is eMMC), so this
# launcher is the RT-BE92U's worktree shape with the RT-BE96U's target dir.
#
# BEFORE THE FIRST BUILD, two things the tree cannot supply on its own:
#   1. bootloaders/obj.gt-be19000/ must be copied over u-boot-2019.07/ by hand
#      (RTL_OBJS.o is untracked on every branch; the model enables rtl8372).
#   2. dongle firmware: the GPL drop ships none, and the build takes it from
#      bcmdrivers/.../dongle/sysdeps/GT-BE19000/{6717a0,6726b0}/rtecdc.bin,
#      which does not exist until the owner decides its source.

case "${1:-}" in
  -h|--help) sed -n "2,4 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
export REAPER_TREE=/home/reaper/port/gt-be19000
export REAPER_TDIR=$REAPER_TREE/release/src-rt-5.04behnd.4916/targets/96813GW
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
BRANCH=gt-be19000
TARGET=gt-be19000
PREFIX=GT-BE19000
VARIANTS="${VARIANTS:-MCP noMCP}"
STORAGE="${STORAGE:-nand}"     # GT-BE19000 is NAND; only the GT-BE19000AI SKU is eMMC
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"          # WINUSER + WIN_ASUS_ROOT (override: export WINUSER)
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
