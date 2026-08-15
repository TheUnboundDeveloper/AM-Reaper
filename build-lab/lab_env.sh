#!/bin/bash
# ============================================================================
# lab_env.sh -- path resolution + the safety assertions every lab run must pass
# ----------------------------------------------------------------------------
# Sourced by lab_build.sh and ab_compare.sh. Defines nothing that changes how a
# build behaves; it only decides WHERE things go and refuses to start when the
# preconditions for a trustworthy measurement are not met.
#
# The refusals are not defensive padding. Each one corresponds to a way a lab
# run has a known route to either (a) producing a number that means nothing, or
# (b) leaving the shared tree in a state that damages the NEXT real build.
# ============================================================================
set -u

# --- where things live -------------------------------------------------------
# REAPER_TREE follows the convention port_sibling_v2.sh already uses, so a
# worktree can be measured without editing anything.
LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$LAB_DIR/.." && pwd)"
R="${REAPER_TREE:-/home/reaper/asuswrt-be96u}"
P="$R/release/src-rt-5.04behnd.4916"
TDIR="$P/targets/96813GW"
RESULTS_ROOT="$LAB_DIR/RESULTS"
export LAB_DIR REPO_DIR R P TDIR RESULTS_ROOT

# reaper_verify: prefer the lean-repo copy (the canonical one) over the local
# fork at /home/reaper/reaper_build/. The lab deliberately does not depend on
# the local copy, because the two have diverged and which one answers is exactly
# the ambiguity this directory exists to remove.
LAB_VERIFY="${LAB_VERIFY:-$REPO_DIR/build-scripts/reaper_verify.sh}"
export LAB_VERIFY

lab_hr() { echo "------------------------------------------------------------"; }
lab_die() { echo "LAB ABORT: $*" >&2; exit 9; }
lab_say() { echo "[lab] $*"; }

# ============================================================================
# Preconditions
# ============================================================================
lab_preflight() {
  local rc=0

  # 1. Not root. The vendor's build/prebuild_checks.mk refuses a root build ~40s
  #    in, but only AFTER writing config and staging files -- a 2026-08-13 run
  #    left 528 root-owned files in a tree that had none. Catch it in advance.
  #    Note `wsl -d Ubuntu-20.04 -- ...` with no -u IS root on this box.
  if [ "$(id -u)" = 0 ]; then
    echo "  [FAIL] running as root -- relaunch with: wsl -d Ubuntu-20.04 -u reaper bash <script>"
    rc=1
  else
    echo "  [ok]   user $(id -un) (uid $(id -u))"
  fi

  # 2. /bin/sh must be bash. It reverts to dash between sessions; observed.
  #    usr-merge means it resolves to /usr/bin/bash, so test the suffix.
  local sh; sh="$(readlink -f /bin/sh)"
  case "$sh" in
    */bash) echo "  [ok]   /bin/sh -> $sh";;
    *) echo "  [FAIL] /bin/sh -> $sh (must be bash; fix as root: ln -sf bash /bin/sh)"; rc=1;;
  esac

  # 3. The tree exists and is the shape we expect.
  [ -d "$P" ] || { echo "  [FAIL] no platform tree at $P"; rc=1; }
  [ -d "$R/.git" ] || { echo "  [FAIL] $R is not a git checkout"; rc=1; }
  [ -d "$P" ] && [ -d "$R/.git" ] && echo "  [ok]   tree $R ($(git -C "$R" rev-parse --abbrev-ref HEAD) @ $(git -C "$R" rev-parse --short HEAD))"

  # 4. No build already running against this tree. Two concurrent makes in one
  #    tree do not just contend -- they interleave writes into the same staging
  #    dirs, and the result is an image with an indeterminate mixture that still
  #    passes the verify gate. Also catches "I forgot the last run was going".
  if pgrep -af "make .*(rt-be9|gt-be9)" >/dev/null 2>&1; then
    echo "  [FAIL] a build is already running against this tree:"
    pgrep -af "make .*(rt-be9|gt-be9)" | sed 's/^/         /'
    rc=1
  else
    echo "  [ok]   no build in flight"
  fi

  # 5. The lab never ships. An inherited SHIP_DIR is refused rather than unset,
  #    because a caller that set it wanted something this harness will not do.
  if [ -n "${SHIP_DIR:-}" ]; then
    echo "  [FAIL] SHIP_DIR is set ('$SHIP_DIR') -- the lab never ships. Unset it."
    rc=1
  else
    echo "  [ok]   SHIP_DIR unset (lab cannot reach the ladder)"
  fi

  # 6. The two flip-targets must be clean BEFORE we start. If a previous build
  #    was killed mid-noMCP they are still flipped, and every timing and image
  #    from this run would describe a build we did not think we were running.
  lab_assert_flip_clean "pre-flight" || rc=1

  # 7. Enough disk for another image set.
  local free_g; free_g=$(df -BG --output=avail "$P" 2>/dev/null | tail -1 | tr -dc '0-9')
  if [ -n "$free_g" ] && [ "$free_g" -lt 15 ]; then
    echo "  [FAIL] only ${free_g}G free on the build volume -- need ~15G headroom"
    rc=1
  else
    echo "  [ok]   ${free_g:-?}G free on the build volume"
  fi

  # 8. verify script reachable (a lab run without the QA gate proves less).
  if [ -f "$LAB_VERIFY" ]; then echo "  [ok]   reaper_verify: $LAB_VERIFY"
  else echo "  [WARN] reaper_verify not found at $LAB_VERIFY -- runs will skip the QA gate"; fi

  return $rc
}

