#!/bin/bash
# Reaper build launcher -- GT-BE98_PRO (quad-band)
# Flow:  git checkout gt-be98-pro ; bump+commit version.conf ; build_gtbe98pro.sh [ship]
# !! VERIFY BEFORE FIRST USE: historically BE98_PRO used a prebuild step
#    (~/_prebuild_be98pro.sh) and its make target resolved via the gt-% pattern
#    rule to `bin`. Confirm `make gt-be98_pro` is the correct target on this
#    branch (or run the prebuild first) before trusting an unattended build.
BRANCH=gt-be98-pro
TARGET=gt-be98_pro
PREFIX=GT-BE98_PRO
VARIANTS="MCP noMCP"
STORAGE="nand"     # nand only (emmc is a build byproduct, never shipped) — confirm vs prior BE98_PRO ship set
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"          # WINUSER + WIN_ASUS_ROOT (override: export WINUSER)
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
