#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inadyn's request dumps must not carry the DDNS credential into syslog.

WHY THIS EXISTS. CVE-2026-16528 (ASUS, 2026-10-07): DDNS credentials readable from the system log
by an authenticated user. In this tree the DDNS client is inadyn, whose debug-level lines logged the
whole provider request - the Basic/Bearer header (base64 of user:password, or the tunnelbroker
update key), password= or token= query values, user:pass@ in a URL, the INADYN_USER environment of
a checkip command. With `ddns_debug` set that is the credential in syslog. log_redact()
(inadyn/src/log.c) masks those parts; every request-logging site must go through it.

WHAT IT DOES. Lifts log_redact() out of log.c (the REAPER_REDACT markers), compiles it on the
host with -Wall -Wextra, runs it over request shapes the plugins produce and checks that the
secrets are gone while the rest of the line survives. Then checks every logit() that prints a
request buffer in inadyn/src and inadyn/plugins wraps it. Exit 0 pass, 1 fail, 77 skipped (no
host C compiler, or no router source tree - pass release/src/router as argv[1] or
REAPER_ROUTER_SRC).
"""
import glob, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
logc = os.path.join(src_root, "inadyn", "src", "log.c") if src_root else ""
if not logc or not os.path.isfile(logc):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

src = open(logc, encoding="utf-8", errors="replace").read()
m = re.search(r"/\* REAPER_REDACT_BEGIN \*/(.*?)/\* REAPER_REDACT_END \*/", src, re.S)
if not m:
    die("log_redact() (REAPER_REDACT markers) missing from inadyn/src/log.c - the CVE-2026-16528 fix is gone")
body = m.group(1)

CASES = [
    ("tunnelbroker Basic auth",
     "GET /nic/update?hostname=1040858&myip=203.0.113.9 HTTP/1.0\r\nHost: ipv4.tunnelbroker.net\r\n"
     "Authorization: Basic Z3dyYWl0aDpVcGQ0dGVLM3k=\r\nUser-Agent: inadyn/2.10.0\r\n\r\n",
     ["Z3dyYWl0aDpVcGQ0dGVLM3k="], ["hostname=1040858", "myip=203.0.113.9", "Host: ipv4.tunnelbroker.net", "HTTP/1.0"]),
    ("namecheap password in the query",
     "GET /update?domain=example.com&password=s3cr3tPw&host=www HTTP/1.0\r\nHost: dynamicdns.park-your-domain.com\r\n\r\n",
     ["s3cr3tPw"], ["domain=example.com", "host=www", "password=[redacted]"]),
    ("user:pass@ in a URL",
     "GET https://alice:hunter2@domains.google.com/nic/update?hostname=x HTTP/1.0\r\n",
     ["hunter2", "alice:"], ["domains.google.com", "hostname=x"]),
    ("checkip command environment",
     "INADYN_PROVIDER=\"default@tunnelbroker.net\" INADYN_USER=\"alice\" getrealip.sh",
     ["\"alice\""], ["INADYN_PROVIDER=\"default@tunnelbroker.net\"", "getrealip.sh"]),
    ("cloudflare token headers",
     "PATCH /client/v4/zones/abc/dns_records/def HTTP/1.0\r\nX-Auth-Email: me@example.com\r\nX-Auth-Key: 0123456789abcdef\r\n"
     "Authorization: Bearer tok_live_xyz\r\nContent-Type: application/json\r\n\r\n{\"content\":\"203.0.113.9\"}",
     ["me@example.com", "0123456789abcdef", "tok_live_xyz"], ["PATCH /client/v4/zones/abc/dns_records/def", "Content-Type: application/json", "203.0.113.9"]),
    ("nothing secret passes through unchanged",
     "GET /checkip HTTP/1.0\r\nHost: checkip.dyndns.org\r\n\r\n",
     [], ["GET /checkip HTTP/1.0\r\nHost: checkip.dyndns.org\r\n\r\n"]),
]

def c_lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") + '"'

main = ["#include <stdio.h>", "#include <string.h>", "#include <stdlib.h>", body,
        "int main(void) {", "  const char *r;"]
for i, (name, inp, gone, keep) in enumerate(CASES):
    main.append('  r = log_redact(%s); printf("CASE %d\\n%%s\\nEND %d\\n", r); ' % (c_lit(inp), i, i))
# a 6000-byte input must come back bounded and marked truncated, never overrun
main.append('  { char *big = malloc(6001); memset(big, \'a\', 6000); big[6000] = 0; r = log_redact(big); printf("BIG %zu %s\\n", strlen(r), strlen(r) >= 3 && !strcmp(r + strlen(r) - 3, "...") ? "dots" : "nodots"); free(big); }')
main.append('  { r = log_redact(NULL); printf("NULL [%s]\\n", r); }')
main.append("  return 0; }")

td = tempfile.mkdtemp(prefix="redact-")
cpath = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
open(cpath, "w").write("\n".join(main) + "\n")
p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wno-unused-parameter", "-o", exe, cpath], capture_output=True, text=True)
if p.returncode != 0:
    die("host compile failed:\n" + p.stderr)
check("log_redact compiles clean with -Wall -Wextra", "warning" not in p.stderr, p.stderr)
# bytes, decoded by hand: text mode would fold the \r\n the requests carry into \n
out = subprocess.run([exe], capture_output=True).stdout.decode("utf-8", "replace")
for i, (name, inp, gone, keep) in enumerate(CASES):
    seg = re.search(r"CASE %d\n(.*?)\nEND %d\n" % (i, i), out, re.S)
    got = seg.group(1) if seg else ""
    check("%s: secrets gone" % name, all(g not in got for g in gone), got)
    check("%s: the rest survives" % name, all(k in got for k in keep), got)
    if gone:
        check("%s: a [redacted] marker is left behind" % name, "[redacted]" in got, got)
big = re.search(r"BIG (\d+) (\w+)", out)
check("oversize input is bounded (< 4096) and ends in '...'", big and int(big.group(1)) < 4096 and big.group(2) == "dots", out[-120:])
check("NULL input yields an empty string, not a crash", "NULL []" in out, out[-60:])

# --- every request-buffer log line goes through log_redact()
bad = []
for path in sorted(glob.glob(os.path.join(src_root, "inadyn", "src", "*.c")) + glob.glob(os.path.join(src_root, "inadyn", "plugins", "*.c"))):
    if not os.path.isfile(path):   # inadyn/src carries a dangling ifaddrs.c symlink
        continue
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        if "logit(" in line and "request_buf" in line and "log_redact(" not in line:
            bad.append("%s:%d" % (os.path.relpath(path, src_root), n))
check("every logit() of a request buffer in inadyn is wrapped in log_redact()", not bad, bad)

shutil.rmtree(td, ignore_errors=True)
if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall inadyn-redact checks passed")
sys.exit(0)
