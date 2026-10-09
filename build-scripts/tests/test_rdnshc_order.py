#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The resolver health check's dual-stack order (dual-stack review 2026-10-08, F4) - helper on the host, wiring pinned.

WHY THIS EXISTS. The firmware writes the router's DNS list as "WAN IPv4 servers, then IPv6 servers",
so a LAN resolver reachable over both families landed as "its IPv4, <off-site IPv4>, its IPv6": with
strict order the IPv6 face was never tried before the off-site server, and when only the IPv4 face
died the health check (alive if EITHER face answers) left the list alone, so every fresh query
stalled on the dead face until the client retransmitted and then went off-site - never to the
server's own IPv6. The fix probes both faces every tick, keeps the IPv6 line directly behind the
IPv4 one, moves a dead face behind the other servers on its own, and closes the DNS intercept gate
per family. The order lives in shared/reaper_resolv_order.c as pure integer logic over a per-line
classification, so it can be proved here.

WHAT IT DOES. Compiles shared/reaper_resolv_order.c on the host behind a small main and asserts
the order for every face state over the shapes the firmware writes; then pins the wiring: rdnshc
classifies lines per face, probes both faces, writes the per-family markers and calls the helper;
reaper_fw's gate script walks both families on their own markers; libshared builds the helper and
shared.h exposes it; the markers pin the staged rc. Exit 0 pass, 1 fail, 77 skipped (no gcc, or
no router source tree - argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_resolv_order.c")):
    skip("no router source tree with shared/reaper_resolv_order.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "reaper_resolv_order.h"
/* argv: "<cls,cls,...>:<down4><down6>" -> "<changed> <idx idx ...>" */
int main(int argc, char **argv)
{
	int a;
	for (a = 1; a < argc; a++) {
		int cls[64], out[64], n = 0, i, ch;
		char *s = strdup(argv[a]), *colon = strchr(s, ':'), *tok;
		int d4 = 0, d6 = 0;
		if (colon) { *colon = 0; d4 = colon[1] == '1'; d6 = colon[2] == '1'; }
		for (tok = strtok(s, ","); tok && n < 64; tok = strtok(NULL, ",")) cls[n++] = atoi(tok);
		ch = reaper_resolv_order(cls, n, d4, d6, out);
		printf("%d", ch);
		for (i = 0; i < n; i++) printf(" %d", out[i]);
		printf("\n");
		free(s);
	}
	return 0;
}
'''
td = tempfile.mkdtemp(prefix="rro-")
try:
    csrc = os.path.join(td, "t.c")
    with open(csrc, "w") as f:
        f.write(MAIN)
    exe = os.path.join(td, "t")
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-o", exe, csrc,
                        os.path.join(SRC, "shared", "reaper_resolv_order.c"), "-I", os.path.join(SRC, "shared")],
                       capture_output=True, text=True)
    if p.returncode != 0:
        die("host compile failed:\n" + p.stderr)
    if "warning" in p.stderr:
        die("host compile warnings:\n" + p.stderr)
    check("shared/reaper_resolv_order.c compiles clean with -Wall -Wextra", True)

    def run(cases):
        r = subprocess.run([exe] + cases, capture_output=True, text=True)
        if r.returncode != 0:
            die("test binary failed: %s %s" % (r.stdout, r.stderr))
        return dict(zip(cases, r.stdout.splitlines()))

    # classes: 0 other line, 1 another upstream, 4 the server's IPv4 line, 6 its IPv6 line
    cases = {
        # the firmware's shape: its IPv4, off-site, its IPv6 - healthy: IPv6 pulled up behind IPv4
        "4,1,6:00": "1 0 2 1",
        "4,6,1:00": "0 0 1 2",          # already right: nothing to rewrite
        # IPv4 face dead, IPv6 alive: the IPv6 line takes the server's place, the IPv4 line goes last
        "4,1,6:10": "1 2 1 0",
        "4,6,1:10": "1 1 2 0",
        # IPv6 face dead, IPv4 alive: the IPv6 line goes last (already last in the firmware's shape)
        "4,1,6:01": "0 0 1 2",
        "4,6,1:01": "1 0 2 1",
        # both dead = the old whole-server demotion
        "4,1,6:11": "1 1 0 2",
        "4,6,1:11": "1 2 0 1",
        # the server listed second by the admin keeps that place; only its own faces move
        "1,4,6:00": "0 0 1 2",
        "1,4,1,6:00": "1 0 1 3 2",
        "1,4,1,6:10": "1 0 3 2 1",
        # a v6-only server (no IPv4 face)
        "1,6:01": "0 0 1",
        "6,1:01": "1 1 0",
        "6,1:00": "0 0 1",
        # other lines (options, domain routes) never move
        "0,4,1,0,6,0:00": "1 0 1 4 2 3 5",
        "0,4,1,0,6,0:10": "1 0 4 2 3 5 1",
        # no face in the file, or nothing at all: identity, not changed
        "1,1,0:11": "0 0 1 2",
        "1:00": "0 0",
    }
    got = run(list(cases))
    for k, want in cases.items():
        check("order %s -> %s" % (k, want), got.get(k) == want, got.get(k))
finally:
    shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- wiring
hdr = read("shared/reaper_resolv_order.h")
check("reaper_resolv_order.h defines the four classes and the entry point",
      all(x in hdr for x in ("#define RRO_OTHER", "#define RRO_UPSTREAM", "#define RRO_FACE4", "#define RRO_FACE6", "int reaper_resolv_order(const int *cls, int n, int down4, int down6, int *out);")))
mk = read("shared/Makefile"); sh = read("shared/shared.h")
check("libshared builds it and shared.h exposes it",
      "OBJS += reaper_resolv_order.o" in mk and '#include "reaper_resolv_order.h"' in sh)

rd = read("rc/rdnshc.c")
check("rdnshc classifies the server's lines per face",
      "static int line_face(" in rd and "return RRO_FACE4;" in rd and rd.count("return RRO_FACE6;") == 2)
check("rdnshc probes BOTH faces every tick (the IPv4 probe no longer skipped after an IPv6 answer)",
      "if (v6_ready) ok6 = probe_addr(&c, a6, AF_INET6);" in rd and "if (a4) ok4 = probe_addr(&c, a4, AF_INET);" in rd
      and "if (!alive && a4 && probe_addr(&c, a4, AF_INET))" not in rd)
check("rdnshc orders the files through the shared helper and rewrites them in that order",
      "reaper_resolv_order(cls, n, down4, down6, out)" in rd and "fputs(lines[out[i]], fp);" in rd)
check("rdnshc keeps one counter set per face with the configured thresholds",
      "fmiss[i] >= c.fail && alive" in rd and "fdown[i] && fhit[i] >= c.recover" in rd)
check("rdnshc writes the per-family markers the gate reads and runs the gate when they change",
      '#define HC_DOWN4\t"/tmp/reaper/rdnshc.down4"' in rd and '#define HC_DOWN6\t"/tmp/reaper/rdnshc.down6"' in rd
      and "if (face_marks(fdown[0], fdown[1]))" in rd and rd.count("face_marks(fdown[0], fdown[1]);") >= 2)
check("rdnshc restores through stock order plus the faces' order, and names a face that stays behind",
      "static void restore(const struct hc_cfg *c, int down4, int down6)" in rd
      and "over IPv6 only for now; its IPv4 line stays behind the others" in rd)
check("rdnshc logs a face flip both ways (syslog contract: state changes only)",
      "stopped answering over %s (%d misses) but still answers over %s" in rd and "answers over %s again (%d hits)" in rd)

check("rdnshc reports each face in its state (fields 4 and 5: 1 / 0 / - / x)",
      'snprintf(st, sizeof(st), "%s %ld %d %c %c", what' in rd and "g_f6 = !(c.af == AF_INET6 || c.alt_af == AF_INET6) ? '-' : (!v6_ready ? 'x'" in rd)
pg = read("www/Reaper_Failover.asp")
check("DNS Failover shows an IPv6 status line under the IPv4 one, Disabled while IPv6 is off",
      'id="st6_v"' in pg and "function render6(st, running, mode)" in pg and "if(!V6ON){ txt = T.v6disabled;" in pg
      and pg.index('id="st_v"') < pg.index('id="st6_v"'))
check("DNS Failover header carries an IPv6 status + server pair under the IPv4 one, Disabled while IPv6 is off",
      'id="chip_state6"' in pg and 'id="chip_target6_v"' in pg and "if(!V6ON){ c6.className = 'chip dim'; c6v.textContent = T.disabled; }" in pg
      and "disabled: `<#CTL_Disabled#>`" in pg and pg.index('id="chip_target"') < pg.index('id="chip_state6"'))
import glob as _g
packs = [x for x in _g.glob(os.path.join(SRC, "www", "*.dict")) if not x.endswith("temp.dict")]
miss = [os.path.basename(x) for x in packs if any(("RDHC_%d=" % k) not in open(x, encoding="utf-8", errors="replace").read() for k in range(46, 53))]
check("RDHC_46..52 exist in all 25 language packs", len(packs) == 25 and not miss, miss)
fw = read("rc/reaper_fw.c")
check("the IPv6 side is never used while IPv6 is disabled: the probe, the ordering, the flags and the gate script",
      "if (!c->v6_on) return 0;" in rd and "c.v6_on = v6_ready;" in rd
      and "if (!v6_ready) { fseen[1] = 0; fdown[1] = 0; fmiss[1] = fhit[1] = 0; }" in rd
      and "fdown[0] = (c.af == AF_INET); fdown[1] = v6_ready;" in rd
      and "int hc_v6 = ipv6_enabled();" in fw and 'hc_v6 ? "iptables ip6tables" : "iptables"' in fw and '"for T in %s; do\\n"' in fw)
check("reaper_fw's gate script walks both families on their own markers",
      '#define RFW_HC_DOWN4 "/tmp/reaper/rdnshc.down4"' in fw and '#define RFW_HC_DOWN6 "/tmp/reaper/rdnshc.down6"' in fw
      and 'case $T in iptables) F=ipv4; M=" RFW_HC_DOWN4 ";; *) F=ipv6; M=" RFW_HC_DOWN6 ";; esac' in fw
      and 'if [ -e " RFW_HC_STATE " ] || [ -e $M ]; then' in fw)
check("a ruleset rebuild re-closes each family on its own marker, not only on the whole-server state",
      '{ [ -e " RFW_HC_STATE " ] || [ -e " RFW_HC_DOWN4 " ]; } && iptables -t nat' in fw
      and '{ [ -e " RFW_HC_STATE " ] || [ -e " RFW_HC_DOWN6 " ]; } && ip6tables -t nat' in fw)
check("reaper_fw's gate script flushes only the family it switched",
      "flush() {" in fw and "flush $F" in fw and "for _f in ipv4 ipv6; do case" not in fw)
check("reaper_fw's gate script names the family in both log lines",
      "intercept gate CLOSED ($F):" in fw and "intercept gate OPEN ($F):" in fw)

here = os.path.dirname(os.path.abspath(__file__))
mk_path = os.path.join(here, "..", "verify_markers.txt")
if os.path.isfile(mk_path):
    m = open(mk_path, encoding="utf-8").read()
    check("verify_markers pins the face move, the per-family gate and the marker path in the staged rc",
          "sbin/rc|stopped answering over |1" in m and "sbin/rc|intercept gate CLOSED ($F)|1" in m and "sbin/rc|/tmp/reaper/rdnshc.down4|1" in m)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
