#!/bin/bash
# check_ovpn_pki.sh <staged-fs>  -- the firmware's own OpenVPN PKI chain, end to end, on the
#                                   staged binaries. reaper_verify check 23 ("ovpn-pki").
#
# WHY THIS EXISTS. Every OpenVPN server certificate this firmware generates comes from ONE
# shell script that libovpn writes at runtime (openvpn_setup.c: ovpn_write_server_keys and
# ovpn_repair_server_cert) and that runs /rom/easy-rsa/pkitool against the image's own
# openssl. That chain broke TWICE after the OpenSSL 3.5 move (v3.1.0), each time silently,
# each time found on a router rather than in a build:
#   - v3.1.4: pkitool put the [server] extensions on the certificate REQUEST; an AKID cannot
#     be computed for a CSR, OpenSSL 3.x fails `req`, and pkitool's && chain stops.
#   - v3.1.5 (review R16): the easy-rsa config points RANDFILE at $ENV::HOME/.rnd, rc runs
#     with HOME=/, and OpenSSL 3.x exits non-zero when it cannot write that file - AFTER the
#     CSR was written, so the chain stops between `openssl req` and `openssl ca`.
# Neither is visible to a compile, a link check or a symbol check: every binary is fine, the
# PROTOCOL between them is what fails. So this runs the protocol: the staged pkitool, the
# staged config, the staged openssl (ARM, under qemu-user), with exactly the environment the
# generated script exports, and asserts a CA, a server certificate and a client certificate
# come out and verify. It also pins the two known causes by inspection so a regression is
# named, not just detected.
#
# Exit: 0 pass, 1 fail, 77 skipped (no qemu-arm - the caller reports a WARN, never a PASS).
set -u
FS=${1:?staged fs}
Q=$(command -v qemu-arm-static 2>/dev/null || command -v qemu-arm 2>/dev/null || true)
[ -n "$Q" ] || { echo "qemu-arm not available on this host - the PKI chain was not exercised"; exit 77; }
for f in usr/sbin/openssl rom/easy-rsa/pkitool rom/easy-rsa/openssl-1.0.0.cnf usr/lib/libovpn.so; do
  [ -e "$FS/$f" ] || { echo "missing in the staged fs: $f"; exit 1; }
done

# 1. the environment the firmware's generated scripts export (libovpn/openvpn_setup.c).
#    The HOME line IS the R16 fix; without it openssl 3.x writes //.rnd and exits 1.
strings -a "$FS/usr/lib/libovpn.so" | grep -q 'export HOME="/etc/openvpn/server%d"' \
  || { echo "libovpn: the first-setup script no longer exports HOME=<key dir> (R16: openssl 3.x exits 1 when RANDFILE is unwritable)"; exit 1; }
strings -a "$FS/usr/lib/libovpn.so" | grep -q 'export HOME="%s"' \
  || { echo "libovpn: the repair script no longer exports HOME=<key dir> (R16)"; exit 1; }
# 2. pkitool must not put the [server] extensions on the REQUEST (the v3.1.4 cause)
if grep -qE '^[[:space:]]*--server[[:space:]]*\)[[:space:]]*REQ_EXT=' "$FS/rom/easy-rsa/pkitool"; then
  echo "pkitool: --server puts -extensions server on the request again (an AKID cannot be computed for a CSR; openssl 3.x fails req)"; exit 1
fi

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/keys"
# the image's openssl, run through qemu-user with the image as its sysroot
printf '#!/bin/sh\nexec "%s" -L "%s" "%s/usr/sbin/openssl" "$@"\n' "$Q" "$FS" "$FS" > "$T/bin/openssl"
chmod 700 "$T/bin/openssl"
OV=$("$T/bin/openssl" version 2>/dev/null | awk '{print $2}')
[ -n "$OV" ] || { echo "the staged openssl does not run under qemu (sysroot $FS)"; exit 1; }

# 3. mirror ovpn_write_server_keys() line for line: same variables, same values, same order,
#    HOME set the way the fixed script sets it. Only the paths are the staged ones.
(
  export OPENSSL="$T/bin/openssl" GREP="grep"
  export KEY_CONFIG="$FS/rom/easy-rsa/openssl-1.0.0.cnf"
  export KEY_DIR="$T/keys" HOME="$T/keys"
  export KEY_SIZE=2048 CA_EXPIRE=3650 KEY_EXPIRE=3650
  export KEY_COUNTRY="TW" KEY_PROVINCE="TW" KEY_CITY="Taipei" KEY_ORG="ASUS" KEY_EMAIL="me@asusrouter.lan" KEY_OU="Home/Office"
  export KEY_CN="RT-VERIFY"
  touch "$KEY_DIR/index.txt"
  "$OPENSSL" rand -hex 16 > "$KEY_DIR/serial"
  sh "$FS/rom/easy-rsa/pkitool" --initca &&
  sh "$FS/rom/easy-rsa/pkitool" --server server &&
  KEY_CN="" sh "$FS/rom/easy-rsa/pkitool" client
) > "$T/log" 2>&1 || { echo "the pkitool chain FAILED on the staged openssl $OV - last lines:"; tail -25 "$T/log" | sed 's/^/    /'; exit 1; }

for f in ca.crt ca.key server.csr server.crt server.key client.crt client.key; do
  [ -s "$T/keys/$f" ] || { echo "pkitool exited 0 but $f is missing or empty"; tail -15 "$T/log" | sed 's/^/    /'; exit 1; }
done
"$T/bin/openssl" verify -CAfile "$T/keys/ca.crt" "$T/keys/server.crt" "$T/keys/client.crt" >> "$T/log" 2>&1 \
  || { echo "the issued certificates do not verify against the CA that issued them"; tail -10 "$T/log" | sed 's/^/    /'; exit 1; }
X=$("$T/bin/openssl" x509 -in "$T/keys/server.crt" -noout -text 2>/dev/null)
echo "$X" | grep -q 'TLS Web Server Authentication' || { echo "server.crt lacks extendedKeyUsage serverAuth - the [server] extensions were not applied at signing"; exit 1; }
echo "$X" | grep -qi 'SSL Server'                    || { echo "server.crt lacks nsCertType server"; exit 1; }
echo "$X" | grep -q 'Authority Key Identifier'       || { echo "server.crt lacks an AKID - not signed through the CA path"; exit 1; }
echo "ca + server + client issued by the staged pkitool on the staged openssl $OV (qemu-user); verify OK; server.crt carries serverAuth, nsCertType server, AKID"
exit 0
