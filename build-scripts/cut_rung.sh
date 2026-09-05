#!/bin/bash
# cut_rung.sh - cut one source rung: export the patches, prove they replay,
# record provenance, check the overlays, move the CI pin, and re-run the PII
# rules. One command, so "push then build" stops depending on remembering five
# coupled files.
#
#   ./build-scripts/cut_rung.sh --version v2.3.4
#
# Runs in WSL against the canon build clone. READ-ONLY against that clone (all
# replay work happens in a throwaway worktree) and it NEVER commits or pushes -
# it leaves a reviewable diff in the lean repo and prints what is left to do.
#
# What it does, in order:
#   1. preflight        branch, clean tree, version format, EXTENDNO agreement
#   2. export           format-patch since the last rung, doc hunks excluded
#   3. normalize        From: identity + message scrub
#   3b. hidden chars    the new patches' ADDED lines must be readable by a
#                       person: no bidi overrides, zero-width/format or control
#                       characters, invalid UTF-8, look-alike letters in
#                       identifiers (reaper_hiddencheck.py). Runs BEFORE
#                       install so a hit leaves the lean repo untouched.
#   4. install          copy into patches/, assert gapless
#   5. replay           git am the WHOLE series onto the pinned base; capture
#                       both tree hashes; assert the version and the diff
#   6. provenance       gen_provenance.py + source_tree_from_series + metadata
#   7. overlays         file-overlap check against overlays/<MODEL>.patch
#   8. pin              EXPECTED_VERSION in public-build.yml
#   9. hygiene          the two PII patterns + allowlist sanity
#
# See docs/RELEASE-PROCESS.md ("Cutting a rung") and docs/GPL-MERGE.md §10.

set -uo pipefail

CLONE=${REAPER_CLONE:-/home/reaper/asuswrt-be96u}
LEAN=${REAPER_LEAN:-/mnt/c/Users/natha/AppData/Roaming/VSC/ASUS/ASUS-Merlin-Reaper}
BRANCH=${REAPER_BRANCH:-be96u-only}
BASE=a7ebfa133ad7e5efc23ed6bb8ee912bc72fd00b3     # the pinned upstream base; never moves
IDENTITY='reaper <theunbounddeveloper@outlook.com>'

VERSION=""; SINCE=""; DO_PIN=1; KEEP_WT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --since)   SINCE="$2";   shift 2 ;;
    --no-pin)  DO_PIN=0;     shift ;;
    --keep-worktree) KEEP_WT=1; shift ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

die()  { echo; echo "FAIL: $*" >&2; exit 1; }
step() { echo; echo "=== $* ==="; }

[ -n "$VERSION" ] || die "--version vX.Y.Z is required"
[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+[a-z]?$ ]] || die "version must look like v2.3.4 or v2.3.4a"
EXTEND="Reaper_$VERSION"

# ---------------------------------------------------------------- 1. preflight
step "1. preflight"
[ -d "$CLONE/.git" ] || die "no build clone at $CLONE"
[ -d "$LEAN/patches" ] || die "no lean repo at $LEAN"

cur=$(git -C "$CLONE" rev-parse --abbrev-ref HEAD)
[ "$cur" = "$BRANCH" ] || die "clone is on '$cur', expected '$BRANCH' (a sibling build leaves it switched)"

dirty=$(git -C "$CLONE" status --short --untracked-files=no | wc -l)
[ "$dirty" -eq 0 ] || die "canon tree has uncommitted tracked changes - commit the rung first"

HEAD_SHA=$(git -C "$CLONE" rev-parse --short=10 HEAD)
got_ver=$(sed -n 's/^EXTENDNO=//p' "$CLONE/release/src-rt/version.conf")
[ "$got_ver" = "$EXTEND" ] || die "version.conf says EXTENDNO=$got_ver but you asked for $EXTEND
       the rung commit must contain the version bump"
echo "  clone   $CLONE @ $HEAD_SHA ($BRANCH)"
echo "  version $EXTEND"

# The previous rung's tip is recorded as the newest manifest entry's build_commit,
# so the export range needs no bookkeeping of its own.
if [ -z "$SINCE" ]; then
  SINCE=$(python3 - "$LEAN/provenance/manifest.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1],encoding="utf-8"))
print(m["releases"][0]["build_commit"])
PY
) || die "cannot read the previous build_commit from provenance/manifest.json"
fi
git -C "$CLONE" cat-file -e "${SINCE}^{commit}" 2>/dev/null || die "--since '$SINCE' is not a commit in the clone"
PREV_VER=$(python3 - "$LEAN/provenance/manifest.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding="utf-8"))["releases"][0]["version"])
PY
)
echo "  since   $SINCE (previous rung $PREV_VER)"

