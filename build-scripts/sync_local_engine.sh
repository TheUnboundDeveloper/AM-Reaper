#!/bin/bash
# ============================================================================
# sync_local_engine.sh -- make the local build engine identical to this repo's
# ----------------------------------------------------------------------------
# Usage:  sync_local_engine.sh [--check] [--dest DIR]
#           --check   report drift and exit non-zero; change nothing
#           --dest    default /home/reaper/reaper_build
#
# WHY THIS EXISTS. There are two copies of the build engine: this repo's
# build-scripts/ (canonical, and the one CI runs) and the maintainer's local
# /home/reaper/reaper_build/. They diverged. On 2026-08-15 the divergence was
# caught in the act: v2.4.3 was built with the stale-configure and cold-tree
# guards present, and v2.4.4 -- the next day -- with neither, because the local
# copy was 162 lines against the canonical 265 and did not contain
# reaper_stale_configure.sh at all.
#
# That means a rung shipped without the guard whose entire job is stopping a
# configure-flag change from being silently inert -- the defect that shipped a
# broken IPSec stack for three weeks across all five models.
#
# A fix applied to one copy does not reach the other, so any build-system change
# must be followed by a sync, and any measurement taken across the two is
# meaningless. Run --check before trusting a local build to predict a CI one.
#
# Only the files the engine actually needs are synced. Local-only tooling
# (port_sibling_v2.sh, reaper_shlint.sh, build logs, backups) is left alone.
# ============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST=/home/reaper/reaper_build
CHECK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=1; shift;;
    --dest)  DEST="$2"; shift 2;;
    -h|--help) sed -n '2,25p' "$0"; exit 0;;
    *) echo "unknown argument '$1'"; exit 2;;
  esac
done

# The engine and everything it reaches for at runtime.
#
# _reaper_env.sh is REQUIRED, not optional: the repo's launchers source it to
# resolve WIN_ASUS_ROOT for SHIP_DIR. Omitting it from this list (first attempt,
# 2026-08-15) syncs launchers that immediately fail to source a file that does
# not exist locally, leaving SHIP_DIR as "/asuswrt-merlin.ng/reaper-firmware" --
# a bogus absolute path, and a silent one, because the launcher has no `set -u`
# at that point. If a file is added to a launcher's source chain, add it here.
FILES="_reaper_build_lib.sh _reaper_env.sh reaper_verify.sh reaper_stale_configure.sh
       reaper_langcheck.py reaper_csrfcheck.py reaper_static_checks.py
       verify_markers.txt _port_protect.sh gen_provenance.sh
       patch_count.sh check_symbols.sh check_ossl_consumers.sh openssl11-consumers.txt
       build_be96u.sh build_be86u.sh build_be88u.sh build_gtbe98.sh build_gtbe98pro.sh
       build_be92u.sh"

[ -d "$DEST" ] || { echo "ERROR: destination $DEST does not exist"; exit 1; }

drift=0; missing=0
echo "canonical: $HERE"
echo "local:     $DEST"
echo

for f in $FILES; do
  src="$HERE/$f"; dst="$DEST/$f"
  [ -f "$src" ] || { printf '  %-32s %s\n' "$f" "SKIP (not in repo)"; continue; }
  if [ ! -f "$dst" ]; then
    printf '  %-32s %s\n' "$f" "MISSING locally"
    missing=$((missing+1)); drift=$((drift+1))
  elif cmp -s "$src" "$dst"; then
    printf '  %-32s %s\n' "$f" "identical"
  else
    printf '  %-32s %s\n' "$f" "DIFFERS  (local $(wc -l < "$dst") lines vs canonical $(wc -l < "$src"))"
    drift=$((drift+1))
  fi
done

echo
if [ "$drift" -eq 0 ]; then
  echo "no drift -- the local engine matches this repo"
  exit 0
fi

if [ "$CHECK" = 1 ]; then
  echo "DRIFT: $drift file(s) differ or are missing ($missing missing)."
  echo "Run without --check to sync. Until then, a local build does NOT run the"
  echo "same engine as CI and cannot be used to predict it."
  exit 1
fi

# --- sync, with a timestamped backup of anything overwritten ----------------
BK="$DEST/.engine-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BK"
echo "backing up the current local copies to $BK"
for f in $FILES; do
  src="$HERE/$f"; dst="$DEST/$f"
  [ -f "$src" ] || continue
  [ -f "$dst" ] && cp -p "$dst" "$BK/"
  if cp "$src" "$dst" 2>/dev/null; then
    chmod +x "$dst" 2>/dev/null || true
    echo "  synced $f"
  else
    echo "  FAILED to write $dst -- check ownership (a previous root build can leave root-owned files here)"
    exit 1
  fi
done

echo
echo "verifying"
bad=0
for f in $FILES; do
  [ -f "$HERE/$f" ] || continue
  cmp -s "$HERE/$f" "$DEST/$f" || { echo "  MISMATCH after sync: $f"; bad=1; }
done
[ "$bad" = 0 ] && echo "  all synced files match the canonical copies" || exit 1
echo
echo "engine sha256: $(sha256sum "$DEST/_reaper_build_lib.sh" | cut -d' ' -f1)"
echo "This hash is printed in every build log's header, so the next log will show"
echo "which engine ran without anyone having to go looking."
