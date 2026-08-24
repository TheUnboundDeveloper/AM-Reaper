#!/bin/bash
# ============================================================================
# port_sibling_v2.sh -- overlay-based, guarded port of be96u-only shared code
#                       onto a sibling model, PRESERVING per-model identity.
# ----------------------------------------------------------------------------
# v1.8.6 post-mortem: the old port did `git checkout be96u-only -- <whitelist>`
# (wholesale copy). It (1) CLOBBERED model-identity files sharing a name across
# models (REAPER1.png -> every sibling showed "RT-BE96U"; also version.conf),
# and (2) MISSED shared code outside the whitelist (SMB3, gkd, dropbear).
#
# Model:  sibling = be96u-only SHARED tree  +  small per-model IDENTITY OVERLAY
#   SHARED code : synced from be96u-only via the FULL diff (not a whitelist).
#   OVERLAY     : never taken from be96u; enforced from the authoritative source
#                 (banner <- reaper-mockups, target.mak SAMBA4 flag), and the
#                 banner now has a MODEL-UNIQUE FILENAME so a copy can't collide.
#   GUARDS      : abort if the wrong base / banner / config would land on a model.
#
# Usage:  port_sibling_v2.sh <MODEL> [--commit] [--version Reaper_vX.Y.Z]
#         default = DRY RUN (report only).  --commit performs sync + commit.
# ============================================================================
set -u
# The tree this port runs in. It used to be safe to hardcode: every model had its
# own WSL instance with its own branch checked out. Those four instances were
# deleted 2026-08-10, so a sibling port now runs in a `git worktree` created off
# the hub tip inside the canon instance - and that worktree is NOT this path.
# Override with REAPER_TREE=<worktree>; the default keeps the old single-tree use.
R=${REAPER_TREE:-/home/reaper/asuswrt-be96u}
# Identity art (per-model banner .png + animated _anim.png). Prefer the copy
# vendored in this repo at reaper-mockups/ -- that is the source of truth and the
# only one a clean checkout or a CI runner can see. Fall back to the developer's
# out-of-tree mockups folder when the scripts are deployed standalone to
# /home/reaper/reaper_build (where ../reaper-mockups does not exist).
_PSV_HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
if [ -d "$_PSV_HERE/../reaper-mockups" ]; then
  MOCK="$(cd "$_PSV_HERE/../reaper-mockups" && pwd)"
else
  . "$_PSV_HERE/_reaper_env.sh"          # WIN_ASUS_ROOT (override: export WINUSER)
  MOCK="$WIN_ASUS_ROOT/reaper-mockups"
fi
CANON=be96u-only
IMGDIR=release/src/router/www/images
TMAK_REL=release/src-rt/target.mak
VER_REL=release/src-rt/version.conf
# www files that reference the banner by name (get synced, then re-pointed)
BANNER_REFS=(release/src/router/www/Main_Login.asp
             release/src/router/www/Main_ReaperDash.asp
             release/src/router/www/reaper_shell.asp
             release/src/router/www/state.js
             release/src/router/www/Main_Password.asp
             release/src/router/www/Reaper_FirstBoot.asp
             release/src/router/www/Logout.asp)

MODEL="${1:-}"; shift 2>/dev/null || true
DO_COMMIT=0; SET_VER=""
while [ $# -gt 0 ]; do case "$1" in
  --commit) DO_COMMIT=1;; --version) shift; SET_VER="${1:-}";;
  *) echo "unknown arg: $1"; exit 2;; esac; shift; done
[ -z "$MODEL" ] && { echo "usage: port_sibling_v2.sh <MODEL> [--commit] [--version V]"; exit 2; }

