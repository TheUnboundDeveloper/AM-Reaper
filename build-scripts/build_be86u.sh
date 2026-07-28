#!/bin/bash
# Reaper build launcher -- RT-BE86U (dual-band: 2.4/5 GHz, NO 6 GHz)
# Flow:  git checkout rt-be86u ; bump+commit version.conf ; build_be86u.sh [ship]
BRANCH=rt-be86u
TARGET=rt-be86u
PREFIX=RT-BE86U
VARIANTS="MCP noMCP"
STORAGE="nand"      # RT-BE86U ships nand only (emmc is a build byproduct, never shipped)
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"          # WINUSER + WIN_ASUS_ROOT (override: export WINUSER)
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
