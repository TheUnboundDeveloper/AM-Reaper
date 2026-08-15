#!/bin/bash
# ============================================================================
# ab_compare.sh -- the measurement that decides whether a change is promoted
# ----------------------------------------------------------------------------
# Usage:
#   ab_compare.sh --model RT-BE96U [--variants "MCP"] [--repeat 2]
#                 [--compare single-pass|config-keep] [--no-warmup]
#
# Runs arm A (baseline) and arm B (candidate) ALTERNATELY, `--repeat` times
# each, and writes a verdict.
#
# --- why the sequence looks like this ---------------------------------------
# A/B on a shared warm tree has one serious confound: each build leaves the tree
# warmer than it found it, so whichever arm runs second is flattered. Three
# things control for that:
#
#   1. A discarded WARM-UP build first. The tree state after any completed build
#      is the steady state; the first build after a source edit, a branch
#      change or an idle week is not, and comparing against it measures the
#      history rather than the change.
#   2. ALTERNATION, A B A B, not A A B B. If warming still drifts across the
#      session, alternating spreads the drift across both arms instead of
#      loading it onto one.
#   3. BOTH replicates must agree. A change that wins once and loses once has
#      not been demonstrated, however good the average looks.
#
# --- what makes a candidate acceptable --------------------------------------
# Speed is the LAST of the three criteria, and the only one that is negotiable.
#   1. Staged-fs digest identical between arms, per variant, every replicate.
#   2. reaper_verify: no FAIL in any run.
#   3. Faster in every replicate.
# Criterion 1 is the one that catches the failure this project actually suffers
# from: a build that is wrong in a way every gate passes. reaper_verify has
# signed off on a stripped dictionary and a missing IPSec stack; the digest
# would not have.
# ============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab_env.sh
source "$HERE/lab_env.sh"

MODEL=""; VARIANTS="MCP"; REPEAT=2; COMPARE="single-pass"; WARMUP=1; BASE_SP="off"; ORDER="AB"

while [ $# -gt 0 ]; do
  case "$1" in
    --model)      MODEL="$2"; shift 2;;
    --variants)   VARIANTS="$2"; shift 2;;
    --repeat)     REPEAT="$2"; shift 2;;
    --compare)    COMPARE="$2"; shift 2;;
    --base-single-pass) BASE_SP="$2"; shift 2;;
    --order)      ORDER="$2"; shift 2;;
    --no-warmup)  WARMUP=0; shift;;
    -h|--help)    sed -n '2,40p' "$0"; exit 0;;
    *) lab_die "unknown argument '$1'";;
  esac
done
case "$ORDER" in AB|BA) ;; *) lab_die "--order must be AB or BA";; esac
[ -n "$MODEL" ] || lab_die "--model is required"

# One experiment per session. Two flags changed at once produce a number that
# cannot be attributed to either.
case "$COMPARE" in
  single-pass)  A_ARGS=(--single-pass off);            B_ARGS=(--single-pass auto);;
  config-keep)  A_ARGS=(--single-pass "$BASE_SP");     B_ARGS=(--single-pass "$BASE_SP" --config-keep);;
  *) lab_die "--compare must be single-pass or config-keep";;
esac

SESSION="$RESULTS_ROOT/ab-$(date +%Y%m%d-%H%M%S)-${MODEL}-${COMPARE}"
mkdir -p "$SESSION"
REPORT="$SESSION/REPORT.md"

lab_hr
echo " A/B session: $COMPARE"
echo " model   : $MODEL   variants: [$VARIANTS]"
echo " arms    : A = ${A_ARGS[*]}"
echo "           B = ${B_ARGS[*]}"
echo " repeat  : $REPEAT  (warm-up: $([ "$WARMUP" = 1 ] && echo yes || echo no))"
echo " builds  : $(( WARMUP + REPEAT * 2 ))  -- budget roughly $(( (WARMUP + REPEAT*2) * 10 )) minutes"
echo " evidence: $SESSION"
lab_hr

echo "pre-flight:"
lab_preflight || { echo "PRE-FLIGHT FAILED -- nothing built."; exit 9; }
lab_hr

