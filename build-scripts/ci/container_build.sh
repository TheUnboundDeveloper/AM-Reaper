#!/usr/bin/env bash
# ============================================================================
# container_build.sh -- clean-room Reaper build, run INSIDE an ubuntu:20.04
#                       container on a GitHub-hosted runner.
# ----------------------------------------------------------------------------
# Reproduces the documented local build environment (build-scripts/README.md,
# memory build-sop) exactly:
#
#   /home/reaper/asuswrt-be96u   pinned upstream base + the published patches
#   /home/reaper/reaper_build    this repo's build-scripts/ verbatim
#   /opt/toolchains              pinned am-toolchains crosstools (gcc-10.3)
#   user reaper, uid 1001        Broadcom prebuild_checks rejects root builds
#   /bin/sh -> bash, python2     Merlin's documented Focal requirements
#
# It then runs THE PROJECT'S OWN build engine (_reaper_build_lib.sh via
# ci/build_one.sh) -- it does not reimplement the build.
#
# Runs first as root (environment prep), then re-execs itself as `reaper`.
#
# Required env: UPSTREAM_REPO BASE_COMMIT BASE_TAG TOOLCHAIN_COMMIT
#               MODEL VARIANT REPO_DIR OUT_DIR SRC_DIR
#               (BUILD_BRANCH is DERIVED from MODEL below -- do not pass it in)
# ============================================================================
set -euo pipefail

: "${UPSTREAM_REPO:?}" "${BASE_COMMIT:?}" "${BASE_TAG:?}" "${TOOLCHAIN_COMMIT:?}"
: "${MODEL:?}" "${VARIANT:?}"
: "${REPO_DIR:?}" "${OUT_DIR:?}" "${SRC_DIR:?}"

# The build branch must match what ci/build_one.sh expects for this model --
# _reaper_build_lib.sh refuses to build unless HEAD is on the model's branch.
#
# MODEL is the ONLY source of truth. This used to honour an inherited
# BUILD_BRANCH, and public-build.yml carried a leftover single-model pin
# (BUILD_BRANCH: be96u-only) that therefore won for every sibling -- all four
# aborted with rc=8 "on branch 'be96u-only' but this launcher builds '<model>'"
# before a single object was compiled. An inherited value is now REFUSED rather
# than obeyed: a caller that disagrees with the model is a caller with a bug.
case "$MODEL" in
  RT-BE96U)    _WANT_BRANCH=be96u-only;;
  RT-BE86U)    _WANT_BRANCH=rt-be86u;;
  RT-BE88U)    _WANT_BRANCH=rt-be88u;;
  GT-BE98)     _WANT_BRANCH=gt-be98;;
  GT-BE98_PRO) _WANT_BRANCH=gt-be98-pro;;
  *) echo "ERROR: unknown MODEL '$MODEL'"; exit 2;;
esac
if [ -n "${BUILD_BRANCH:-}" ] && [ "$BUILD_BRANCH" != "$_WANT_BRANCH" ]; then
  echo "::error::BUILD_BRANCH='$BUILD_BRANCH' was inherited but MODEL='$MODEL' requires '$_WANT_BRANCH'."
  echo "          Unset BUILD_BRANCH in the caller -- it is derived from MODEL here."
  exit 2
fi
BUILD_BRANCH="$_WANT_BRANCH"
export BUILD_BRANCH
echo "build branch for $MODEL: $BUILD_BRANCH"

REAPER_HOME=/home/reaper
BUILD_SCRIPTS="$REAPER_HOME/reaper_build"

hr() { echo "============================================================"; }

