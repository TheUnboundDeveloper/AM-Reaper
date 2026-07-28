#!/bin/bash
# Reaper build launcher -- RT-BE96U (tri-band: 2.4/5/6 GHz)
# Flow:  git checkout be96u-only ; bump+commit version.conf ; build_be96u.sh [ship]
# NOTE: recent v1.8.x BE96U releases shipped MCP/nand only. Set VARIANTS/STORAGE
#       to whatever a given release should carry (full matrix is the default).
BRANCH=be96u-only
TARGET=rt-be96u
PREFIX=RT-BE96U
VARIANTS="MCP noMCP"
STORAGE="nand"     # RT-BE96U ships nand only (emmc is a build byproduct)
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "$HERE/_reaper_env.sh"          # WINUSER + WIN_ASUS_ROOT (override: export WINUSER)
SHIP_DIR="$WIN_ASUS_ROOT/asuswrt-merlin.ng/reaper-firmware"
source "$HERE/_reaper_build_lib.sh"
reaper_build "$@"
