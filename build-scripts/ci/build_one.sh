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

# --- CI buildability gate ---------------------------------------------------
# The published patches/ series reproduces the CANON branch (be96u-only) only.
# Sibling models are separate branches produced by port_sibling_v2.sh from a
# clone that holds all five branches plus the out-of-tree identity art -- none
# of which exists in a clean-room CI checkout. Fail loudly rather than build
# something that merely looks like a sibling.
if [ "$MODEL" != "RT-BE96U" ]; then
  echo "FATAL: $MODEL cannot be built from the published patch series."
  echo "       patches/ reproduces be96u-only (RT-BE96U). Sibling models need"
  echo "       the per-model identity overlay + port_sibling_v2.sh against a"
  echo "       five-branch clone. See docs/CI-PUBLIC-BUILD.md ('Why one model')."
  exit 3
fi

STORAGE="nand"          # all five models ship nand only; emmc is a byproduct
VARIANTS="$VARIANT"     # ONE variant per CI job (6-hour job ceiling)
unset SHIP_DIR          # no ladder in CI; reaper_build is called without 'ship'

HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# NOTE: _reaper_env.sh is deliberately NOT sourced -- it shells out to
# powershell.exe to resolve a Windows profile path, which is meaningless here.
source "$HERE/../_reaper_build_lib.sh"

echo "== CI build: $MODEL / $VARIANT (branch $BRANCH, target $TARGET) =="
reaper_build