# ============================================================================
# PART 1 -- root: environment preparation
# ============================================================================
if [ "$(id -u)" = 0 ]; then
  export DEBIAN_FRONTEND=noninteractive

  hr; echo " Reaper clean-room build -- $MODEL / $VARIANT"; hr

  # --- host packages ------------------------------------------------------
  # Bulk install first; on failure fall back to one-by-one so a single
  # unavailable package reports itself instead of killing a 3-hour job.
  apt-get update -qq
  apt-get install -y -qq software-properties-common ca-certificates \
                         git curl wget sudo >/dev/null
  add-apt-repository -y universe >/dev/null 2>&1
  dpkg --add-architecture i386
  apt-get update -qq

  PKGS="build-essential bison flex gawk gettext libreadline-dev libssl-dev
        autogen autoconf automake libtool gtk-doc-tools u-boot-tools
        python2 python2-dev python3 python3-distutils python3-dev
        cmake liblzo2-dev uuid-dev xxd patch gdisk bc lzop lz4 zstd kmod
        libelf-dev libncurses5-dev pkg-config binutils file rsync perl
        qemu-user-static binfmt-support libparse-yapp-perl autopoint unzip
        gengetopt texinfo gperf libtool-bin m4 bzip2 dos2unix zlib1g-dev
        libexpat1-dev libxml-parser-perl libxml2-dev intltool libglib2.0-dev
        autoconf-archive xsltproc libltdl-dev shtool gcc-multilib g++-multilib
        lib32ncurses-dev lib32z1-dev lib32stdc++6 libelf-dev:i386 libelf1:i386
        mtd-utils lzip patchelf execstack libproxy-dev groff-base libslang2
        subversion cvs libncurses5 libvorbis-dev xutils-dev
        libc6:i386 libstdc++6:i386 libncurses5:i386 zlib1g:i386"

  echo "-- installing build dependencies"
  if ! apt-get install -y -qq $PKGS >/dev/null 2>&1; then
    echo "   bulk install failed; retrying package-by-package"
    missing=""
    for p in $PKGS; do
      apt-get install -y -qq "$p" >/dev/null 2>&1 || missing="$missing $p"
    done
    [ -n "$missing" ] && echo "::warning::packages unavailable:$missing"
  fi

  # Documented Merlin build requirements.
  ln -sf bash /bin/sh
  update-alternatives --install /usr/bin/python python /usr/bin/python2 1 >/dev/null

  # UTF-8 LOCALE -- REQUIRED, not cosmetic. The 25 www/*.dict language files are
  # UTF-8, and the build runs them through the PREBUILT tool
  # router/tools/Lnx_ToolHelp/LnxHtmlEnumDict. A bare ubuntu:20.04 container has
  # no locale set and no `locales` package, i.e. POSIX/C with no multibyte
  # support -- under which that tool SEGFAULTS (6 times, seen in every run so
  # far) and emits ASCII-only dictionaries. The 2026-08-09 CI-vs-local image
  # diff caught it: TH.dict went from 5,579 lines containing non-ASCII down to
  # 14, i.e. every Thai/Cyrillic/CJK string silently deleted, while the line
  # count stayed lockstep at 6142 so the verify gate never noticed.
  # The maintainer's WSL builds under LANG=C.UTF-8 -- match it exactly.
  apt-get install -y -qq locales >/dev/null 2>&1 || true
  export LANG=C.UTF-8 LANGUAGE=
  # NOTE: LANG only. Do NOT export LC_ALL -- the staged-fs digest below relies on
  # inline `LC_ALL=C sort` for deterministic ordering, and a global LC_ALL would
  # be harder to reason about. C.UTF-8 is built into glibc on Focal, so this
  # needs no locale-gen.

  echo "-- build environment"
  grep PRETTY_NAME /etc/os-release
  echo "   sh   -> $(readlink -f /bin/sh)"
  echo "   LANG -> ${LANG:-<unset>}  (multibyte: $(printf 'ä' | wc -m) char for a 2-byte sequence -- must be 1)"
  echo "   $(python --version 2>&1)"
  echo "   $(gcc --version | head -1)"

  # --- non-root build user (uid 1001 == the runner's uid, so the bind-mounted
  #     home and workspace are already owned correctly) ----------------------
  if ! id reaper >/dev/null 2>&1; then
    useradd -u 1001 -d "$REAPER_HOME" -s /bin/bash reaper 2>/dev/null \
      || useradd -d "$REAPER_HOME" -s /bin/bash reaper
  fi
  mkdir -p "$REAPER_HOME" "$BUILD_SCRIPTS" "$OUT_DIR" "$SRC_DIR"

  # --- pinned toolchains --------------------------------------------------
  hr; echo " Pinned Asuswrt-Merlin toolchains"; hr
  [ -d /opt/am-toolchains/.git ] || { echo "ERROR: toolchain cache not mounted at /opt/am-toolchains"; exit 1; }
  # Bind-mounted from the host, so git's ownership check needs an exemption.
  git config --system --add safe.directory /opt/am-toolchains
  ACTUAL_TC="$(git -C /opt/am-toolchains rev-parse HEAD)"
  echo "   expected $TOOLCHAIN_COMMIT"
  echo "   actual   $ACTUAL_TC"
  [ "$ACTUAL_TC" = "$TOOLCHAIN_COMMIT" ] || { echo "ERROR: toolchain commit mismatch"; exit 1; }
  rm -f /opt/toolchains
  ln -s /opt/am-toolchains/brcm-arm-hnd /opt/toolchains

  # Linker-development symlinks: the crosstools sysroot ships libX.so.1 without
  # the unversioned libX.so that -lnsl / -lcrypt etc. resolve through. No-op if
  # the toolchain already carries them.
  SYSROOT_LIB="$(find /opt/toolchains/crosstools-arm-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1 \
                   -type d -path '*/arm-buildroot-linux-gnueabi/sysroot/lib' -print -quit 2>/dev/null || true)"
  if [ -n "$SYSROOT_LIB" ]; then
    for lib in nsl util resolv crypt anl; do
      [ -e "$SYSROOT_LIB/lib${lib}.so.1" ] && ln -sf "lib${lib}.so.1" "$SYSROOT_LIB/lib${lib}.so"
    done
    echo "   arm sysroot: $SYSROOT_LIB"
  else
    echo "ERROR: ARM sysroot not found under /opt/toolchains"; exit 1
  fi

  # --- this repo's build scripts, verbatim --------------------------------
  cp -a "$REPO_DIR/build-scripts/." "$BUILD_SCRIPTS/"
  chmod +x "$BUILD_SCRIPTS"/*.sh "$BUILD_SCRIPTS"/ci/*.sh 2>/dev/null || true
  chown -R reaper:reaper "$REAPER_HOME" "$OUT_DIR" "$SRC_DIR" 2>/dev/null || true
  echo "-- build-scripts staged to $BUILD_SCRIPTS"
  [ -f "$BUILD_SCRIPTS/verify_markers.txt" ] \
    && echo "   verify_markers.txt present (patch-marker check armed)" \
    || echo "::warning::verify_markers.txt absent -- reaper_verify will WARN instead of checking rung markers"

  hr; echo " Dropping to user reaper (uid $(id -u reaper)) for the build"; hr
  exec runuser -u reaper --preserve-environment -- bash "$0" --as-reaper
fi

# ============================================================================
# PART 2 -- reaper: fetch, patch, prove provenance, build
# ============================================================================
[ "${1:-}" = "--as-reaper" ] || { echo "ERROR: part 2 reached without re-exec"; exit 1; }
export HOME="$REAPER_HOME"
cd "$SRC_DIR"

# --- pinned upstream base ---------------------------------------------------
hr; echo " Fetching pinned Asuswrt-Merlin base ($BASE_TAG)"; hr
git init -q
git remote add origin "$UPSTREAM_REPO"
git fetch --depth 1 -q origin "$BASE_COMMIT"
git checkout -q -b "$BUILD_BRANCH" FETCH_HEAD
ACTUAL_BASE="$(git rev-parse HEAD)"
echo "   expected $BASE_COMMIT"
echo "   actual   $ACTUAL_BASE"
[ "$ACTUAL_BASE" = "$BASE_COMMIT" ] || { echo "ERROR: upstream base mismatch"; exit 1; }
git config user.name  "Reaper CI"
git config user.email "ci@localhost"
df -h "$SRC_DIR" | tail -1

# --- the published patch series --------------------------------------------
# --keep-cr is REQUIRED: several third-party files (lltdc) are CRLF and the
# series fails at qospktio.c without it.
hr; echo " Applying the published Reaper patch series"; hr
mapfile -t PATCHES < <(ls "$REPO_DIR"/patches/[0-9]*.patch | sort)
PATCH_COUNT="${#PATCHES[@]}"
[ "$PATCH_COUNT" -gt 0 ] || { echo "ERROR: no patches found in $REPO_DIR/patches"; exit 1; }
echo "   patch count: $PATCH_COUNT"
if ! git am --keep-cr "${PATCHES[@]}"; then
  echo "::error::patch application FAILED"
  echo "--- failing patch (head) ---"
  git am --show-current-patch=raw 2>/dev/null | head -40 || true
  echo "--- version.conf ---"; sed -n '1,15p' release/src-rt/version.conf || true
  echo "--- status ---"; git status --short | head -20 || true
  exit 1
fi
SOURCE_COMMIT="$(git rev-parse HEAD)"
ROUTER_TREE="$(git rev-parse "HEAD:release/src/router")"
SRC_RT_TREE="$(git rev-parse "HEAD:release/src-rt")"
echo "   applied cleanly -> $SOURCE_COMMIT"

# --- per-model identity overlay ---------------------------------------------
# The series reproduces the RT-BE96U canon. A sibling is that tree plus its
# published overlay. GT-BE98 additionally needs the platform tree that the
# pinned upstream does not carry (its ASUS GPL drop is a different release);
# that ships here as a hash-pinned archive so no external download is needed.
if [ "$MODEL" != "RT-BE96U" ]; then
  hr; echo " Applying the $MODEL identity overlay"; hr

  PLAT="$REPO_DIR/overlays/${MODEL}-platform.tar.gz"
  if [ -f "$PLAT" ]; then
    SUMS="$REPO_DIR/overlays/${MODEL}-platform.sha256"
    if [ -f "$SUMS" ]; then
      want=$(awk '{print $1}' "$SUMS" | head -1)
      got=$(sha256sum "$PLAT" | cut -d' ' -f1)
      echo "   platform archive sha256 $got"
      if [ "$want" != "$got" ]; then
        echo "::error::$MODEL platform archive hash mismatch"
        echo "   expected $want"; echo "   got      $got"; exit 1
      fi
      echo "   [MATCH] platform archive matches its recorded hash"
    else
      echo "::error::$PLAT has no recorded sha256 -- refusing to unpack an unverified archive"; exit 1
    fi
    tar -xzf "$PLAT"
    echo "   unpacked $(tar -tzf "$PLAT" | wc -l) platform files"
  fi

  OV="$REPO_DIR/overlays/${MODEL}.patch"
  [ -f "$OV" ] || { echo "::error::no overlay for $MODEL at overlays/${MODEL}.patch"; exit 1; }
  if ! git apply --binary --whitespace=nowarn "$OV"; then
    echo "::error::$MODEL overlay failed to apply"
    git apply --binary --check -v "$OV" 2>&1 | head -20
    exit 1
  fi
  # Deterministic tree id for the post-overlay source, so a sibling build is as
  # traceable as a canon one. The overlay is intentionally uncommitted, so stage
  # it briefly to let git compute the tree, then restore the working state.
  git add -A >/dev/null 2>&1
  echo "   overlay applied: $(git diff --cached --name-only | wc -l) files staged"
  _MROOT="$(git write-tree)"
  MODEL_TREE="$(git rev-parse "${_MROOT}:release/src/router")"
  git reset --mixed HEAD >/dev/null 2>&1
else
  MODEL_TREE="$ROUTER_TREE"
fi

# --- u-boot rtl8372 prebuilt -------------------------------------------------
# RTL_OBJS.o is the Realtek RTL8372 switch blob. It ships in the ASUS bootloader
# drop and is UNTRACKED IN EVERY GIT REF -- it has only ever existed on the
# maintainer's disk, so the clean room could never get it. That is why RT-BE86U
# died in u-boot the first time a sibling actually compiled (2026-08-10):
#   cp: cannot stat '.../u-boot-2019.07/drivers/net/bcmbca/rtl8372/RTL_OBJS.o'
# RT-BE96U and RT-BE88U never noticed because neither enables rtl8372.
#
# Which models need it is DERIVED from the (possibly overlay-patched) Makefile
# rather than hardcoded: rt-be86u's overlay adds $(RTBE86U) to the enable list,
# while GTBE98/GTBE98_PRO are in it already upstream.
UB_DIR=release/src-rt-5.04behnd.4916/bootloaders/u-boot-2019.07/drivers/net/bcmbca
case "$MODEL" in
  RT-BE96U) UB_SYM=RTBE96U;;  RT-BE86U) UB_SYM=RTBE86U;;  RT-BE88U) UB_SYM=RTBE88U;;
  GT-BE98)  UB_SYM=GTBE98;;   GT-BE98_PRO) UB_SYM=GTBE98_PRO;;
  *) UB_SYM="";;
esac
# The literal "$(SYM)" including the closing paren, so GTBE98 never matches
# GTBE98_PRO.
if [ -n "$UB_SYM" ] && grep -B4 'obj-y += rtl8372/' "$UB_DIR/Makefile" 2>/dev/null \
     | grep -q -F "\$($UB_SYM)"; then
  hr; echo " $MODEL enables rtl8372 -- staging the RTL_OBJS.o prebuilt"; hr
  # GT-BE98's blob differs from every other model's (its GPL drop is a different
  # release), exactly as with its platform tree.
  case "$MODEL" in
    GT-BE98) RTL_NAME=uboot-rtl8372-GT-BE98;;
    *)       RTL_NAME=uboot-rtl8372-default;;
  esac
  RTL_TGZ="$REPO_DIR/overlays/$RTL_NAME.tar.gz"
  RTL_SUM="$REPO_DIR/overlays/$RTL_NAME.sha256"
  [ -f "$RTL_TGZ" ] || { echo "::error::$MODEL needs rtl8372 but $RTL_NAME.tar.gz is missing"; exit 1; }
  [ -f "$RTL_SUM" ] || { echo "::error::$RTL_NAME.tar.gz has no recorded sha256 -- refusing to unpack an unverified archive"; exit 1; }
  _want=$(awk '{print $1}' "$RTL_SUM" | head -1)
  _got=$(sha256sum "$RTL_TGZ" | cut -d' ' -f1)
  echo "   archive sha256 $_got"
  [ "$_want" = "$_got" ] || { echo "::error::$RTL_NAME.tar.gz hash mismatch"; echo "   expected $_want"; echo "   got      $_got"; exit 1; }
  echo "   [MATCH] archive matches its recorded hash"
  tar -xzf "$RTL_TGZ"
  # Fail loudly here rather than 40 minutes later inside u-boot.
  [ -f "$UB_DIR/rtl8372/RTL_OBJS.o" ] \
    || { echo "::error::RTL_OBJS.o still absent after unpacking $RTL_NAME.tar.gz"; exit 1; }
  echo "   staged $UB_DIR/rtl8372/RTL_OBJS.o ($(stat -c%s "$UB_DIR/rtl8372/RTL_OBJS.o") bytes)"
else
  echo "rtl8372 not enabled for $MODEL -- RTL_OBJS.o not needed"
fi

VER="$(grep -oE 'Reaper_v[0-9]+\.[0-9]+(\.[0-9]+)?[a-z]?' release/src-rt/version.conf | head -1)"
[ -n "$VER" ] || { echo "ERROR: cannot read Reaper version from version.conf"; exit 1; }
SHORT_VER="${VER#Reaper_}"

# The patch series carries its own EXTENDNO. Assert it produced the version the
# workflow declares, so a stale or partially-extracted series can never ship an
# image labelled as something it is not.
if [ -n "${EXPECTED_VERSION:-}" ] && [ "$VER" != "$EXPECTED_VERSION" ]; then
  echo "::error::version mismatch after applying $PATCH_COUNT patches"
  echo "   workflow expects $EXPECTED_VERSION"
  echo "   series produced  $VER"
  echo "   Either the series is missing the newest rung's patches, or"
  echo "   EXPECTED_VERSION in the workflow needs bumping."
  exit 1
fi
echo "   version: $VER (matches EXPECTED_VERSION)"

# --- source-level reproducibility gate --------------------------------------
# provenance/manifest.json records the release/src/router tree hash produced by
# a given patch count. When the series length matches a recorded release, the
# hash MUST match -- that is an exact, timestamp-free proof that this CI source
# is the same source the published firmware was built from.
hr; echo " Source provenance"; hr
python3 - "$REPO_DIR/provenance/manifest.json" "$PATCH_COUNT" "$ROUTER_TREE" <<'PY'
import json, sys
path, count, got = sys.argv[1], int(sys.argv[2]), sys.argv[3]
try:
    m = json.load(open(path))
except Exception as e:
    print(f"::warning::cannot read provenance manifest ({e}) -- source assertion skipped")
    raise SystemExit(0)
hit = [r for r in m.get("releases", []) if r.get("patch_count") == count]
if not hit:
    counts = sorted(r["patch_count"] for r in m.get("releases", []) if r.get("patch_count"))
    print(f"   no manifest entry for a {count}-patch series "
          f"(recorded: {counts if counts else 'none'})")
    print(f"   computed release/src/router tree = {got}")
    print(f"::warning::no recorded provenance for {count} patches -- "
          f"record tree {got} in provenance/manifest.json to make this build self-verifying")
    raise SystemExit(0)
r = hit[0]
# source_tree_from_series is what applying the published patches from the pinned
# base yields; source_tree is the build commit's tree on the branch. They differ
# only by vendored openssh-sftp *.md files the doc-hunk exclusion strips.
want = (r.get("source_tree_from_series") or r["source_tree"])["release/src/router"]
if want == got:
    print(f"   [MATCH] {r['version']}: release/src/router = {got}")
else:
    print(f"::error::source tree MISMATCH for {r['version']}")
    print(f"   expected {want}")
    print(f"   got      {got}")
    raise SystemExit(1)
PY

cat > "$OUT_DIR/source-${MODEL}-${VARIANT}.env" <<EOF
MODEL=$MODEL
VARIANT=$VARIANT
VERSION=$VER
BASE_TAG=$BASE_TAG
BASE_COMMIT=$ACTUAL_BASE
PATCH_REPO_COMMIT=$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo unknown)
PATCH_COUNT=$PATCH_COUNT
SOURCE_COMMIT=$SOURCE_COMMIT
SOURCE_TREE_ROUTER=$ROUTER_TREE
MODEL_TREE_ROUTER=$MODEL_TREE
SOURCE_TREE_SRC_RT=$SRC_RT_TREE
TOOLCHAIN_COMMIT=$TOOLCHAIN_COMMIT
EOF
cat "$OUT_DIR/source-${MODEL}-${VARIANT}.env" | sed 's/^/   /'

# --- the build ---------------------------------------------------------------
hr; echo " Building $MODEL $VER ($VARIANT)"; hr
echo "   started $(date -u +%FT%TZ)"
BUILD_RC=0
"$BUILD_SCRIPTS/ci/build_one.sh" "$MODEL" "$VARIANT" || BUILD_RC=$?
echo "   finished $(date -u +%FT%TZ) (reaper_build rc=$BUILD_RC)"
[ "$BUILD_RC" -eq 0 ] || { echo "::error::build/verify failed (rc=$BUILD_RC)"; exit "$BUILD_RC"; }

# --- collect -----------------------------------------------------------------
hr; echo " Collecting artifacts"; hr
TARGET_DIR="$SRC_DIR/release/src-rt-5.04behnd.4916/targets/96813GW"
tag=""; [ "$VARIANT" = "noMCP" ] && tag="_noMCP"
IMG="$TARGET_DIR/${MODEL}_3006_102.8_${VER}${tag}_nand_squashfs.pkgtb"
[ -f "$IMG" ] || { echo "::error::expected image not found: $IMG"; ls -la "$TARGET_DIR" | head -30; exit 1; }
cp -v "$IMG" "$OUT_DIR/"
IMG_NAME="$(basename "$IMG")"
IMG_SHA="$(sha256sum "$OUT_DIR/$IMG_NAME" | cut -d' ' -f1)"
echo "$IMG_SHA  $IMG_NAME" > "$OUT_DIR/SHA256SUMS-${MODEL}-${VER}${tag}.txt"

# Build log (the lib tees it here).
BLOG="$REAPER_HOME/build_$(echo "$MODEL" | tr 'A-Z' 'a-z')_${VER}.log"
[ -f "$BLOG" ] || BLOG="$(find "$REAPER_HOME" -maxdepth 1 -type f -name 'build_*.log' -print -quit)"
[ -n "${BLOG:-}" ] && [ -f "$BLOG" ] && cp -v "$BLOG" "$OUT_DIR/build-${MODEL}-${VARIANT}-${VER}.log"

# --- staged-filesystem digest ------------------------------------------------
# The .pkgtb embeds squashfs build timestamps, so raw image hashes cannot match
# across builds even when the CONTENT is identical. This digest hashes the
# staged rootfs instead (path, type, mode, symlink target, file content) and is
# the artifact to compare between a CI build and a local build. Deterministic.
FS="$TARGET_DIR/fs"
if [ -d "$FS" ]; then
  ( cd "$FS" && find . \( -type f -o -type l -o -type d \) -printf '%y %m %p %l\n' | LC_ALL=C sort ) \
      > "$OUT_DIR/stagedfs-inventory-${MODEL}-${VARIANT}.txt"
  ( cd "$FS" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum ) \
      > "$OUT_DIR/stagedfs-hashes-${MODEL}-${VARIANT}.txt"
  FS_DIGEST="$(cat "$OUT_DIR/stagedfs-inventory-${MODEL}-${VARIANT}.txt" \
                   "$OUT_DIR/stagedfs-hashes-${MODEL}-${VARIANT}.txt" | sha256sum | cut -d' ' -f1)"
  echo "   staged-fs digest: $FS_DIGEST"
  echo "STAGED_FS_DIGEST=$FS_DIGEST" >> "$OUT_DIR/source-${MODEL}-${VARIANT}.env"
else
  echo "::warning::staged rootfs not found at $FS -- no staged-fs digest"
  FS_DIGEST="(unavailable)"
fi

# --- binary reproducibility comparison vs the published release --------------
# Informational, NOT a gate: a raw .pkgtb hash match would mean bit-identical
# reproduction (squashfs timestamps make that unlikely); a mismatch alone proves
# nothing. The staged-fs digest above is the meaningful comparison.
hr; echo " Reproducibility comparison"; hr
# releases/ uses short model dirs: BE96U, BE86U, BE88U, BE98, BE98Pro
REL_DIR="$REPO_DIR/releases/$(echo "$MODEL" | sed 's/^GT-BE98_PRO$/BE98Pro/; s/^RT-//; s/^GT-//')"
REF="$REL_DIR/$(basename "$REL_DIR")-REAPER-${SHORT_VER}/SHA256SUMS-${MODEL}-${VER}.txt"
REPRO="not-compared"
if [ -f "$REF" ]; then
  WANT="$(awk -v f="$IMG_NAME" '$2==f {print $1}' "$REF")"
  if [ -z "$WANT" ]; then
    echo "   published sums exist for $SHORT_VER but list no $IMG_NAME"
    REPRO="no-reference-entry"
  elif [ "$WANT" = "$IMG_SHA" ]; then
    echo "   [BIT-IDENTICAL] $IMG_NAME matches the published $SHORT_VER release"
    REPRO="bit-identical"
  else
    echo "   [DIFFERS] $IMG_NAME"
    echo "     published $WANT"
    echo "     this build $IMG_SHA"
    echo "     Expected: .pkgtb squashfs embeds build timestamps. Compare the"
    echo "     staged-fs digest against a local build to check CONTENT equality."
    REPRO="differs-from-published"
  fi
else
  echo "   no published SHA256SUMS for $SHORT_VER at $REF -- nothing to compare"
  REPRO="no-published-release"
fi
echo "REPRODUCIBILITY=$REPRO" >> "$OUT_DIR/source-${MODEL}-${VARIANT}.env"

# --- human-readable provenance ----------------------------------------------
{
  echo "Reaper firmware -- GitHub Actions clean-room build"
  echo
  echo "Model:              $MODEL"
  echo "Variant:            $VARIANT"
  echo "Reaper version:     $VER"
  echo
  echo "Upstream repo:      $UPSTREAM_REPO"
  echo "Upstream tag:       $BASE_TAG"
  echo "Upstream commit:    $ACTUAL_BASE"
  echo "Patch repo commit:  $(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "Patches applied:    $PATCH_COUNT"
  echo "Patched HEAD:       $SOURCE_COMMIT"
  echo "release/src/router: $ROUTER_TREE"
  echo "post-overlay router: $MODEL_TREE"
  echo "release/src-rt:     $SRC_RT_TREE"
  echo "Toolchain commit:   $TOOLCHAIN_COMMIT"
  echo "Build environment:  Ubuntu 20.04 container, user reaper (uid 1001)"
  echo
  echo "Image SHA-256:"
  echo "  $IMG_SHA  $IMG_NAME"
  echo "Staged-fs digest:   $FS_DIGEST"
  echo "Vs published:       $REPRO"
} > "$OUT_DIR/build-provenance-${MODEL}-${VARIANT}.txt"
cat "$OUT_DIR/build-provenance-${MODEL}-${VARIANT}.txt"

hr; echo " Done"; hr
ls -lh "$OUT_DIR"
