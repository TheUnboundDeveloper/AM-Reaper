#!/bin/bash
# ============================================================================
# reaper_verify.sh  --  deep post-build QA gate for Reaper firmware
# ----------------------------------------------------------------------------
# Inspects the STAGED rootfs + the packed image and fails loudly on the classes
# of defect that shipped undetected in v1.8.6 (Samba flag miss, mispackaged /
# stale www, missing shared libs, wrong-model identity, MCP/noMCP leakage).
#
# Usage:  reaper_verify.sh MODEL VARIANT VERSION [FS_DIR] [IMAGE]
#   MODEL    e.g. RT-BE86U | RT-BE96U | RT-BE88U | GT-BE98 | GT-BE98_PRO
#   VARIANT  MCP | noMCP
#   VERSION  e.g. Reaper_v1.8.6
#   FS_DIR   staged rootfs (default: targets/96813GW/fs)
#   IMAGE    packed pkgtb   (default: derived nand main image in target dir)
#
# Exit: 0 = all checks PASS (WARN allowed), non-zero = one or more FAIL.
# Prints one line per check: [PASS]/[FAIL]/[WARN] <check> -- <detail>
# ============================================================================

case "${1:-}" in
  -h|--help) sed -n "2,18 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
set -u
MODEL="${1:?MODEL}"; VARIANT="${2:?VARIANT}"; VERSION="${3:?VERSION}"
# REAPER_TREE / REAPER_TDIR let a sibling that builds in a worktree and/or to a
# different target profile be verified in place. Defaults keep the 5 canon-tree
# models (96813GW) unchanged; RT-BE92U sets REAPER_TREE=/home/reaper/port/rt-be92u
# and REAPER_TDIR=.../targets/96765GW (build_be92u.sh exports both).
R=${REAPER_TREE:-/home/reaper/asuswrt-be96u}
P=$R/release/src-rt-5.04behnd.4916
TDIR=${REAPER_TDIR:-$P/targets/96813GW}
FS="${4:-$TDIR/fs}"
tag=""; [ "$VARIANT" = "noMCP" ] && tag="_noMCP"
IMAGE="${5:-$TDIR/${MODEL}_3006_102.8_${VERSION}${tag}_nand_squashfs.pkgtb}"
RCONF="$R/release/src/router/.config"

FAILN=0; WARNN=0; PASSN=0
pass(){ echo "[PASS] $1 -- $2"; PASSN=$((PASSN+1)); }
warn(){ echo "[WARN] $1 -- $2"; WARNN=$((WARNN+1)); }
fail(){ echo "[FAIL] $1 -- $2"; FAILN=$((FAILN+1)); }

echo "================ reaper_verify: $MODEL $VARIANT $VERSION ================"
echo "fs=$FS"
echo "image=$IMAGE"
[ -d "$FS" ] || { fail "staged-fs" "missing dir $FS"; echo "ABORT"; exit 2; }

READELF=$(command -v readelf || echo readelf)

# ---- 1. core binaries present + non-empty + ARM ELF ------------------------
check_elf(){ # $1 path-in-fs  $2 label  $3 required(1/0)
  local f="$FS/$1"
  if [ ! -e "$f" ]; then
    [ "$3" = 1 ] && fail "bin:$2" "MISSING $1" || warn "bin:$2" "absent $1"
    return
  fi
  [ -s "$f" ] || { fail "bin:$2" "zero-size $1"; return; }
  local m; m=$($READELF -h "$f" 2>/dev/null | awk -F: '/Machine:/{print $2}' | xargs)
  case "$m" in
    *ARM*) pass "bin:$2" "$1 ($(stat -c%s "$f")B, $m)";;
    "")    warn "bin:$2" "not ELF? $1";;
    *)     fail "bin:$2" "wrong arch $m for $1";;
  esac
}
check_elf usr/sbin/httpd httpd 1
check_elf usr/sbin/smbd  smbd  1
check_elf usr/sbin/nmbd  nmbd  1
check_elf usr/sbin/wl     wl    0

