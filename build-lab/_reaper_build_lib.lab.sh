#!/bin/bash
# ============================================================================
# _reaper_build_lib.lab.sh -- EXPERIMENTAL build engine (build-lab only)
# ----------------------------------------------------------------------------
# Derived from build-scripts/_reaper_build_lib.sh (the canonical / CI copy) at
# the state recorded in RESULTS/BASELINE.txt. Every proposed change is behind a
# flag whose DEFAULT REPRODUCES THE CANONICAL ENGINE EXACTLY.
#
# That default matters more than the experiments. The A arm of every comparison
# is this file with no flags set, so if the default drifts from the canonical
# engine, every measurement in RESULTS/ is comparing two candidates rather than
# a candidate against the truth.
#
#   LAB_SINGLE_PASS  off | auto | force     (default off  -> two passes, as today)
#   LAB_CONFIG_KEEP  0 | 1                  (default 0    -> unconditional rm, as today)
#   LAB_VARIANTS     "MCP" | "MCP noMCP"    (default "MCP noMCP", as today)
#   REAPER_JOBS      integer                (default 1    -- DO NOT RAISE, see below)
#
# Differences from the canonical engine that are NOT flagged, because they are
# instrumentation or safety and cannot change what gets built:
#   - [lab-timing] lines around each phase
#   - logs go to the lab RESULTS dir, never /home/reaper/build_*.log
#   - no ship step exists at all
#   - the flip is restored on every exit path (canonical restores only at the end)
# ============================================================================
set -u

# R / P / TDIR / LAB_VERIFY come from lab_env.sh, which must be sourced first.
: "${R:?lab_env.sh must be sourced before this file}"
: "${P:?}" "${TDIR:?}"

# --- REAPER_JOBS ------------------------------------------------------------
# DEFAULT 1 - PROVEN REQUIRED, and not an experiment in this lab.
# The vendor's top-level targets have NO dependency ordering: clean-build's
# `rm -rf fs.build` races component installs, and fsbuild races the fs.install
# skeleton. They are sequenced only by serial execution. A -j8 attempt failed
# deterministically and the gate caught it -- but that is luck, not design.
# Low -j values are MORE dangerous than high ones: they make the race
# intermittent, and its output is a silently-wrong image that passes verify.
# Compile is not the warm-tree bottleneck anyway (391 cross-gcc invocations per
# pass against 2508 directory traversals), so there is nothing here to win.
: "${REAPER_JOBS:=1}"
: "${LAB_SINGLE_PASS:=off}"
: "${LAB_CONFIG_KEEP:=0}"

# ---------------------------------------------------------------------------
# Instrumentation. Machine-readable, parsed by ab_compare.sh -- keep the shape.
# ---------------------------------------------------------------------------
_lab_t0=0
_lab_phase_start() { _lab_t0=$(date +%s); }
_lab_phase_end() {   # $1=variant $2=phase $3=rc [$4=extra k=v]
  local secs=$(( $(date +%s) - _lab_t0 ))
  echo "[lab-timing] variant=$1 phase=$2 seconds=$secs rc=$3 ${4:-}"
}