# ---- per-model IDENTITY MANIFEST (source of truth for every guard) ----------
# BRANCH TARGET BANNER_FILE BANNER_SHA256 BUILD_NAME HAS6G QUAD
model_meta() {
  case "$1" in
  RT-BE96U)    BRANCH=be96u-only;  TARGET=rt-be96u;    BANNER_FILE=RT-96U_REAPER_Header.png; MP4_SRC="RT-BE96U Header Animation.mp4";
               BSHA=f2607d4fd490041bebde08fd526d28704083332eef97417e2d67cafd7bd68c7d; BUILD_NAME=RT-BE96U;    HAS6G=y; QUAD=n;;
  RT-BE86U)    BRANCH=rt-be86u;    TARGET=rt-be86u;    BANNER_FILE=RT-BE86U_REAPER_Header.png; MP4_SRC="RT-BE86U Header Animation.mp4";
               BSHA=643036d89ca249311eec964035d973a6eeaaec38d5c9ec1ecd47f33298c28ece; BUILD_NAME=RT-BE86U;    HAS6G=n; QUAD=n;;
  RT-BE88U)    BRANCH=rt-be88u;    TARGET=rt-be88u;    BANNER_FILE=RT-BE88U_REAPER_Header.png; MP4_SRC="RT-BE88U Header Animation.mp4";
               BSHA=a46320ea1abf53eb4212eb02b1682ed80a91a129f0c7d1ced6a836d832817f27; BUILD_NAME=RT-BE88U;    HAS6G=n; QUAD=n;;
  GT-BE98)     BRANCH=gt-be98;     TARGET=gt-be98;     BANNER_FILE=GT-BE98_REAPER_Header.png; MP4_SRC="GT-BE98 Header Animation.mp4";
               BSHA=0df4d8c19c9f044a1c2eb8334d2b23d085ff8f090348177251d1518b49572108; BUILD_NAME=GT-BE98;     HAS6G=y; QUAD=y;;
  GT-BE98_PRO) BRANCH=gt-be98-pro; TARGET=gt-be98_pro; BANNER_FILE=GT-BE98P_REAPER_Header.png; MP4_SRC="GT-BE98P Header Animation.mp4";
               BSHA=277f468046f99abda5d15181700ee150cd56ab0d258e7495090b8128d08fc08b; BUILD_NAME=GT-BE98_PRO; HAS6G=y; QUAD=y;;
  RT-BE92U)    BRANCH=rt-be92u;    TARGET=rt-be92u;    BANNER_FILE=RT-BE92U_REAPER_Header.png; MP4_SRC="RT-BE92U Header Animation.mp4";
               BSHA=032fc64c249e10391c12041cde1dd6f1d9d9bf8349495f79a09ba36e77d6db72; BUILD_NAME=RT-BE92U;    HAS6G=y; QUAD=n;;
  *) return 1;; esac
}
# RT-BE92U (BCM6765, 96765GW profile) is a Tier-A sibling whose banner is a
# PLACEHOLDER generated from the RT-BE96U art (sha 032fc64c) until the owner
# supplies real BE92U banner art - re-checksum here when that lands.
ALL_MODELS="RT-BE96U RT-BE86U RT-BE88U GT-BE98 GT-BE98_PRO RT-BE92U"
model_meta "$MODEL" || { echo "FATAL: unknown model '$MODEL' (valid: $ALL_MODELS)"; exit 2; }
BANNER_REL="$IMGDIR/$BANNER_FILE"
ANIM_FILE="${BANNER_FILE%.png}_anim.png"; ANIM_REL="$IMGDIR/$ANIM_FILE"

cd "$R" || { echo "FATAL: no repo at $R"; exit 2; }
FAIL=0; die(){ echo "  [GUARD-FAIL] $*"; FAIL=1; }; ok(){ echo "  [ok] $*"; }; note(){ echo "  [..] $*"; }
refsha(){ git rev-parse "$1:$2" 2>/dev/null; }

echo "############################################################"
echo "# port_sibling_v2  MODEL=$MODEL  BRANCH=$BRANCH  banner=$BANNER_FILE  ($([ $DO_COMMIT = 1 ] && echo COMMIT || echo DRY-RUN))"
echo "############################################################"

