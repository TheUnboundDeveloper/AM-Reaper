#!/bin/bash
# cut_fleet.sh - every step of a release rung that CAN ONLY be done locally,
# in one command, in the right order.
#
#   ./build-scripts/cut_fleet.sh --version v2.3.4
#
# The split this script encodes: CI can verify anything derivable from the
# PUBLISHED inputs (patch series + overlays), but it cannot PRODUCE them - the
# canon tree and the four sibling branches live only in the private WSL clone
# and the bare hub. So everything here needs firmware source; everything CI does
# needs none. That is the whole reason this file exists.
#
# Order matters and is not negotiable:
#   1. cut the rung        patches + provenance + CI pin + hygiene (cut_rung.sh)
#   2. port the siblings   canon's shared code onto the 4 branches
#   3. THEN the overlays   regenerate/verify - doing this BEFORE step 2 writes an
#                          overlay that REVERTS the rung on every sibling, which
#                          is the 2026-08-10 regression, and it applies cleanly
#                          so nothing downstream would catch it.
#
# Commits on the sibling branches (that is what a port is). Never commits in the
# lean repo and NEVER pushes anything, anywhere.
set -uo pipefail

CANON_DIR=${REAPER_CLONE:-/home/reaper/asuswrt-be96u}
LEAN=${REAPER_LEAN:-/mnt/c/Users/natha/AppData/Roaming/VSC/ASUS/ASUS-Merlin-Reaper}
PORTDIR=${REAPER_PORTDIR:-/home/reaper/port}
CANON=be96u-only
MODELS="RT-BE86U:rt-be86u RT-BE88U:rt-be88u GT-BE98:gt-be98 GT-BE98_PRO:gt-be98-pro RT-BE92U:rt-be92u"

VERSION=""; DO_CUT=1; DO_PORT=1; DO_OVERLAY=1
while [ $# -gt 0 ]; do
  case "$1" in
    --version)     VERSION="$2"; shift 2 ;;
    --skip-cut)    DO_CUT=0; shift ;;
    --skip-port)   DO_PORT=0; shift ;;
    --skip-overlay) DO_OVERLAY=0; shift ;;
    -h|--help)     sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$VERSION" ] || { echo "FAIL: --version vX.Y.Z is required" >&2; exit 2; }
EXTEND="Reaper_$VERSION"

die()  { echo; echo "FAIL: $*" >&2; exit 1; }
head1() { echo; echo "=============================================================="; echo " $*"; echo "=============================================================="; }
step() { echo; echo "-- $* --"; }

# ============================================================ 0. preflight ====
head1 "0. preflight"
[ -d "$CANON_DIR/.git" ] || die "no canon clone at $CANON_DIR"
[ -d "$LEAN/patches" ]   || die "no lean repo at $LEAN"
cur=$(git -C "$CANON_DIR" rev-parse --abbrev-ref HEAD)
[ "$cur" = "$CANON" ] || die "canon is on '$cur', expected '$CANON'"
[ "$(git -C "$CANON_DIR" status --short --untracked-files=no | wc -l)" -eq 0 ] \
  || die "canon has uncommitted tracked changes - commit the rung first"
got=$(sed -n 's/^EXTENDNO=//p' "$CANON_DIR/release/src-rt/version.conf")
[ "$got" = "$EXTEND" ] || die "version.conf says $got but you asked for $EXTEND"
echo "  canon   $(git -C "$CANON_DIR" rev-parse --short=10 HEAD) ($CANON), clean"
echo "  version $EXTEND"

# The lean repo lives on a Windows mount; a stray read-only attribute makes
# cut_rung's `sed -i` pin step fail to write. Say so rather than let the pin
# silently stay at the previous version.
if [ ! -w "$LEAN/.github/workflows/public-build.yml" ]; then
  die "public-build.yml is not writable (read-only attribute?) - the EXPECTED_VERSION pin would silently not apply"
fi

# ============================================================ 1. cut rung =====
if [ "$DO_CUT" = 1 ]; then
  head1 "1. cut the rung"
  bash "$LEAN/build-scripts/cut_rung.sh" --version "$VERSION" || die "cut_rung.sh failed"
else
  echo; echo "(1. cut the rung - SKIPPED)"
fi

