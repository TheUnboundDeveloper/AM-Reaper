#!/bin/bash
# ============================================================================
# reaper_stale_configure.sh -- find (and clear) packages whose configure flags
# have been edited since the package was last configured.
# ----------------------------------------------------------------------------
# WHY THIS EXISTS (2026-08-09):
# router/Makefile guards every autotools package with
#       <pkg>/Makefile: <pkg>/configure
# Upstream tarballs carry an EPOCH mtime -- strongswan's configure is dated
# 2000-01-03 -- so once <pkg>/Makefile exists it is permanently newer and
# configure NEVER RE-RUNS, even after a patch changes its --enable/--disable
# flags. The change is then silently inert on a warm tree.
#
# Real case: commit 933373f773 "strongswan: sync build recipes with upstream -
# fixes missing exe" (2026-08-03) added --enable-stroke/aes/des/md5/sha1/sha2/
# hmac/gcm/fips-prf/curve25519. The tree had been configured 2026-07-21, so none
# of them were ever built. Every local build from 21 July onward -- all five
# models, v2.3.1 included -- shipped an IPSec stack missing usr/sbin/ipsec,
# usr/lib/ipsec/{starter,stroke} and the software crypto plugins. The pristine
# CI build produced them correctly; the defect was only visible by decomposing
# an image and diffing it against CI's.
#
# NO BUILD GATE CATCHES THIS. The build succeeds, reaper_verify passes 19/19,
# the image boots. Hence this check.
#
# USAGE:  reaper_stale_configure.sh [--check|--fix] [tree-root]
#   --check (default) report only, exit 1 if anything is stale
#   --fix             also remove <pkg>/Makefile + <pkg>/config.status + <pkg>/stamp-h1
#                     so the next build re-runs configure with the current flags
# 2026-11-14, same run: tracked kernel objects that equal their committed copy are handed back to kbuild
# (their .cmd is removed), and wpa_supplicant / getdns built against another OpenSSL are cleared - see the
# two REAPER-STALE sections near the end.
# ============================================================================

case "${1:-}" in
  -h|--help) sed -n "2,30 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
set -u
MODE="${1:---check}"
ROOT="${2:-/home/reaper/asuswrt-be96u}"
R="$ROOT/release/src/router"

[ -d "$R" ] || { echo "stale-configure: no router tree at $R"; exit 0; }
cd "$ROOT" || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || { echo "stale-configure: $ROOT is not a git tree; skipping"; exit 0; }

