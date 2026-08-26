#!/bin/bash
# Reaper build launcher -- GT-BE98 (quad-band: 2.4/5/5/6 GHz)
# Flow:  git checkout gt-be98 ; bump+commit version.conf ; build_gtbe98.sh [ship]

case "${1:-}" in
  -h|--help) sed -n "2,3 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
BRANCH=gt-be98
TARGET=gt-be98
PREFIX=GT-BE98
VARIANTS="MCP noMCP"
STORAGE="nand"     # GT-BE98 ships nand only (emmc is a build byproduct, never shipped)
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"          # WINUSER + WIN_ASUS_ROOT (override: export WINUSER)
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