# ============================================================ 2. port =========
if [ "$DO_PORT" = 1 ]; then
  head1 "2. port the rung onto the four sibling branches"

  step "refresh the hub refs"
  git -C "$CANON_DIR" fetch hub --prune || die "cannot fetch hub"

  for pair in $MODELS; do
    M=${pair%%:*}; B=${pair##*:}; W=$PORTDIR/$B
    step "$M ($B)"

    # Canon carries STALE local copies of every sibling branch, frozen at clone
    # time. Reading one of those is what generated v2.1.4-era overlays in Aug
    # 2026. hub/<branch> is the only truth; move the local ref onto it, but only
    # after proving the local is an ancestor so the force-move loses nothing.
    if ! git -C "$CANON_DIR" rev-parse --verify -q "hub/$B" >/dev/null; then
      # A model not yet pushed to the hub (e.g. the experimental RT-BE92U): there
      # is no hub tip to reconcile against, so keep the local branch as-is. The
      # owner pushes it to the hub when it graduates; until then the local branch
      # IS the source of truth for it. (If neither the hub nor a local branch
      # exists, the worktree assertion below fails loudly, which is correct.)
      echo "  NOTE: hub has no $B yet - keeping the local branch (not yet pushed to the hub)"
    elif git -C "$CANON_DIR" rev-parse --verify -q "$B" >/dev/null; then
      if git -C "$CANON_DIR" merge-base --is-ancestor "$B" "hub/$B"; then
        # local is behind (or equal): the stale-clone case - take the hub tip
        git -C "$CANON_DIR" branch -f "$B" "hub/$B" || die "cannot move $B onto hub/$B"
      elif git -C "$CANON_DIR" merge-base --is-ancestor "hub/$B" "$B"; then
        # local is AHEAD and contains the hub tip: a previous rung was ported but
        # not yet pushed to the hub. Keeping the local tip is the only correct
        # move - resetting to the hub would silently discard that port. Warn,
        # because the hub is meant to be the source of truth.
        ahead=$(git -C "$CANON_DIR" rev-list --count "hub/$B..$B")
        echo "  NOTE: $B is $ahead commit(s) AHEAD of hub/$B (unpushed port) - keeping the local tip"
      else
        die "$B and hub/$B have DIVERGED - neither contains the other; resolve by hand"
      fi
    else
      git -C "$CANON_DIR" branch -f "$B" "hub/$B" || die "cannot create $B from hub/$B"
    fi

    [ -d "$W" ] || git -C "$CANON_DIR" worktree add "$W" "$B" >/dev/null 2>&1 \
      || die "cannot create worktree for $B"
    [ "$(git -C "$W" rev-parse --abbrev-ref HEAD)" = "$B" ] || die "worktree $W is not on $B"

    # --- the port itself ---
    REAPER_TREE="$W" bash "$LEAN/build-scripts/port_sibling_v2.sh" "$M" --commit --version "$EXTEND" \
      || die "port_sibling_v2 failed for $M (guards abort BEFORE committing; inspect $W)"

    # --- dictionaries ---
    # _port_protect classifies *.dict PROTECTED. Correct for a same-version port;
    # across a version JUMP it means the sibling ships raw <#TOKEN#> on new pages
    # and English where canon now has translations. Copy them - but only after
    # proving the copy is additive.
    step "$M dictionaries"
    unsafe=0
    # Enumerate from the TREE, not an on-disk glob: www/ carries a gitignored
    # temp.dict scratch file, and globbing the working directory drags it in -
    # `git show <branch>:...temp.dict` then prints a fatal for every model.
    # Keys canon DELETED since this sibling last synced are an INTENTIONAL
    # fleet-wide removal (a feature dropped from the firmware), not sibling
    # data: the sibling has just taken canon's pages in the port above, so a
    # token canon no longer defines is a token nothing references any more.
    # Blocking on those would make it impossible to ever delete a dict key.
    # A key the sibling has that canon NEVER had is the real hazard (model
    # identity / a translation only that branch carries) and still blocks.
    MB=$(git -C "$CANON_DIR" merge-base "$CANON" "$B" 2>/dev/null)
    while IFS= read -r d; do
      [ -n "$d" ] || continue
      git -C "$CANON_DIR" show "$CANON:$d" | sed -n 's/^\([A-Za-z0-9_]*\)=.*/\1/p' | sort -u > /tmp/cf_kc
      git -C "$CANON_DIR" show "$B:$d" 2>/dev/null | sed -n 's/^\([A-Za-z0-9_]*\)=.*/\1/p' | sort -u > /tmp/cf_ks
      : > /tmp/cf_kr
      if [ -n "$MB" ]; then
        git -C "$CANON_DIR" show "$MB:$d" 2>/dev/null \
          | sed -n 's/^\([A-Za-z0-9_]*\)=.*/\1/p' | sort -u > /tmp/cf_kmb
        comm -23 /tmp/cf_kmb /tmp/cf_kc > /tmp/cf_kr   # deleted from canon since the sibling synced
      fi
      if [ -s /tmp/cf_ks ]; then
        comm -13 /tmp/cf_kc /tmp/cf_ks > /tmp/cf_so    # sibling-only
        real=$(comm -23 /tmp/cf_so /tmp/cf_kr)         # minus the intentional deletions
        if [ -n "$real" ]; then
          echo "    $d: sibling-only key(s) canon never had: $(printf '%s' "$real" | tr '\n' ' ')"
          unsafe=1
        fi
      fi
      # a differing sibling value naming a model would be model identity
      if git -C "$CANON_DIR" diff "$CANON" "$B" -- "$d" | grep -E '^\+' | grep -vE '^\+\+\+' \
         | grep -qE 'RT-BE96U|RT-BE86U|RT-BE88U|GT-BE98'; then
        echo "    $d: a sibling-side differing value carries a model name"
        unsafe=1
      fi
    done < <(git -C "$CANON_DIR" ls-tree --name-only "$CANON" release/src/router/www/ | grep '\.dict$')
    [ "$unsafe" = 0 ] || die "dict copy for $B is NOT additive-safe - inspect before proceeding"

    # quoted so the shell cannot pre-expand it against the worktree (same
    # temp.dict trap: an expanded glob makes git checkout fatal on a path that
    # exists on disk but not in the tree)
    git -C "$W" checkout "$CANON" -- 'release/src/router/www/*.dict' || die "dict checkout failed for $B"
    if git -C "$W" diff --cached --quiet; then
      echo "    dicts already in sync"
    else
      n=$(git -C "$W" diff --cached --name-only | wc -l)
      git -C "$W" commit -q -m "$B: sync language dicts from $CANON (version-jump port)

port_sibling_v2 protects *.dict, which is right for a same-version port and
wrong across a version jump: this branch would otherwise ship raw <#TOKEN#>
placeholders on the rung's new pages and English text in 24 languages.

Verified additive-safe before copying: no key exists in a sibling dict that
canon lacks, and no sibling-side differing value carries model identity.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>" \
        || die "dict commit failed for $B"
      echo "    committed $n dict file(s)"
    fi

    # From the TREE, not an on-disk glob: www/ carries a gitignored temp.dict
    # scratch file (0 lines) and globbing the working directory counts it, which
    # reports a false "not in lockstep" on an otherwise perfect port.
    lc=$(git -C "$W" ls-tree --name-only HEAD release/src/router/www/ | grep '\.dict$' \
         | while IFS= read -r _d; do git -C "$W" show "HEAD:$_d" | wc -l; done | sort -u | wc -l)
    [ "$lc" = 1 ] || die "$B dicts are NOT in lockstep ($lc distinct line counts)"
    echo "    $B -> $(git -C "$W" rev-parse --short HEAD), dicts lockstep, EXTENDNO=$(sed -n 's/^EXTENDNO=//p' "$W/release/src-rt/version.conf")"
  done
else
  echo; echo "(2. port - SKIPPED)"
fi

# ============================================================ 3. overlays =====
if [ "$DO_OVERLAY" = 1 ]; then
  head1 "3. overlays"

  # Regenerate ONLY where the result actually differs. An overlay is normally
  # unchanged by a rung: once the siblings are ported, diff(canon, sibling) is
  # back to pure identity. Rewriting a ~4 MB patch to change only its `index`
  # blob hashes - which `git apply` never reads, since CI does not use --3way -
  # would add megabytes of blobs to the repo for no behavioural difference.
  for pair in $MODELS; do
    M=${pair%%:*}; B=${pair##*:}
    OV="$LEAN/overlays/$M.patch"
    [ -f "$OV" ] || { echo "  $M: no overlay, skipping"; continue; }

    # Restrict to the overlay's own file set. Unrestricted, the diff drags in
    # committed build byproducts and (for GT-BE98) collides with the separately
    # shipped platform archive. Take paths from the `diff --git` headers: a
    # --binary hunk (every banner PNG) has no ---/+++ pair to read.
    fs=$(mktemp); new=$(mktemp)
    sed -n 's|^diff --git a/\(.*\) b/\1$|\1|p' "$OV" | sort -u > "$fs"
    want=$(grep '^diff --git' "$OV" | sed 's|^diff --git a/||; s| b/.*$||' | sort -u | wc -l)
    [ "$(wc -l < "$fs")" = "$want" ] || die "cannot parse every path out of $M.patch"

    git -C "$CANON_DIR" diff --binary "$CANON" "$B" -- $(tr '\n' ' ' < "$fs") > "$new"

    if cmp -s "$OV" "$new"; then
      echo "  $M: unchanged"
    else
      # ignore a pure index-hash churn; report anything else
      d=$(diff "$OV" "$new" | grep '^[<>]' | grep -vc '^[<>] index ')
      if [ "$d" -eq 0 ]; then
        echo "  $M: only blob-hash (index) lines differ - NOT rewriting (git apply never reads them)"
      else
        cp "$new" "$OV" && echo "  $M: REGENERATED ($d substantive line(s) changed)"
      fi
    fi
    rm -f "$fs" "$new"
  done

  step "overlay identity gate (the same check CI runs)"
  python3 "$LEAN/build-scripts/ci/check_overlays.py" "$LEAN/overlays" \
    || die "overlay identity gate FAILED - an overlay carries shared code, not identity"
fi

# ============================================================ summary =========
cat <<EOF

==============================================================
 RUNG $VERSION - local work complete. Nothing committed in the
 lean repo, nothing pushed anywhere.
==============================================================
 STILL YOURS TO DO (none of it automatable)
   1. prose: provenance summary + models_note, and the
      docs/CHANGELOG.md section - the release notes are
      extracted from it, so a missing section ships as
      missing notes.
   2. review:  git -C "$LEAN" diff   (+ 'git status' for the new patches)
   3. commit the lean repo, push Dev to dry-run, then main.
   4. push canon + the four ported branches to the hub - they
      exist only in $CANON_DIR until you do.
   5. on-metal validation. Nothing above proves a router boots.

 The overlay gate now also runs in CI before the build matrix,
 so a bad overlay fails in seconds instead of after 10 builds.
EOF
