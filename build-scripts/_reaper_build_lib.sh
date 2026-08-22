#!/bin/bash
# ============================================================================
# Reaper shared per-model build engine  (sourced by build_<model>.sh launchers)
# ----------------------------------------------------------------------------
# A launcher sets these, then calls `reaper_build [ship]`:
#     BRANCH   git branch for the model      (e.g. rt-be88u)
#     TARGET   make target                    (e.g. rt-be88u)
#     PREFIX   image name prefix / BUILD_NAME (e.g. RT-BE88U)
#     VARIANTS space list                     (e.g. "MCP noMCP")
#     STORAGE  space list                     (e.g. "nand emmc")
#     SHIP_DIR ladder dir for `ship` step     (optional)
#
# VER is auto-read from the *committed* version.conf on the branch, so the
# normal flow is: checkout branch -> bump+commit version.conf -> run launcher.
# Nothing in these scripts needs editing per version.
#
# Derived from the proven build_model_v175.sh. Key model-switch fix: each
# variant does `rm .config config_<target>` so `make <model>` re-generates the
# profile for THIS model (otherwise a stale .config triggers MODEL NAME
# MISMATCH when switching models in the shared clone).
# ============================================================================
set -u
R=/home/reaper/asuswrt-be96u
P=$R/release/src-rt-5.04behnd.4916
TDIR=$P/targets/96813GW

# REAPER_JOBS: top-level make parallelism. DEFAULT 1 - PROVEN REQUIRED.
# 2026-08-04: a -j8 attempt (owner ask, first run) failed deterministically:
# the vendor top-level targets have NO dependency ordering (clean-build's
# `rm -rf fs.build` raced component installs -> "Directory not empty";
# fsbuild raced the fs.install skeleton -> "cannot create directory ...
# Not a directory"; make rt-be96u Error 2, reaper_verify 2 FAIL, ship
# blocked). They are sequenced ONLY by serial execution - top level MUST
# stay -j1. Parallelism comes from (a) sub-makes that force their own -jN
# internally (libxml2/json-c force -j14) and (b) running two DISTROS at
# once. Do not raise this default again without fixing the vendor Makefile
# ordering.
: "${REAPER_JOBS:=1}"

# REAPER_SINGLE_PASS: skip pass 2 when pass 1 already produced the image.
#   auto  (default) skip only on positive evidence -- see the decision below
#   off             always run both passes (the pre-2026-08-15 behaviour)
#   force           never run pass 2 -- DIAGNOSTIC ONLY, never a shipping mode
#
# WHY. The two-pass structure exists because a fresh clone dies at setprofile in
# pass 1. That stopped happening locally: `pass1_exit=0` in every rung from
# v2.3.8 to v2.4.4, i.e. pass 1 ran to completion and wrote the .pkgtb, and
# pass 2 then rebuilt what already existed. The likely cause is FORCE=1 (added
# 2026-07-27), which skips profile_saved_check -- the very check that made pass 1
# fail. Nobody removed pass 2 afterwards.
#
# MEASURED (build-lab session ab-20260815-155150, RT-BE96U MCP, warm tree):
#   two-pass 12:04 -> single-pass 6:28  (-46%), and the candidate ran FIRST on
#   the colder tree so the figure is conservative. Content EQUIVALENT: 3328 of
#   3333 staged files hash-identical, 0 structural differences, reaper_verify
#   20/20. The 5 files that differ are the build's own irreproducibility -- they
#   differ between two IDENTICAL-config builds as well (three timestamps, an
#   unsorted depmod output, and libshared.so's compiled-in build stamp).
#   Replicated over 6 more variant builds in session ab-20260815-163332.
#
# COLD TREES ARE UNAFFECTED BY CONSTRUCTION. There pass 1 genuinely dies, so the
# rc test below fails and both passes run exactly as before. That is the CI case,
# which is why this default does not change the release path's behaviour.
: "${REAPER_SINGLE_PASS:=auto}"