found=0
for cs in "$R"/*/config.status; do
  [ -f "$cs" ] || continue
  d=$(dirname "$cs"); pkg=$(basename "$d")
  [ -f "$d/configure" ] || continue
  # 2026-10-27 (102.10 rebase): a package whose config.status is TRACKED ships
  # pre-configured from upstream (LPRng); the build never runs its configure, so
  # a rule edit cannot leave it stale - and clearing it deleted tracked files and
  # re-ran a 2006 configure that writes SHELL="/bin/sh" (quotes included), which
  # killed the build at LPRng/UTILS. A rebase re-dates every replayed commit, so
  # after one, every configured package looks stale and this line is what keeps
  # the over-broad re-configure harmless.
  git ls-files --error-unmatch -- "release/src/router/$pkg/config.status" >/dev/null 2>&1 && continue

  cs_epoch=$(stat -c%Y "$cs" 2>/dev/null) || continue
  # Last commit whose diff to router/Makefile mentions this package. -G matches
  # the diff text, so a rule edit for THIS package is what trips it.
  chg=$(git log -1 --format='%ct' -G"\b${pkg}\b" -- release/src/router/Makefile 2>/dev/null)
  subj=""
  # 2026-11-06: the package's own preconfigure-script* counts too - that is where its CFLAGS/LDFLAGS
  # live. The 2026-11-05 lighttpd full-RELRO edit was made there, this check looked at router/Makefile
  # only, and every local image after it still shipped the 2026-10-27 lighttpd (ET_EXEC, no BIND_NOW);
  # a clean CI tree configures fresh. Newest of the script's last commit and its file time (an
  # uncommitted edit is just as stale).
  for pc in "$d"/preconfigure-script*; do
    [ -f "$pc" ] || continue
    for v in $(git log -1 --format='%ct' -- "release/src/router/$pkg/${pc##*/}" 2>/dev/null) $(stat -c%Y "$pc" 2>/dev/null); do
      if [ "$v" -gt "${chg:-0}" ]; then chg=$v; subj="$pkg/${pc##*/} changed"; fi
    done
  done
  # 2026-11-16: and any change inside the package's configure RECIPE block in router/Makefile, whatever the changed
  # line says. The v3.8.1 SNMP change removed `ucd-snmp/dlmod,` from net-snmp's --with-mib-modules list; that line
  # does not name net-snmp, so the name search above never saw it, and the local alpha image built from a tree
  # configured on 2026-11-04 still carried the agent's module loader (CI, configuring fresh, did not). The block runs
  # from the package's `<pkg>/stamp-h1:`, `<pkg>/Makefile:` or `<pkg>/config.status:` target to the next blank
  # line or target. Only commits made after the package was configured are searched (--since), so this stays quick.
  _blk=$(awk -v p="$pkg" '
    !s && index($0, p "/") == 1 && $0 ~ "^[^ \t]*/(stamp-h1|Makefile|config[.]status)([ \t][^:]*)?[ \t]*:" { s = NR; next }
    s && !e && ($0 ~ /^[ \t]*$/ || $0 ~ /^[^ \t#][^=]*:([^=]|$)/) { e = NR - 1 }
    END { if (s) { if (!e) e = NR; if (e >= s) print s "," e } }' "$R/Makefile" 2>/dev/null)
  if [ -n "$_blk" ]; then
    _bl=$(git log -1 --format='%ct %h %s' --since="@$cs_epoch" -L "$_blk:release/src/router/Makefile" 2>/dev/null | head -1)
    _bv=${_bl%% *}
    case "$_bv" in ''|*[!0-9]*) ;; *)
      if [ "$_bv" -gt "${chg:-0}" ]; then chg=$_bv; subj="$(echo "${_bl#* }" | cut -c1-88) (its configure recipe)"; fi ;;
    esac
  fi
  [ -n "$chg" ] || continue
  [ "$chg" -gt "$cs_epoch" ] || continue

  found=$((found+1))
  [ -n "$subj" ] || subj=$(git log -1 --format='%h %s' -G"\b${pkg}\b" -- release/src/router/Makefile 2>/dev/null | cut -c1-88)
  echo "  [STALE] $pkg"
  echo "          configured $(date -d "@$cs_epoch" +%Y-%m-%d), rules changed $(date -d "@$chg" +%Y-%m-%d)"
  echo "          $subj"
  if [ "$MODE" = "--fix" ]; then
    # v3.3.4 cut (2026-10-06): the router Makefile re-runs configure only when the
    # package's stamp-h1 sentinel is missing (76 packages use one). Clearing the
    # Makefile without it left expat-2.0.1 "configured" with no Makefile, and the
    # build died "no makefile found". The sentinel goes with the rest.
    rm -f "$d/Makefile" "$d/config.status" "$d/stamp-h1"
    # 2026-10-27: some router/Makefile rules are keyed on a GENERATED configure
    # (libcap-ng: `libcap-ng: libcap-ng/configure`, whose recipe runs autogen and
    # configure together). With only the Makefile gone the configure target was
    # still up to date, nothing re-ran it, and the build died "no makefile found"
    # in libcap-ng. Every package source is tracked, so an untracked configure is
    # a build product: removing it puts the package back to its cold-tree state.
    if ! git ls-files --error-unmatch -- "release/src/router/$pkg/configure" >/dev/null 2>&1; then
      rm -f "$d/configure"
      echo "          -> also removed the generated configure (its rule regenerates it)"
    fi
    # 2026-11-06: and its build objects. Automake objects depend on their sources, not on the flags, so a
    # re-configure with new CFLAGS relinked the 2026-10-27 lighttpd objects under the new LDFLAGS (-pie
    # over non-PIC code = TEXTREL, no FORTIFY). Only git-ignored products go (*.o *.lo *.la *.a and
    # .libs/), all of them together - a tracked prebuilt is never touched.
    _objs=$(git ls-files --others --ignored --exclude-standard -- "release/src/router/$pkg" 2>/dev/null \
            | grep -E '\.(o|lo|la|a)$|/\.libs/' | grep -c .)
    git ls-files -z --others --ignored --exclude-standard -- "release/src/router/$pkg" 2>/dev/null \
      | grep -zE '\.(o|lo|la|a)$|/\.libs/' | xargs -0 -r rm -f --
    echo "          -> removed $_objs build object(s) so they compile with the new flags"
    echo "          -> cleared Makefile + config.status + stamp-h1; next build re-configures"
  fi
done

# ---- REAPER-STALE-OBJ-BEGIN: tracked objects the kernel build regenerates (2026-11-14) ----
# ASUS ships some kernel objects in git (bcmmcast.o, wlshared_linux.o, pktrunner.o ...) and kbuild rebuilds them
# here, which leaves them "modified". Restoring them (git checkout, to hand a cut a clean tree) puts the OLD
# committed bytes back with a NEW mtime, and kbuild - which decides by mtime and its saved .cmd - never rebuilds
# them. From 2026-11-05 every local image carried the committed bcmmcast.o, without the netlink privilege gate
# that had been compiled into bcm_mcast_netlink.o two days earlier; a clean tree (CI) has no .cmd files, builds
# everything, and was correct. So: a tracked object that kbuild built here (its .cmd sits beside it) and that is
# byte-identical to the committed copy gets its .cmd removed - the state of a clean tree for that one object.
# kbuild then rebuilds it: a reproducible object comes out the same again, a restored one comes out current.
kb_same=0; kb_cur=0; _kc=()
while IFS= read -r _f; do
  [ -e "${_f%/*}/.${_f##*/}.cmd" ] && _kc+=("$_f")
done < <(git ls-files -- 'release/src-rt-*/*.o' 'release/src-rt-*/*.ko' 2>/dev/null)
if [ "${#_kc[@]}" -gt 0 ]; then
  _mod=$(git status --porcelain --untracked-files=no -- "${_kc[@]}" 2>/dev/null | cut -c4-)
  for _f in "${_kc[@]}"; do
    if printf '%s\n' "$_mod" | grep -qxF -- "$_f"; then kb_cur=$((kb_cur+1)); continue; fi   # built here, differs from git: current
    kb_same=$((kb_same+1))
    [ "$MODE" = "--fix" ] && rm -f -- "${_f%/*}/.${_f##*/}.cmd"
  done
  if [ "$MODE" = "--fix" ]; then
    echo "  tracked kernel objects: $kb_same equal the committed copy -> their .cmd removed, kbuild rebuilds them ($kb_cur built here already)"
  else
    echo "  tracked kernel objects: $kb_same equal the committed copy (a build rebuilds them; --fix clears their .cmd), $kb_cur built here"
  fi
fi
# ---- REAPER-STALE-OBJ-END ----

# ---- REAPER-STALE-OSSL-BEGIN: OpenSSL consumers built against another OpenSSL (2026-11-14) ----
# Two objects the 2026-11-04 comparison with a clean-tree image found, still there on 2026-11-14: wpa_supplicant
# compiled under the previous OpenSSL release (its own makefiles do not depend on the OpenSSL headers), and getdns /
# stubby configured (cmake) while the tree's OpenSSL had no OSSL_PARAM_BLD_new, so it kept the legacy key API.
# Judged by what the built files say, not by dates (this tree's mtimes have been rewritten more than once).
_vd="$R/openssl-3.5/VERSION.dat"
if [ -f "$_vd" ] && grep -q '^RTCONFIG_OPENSSL35=y' "$R/.config" 2>/dev/null; then
  _v() { sed -n "s/^$1=\"\{0,1\}\([^\"]*\)\"\{0,1\}\$/\1/p" "$_vd" | head -1; }
  _want="OpenSSL $(_v MAJOR).$(_v MINOR).$(_v PATCH) $(_v RELEASE_DATE)"
  for _wd in "$ROOT"/release/src-rt-*/bcmdrivers/broadcom/net/wl/impl*/main/components/opensource/router_tools/wpa_supplicant; do
    _b="$_wd/wpa_supplicant/wpa_supplicant"
    [ -f "$_b" ] || continue
    _have=$(grep -a -o -E 'OpenSSL [0-9]+\.[0-9]+\.[0-9]+ [0-9]+ [A-Z][a-z]{2} [0-9]{4}' "$_b" 2>/dev/null | sort -u | head -1)
    [ -n "$_have" ] && [ "$_have" != "$_want" ] || continue
    found=$((found+1))
    echo "  [STALE] wpa_supplicant"
    echo "          compiled under $_have, the tree has $_want"
    if [ "$MODE" = "--fix" ]; then
      _rel="${_wd#$ROOT/}"
      _n=$(git ls-files --others -- "$_rel" 2>/dev/null | grep -c -E '\.(o|d)$')
      git ls-files -z --others -- "$_rel" 2>/dev/null \
        | grep -zE '\.(o|d)$|/wpa_supplicant/(wpa_supplicant|wpa_cli|wpa_passphrase|libwpa_client\.so)$' | xargs -0 -r rm -f --
      echo "          -> removed $_n object(s) and the built programs; the next build compiles them again"
    fi
  done
  _gh="$R/getdns/build/config.h"
  if [ -f "$_gh" ] && [ "$(_v MAJOR)" -ge 3 ] 2>/dev/null && ! grep -q '^#define HAVE_OSSL_PARAM_BLD_NEW' "$_gh"; then
    found=$((found+1))
    echo "  [STALE] getdns (stubby)"
    echo "          configured for the legacy OpenSSL key API (no OSSL_PARAM_BLD_new), the tree has $_want"
    if [ "$MODE" = "--fix" ]; then
      rm -rf -- "$R/getdns/build"
      echo "          -> removed getdns/build; the next build configures and compiles it again"
    fi
  fi
fi
# ---- REAPER-STALE-OSSL-END ----

if [ "$found" -eq 0 ]; then
  echo "  stale-configure: clean (no package's flags changed after it was configured, no stale OpenSSL consumer)"
  exit 0
fi
echo "  stale-configure: $found package(s) flagged"
[ "$MODE" = "--fix" ] && exit 0
echo "  run with --fix, or: rm -f <pkg>/Makefile <pkg>/config.status <pkg>/stamp-h1"
exit 1
