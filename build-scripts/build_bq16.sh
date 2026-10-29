#!/bin/bash
# Reaper build launcher -- ZenWiFi BQ16 (non-Pro; quad-band 2.4/5/5/6 GHz, BCM4916 / 96813GW)
# Builds in the git WORKTREE /home/reaper/port/bq16 (canon stays on be96u-only).
# Flow:  (worktree on bq16) ; bump+commit version.conf there ; build_bq16.sh [ship]
#
# Onboarded 2026-10-01 from the ASUS GPL 102_39256 drop. Same silicon, profile
# and NAND layout as the RT-BE96U. Boards BQ16_2556 and BQ16_2556_2; Broadcom
# PHYs plus a BCM53134 switch, NO RTL8372 - so no u-boot switch blob and no
# uboot-rtl8372 overlay.
#
# BEFORE THE FIRST BUILD, one thing the tree cannot supply on its own:
#   bootloaders/obj.bq16/ (common/autoboot.o, net/tftp.o - the drop's u-boot
#   objects that differ from the baseline) is copied over u-boot-2019.07/ by hand.
#
# DONGLE FIRMWARE: bcmdrivers/.../dongle/sysdeps/BQ16/{6717a0,6726b0}/rtecdc.bin,
# taken from the vendor's own BQ16 image (102_39256), each Broadcom
# 17.10.369.39012 (r839077) - the host dhd driver's version - and each stamped
# "BQ16" (the 6726b0 also carries "BQ16.v2", the second board revision).
# reaper_verify 8c expects both chips; 8d checks the stamp.

case "${1:-}" in
  -h|--help) sed -n "2,4 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
export REAPER_TREE=/home/reaper/port/bq16
export REAPER_TDIR=$REAPER_TREE/release/src-rt-5.04behnd.4916/targets/96813GW
# COLD-TREE LIBTOOL PINS (same as build-scripts/ci/build_one.sh and build_gtbe19000.sh).
export lt_cv_sys_max_cmd_len="${lt_cv_sys_max_cmd_len:-1572864}"
_tc="$(ls -d /opt/toolchains/crosstools-arm_softfp-gcc-10.3*/usr/bin 2>/dev/null | head -1)"
[ -x "$_tc/arm-buildroot-linux-gnueabi-ld" ] && export lt_cv_path_LD="${lt_cv_path_LD:-$_tc/arm-buildroot-linux-gnueabi-ld}"
export lt_cv_prog_gnu_ld="${lt_cv_prog_gnu_ld:-yes}"
echo "libtool LD pin: lt_cv_path_LD=${lt_cv_path_LD:-<unset>} lt_cv_prog_gnu_ld=$lt_cv_prog_gnu_ld"
BRANCH=bq16
TARGET=bq16
PREFIX=BQ16
VARIANTS="${VARIANTS:-MCP noMCP}"
STORAGE="${STORAGE:-nand}"
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"          # WINUSER + WIN_ASUS_ROOT (override: export WINUSER)
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
