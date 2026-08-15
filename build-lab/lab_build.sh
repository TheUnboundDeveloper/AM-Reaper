#!/bin/bash
# ============================================================================
# lab_build.sh -- run ONE lab build. No ship, own logs, flip restored on exit.
# ----------------------------------------------------------------------------
# Usage:
#   lab_build.sh --model RT-BE96U [options]
#
#   --model    <MODEL>        RT-BE96U | RT-BE86U | RT-BE88U | GT-BE98 | GT-BE98_PRO
#   --variants "<list>"       default "MCP noMCP"; use "MCP" for a dev iteration
#   --single-pass <mode>      off (default) | auto | force
#   --config-keep             enable the conditional .config invalidation (L4)
#   --arm <name>              label for this run in RESULTS/ (default: derived)
#   --run-dir <path>          write evidence here instead of a fresh RESULTS dir
#   --dry-run                 run pre-flight and print the plan, build nothing
#
# Exit: 0 build + verify clean, non-zero otherwise. Evidence always written.
# ============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab_env.sh
source "$HERE/lab_env.sh"

MODEL=""; LAB_VARIANTS="MCP noMCP"; LAB_SINGLE_PASS="off"; LAB_CONFIG_KEEP=0
ARM=""; RUN_DIR=""; DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --model)        MODEL="$2"; shift 2;;
    --variants)     LAB_VARIANTS="$2"; shift 2;;
    --single-pass)  LAB_SINGLE_PASS="$2"; shift 2;;
    --config-keep)  LAB_CONFIG_KEEP=1; shift;;
    --arm)          ARM="$2"; shift 2;;
    --run-dir)      RUN_DIR="$2"; shift 2;;
    --dry-run)      DRY=1; shift;;
    -h|--help)      sed -n '2,20p' "$0"; exit 0;;
    *) lab_die "unknown argument '$1'";;
  esac
done

[ -n "$MODEL" ] || lab_die "--model is required"
case "$LAB_SINGLE_PASS" in off|auto|force) ;; *) lab_die "--single-pass must be off|auto|force";; esac
export LAB_VARIANTS LAB_SINGLE_PASS LAB_CONFIG_KEEP

lab_model_table "$MODEL"

# Arm name encodes the configuration, so a RESULTS dir is self-describing even
# if someone reads it a month later with no memory of how it was produced.
if [ -z "$ARM" ]; then
  ARM="sp-${LAB_SINGLE_PASS}"
  [ "$LAB_CONFIG_KEEP" = 1 ] && ARM="${ARM}_ck"
  ARM="${ARM}_$(echo "$LAB_VARIANTS" | tr ' ' '+')"
fi

if [ -z "$RUN_DIR" ]; then
  RUN_DIR="$RESULTS_ROOT/$(date +%Y%m%d-%H%M%S)-${MODEL}-${ARM}"
fi
mkdir -p "$RUN_DIR"
export LAB_RUN_DIR="$RUN_DIR"

lab_hr
echo " Reaper build-lab -- $MODEL / [$LAB_VARIANTS] / arm=$ARM"
echo " tree     : $R"
echo " evidence : $RUN_DIR"
lab_hr
echo "pre-flight:"
if ! lab_preflight; then
  lab_hr; echo "PRE-FLIGHT FAILED -- nothing was built, nothing was touched."; exit 9
fi
lab_hr

# --- record exactly what is being measured ----------------------------------
# Without this the numbers are unattributable. The canonical-engine hash is here
# so a later reader can tell whether the baseline arm still corresponds to the
# engine that was live at the time.
{
  echo "timestamp_utc=$(date -u +%FT%TZ)"
  echo "model=$MODEL"
  echo "branch=$BRANCH"
  echo "target=$TARGET"
  echo "prefix=$PREFIX"
  echo "arm=$ARM"
  echo "variants=$LAB_VARIANTS"
  echo "lab_single_pass=$LAB_SINGLE_PASS"
  echo "lab_config_keep=$LAB_CONFIG_KEEP"
  echo "reaper_jobs=${REAPER_JOBS:-1}"
  echo "tree=$R"
  echo "head=$(git -C "$R" rev-parse HEAD)"
  echo "version=$(lab_read_version)"
  echo "host_nproc=$(nproc)"
  echo "host_mem_gb=$(free -g | awk '/^Mem:/{print $2}')"
  echo "lab_engine_sha256=$(sha256sum "$HERE/_reaper_build_lib.lab.sh" | cut -d' ' -f1)"
  echo "canonical_engine_sha256=$(sha256sum "$REPO_DIR/build-scripts/_reaper_build_lib.sh" 2>/dev/null | cut -d' ' -f1)"
} > "$RUN_DIR/run.env"
sed 's/^/  /' "$RUN_DIR/run.env"
lab_hr

if [ "$DRY" = 1 ]; then
  echo "--dry-run: pre-flight passed, plan recorded, no build started."
  exit 0
fi

# A single-variant build is a development artifact. Say so in the evidence so it
# can never be picked up later and mistaken for a release candidate.
case "$LAB_VARIANTS" in
  *MCP*noMCP*|*noMCP*MCP*) ;;
  *) echo "DEV-ONLY: variant set '$LAB_VARIANTS' is incomplete -- not a shippable build" \
       > "$RUN_DIR/DEV-ONLY.txt"
     echo "[lab] note: incomplete variant set -- marked DEV-ONLY";;
esac

lab_install_trap

# shellcheck source=_reaper_build_lib.lab.sh
source "$HERE/_reaper_build_lib.lab.sh"

LOG="$RUN_DIR/build.log"
START=$(date +%s)
# The build's exit code is written to a file rather than read from $? or
# PIPESTATUS. Both are wrong here: the `$(date +%s)` in the summary line resets
# $? before it can be read, and the group runs in a pipeline subshell so
# PIPESTATUS[0] reports the group's last command (the echo), which always
# succeeds. A harness that silently reports rc=0 for a failed build is worse
# than no harness.
RCF="$RUN_DIR/.rc"
{
  lab_reaper_build; _rc=$?
  echo "$_rc" > "$RCF"
  echo "[lab-total] seconds=$(( $(date +%s) - START )) rc=$_rc"
} 2>&1 | tee "$LOG"
RC="$(cat "$RCF" 2>/dev/null || echo 1)"
rm -f "$RCF"

# --- post-run assertions ----------------------------------------------------
lab_hr
echo "post-run:"
lab_assert_flip_clean "post-run" || RC=$(( RC == 0 ? 1 : RC ))

# Distil the timing lines into something a human reads without opening the log.
grep -E '^\[lab-(timing|decision|image|digest|verify|total|config)\]' "$LOG" > "$RUN_DIR/summary.txt" || true
echo
echo "timing summary:"
awk -F'[ =]' '/^\[lab-timing\]/{printf "  %-10s %-16s %6ss  rc=%s %s\n",$3,$5,$7,$9,$10}' "$LOG"
TOTAL=$(grep -oE '^\[lab-total\] seconds=[0-9]+' "$LOG" | grep -oE '[0-9]+$' | tail -1)
[ -n "${TOTAL:-}" ] && printf "  %-10s %-16s %6ss\n" TOTAL "" "$TOTAL"
lab_hr
echo "evidence: $RUN_DIR"
exit "$RC"
