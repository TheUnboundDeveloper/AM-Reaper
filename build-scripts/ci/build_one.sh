#!/bin/bash
# ============================================================================
# build_one.sh -- CI launcher: ONE model, ONE variant, no ship.
# ----------------------------------------------------------------------------
# This is a thin launcher in exactly the shape _reaper_build_lib.sh documents
# (set BRANCH/TARGET/PREFIX/VARIANTS/STORAGE, then call reaper_build). It exists
# because the interactive launchers (build_be96u.sh et al) hardcode
# VARIANTS="MCP noMCP" and a Windows SHIP_DIR -- both wrong for CI, where each
# variant is its own job and nothing is shipped to a ladder.
#
# Everything else is IDENTICAL to a local build: same engine, same two-pass
# make, same noMCP flip, same reaper_verify gate. Do not fork the engine.
#
# Usage:  build_one.sh <MODEL> <MCP|noMCP>
# ============================================================================
set -u

MODEL="${1:?usage: build_one.sh <MODEL> <MCP|noMCP>}"
VARIANT="${2:?usage: build_one.sh <MODEL> <MCP|noMCP>}"

case "$VARIANT" in
  MCP|noMCP) ;;
  *) echo "FATAL: variant must be MCP or noMCP (got '$VARIANT')"; exit 2;;
esac

# Same model table as port_sibling_v2.sh / build-scripts/README.md.
case "$MODEL" in
  RT-BE96U)    BRANCH=be96u-only;  TARGET=rt-be96u;    PREFIX=RT-BE96U;;
  RT-BE86U)    BRANCH=rt-be86u;    TARGET=rt-be86u;    PREFIX=RT-BE86U;;
  RT-BE88U)    BRANCH=rt-be88u;    TARGET=rt-be88u;    PREFIX=RT-BE88U;;
  GT-BE98)     BRANCH=gt-be98;     TARGET=gt-be98;     PREFIX=GT-BE98;;
  GT-BE98_PRO) BRANCH=gt-be98-pro; TARGET=gt-be98_pro; PREFIX=GT-BE98_PRO;;
  *) echo "FATAL: unknown model '$MODEL'"; exit 2;;
esac

# All five models are buildable in CI. The published patches/ series reproduces
# the CANON tree (RT-BE96U); a sibling is that tree plus overlays/<MODEL>.patch
# (banner + animated header + the pages that reference them + target.mak), and
# for GT-BE98 also overlays/GT-BE98-platform.tar.gz (the platform tree the
# pinned upstream does not carry). container_build.sh applies those before this
# script runs; here we only sanity-check that the identity actually landed.
BANNER_DIR=/home/reaper/asuswrt-be96u/release/src/router/www/images
case "$MODEL" in
  RT-BE96U)    WANT_BANNER=RT-96U_REAPER_Header.png;;
  RT-BE86U)    WANT_BANNER=RT-BE86U_REAPER_Header.png;;
  RT-BE88U)    WANT_BANNER=RT-BE88U_REAPER_Header.png;;
  GT-BE98)     WANT_BANNER=GT-BE98_REAPER_Header.png;;
  GT-BE98_PRO) WANT_BANNER=GT-BE98P_REAPER_Header.png;;
esac
if [ ! -f "$BANNER_DIR/$WANT_BANNER" ]; then
  echo "FATAL: $MODEL identity overlay did not land -- $WANT_BANNER is not staged."
  echo "       Expected overlays/$MODEL.patch to have been applied."
  exit 3
fi
foreign=$(ls "$BANNER_DIR"/*_REAPER_Header.png 2>/dev/null | grep -v "/$WANT_BANNER\$" || true)
if [ -n "$foreign" ]; then
  echo "FATAL: a foreign model banner is present alongside $MODEL's:"
  echo "$foreign" | sed 's|.*/|       |'
  echo "       This is the v1.8.6 clobber signature -- refusing to build."
  exit 3
fi
echo "identity: $WANT_BANNER present, no foreign banner"

STORAGE="nand"          # all five models ship nand only; emmc is a byproduct
VARIANTS="$VARIANT"     # ONE variant per CI job (6-hour job ceiling)
unset SHIP_DIR          # no ladder in CI; reaper_build is called without 'ship'

HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# NOTE: _reaper_env.sh is deliberately NOT sourced -- it shells out to
# powershell.exe to resolve a Windows profile path, which is meaningless here.
source "$HERE/../_reaper_build_lib.sh"

echo "== CI build: $MODEL / $VARIANT (branch $BRANCH, target $TARGET) =="
reaper_build
