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

_rb_variant() {   # $1 = MCP|noMCP
  local label="$1"
  cd "$P" || return 9
  rm -f .config "config_${TARGET}" "$R"/release/src/router/zlib/stamp-h1
  echo "=== [$label] make $TARGET pass1 (regen; may die at setprofile) $(date) ==="
  nice make "$TARGET" FORCE=1 -j1 >/dev/null 2>&1; echo "[$label] pass1_exit=$?"
  echo "=== [$label] make $TARGET pass2 $(date) ==="
  nice make "$TARGET" FORCE=1 -j1; echo "[$label] MAKE_EXIT=$?"
  cd "$R"
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

  # baseline / toolchain / autotools-mtime normalize (proven recipe, unchanged)
  git checkout -- release/src/router/config_base release/src-rt/version.conf 2>/dev/null
  local SL=release/src-rt-5.04behnd.4916/bcmdrivers/broadcom/net/wl/impl103/main/src/router
  if [ ! -L "$SL" ]; then rm -rf "$SL"; ( cd "$(dirname "$SL")" && ln -s ../../../../../../../../src/router router ); echo "wl symlink restored"; fi
  for d in /opt/toolchains/crosstools-*gcc-10.3*/usr/bin; do export PATH="$PATH:$d"; done
  find "$R"/release/src/router \( -name 'configure.ac' -o -name 'configure.in' -o -name '*.am' -o \( -name '*.m4' ! -name 'aclocal.m4' \) -o -name '*.inc' -o -name 'gnulib.mk' -o -name 'glib.mk' -o -name 'glib-tap.mk' -o -name 'doxygen.mk' -o -name 'gtk-doc.make' -o -name 'Makefile.gnulib' -o -name 'Makefile-files' -o -name 'Makefile.plugins' -o -name 'Makefile.soname' \) -exec touch -t 200001010000 {} + 2>/dev/null
  find "$R"/release/src/router -name 'aclocal.m4' -exec touch -t 200001020000 {} + 2>/dev/null
  find "$R"/release/src/router \( -name 'configure' -o -name 'Makefile.in' -o -name 'config.h.in' \) -exec touch -t 200001030000 {} + 2>/dev/null
  echo "normalize done"

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
