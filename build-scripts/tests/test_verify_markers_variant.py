#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_markers.txt variant field (2026-10-09) - the marker loop run for real.

WHY THIS EXISTS. The v3.3.7 IPv6 rung pinned rmcpd, the Advisor page and httpd's MCP-gated
"url6" reply as plain markers. rmcpd and the Advisor are absent from noMCP by design, so every
noMCP image in the v3.3.7 CI run failed reaper_verify (4 FAIL each) after a clean compile. The
manifest had no way to say "MCP only"; it now takes an optional 4th field naming the one variant
a line applies to.

WHAT IT DOES. Lifts section 10 (the patch-marker loop) out of reaper_verify.sh, runs it under
bash against a throwaway staged fs and a throwaway manifest for both variants, and proves: a
tagged line is skipped for the other variant and enforced for its own; an untagged line is
enforced for both; an unknown tag fails. Then checks the real manifest: every 4th field is MCP or
noMCP, and every line for an MCP-only artifact (rmcpd, the Advisor page) is tagged MCP.
Exit 0 pass, 1 fail, 77 skipped."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

HERE = os.path.dirname(os.path.abspath(__file__))
BS = os.path.dirname(HERE)
BASH = shutil.which("bash")
if not BASH:
    skip("no bash")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(os.path.join(BS, "reaper_verify.sh"), encoding="utf-8").read()
m = re.search(r"^# ---- 10\..*?(?=^# ---- \d+\.)", src, re.S | re.M)
if not m:
    print("FAIL: section 10 (patch markers) not found in reaper_verify.sh"); sys.exit(1)
sec = m.group(0)
MARK_LINE = "MARKF=/home/reaper/reaper_build/verify_markers.txt"
check("section 10 reads the synced manifest path", MARK_LINE in sec)
check("the loop reads a 4th (variant) field", "read -r mpath mpat mmin mvar" in sec)

tmp = tempfile.mkdtemp(prefix="vmv_")
try:
    fs = os.path.join(tmp, "fs")
    os.makedirs(os.path.join(fs, "usr", "sbin"))
    with open(os.path.join(fs, "usr", "sbin", "httpd"), "w") as f:
        f.write("always-here\n")
    # fs holds NO bin/rmcpd: what a noMCP image looks like
    def run(variant, manifest):
        mk = os.path.join(tmp, "markers.txt")
        with open(mk, "w", newline="\n") as f:
            f.write(manifest)
        body = sec.replace(MARK_LINE, "MARKF='%s'" % mk)
        script = ("FAILN=0; PASSN=0; WARNN=0\n"
                  "pass(){ echo \"[PASS] $1 -- $2\"; PASSN=$((PASSN+1)); }\n"
                  "warn(){ echo \"[WARN] $1 -- $2\"; WARNN=$((WARNN+1)); }\n"
                  "fail(){ echo \"[FAIL] $1 -- $2\"; FAILN=$((FAILN+1)); }\n"
                  "set -u\nVARIANT='%s'; FS='%s'\n" % (variant, fs)
                  + body + "\necho \"FAILN=$FAILN\"\n")
        sp = os.path.join(tmp, "sec10.sh")
        with open(sp, "w", newline="\n") as f:
            f.write(script)
        r = subprocess.run([BASH, sp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        mm = re.search(r"FAILN=(\d+)", r.stdout)
        return (int(mm.group(1)) if mm else -1), r.stdout

    tagged = "usr/sbin/httpd|always-here|1\nbin/rmcpd|IPv6 listener|1|MCP\n"
    n, out = run("noMCP", tagged)
    check("noMCP skips an MCP-tagged line for an absent binary", n == 0, out)
    n, out = run("MCP", tagged)
    check("MCP enforces the same line (rmcpd missing -> FAIL)", n == 1 and "bin/rmcpd MISSING" in out, out)
    n, out = run("noMCP", "bin/rmcpd|IPv6 listener|1\n")
    check("an UNTAGGED MCP-only line still fails noMCP (the v3.3.7 failure, reproduced)", n == 1, out)
    n, out = run("MCP", "usr/sbin/httpd|!not-here||noMCP\nusr/sbin/httpd|always-here|1|noMCP\n")
    check("noMCP-tagged lines are skipped for MCP", n == 0, out)
    n, out = run("noMCP", "usr/sbin/httpd|!always-here||noMCP\n")
    check("a noMCP-tagged forbidden line is enforced for noMCP", n == 1, out)
    n, out = run("MCP", "usr/sbin/httpd|always-here|1|mcp\n")
    check("an unknown variant tag FAILS instead of silently skipping", n == 1 and "unknown variant" in out, out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# The real manifest.
MCP_ONLY = ("bin/rmcpd", "www/Reaper_Advisor.asp")
bad_tag, untagged = [], []
for i, line in enumerate(open(os.path.join(BS, "verify_markers.txt"), encoding="utf-8").read().split("\n"), 1):
    if not line or line.startswith("#"):
        continue
    parts = line.split("|")
    if len(parts) > 4 or (len(parts) == 4 and parts[3] not in ("MCP", "noMCP")):
        bad_tag.append("%d: %s" % (i, line))
    if parts[0] in MCP_ONLY and (len(parts) < 4 or parts[3] != "MCP"):
        untagged.append("%d: %s" % (i, line))
check("every variant field in verify_markers.txt is MCP or noMCP", not bad_tag, bad_tag)
check("every rmcpd / Advisor-page marker is tagged MCP", not untagged, untagged)

if fails:
    print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
print("all checks passed: MCP-only markers are skipped for noMCP and enforced for MCP")
