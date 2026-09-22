"""Prove the reaper_diag counter fixes (v1.3.14) hold, and that reverting any
one of them is caught.

Run:  python3 build-scripts/tests/test_reaper_diag_counters.py
      REAPER_ROUTER_SRC=/home/reaper/port/gt-be98/release/src/router python3 ...

Exit 0 = every property holds AND every reversal is caught.  Exit 77 = the
router source tree is not on this machine (a CI runner), nothing to check.

Background - all six were measured on live metal 2026-09-10, not reasoned:

  * The USB/jffs mirror is a rolling copy of the same syslog, so concatenating
    the sources counted the overlap twice: 12,360 lines against 5,634 distinct.
    Every counter in section 19b was inflated about 2.2x.
  * The lab MCP echoes the operator's own command text into syslog under
    `rmcpd-lab: exec:`, so any counter whose pattern appears in a command run
    through it is inflated.  Together with a case-insensitive bare `Oops`, that
    made panic/oops/oom report 2 on a box that had neither - the most alarming
    line in the report, and the least trustworthy.
  * "boots in span" counted `syslogd started`; a service cascade restarts
    syslogd without a reboot.  Metal showed a start 1h20m old on a box up
    10h42m.  There is no RTC, so /proc/uptime is the only reliable marker.
  * /proc/net/nf_conntrack was read six times for six figures, so the total and
    the per-protocol sum came from different instants and could not reconcile.
  * RW_FDROP is never created (forward drops share RW_DROP by design), so the
    probe printed "absent" on every healthy box, reading as a fault.
  * /proc/sys/kernel/tainted is a bitmask; 4097 = proprietary + out-of-tree
    module, the expected state.  Printed as an integer it looked alarming.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

EXIT_SKIP = 77
SRC = os.environ.get("REAPER_ROUTER_SRC",
                     "/home/reaper/asuswrt-be96u/release/src/router")
DIAG = os.path.join(SRC, "others", "reaper_diag")

if not os.path.isfile(DIAG):
    print("SKIP test_reaper_diag_counters: no reaper_diag at %s" % DIAG)
    print("     set REAPER_ROUTER_SRC=<router source tree> to run it")
    sys.exit(EXIT_SKIP)


def read(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8", "replace")


def code_only(text):
    """Strip whole-line shell comments before testing for code shapes.

    Every property below is a claim about what the script DOES.  The fixes
    carry long comments explaining why they exist, and those comments quote
    the very strings being searched for ("boots in span", "panic/oops/oom",
    "rmcpd-lab: exec:").  Scanning raw text therefore matched the rationale
    and reported a correctly fixed file as broken - the same trap that made
    the workflow shell-vars suite pass a reintroduced bug twice.  Comments
    are prose; test the code.
    """
    keep = [ln for ln in text.split(chr(10)) if not ln.lstrip().startswith("#")]
    return chr(10).join(keep)


# ---------------------------------------------------------------------------
# The properties.  Each returns a problem string, or None when it holds.
# ---------------------------------------------------------------------------
def p_snapshot_deduped(s):
    if not re.search(r"awk '!seen\[\$0\]\+\+'[^\n]*>\s*\"\$SNAP\"", s):
        return ("the syslog sources are not collapsed into $SNAP with an "
                "order-preserving dedup - overlapping mirror lines count twice")
    return None


def p_snapshot_lab_filtered(s):
    m = re.search(r"[^\n]*>\s*\"\$SNAP\"", s)
    if not m:
        return "no $SNAP is built at all"
    if "rmcpd-lab: exec:" not in m.group(0):
        return ("the $SNAP pipeline does not drop `rmcpd-lab: exec:` lines - "
                "operator command text is counted as router events")
    return None


def p_snapshot_is_used(s):
    if not re.search(r"^\s*SLF=\"\$SNAP\"", s, re.M):
        return ("SLF is not repointed at $SNAP, so the counters below still "
                "read the raw concatenated sources")
    return None


def p_panic_anchored(s):
    m = re.search(r"panic/oops/oom[^\n]*", s)
    if not m:
        return "the panic/oops/oom line is gone"
    line = m.group(0)
    if re.search(r"grep -[a-z]*i[a-z]*E", line):
        return ("the panic/oops/oom grep is case-insensitive again - the word "
                "'oops' in any prose line matches")
    if "Oops:" not in line:
        return ("the panic pattern no longer anchors on 'Oops:' - a bare "
                "'Oops' matches prose")
    return None


def p_boots_not_from_syslogd(s):
    if "boots in span" in s:
        return ("'boots in span' is back - it counts syslogd restarts, not "
                "boots; /proc/uptime is the only reliable marker on this "
                "hardware (no RTC)")
    if "/proc/uptime" not in s:
        return "nothing reads /proc/uptime, so no reliable boot marker is reported"
    return None


def p_conntrack_single_read(s):
    start = s.find("CT=/proc/net/nf_conntrack")
    if start < 0:
        return "the conntrack section could not be located"
    blk = s[start:]
    end = blk.find("-- timeouts (s) --")
    if end > 0:
        blk = blk[:end]
    if 'cat $CT > "$CTS"' not in blk:
        return "conntrack is not snapshotted into $CTS before being counted"
    # NB: several figures share ONE echo line, so "does this line mention
    # $CTS" is not a safe exemption - a line can read the snapshot for one
    # figure and the live file for another, which is exactly what a partial
    # revert looks like.  Match $CT not followed by a letter, so $CTS itself
    # is excluded without excluding the line it sits on.
    for ln in blk.split("\n"):
        if "cat $CT > " in ln:
            continue
        if re.search(r"(wc -l|grep -c|awk)[^\n]*\$CT(?![A-Za-z])", ln):
            return ("a conntrack figure still reads the LIVE file, so the "
                    "totals cannot reconcile: %s" % ln.strip()[:90])
    return None


def p_no_rw_fdrop_probe(s):
    m = re.search(r"^for C in REAPER_WARDEN[^\n]*", s, re.M)
    if not m:
        return "the warden chain probe loop is gone"
    if "RW_FDROP" in m.group(0):
        return ("RW_FDROP is probed again - it is never created (forward drops "
                "share RW_DROP), so it always reports 'absent' as if faulty")
    return None


def p_taint_decoded(s):
    if "DIED_OOPS" not in s:
        return ("the kernel taint value is not decoded into flags - it is a "
                "bitmask, not a count")
    if not re.search(r"_tv >> _tb", s):
        return "the taint bitmask decode loop is gone"
    return None


PROPERTIES = [
    ("syslog sources collapsed with an order-preserving dedup", p_snapshot_deduped),
    ("lab command echoes dropped from the snapshot", p_snapshot_lab_filtered),
    ("the counters actually read the snapshot", p_snapshot_is_used),
    ("panic/oops/oom anchored on what the kernel prints", p_panic_anchored),
    ("boots reported from uptime, not syslogd restarts", p_boots_not_from_syslogd),
    ("conntrack figures all derive from one snapshot", p_conntrack_single_read),
    ("RW_FDROP is not probed as if it were a fault", p_no_rw_fdrop_probe),
    ("kernel taint rendered as flags", p_taint_decoded),
]


def check(path):
    s = code_only(read(path))
    out = []
    for name, fn in PROPERTIES:
        why = fn(s)
        if why:
            out.append((name, why))
    return out


# ---------------------------------------------------------------------------
# 1. Baseline
# ---------------------------------------------------------------------------
print("== 1. the current reaper_diag holds every property ==")
BASE = check(DIAG)
for name, why in BASE:
    print("FAIL %s\n       %s" % (name, why))
if BASE:
    sys.exit("baseline must pass before the scenarios mean anything")
for name, _fn in PROPERTIES:
    print("OK   %s" % name)

# ---------------------------------------------------------------------------
# 2. Reversal scenarios - each must be caught
# ---------------------------------------------------------------------------
UNREPLIED_NEW = "grep -c 'UNREPLIED' \"$CTS\""
UNREPLIED_OLD = "grep -c 'UNREPLIED' $CT"

SCENARIOS = [
    # Anchored on the whole prefix: `awk '!seen[$0]++'` also appears in the
    # secrets-sorting pipeline near the top of the file, and mutating that one
    # leaves the fix untouched.  A scenario that edits the wrong line tests
    # nothing - and correctly reports itself as a MISS, which is how this was
    # found.
    ("the dedup is removed from the snapshot pipeline",
     "cat $SLF 2>/dev/null | awk '!seen[$0]++' | ",
     "cat $SLF 2>/dev/null | ", "order-preserving dedup"),
    ("the lab-echo filter is removed",
     "| grep -v 'rmcpd-lab: exec:' ", "", "rmcpd-lab"),
    ("SLF is not repointed at the snapshot",
     "\n  SLF=\"$SNAP\"", "", "SLF is not repointed"),
    ("the panic grep goes case-insensitive again",
     "grep -cE 'Kernel panic|Oops:|oom-killer",
     "grep -ciE 'kernel panic|Oops|oom-killer", "case-insensitive"),
    ("'boots in span' is reintroduced",
     "  echo \"  syslogd starts    :",
     "  echo \"  boots in span     :", "boots in span"),
    ("a conntrack figure reads the live file again",
     UNREPLIED_NEW, UNREPLIED_OLD, "LIVE file"),
    ("RW_FDROP is probed again",
     "for C in REAPER_WARDEN RW_OUT RW_SELF RW_DROP RW_ODROP",
     "for C in REAPER_WARDEN RW_OUT RW_SELF RW_DROP RW_FDROP RW_ODROP",
     "RW_FDROP is probed"),
]

print("\n== 2. reverting any one fix is caught ==")
FAILS = 0
for name, old, new, expect in SCENARIOS:
    tmp = tempfile.mkdtemp(prefix="diagchk_")
    try:
        s = read(DIAG)
        if s.count(old) < 1:
            print("MISS %s\n       setup failed: %r not in the file"
                  % (name, old[:60]))
            FAILS += 1
            continue
        dst = os.path.join(tmp, "reaper_diag")
        with open(dst, "wb") as fh:
            fh.write(s.replace(old, new, 1).encode("utf-8"))
        problems = check(dst)
        blob = " | ".join(w for _n, w in problems)
        caught = bool(problems) and expect in blob
        print("%-4s %s" % ("OK" if caught else "MISS", name))
        if caught:
            print("       -> %s" % [w for _n, w in problems if expect in w][0][:120])
        else:
            FAILS += 1
            print("       got: %s" % (blob[:160] or "<nothing reported>"))
    finally:
        shutil.rmtree(tmp)

# ---------------------------------------------------------------------------
# 3. Functional - run the real lines against fixtures
# ---------------------------------------------------------------------------
print("\n== 3. the real code, run against fixtures ==")


def sh(script):
    proc = subprocess.run(["sh", "-c", script], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
    return proc.stdout.decode("utf-8", "replace").strip()


SRCTXT = code_only(read(DIAG))
LINES = SRCTXT.split("\n")

PIPE = [ln.strip() for ln in LINES if '> "$SNAP"' in ln and "awk" in ln][0]
PANIC = [ln.strip() for ln in LINES
         if "panic/oops/oom" in ln and "grep -cE" in ln][0]

tmp = tempfile.mkdtemp(prefix="diagfix_")
try:
    mirror = os.path.join(tmp, "mirror")
    live = os.path.join(tmp, "syslog")
    snap = os.path.join(tmp, "snap")
    shared = ["Sep 10 20:00:01 kernel: shared line %d" % i for i in range(50)]
    with open(mirror, "w") as fh:
        fh.write("\n".join(shared + ["Sep 10 19:00:00 kernel: mirror only"]) + "\n")
    with open(live, "w") as fh:
        fh.write("\n".join(shared + [
            "Sep 10 22:02:16 rmcpd-lab: rmcpd-lab: exec: grep 'Kernel panic' /tmp/syslog.log",
            "Sep 10 22:03:00 kernel: ordinary line"]) + "\n")

    out = sh('SLF="%s %s"; SNAP="%s"; %s; wc -l < "$SNAP"'
             % (mirror, live, snap, PIPE))
    got = int(out.split()[-1])
    want = 52  # 50 shared once + mirror-only + ordinary; the lab echo dropped
    print("%-4s dedup + lab filter: 103 raw lines -> %d distinct (want %d)"
          % ("OK" if got == want else "FAIL", got, want))
    if got != want:
        FAILS += 1

    out = sh('SNAP="%s"; %s' % (snap, PANIC))
    hit = re.search(r"panic/oops/oom\s*:\s*(\d+)", out)
    val = int(hit.group(1)) if hit else -1
    print("%-4s panic counter where the only 'Kernel panic' is echoed command "
          "text: %d (want 0)" % ("OK" if val == 0 else "FAIL", val))
    if val != 0:
        FAILS += 1

    with open(snap, "a") as fh:
        fh.write("Sep 10 23:00:00 kernel: Kernel panic - not syncing: bad\n")
    out = sh('SNAP="%s"; %s' % (snap, PANIC))
    hit = re.search(r"panic/oops/oom\s*:\s*(\d+)", out)
    val = int(hit.group(1)) if hit else -1
    print("%-4s the same counter still catches a REAL kernel panic: %d (want 1)"
          % ("OK" if val == 1 else "FAIL", val))
    if val != 1:
        FAILS += 1
finally:
    shutil.rmtree(tmp)

START = next(i for i, l in enumerate(LINES) if l.strip().startswith('_tb=0; _tf=""'))
END = next(i for i in range(START, len(LINES)) if LINES[i].strip() == "done")
DECODER = "\n".join(LINES[START:END + 1])

for mask, want_flags in ((4097, "PROPRIETARY_MODULE OUT_OF_TREE_MODULE"),
                         (128, "DIED_OOPS"),
                         (0, ""),
                         (1, "PROPRIETARY_MODULE")):
    out = sh('_tv=%d\n%s\necho "$_tf"' % (mask, DECODER)).strip()
    ok = out == want_flags
    print("%-4s taint %-5d -> %s" % ("OK" if ok else "FAIL", mask,
                                     out or "(clean)"))
    if not ok:
        FAILS += 1
        print("       wanted: %s" % (want_flags or "(clean)"))

print("\n%d problem(s)" % FAILS)
sys.exit(1 if FAILS else 0)