# ---------------------------------------------------------------------------
run_one() {   # $1=arm-label $2=replicate  $3.. = extra lab_build args
  local arm="$1" rep="$2"; shift 2
  local dir="$SESSION/${arm}-r${rep}"
  mkdir -p "$dir"
  echo
  lab_hr
  echo " RUN  arm=$arm  replicate=$rep  $(date -u +%FT%TZ)"
  lab_hr
  bash "$HERE/lab_build.sh" --model "$MODEL" --variants "$VARIANTS" \
       --arm "$arm-r$rep" --run-dir "$dir" "$@" > "$dir/console.log" 2>&1
  local rc=$?
  local total; total=$(grep -oE '^\[lab-total\] seconds=[0-9]+' "$dir/build.log" 2>/dev/null | grep -oE '[0-9]+$' | tail -1)
  echo "  rc=$rc  total=${total:-?}s"
  grep -E '^\[lab-digest\]|^\[lab-decision\]' "$dir/build.log" 2>/dev/null | sed 's/^/  /'
  echo "${arm}|${rep}|${rc}|${total:-0}" >> "$SESSION/runs.tsv"

  # Compress the logs now that everything downstream has been read out of them.
  # A two-pass build log is ~4.75 MB and console.log is a byte-identical copy of
  # it (lab_build.sh tees one, this script redirects the other), so an A/B
  # session was writing ~19 MB of duplicated text. The report is built from
  # runs.tsv, the digest .env files, the verify output and the hash lists --
  # never from these -- so compressing here loses nothing. Kept rather than
  # deleted: a failed run's full log is the only thing that explains it.
  gzip -9f "$dir/build.log" "$dir/console.log" 2>/dev/null || true

  return $rc
}

digest_of() {   # $1=run-dir $2=variant  -> NORMALISED digest or "-"
  local f="$1/stagedfs-digest-${PREFIX}-${2}.env"
  [ -f "$f" ] && grep -oE '^digest_norm=.*' "$f" | cut -d= -f2 || echo "-"
}
digest_raw_of() {   # $1=run-dir $2=variant  -> RAW digest or "-"
  local f="$1/stagedfs-digest-${PREFIX}-${2}.env"
  [ -f "$f" ] && grep -oE '^digest=.*' "$f" | cut -d= -f2 || echo "-"
}
# The set of files whose hash differs between two runs. This is what makes the
# comparison sound: the warm-up and arm A share a configuration, so whatever
# differs between THEM is the build's own irreproducibility, not the change
# under test. A candidate whose difference set is a subset of that noise floor
# has not altered anything.
diffset() {   # $1=run-dir-a $2=run-dir-b $3=variant
  local a="$1/stagedfs-hashes-${PREFIX}-${3}.txt" b="$2/stagedfs-hashes-${PREFIX}-${3}.txt"
  [ -f "$a" ] && [ -f "$b" ] || return 0
  join -t$'\t' \
    <(awk '{h=$1;$1="";sub(/^ +/,"");print $0"\t"h}' "$a" | LC_ALL=C sort) \
    <(awk '{h=$1;$1="";sub(/^ +/,"");print $0"\t"h}' "$b" | LC_ALL=C sort) \
    | awk -F'\t' '$2!=$3 {print $1}' | LC_ALL=C sort
}
verify_of() {   # $1=run-dir $2=variant  -> "P/W/F" counts
  local f="$1/verify-${PREFIX}-${2}.txt"
  if [ -f "$f" ]; then
    printf '%s/%s/%s' "$(grep -c '^\[PASS\]' "$f")" "$(grep -c '^\[WARN\]' "$f")" "$(grep -c '^\[FAIL\]' "$f")"
  else echo "-/-/-"; fi
}

lab_model_table "$MODEL"
: > "$SESSION/runs.tsv"

# --- warm-up (discarded) ----------------------------------------------------
if [ "$WARMUP" = 1 ]; then
  echo; echo "WARM-UP (result discarded -- it establishes the steady state, it is not a data point)"
  run_one warmup 0 "${A_ARGS[@]}" || echo "  warm-up returned non-zero; continuing (it is discarded)"
fi

# --- alternating replicates -------------------------------------------------
# Order matters most at --repeat 1, where there is no alternation to spread the
# warming drift. Running the CANDIDATE first (--order BA) makes the bias work
# AGAINST it: B builds on the colder tree, A on the tree B just warmed. A win
# under those conditions is a conservative result rather than a flattered one.
FAILED=0
for rep in $(seq 1 "$REPEAT"); do
  if [ "$ORDER" = "BA" ]; then
    run_one B "$rep" "${B_ARGS[@]}" || FAILED=1
    run_one A "$rep" "${A_ARGS[@]}" || FAILED=1
  else
    run_one A "$rep" "${A_ARGS[@]}" || FAILED=1
    run_one B "$rep" "${B_ARGS[@]}" || FAILED=1
  fi
done

