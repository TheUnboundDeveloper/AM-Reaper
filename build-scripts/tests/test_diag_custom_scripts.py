#!/usr/bin/env python3
"""reaper_diag v1.3.51 section 13: each custom script and why it might not run (2026-10-26).

WHY. A firewall-start that "is not honoured" has five usual causes and Reaper's report named none of them: custom
scripts switched off, the file not executable, Windows line endings (its #! line names "/bin/sh\\r"), a command
failing inside it, or the file sitting at /jffs/<name> where rc never looks. Section 13 now reports each script in
/jffs/scripts - executable, CRLF, how its last run ended (the outcome from rc's custom_script syslog lines, never
what the script printed) and whether rc kept its output - with a finding for each cause.

WHAT IT DOES. Lifts section 13 out of others/reaper_diag, points /jffs, /tmp/syslog.log and /tmp/reaper at a scratch
folder, stubs nvram and finding(), and runs it under sh and busybox ash (when present) over a set of scripts that
covers every case.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "others", "reaper_diag") if SRC else ""
if not P or not os.path.isfile(P):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
d = open(P, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:500] if detail else ""))

check("the report is v1.3.51", 'VER="REAPER-DIAG v1.3.52"' in d)
i, j = d.find('sec "13. ADDONS / JFFS"'), d.find('echo "  entware:')
check("section 13 found", 0 < i < j, (i, j))
sec = d[i:j]
check("section 13 prints outcomes only, never what a script printed",
      "sed -n 's/.*exited with status \\([0-9]*\\).*/\\1/p'" in sec and "cat " not in sec and "tail -n 1 \"/tmp/reaper" not in sec)

shells = [["sh"]] + ([["busybox", "ash"]] if shutil.which("busybox") else [])
for shell in shells:
    tag = "ash" if shell[0] == "busybox" else "sh"
    w = tempfile.mkdtemp(prefix="diag13_")
    try:
        J, T = os.path.join(w, "jffs"), os.path.join(w, "tmp")
        os.makedirs(os.path.join(J, "scripts")); os.makedirs(os.path.join(T, "reaper"))
        def put(rel, text, mode=0o755, crlf=False):
            p = os.path.join(J, rel); open(p, "w", newline="").write(text.replace("\n", "\r\n") if crlf else text); os.chmod(p, mode)
        put("scripts/firewall-start", "#!/bin/sh\niptables -w -I INPUT -j ACCEPT\n")
        put("scripts/nat-start", "#!/bin/sh\necho ok\n")
        put("scripts/services-start", "#!/bin/sh\necho x\n", mode=0o644)
        put("scripts/wan-event", "#!/bin/sh\necho y\n", crlf=True)
        put("scripts/post-mount", "#!/bin/sh\nsleep 99\n")
        put("dhcpc-event", "#!/bin/sh\necho misplaced\n")
        open(os.path.join(T, "reaper", "script-firewall-start.log"), "w").write("iptables v1.4.18: unknown option \"-w\" 192.0.2.9\n")
        open(os.path.join(T, "syslog.log"), "w").write(
            "Oct 26 10:00:00 custom_script: Running /jffs/scripts/firewall-start (args: eth0)\n"
            "Oct 26 10:00:00 custom_script: /jffs/scripts/firewall-start exited with status 2: iptables v1.4.18: unknown option \"-w\" 192.0.2.9 - its output: /tmp/reaper/script-firewall-start.log\n"
            "Oct 26 10:00:01 custom_script: Running /jffs/scripts/nat-start\n"
            "Oct 26 10:00:02 custom_script: Found services-start, but script is not set executable!\n"
            "Oct 26 10:00:03 custom_script: /jffs/scripts/post-mount did not finish in 120 s and was stopped - its output: /tmp/reaper/script-post-mount.log\n")
        # repoint only what touches the filesystem; the syslog patterns and the finding texts keep the real paths
        body = sec
        for a, b in (("for f in /jffs/scripts/*; do", "for f in %s/scripts/*; do" % J),
                     ('[ -f "/jffs/$n" ] && [ ! -f "/jffs/scripts/$n" ]', '[ -f "%s/$n" ] && [ ! -f "%s/scripts/$n" ]' % (J, J)),
                     ("/tmp/syslog.log", T + "/syslog.log"),
                     ('[ -s "/tmp/reaper/script-$n.log" ]', '[ -s "%s/reaper/script-$n.log" ]' % T),
                     ('wc -c < "/tmp/reaper/script-$n.log"', 'wc -c < "%s/reaper/script-$n.log"' % T)):
            assert body.count(a) == 1, ("harness anchor", a)
            body = body.replace(a, b)
        def run(js):
            sp = os.path.join(w, "run.sh")
            open(sp, "w").write('sec() { echo "#### $1 ####"; }\nnvram() { [ "$2" = jffs2_scripts ] && echo %s; }\n'
                                'finding() { echo "FINDING [$1] $2"; }\n%s' % (js, body))
            return subprocess.run(shell + [sp], capture_output=True, text=True, timeout=30)
        r = run(1); o = r.stdout
        lines = {m.group(1): m.group(0) for m in re.finditer(r"  script (\S+): .*", o)}
        check(tag + ": the switch is reported", "custom scripts (System > Enable JFFS custom scripts and configs): on" in o, o[:300])
        check(tag + ": a failed run is named with its status, and only its status",
              "last=failed (exit 2)" in lines.get("firewall-start", "") and "192.0.2.9" not in o and "unknown option" not in o, o)
        check(tag + ": a kept output file is reported by size", "output=" in lines.get("firewall-start", "") and "B kept" in lines.get("firewall-start", ""))
        check(tag + ": a clean run reads 'ran'", "last=ran" in lines.get("nat-start", ""), lines.get("nat-start"))
        check(tag + ": not executable -> refused + a WARN", "executable=no" in lines.get("services-start", "")
              and "last=refused (not executable)" in lines.get("services-start", "")
              and "/jffs/scripts/services-start is not executable" in o, lines.get("services-start"))
        check(tag + ": CRLF -> a WARN", "crlf=yes" in lines.get("wan-event", "") and "has Windows line endings" in o, lines.get("wan-event"))
        check(tag + ": a time-limited stop is a WARN", "last=stopped at its time limit" in lines.get("post-mount", "")
              and "post-mount stopped at its time limit on its last run" in o, lines.get("post-mount"))
        check(tag + ": a failed run is a WARN pointing at the output file", "firewall-start failed (exit 2) on its last run" in o)
        check(tag + ": a script at /jffs/<name> is a WARN", "/dhcpc-event is never run - custom scripts live in /jffs/scripts/" in o, o[-600:])
        check(tag + ": no 'custom scripts are OFF' while on", "custom scripts are OFF" not in o)
        r = run(0); o = r.stdout
        check(tag + ": switched off -> one WARN naming the count", "custom scripts are OFF: none of the 5 script(s)" in o, o[-400:])
        check(tag + ": nothing on stderr", r.stderr.strip() == "", r.stderr[:300])
    finally:
        shutil.rmtree(w, ignore_errors=True)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
