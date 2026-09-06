#!/bin/bash
# check_ossl_consumers.sh <staged-rootfs> [allowlist] [readelf] [nm]
#
# reaper_verify check 22 -- "who may still link the OpenSSL 1.1 SONAME".
#
# WHY THIS EXISTS
# ---------------
# check 21 (check_symbols.sh) asks whether every OpenSSL symbol a binary imports
# exists in the library it links. That is the right question for a broken
# image; it is the wrong question for a STALE one. On a warm tree a library
# swap leaves every consumer that was not relinked still naming the OLD SONAME,
# and with a compat shim of that name present those consumers all resolve --
# through the shim -- and check 21 is satisfied. The v3.0.3 hostapd was exactly
# that: compiled on 2026-07-27, never relinked, bound to a 95-symbol shim.
#
# So this check asks the stale question directly: in an image that carries the
# real OpenSSL 3.x, WHICH binaries are still allowed to depend on the 1.1
# SONAME? Only two kinds:
#
#   closed  a tracked prebuilt (shipped as a binary; can never be recompiled).
#           May link only the 1.1 name -- that is what the shim is for.
#   host    a source-built binary that absorbs tracked prebuilt OBJECTS (httpd,
#           rc, infosvr...). Upstream links these against BOTH the real .so.3
#           and the shim, so a rebuilt host ALWAYS also names libcrypto.so.3.
#           A host that names only the 1.1 SONAME was not relinked -> FAIL.
#
# Everything else that names the 1.1 SONAME is a stale artifact (rebuild its
# package) or a new closed consumer nobody classified -> FAIL either way. And a
# short list of `must3` binaries (hostapd first) must name libcrypto.so.3
# outright, verified with readelf, never inferred from a green build.
#
# The check is INERT on an image that has no libcrypto.so.3 staged: a 1.1 image
# legitimately links the 1.1 name everywhere, and a gate that fails on the
# current line would just be switched off.
#
# Allowlist format (one per line, '#' comments):  <path-in-rootfs>|<kind>
#   kind = closed | host | must3       (absent path = fine: per-model blob sets)
set -u
FS="${1:?usage: check_ossl_consumers.sh <staged-rootfs> [allowlist] [readelf] [nm]}"
AL="${2:-$(dirname "${BASH_SOURCE[0]}")/openssl11-consumers.txt}"
RE="${3:-}"; NM="${4:-}"
[ -n "$RE" ] || RE=$(ls /opt/toolchains/crosstools-arm*gcc-10.3*/usr/bin/*-readelf 2>/dev/null | head -1)
[ -n "$NM" ] || NM=$(ls /opt/toolchains/crosstools-arm*gcc-10.3*/usr/bin/*-nm 2>/dev/null | head -1)
[ -n "$RE" ] && [ -x "$RE" ] || RE=$(command -v readelf || true)
[ -n "$NM" ] && [ -x "$NM" ] || NM=$(command -v nm || true)
[ -n "$RE" ] && [ -n "$NM" ] || { echo "check-ossl-consumers: SKIP (no readelf/nm)"; exit 0; }
[ -d "$FS" ] || { echo "check-ossl-consumers: SKIP (no staged fs at $FS)"; exit 0; }
[ -f "$AL" ] || { echo "check-ossl-consumers: FAIL (allowlist $AL missing -- the check cannot tell closed from stale)"; exit 1; }
export LC_ALL=C

LIB3=""; LIB11=""
for d in /usr/lib /lib; do
  [ -z "$LIB3" ]  && [ -f "$FS$d/libcrypto.so.3" ]   && LIB3="$FS$d/libcrypto.so.3"
  [ -z "$LIB11" ] && [ -f "$FS$d/libcrypto.so.1.1" ] && LIB11="$FS$d/libcrypto.so.1.1"
done
if [ -z "$LIB3" ]; then
  echo "check-ossl-consumers: inert -- no libcrypto.so.3 staged (image is on OpenSSL 1.1)"
  exit 0
fi

exports(){ "$NM" -D --defined-only "$1" 2>/dev/null | awk '$2 ~ /^[TWiDB]$/' | wc -l; }
nfail=0
say(){ echo "  $*"; }

e3=$(exports "$LIB3")
if [ "$e3" -lt 3000 ]; then
  say "FAIL ${LIB3#$FS}: only $e3 exported symbols -- not the real OpenSSL 3.x library"; nfail=$((nfail+1))
fi
shim=0
if [ -n "$LIB11" ]; then
  e11=$(exports "$LIB11")
  if [ "$e11" -ge 3000 ]; then
    say "FAIL ${LIB11#$FS}: $e11 exported symbols = a REAL OpenSSL 1.1 next to 3.x. Two OpenSSLs in one"
    say "     image means a process that loads both mixes their state; the plan rejects dual-stack."
    nfail=$((nfail+1))
  elif [ "$e11" -lt 50 ]; then
    say "FAIL ${LIB11#$FS}: only $e11 exported symbols -- not a usable compat shim"; nfail=$((nfail+1))
  else
    shim=1
  fi
fi

kind_of(){ # $1 = path in rootfs -> kind or ""
  awk -F'|' -v p="$1" '$0 !~ /^[[:space:]]*#/ && $1==p {print $2; exit}' "$AL"
}

n11=0; n3=0; nclosed=0; nhost=0; unknown=""
while read -r f; do
  head -c4 "$f" 2>/dev/null | grep -q ELF || continue
  rel="${f#$FS}"; b=$(basename "$f")
  case "$b" in libcrypto.so.1.1|libssl.so.1.1|libcrypto.so.3|libssl.so.3|legacy.so) continue;; esac
  needed=$("$RE" -d "$f" 2>/dev/null | sed -n 's/.*NEEDED.*\[\(.*\)\]/\1/p')
  has11=0; has3=0
  echo "$needed" | grep -q '^lib\(crypto\|ssl\)\.so\.1\.1$' && has11=1
  echo "$needed" | grep -q '^lib\(crypto\|ssl\)\.so\.3$'    && has3=1
  [ "$has11" = 1 ] && n11=$((n11+1))
  [ "$has3" = 1 ]  && n3=$((n3+1))
  k=$(kind_of "$rel")
  case "$k" in
    closed)
      [ "$has11" = 1 ] && nclosed=$((nclosed+1))
      ;;
    host)
      [ "$has11" = 1 ] && nhost=$((nhost+1))
      if [ "$has3" = 0 ]; then
        say "FAIL $rel: host of prebuilt objects links only the 1.1 SONAME -- not relinked against 3.x (stale)"
        nfail=$((nfail+1))
      fi
      ;;
    must3)
      if [ "$has11" = 1 ]; then
        say "FAIL $rel: source-built, must NOT depend on the 1.1 SONAME (stale link)"; nfail=$((nfail+1))
      fi
      if [ "$has3" = 0 ]; then
        say "FAIL $rel: must link libcrypto.so.3 (stale link, or its Makefile points at openssl-1.1)"; nfail=$((nfail+1))
      fi
      ;;
    *)
      if [ "$has11" = 1 ]; then
        unknown="$unknown $rel"; nfail=$((nfail+1))
      fi
      ;;
  esac
done < <(find "$FS" -type f \( -perm -u+x -o -name '*.so*' \) 2>/dev/null | sort)

if [ -n "$unknown" ]; then
  say "FAIL unclassified consumer(s) of the 1.1 SONAME:"
  for u in $unknown; do say "     $u"; done
  say "     -> a stale build artifact (rebuild that package: it must relink to .so.3) or a"
  say "        new closed prebuilt (classify it as closed|host in $(basename "$AL"))."
fi
if [ "$n11" -gt 0 ] && [ -z "$LIB11" ]; then
  say "FAIL $n11 binaries need libcrypto.so.1.1 but no such library is staged -- they cannot load"
  nfail=$((nfail+1))
fi
# must3 entries that are simply absent are fine (per-model); a must3 that is
# present has already been judged above.

summary="1.1-SONAME consumers: $n11 (closed $nclosed, hosts $nhost); .so.3 consumers: $n3; shim staged: $shim"
if [ "$nfail" -gt 0 ]; then
  echo "check-ossl-consumers: $nfail problem(s) -- $summary"
  exit 1
fi
echo "check-ossl-consumers: OK -- $summary"
exit 0