# =================== PREFLIGHT GUARDS =======================================
echo "== preflight guards =="
CUR=$(git rev-parse --abbrev-ref HEAD)
[ "$CUR" = "$BRANCH" ] && ok "on branch $BRANCH" || die "on '$CUR' but $MODEL builds on '$BRANCH'"
git show "$BRANCH:$TMAK_REL" 2>/dev/null | grep -qE "^export ${MODEL} :=|^export ${MODEL} \+=" \
  && ok "target.mak has 'export $MODEL' block" || die "target.mak has NO 'export $MODEL' block"
git show "$BRANCH:$TMAK_REL" 2>/dev/null | grep -qE "BUILD_NAME=\"?${MODEL}\"?" \
  && ok "target.mak sets BUILD_NAME=$MODEL" || die "target.mak missing BUILD_NAME=$MODEL"
{ [ -d "$R/release/src-rt-5.04behnd.4916/router-sysdep.${TARGET}" ] || \
  git show "$BRANCH:release/src-rt-5.04behnd.4916/router-sysdep.${TARGET}/Makefile" >/dev/null 2>&1; } \
  && ok "base: router-sysdep.${TARGET} present" || die "base: router-sysdep.${TARGET} MISSING (wrong base package)"
S6=$(git show "$BRANCH:$TMAK_REL" 2>/dev/null | sed -n "/^export ${MODEL} /,/^$/p" | grep -c "HAS_6G=y")
if [ "$HAS6G" = y ] && [ "$S6" -ge 1 ]; then ok "band: HAS_6G=y matches $MODEL"
elif [ "$HAS6G" = n ] && [ "$S6" -eq 0 ]; then ok "band: no HAS_6G matches $MODEL"
else die "band: HAS_6G ($S6) contradicts manifest ($HAS6G)"; fi
# GUARD: the model's own banner file exists on the branch (post-rename identity)
[ -n "$(refsha "$BRANCH" "$BANNER_REL")" ] && ok "banner file $BANNER_FILE present on branch" \
  || die "banner $BANNER_FILE not on branch (rename not applied?)"
[ "$FAIL" = 1 ] && { echo; echo "ABORT: preflight guards failed -- refusing to touch $MODEL"; exit 1; }

# =================== OVERLAY / PROTECT SET ==================================
# Classification rules live in _port_protect.sh -- the SINGLE SOURCE shared
# with reaper_verify.sh's shared-parity check. Do not redefine rules here.
. /home/reaper/reaper_build/_port_protect.sh
PROTECT_RE="$PP_PROTECT_RE"
is_protected(){ [ "$(pp_classify "$1")" = 0 ]; }

echo "== compute shared-vs-overlay split ($MODEL vs $CANON) =="
mapfile -t DIFFS < <(git diff --name-only "$CANON" "$BRANCH" 2>/dev/null)
SYNC=(); PROT=()
for f in "${DIFFS[@]}"; do
  if is_protected "$f"; then PROT+=("$f")
  elif git cat-file -e "$CANON:$f" 2>/dev/null; then SYNC+=("$f")
  else PROT+=("$f (model-only)"); fi
done
echo "  SHARED to sync from $CANON : ${#SYNC[@]}"
echo "  OVERLAY protected          : ${#PROT[@]}"
printf '%s\n' "${PROT[@]}" | grep -vE "$PROTECT_RE" | sed 's/^/     keep /' | head -20

if [ "$DO_COMMIT" = 0 ]; then
  echo; echo "== DRY-RUN: would sync ${#SYNC[@]} shared files, protect ${#PROT[@]}, enforce banner+refs+target.mak+version =="
  echo "   re-run with --commit to apply"; echo "== running guards against current branch state only =="
fi

