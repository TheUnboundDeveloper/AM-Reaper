#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal: a frame the router itself sent on the portal's interface is not a client (2026-11-13).

WHY THIS EXISTS. At every start the portal logged a new client and held a pool address for the router's own
address. coova-chilli reads its interface through a packet socket, which also delivers the frames the router
sends there, and its ARP and IP paths open a client entry for any source address they have not seen. The entry
never signed in, so no list showed it; it cost one address and one log line per start.

WHAT IT DOES. Compiles the REAPER-OWNMAC block of coovachilli/src/dhcp.c on the host and runs it (own address,
another address, one byte off, an unknown all-zero interface address); then pins the wiring: dhcp_decaps_cb()
tests the frame's Ethernet source against the address of the interface the frame arrived on, returns before any
protocol handler runs, and the test sits after the length check. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no
router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
DHCP = os.path.join(SRC, "coovachilli", "src", "dhcp.c") if SRC else ""
if not DHCP or not os.path.isfile(DHCP):
    skip("no router tree with coovachilli/src/dhcp.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def done():
    print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
    if fails:
        print("\n".join(fails))
    sys.exit(1 if fails else 0)

src = open(DHCP, encoding="utf-8", errors="surrogateescape").read()
m = re.search(r"/\* REAPER-OWNMAC-BEGIN.*?\*/(.*?)/\* REAPER-OWNMAC-END \*/", src, re.S)
check("dhcp.c carries the REAPER-OWNMAC block", m is not None)
if not m:
    done()

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
%s
int main(int argc, char **argv)
{
	uint8_t a[6], b[6]; unsigned int v[12]; int i;
	if (argc != 3) return 2;
	if (sscanf(argv[1], "%%2x%%2x%%2x%%2x%%2x%%2x", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]) != 6) return 2;
	if (sscanf(argv[2], "%%2x%%2x%%2x%%2x%%2x%%2x", &v[6], &v[7], &v[8], &v[9], &v[10], &v[11]) != 6) return 2;
	for (i = 0; i < 6; i++) { a[i] = (uint8_t)v[i]; b[i] = (uint8_t)v[6 + i]; }
	printf("%%d\n", reaper_own_frame(a, b));
	return 0;
}
'''
tmp = tempfile.mkdtemp()
try:
    c = os.path.join(tmp, "o.c"); exe = os.path.join(tmp, "o")
    open(c, "w").write(MAIN % m.group(1))
    r = subprocess.run([CC, "-Wall", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("the block compiles with -Wall -Werror", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        def own(frame_src, if_addr):
            return subprocess.run([exe, frame_src, if_addr], capture_output=True, text=True).stdout.strip()
        check("source = the interface's own address -> the router's own frame", own("0211223344aa", "0211223344aa") == "1")
        check("another device's address -> a client frame", own("0211223344ab", "0211223344aa") == "0")
        check("first byte differs -> a client frame", own("0611223344aa", "0211223344aa") == "0")
        check("interface address unknown (all zero) -> nothing is filtered",
              own("000000000000", "000000000000") == "0" and own("0211223344aa", "000000000000") == "0")
        check("broadcast source against a real interface address -> not the router's frame", own("ffffffffffff", "0211223344aa") == "0")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# wiring in dhcp_decaps_cb()
f = re.search(r"\nint dhcp_decaps_cb\(void \*pctx, struct pkt_buffer \*pb\) \{(.*?)\n\}\n", src, re.S)
check("dhcp_decaps_cb() found", f is not None)
if f:
    body = f.group(1)
    call = re.search(r"if \(reaper_own_frame\(pkt_ethhdr\(packet\)->src, ctx->parent->rawif\[ctx->idx\]\.hwaddr\)\)\s*\n\s*return 0;", body)
    check("the frame's Ethernet source is tested against the address of the interface it arrived on, then dropped", call is not None)
    check("exactly one such test in the tree's dhcp.c", src.count("if (reaper_own_frame(") == 1)
    if call:
        at = call.start()
        first = [body.find(k) for k in ("dhcp_receive_arp(", "dhcp_receive_ip(", "dhcp_receive_ipv6(", "dhcp_receive_eapol(", "is_8021q(packet)", "dhcp_ignore(")]
        first = [x for x in first if x >= 0]
        check("the test runs before any protocol handler or tag parsing", bool(first) and at < min(first))
        ln = body.find("if (length < min_length)")
        check("the test runs after the minimum-length check", 0 <= ln < at)
    check("the block is defined before dhcp_decaps_cb()", src.index("REAPER-OWNMAC-END") < f.start())

done()
