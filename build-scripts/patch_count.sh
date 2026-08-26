#!/bin/bash
# patch_count.sh - the ONE place that answers "how many patches is this tree?"
#
# WHY THIS EXISTS
# ---------------
# The About page's "Patches applied" figure has now regressed three times
# (v2.5.0-v2.5.8 shipped a stale 465; v2.7.6 shipped a dash; v2.7.7 again), and
# every fix so far has patched a different symptom of the SAME design flaw: the
# count was read out of the lean repo's patches/ DIRECTORY.
#
# That directory is a DOWNSTREAM artifact. It is regenerated at publish time, so
# during a local build it is routinely one rung behind the tree being compiled
# (see repo-topology: "the series TRAILS the built fleet"). Worse, the count was
# inferred from patch FILENAMES, which meant it also depended on whether the
# rung's tip happened to be the version-bump patch, and on resolving a path into
# a different repository from whatever directory the build engine was synced to.
# Three independent ways to silently produce a wrong number or none at all.
#
# The tree being built already knows the answer exactly. The published series is
# `git format-patch <BASE>..HEAD` with the GPL-MERGE section 10 doc-exclude
# pathspec, minus the model-strip commit. Counting the commits that range would
# emit is deterministic, needs no second repository, and is correct the instant a
# commit lands - long before anyone regenerates patches/.
#
# Verified 2026-08-25 against the real series at v2.7.7: tree-derived 541,
# patches/ 541. Use --verify to re-assert that equality whenever both exist.
#
# USAGE
#   patch_count.sh <source-tree-root>              -> prints the count, e.g. 541
#   patch_count.sh <source-tree-root> --series     -> prints the series version
#   patch_count.sh <source-tree-root> --verify DIR -> compare against a patches dir
#
# EXIT
#   0  answer printed on stdout
#   2  bad usage
#   3  cannot determine (not a git tree / base commit absent) - prints nothing,
#      so a caller can stamp an empty field, which renders as an honest dash
#   4  --verify mismatch (message on stderr)

case "${1:-}" in
  -h|--help) sed -n "2,38 p" "$0" | sed "s/^# \?//"; exit 0 ;;
esac
set -uo pipefail

# The upstream pin every Reaper patch is generated against, and the one commit
# that is deliberately dropped from the published series (it strips the sibling
# models out of the vendor tree and is not part of the Reaper changeset).
BASE=a7ebfa133ad7e5efc23ed6bb8ee912bc72fd00b3
STRIP=48b0698465

SRC="${1:-}"
MODE="${2:-count}"
[ -n "$SRC" ] || { echo "usage: patch_count.sh <source-tree-root> [--series|--verify DIR]" >&2; exit 2; }

git -C "$SRC" rev-parse --git-dir >/dev/null 2>&1 || exit 3
git -C "$SRC" cat-file -e "$BASE^{commit}" 2>/dev/null || exit 3

series_version() {
	grep '^EXTENDNO=' "$SRC/release/src-rt/version.conf" 2>/dev/null \
		| grep -oE 'v[0-9]+\.[0-9]+(\.[0-9]+)?[a-z]?' | head -1
}

count_patches() {
	# Same range + pathspec as GPL-MERGE section 10, so this counts exactly what
	# format-patch would emit. The excludes drop pure-doc commits and strip doc
	# hunks from mixed ones - a commit touching ONLY excluded paths produces no
	# patch and correctly does not appear here.
	local all strip_sha n
	all=$(git -C "$SRC" log --format=%H "$BASE"..HEAD -- . \
		':(exclude)*.md' ':(exclude)docs' ':(exclude).mailmap' \
		':(exclude).gitattributes' ':(exclude).gitignore' 2>/dev/null) || return 1
	[ -n "$all" ] || return 1
	n=$(printf '%s\n' "$all" | grep -c .)
	strip_sha=$(git -C "$SRC" rev-parse "$STRIP" 2>/dev/null)
	if [ -n "$strip_sha" ] && printf '%s\n' "$all" | grep -q "^$strip_sha$"; then
		n=$((n - 1))
	fi
	printf '%s\n' "$n"
}

case "$MODE" in
count)
	N=$(count_patches) || exit 3
	printf '%s\n' "$N"
	;;
--series)
	SV=$(series_version)
	[ -n "$SV" ] || exit 3
	printf '%s\n' "$SV"
	;;
--verify)
	PD="${3:-}"
	[ -n "$PD" ] || { echo "usage: patch_count.sh <src> --verify <patches-dir>" >&2; exit 2; }
	N=$(count_patches) || { echo "patch_count: cannot derive count from $SRC" >&2; exit 3; }
	# Missing/empty patches dir is NOT a mismatch: a local rung ahead of its cut
	# legitimately has no regenerated series yet. Only disagree when both exist.
	D=$(ls "$PD"/*.patch 2>/dev/null | grep -c .)
	if [ "$D" -eq 0 ]; then
		echo "patch_count: tree=$N, no patches/ to compare (not yet cut) - OK" >&2
		printf '%s\n' "$N"
		exit 0
	fi
	if [ "$N" != "$D" ]; then
		echo "patch_count: MISMATCH tree=$N patches/=$D in $PD" >&2
		echo "  the series is stale or the tree has commits the cut has not exported;" >&2
		echo "  regenerate per GPL-MERGE section 10 before publishing." >&2
		exit 4
	fi
	echo "patch_count: tree=$N patches/=$D - MATCH" >&2
	printf '%s\n' "$N"
	;;
*)
	echo "patch_count: unknown mode '$MODE'" >&2; exit 2
	;;
esac
