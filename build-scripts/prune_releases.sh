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
#
# FAIL CLOSED (review 2026-09-12, R08): the first cut derived the keep-set from the
# manifest with no check that the manifest was usable. An empty or comment-only
# manifest (a bad push, a wrong branch) produced an empty keep-set and a plan that
# deleted EVERY release - and `--yes` would have done it. Every invariant the rule
# rests on is now asserted before a plan is printed, and a plan that fails one is
# refused, with or without --yes.
# set -e and -u, deliberately NOT pipefail: with pipefail a `grep` that matches nothing turns
# the whole pipeline into a silent abort with no message, which is the one failure mode an
# operator must never get from this script. Every pipeline below ends in a command whose
# status is meaningful (sort, tail, count), and the invariants are asserted explicitly.
set -eu
REPO=TheUnboundDeveloper/AM-Reaper
LEAN=$(cd "$(dirname "$0")/.." && pwd)
YES=0; [ "${1:-}" = "--yes" ] && YES=1
die() { echo "REFUSED: $*" >&2; exit 1; }
count() { grep -c . || true; }          # `grep -c` exits 1 on zero matches; that is a number, not an error
git -C "$LEAN" fetch -q origin main
MANI=$(git -C "$LEAN" show origin/main:updates/manifest_3006.txt)
records=$(echo "$MANI" | grep -vE '^[[:space:]]*(#|$)' | count)   # grep -v on an all-comment file exits 1; count() is the pipeline's status
[ "$records" -gt 0 ] || die "the manifest on origin/main has no records (empty or comment-only) - nothing can be planned from it"
keep_ref=$(echo "$MANI" | grep -oE 'releases/download/[^/]+' | sed 's#releases/download/##' | sort -u)
[ -n "$keep_ref" ] || die "the manifest references no release download - it is not a manifest this rule understands"
stable_ver=$(echo "$MANI" | grep -vE '^#' | grep -vE '#[A-Za-z]+-beta#' | awk -F'#' '{print $3}' | sort -uV | tail -1)
echo "$stable_ver" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || die "no stable line in the manifest (stable version parsed as '${stable_ver:-}')"
all=$(gh release list -R "$REPO" --limit 500 --json tagName --jq '.[].tagName')
n_all=$(echo "$all" | count)
[ "$n_all" -gt 0 ] || die "gh returned no releases - not authenticated, or the wrong repository"
[ "$n_all" -lt 500 ] || die "gh returned 500 releases - the list may be truncated; raise --limit before planning"
# every release the manifest points a router at must exist, or the manifest and the releases disagree
for t in $keep_ref; do
  echo "$all" | grep -qx -- "$t" || die "the manifest references release $t, which does not exist - fix the manifest or the releases first"
done
# previous stable line: tags vX.Y.Z-MODEL (no -beta) with X.Y.Z below the manifest's stable
prev_ver=$(echo "$all" | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+-[A-Z]' | sed -E 's/^v([0-9.]+)-.*/\1/' | sort -uV \
           | awk -v s="$stable_ver" '$0 != s' \
           | while read -r v; do [ "$(printf '%s\n%s\n' "$v" "$stable_ver" | sort -V | tail -1)" = "$stable_ver" ] && echo "$v"; done | tail -1 || true)
[ -n "$prev_ver" ] || die "no stable line below v$stable_ver exists among the releases - there is no rollback target to keep"
keep_prev=$(echo "$all" | grep -E "^v${prev_ver}-[A-Z]" || true)
keep=$(printf '%s\n%s\n' "$keep_ref" "$keep_prev" | grep -v '^$' | sort -u)
n_keep=$(echo "$keep" | count)
[ "$n_keep" -ge 2 ] || die "the keep-set has $n_keep release(s); the rule always keeps at least the current and the previous stable"
del=$(comm -23 <(echo "$all" | sort -u) <(echo "$keep"))
n_del=$(echo "$del" | count)
[ "$n_del" -lt "$n_all" ] || die "the plan would delete every release ($n_del of $n_all) - refusing"
echo "manifest stable line: v$stable_ver   previous stable line kept: v$prev_ver"
echo "releases total: $n_all   keep: $n_keep   delete: $n_del"
echo; echo "KEEP:"; echo "$keep" | sed 's/^/  /'
echo; echo "DELETE:"; echo "$del" | tr '\n' ' ' | fold -s -w 110 | sed 's/^/  /'; echo
[ "$YES" = 1 ] || { echo; echo "(dry run - pass --yes to delete the releases above; tags are kept regardless)"; exit 0; }
[ "$n_del" -gt 0 ] || { echo "nothing to delete"; exit 0; }
echo; n=0; fail=0
for t in $del; do
  if gh release delete "$t" -R "$REPO" --yes >/dev/null 2>&1; then n=$((n+1)); printf '\r  deleted %d/%d  %-32s' "$n" "$n_del" "$t"
  else fail=$((fail+1)); echo; echo "  FAILED: $t"; fi
done
echo; echo "deleted: $n   failed: $fail"
echo "releases now: $(gh release list -R "$REPO" --limit 500 --json tagName --jq '.[].tagName' | count)   tags still on origin: $(git -C "$LEAN" ls-remote --tags origin | grep -vc '\^{}' || true)"
