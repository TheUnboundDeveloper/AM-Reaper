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
#   dicts (supplemented separately, lockstep-checked), the two radio-gated
#   pages, and the GT-BE98 chanlist shim.
PP_PROTECT_GLOB='[A-Z][A-Z]\.dict$|Main_WStatus_Content\.asp|Tools_Sysinfo\.asp|reaper_chanlist_shim\.c'

# Per-branch identity files (never taken from canon):
PP_PROTECT_EXACT="release/src-rt/version.conf release/src-rt/target.mak"

# Shared pages that legitimately differ from canon by EXACTLY the model-unique
# banner filename (synced then re-pointed by the port). Verify compares these
# banner-normalized.
PP_BANNER_REFS="release/src/router/www/Main_Login.asp release/src/router/www/Main_ReaperDash.asp release/src/router/www/reaper_shell.asp release/src/router/www/state.js release/src/router/www/Main_Password.asp release/src/router/www/Reaper_FirstBoot.asp release/src/router/www/Logout.asp"

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
