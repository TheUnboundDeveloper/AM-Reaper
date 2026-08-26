#!/bin/bash
# Reaper build launcher -- RT-BE88U (dual-band: 2.4/5 GHz, NO 6 GHz)
# Flow:  git checkout rt-be88u ; bump+commit version.conf ; build_be88u.sh [ship]

case "${1:-}" in
  -h|--help) sed -n "2,3 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
BRANCH=rt-be88u
TARGET=rt-be88u
PREFIX=RT-BE88U
VARIANTS="MCP noMCP"
STORAGE="nand"      # RT-BE88U ships nand only (emmc is a build byproduct, never shipped)
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"          # WINUSER + WIN_ASUS_ROOT (override: export WINUSER)
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