# ---- 2. httpd shared-lib link closure (every NEEDED .so exists in rootfs) --
if [ -e "$FS/usr/sbin/httpd" ]; then
  miss=""
  for so in $($READELF -d "$FS/usr/sbin/httpd" 2>/dev/null | awk -F'[][]' '/NEEDED/{print $2}'); do
    found=$(find "$FS"/lib "$FS"/usr/lib -name "$so" 2>/dev/null | head -1)
    [ -z "$found" ] && miss="$miss $so"
  done
  if [ -n "$miss" ]; then fail "httpd-link" "missing NEEDED libs:$miss"
  else pass "httpd-link" "all NEEDED libs resolve in rootfs"; fi
fi

# ---- 3. Samba flag <-> staged binaries consistency -------------------------
CFG_S4=$(grep -c '^RTCONFIG_SAMBA4=y' "$RCONF" 2>/dev/null)
CFG_S36=$(grep -c '^RTCONFIG_SAMBA36X=y' "$RCONF" 2>/dev/null)
S4LIBS=$(find "$FS"/usr/lib/samba -name '*-samba4.so' 2>/dev/null | head -1)
ICONV=$(find "$FS"/usr/lib -name 'libiconv*' 2>/dev/null | head -1)
if [ "${CFG_S4:-0}" -ge 1 ]; then
  [ -n "$S4LIBS" ] && pass "samba" "SAMBA4 config + samba4 libs staged" || fail "samba" "SAMBA4 in .config but NO *-samba4.so staged"
  [ -z "$ICONV" ] && pass "samba-iconv" "no libiconv (correct for SAMBA4)" || warn "samba-iconv" "libiconv present under SAMBA4: $ICONV"
elif [ "${CFG_S36:-0}" -ge 1 ]; then
  fail "samba" "built SAMBA36X (old Samba 3.6.x) -- expected SAMBA4 for Reaper parity"
else
  warn "samba" "neither SAMBA4 nor SAMBA36X set in .config (check)"
fi

# ---- 3b. smbd link closure -- catches the v2.0.0 bug: samba4 private libs live
#          in /usr/lib/samba (non-default path) and smbd carries no RUNPATH, so they
#          are only reachable because reaper adds /usr/lib/samba to /etc/ld.so.conf.
#          Verify BOTH that every NEEDED lib is staged AND that the dir is registered.
if [ -e "$FS/usr/sbin/smbd" ]; then
  miss=""
  for so in $($READELF -d "$FS/usr/sbin/smbd" 2>/dev/null | awk -F'[][]' '/NEEDED/{print $2}'); do
    found=$(find "$FS"/lib "$FS"/usr/lib "$FS"/usr/lib/samba -name "$so" 2>/dev/null | head -1)
    [ -z "$found" ] && miss="$miss $so"
  done
  reg=0; grep -qx '/usr/lib/samba' "$FS"/rom/etc/ld.so.conf 2>/dev/null && reg=1
  if [ -n "$miss" ]; then fail "smbd-link" "missing NEEDED libs:$miss"
  elif [ "$reg" != 1 ]; then fail "smbd-link" "libs staged but /usr/lib/samba NOT in ld.so.conf -- smbd cannot load them at runtime (v2.0.0 regression)"
  else pass "smbd-link" "all NEEDED libs resolve + /usr/lib/samba registered in ld.so.conf"; fi
fi

# ---- 4. MCP / noMCP correctness --------------------------------------------
RMCPD=$(find "$FS" -name rmcpd 2>/dev/null | head -1)
ADV=$(find "$FS"/www -name 'Reaper_Advisor.asp' 2>/dev/null | head -1)
if [ "$VARIANT" = "noMCP" ]; then
  { [ -z "$RMCPD" ] && [ -z "$ADV" ]; } && pass "mcp" "noMCP: no rmcpd / Reaper_Advisor.asp (clean)" \
    || fail "mcp" "noMCP but MCP artifacts present: ${RMCPD:-} ${ADV:-}"
else
  { [ -n "$RMCPD" ] && [ -n "$ADV" ]; } && pass "mcp" "MCP: rmcpd + Reaper_Advisor.asp present" \
    || warn "mcp" "MCP but missing rmcpd/Advisor: rmcpd=${RMCPD:-none} adv=${ADV:-none}"
fi

