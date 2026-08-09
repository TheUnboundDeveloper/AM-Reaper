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

# Capture pass 1 instead of discarding it. On a cold clean-room tree pass 1 is
# where the samba crypto chain gets built, so its output is the only record of
# how that chain went -- discarding it is why the first two clean-room failures
# could not be diagnosed from the job log. It goes to /tmp, NOT the job's stdout
# (pass 1 is expected to die at setprofile and its full output is hundreds of
# MB); an excerpt is copied into OUT_DIR below so it rides the evidence upload.
export REAPER_PASS1_LOG="${REAPER_PASS1_LOG:-/tmp/pass1_${MODEL}_${VARIANT}.log}"

# ---------------------------------------------------------------------------
# gmp shared-link failure (runs #1-#4). OBSERVED, not inferred: in CI libtool
# emitted NO link command for libgmp -- no `gcc -shared`, no linker-script
# fallback, not even the `rm -fr .libs/libgmp.lai` that precedes every healthy
# link in the same log -- then created .libs/libgmp.so.10{,.4.1} symlinks
# pointing at a file it never built, and exited 0. `make install` then failed
# with `cannot stat '.libs/libgmp.so.10.4.1'`.
#
# gmp is the longest link in the build (~700 objects, ~120-char paths), and it
# is the ONLY one that fails, so libtool's "command line too long" handling is
# the suspect branch. Which sub-branch it takes is fixed at configure time by
# max_cmd_len / file_list_spec / with_gnu_ld. Locally max_cmd_len=1572864 and
# the direct link is used; a forced-small value still links via a linker
# script. Both local paths work -- so pin CI to the known-good local value
# rather than let it probe its way into the branch that produces nothing.
#
# lt_cv_sys_max_cmd_len is an autoconf CACHE variable: configure honours it
# from the environment, so this needs no change to build-reaper.sh or any
# patch in the published series.
export lt_cv_sys_max_cmd_len="${lt_cv_sys_max_cmd_len:-1572864}"

# ROOT CAUSE (confirmed from the run-4 post-mortem, not inferred):
#   with_gnu_ld="no"   archive_cmds=""   build_libtool_libs=yes
# On Linux libtool only fills archive_cmds when it believes the linker is GNU
# ld. In the container its probe said "no", leaving archive_cmds EMPTY -- and
# link mode does `eval cmds=\"$archive_cmds\"` then loops over the result, so an
# empty list runs zero commands, prints nothing, and returns success. libtool
# then symlinks libgmp.so -> libgmp.so.10.4.1, a file it never built, and
# `make install` dies on the symlink target two steps later.
#
# The linker IS GNU ld: `ld -v` reports "GNU ld (GNU Binutils) 2.36.1". The
# probe is what is wrong. Locally the question never arises: build-reaper.sh
# skips the whole chain while staging/lib/libgnutls.so.30 exists, so the
# maintainer's libtool was generated once in a clean environment and reused
# ever since. CI re-configures every run, under the vendor make environment.
#
# lt_cv_path_LD / lt_cv_prog_gnu_ld are the cache variables behind that probe.
# Pinning them states something true of every linker in this build (target and
# host are both GNU binutils), so it is safe to set globally.
_tc="$(ls -d /opt/toolchains/crosstools-arm_softfp-gcc-10.3*/usr/bin 2>/dev/null | head -1)"
if [ -x "$_tc/arm-buildroot-linux-gnueabi-ld" ]; then
  export lt_cv_path_LD="${lt_cv_path_LD:-$_tc/arm-buildroot-linux-gnueabi-ld}"
fi
export lt_cv_prog_gnu_ld="${lt_cv_prog_gnu_ld:-yes}"
echo "libtool LD pin: lt_cv_path_LD=${lt_cv_path_LD:-<unset>} lt_cv_prog_gnu_ld=$lt_cv_prog_gnu_ld"

HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# NOTE: _reaper_env.sh is deliberately NOT sourced -- it shells out to
# powershell.exe to resolve a Windows profile path, which is meaningless here.
source "$HERE/../_reaper_build_lib.sh"

echo "== CI build: $MODEL / $VARIANT (branch $BRANCH, target $TARGET) =="
reaper_build
rc=$?

# Preserve the pass-1 evidence whether or not the build passed: a build that
# succeeds still tells us what a healthy cold-tree crypto chain looks like,
# which is the baseline a future failure gets compared against. Excerpt only --
# the full log is far too large for an artifact.
if [ -n "${OUT_DIR:-}" ] && [ -f "$REAPER_PASS1_LOG" ]; then
  EX="$OUT_DIR/pass1-crypto-${MODEL}-${VARIANT}.log"
  {
    echo "### pass1 crypto-chain excerpt -- $MODEL/$VARIANT (rc=$rc)"
    echo "### full pass1 log was $(wc -c <"$REAPER_PASS1_LOG") bytes"
    echo
    grep -nE '\[build-reaper\]|libgmp|libgnutls|libnettle|mode=link|gcc -shared|cannot stat|Error [0-9]+|No such file' \
      "$REAPER_PASS1_LOG" 2>/dev/null | head -400
    echo
    echo "### last 200 lines of pass1"
    tail -200 "$REAPER_PASS1_LOG"
  } > "$EX" 2>/dev/null || true
  echo "pass1 excerpt -> $(basename "$EX")"
fi
exit $rc
