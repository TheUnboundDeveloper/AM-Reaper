#!/bin/bash
# ============================================================================
# reaper_stale_configure.sh -- find (and clear) packages whose configure flags
# have been edited since the package was last configured.
# ----------------------------------------------------------------------------
# WHY THIS EXISTS (2026-08-09):
# router/Makefile guards every autotools package with
#       <pkg>/Makefile: <pkg>/configure
# Upstream tarballs carry an EPOCH mtime -- strongswan's configure is dated
# 2000-01-03 -- so once <pkg>/Makefile exists it is permanently newer and
# configure NEVER RE-RUNS, even after a patch changes its --enable/--disable
# flags. The change is then silently inert on a warm tree.
#
# Real case: commit 933373f773 "strongswan: sync build recipes with upstream -
# fixes missing exe" (2026-08-03) added --enable-stroke/aes/des/md5/sha1/sha2/
# hmac/gcm/fips-prf/curve25519. The tree had been configured 2026-07-21, so none
# of them were ever built. Every local build from 21 July onward -- all five
# models, v2.3.1 included -- shipped an IPSec stack missing usr/sbin/ipsec,
# usr/lib/ipsec/{starter,stroke} and the software crypto plugins. The pristine
# CI build produced them correctly; the defect was only visible by decomposing
# an image and diffing it against CI's.
#
# NO BUILD GATE CATCHES THIS. The build succeeds, reaper_verify passes 19/19,
# the image boots. Hence this check.
#
# USAGE:  reaper_stale_configure.sh [--check|--fix] [tree-root]
#   --check (default) report only, exit 1 if anything is stale
#   --fix             also remove <pkg>/Makefile + <pkg>/config.status so the
#                     next build re-runs configure with the current flags
# ============================================================================

case "${1:-}" in
  -h|--help) sed -n "2,30 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
set -u
MODE="${1:---check}"
ROOT="${2:-/home/reaper/asuswrt-be96u}"
R="$ROOT/release/src/router"

[ -d "$R" ] || { echo "stale-configure: no router tree at $R"; exit 0; }
cd "$ROOT" || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || { echo "stale-configure: $ROOT is not a git tree; skipping"; exit 0; }

found=0
for cs in "$R"/*/config.status; do
  [ -f "$cs" ] || continue
  d=$(dirname "$cs"); pkg=$(basename "$d")
  [ -f "$d/configure" ] || continue

  cs_epoch=$(stat -c%Y "$cs" 2>/dev/null) || continue
  # Last commit whose diff to router/Makefile mentions this package. -G matches
  # the diff text, so a rule edit for THIS package is what trips it.
  chg=$(git log -1 --format='%ct' -G"\b${pkg}\b" -- release/src/router/Makefile 2>/dev/null)
  [ -n "$chg" ] || continue
  [ "$chg" -gt "$cs_epoch" ] || continue

  found=$((found+1))
  subj=$(git log -1 --format='%h %s' -G"\b${pkg}\b" -- release/src/router/Makefile 2>/dev/null | cut -c1-88)
  echo "  [STALE] $pkg"
  echo "          configured $(date -d "@$cs_epoch" +%Y-%m-%d), rules changed $(date -d "@$chg" +%Y-%m-%d)"
  echo "          $subj"
  if [ "$MODE" = "--fix" ]; then
    rm -f "$d/Makefile" "$d/config.status"
    echo "          -> cleared Makefile + config.status; next build re-configures"
  fi
done

if [ "$found" -eq 0 ]; then
  echo "  stale-configure: clean (no package's flags changed after it was configured)"
  exit 0
fi
echo "  stale-configure: $found package(s) flagged"
[ "$MODE" = "--fix" ] && exit 0
echo "  run with --fix, or: rm -f <pkg>/Makefile <pkg>/config.status"
exit 1