# ---- 5. www presence + integrity (build transforms www; no source-sha) -----
# NOTE: the build post-processes .asp during packing (packed != git source),
# so a source sha-compare gives false positives. Check presence, non-trivial
# size, and expected content markers (survive the transform) instead.
critical="index.asp Main_ReaperDash.asp Advanced_VPNStatus.asp Reaper_Warden.asp"
missp=""; smallp=""
for w in $critical; do
  f="$FS/www/$w"
  [ -e "$f" ] || { missp="$missp $w"; continue; }
  [ "$(stat -c%s "$f" 2>/dev/null || echo 0)" -lt 200 ] && smallp="$smallp $w"
done
[ -z "$missp" ] && pass "www-present" "critical pages present" || fail "www-present" "missing:$missp"
[ -z "$smallp" ] && pass "www-size" "critical pages non-trivial size" || fail "www-size" "truncated/empty:$smallp"
if grep -qa "VPN" "$FS/www/Advanced_VPNStatus.asp" 2>/dev/null && grep -qai "warden" "$FS/www/Reaper_Warden.asp" 2>/dev/null; then
  pass "www-marker" "key pages contain expected content"
else warn "www-marker" "expected content markers missing (inspect pages)"; fi

# ---- 6. i18n dict lockstep (token counts equal across languages) -----------
DDIR=""
for d in "$FS/www/dict" "$FS/www"; do [ -d "$d" ] && ls "$d"/*.dict >/dev/null 2>&1 && { DDIR="$d"; break; }; done
if [ -n "$DDIR" ]; then
  counts=$(for f in "$DDIR"/*.dict; do wc -l < "$f" 2>/dev/null; done | sort -un | tr '\n' ' ')
  n=$(echo "$counts" | wc -w)
  [ "$n" -le 1 ] && pass "i18n-dict" "all dicts lockstep ($counts lines)" || warn "i18n-dict" "dict LINE counts DIFFER across langs: $counts"
else
  warn "i18n-dict" "no *.dict found under www (mechanism may differ)"
fi

# ---- 7. model identity in the packed image ---------------------------------
if [ -f "$IMAGE" ]; then
  # authoritative identity = the FIT description (u-boot image tree), not raw
  # strings (the shared CLM board-table + model.c enum list every model).
  fitmodel=$(dumpimage -l "$IMAGE" 2>/dev/null | grep -iE 'FIT description' | head -1 | sed -E 's/.*:[[:space:]]*//' | xargs)
  if [ -n "$fitmodel" ]; then
    [ "$fitmodel" = "$MODEL" ] && pass "model-id" "FIT description=$fitmodel matches target" \
      || fail "model-id" "FIT description=$fitmodel != target $MODEL (WRONG-MODEL BUILD)"
  else warn "model-id" "could not read FIT description from image"; fi
else
  warn "image" "packed image not found: $IMAGE"
fi

# ---- 8. model-branded header banner (model-UNIQUE filename) matches model ---
# Post-v1.8.6: each model has its own banner filename (clobber-proof). Verify
# the right file, right content, and NO stale REAPER1.png / foreign banner.
case "$MODEL" in
  RT-BE96U)    want_ban=f2607d4fd490041bebde08fd526d28704083332eef97417e2d67cafd7bd68c7d; ban_file=RT-96U_REAPER_Header.png;;
  RT-BE86U)    want_ban=643036d89ca249311eec964035d973a6eeaaec38d5c9ec1ecd47f33298c28ece; ban_file=RT-BE86U_REAPER_Header.png;;
  RT-BE88U)    want_ban=a46320ea1abf53eb4212eb02b1682ed80a91a129f0c7d1ced6a836d832817f27; ban_file=RT-BE88U_REAPER_Header.png;;
  GT-BE98)     want_ban=0df4d8c19c9f044a1c2eb8334d2b23d085ff8f090348177251d1518b49572108; ban_file=GT-BE98_REAPER_Header.png;;
  GT-BE98_PRO) want_ban=277f468046f99abda5d15181700ee150cd56ab0d258e7495090b8128d08fc08b; ban_file=GT-BE98P_REAPER_Header.png;;
  RT-BE92U)    want_ban=032fc64c249e10391c12041cde1dd6f1d9d9bf8349495f79a09ba36e77d6db72; ban_file=RT-BE92U_REAPER_Header.png;;
  *)           want_ban=""; ban_file="";;
