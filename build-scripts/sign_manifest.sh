#!/bin/bash
# sign_manifest.sh -- ed25519-sign the firmware-update manifest (v2.7.3).
#
# The on-router update check (rom/webs_scripts/reaper_webs_update.sh) verifies
# updates/manifest_3006.txt against the public key baked into the firmware and
# REFUSES the whole manifest -- fail closed -- when the signature is missing or
# wrong. So every publish that touches the manifest MUST be followed by this
# script + a commit of the .sig, or every fielded box reports "check failed".
#
#   RELEASE FLOW:  build -> publish -> refresh_manifest (CI or stage_release)
#                  -> sign_manifest.sh -> commit updates/ -> push
#
# The PRIVATE key is deliberately not in any repository and must never be
# committed or uploaded (not to CI secrets either -- the point is that a
# compromised repository/account cannot mint a valid manifest). Default
# location is the local reaper-keys folder next to the repos; override with
# REAPER_MANIFEST_KEY=<path> to sign from an offline copy (USB stick).
#
# Key rotation: generate a new pair, replace build-scripts/manifest_pub.pem
# AND the embedded pubkey in reaper_webs_update.sh, ship that firmware, and
# only then start signing with the new key -- boxes on older firmware keep
# verifying with the old key, so keep publishing old-key signatures until the
# fleet has moved (or accept that older boxes fail closed until upgraded).
set -e
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO="$(dirname "$HERE")"
. "$HERE/_reaper_env.sh"   # not set -u clean; sourced before we tighten up
set -u
KEY="${REAPER_MANIFEST_KEY:-/mnt/c/Users/$WINUSER/AppData/Roaming/VSC/ASUS/reaper-keys/manifest_rsa4096.pem}"
PUB="$HERE/manifest_pub.pem"
MAN="$REPO/updates/manifest_3006.txt"
SIG="$MAN.sig"

[ -f "$MAN" ] || { echo "ERROR: $MAN not found - run refresh_manifest / stage_release first"; exit 1; }
[ -f "$KEY" ] || { echo "ERROR: private key not found at $KEY (set REAPER_MANIFEST_KEY)"; exit 1; }
[ -f "$PUB" ] || { echo "ERROR: $PUB missing from the repo"; exit 1; }

openssl dgst -sha256 -sign "$KEY" "$MAN" | openssl base64 -A > "$SIG"
echo "" >> "$SIG"   # trailing newline so git/raw serving is clean

# never publish a signature we did not verify against the SHIPPED public key
openssl base64 -d -A -in "$SIG" -out /tmp/reaper_manifest_sig.bin
if openssl dgst -sha256 -verify "$PUB" -signature /tmp/reaper_manifest_sig.bin "$MAN" >/dev/null 2>&1; then
	echo "signed + verified: $SIG"
	rm -f /tmp/reaper_manifest_sig.bin
else
	rm -f "$SIG" /tmp/reaper_manifest_sig.bin
	echo "ERROR: self-verify FAILED - the private key does not match manifest_pub.pem; nothing written"
	exit 1
fi