# ============================================================================
# Report
# ============================================================================
{
  echo "# A/B result — $COMPARE — $MODEL"
  echo
  echo "- session: \`$(basename "$SESSION")\`"
  echo "- date (UTC): $(date -u +%FT%TZ)"
  echo "- tree: \`$R\` @ \`$(git -C "$R" rev-parse --short HEAD)\` (\`$(git -C "$R" rev-parse --abbrev-ref HEAD)\`)"
  echo "- version: \`$(lab_read_version)\`"
  echo "- variants: \`$VARIANTS\`  ·  replicates: $REPEAT  ·  warm-up: $([ "$WARMUP" = 1 ] && echo yes || echo no)  ·  order: \`$ORDER\`"
  [ "$ORDER" = "BA" ] && echo "- ordering note: the candidate ran **first**, on the colder tree, so any win here is conservative."
  echo "- arm A (baseline): \`${A_ARGS[*]}\`"
  echo "- arm B (candidate): \`${B_ARGS[*]}\`"
  echo
  echo "## Timing"
  echo
  echo "| arm | replicate | rc | total (s) | total (m:ss) |"
  echo "|---|---|---|---|---|"
  while IFS='|' read -r a r rc t; do
    [ "$a" = warmup ] && continue
    printf '| %s | %s | %s | %s | %d:%02d |\n' "$a" "$r" "$rc" "$t" "$((t/60))" "$((t%60))"
  done < "$SESSION/runs.tsv"
  echo
  echo "## Content equality (the criterion that decides promotion)"
  echo
  echo "Digests are **normalised** — the paths in \`nondeterministic.txt\` are excluded,"
  echo "because this build is not bit-reproducible and never has been. The raw digest is"
  echo "shown too; a future reproducible-builds effort would drive the two together."
  echo
  echo "| variant | arm | replicate | normalised digest | raw digest | verify P/W/F |"
  echo "|---|---|---|---|---|---|"
  for v in $VARIANTS; do
    for rep in $(seq 1 "$REPEAT"); do
      for arm in A B; do
        d="$SESSION/${arm}-r${rep}"
        printf '| %s | %s | %s | `%s` | `%s` | %s |\n' "$v" "$arm" "$rep" \
          "$(digest_of "$d" "$v")" "$(digest_raw_of "$d" "$v" | cut -c1-16)" "$(verify_of "$d" "$v")"
      done
    done
  done
  echo
  # --- the noise floor, measured not assumed --------------------------------
  if [ "$WARMUP" = 1 ]; then
    echo "### Irreproducibility noise floor"
    echo
    echo "Files differing between the warm-up and arm A — two builds of **identical**"
    echo "configuration. Anything the candidate changes beyond this set is real."
    echo
    for v in $VARIANTS; do
      nf="$(diffset "$SESSION/warmup-r0" "$SESSION/A-r1" "$v")"
      cf="$(diffset "$SESSION/A-r1" "$SESSION/B-r1" "$v")"
      echo "\`$v\` — noise floor: $(echo "$nf" | grep -c .) files · candidate: $(echo "$cf" | grep -c .) files"
      echo
      echo '```'
      echo "noise floor (A-config vs A-config):"; echo "$nf" | sed 's/^/  /'
      echo "candidate   (A vs B):"; echo "$cf" | sed 's/^/  /'
      echo "beyond the noise floor (REAL divergence if non-empty):"
      comm -23 <(echo "$cf") <(echo "$nf") | sed 's/^/  /'
      echo '```'
      echo
    done
  fi
  echo "## Verdict"
  echo
} > "$REPORT"

# --- criterion 1: digest equality -------------------------------------------
DIGEST_OK=1
for v in $VARIANTS; do
  ref="";
  for rep in $(seq 1 "$REPEAT"); do
    for arm in A B; do
      d="$(digest_of "$SESSION/${arm}-r${rep}" "$v")"
      [ "$d" = "-" ] && { DIGEST_OK=0; echo "- **MISSING** digest for $v $arm r$rep" >> "$REPORT"; continue; }
      if [ -z "$ref" ]; then ref="$d"
      elif [ "$d" != "$ref" ]; then
        DIGEST_OK=0
        echo "- **DIGEST MISMATCH** \`$v\` arm $arm replicate $rep: \`$d\` vs \`$ref\`" >> "$REPORT"
      fi
    done
  done
