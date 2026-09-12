#!/bin/bash
# prune_releases.sh [--yes]   -- retire GitHub releases the retention rule no longer keeps.
#
# Retention rule (2026-09-12, owner): keep
#   1. every release the LIVE update manifest references (updates/manifest_3006.txt
#      on origin/main) - stable line + advertised beta line; a fielded router
#      downloads from exactly these tags, so deleting one breaks its update;
#   2. the previous stable line (rollback target), derived as the highest stable
#      version below the manifest's stable version;
#   3. nothing else. Betas are disposable once the next beta or their stable ships.
# Releases are deleted; GIT TAGS ARE NEVER DELETED (no --cleanup-tag): the tag is
# where the source correspondence lives (patch series, pinned base, provenance).
# Without --yes this only prints the plan. Needs `gh auth login` as the repo owner.
set -eu
REPO=TheUnboundDeveloper/AM-Reaper
LEAN=$(cd "$(dirname "$0")/.." && pwd)
YES=0; [ "${1:-}" = "--yes" ] && YES=1
git -C "$LEAN" fetch -q origin main
MANI=$(git -C "$LEAN" show origin/main:updates/manifest_3006.txt)
keep_ref=$(echo "$MANI" | grep -oE 'releases/download/[^/]+' | sed 's#releases/download/##' | sort -u)
stable_ver=$(echo "$MANI" | grep -vE '^#' | grep -vE '#[A-Za-z]+-beta#' | awk -F'#' '{print $3}' | sort -uV | tail -1)
all=$(gh release list -R "$REPO" --limit 500 --json tagName --jq '.[].tagName')
# previous stable line: tags vX.Y.Z-MODEL (no -beta) with X.Y.Z below the manifest's stable
prev_ver=$(echo "$all" | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+-[A-Z]' | sed -E 's/^v([0-9.]+)-.*/\1/' | sort -uV \
           | awk -v s="$stable_ver" '$0 != s' \
           | while read -r v; do [ "$(printf '%s\n%s\n' "$v" "$stable_ver" | sort -V | tail -1)" = "$stable_ver" ] && echo "$v"; done | tail -1)
keep_prev=$(echo "$all" | grep -E "^v${prev_ver}-[A-Z]" || true)
keep=$(printf '%s\n%s\n' "$keep_ref" "$keep_prev" | grep -v '^$' | sort -u)
del=$(comm -23 <(echo "$all" | sort -u) <(echo "$keep"))
echo "manifest stable line: v$stable_ver   previous stable line kept: v${prev_ver:-?}"
echo "releases total: $(echo "$all" | grep -c .)   keep: $(echo "$keep" | grep -c .)   delete: $(echo "$del" | grep -c .)"
echo; echo "KEEP:"; echo "$keep" | sed 's/^/  /'
echo; echo "DELETE:"; echo "$del" | tr '\n' ' ' | fold -s -w 110 | sed 's/^/  /'; echo
[ "$YES" = 1 ] || { echo; echo "(dry run - pass --yes to delete the releases above; tags are kept regardless)"; exit 0; }
echo; n=0; fail=0; total=$(echo "$del" | grep -c .)
for t in $del; do
  if gh release delete "$t" -R "$REPO" --yes >/dev/null 2>&1; then n=$((n+1)); printf '\r  deleted %d/%d  %-32s' "$n" "$total" "$t"
  else fail=$((fail+1)); echo; echo "  FAILED: $t"; fi
done
echo; echo "deleted: $n   failed: $fail"
echo "releases now: $(gh release list -R "$REPO" --limit 500 --json tagName --jq '.[].tagName' | grep -c .)   tags still on origin: $(git -C "$LEAN" ls-remote --tags origin | grep -vc '\^{}')"
