#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal: a device that has not signed in gets the portal's address for every lookup (2026-11-12).

WHY THIS EXISTS. Field report: Android 17 / iOS 27 showed no "Sign in to network" on a Guest Portal network and
then "No internet". A phone offers the sign-in page only when its probe name resolves and the HTTP request is
redirected. Before sign-in coova-chilli let lookups through to the network's own resolver only, which has no
upstream while the network's VPN client is down (fail-closed by the owner's choice): no answer, no redirect.

WHAT IT DOES. Compiles the REAPER-PREAUTH block of coovachilli/src/dhcp.c on the host and runs the decision table
(signed in or not, A / AAAA / other types, walled-garden names exact and as a suffix, a malformed question) and
the question-type reader on real DNS question bytes; then pins the wiring in dhcp_dns(): the branch is last in the
match chain (so the portal's own host name still answers first), uses the portal alias address, and a non-A
question is answered with the question alone and ancount 0. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router
tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, struct, subprocess, sys, tempfile

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

src = open(DHCP, encoding="utf-8", errors="surrogateescape").read()
m = re.search(r"/\* REAPER-PREAUTH-BEGIN.*?\*/(.*?)/\* REAPER-PREAUTH-END \*/", src, re.S)
check("dhcp.c carries the REAPER-PREAUTH block", m is not None)
if not m:
    print("\n1 check failed"); sys.exit(1)

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
%s
static unsigned char hex(char c) { return (unsigned char)(c <= '9' ? c - '0' : c - 'a' + 10); }
int main(int argc, char **argv)
{
	if (argv[1][0] == 'd') {	/* d signed_in qtype name [garden ...] */
		char *doms[8] = { 0 };
		int i;
		for (i = 5; i < argc && i - 5 < 8; i++) doms[i - 5] = argv[i];
		printf("%%d\n", reaper_preauth_dns(atoi(argv[2]), atoi(argv[3]), argv[4], doms, 8));
	} else {			/* q hexbytes */
		unsigned char b[512]; size_t n = 0; const char *h = argv[2];
		while (h[0] && h[1] && n < sizeof(b)) { b[n++] = (unsigned char)(hex(h[0]) << 4 | hex(h[1])); h += 2; }
		printf("%%d\n", reaper_dns_qtype(b, n));
	}
	return 0;
}
'''
tmp = tempfile.mkdtemp()
try:
    c = os.path.join(tmp, "p.c"); exe = os.path.join(tmp, "p")
    open(c, "w").write(MAIN % m.group(1))
    r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    check("the block compiles with -Wall -Werror", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        def d(signed, qt, name, *garden):
            return subprocess.run([exe, "d", str(signed), str(qt), name] + list(garden), capture_output=True, text=True).stdout.strip()
        def q(hx):
            return subprocess.run([exe, "q", hx], capture_output=True, text=True).stdout.strip()
        check("not signed in, A lookup of a phone probe -> the portal address",
              d(0, 1, "captive.apple.com") == "1" and d(0, 1, "connectivitycheck.gstatic.com") == "1")
        check("not signed in, AAAA / HTTPS (65) lookup -> an empty answer", d(0, 28, "captive.apple.com") == "2" and d(0, 65, "www.google.com") == "2")
        check("signed in -> forwarded as before, any type", d(1, 1, "captive.apple.com") == "0" and d(1, 28, "example.com") == "0")
        check("walled-garden name, exact or a subdomain -> forwarded",
              d(0, 1, "pay.example.com", "pay.example.com") == "0" and d(0, 1, "a.pay.example.com", "pay.example.com") == "0"
              and d(0, 1, "x.cdn.net", ".cdn.net") == "0")
        check("a name that only ends with the garden text (no dot boundary) is NOT the garden",
              d(0, 1, "notpay.example.com", "pay.example.com") == "1")
        check("unreadable question or empty name -> forwarded", d(0, -1, "example.com") == "0" and d(0, 1, "") == "0")
        def qhex(name, qtype):
            b = b"".join(bytes([len(x)]) + x.encode() for x in name.split(".")) + b"\0" + struct.pack(">HH", qtype, 1)
            return b.hex()
        check("question type read from real question bytes (A, AAAA, HTTPS)",
              q(qhex("captive.apple.com", 1)) == "1" and q(qhex("captive.apple.com", 28)) == "28" and q(qhex("www.google.com", 65)) == "65")
        check("question type: a compression pointer or a truncated question -> -1",
              q("c00c00010001") == "-1" and q(qhex("captive.apple.com", 1)[:-6]) == "-1" and q("3f61") == "-1")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# the block must stand on its own between functions: the _r1 build broke on "duplicate 'static'" because it had
# been inserted between dhcp_matchDNS's own "static " line and its "int dhcp_matchDNS(" line
check("the block sits between whole functions (dhcp_matchDNS keeps its own 'static' line)",
      re.search(r"static\s*/\* REAPER-PREAUTH-BEGIN", src) is None
      and "/* REAPER-PREAUTH-END */\n\nstatic \nint dhcp_matchDNS(uint8_t *r, char *name) {" in src)

# ---------------------------------------------------------------- wiring in dhcp_dns()
fn = src[src.find("int dhcp_dns(struct dhcp_conn_t *conn, uint8_t *pack,"):]
fn = fn[:fn.find("\nint dhcp_", 10)]
br = fn.find("/* reaper 2026-11-12: a device that has not signed in - see reaper_preauth_dns */")
check("the pre-auth branch sits in dhcp_dns()", br > 0)
check("it is the LAST match: after logout, the WAN-down answer, the portal host name and alias, and the local domain",
      0 < fn.find('dhcp_matchDNS(q, "logout")') < br and 0 < fn.find("if (!match && hostname) {") < br
      and 0 < fn.find("if (!match && aliasname) {") < br and 0 < fn.find("_options.domaindnslocal && _options.domain") < br
      and fn.find("      if (match) {\n", br) > br)
check("signed-in test is the connection's own state; the walled garden and the domain file are honoured",
      "reaper_preauth_dns(conn->authstate == DHCP_AUTH_PASS," in fn and "_options.uamdomains, MAX_UAM_DOMAINS);" in fn
      and "garden_check_domainfile((char *)q) == 1)" in fn)
check("the answer is an outside address that goes through chilli's own redirect to uamlisten:uamport - NOT the alias, "
      "which chilli rewrites onto its UI port 3991 (_r2: the sign-in page then reloaded for ever)",
      "reaper_redir.s_addr = htonl(0xC6120001);	/* 198.18.0.1 */\n\t  memcpy(reply, &reaper_redir.s_addr, 4);" in fn
      and "memcpy(reply, &_options.uamalias.s_addr, 4);\n\t}\n      }\n\n      if (match) {" not in fn)
check("a non-A question: question alone, ancount 0; an A answer keeps TTL 0",
      "if (!reaper_noans) {	/* reaper 2026-11-12" in fn and "answer_dns->ancount = htons(reaper_noans ? 0x0000 : 0x0001);" in fn
      and "\tquery[query_len++] = 0x00;\n\tquery[query_len++] = 0x00;\n\tquery[query_len++] = 0x00;\n\tquery[query_len++] = 0x00;\n\tquery[query_len++] = 0x00;\n\tquery[query_len++] = 0x04;" in fn)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