esac
BAN="$FS/www/images/$ban_file"
if [ -n "$want_ban" ] && [ -f "$BAN" ]; then
  got_ban=$(sha256sum "$BAN" 2>/dev/null | cut -d' ' -f1)
  [ "$got_ban" = "$want_ban" ] && pass "header-banner" "$ban_file = correct $MODEL banner" \
    || fail "header-banner" "WRONG banner content for $MODEL ($ban_file got ${got_ban:0:12}, want ${want_ban:0:12})"
elif [ -n "$ban_file" ]; then fail "header-banner" "model banner $ban_file NOT staged"
else warn "header-banner" "no expected banner registered for $MODEL"; fi
# guard: no legacy shared-name file, no foreign model banner
if [ -f "$FS/www/images/REAPER1.png" ]; then fail "banner-stale" "legacy REAPER1.png still staged (rename regression)"; fi
foreign=$(ls "$FS"/www/images/*_REAPER_Header.png 2>/dev/null | grep -v "/${ban_file}\$")
if [ -n "$foreign" ]; then fail "banner-foreign" "foreign banner staged: $(echo "$foreign" | xargs -n1 basename 2>/dev/null | tr '\n' ' ')"
else pass "banner-solo" "only $MODEL banner present (no foreign/legacy)"; fi

# ---- 9. shared-code parity vs canon (the /sysdep/ lesson, 2026-08-05) ------
# Every SHARED file must match canon (be96u-only) at build time; per-model
# overlay files are skipped and the four banner-ref pages compare with the
# model banner filename normalized. Classifier = _port_protect.sh (the SAME
# rules the port uses -- if they disagree, gaps ship silently).
if [ -f /home/reaper/reaper_build/_port_protect.sh ]; then
  . /home/reaper/reaper_build/_port_protect.sh
  CANON_REF=be96u-only
  if git -C "$R" rev-parse --verify -q "$CANON_REF" >/dev/null 2>&1; then
    HEADB=$(git -C "$R" rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ "$HEADB" = "$CANON_REF" ]; then
      pass "shared-parity" "build branch IS canon ($CANON_REF)"
    else
      plist=$(cd "$R" && pp_parity_check "$CANON_REF" HEAD)
      if [ -z "$plist" ]; then
        pass "shared-parity" "0 unsynced shared files vs canon $(git -C "$R" rev-parse --short "$CANON_REF")"
      else
        echo "$plist" | sed 's/^/    /'
        fail "shared-parity" "shared files differ from canon (PORT GAP) -- see list"
      fi
    fi
  else warn "shared-parity" "no local canon ref $CANON_REF"; fi
else warn "shared-parity" "_port_protect.sh not deployed -- parity unchecked"; fi

# ---- 10. rung-critical patch markers in the STAGED image -------------------
# verify_markers.txt lines: <staged-path>|<literal>|<min>  or  <staged-path>|!<literal>
# One line per field-critical fix -> every model/variant image PROVES it ships.
MARKF=/home/reaper/reaper_build/verify_markers.txt
if [ -f "$MARKF" ]; then
  mfail=0; mnum=0
  while IFS='|' read -r mpath mpat mmin; do
    case "$mpath" in ''|'#'*) continue;; esac
    mnum=$((mnum+1))
    tgt="$FS/$mpath"
    if [ ! -f "$tgt" ]; then fail "patch-marker" "$mpath MISSING from staged fs"; mfail=1; continue; fi
    case "$mpat" in
      '!'*) c=$(grep -aFc -- "${mpat#!}" "$tgt" 2>/dev/null); c=${c:-0}
            [ "$c" -eq 0 ] || { fail "patch-marker" "$mpath: FORBIDDEN '${mpat#!}' present x$c"; mfail=1; };;
      *)    c=$(grep -aFc -- "$mpat" "$tgt" 2>/dev/null); c=${c:-0}
            [ "$c" -ge "${mmin:-1}" ] || { fail "patch-marker" "$mpath: '$mpat' x$c < ${mmin:-1}"; mfail=1; };;
    esac
  done < "$MARKF"
  [ "$mfail" = 0 ] && pass "patch-markers" "$mnum marker rules hold in the staged fs"
else
  warn "patch-markers" "verify_markers.txt missing -- no rung markers checked"
fi

# ---- 17. de-cloud: no ASUS-CDN REQUEST may ship (backlog [P3], 2026-08-11) --
# The v2.3.3 sweep removed every browser->ASUS request from the files that ship
# on this model. What it could not do is stop a FUTURE model from reintroducing
# them: www/Makefile copies sysdep/FUNCTION/{ROG_UI,TUF_UI,UI4,GS_UI} over the
# staged www whenever the matching RTCONFIG flag is y, and those overlays still
# carry ~133 ASUS URLs. No model in this tree sets those flags today - so rather
# than sweep dead source, this gate FAILS THE BUILD the moment such a reference
# reaches the staged www in a request-shaped position.
# Deliberately NOT flagged: plain href / openLink / window.open links to ASUS
# support pages. Those are user-initiated navigation, not a silent callback, and
# the shipped stock pages carry ~170 of them.
decloud_hits=$(grep -rlnE \
  "(fetch\(|XMLHttpRequest|\.ajax\(|getJSON\(|new Image\(|\.src[[:space:]]*=|<script[^>]+src=|<img[^>]+src=|<link[^>]+href=).*https?://[a-z0-9.-]*(asus|dlcdnet)" \
  "$FS/www" 2>/dev/null | head -20)
if [ -n "$decloud_hits" ]; then
  echo "$decloud_hits" | sed 's/^/    /'
  fail "de-cloud" "staged www makes an ASUS-CDN request (files above)"
else
  pass "de-cloud" "no ASUS-CDN request in the staged www"
fi

# ---- summary ---------------------------------------------------------------
echo "------------------------------------------------------------"
# ---- 16. i18n quote-context safety (reaper-ui rule 29) ---------------------
if out=$(python3 /home/reaper/reaper_build/reaper_langcheck.py "$FS/www" 2>&1); then
  pass "i18n-quote" "no language can break a JS string in reaper www ($(echo "$out" | tail -1))"
else
  echo "$out" | sed 's/^/    /'
  fail "i18n-quote" "dict token embedded in a breakable JS string context (see above)"
fi

# ---- 18. provenance stamp: the About page's patch count must be REAL -------
# Stamping is deliberately non-fatal, and for three releases nothing downstream
# ever looked at the result - so a stale 465 shipped through v2.5.8, a dash in
# v2.7.6, and a wrong figure again in v2.7.7. This is that look. It catches an
# empty/non-numeric count, a count that disagrees with the tree being built, and
# a provenance file left over from an earlier rung (it is gitignored, so it
# survives in the tree and would otherwise ship a previous version's figures).
PROV="$FS/www/reaper_provenance.js"
if [ ! -f "$PROV" ]; then
  fail "provenance-stamp" "no www/reaper_provenance.js in the staged fs"
else
  # staged www is minified - read values by regex, never by line shape
  _pv=$(tr -d '\r' < "$PROV" | grep -oE 'patches:[[:space:]]*"[^"]*"' | sed 's/.*"\(.*\)"/\1/')
  _vv=$(tr -d '\r' < "$PROV" | grep -oE 'version:[[:space:]]*"[^"]*"' | sed 's/.*"\(.*\)"/\1/')
  _want_v="${VERSION#Reaper_}"
  _pcs="$(dirname "${BASH_SOURCE[0]}")/patch_count.sh"
  if ! printf '%s' "$_pv" | grep -qE '^[0-9]+$'; then
    fail "provenance-stamp" "patch count is '${_pv:-<empty>}' -- About page shows a dash"
  elif [ "$_vv" != "$_want_v" ]; then
    fail "provenance-stamp" "stamped version '$_vv' != build version '$_want_v' (stale provenance file)"
  elif [ -f "$_pcs" ]; then
    _tc=$(bash "$_pcs" "$R" 2>/dev/null)
    if [ -n "$_tc" ] && [ "$_tc" != "$_pv" ]; then
      fail "provenance-stamp" "stamped $_pv patches, tree has $_tc"
    else
      pass "provenance-stamp" "$_pv patches, version $_vv"
    fi
  else
    warn "provenance-stamp" "$_pv patches, version $_vv (patch_count.sh absent, count not cross-checked)"
  fi
fi

echo "reaper_verify: $PASSN pass, $WARNN warn, $FAILN FAIL  ($MODEL $VARIANT)"
[ "$FAILN" -gt 0 ] && { echo "== VERIFY FAILED =="; exit 1; }
echo "== VERIFY OK =="; exit 0