_rb_variant() {   # $1 = MCP|noMCP
  local label="$1"

  # STALE-CONFIGURE GUARD (2026-08-09). `<pkg>/Makefile: <pkg>/configure` never
  # re-fires on a warm tree because tarball configure scripts carry an epoch
  # mtime, so a patch that changes --enable/--disable flags is silently inert.
  # strongswan shipped that way for three weeks across all five models before a
  # CI-vs-local image diff caught it. --fix clears the stale state so the next
  # build re-configures; a clean tree (CI) is a no-op.
  local _sc="$(dirname "${BASH_SOURCE[0]}")/reaper_stale_configure.sh"
  if [ -x "$_sc" ] || [ -f "$_sc" ]; then
    echo "=== [$label] stale-configure guard ==="
    bash "$_sc" --fix "$R" || true
  fi

  # PROVENANCE STAMP. CI runs gen_provenance.sh before its build; the local
  # engine never did, so a locally built image showed dashes on the About page
  # where a CI image of the same source shows real figures - a visible
  # difference between two images that should be identical, which is exactly
  # what the decompose-and-diff cross-check exists to notice. Must run BEFORE
  # the vendor www install, i.e. before make. Deliberately non-fatal: an empty
  # field renders as a dash, which is honest, so a stamping failure must never
  # take a build down. Output is gitignored, so this cannot dirty the tree and
  # cannot make cut_fleet refuse to run.
  local _gp="$(dirname "${BASH_SOURCE[0]}")/gen_provenance.sh"
  if [ -f "$_gp" ]; then
    # Patch count: claim one ONLY when the public series' tip IS this version
    # (the tip is the bump patch, named ...Reaper_v<X>). A local rung built
    # ahead of its cut stamps a dash - honest - never the previous cut's
    # count (that stale-number failure shipped v2.5.0/465 on every local
    # image up to v2.5.8). In CI, series == EXPECTED_VERSION == build, so
    # the real count shows. Series dir: lean repo layout first, engine-dir
    # fallback via WIN_ASUS_ROOT (set by _reaper_env.sh).
    local _pd="$(dirname "${BASH_SOURCE[0]}")/../patches"
    [ -n "$(ls "$_pd"/*.patch 2>/dev/null | head -1)" ] \
      || _pd="${WIN_ASUS_ROOT:-/mnt/c/Users/natha/AppData/Roaming/VSC/ASUS}/ASUS-Merlin-Reaper/patches"
    # 2026-08-22 (field, v2.6.7): the owner runs the LOCAL images, so "dash
    # until cut" showed a dash on every image that was ever flashed. Now the
    # series count is ALWAYS stamped together with the version the series is
    # AS OF (its tip); the page prints the plain count when that equals the
    # running version, and "N - series as of vX" when the image is ahead of
    # its cut. Still never the previous cut's count passed off as this one's.
    local _pc="" _tip="" _sv="" _cv=""
    _cv=$(grep '^EXTENDNO=' "$R/release/src-rt/version.conf" 2>/dev/null \
          | grep -oE 'v[0-9]+\.[0-9]+(\.[0-9]+)?[a-z]?' | head -1)
    _tip=$(ls "$_pd"/*.patch 2>/dev/null | tail -1)
    if [ -n "$_tip" ]; then
      _sv=$(basename "$_tip" | grep -oE 'v[0-9]+\.[0-9]+(\.[0-9]+)?[a-z]?' | tail -1)
      [ -n "$_sv" ] && _pc=$(ls "$_pd"/*.patch 2>/dev/null | wc -l)
    fi
    # VARIANT must be passed explicitly: the generator's .config fallback
    # reads the PREVIOUS variant's config at stamp time (we run before make).
    echo "=== [$label] provenance stamp (patches=${_pc:--} series=${_sv:--} build=${_cv:--}) ==="
    VARIANT="$label" PATCH_SERIES="$_sv" bash "$_gp" "$R" "$_pc" a7ebfa133ad7e5efc23ed6bb8ee912bc72fd00b3 \
      || echo "    ! provenance stamp failed - the About page will show dashes"
  fi

  cd "$P" || return 9
  # 2026-08-13: "config_${TARGET}" was RELATIVE here, and we have just cd'd to
  # $P - but the generated model profile lives in release/src/router/, so that
  # argument matched nothing and the rm had been a silent no-op since the script
  # was written. (The zlib stamp on the same line was already absolute, which is
  # what makes the inconsistency easy to miss.) Nothing broke, because deleting
  # .config alone is enough to force the regen; the profile is rewritten every
  # pass regardless. Fixed so the code does what its comment claims, which
  # matters in a model-switch failure - the stale-profile MODEL NAME MISMATCH
  # this line is supposed to prevent is exactly the situation where someone
  # would read it and believe the protection was already in place.
  rm -f .config "$R/release/src/router/config_${TARGET}" \
        "$R"/release/src/router/zlib/stamp-h1
  echo "=== [$label] make $TARGET pass1 (regen; may die at setprofile, -j${REAPER_JOBS}) $(date) ==="
  # Pass 1 is silenced because it is EXPECTED to die at setprofile. On a cold
  # tree that is a problem: the samba crypto chain (zlib/gmp/nettle/gnutls) is
  # built HERE, so discarding pass 1 throws away every compile and link line for
  # it. A chain failure then surfaces only in pass 2 as a bare
  #   install: cannot stat '.libs/libgmp.so.10.4.1'
  # with no build output anywhere in the log to explain it -- which is exactly
  # how the first two clean-room CI runs failed undiagnosably.
  # Local builds keep the quiet default; set REAPER_PASS1_LOG=<path> to capture.
  local _p1rc _p1start
  _p1start=$(date +%s)
  if [ -n "${REAPER_PASS1_LOG:-}" ]; then
    nice make "$TARGET" FORCE=1 -j"${REAPER_JOBS}" >"$REAPER_PASS1_LOG" 2>&1; _p1rc=$?
  else
    nice make "$TARGET" FORCE=1 -j"${REAPER_JOBS}" >/dev/null 2>&1; _p1rc=$?
  fi
  echo "[$label] pass1_exit=$_p1rc"

  # COLD-TREE GUARD (2026-08-09, found by the first clean-room CI build).
  # samba-4.15.13/build/ is gitignored, so a fresh clone has no crypto chain.
  # build-reaper.sh only builds that chain when staging/lib/libgnutls.so.30 is
  # absent, and it `tar xf`s the dep tarballs OVER whatever is already there.
  # Pass 1 legitimately dies at setprofile, leaving gmp half-built; pass 2 then
  # re-extracts on top, make treats libgmp.la as current, and `make install`
  # copies .libs/libgmp.so.10.4.1 -- which was never linked:
  #   /usr/bin/install: cannot stat '.libs/libgmp.so.10.4.1': No such file
  # Clearing a demonstrably incomplete chain makes pass 2 build it from scratch.
  # NO-OP on a warm tree (the .so exists), so local builds are unaffected.
  # The guard reports on EVERY path, not just when it fires. A guard that is
  # silent when it decides to do nothing is indistinguishable in the log from a
  # guard that never ran -- which is precisely why run #2 could not be read: it
  # was impossible to tell whether gmp was built in pass 1 (discarded) or in
  # pass 2 (logged), and therefore whether the evidence existed at all.
  local _sam="$R/release/src/router/samba-4.15.13"
  if [ ! -d "$_sam/build" ]; then
    echo "[$label] cold-tree guard: no samba build/ after pass1 -- pass2 builds the crypto chain from scratch"
  elif [ ! -e "$_sam/build/staging/lib/libgnutls.so.30" ]; then
    echo "[$label] cold-tree guard: FIRED -- chain incomplete after pass1 (no libgnutls.so.30); clearing build/"
    echo "[$label]   staging/lib was: $(ls "$_sam/build/staging/lib" 2>/dev/null | tr '\n' ' ')"
    echo "[$label]   gmp .so present: $(ls "$_sam"/build/gmp-6.2.1/.libs/libgmp.so.10.4.1 2>/dev/null || echo NO)"
    rm -rf "$_sam/build" "$_sam/.reaper-built"
  else
    echo "[$label] cold-tree guard: not needed -- crypto chain complete after pass1 (libgnutls.so.30 staged)"
  fi

  # --- pass 2, or the evidence-backed decision to skip it -------------------
  # Skip ONLY on all three of:
  #   (a) pass 1 returned 0;
  #   (b) every expected image for this variant exists;
  #   (c) each is not older than the moment pass 1 started.
  # (c) is the one that matters. Without it a stale image left by a PREVIOUS
  # build of the same version satisfies (b) and pass 2 gets skipped over work
  # that never happened. The filename proves nothing; the mtime does.
  local _p2rc=0 _skip=no _decide _st _img
  case "$REAPER_SINGLE_PASS" in
    force) _decide="skip (FORCED -- diagnostic mode, not for shipping)";;
    off)   _decide="two-pass (REAPER_SINGLE_PASS=off)";;
    auto)
      if [ "$_p1rc" -ne 0 ]; then
        _decide="two-pass (pass1 rc=$_p1rc -- cold tree or a real failure)"
      else
        _decide="skip (pass1 rc=0, images fresh)"
        for _st in ${STORAGE:-nand}; do
          _img="$TDIR/${PREFIX}_3006_102.8_${VER}$([ "$label" = noMCP ] && echo _noMCP)_${_st}_squashfs.pkgtb"
          if [ ! -f "$_img" ]; then
            _decide="two-pass (no $_st image after pass1)"; break
          elif [ "$(stat -c %Y "$_img" 2>/dev/null || echo 0)" -lt "$_p1start" ]; then
            _decide="two-pass ($_st image predates pass1 -- stale, not built by this pass)"; break
          fi
        done
      fi;;
    *) _decide="two-pass (unrecognised REAPER_SINGLE_PASS='$REAPER_SINGLE_PASS')";;
  esac
  echo "[$label] pass2 decision: $_decide"

  if [ "${_decide#skip}" != "$_decide" ]; then
    _skip=yes
    echo "[$label] MAKE_EXIT=0 (pass2 skipped -- pass1 produced the image)"
  else
    echo "=== [$label] make $TARGET pass2 (-j${REAPER_JOBS}) $(date) ==="
    nice make "$TARGET" FORCE=1 -j"${REAPER_JOBS}"; _p2rc=$?
    echo "[$label] MAKE_EXIT=$_p2rc"
    [ "$_p2rc" -eq 0 ] || _rb_crypto_postmortem "$label"
  fi
  echo "[$label] pass2_skipped=$_skip"
  cd "$R" || return 1
  return "$_p2rc"
}

# Called only when pass 2 failed. The samba crypto chain is the one part of the
# build whose failure mode is silent -- `make all` can report success while the
# shared object was never linked, so the error lands in `make install` and names
# a file, not a cause. This answers the questions that actually discriminate:
# was the library linked at all, does the .la claim a shared name, and does make
# consider it up to date against sources a re-extract may have back-dated.
_rb_crypto_postmortem() {   # $1 = label
  local label="$1" S="$R/release/src/router/samba-4.15.13" G
  G="$S/build/gmp-6.2.1"
  echo "--- [$label] crypto-chain post-mortem ---"
  echo "  staging/lib : $(ls "$S/build/staging/lib" 2>/dev/null | tr '\n' ' ')"
  if [ -d "$G" ]; then
    if ls "$G"/.libs/libgmp.so* >/dev/null 2>&1; then
      ls -l "$G"/.libs/libgmp.so* 2>/dev/null | sed 's/^/    /'
    else
      echo "    NO .libs/libgmp.so* -- the shared link never ran"
    fi
    if [ -f "$G/libgmp.la" ]; then
      grep -E '^(dlname|library_names|installed)=' "$G/libgmp.la" | sed 's/^/    la: /'
      echo "  sources newer than libgmp.la (would force a relink):"
      find "$G" -maxdepth 1 -name '*.c' -newer "$G/libgmp.la" 2>/dev/null | head -3 | sed 's/^/    /'
      echo "  libgmp.la mtime: $(stat -c%y "$G/libgmp.la" 2>/dev/null)"
    else
      echo "    libgmp.la absent -- gmp never reached its link step"
    fi
    # The three values that decide which link branch libtool takes. gmp is the
    # longest link in the build and the only one that fails, and in CI libtool
    # emitted no link command at all -- so these are the numbers that explain
    # it. Locally: max_cmd_len=1572864, and the link succeeds.
    if [ -f "$G/libtool" ]; then
      echo "  libtool link-branch config:"
      grep -E '^(max_cmd_len|file_list_spec|with_gnu_ld|archive_cmds|build_libtool_libs)=' \
        "$G/libtool" | cut -c1-160 | sed 's/^/    /'
    fi
    echo "  lt_cv_sys_max_cmd_len in env: ${lt_cv_sys_max_cmd_len:-<unset>}"
  else
    echo "  no gmp build dir (chain not reached, or cleared by the cold-tree guard)"
  fi
  [ -n "${REAPER_PASS1_LOG:-}" ] && [ -f "$REAPER_PASS1_LOG" ] && {
    echo "  pass1 crypto-chain lines (pass 1 is where the chain is built):"
    grep -E '\[build-reaper\]|libgmp|mode=link|cannot stat|Error [0-9]' \
      "$REAPER_PASS1_LOG" 2>/dev/null | tail -25 | sed 's/^/    /'
  }
  echo "--- end post-mortem ---"
}

reaper_ship() {   # $1 = VER
  local VER="$1" shipped=0 v tag st suf f
  [ -z "${SHIP_DIR:-}" ] && { echo "no SHIP_DIR set; skip ship"; return 0; }
  echo "== ship $PREFIX $VER -> $SHIP_DIR (never overwrites an existing ladder entry) =="
  for v in $VARIANTS; do tag=""; [ "$v" = "noMCP" ] && tag="_noMCP"
    for st in $STORAGE; do
      for suf in "_squashfs.pkgtb" "_squashfs_loader.pkgtb"; do
        f="${PREFIX}_3006_102.8_${VER}${tag}_${st}${suf}"
        [ -f "$TDIR/$f" ] || continue
        if [ -e "$SHIP_DIR/$f" ]; then echo "  [skip exists] $f"; continue; fi
        if cp "$TDIR/$f" "$SHIP_DIR/$f"; then
          b=$(sha256sum "$TDIR/$f"|awk '{print $1}'); s=$(sha256sum "$SHIP_DIR/$f"|awk '{print $1}')
          [ "$b" = "$s" ] && echo "  [ship+MATCH] $f" || echo "  [SHIP MISMATCH] $f"
          shipped=1
        fi
      done
    done
  done
  [ $shipped = 1 ] && ( cd "$SHIP_DIR" && sha256sum ${PREFIX}_*_${VER}*_squashfs*.pkgtb 2>/dev/null > "SHA256SUMS-${PREFIX}-${VER}.txt"; echo "  wrote SHA256SUMS-${PREFIX}-${VER}.txt" )
}

reaper_build() {
  local DO_SHIP="${1:-}" VER cur ok=1 v st tag img
  cd "$R" || return 9

  # --- branch safety: must be on the model's branch, working tree clean-ish ---
  cur=$(git rev-parse --abbrev-ref HEAD)
  if [ "$cur" != "$BRANCH" ]; then
    echo "ABORT: on branch '$cur' but this launcher builds '$BRANCH'."
    echo "       Run:  git checkout $BRANCH   (commit/stash your work first), then re-run."
    return 8
  fi

  VER=$(grep -oE 'Reaper_v[0-9]+\.[0-9]+(\.[0-9]+)?[a-z]?' release/src-rt/version.conf | head -1)
  [ -z "$VER" ] && { echo "ABORT: could not read Reaper_vX.Y from release/src-rt/version.conf"; return 7; }

  local LOG=/home/reaper/build_${TARGET}_${VER}.log
  exec > >(tee "$LOG") 2>&1
  echo "############ $PREFIX $VER  ($BRANCH -> $TARGET)  $(date) ############"
  echo "head: $(git rev-parse --short HEAD)   variants:[$VARIANTS]   storage:[$STORAGE]"
  # ENGINE IDENTITY IN EVERY LOG. Two copies of this file exist -- this one and
  # /home/reaper/reaper_build/ -- and on 2026-08-15 they were found to have
  # diverged: v2.4.3 built with the guards present, v2.4.4 the next day without
  # them, and nothing in either log said so. Recording the path and hash makes
  # that visible at a glance in any log, forever, instead of requiring an
  # archaeology session to notice.
  echo "engine: ${BASH_SOURCE[0]}"
  echo "engine_sha256: $(sha256sum "${BASH_SOURCE[0]}" 2>/dev/null | cut -d' ' -f1)"
  echo "single_pass: $REAPER_SINGLE_PASS   jobs: $REAPER_JOBS"

  # baseline / toolchain / autotools-mtime normalize (proven recipe, unchanged)
  git checkout -- release/src/router/config_base release/src-rt/version.conf 2>/dev/null
  local SL=release/src-rt-5.04behnd.4916/bcmdrivers/broadcom/net/wl/impl103/main/src/router
  if [ ! -L "$SL" ]; then rm -rf "$SL"; ( cd "$(dirname "$SL")" && ln -s ../../../../../../../../src/router router ); echo "wl symlink restored"; fi
  for d in /opt/toolchains/crosstools-*gcc-10.3*/usr/bin; do export PATH="$PATH:$d"; done
  find "$R"/release/src/router \( -name 'configure.ac' -o -name 'configure.in' -o -name '*.am' -o \( -name '*.m4' ! -name 'aclocal.m4' \) -o -name '*.inc' -o -name 'gnulib.mk' -o -name 'glib.mk' -o -name 'glib-tap.mk' -o -name 'doxygen.mk' -o -name 'gtk-doc.make' -o -name 'Makefile.gnulib' -o -name 'Makefile-files' -o -name 'Makefile.plugins' -o -name 'Makefile.soname' \) -exec touch -t 200001010000 {} + 2>/dev/null
  find "$R"/release/src/router -name 'aclocal.m4' -exec touch -t 200001020000 {} + 2>/dev/null
  find "$R"/release/src/router \( -name 'configure' -o -name 'Makefile.in' -o -name 'config.h.in' \) -exec touch -t 200001030000 {} + 2>/dev/null
  echo "normalize done"

  # --- openvpn autotools version-drift guard -------------------------------
  # openvpn's build rule (release/src/router/Makefile) only runs ./autogen.sh
  # when openvpn/Makefile is ABSENT, and the mtime-normalize above freezes the
  # generated ./configure as "newer than version.m4" so autotools never
  # regenerates it. Net effect: a version.m4 bump (e.g. 2.7.4 -> 2.7.5, carried
  # from upstream Merlin) never reaches the generated config.h, so the compiled
  # binary keeps reporting the OLD version even though the .c source is new
  # (field-observed: v2.1.2 shipped 2.7.5 code still reporting "OpenVPN 2.7.4").
  # If the committed version.m4 disagrees with the generated config.h, wipe the
  # openvpn generated files so the next build regenerates them at the real
  # version. Cheap: fires only on an actual version bump.
  local _ov="$R"/release/src/router/openvpn _ovv _ovc
  if [ -f "$_ov/version.m4" ]; then
    _ovv=$(grep -oE 'PRODUCT_VERSION_RESOURCE\], \[[0-9]+,[0-9]+,[0-9]+' "$_ov/version.m4" | grep -oE '[0-9]+,[0-9]+,[0-9]+' | tr ',' '.')
    if [ -n "$_ovv" ] && [ -f "$_ov/config.h" ] && ! grep -q "OpenVPN ${_ovv}\"" "$_ov/config.h"; then
      _ovc=$(grep -oE 'OpenVPN [0-9.]+' "$_ov/config.h" | head -1)
      echo "openvpn version drift: version.m4=$_ovv but config.h=[$_ovc] -> wiping openvpn generated files to force autogen regen"
      rm -f "$_ov/Makefile" "$_ov/config.h" "$_ov/config.status" "$_ov/configure"
    fi
  fi

  for v in $VARIANTS; do
    if [ "$v" = "noMCP" ]; then
      sed -i 's/^RTCONFIG_REAPER_MCP=y$/# RTCONFIG_REAPER_MCP is not set/' release/src/router/config_base
      sed -i "s/^EXTENDNO=${VER}\$/EXTENDNO=${VER}_noMCP/" release/src-rt/version.conf
      echo "noMCP flip: $(grep REAPER_MCP release/src/router/config_base) | $(grep ^EXTENDNO= release/src-rt/version.conf)"
    fi
    _rb_variant "$v"
    tag=""; [ "$v" = "noMCP" ] && tag="_noMCP"
    for st in $STORAGE; do
      img="$TDIR/${PREFIX}_3006_102.8_${VER}${tag}_${st}_squashfs.pkgtb"
      if [ -f "$img" ]; then echo "  [OK] $v/$st  $(basename "$img")  sha:$(sha256sum "$img"|cut -c1-16)"
      else echo "  [MISSING] $v/$st  $(basename "$img")"; ok=0; fi
    done
    # deep post-build QA gate (reaper_verify): fail-closed on packaging defects
    if [ -x /home/reaper/reaper_build/reaper_verify.sh ]; then
      if ! /home/reaper/reaper_build/reaper_verify.sh "$PREFIX" "$v" "$VER"; then
        echo "  [VERIFY FAILED] $PREFIX $v -- see checks above; blocking ship"; ok=0
      fi
    fi
    git checkout -- release/src-rt/version.conf 2>/dev/null   # reset EXTENDNO between variants
  done
  git checkout -- release/src/router/config_base release/src-rt/version.conf 2>/dev/null

  if [ $ok = 1 ]; then echo "== BUILD OK: all $VARIANTS x $STORAGE images present =="
  else echo "== BUILD INCOMPLETE - inspect $LOG (grep MAKE_EXIT / MISMATCH / Error) =="; return 1; fi

  [ "$DO_SHIP" = "ship" ] && reaper_ship "$VER"
  echo "############ $PREFIX $VER done $(date) ############"
}
