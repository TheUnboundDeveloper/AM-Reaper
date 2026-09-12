#!/bin/bash
# reaper_dongle_id.sh MODEL rtecdc.bin...   -- do these radio blobs belong to MODEL?
#
# Broadcom builds the dongle firmware (rtecdc.bin, the code that runs on each
# radio chip's own CPU) per model and stamps the model name into it as a
# printable string. Shipping another model's firmware - a sibling's, or the
# other SKU of the same model - is not a degraded radio, it is a bricked
# router: ASUS's guidance is that the wrong radio firmware locks the device
# out until the ASUS recovery tool or a manual reflash. So the name in the
# blob is checked as identity, exact line, at THREE points: before the build
# (source tree, both locally and in the CI container), and after it, on the
# staged image (reaper_verify 8d). All three call this one script so the
# model->name table below exists once.
#
# Surveyed 2026-09-12 across the fleet's own blobs:
#   RT-BE96U RT-BE86U RT-BE88U GT-BE98 GT-BE19000  -> the model name, exact line
#   GT-BE98_PRO                                    -> "GT-BE98 PRO" (space)
#   (and the GT-BE19000AI tree's blob answers "GT-BE19000AI" - the trap this
#    check was written after.)
# Exact-line match: "GT-BE98" does not accept a "GT-BE98 PRO" blob or vice
# versa. No binutils dependency (tr/grep only) so it runs anywhere.
#
# Exit 0: every file names MODEL.  Exit 1: a file names something else, or no
# files were given (a model with NO dongle firmware ships dead radios - the
# build's copy rules skip a missing sysdeps/<MODEL>/ silently).
set -u
MODEL="${1:?MODEL}"; shift
case "$MODEL" in
  GT-BE98_PRO) want="GT-BE98 PRO";;
  *)           want="$MODEL";;
esac
[ $# -gt 0 ] || { echo "  [dongle-id] NO rtecdc.bin given for $MODEL - no radio firmware at all"; exit 1; }
rc=0
for f in "$@"; do
  chip=$(basename "$(dirname "$f")"); [ "$chip" = release ] && chip=$(basename "$(dirname "$(dirname "$f")")")
  if [ ! -s "$f" ]; then echo "  [dongle-id] $chip: MISSING or empty: $f"; rc=1; continue; fi
  if tr -c '[:print:]' '\n' < "$f" | grep -qx -- "$want"; then
    echo "  [dongle-id] $chip: names \"$want\" ($(stat -c %s "$f") B)"
  else
    says=$(tr -c '[:print:]' '\n' < "$f" | grep -E '^(GT-|RT-|TUF-|ZenWiFi|XT|ET)[A-Z]*[0-9]{2,}' | sort -u | head -3 | tr '\n' ' ')
    echo "  [dongle-id] $chip: WRONG MODEL - names ${says:-nothing recognisable}- expected \"$want\": $f"; rc=1
  fi
done
exit $rc