# ============================================================================
# One variant
# ============================================================================
_rb_variant() {   # $1 = MCP|noMCP
  local label="$1"

  # --- stale-configure guard (canonical behaviour, unchanged) --------------
  # `<pkg>/Makefile: <pkg>/configure` never re-fires on a warm tree because
  # tarball configure scripts carry an epoch mtime, so a patch that changes
  # --enable/--disable flags is silently inert. strongswan shipped that way for
  # three weeks across all five models before a CI-vs-local image diff caught
  # it. This runs in the lab for the same reason it runs in CI: a measurement
  # taken without it is a measurement of a build that may be quietly wrong.
  local _sc="$REPO_DIR/build-scripts/reaper_stale_configure.sh"
  if [ -f "$_sc" ]; then
    echo "=== [$label] stale-configure guard ==="
    _lab_phase_start
    bash "$_sc" --fix "$R" || true
    _lab_phase_end "$label" staleconfigure 0
  fi

  cd "$P" || return 9

  # --- config invalidation -------------------------------------------------
  # CANONICAL: delete .config, the generated model profile and the zlib stamp
  # unconditionally, every variant. Its stated purpose is protecting against a
  # stale profile from a DIFFERENT model (MODEL NAME MISMATCH).
  # EXPERIMENT (LAB_CONFIG_KEEP=1): do that only when the profile is absent or
  # names another model, which is the same protection stated precisely.
  local _prof="$R/release/src/router/config_${TARGET}"
  local _keep=0

  # WHICH FILE CARRIES THE MODEL IDENTITY -- checked, not assumed (2026-08-15).
  # The first version of this predicate grepped config_<target> for the target
  # string. That file contains NO model identifier at all: it is 839 lines of
  # RTCONFIG_ flags, and its model is encoded in the FILENAME, which cannot be
  # stale by construction. The predicate would never have fired and the session
  # would have measured nothing.
  #
  # The stale-model risk lives in `.config`, which is NOT model-named and IS
  # rewritten per build -- it carries `export BUILD_NAME=RT-BE96U`. A leftover
  # .config from a different model is precisely what produces MODEL NAME
  # MISMATCH, so that is the thing to test.
  if [ "$LAB_CONFIG_KEEP" = "1" ] && [ -f "$_prof" ] && [ -f "$P/.config" ] \
     && grep -qE "^export BUILD_NAME=${PREFIX}[[:space:]]*$" "$P/.config"; then
    _keep=1
  fi

  # The zlib stamp is deleted on BOTH arms unconditionally. It guards a
  # different failure (a stale stamp-h1 skips zlib's configure and leaves the
  # committed stub Makefile in place, which dies with "No rule to make target
  # 'install'"). Bundling it into the config-keep branch would make this a
  # two-variable experiment.
  rm -f "$R"/release/src/router/zlib/stamp-h1

  if [ "$_keep" = 1 ]; then
    echo "[$label] config-keep: .config already declares BUILD_NAME=$PREFIX -- keeping it, no forced regen"
  else
    rm -f .config "$_prof"
    if [ "$LAB_CONFIG_KEEP" = "1" ]; then
      echo "[$label] config-keep: armed but .config is absent or names another model -- regen FORCED (guard working)"
    fi
  fi

  # --- pass 1 --------------------------------------------------------------
  local _p1start _p1rc
  _p1start=$(date +%s)
  echo "=== [$label] make $TARGET pass1 (-j${REAPER_JOBS}) $(date) ==="
  _lab_phase_start
  if [ -n "${REAPER_PASS1_LOG:-}" ]; then
    nice make "$TARGET" FORCE=1 -j"${REAPER_JOBS}" >"$REAPER_PASS1_LOG" 2>&1; _p1rc=$?
  else
    nice make "$TARGET" FORCE=1 -j"${REAPER_JOBS}" >/dev/null 2>&1; _p1rc=$?
  fi
  _lab_phase_end "$label" pass1 "$_p1rc"
  echo "[$label] pass1_exit=$_p1rc"

  # --- cold-tree guard (canonical behaviour, unchanged) --------------------
  # samba-4.15.13/build/ is gitignored, so a fresh clone has no crypto chain.
  # Pass 1 legitimately dies at setprofile on such a tree, leaving gmp
  # half-built; pass 2 then re-extracts on top and `make install` copies a
  # .so that was never linked. Reports on every path, including "not needed" --
  # a guard that is silent when it decides to do nothing is indistinguishable
  # in a log from a guard that never ran.
  local _sam="$R/release/src/router/samba-4.15.13"
  if [ ! -d "$_sam/build" ]; then
    echo "[$label] cold-tree guard: no samba build/ after pass1 -- pass2 builds the crypto chain from scratch"
  elif [ ! -e "$_sam/build/staging/lib/libgnutls.so.30" ]; then
    echo "[$label] cold-tree guard: FIRED -- chain incomplete after pass1; clearing build/"
    rm -rf "$_sam/build" "$_sam/.reaper-built"
  else
    echo "[$label] cold-tree guard: not needed -- crypto chain complete after pass1"
  fi

  # --- pass 2, or the decision to skip it ----------------------------------
  # THE EXPERIMENT (L2). Skip pass 2 only on positive evidence that pass 1
  # already produced this build's image:
  #   (a) pass 1 returned 0, AND
  #   (b) the expected .pkgtb exists, AND
  #   (c) it is not older than the moment pass 1 started -- so a stale image
  #       left by a PREVIOUS build of the same version can never be mistaken
  #       for output pass 1 produced. This is the condition that matters; the
  #       filename alone proves nothing.
  # Anything short of all three runs pass 2 exactly as the canonical engine
  # does. A cold tree fails (a), so CI keeps both passes by construction.
  local _img _skip=no _p2rc=0
  _img="$(lab_image_path "$PREFIX" "$label" "$VER")"

  local _decide="two-pass"
  case "$LAB_SINGLE_PASS" in
    force) _decide="skip (forced -- diagnostic only, never a shipping mode)";;
    auto)
      if [ "$_p1rc" -ne 0 ]; then
        _decide="two-pass (pass1 rc=$_p1rc)"
      elif [ ! -f "$_img" ]; then
        _decide="two-pass (no image after pass1)"
      elif [ "$(stat -c %Y "$_img" 2>/dev/null || echo 0)" -lt "$_p1start" ]; then
        _decide="two-pass (image older than pass1 start -- stale, not produced by this pass)"
      else
        _decide="skip (pass1 rc=0, image fresh)"
      fi;;
    off) _decide="two-pass (baseline)";;
    *) _decide="two-pass (unknown LAB_SINGLE_PASS='$LAB_SINGLE_PASS')";;
  esac
  echo "[$label] single-pass decision: $_decide"

  if [ "${_decide#skip}" != "$_decide" ]; then
    _skip=yes
    _lab_phase_end "$label" pass2 0 "skipped=yes"
    echo "[$label] MAKE_EXIT=0 (pass2 skipped)"
  else
    echo "=== [$label] make $TARGET pass2 (-j${REAPER_JOBS}) $(date) ==="
    _lab_phase_start
    nice make "$TARGET" FORCE=1 -j"${REAPER_JOBS}"; _p2rc=$?
    _lab_phase_end "$label" pass2 "$_p2rc" "skipped=no"
    echo "[$label] MAKE_EXIT=$_p2rc"
  fi

  echo "[lab-decision] variant=$label single_pass=$LAB_SINGLE_PASS pass2_skipped=$_skip config_keep=$_keep"
  cd "$R" || return 1
  return "$_p2rc"
}