# =================== APPLY ==================================================
if [ "$DO_COMMIT" = 1 ]; then
  echo "== sync shared code from $CANON =="
  n=0; for f in "${SYNC[@]}"; do git checkout "$CANON" -- "$f" 2>/dev/null && n=$((n+1)); done
  echo "  synced $n/${#SYNC[@]} shared files"

  echo "== enforce IDENTITY OVERLAY =="
  # 1) authoritative banner content, model-unique filename
  cp "$MOCK/$BANNER_FILE" "$R/$BANNER_REL" || die "cannot copy banner $BANNER_FILE"
  # per-model animated header APNG (same per-model discipline as the banner .png)
  cp "$MOCK/$ANIM_FILE" "$R/$ANIM_REL" || die "cannot copy header APNG $ANIM_FILE"
  # 2) remove any FOREIGN model banner that a sync may have introduced
  for stray in "$R/$IMGDIR"/*_REAPER_Header.png; do
    [ -e "$stray" ] || continue
    [ "$(basename "$stray")" = "$BANNER_FILE" ] && continue
    note "removing foreign banner $(basename "$stray")"; git rm -q -f --ignore-unmatch "$stray" 2>/dev/null || rm -f "$stray"
  done
  for stray in "$R/$IMGDIR"/*_REAPER_Header_anim.png; do
    [ -e "$stray" ] || continue
    [ "$(basename "$stray")" = "$ANIM_FILE" ] && continue
    note "removing foreign header APNG $(basename "$stray")"; git rm -q -f --ignore-unmatch "$stray" 2>/dev/null || rm -f "$stray"
  done
  # header is an APNG now -- purge any stale per-model .mp4 (v2.2.9-era leftover)
  for stray in "$R/$IMGDIR"/*_REAPER_Header.mp4; do
    [ -e "$stray" ] || continue
    note "removing stale header mp4 $(basename "$stray")"; git rm -q -f --ignore-unmatch "$stray" 2>/dev/null || rm -f "$stray"
  done
  # 3) re-point every banner reference at THIS model's filename (files were synced from be96u)
  for rf in "${BANNER_REFS[@]}"; do
    [ -e "$R/$rf" ] || continue
    sed -i "s#[A-Za-z0-9_-]*_REAPER_Header_anim\.png#$ANIM_FILE#g; s#[A-Za-z0-9_-]*_REAPER_Header\.png#$BANNER_FILE#g; s#REAPER1\.png#$BANNER_FILE#g" "$R/$rf"
  done
  # 4) target.mak: keep model block; ensure SAMBA4 override present
  if ! sed -n "/^export ${MODEL} /,/^$/p" "$R/$TMAK_REL" | grep -q "SAMBA4=y"; then
    note "target.mak: adding SAMBA4 override to $MODEL block"
    awk -v m="$MODEL" '{print} $0 ~ ("^export " m " \\+=") {inb=1}
      inb && $0 !~ /\\[[:space:]]*$/ {print ""; print "export " m " += SAMBA4=y SAMBA3="; inb=0}' \
      "$R/$TMAK_REL" > "$R/$TMAK_REL.new" && mv "$R/$TMAK_REL.new" "$R/$TMAK_REL"
  fi
  # 5) version
  [ -n "$SET_VER" ] && sed -i "s/^EXTENDNO=.*/EXTENDNO=${SET_VER}/" "$R/$VER_REL"
fi

# =================== POSTFLIGHT GUARDS ======================================
echo "== postflight guards =="
# banner content == THIS model's; and NOT any other model's (wrong-png reject)
CHK=$([ "$DO_COMMIT" = 1 ] && sha256sum "$R/$BANNER_REL" 2>/dev/null | cut -d' ' -f1 \
      || git show "$BRANCH:$BANNER_REL" 2>/dev/null | sha256sum | cut -d' ' -f1)
if [ "$CHK" = "$BSHA" ]; then ok "banner $BANNER_FILE = correct $MODEL content"
else
  wrong=""; for m in $ALL_MODELS; do ( model_meta "$m"; [ "$CHK" = "$BSHA" ] && printf '%s ' "$m" ); done >/tmp/pv_w 2>/dev/null
  wrong=$(cat /tmp/pv_w 2>/dev/null)
  die "banner content ${CHK:0:12} does NOT match $MODEL${wrong:+ (matches model [$wrong] -- WRONG-PNG)}"
