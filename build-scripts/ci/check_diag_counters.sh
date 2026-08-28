#!/bin/sh
# check_diag_counters.sh - regression guard for the two reaper_diag counter bugs
# fixed in REAPER-DIAG v1.3.8 (2026-08-28). Both were TRUNCATION/OVER-COUNT bugs
# that made the diag misreport a healthy or benign state:
#
#   QOSDIAG-2  section 10 piped `tmctl getqcfg` through `head -3`, keeping
#              qid/priority/qsize and cutting weight/minBufs/schedMode/SHAPER
#              and the "ret code" status line. The survivors are programmed
#              unconditionally, so "shaping correctly" and "armed but toothless"
#              printed identically.
#   CHURNFIX   section 19b counted syslog LINES, not events. hostapd repeats the
#              disassoc line (bursts of up to 10 in one second) -> 6.8x inflation
#              on metal (2810 lines / 411 events; top station 1057 vs 218).
#
# Two layers: (A) source invariants, (B) the REAL awk programs extracted from the
# diag source and run against fixtures - so these tests cannot drift from what
# actually ships.
#
# Usage: check_diag_counters.sh [path/to/reaper_diag]
# Default path is the WSL canon tree. Layer A is skipped (not failed) when the
# source is absent, so this still runs in a checkout without the vendor tree.

set -u
DIAG="${1:-/home/reaper/asuswrt-be96u/release/src/router/others/reaper_diag}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0; ran=0
ok()   { ran=$((ran+1)); printf '  ok    %s\n' "$1"; }
bad()  { ran=$((ran+1)); fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
note() { printf '  --    %s\n' "$1"; }

echo "== check_diag_counters.sh =="
echo "source: $DIAG"

# ---------------------------------------------------------------- A: invariants
echo "-- A. source invariants --"
if [ ! -r "$DIAG" ]; then
  note "source not readable - layer A skipped (layer B still runs)"
else
  V="$(sed -n 's/^VER="REAPER-DIAG v\([0-9.]*\)".*/\1/p' "$DIAG" | head -1)"
  case "$V" in
    ""|1.0*|1.1*|1.2*|1.3.[0-7]) bad "VER is $V - expected >= 1.3.8" ;;
    *) ok "VER $V carries the fixes" ;;
  esac

  if grep -q 'getqcfg .*head -3' "$DIAG"; then
    bad "QOSDIAG-2 REGRESSED: getqcfg is piped through 'head -3' again"
  else
    ok "getqcfg is not truncated"
  fi
  grep -q '/shaper/{sh=' "$DIAG" && ok "getqcfg formatter captures the shaper field" \n                                 || bad "formatter does not capture shaper - readback still blind"
  grep -q 'TMCTL-ERR' "$DIAG" && ok "getqcfg surfaces a non-zero ret code" \
                              || bad "no TMCTL-ERR tag - ret code discarded again"

  n="$(grep -c 'seen\[\$1" "\$2" "\$3' "$DIAG")"
  if [ "$n" -ge 2 ]; then
    ok "churn dedup present in both counters ($n sites)"
  else
    bad "CHURNFIX REGRESSED: dedup found at $n site(s), need 2 (table + finding)"
  fi
fi

# ------------------------------------------------------------- B: real behaviour
echo "-- B. extracted-logic behaviour --"

# B1/B2: the multi-line qcfg awk, lifted verbatim from the source.
if [ -r "$DIAG" ]; then
  sed -n "/awk -v q=\$q '/,/}'$/p" "$DIAG" \
    | sed -e "1s/.*awk -v q=\$q '//" -e "\$s/'\$//" > "$TMP/qcfg.awk"
fi
if [ -r "$DIAG" ] && [ -s "$TMP/qcfg.awk" ]; then
  cat > "$TMP/qcfg.good" <<'FIX'
    qid      : 4
    priority : 2
    qsize    : 2728
    weight   : 0
    minBufs  : 0
    schedMode: 1
    shaper   : (2090000, 0, 0)
ret code = 0.
FIX
  out="$(awk -v q=4 -f "$TMP/qcfg.awk" < "$TMP/qcfg.good")"
  exp="     qid4 prio=2 qsize=2728 sched=1 wt=0 shaper=(2090000,0,0)"
  [ "$out" = "$exp" ] && ok "qcfg formatter emits every field incl. shaper" \
    || { bad "qcfg formatter output wrong"; printf '        got: [%s]\n        exp: [%s]\n' "$out" "$exp"; }

  sed 's/ret code = 0./ret code = -1./' "$TMP/qcfg.good" > "$TMP/qcfg.err"
  out="$(awk -v q=4 -f "$TMP/qcfg.awk" < "$TMP/qcfg.err")"
  case "$out" in
    *TMCTL-ERR*) ok "qcfg formatter flags a failed readback" ;;
    *) bad "non-zero ret code not flagged: [$out]" ;;
  esac
else
  bad "could not extract the qcfg awk program from the source"
fi

# B3: the churn awk, lifted verbatim, against a fixture with known duplicates.
cat > "$TMP/syslog" <<'FIX'
Aug 28 05:44:17 hostapd: wl0.2: STA aa:bb:cc:dd:ee:01 IEEE 802.11: disassociated
Aug 28 05:44:17 hostapd: wl0.2: STA aa:bb:cc:dd:ee:01 IEEE 802.11: disassociated
Aug 28 05:44:19 hostapd: wl0.2: STA aa:bb:cc:dd:ee:01 IEEE 802.11: disassociated
Aug 28 05:44:19 hostapd: wl0.2: STA aa:bb:cc:dd:ee:01 IEEE 802.11: associated
Aug 28 05:45:19 hostapd: wl0.2: STA aa:bb:cc:dd:ee:01 IEEE 802.11: disassociated
Aug 28 05:45:19 hostapd: wl0.2: STA aa:bb:cc:dd:ee:01 IEEE 802.11: disassociated
Aug 28 05:45:19 hostapd: wl0.2: STA aa:bb:cc:dd:ee:01 IEEE 802.11: disassociated
Aug 28 05:44:20 hostapd: wl1.1: STA aa:bb:cc:dd:ee:02 IEEE 802.11: disassociated
FIX
# 8 lines; deduped: :01 -> 3 disassoc events + 1 assoc, :02 -> 1 disassoc
if [ -r "$DIAG" ]; then
  grep -o "awk '{m=\$7;[^|]*}'" "$DIAG" | head -1 | sed -e "s/^awk '//" -e "s/'\$//" > "$TMP/churn.awk"
fi
if [ -r "$DIAG" ] && [ -s "$TMP/churn.awk" ]; then
  raw="$(grep -c 'disassociated' "$TMP/syslog")"
  got="$(grep -E 'hostapd: .*STA .* (associated|disassociated)' "$TMP/syslog" \
         | awk -f "$TMP/churn.awk" | sort -rn | awk '$3=="aa:bb:cc:dd:ee:01"{print $1"/"$2}')"
  if [ "$got" = "3/1" ]; then
    ok "churn counter dedups bursts (7 disassoc lines -> 3 events, assoc 1)"
  else
    bad "churn dedup wrong: got [$got], expected [3/1] (raw lines were $raw)"
  fi
  [ "$raw" = "7" ] && note "fixture holds $raw disassoc LINES - a line counter would report 7" \
                   || note "fixture line count changed ($raw)"
else
  bad "could not extract the churn awk program from the source"
fi

echo
if [ "$fail" -eq 0 ]; then echo "PASS ($ran checks)"; else echo "FAIL ($fail of $ran checks)"; fi
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
