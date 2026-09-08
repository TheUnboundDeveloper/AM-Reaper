#!/bin/bash
# check_symbols.sh <staged-rootfs> [readelf] [nm]
#
# Verify that every binary linking OpenSSL can actually RESOLVE the OpenSSL
# symbols it imports from the OpenSSL libraries it links.
#
# WHY THIS EXISTS
# ---------------
# reaper_verify's httpd-link check asks "do the NEEDED libraries exist?" - it
# does NOT ask "do the symbols inside them exist?". Those are different
# questions, and the difference shipped a broken image.
#
# v3.0.3 replaced the real libcrypto.so.1.1 (4,382 exported symbols) with the
# OpenSSL 1.1 compat shim (95) under binaries that had NOT been rebuilt. hostapd
# still linked the 1.1 SONAME and needed 338 OpenSSL symbols; 265 no longer
# existed, 61 of them EC_*/BN_*. Lazy binding let it START - so 2.4/5 GHz came up
# on WPA2 paths - and then 6 GHz initialised WPA3-SAE, called a missing
# elliptic-curve function, and died. dhd_monitor restart-looped it 41 times.
# Every library resolved, so httpd-link passed and the gate shipped it.
#
# SCOPE - deliberately narrow
# ---------------------------
# This checks OpenSSL symbols only. A first cut checked every undefined symbol in
# every ELF and produced three separate waves of false positives: dlopen plugins
# (samba modules, libnl cli, pppd, lighttpd mods) resolve from the host binary
# that loads them, and samba's private libraries legitimately expect symbols from
# smbd/winbindd. Those are all correct-by-design, and per reaper_docs.py's own
# rule - "a gate that cries wolf is a gate everyone learns to skip" - a narrow
# check that never lies beats a broad one that has to be ignored.
#
# It is deliberately NOT "does the symbol exist somewhere in the rootfs": that
# weaker test would have PASSED the very bug this exists to catch, because
# hostapd's missing EC_* symbols DID exist in the staged libcrypto.so.3 - just
# not in the library hostapd links.
set -u
FS="${1:?usage: check_symbols.sh <staged-rootfs> [readelf] [nm]}"
RE="${2:-}"; NM="${3:-}"
[ -n "$RE" ] || RE=$(ls /opt/toolchains/crosstools-arm*gcc-10.3*/usr/bin/*-readelf 2>/dev/null | head -1)
[ -n "$NM" ] || NM=$(ls /opt/toolchains/crosstools-arm*gcc-10.3*/usr/bin/*-nm 2>/dev/null | head -1)
[ -x "$RE" ] && [ -x "$NM" ] || { echo "check-symbols: SKIP (no cross readelf/nm)"; exit 0; }
[ -d "$FS" ] || { echo "check-symbols: SKIP (no staged fs at $FS)"; exit 0; }

export LC_ALL=C
WORK=$(mktemp -d 2>/dev/null || echo /tmp/cksym.$$); mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

find_lib() {
  local s="$1" d
  for d in /usr/lib /lib /usr/lib/samba /usr/lib/ipsec; do
    [ -f "$FS$d/$s" ] && { echo "$FS$d/$s"; return 0; }
  done
  return 1
}

# "Is this undefined symbol an OpenSSL one?" is answered by a STABLE name-prefix
# rule, NOT by reading the staged libraries.
#
# A first cut derived that set from the staged libcrypto/libssl themselves, which
# is circular: gut the library and the set shrinks with it, so the missing
# symbols stop being recognised as OpenSSL symbols and the check silently passes.
# The negative test caught it - a synthetic rootfs with a hollowed-out
# libcrypto.so.1.1 was reported clean. Never define the expectation in terms of
# the artifact under test.
OSSL_RE='^(SSL_|TLS_|SSLv[23]|DTLS|EVP_|EC_|ECDSA_|ECDH_|BN_|RSA_|DSA_|DH_|X509|X509V3_|ASN1_|PEM_|BIO_|ERR_|CRYPTO_|OPENSSL_|OBJ_|AES_|DES_|RC4_|MD4|MD5|SHA1|SHA224|SHA256|SHA384|SHA512|HMAC|CMAC|CMS_|OCSP_|PKCS[0-9]|RAND_|ENGINE_|CONF_|NCONF_|UI_|SRP_|EC_KEY|d2i_|i2d_|PKCS8_|GENERAL_NAME|AUTHORITY_)'

# Other projects define symbols that collide with those prefixes. strongSwan's
# asn1 module exports ASN1_INTEGER_0/1/2 as its own constants - OpenSSL has no
# such symbols (its ASN1_INTEGER API is ASN1_INTEGER_get/set/free/...). Without
# this the strongswan x509/pkcs1/pkcs7/curve25519 plugins are all flagged.
# Broadcom ships its own MD5/SHA1 under names that differ from OpenSSL's only by
# the underscore: theirs are MD5Init/MD5Update/MD5Final and
# SHA1Input/SHA1Reset/SHA1Result, satisfied inside libbcmcrypto; OpenSSL's are
# MD5_Init/MD5_Update/... This false-positive set is already on record in the
# openssl35-shim notes from the 2026-08 symbol survey.
NOT_OSSL_RE='^(ASN1_INTEGER_[0-9]+|MD5(Init|Update|Final)|SHA1(Input|Reset|Result))$'

nfail=0; nchecked=0; details="$WORK/details"; : > "$details"
while read -r f; do
  head -c4 "$f" 2>/dev/null | grep -q ELF || continue
  # only binaries that actually link OpenSSL
  libs=$("$RE" -d "$f" 2>/dev/null | sed -n 's/.*NEEDED.*\[\(lib\(crypto\|ssl\)\.so[0-9.]*\)\]/\1/p')
  [ -n "$libs" ] || continue
  nchecked=$((nchecked+1))

  : > "$WORK/have"
  for s in $libs; do
    p=$(find_lib "$s") || continue
    "$NM" -D --defined-only "$p" 2>/dev/null | awk '{print $NF}' | sed 's/@.*//' >> "$WORK/have"
  done
  sort -u "$WORK/have" -o "$WORK/have"

  "$NM" -D --undefined-only "$f" 2>/dev/null | awk '{print $NF}' | sed 's/@.*//' \
    | grep -E "$OSSL_RE" | grep -vE "$NOT_OSSL_RE" | sort -u > "$WORK/need"
  miss=$(comm -23 "$WORK/need" "$WORK/have")                  # ...that its own libs lack
  n=$(printf '%s' "$miss" | grep -c . || true)
  if [ "$n" -gt 0 ]; then
    nfail=$((nfail+1))
    { printf '  %s: %s of %s OpenSSL symbols unresolved (links: %s)\n' \
        "${f#$FS}" "$n" "$(wc -l < "$WORK/need")" "$(echo $libs | tr '\n' ' ')"
      printf '%s\n' "$miss" | head -8 | sed 's/^/      /'; } >> "$details"
  fi
done < <(find "$FS" -type f \( -perm -u+x -o -name '*.so*' \) 2>/dev/null | sort)

if [ "$nfail" -gt 0 ]; then
  echo "check-symbols: $nfail of $nchecked OpenSSL consumer(s) have UNRESOLVED symbols"
  cat "$details"
  echo "  -> these die at load or first call. A library swap left a consumer short;"
  echo "     rebuild it against the OpenSSL it now links, or restore the library it needs."
  exit 1
fi
echo "check-symbols: all $nchecked OpenSSL consumer(s) resolve"
exit 0