fi
# exactly ONE banner file present, and it is THIS model's
if [ "$DO_COMMIT" = 1 ]; then
  cnt=$(ls "$R/$IMGDIR"/*_REAPER_Header.png 2>/dev/null | wc -l)
  [ "$cnt" = 1 ] && ok "exactly one banner file staged ($BANNER_FILE)" || die "$cnt banner files present (foreign banner leak)"
fi
# every banner reference points at THIS model's file (no stale/foreign ref)
badref=0
for rf in "${BANNER_REFS[@]}"; do
  c=$([ "$DO_COMMIT" = 1 ] && cat "$R/$rf" 2>/dev/null || git show "$BRANCH:$rf" 2>/dev/null)
  echo "$c" | grep -qE "_REAPER_Header\.png" || continue
  if echo "$c" | grep -oE "[A-Za-z0-9_-]*_REAPER_Header\.png" | grep -qv "^$BANNER_FILE\$"; then badref=1; fi
done
[ "$badref" = 0 ] && ok "all banner references point at $BANNER_FILE" || die "a banner reference points at a FOREIGN banner"
# target.mak identity intact
TM=$([ "$DO_COMMIT" = 1 ] && cat "$R/$TMAK_REL" || git show "$BRANCH:$TMAK_REL")
echo "$TM" | grep -qE "BUILD_NAME=\"?${MODEL}\"?" && ok "target.mak still BUILD_NAME=$MODEL" || die "target.mak lost BUILD_NAME=$MODEL"
echo "$TM" | sed -n "/^export ${MODEL} /,/^\$/p" | grep -q "SAMBA4=y" && ok "target.mak $MODEL block has SAMBA4" || die "target.mak $MODEL block missing SAMBA4"

[ "$FAIL" = 1 ] && { echo; echo "ABORT: postflight guard failed."; [ "$DO_COMMIT" = 1 ] && echo "  tree modified but NOT committed -- inspect/reset."; exit 1; }

# =================== COMMIT =================================================
if [ "$DO_COMMIT" = 1 ]; then
  # stage ONLY the files this port touched -- never `git add -A` (the tree is
  # full of untracked build artifacts that must not enter the commit).
  git add -- "$BANNER_REL" "$ANIM_REL" "$TMAK_REL" "$VER_REL" "${BANNER_REFS[@]}" 2>/dev/null
  [ "${#SYNC[@]}" -gt 0 ] && git add -- "${SYNC[@]}" 2>/dev/null
  git diff --cached --quiet && { echo "== no changes (already in sync) =="; exit 0; }
  git commit -q -m "$BRANCH: overlay-port shared code from $CANON (guarded)

Sync ${#SYNC[@]} shared files from $CANON; preserve $MODEL identity overlay
(model-unique banner $BANNER_FILE, target.mak block + SAMBA4, version.conf,
model www/blobs). Guards: banner==$MODEL (rejects foreign), one banner file,
refs point at it, BUILD_NAME=$MODEL, base router-sysdep.${TARGET}, HAS_6G=$HAS6G.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  # post-commit residual assertion: after a port, ZERO shared files may still
  # differ from canon (catches partial checkouts / classifier drift AT THE PORT)
  resid=$(pp_parity_check "$CANON" HEAD)
  if [ -n "$resid" ]; then
    echo "$resid" | sed 's/^/     /'
    echo "ABORT: port committed but a shared residual remains -- fix before building."
    exit 1
  fi
  echo "  [ok] post-commit parity: 0 unsynced shared files vs $CANON"
  echo "== committed $(git rev-parse --short HEAD) on $BRANCH =="
  echo "   NEXT: build_${TARGET}.sh  ->  reaper_verify re-checks banner/model-id/samba on the image"
fi
echo "== port_sibling_v2 $MODEL: all guards passed =="
exit 0