# ============================================================================
# The noMCP flip guard
# ----------------------------------------------------------------------------
# config_base and version.conf are the two files the noMCP flip edits. The live
# engine restores them only at the very end of a successful run, so an abort
# leaves the tree flipped and the NEXT build silently produces a noMCP image
# stamped _noMCP while believing it built MCP. The lab restores on every exit
# path and re-asserts afterwards.
# ============================================================================
LAB_FLIP_FILES="release/src/router/config_base release/src-rt/version.conf"

lab_assert_flip_clean() {   # $1 = context label
  local ctx="${1:-check}" dirty
  dirty="$(git -C "$R" status --porcelain -- $LAB_FLIP_FILES 2>/dev/null)"
  if [ -n "$dirty" ]; then
    echo "  [FAIL] ($ctx) flip targets are modified -- a previous build was probably killed mid-noMCP:"
    echo "$dirty" | sed 's/^/         /'
    echo "         recover with: git -C $R checkout -- $LAB_FLIP_FILES"
    return 1
  fi
  echo "  [ok]   ($ctx) config_base + version.conf clean"
  return 0
}

lab_restore_flip() {
  git -C "$R" checkout -- $LAB_FLIP_FILES 2>/dev/null || true
}

# Installed by lab_build.sh. Restores the flip on ANY exit, including SIGINT.
lab_install_trap() {
  trap 'rc=$?; lab_restore_flip; [ $rc -ne 0 ] && echo "[lab] exited rc=$rc -- flip targets restored"; exit $rc' EXIT
  trap 'echo; echo "[lab] interrupted -- restoring flip targets"; lab_restore_flip; exit 130' INT TERM
}

# ============================================================================
# Version / naming
# ============================================================================
lab_read_version() {
  grep -oE 'Reaper_v[0-9]+\.[0-9]+(\.[0-9]+)?[a-z]?' "$R/release/src-rt/version.conf" | head -1
}

# Image path for a model+variant+version, matching what the engine produces.
lab_image_path() {   # $1=PREFIX $2=VARIANT $3=VER
  local tag=""; [ "$2" = "noMCP" ] && tag="_noMCP"
  echo "$TDIR/${1}_3006_102.8_${3}${tag}_nand_squashfs.pkgtb"
}

# Model table -- the single source of truth, same as ci/build_one.sh.
lab_model_table() {   # $1 = MODEL ; sets BRANCH TARGET PREFIX
  case "$1" in
    RT-BE96U)    BRANCH=be96u-only;  TARGET=rt-be96u;    PREFIX=RT-BE96U;;
    RT-BE86U)    BRANCH=rt-be86u;    TARGET=rt-be86u;    PREFIX=RT-BE86U;;
    RT-BE88U)    BRANCH=rt-be88u;    TARGET=rt-be88u;    PREFIX=RT-BE88U;;
    GT-BE98)     BRANCH=gt-be98;     TARGET=gt-be98;     PREFIX=GT-BE98;;
    GT-BE98_PRO) BRANCH=gt-be98-pro; TARGET=gt-be98_pro; PREFIX=GT-BE98_PRO;;
    *) lab_die "unknown model '$1'";;
  esac
  export BRANCH TARGET PREFIX
}