done
# Secondary, and independent of the digest: no file may differ between arms that
# does not also differ between two identical-config builds.
SUBSET_OK=1
if [ "$WARMUP" = 1 ]; then
  for v in $VARIANTS; do
    beyond="$(comm -23 <(diffset "$SESSION/A-r1" "$SESSION/B-r1" "$v") \
                       <(diffset "$SESSION/warmup-r0" "$SESSION/A-r1" "$v"))"
    if [ -n "$beyond" ]; then
      SUBSET_OK=0
      echo "- **BEYOND NOISE FLOOR** \`$v\` — the candidate changed files that two identical builds do not:" >> "$REPORT"
      echo "$beyond" | sed 's/^/  - `/; s/$/`/' >> "$REPORT"
    fi
  done
fi

if [ "$DIGEST_OK" = 1 ] && [ "$SUBSET_OK" = 1 ]; then
  echo "- **PASS — content equivalent.** Normalised digests match across every arm and replicate, and the candidate changed nothing that two identical-config builds do not also change." >> "$REPORT"
elif [ "$DIGEST_OK" = 1 ]; then
  echo "- **PASS (digest) with a caveat** — normalised digests match, but see the noise-floor note above." >> "$REPORT"
else
  echo "- **FAIL — the candidate changes what gets built.** Stop here; do not promote, and do not read the timing as a result." >> "$REPORT"
fi

# --- criterion 2: no verify failures ----------------------------------------
VERIFY_OK=1
for v in $VARIANTS; do
  for rep in $(seq 1 "$REPEAT"); do
    for arm in A B; do
      f="$SESSION/${arm}-r${rep}/verify-${PREFIX}-${v}.txt"
      [ -f "$f" ] || continue
      n=$(grep -c '^\[FAIL\]' "$f")
      [ "$n" -gt 0 ] && { VERIFY_OK=0; echo "- **VERIFY FAIL** \`$v\` arm $arm replicate $rep — $n failed checks" >> "$REPORT"; }
    done
  done
done
[ "$VERIFY_OK" = 1 ] && echo "- **PASS — reaper_verify clean in every run.**" >> "$REPORT"

# --- criterion 3: faster in every replicate ---------------------------------
SPEED_OK=1; SUMA=0; SUMB=0
for rep in $(seq 1 "$REPEAT"); do
  ta=$(awk -F'|' -v r="$rep" '$1=="A" && $2==r {print $4}' "$SESSION/runs.tsv" | tail -1)
  tb=$(awk -F'|' -v r="$rep" '$1=="B" && $2==r {print $4}' "$SESSION/runs.tsv" | tail -1)
  ta=${ta:-0}; tb=${tb:-0}
  SUMA=$((SUMA+ta)); SUMB=$((SUMB+tb))
  if [ "$ta" -gt 0 ] && [ "$tb" -gt 0 ] && [ "$tb" -lt "$ta" ]; then
    pct=$(( (ta - tb) * 100 / ta ))
    echo "- replicate $rep: ${ta}s → ${tb}s (**−${pct}%**)" >> "$REPORT"
  else
    SPEED_OK=0
    echo "- replicate $rep: ${ta}s → ${tb}s (**no improvement**)" >> "$REPORT"
  fi
done
if [ "$SUMA" -gt 0 ]; then
  echo "- aggregate: ${SUMA}s → ${SUMB}s over $REPEAT replicates" >> "$REPORT"
fi

{
  echo
  if [ "$DIGEST_OK" = 1 ] && [ "$SUBSET_OK" = 1 ] && [ "$VERIFY_OK" = 1 ] && [ "$SPEED_OK" = 1 ] && [ "$FAILED" = 0 ]; then
    echo "### PROMOTE"
    echo
    echo "All three criteria hold. The change may be ported into"
    echo "\`build-scripts/_reaper_build_lib.sh\` — and note that the local copy at"
    echo "\`/home/reaper/reaper_build/\` is a divergent fork of that file, so"
    echo "porting to one engine reaches only one of the two that currently"
    echo "alternate between rungs. Converge them first (plan item L1)."
  else
    echo "### DO NOT PROMOTE"
    echo
    echo "At least one criterion failed. The evidence is in this directory; the"
    echo "per-run build logs carry the \`[lab-timing]\` and \`[lab-decision]\` lines"
    echo "that explain what each arm actually did."
  fi
  echo
  echo "---"
  echo
  echo "_Generated by \`build-lab/ab_compare.sh\`. No file outside \`build-lab/RESULTS/\` was modified._"
} >> "$REPORT"

lab_hr
cat "$REPORT"
lab_hr
echo "report: $REPORT"
[ "$DIGEST_OK" = 1 ] && [ "$SUBSET_OK" = 1 ] && [ "$VERIFY_OK" = 1 ] && [ "$FAILED" = 0 ] || exit 1
exit 0