# ============================================================================
# The run
# ============================================================================
lab_reaper_build() {
  local ok=1 v st tag img cur

  cd "$R" || return 9

  cur=$(git rev-parse --abbrev-ref HEAD)
  if [ "$cur" != "$BRANCH" ]; then
    echo "ABORT: on branch '$cur' but this run builds '$BRANCH'."
    return 8
  fi

  VER="$(lab_read_version)"
  [ -z "$VER" ] && { echo "ABORT: cannot read Reaper version from version.conf"; return 7; }
  export VER

  echo "############ LAB $PREFIX $VER  ($BRANCH -> $TARGET)  $(date) ############"
  echo "head: $(git rev-parse --short HEAD)   variants:[$LAB_VARIANTS]"
  echo "[lab-config] single_pass=$LAB_SINGLE_PASS config_keep=$LAB_CONFIG_KEEP jobs=$REAPER_JOBS variants='$LAB_VARIANTS'"

  # --- baseline / toolchain / mtime normalize (canonical, unchanged) -------
  # The normalize sweeps are kept despite costing only 0.32s, because removing
  # them would change what gets built, and this harness exists to measure one
  # thing at a time.
  git checkout -- release/src/router/config_base release/src-rt/version.conf 2>/dev/null
  local SL=release/src-rt-5.04behnd.4916/bcmdrivers/broadcom/net/wl/impl103/main/src/router
  if [ ! -L "$SL" ]; then rm -rf "$SL"; ( cd "$(dirname "$SL")" && ln -s ../../../../../../../../src/router router ); echo "wl symlink restored"; fi
  for d in /opt/toolchains/crosstools-*gcc-10.3*/usr/bin; do export PATH="$PATH:$d"; done
  _lab_phase_start
  find "$R"/release/src/router \( -name 'configure.ac' -o -name 'configure.in' -o -name '*.am' -o \( -name '*.m4' ! -name 'aclocal.m4' \) -o -name '*.inc' -o -name 'gnulib.mk' -o -name 'glib.mk' -o -name 'glib-tap.mk' -o -name 'doxygen.mk' -o -name 'gtk-doc.make' -o -name 'Makefile.gnulib' -o -name 'Makefile-files' -o -name 'Makefile.plugins' -o -name 'Makefile.soname' \) -exec touch -t 200001010000 {} + 2>/dev/null
  find "$R"/release/src/router -name 'aclocal.m4' -exec touch -t 200001020000 {} + 2>/dev/null
  find "$R"/release/src/router \( -name 'configure' -o -name 'Makefile.in' -o -name 'config.h.in' \) -exec touch -t 200001030000 {} + 2>/dev/null
  _lab_phase_end "-" normalize 0
  echo "normalize done"

  # --- openvpn autotools version-drift guard (canonical, unchanged) -------
  local _ov="$R"/release/src/router/openvpn _ovv _ovc
  if [ -f "$_ov/version.m4" ]; then
    _ovv=$(grep -oE 'PRODUCT_VERSION_RESOURCE\], \[[0-9]+,[0-9]+,[0-9]+' "$_ov/version.m4" | grep -oE '[0-9]+,[0-9]+,[0-9]+' | tr ',' '.')
    if [ -n "$_ovv" ] && [ -f "$_ov/config.h" ] && ! grep -q "OpenVPN ${_ovv}\"" "$_ov/config.h"; then
      _ovc=$(grep -oE 'OpenVPN [0-9.]+' "$_ov/config.h" | head -1)
      echo "openvpn version drift: version.m4=$_ovv but config.h=[$_ovc] -> forcing autogen regen"
      rm -f "$_ov/Makefile" "$_ov/config.h" "$_ov/config.status" "$_ov/configure"
    fi
  fi

  # --- variants ------------------------------------------------------------
  for v in $LAB_VARIANTS; do
    if [ "$v" = "noMCP" ]; then
      sed -i 's/^RTCONFIG_REAPER_MCP=y$/# RTCONFIG_REAPER_MCP is not set/' release/src/router/config_base
      sed -i "s/^EXTENDNO=${VER}\$/EXTENDNO=${VER}_noMCP/" release/src-rt/version.conf
      echo "noMCP flip: $(grep REAPER_MCP release/src/router/config_base) | $(grep ^EXTENDNO= release/src-rt/version.conf)"
    fi

    _rb_variant "$v"

    tag=""; [ "$v" = "noMCP" ] && tag="_noMCP"
    img="$(lab_image_path "$PREFIX" "$v" "$VER")"
    if [ -f "$img" ]; then
      echo "  [OK] $v  $(basename "$img")  sha:$(sha256sum "$img" | cut -c1-16)"
      echo "[lab-image] variant=$v sha256=$(sha256sum "$img" | cut -d' ' -f1) bytes=$(stat -c%s "$img")"
    else
      echo "  [MISSING] $v  $(basename "$img")"; ok=0
    fi

    # --- staged-fs digest, captured BEFORE the next variant overwrites fs/ --
    # This is the comparator the whole harness turns on. reaper_verify checks
    # proxies (line counts, file presence) and has passed builds with a
    # stripped dictionary and a missing IPSec stack; the digest does not.
    if [ -x "$LAB_DIR/stagedfs_digest.sh" ] || [ -f "$LAB_DIR/stagedfs_digest.sh" ]; then
      _lab_phase_start
      bash "$LAB_DIR/stagedfs_digest.sh" "$TDIR/fs" "$LAB_RUN_DIR" "${PREFIX}-${v}" || echo "[lab] digest failed for $v"
      _lab_phase_end "$v" digest 0
    fi

    # --- QA gate -------------------------------------------------------------
    if [ -f "$LAB_VERIFY" ]; then
      _lab_phase_start
      if bash "$LAB_VERIFY" "$PREFIX" "$v" "$VER" "$TDIR/fs" "$img" \
           > "$LAB_RUN_DIR/verify-${PREFIX}-${v}.txt" 2>&1; then
        echo "[lab-verify] variant=$v result=PASS $(grep -c '^\[PASS\]' "$LAB_RUN_DIR/verify-${PREFIX}-${v}.txt") checks"
      else
        echo "[lab-verify] variant=$v result=FAIL -- see verify-${PREFIX}-${v}.txt"; ok=0
      fi
      _lab_phase_end "$v" verify 0
      grep -E '^\[(FAIL|WARN)\]' "$LAB_RUN_DIR/verify-${PREFIX}-${v}.txt" | sed 's/^/    /' || true
    fi

    git checkout -- release/src-rt/version.conf 2>/dev/null   # reset EXTENDNO between variants
  done

  lab_restore_flip

  if [ $ok = 1 ]; then echo "== LAB BUILD OK =="; else echo "== LAB BUILD INCOMPLETE =="; return 1; fi
  echo "############ LAB $PREFIX $VER done $(date) ############"
}