new_commits=$(git -C "$CLONE" rev-list --count "$SINCE..HEAD")
[ "$new_commits" -gt 0 ] || die "no commits between $SINCE and HEAD - nothing to cut"
echo "  commits $new_commits to export"

HAVE=$(ls -1 "$LEAN"/patches/[0-9]*.patch 2>/dev/null | wc -l)
START=$((HAVE + 1))
echo "  patches $HAVE existing, new series starts at $(printf '%04d' $START)"

# ------------------------------------------------------------------- 2. export
step "2. export (doc hunks excluded)"
STAGE=$(mktemp -d)
trap '[ "$KEEP_WT" = 0 ] && rm -rf "$STAGE"' EXIT
git -C "$CLONE" format-patch "$SINCE..HEAD" -o "$STAGE" -N --no-cover-letter \
    --start-number "$START" -- \
    . ':(exclude)*.md' ':(exclude)docs' ':(exclude).mailmap' \
    ':(exclude).gitattributes' ':(exclude).gitignore' >/dev/null \
  || die "format-patch failed"
made=$(ls -1 "$STAGE"/*.patch 2>/dev/null | wc -l)
[ "$made" -gt 0 ] || die "format-patch produced nothing (was the rung docs-only?)"
echo "  $made patch file(s)"

# ---------------------------------------------------------------- 3. normalize
step "3. normalize identity + scrub messages"
# Assembled from fragments so this script is not itself a PII-scan hit (the same
# trick repo-hygiene.yml uses on its own patterns).
OLDHOME='/home/na'"than"
OLDREPO='ASUS-Merlin''-Reaper'
for p in "$STAGE"/*.patch; do
  sed -i \
    -e "/^From: Eric Sauvageau <merlin@asuswrt-merlin.net>/! s|^From: .*|From: $IDENTITY|" \
    -e "s|$OLDHOME|/home/builder|g" \
    -e "s|$OLDREPO|AM-Reaper|g" "$p"
done
echo "  From: -> $IDENTITY, build-host + repo-name strings scrubbed"

# ------------------------------------------------------- 3b. hidden characters
step "3b. hidden characters (the new code must be readable by a person)"
# Only the ADDED lines of the freshly exported patches, and before they touch
# the lean repo: bidirectional overrides, zero-width and format characters,
# control bytes, invalid UTF-8, look-alike letters inside identifiers are FATAL;
# odd spaces, eval/atob shapes and very long lines are printed as warnings and
# do not stop the cut. .github/hidden-allowlist.txt downgrades vendored paths.
# A FAIL means the source commit carries something a reviewer cannot see - fix
# the commit, never the allowlist, then re-cut.
python3 "$LEAN/build-scripts/reaper_hiddencheck.py" \
    --allowlist "$LEAN/.github/hidden-allowlist.txt" --max-details 8 "$STAGE"/*.patch \
  || die "hidden-character scan FAILED on the new patches - nothing installed"

# ------------------------------------------------------------------ 4. install
step "4. install into patches/"
# Plain cp, NOT cp -p: the lean repo normally sits on a DrvFs /mnt/c mount, where
# preserving times fails ("Operation not permitted") and cp exits non-zero even
# though every file copied. Patch mtimes carry no meaning - git records content,
# and .gitattributes -text is what keeps these byte-exact.
cp "$STAGE"/*.patch "$LEAN/patches/" || die "copy into patches/ failed"
mapfile -t nums < <(ls -1 "$LEAN"/patches/[0-9]*.patch | xargs -n1 basename | cut -c1-4 | sort)
count=${#nums[@]}
diff <(seq -f '%04g' 1 "$count") <(printf '%s\n' "${nums[@]}") >/dev/null \
  || die "patch numbering is not gapless 0001..$(printf '%04d' "$count")"
echo "  $count patches, gapless"

# ------------------------------------------------------------------- 5. replay
step "5. replay the full series onto the pinned base"
WT="$CLONE/../wt_cut_$$"
git -C "$CLONE" worktree add --detach "$WT" "$BASE" >/dev/null 2>&1 || die "cannot create the replay worktree"
cleanup_wt() { [ "$KEEP_WT" = 1 ] || { git -C "$CLONE" worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"; }; }

# --keep-cr is mandatory: some third-party files (lltdc) are CRLF and the series
# fails at qospktio.c without it.
if ! git -C "$WT" am --keep-cr $(ls -1 "$LEAN"/patches/[0-9]*.patch | sort) >"$STAGE/am.log" 2>&1; then
  tail -20 "$STAGE/am.log"
  KEEP_WT=1; die "the series does not apply cleanly - worktree kept at $WT"
fi

SER_ROUTER=$(git -C "$WT" rev-parse HEAD:release/src/router)
SER_SRCRT=$(git -C "$WT" rev-parse HEAD:release/src-rt)
BLD_ROUTER=$(git -C "$CLONE" rev-parse HEAD:release/src/router)
BLD_SRCRT=$(git -C "$CLONE" rev-parse HEAD:release/src-rt)
ser_ver=$(sed -n 's/^EXTENDNO=//p' "$WT/release/src-rt/version.conf")
[ "$ser_ver" = "$EXTEND" ] || { cleanup_wt; die "the series produces EXTENDNO=$ser_ver, not $EXTEND"; }

# The only legitimate difference is vendored *.md docs the pathspec strips.
mapfile -t diffs < <(git -C "$CLONE" diff --name-only "$(git -C "$WT" rev-parse HEAD)" HEAD -- release/src/router release/src-rt)
bad=0; for f in "${diffs[@]:-}"; do [ -z "$f" ] && continue; [[ "$f" == *.md ]] || { echo "  UNEXPECTED: $f"; bad=1; }; done
[ "$bad" -eq 0 ] || { KEEP_WT=1; cleanup_wt; die "the replayed tree differs from HEAD in non-doc files (worktree kept)"; }
echo "  series EXTENDNO   $ser_ver"
echo "  series tree       $SER_ROUTER (release/src/router)"
echo "  build-commit tree $BLD_ROUTER"
echo "  diff vs HEAD      ${#diffs[@]} file(s), all *.md (expected)"
cleanup_wt

# --------------------------------------------------------------- 6. provenance
step "6. provenance"
python3 "$LEAN/build-scripts/gen_provenance.py" --version "$VERSION" --commit "$HEAD_SHA" \
        --patch-count "$count" --no-images || die "gen_provenance.py failed"
python3 - "$LEAN/provenance/manifest.json" "$VERSION" "$SER_ROUTER" "$SER_SRCRT" "$PREV_VER" <<'PY' || die "manifest update failed"
import json, sys, collections, datetime
path, ver, ser_router, ser_srcrt, prev = sys.argv[1:6]
m = json.load(open(path, encoding="utf-8"))
rel = next(r for r in m["releases"] if r["version"] == ver)
rel["source_tree_from_series"] = {"release/src/router": ser_router, "release/src-rt": ser_srcrt}
rel.setdefault("images", [])
rel.setdefault("models", ["RT-BE96U", "RT-BE86U", "RT-BE88U", "GT-BE98", "GT-BE98_PRO"])
rel["date"] = datetime.date.today().isoformat()
rel["parent"] = prev
rel.setdefault("summary", "TODO: what this rung changes, in prose. "
                          "NO IMAGES YET - this entry records the source rung; "
                          "image hashes are added when the build ships.")
rel.setdefault("models_note", "TODO: overlay-overlap result (see step 7).")
order = ["version", "firmware", "build_commit", "source_tree", "source_tree_from_series",
         "images", "patch_count", "verifiable", "models", "date", "parent", "summary",
         "models_note"]
o = collections.OrderedDict((k, rel[k]) for k in order if k in rel)
for k, v in rel.items():
    o.setdefault(k, v)
m["releases"][m["releases"].index(rel)] = o
with open(path, "w", encoding="utf-8") as f:
    json.dump(m, f, indent=2, ensure_ascii=False); f.write("\n")
print(f"  {ver}: patch_count {rel['patch_count']}, verifiable, parent {prev}")
print("  ! summary/models_note carry TODO text - write the prose before committing")
PY

# ----------------------------------------------------------------- 7. overlays
step "7. overlay overlap"
python3 - "$LEAN" "$START" <<'PY'
import glob, os, sys
lean, start = sys.argv[1], int(sys.argv[2])
def files(p):
    s = set()
    for l in open(p, encoding="utf-8", errors="replace"):
        if l.startswith("--- a/") or l.startswith("+++ b/"):
            s.add(l[6:].strip())
    s.discard("/dev/null"); return s
new = set()
for p in sorted(glob.glob(f"{lean}/patches/[0-9]*.patch")):
    if int(os.path.basename(p)[:4]) >= start:
        new |= files(p)
print(f"  this rung touches {len(new)} file(s)")
hit = False
for ov in sorted(glob.glob(f"{lean}/overlays/*.patch")):
    inter = new & files(ov)
    if inter:
        hit = True
        print(f"  OVERLAP {os.path.basename(ov)}: {sorted(inter)}")
if hit:
    print("  ! regenerate the affected overlays/<MODEL>.patch before the fleet run")
else:
    print("  no overlap with any overlays/<MODEL>.patch - siblings pick this up from the series")
PY

# ---------------------------------------------------------------------- 8. pin
step "8. CI version pin"
YML="$LEAN/.github/workflows/public-build.yml"
if [ "$DO_PIN" = 1 ]; then
  if grep -q "'Reaper_v[0-9][^']*'" "$YML"; then
    # NOT `sed -i`. This file lives on the Windows mount, where sed -i writes a
    # temp file and renames it over the target: the rename cannot carry the
    # permissions across, logs "preserving permissions ... Operation not
    # permitted", and leaves the result with the Windows ReadOnly attribute set
    # - so the NEXT cut_fleet aborts at preflight 0 and every cut broke the one
    # after it. Redirecting onto the existing file truncates it in place, reuses
    # the inode, and therefore keeps its attributes. Applies to any sed -i these
    # scripts run against a path under /mnt/c.
    _pin=$(mktemp)
    sed "s/'Reaper_v[0-9][^']*'/'$EXTEND'/" "$YML" > "$_pin" \
      || { rm -f "$_pin"; die "could not rewrite EXPECTED_VERSION in $YML"; }
    cat "$_pin" > "$YML" \
      || { rm -f "$_pin"; die "could not write EXPECTED_VERSION into $YML"; }
    rm -f "$_pin"
    [ -w "$YML" ] || echo "  ! $YML is no longer writable - the next cut will abort"
    echo "  EXPECTED_VERSION -> $EXTEND"
  else
    echo "  ! could not find the EXPECTED_VERSION literal - set it by hand"
  fi
else
  echo "  skipped (--no-pin)"
fi

# ------------------------------------------------------------------ 9. hygiene
step "9. hygiene"
p1='[A-Za-z0-9._%+-]+@gm''ail\.com'
p2="$OLDHOME"
# The allowlist has to be applied HERE, not just reported on below. Four patches
# (0103/0222/0223/0294) carry third-party upstream author addresses in vendored
# changelogs and have been allowlisted for exactly that reason since 2026-08-09 -
# so an allowlist-blind grep prints the same four names on every single cut. That
# is how a genuine leak gets lost: the operator learns the warning is always there
# and stops reading it. Allowlisted hits are counted, not listed; anything NOT on
# the list is the thing worth stopping for.
# (no trap here: the script already owns an EXIT trap for $STAGE, and this temp
# file is removed explicitly a few lines down.)
allowed=$(mktemp)
grep -vE '^\s*(#|$)' "$LEAN/.github/pii-allowlist.txt" > "$allowed"
new_hits=0; old_hits=0
while IFS= read -r f; do
  rel="patches/$(basename "$f")"
  if grep -qxF "$rel" "$allowed"; then
    old_hits=$((old_hits + 1))
  else
    [ "$new_hits" -eq 0 ] && echo "  ! PII pattern hit in a NOT-allowlisted patch:"
    new_hits=$((new_hits + 1))
    echo "    $rel"
  fi
done < <(grep -rIlE "$p1|$p2" "$LEAN/patches"/[0-9]*.patch 2>/dev/null)
if [ "$new_hits" -gt 0 ]; then
  echo "    fix the source commit message - do NOT just add it to the allowlist"
else
  echo "  no un-allowlisted PII-pattern hits in patches/"
fi
[ "$old_hits" -gt 0 ] && echo "  ($old_hits allowlisted third-party hit(s), expected - see .github/pii-allowlist.txt)"
rm -f "$allowed"
missing=0
while IFS= read -r line; do
  case "$line" in ''|'#'*) continue ;; esac
  [ -e "$LEAN/$line" ] || { echo "  ! allowlist path no longer exists: $line"; missing=1; }
done < "$LEAN/.github/pii-allowlist.txt"
[ "$missing" -eq 0 ] && echo "  pii-allowlist paths all resolve"

# -------------------------------------------------------------------- summary
cat <<EOF

======================================================================
 RUNG $VERSION CUT - nothing committed, nothing pushed
======================================================================
 patches/          $made new, $count total, gapless, replay-verified
 provenance        entry added (source_tree + source_tree_from_series)
 EXPECTED_VERSION  $([ "$DO_PIN" = 1 ] && echo "$EXTEND" || echo "unchanged (--no-pin)")

 STILL YOURS TO DO
   1. write the provenance summary + models_note (they say TODO)
   2. add the docs/CHANGELOG.md section - release notes are extracted from it
   3. review:  git -C "$LEAN" diff
   4. commit + push, then dispatch the build (leave the version field blank)

 Reminder: a manual per-model publish does NOT run refresh_manifest, so the
 router update check keeps advertising the previous version until you run
 build-scripts/refresh_manifest.py.
EOF
