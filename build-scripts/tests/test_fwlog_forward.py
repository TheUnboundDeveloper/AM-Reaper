#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The firewall log's remote forward: room for bursts, and visible loss (owner, 2026-11-10, image _r6).

WHY THIS EXISTS. rflogd sends every firewall line to the remote log server set on the System Log page, one UDP
datagram per line, without waiting. With the default send buffer a burst at the flood ceiling (10000 lines a
second per rule) could fill the socket, and a line that could not be sent was only counted in a file nobody
looked at. Now the forward socket asks for a 1 MB buffer (SO_SNDBUFFORCE; CAP_NET_ADMIN is kept), the size it got
is in stats.json, the first unsent line in a minute goes to the system log, the Firewall page shows sent / not
sent (amber when any were not), and the diag (v1.3.57) reports the collector and the forward in section 14 with
findings. A server that is set but is not an address is said plainly: nothing is forwarded to it.

WHAT IT DOES. Compiles rflogd's real rfl_fwd_open() and rfl_forward() on the host and sends lines to a local UDP
receiver, then forces send failures to check the count and the once-a-minute log line; runs the diag's new
section-14 lines in sh against sample stats files; runs the page's callback in node against sample answers;
pins httpd and the language packs.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import glob, json, os, re, shutil, socket, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RFL = os.path.join(SRC, "rflogd", "rflogd.c") if SRC else ""
if not RFL or not os.path.isfile(RFL):
    skip("no router source tree with rflogd/rflogd.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
def cut(text, start, end):
    a = text.find(start); b = text.find(end, a + 1) if a >= 0 else -1
    return text[a:b] if 0 <= a < b else ""
tmp = tempfile.mkdtemp(prefix="fwlogfwd-")

# ------------------------------------------------------------------ rflogd: the forward
c = rd(RFL)
fwd = cut(c, "static void rfl_forward(const char *body, long long sec)", "\nstatic void rfl_line(")
opn = cut(c, "static void rfl_fwd_open(void)", "\nstatic void rfl_conf_load(void)")
check("rflogd: the two functions are found", "sendto(" in fwd and "socket(" in opn)
m = re.search(r"#define RFL_FWD_SNDBUF\s+\(1 << 20\)", c)
check("rflogd: the forward socket asks for 1 MB", m is not None)
check("rflogd: FORCE first (passes wmem_max), plain SO_SNDBUF as the fallback, the size read back",
      opn.find("SO_SNDBUFFORCE") < opn.find("SO_SNDBUF, &sz") < opn.find("getsockopt(fwd_fd, SOL_SOCKET, SO_SNDBUF"))
check("rflogd: the forward is opened after the capabilities are dropped, and CAP_NET_ADMIN is among those kept",
      c.find("rfl_drop_caps();\n\trfl_fwd_open();") > 0 and "CAP_NET_ADMIN" in cut(c, "static void rfl_drop_caps(void)", "\n}\n"))
check("rflogd: stats.json carries the buffer size", '\\"fwd_sndbuf\\":%d' in c and "n_fwd, n_fwd_err, fwd_sndbuf);" in c)
H = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>
#include <syslog.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#define RFL_LINE 1024
#define RFL_FWD_SNDBUF (1 << 20)
static struct { char fwd_host[64]; int fwd_port; char host[64]; } C;
static int fwd_fd = -1, fwd_sndbuf, stats_dirty, NLOG;
static long fwd_err_at = -1000, NOW = 1000;
static unsigned long long n_fwd, n_fwd_err;
static struct sockaddr_storage fwd_sa; static socklen_t fwd_salen;
static char fwd_dst[INET6_ADDRSTRLEN + 8], fwd_dpt[24];	/* review 2026-11-11: see rfl_forward() */
static long mono(void) { return NOW; }
static int FAIL;
static ssize_t t_sendto(int fd, const void *b, size_t n, int fl, const struct sockaddr *a, socklen_t l) {
  if (FAIL) { errno = EAGAIN; return -1; } return sendto(fd, b, n, fl, a, l); }
static void t_syslog(int pri, const char *fmt, ...) { (void)pri; NLOG++; printf("syslog: %s\n", fmt); }
#define sendto t_sendto
#define syslog t_syslog
''' + opn + "\n" + fwd + r'''
int main(int argc, char **argv) {
  int i, n = atoi(argv[3]);
  snprintf(C.fwd_host, sizeof(C.fwd_host), "%s", argv[1]); C.fwd_port = atoi(argv[2]); snprintf(C.host, sizeof(C.host), "router");
  rfl_fwd_open();
  printf("fd=%d sndbuf=%d\n", fwd_fd >= 0, fwd_sndbuf);
  for (i = 0; i < n; i++) rfl_forward("ACCEPT IN=br0 OUT=eth0 SRC=192.0.2.1 DST=198.51.100.1 PROTO=TCP SPT=1 DPT=2", 1731300000);
  printf("sent=%llu err=%llu log=%d\n", n_fwd, n_fwd_err, NLOG);
  { /* review 2026-11-11: a line about our own forward packet is not forwarded; near misses are */
    unsigned long long b0 = n_fwd, b1, b2; char s[200];
    snprintf(s, sizeof(s), "DROP IN= OUT=eth0 SRC=192.0.2.1 DST=%s LEN=120 PROTO=UDP SPT=40000 DPT=%d LEN=100 ", argv[1], C.fwd_port);
    for (i = 0; i < 3; i++) rfl_forward(s, 1731300000);
    b1 = n_fwd;
    snprintf(s, sizeof(s), "DROP IN= OUT=eth0 SRC=192.0.2.1 DST=%s LEN=120 PROTO=UDP SPT=40000 DPT=%d LEN=100 ", argv[1], C.fwd_port + 1);
    rfl_forward(s, 1731300000);
    snprintf(s, sizeof(s), "DROP IN= OUT=eth0 SRC=192.0.2.1 DST=%s0 LEN=120 PROTO=UDP SPT=40000 DPT=%d LEN=100 ", argv[1], C.fwd_port);
    rfl_forward(s, 1731300000);
    b2 = n_fwd;
    if (n) printf("self=%llu near=%llu\n", b1 - b0, b2 - b1);
    n_fwd = b0;	/* the counts below are the earlier test's */
  }
  FAIL = 1;
  for (i = 0; i < 500; i++) rfl_forward("DROP x", 1731300000);
  printf("after-fail sent=%llu err=%llu log=%d dirty=%d\n", n_fwd, n_fwd_err, NLOG, stats_dirty);
  NOW += 59; rfl_forward("DROP x", 1731300000); printf("59s log=%d\n", NLOG);
  NOW += 1; rfl_forward("DROP x", 1731300000); printf("60s log=%d err=%llu\n", NLOG, n_fwd_err);
  return 0; }
'''
cf = os.path.join(tmp, "fwd.c"); xf = os.path.join(tmp, "fwd")
open(cf, "w").write(H)
r = subprocess.run([CC, "-O1", "-Wall", "-Werror", "-Wno-unused-function", "-o", xf, cf], capture_output=True, text=True)
check("rflogd: the real forward code compiles on the host", r.returncode == 0, r.stderr)
if r.returncode == 0:
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rx.bind(("127.0.0.1", 0))
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)
    port = rx.getsockname()[1]
    o = subprocess.run([xf, "127.0.0.1", str(port), "2000"], capture_output=True, text=True, timeout=60).stdout
    rx.settimeout(0.5); got = []
    try:
        while True: got.append(rx.recv(2048))
    except socket.timeout: pass
    rx.close()
    m1 = re.search(r"fd=(\d) sndbuf=(\d+)", o)
    check("forward: a socket is opened for an IPv4 server and has a send buffer", m1 and m1.group(1) == "1" and int(m1.group(2)) > 0, o)
    check("forward: 2000 lines sent and counted, none failed", "sent=2000 err=0 log=0" in o, o)
    check("forward: the server received them as RFC 3164 lines, facility kern, severity notice, tagged rflogd",
          len(got) >= 1990 and all(g.startswith(b"<5>") and b" router rflogd: ACCEPT IN=br0" in g for g in got[:50]), (len(got), got[:1]))
    check("forward: failed sends are counted and mark the stats for rewriting, the system log gets ONE line",
          "after-fail sent=2000 err=500 log=1 dirty=1" in o, o)
    check("forward: no second log line within the minute, one more after it", "59s log=1" in o and "60s log=2 err=502" in o, o)
    check("forward: a line about the forward's own packet (same address AND port) is never sent on; another port or address is",
          "self=0 near=2" in o, o)
    o6 = subprocess.run([xf, "::1", str(port), "0"], capture_output=True, text=True, timeout=30).stdout
    check("forward: an IPv6 server address opens an IPv6 socket", o6.startswith("fd=1"), o6)
    on = subprocess.run([xf, "logs.example.net", "514", "3"], capture_output=True, text=True, timeout=30).stdout
    check("forward: a name, not an address, opens nothing, says so once, and forwards nothing",
          "fd=0 sndbuf=0" in on and "is not an address" in on and "sent=0 err=0" in on, on)

# ------------------------------------------------------------------ httpd
web = rd(os.path.join(SRC, "httpd", "web.c"))
h = cut(web, 'if (strcmp(action, "fwlog_stats") == 0) {', "\n\t}\n")
check("httpd: fwlog_stats says whether a server is set, never which", '\\"fwd_set\\":%d' in h and '*nvram_safe_get("log_ipaddr") ? 1 : 0' in h
      and h.count("log_ipaddr") == 1)

# ------------------------------------------------------------------ the page
pg = rd(os.path.join(SRC, "www", "Reaper_Firewall.asp"))
check("page: the forward line element", '<p class="note hidden" id="l_fwd"></p>' in pg)
cb = cut(pg, "xhr('/reaper_fw.cgi?action=fwlog_stats&http_id='+encodeURIComponent(REAPER_HTTPID),function(s){", "\n  });")
NODE = shutil.which("node")
if not NODE or not cb:
    check("page: the callback is found", bool(cb))
    print("skip page run: no node")
else:
    en = {}
    for line in open(os.path.join(SRC, "www", "EN.dict"), encoding="utf-8"):
        if "=" in line: k, v = line.rstrip("\n").split("=", 1); en[k] = v
    body = re.sub(r"<#([A-Za-z0-9_]+)#>", lambda mm: en.get(mm.group(1), "MISSING:" + mm.group(1)), cb)
    js = ("var E={l_coll:{className:'',textContent:''},l_fwd:{className:'',textContent:''}};function $(i){return E[i];}\n"
          "var cb=function(s){" + body[body.find("function(s){") + len("function(s){"):] + "};\n"
          "var cases=" + json.dumps({
              "on": {"ok": 1, "running": 1, "path": "nflog", "fwd_set": 1, "stats": {"rx": 9, "fwd": 1, "fwd_sent": 1200, "fwd_err": 0}},
              "lost": {"ok": 1, "running": 1, "path": "nflog", "fwd_set": 1, "stats": {"rx": 9, "fwd": 1, "fwd_sent": 1200, "fwd_err": 37}},
              "name": {"ok": 1, "running": 1, "path": "nflog", "fwd_set": 1, "stats": {"rx": 9, "fwd": 0}},
              "off": {"ok": 1, "running": 1, "path": "nflog", "fwd_set": 0, "stats": {"rx": 9, "fwd": 0}},
              "fallback": {"ok": 1, "running": 0, "path": "log", "fwd_set": 1, "stats": None}}) + ";\n"
          "var out={};for(var k in cases){E.l_fwd={className:'',textContent:''};cb(cases[k]);out[k]=[E.l_fwd.className,E.l_fwd.textContent];}\n"
          "console.log(JSON.stringify(out));\n")
    jf = os.path.join(tmp, "cb.js"); open(jf, "w", encoding="utf-8").write(js)
    r = subprocess.run([NODE, jf], capture_output=True, text=True, timeout=60)
    try: out = json.loads(r.stdout)
    except Exception: out = {}
    check("page: the callback runs", bool(out), r.stderr[:400])
    if out:
        check("page: forwarding - plain note with the two counts", out["on"][0] == "note" and "1200 lines sent, 0 not sent" in out["on"][1], out["on"])
        check("page: lines not sent - amber", out["lost"][0] == "note warn" and "37 not sent" in out["lost"][1], out["lost"])
        check("page: a server set but not forwarded to - amber, says it must be an IP address",
              out["name"][0] == "note warn" and "must be an IP address" in out["name"][1], out["name"])
        check("page: no server set - the line is hidden", out["off"][0] == "note hidden", out["off"])
        check("page: the collector not running - the line is hidden (the fallback goes through the system log)", out["fallback"][0] == "note hidden", out["fallback"])

# ------------------------------------------------------------------ the diag
DG = os.path.join(SRC, "others", "reaper_diag")
dg = rd(DG)
check("diag: v1.3.57 or later in the script and on its page (the collector lines came with v1.3.57)",
      re.search(r'VER="REAPER-DIAG v1\.3\.(5[7-9]|[6-9][0-9])"', dg) is not None and "REAPER-DIAG v1.3.5" in rd(os.path.join(SRC, "www", "Reaper_Diag.asp")))
snip = cut(dg, "# v1.3.57: the firewall log collector (rflogd)", '\nsec "14b.')
check("diag: the collector lines sit in section 14, before 14b", bool(snip) and dg.find('sec "14. FIREWALL') < dg.find(snip[:40]) < dg.find('sec "14b.'))
check("diag: the server's address is never printed (only whether it is set)", snip.count("log_ipaddr") == 1 and '[ -n "$(nvram get log_ipaddr' in snip)
SH = shutil.which("busybox")
def diag_run(stats, path, ipaddr, running):
    d = os.path.join(tmp, "dg"); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    if stats is not None: open(os.path.join(d, "stats.json"), "w").write(json.dumps(stats, separators=(",", ":")))   # as rflogd writes it
    if path is not None: open(os.path.join(d, "path"), "w").write(path + "\n")
    body = snip.replace("/tmp/reaper/fwlog", d)
    pre = ("FIND=%s/find\n: > \"$FIND\"\nfinding() { echo \"  [$1] $2\" >> \"$FIND\"; }\n"
           "nvram() { [ \"$2\" = log_ipaddr ] && echo '%s'; }\npidof() { return %d; }\n") % (d, ipaddr, 0 if running else 1)
    sf = os.path.join(d, "t.sh"); open(sf, "w").write(pre + body + '\necho "--find--"; cat "$FIND"\n')
    shells = [["sh", sf]] + ([[SH, "ash", sf]] if SH else [])
    return [subprocess.run(s, capture_output=True, text=True, timeout=30).stdout for s in shells]
ST = {"updated": 1, "since": 1, "pid": 9, "mode": "full", "rx": 5000, "written": 812345, "lost_seq": 0, "bad": 0, "enobufs": 0,
      "suppressed": 12, "ring_bytes": 1, "ram_kb": 2048, "store": "none", "fwd": 1, "fwd_sent": 4990, "fwd_err": 0,
      "fwd_sndbuf": 2097152, "groups": [{"g": 40, "rx": 77, "lost": 0, "suppressed": 0}]}
for o in diag_run(ST, "nflog", "192.0.2.9", True):
    check("diag: counters are the top-level ones, not a group's (rx 5000, not 77)",
          "path=nflog running=yes lines=5000 written_bytes=812345 lost=0 held_back=12 enobufs=0" in o, o)
    check("diag: the forward line, and no finding when nothing was lost", "remote forward=on sent=4990 not_sent=0 send_buffer=2097152" in o
          and o.rstrip().endswith("--find--"), o)
    check("diag: the address is not in the output", "192.0.2.9" not in o)
bad = dict(ST, lost_seq=3, fwd_err=41)
for o in diag_run(bad, "nflog", "192.0.2.9", True):
    check("diag: lost and unsent lines are findings", "[WARN] firewall log: 3 line(s) lost" in o and "[WARN] firewall log: 41 line(s) could not be sent" in o, o)
for o in diag_run(dict(ST, fwd=0, fwd_sent=0, fwd_sndbuf=0), "nflog", "logs.example.net", True):
    check("diag: a server set but not forwarded to is said, with a finding; its name is not printed",
          "remote forward=set-but-not-forwarded" in o and "[WARN] a remote log server is set but firewall lines are not forwarded" in o
          and "logs.example.net" not in o, o)
for o in diag_run(None, None, "", False):
    check("diag: no collector, no file - zeros, no shell error, no finding",
          "path=log running=no lines=0 written_bytes=0 lost=0 held_back=0 enobufs=0" in o and "remote forward=off sent=0 not_sent=0 send_buffer=0" in o
          and o.rstrip().endswith("--find--"), o)
r = subprocess.run(["sh", "-n", DG], capture_output=True, text=True)
check("diag: the whole script parses (sh -n)", r.returncode == 0, r.stderr)
if SH:
    r = subprocess.run([SH, "ash", "-n", DG], capture_output=True, text=True)
    check("diag: the whole script parses (busybox ash -n)", r.returncode == 0, r.stderr)

# ------------------------------------------------------------------ language packs
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if os.path.basename(p) != "temp.dict")
bad = []
for p in packs:
    t = open(p, encoding="utf-8").read().split("\n")
    i = [k for k, l in enumerate(t) if l.startswith("RFW_414=")]
    v = [l for l in t if l.startswith("RFW_415=") or l.startswith("RFW_416=")]
    if len(i) != 1 or t[i[0] + 1][:8] != "RFW_415=" or t[i[0] + 2][:8] != "RFW_416=" or len(v) != 2: bad.append(os.path.basename(p)); continue
    if any(ch in x for x in v for ch in ('"', "\\", "`", "${", "</")): bad.append(os.path.basename(p) + " chars")
    if v[0].count("%1") != 1 or v[0].count("%2") != 1: bad.append(os.path.basename(p) + " placeholders")
check("packs: RFW_415 / RFW_416 right after RFW_414 in all 25, no character that breaks the page, both placeholders", len(packs) == 25 and not bad, bad)
de = open(os.path.join(SRC, "www", "DE.dict"), encoding="utf-8").read()
check("packs: translated, not English placeholders (DE)", "RFW_415=Entfernter Protokollserver" in de)

shutil.rmtree(tmp, ignore_errors=True)
print("\n%d failed" % len(fails) if fails else "\nall passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
