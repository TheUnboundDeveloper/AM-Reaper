#!/bin/bash
# ============================================================================
# _port_protect.sh -- SINGLE SOURCE OF TRUTH for the shared-vs-per-model
# classification used by port_sibling_v2.sh (what to sync) AND reaper_verify.sh
# (what must never lag). Sourced, not executed.
#
# 2026-08-05: created after the MSWAN /sysdep/ gap shipped v2.1.5/v2.1.6 sibling
# images without the PPPoE-1500 fix. Rules live HERE ONLY -- if the port and the
# verifier disagree about what is shared, gaps ship silently.
# ============================================================================


# Protect ONLY genuinely per-model content:
#   - the two ASUS model-asset sysdep dirs (www/sysdep/<MODEL> art, router/sysdep staging)
#   - prebuilt blobs / per-model build dirs / kernel+bootloader trees
#   - per-model config + the model-unique banner
PP_PROTECT_RE='(release/src/router/(www/)?sysdep/|/prebuild/|/prebuilt/|targets/|bootloaders/|bcmdrivers/|/dts/|/rdp/|router-sysdep\.|\.o$|\.a$|\.so$|\.ko$|\.bin$|/config_[a-z0-9_-]+$|_REAPER_Header(_anim)?\.(png|mp4)$)'

# Inside the protected www/sysdep, FUNCTION/ is FLAG-keyed shared code
# (MSWAN WAN page, VPN pages, SDN, QIS, themes) -- ALWAYS shared.
PP_SYNC_ANYWAY_RE='^release/src/router/www/sysdep/FUNCTION/'

# Protected by design (per-model divergence is intentional):
#   dicts (supplemented separately, lockstep-checked) and the GT-BE98 chanlist
#   shim. Both radio pages have now left this set - see below.
#
# 2026-08-25: Tools_Sysinfo.asp REMOVED from this set. It was listed as one of
# "the two radio-gated pages", but it does not gate per BRANCH at all - it gates
# at RUNTIME on based_modelid, so one shared copy serves every model. Protecting
# it meant the port skipped it, and four siblings silently froze at the pre-
# 2026-08-17 temperature chart while Reaper_QoSDiag.asp - the OTHER half of the
# same two-file rewrite, and not protected - synced normally. Those images ship
# a time-based x axis on one chart and the old 20-slot category axis on the
# other. Proof the file needs no divergence: rt-be92u is BYTE-IDENTICAL to canon
# and shipped v2.7.6 + v2.7.7, and canon's copy carries the SUPERSET of the model
# checks (GT-AXE16000 || GT-BE98, plus GT-BE98_PRO) where the stale copies knew
# only GT-AXE16000. Un-protecting makes the parity check surface the gap instead
# of hiding it.
# 2026-08-25: Main_WStatus_Content.asp REMOVED for the same reason as
# Tools_Sysinfo.asp above - it maps radios at RUNTIME from based_modelid
# (GT-AXE16000||GT-BE98 quad-band / GT-BE98_PRO / generic tri-band), not per
# branch. Four of five siblings were already byte-identical to canon; only
# gt-be98-pro differed, and only by MISSING canon's 2ea3eafaf2 ("add GT-BE98 to
# the quad-band radio branch"). That omission is inert on GT-BE98_PRO hardware -
# based_modelid takes the GT-BE98_PRO branch either way - but it is still drift
# the port could never heal while the file was protected.
PP_PROTECT_GLOB='[A-Z][A-Z]\.dict$|reaper_chanlist_shim\.c'

# Per-branch identity files (never taken from canon):
PP_PROTECT_EXACT="release/src-rt/version.conf release/src-rt/target.mak"

# Shared pages that legitimately differ from canon by EXACTLY the model-unique
# banner filename (synced then re-pointed by the port). Verify compares these
# banner-normalized.
# DERIVED from canon, not listed - the third copy of this list to be fixed on
# 2026-09-10, after port_sibling_v2.sh and check_overlays.py. All three stopped
# at six pages; Reaper_WiFiSetup.asp (v3.1.0, first-boot Wi-Fi) references the
# animated header and was never added anywhere, so every sibling shipped it
# naming canon's RT-96U banner - a file the sibling removes. Once the port tool
# started re-pointing it, THIS list turned the corrected page into a "shared
# residual", so the two had to move together. The fallback is the historical
# six with a warning, never fewer: a broken derivation must fail loud at the
# parity check, not quietly stop classifying pages as banner-normalized.
PP_BANNER_REFS=$(git -C "${R:-/home/reaper/asuswrt-be96u}" grep -l -- '_REAPER_Header' "${PP_CANON:-be96u-only}" -- \
    'release/src/router/www/*.asp' 'release/src/router/www/*.js' 2>/dev/null \
  | sed "s/^${PP_CANON:-be96u-only}://" | sort | tr '\n' ' ')
if [ "$(echo $PP_BANNER_REFS | wc -w)" -lt 6 ]; then
  echo "_port_protect: WARNING - could not derive the banner-referencing pages from canon; using the historical six (a newer page will read as a shared residual)" >&2
  PP_BANNER_REFS="release/src/router/www/Main_Login.asp release/src/router/www/Main_ReaperDash.asp release/src/router/www/reaper_shell.asp release/src/router/www/state.js release/src/router/www/Main_Password.asp release/src/router/www/Logout.asp"
fi

# classification: 0 = protected (per-model, skip), 1 = shared (must match canon),
#                 2 = banner-ref (shared modulo banner name)
pp_classify(){ # $1 = repo-relative path
  local f="$1" e
  echo "$f" | grep -qE "$PP_SYNC_ANYWAY_RE" && { echo 1; return; }
  echo "$f" | grep -qE "$PP_PROTECT_RE"     && { echo 0; return; }
  echo "$f" | grep -qE "$PP_PROTECT_GLOB"   && { echo 0; return; }
  for e in $PP_PROTECT_EXACT; do [ "$f" = "$e" ] && { echo 0; return; }; done
  for e in $PP_BANNER_REFS;   do [ "$f" = "$e" ] && { echo 2; return; }; done
  echo 1
}

# strip the model-unique banner filename for normalized comparison
pp_norm_banner(){ sed -E 's/[A-Za-z0-9_-]*_REAPER_Header_anim\.png/BANNER_ANIM/g; s/[A-Za-z0-9_-]*_REAPER_Header\.(png|mp4)/BANNER.\1/g'; }

# pp_parity_check CANON_REF HEAD_REF  -> prints offending files, returns 1 if any
# shared file differs from canon (model-only files -- absent from canon -- skip).
pp_parity_check(){
  local canon="$1" head="$2" f cls bad=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    cls=$(pp_classify "$f")
    [ "$cls" = 0 ] && continue
    if ! git cat-file -e "$canon:$f" 2>/dev/null; then continue; fi   # model-only
    if [ "$cls" = 2 ]; then
      a=$(git show "$canon:$f" 2>/dev/null | pp_norm_banner | md5sum | cut -d' ' -f1)
      b=$(git show "$head:$f"  2>/dev/null | pp_norm_banner | md5sum | cut -d' ' -f1)
      [ "$a" = "$b" ] || { echo "UNSYNCED(banner-ref, differs beyond banner): $f"; bad=1; }
    else
      git diff --quiet "$canon" "$head" -- "$f" 2>/dev/null || { echo "UNSYNCED(shared): $f"; bad=1; }
    fi
  done < <(git diff --name-only "$canon" "$head" 2>/dev/null)
  return $bad
}
