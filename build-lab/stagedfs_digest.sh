#!/bin/bash
# ============================================================================
# stagedfs_digest.sh -- deterministic digest of a staged rootfs
# ----------------------------------------------------------------------------
# Usage:  stagedfs_digest.sh <FS_DIR> <OUT_DIR> <LABEL>
#
# Emits TWO digests:
#   digest       every file -- comparable with the one ci/container_build.sh
#                already ships as build evidence (same find, same field order,
#                same LC_ALL=C sort, same concatenation into sha256sum)
#   digest_norm  the same, MINUS the paths in nondeterministic.txt
#
# The normalised digest exists because this build is not bit-reproducible and
# never has been. Five staged files differ between any two builds of identical
# source: three literal timestamps, one unsorted depmod output, and one binary
# with a compiled-in build stamp (see nondeterministic.txt for the evidence).
# A gate demanding raw equality can therefore never pass, which makes it a
# broken gate rather than a strict one.
#
# BOTH are recorded. The raw digest is what a future reproducible-builds effort
# would drive to zero; the normalised digest is what decides promotion today.
#
# Also archives the small differing-file candidates so a mismatch can be
# investigated after the fact -- the staged fs is overwritten by the next build,
# and the first run of this harness hit exactly that wall.
# ============================================================================
set -euo pipefail

FS="${1:?usage: stagedfs_digest.sh <FS_DIR> <OUT_DIR> <LABEL>}"
OUT="${2:?}"
LABEL="${3:?}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NONDET="${LAB_NONDET:-$HERE/nondeterministic.txt}"

[ -d "$FS" ] || { echo "[digest] no staged rootfs at $FS" >&2; exit 2; }
mkdir -p "$OUT"

INV="$OUT/stagedfs-inventory-${LABEL}.txt"
HSH="$OUT/stagedfs-hashes-${LABEL}.txt"

( cd "$FS" && find . \( -type f -o -type l -o -type d \) -printf '%y %m %p %l\n' | LC_ALL=C sort ) > "$INV"
( cd "$FS" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum ) > "$HSH"

DIGEST="$(cat "$INV" "$HSH" | sha256sum | cut -d' ' -f1)"

# --- normalised digest ------------------------------------------------------
PATTERNS=()
if [ -f "$NONDET" ]; then
  while IFS= read -r line; do
    line="${line%%#*}"; line="$(echo "$line" | tr -d '[:space:]')"
    [ -n "$line" ] && PATTERNS+=("$line")
  done < "$NONDET"
fi

HSHN="$OUT/stagedfs-hashes-norm-${LABEL}.txt"
cp "$HSH" "$HSHN"
EXCLUDED=0
ARCH="$OUT/nondet-files-${LABEL}"
for pat in "${PATTERNS[@]+"${PATTERNS[@]}"}"; do
  # Match on the PATH field (everything after the hash + two spaces).
  before=$(wc -l < "$HSHN")
  awk -v p="$pat" 'BEGIN{n=0}
    { path=$0; sub(/^[0-9a-f]+  /,"",path);
      if (path ~ "^"(gensub(/\*/,"[^ ]*","g",p))"$") next; print }' "$HSHN" > "$HSHN.tmp" 2>/dev/null \
    || grep -v -F -- "$pat" "$HSHN" > "$HSHN.tmp"
  mv "$HSHN.tmp" "$HSHN"
  EXCLUDED=$(( EXCLUDED + before - $(wc -l < "$HSHN") ))
done

INVN="$OUT/stagedfs-inventory-norm-${LABEL}.txt"
cp "$INV" "$INVN"

DIGEST_NORM="$(cat "$INVN" "$HSHN" | sha256sum | cut -d' ' -f1)"

# --- archive the excluded files, and structurally fingerprint any binaries ---
# Small text files are copied verbatim; ELF objects get a section+symbol digest,
# which an embedded date string does not move but a real code change does.
mkdir -p "$ARCH"
for pat in "${PATTERNS[@]+"${PATTERNS[@]}"}"; do
  for f in $(cd "$FS" && eval ls -1d "$pat" 2>/dev/null || true); do
    src="$FS/$f"; [ -f "$src" ] || continue
    safe="$(echo "$f" | sed 's#^\./##; s#/#_#g')"
    if head -c4 "$src" | grep -q ELF 2>/dev/null; then
      { readelf -SW "$src" 2>/dev/null; readelf -sW "$src" 2>/dev/null; stat -c%s "$src"; } \
        | sha256sum | cut -d' ' -f1 > "$ARCH/$safe.elfstruct"
    elif [ "$(stat -c%s "$src")" -le 65536 ]; then
      cp "$src" "$ARCH/$safe"
    fi
  done
done

{
  echo "label=$LABEL"
  echo "digest=$DIGEST"
  echo "digest_norm=$DIGEST_NORM"
  echo "entries=$(wc -l < "$INV")"
  echo "files=$(wc -l < "$HSH")"
  echo "excluded=$EXCLUDED"
} > "$OUT/stagedfs-digest-${LABEL}.env"

echo "[lab-digest] label=$LABEL digest=$DIGEST norm=$DIGEST_NORM entries=$(wc -l < "$INV") files=$(wc -l < "$HSH") excluded=$EXCLUDED"
