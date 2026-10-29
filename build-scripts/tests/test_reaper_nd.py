#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The shared LAN IPv6 neighbour cache (shared/reaper_nd.c) compiles and answers.

WHY THIS EXISTS. IPv6 remediation 2026-10-07, step 0c: httpd (Flow Explorer, Devices,
the Gatekeeper captive check), gkd and rtrafd all need "which MAC owns this IPv6
address" and "which global IPv6 address does this MAC use". rtrafd carried a private
netlink dump; it is now one helper, and three consumers depend on its contract.

WHAT IT DOES. Compiles shared/reaper_nd.c on the host with -Wall -Wextra -Werror, then
runs a harness that (1) feeds a hand-built table through every lookup and checks the
answers, including the global/link-local/multicast/v4-mapped classifier, and (2) calls
reaper_nd_load() against the host kernel, which must return a non-negative count
without crashing (the host has no br* neighbours, so 0 is the normal answer).

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
C = os.path.join(SRC, "shared", "reaper_nd.c")
H = os.path.join(SRC, "shared", "reaper_nd.h")
if not SRC or not os.path.isfile(C) or not os.path.isfile(H):
    skip("no router source tree with shared/reaper_nd.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

MAIN = r'''
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include "reaper_nd.h"
static void put(struct reaper_nd *e, const char *ip, const char *mac, const char *br)
{
	memset(e, 0, sizeof(*e));
	inet_pton(AF_INET6, ip, e->ip);
	snprintf(e->mac, sizeof(e->mac), "%s", mac);
	snprintf(e->br, sizeof(e->br), "%s", br);
}
int main(void)
{
	struct reaper_nd t[6], live[512];
	unsigned char a[16];
	char mac[18], br[16];
	int n;
	put(&t[0], "fe80::1a2b:3c4d:5e6f:7a8b", "aa:bb:cc:dd:ee:01", "br0");	/* link-local first */
	put(&t[1], "2001:db8:1::10",            "aa:bb:cc:dd:ee:01", "br0");	/* the global one */
	put(&t[2], "fd00::20",                  "aa:bb:cc:dd:ee:02", "br55");	/* ULA counts as global */
	put(&t[3], "ff02::1",                   "aa:bb:cc:dd:ee:03", "br0");	/* multicast: never */
	put(&t[4], "::ffff:192.168.50.5",       "aa:bb:cc:dd:ee:04", "br0");	/* v4-mapped: never */
	put(&t[5], "::1",                       "aa:bb:cc:dd:ee:05", "br0");
	printf("global fe80=%d gua=%d ula=%d mcast=%d mapped=%d loop=%d\n",
	       reaper_nd_global(t[0].ip), reaper_nd_global(t[1].ip), reaper_nd_global(t[2].ip),
	       reaper_nd_global(t[3].ip), reaper_nd_global(t[4].ip), reaper_nd_global(t[5].ip));
	mac[0] = br[0] = 0;
	printf("mac_of_str 2001:db8:1::10 -> %d %s %s\n",
	       reaper_nd_mac_of_str(t, 6, "2001:db8:1::10", mac, sizeof(mac), br, sizeof(br)), mac, br);
	printf("mac_of_str miss -> %d\n", reaper_nd_mac_of_str(t, 6, "2001:db8:9::9", mac, sizeof(mac), NULL, 0));
	printf("mac_of_str v4 -> %d\n", reaper_nd_mac_of_str(t, 6, "192.168.50.5", mac, sizeof(mac), NULL, 0));
	inet_pton(AF_INET6, "fd00::20", a);
	printf("mac_of fd00::20 -> %d %s\n", reaper_nd_mac_of(t, 6, a, mac, sizeof(mac), NULL, 0), mac);
	n = reaper_nd_addr_of(t, 6, "AA:BB:CC:DD:EE:01", a);
	inet_ntop(AF_INET6, a, mac, sizeof(mac) > 46 ? 46 : 18);
	{
		char s[46];
		inet_ntop(AF_INET6, a, s, sizeof(s));
		printf("addr_of ee:01 (upper-case) -> %d %s\n", n, n ? s : "-");
	}
	printf("addr_of ee:03 (multicast only) -> %d\n", reaper_nd_addr_of(t, 6, "aa:bb:cc:dd:ee:03", a));
	printf("addr_of unknown -> %d\n", reaper_nd_addr_of(t, 6, "00:00:00:00:00:09", a));
	n = reaper_nd_load(live, 512);
	printf("load -> %d\n", n);
	printf("load null -> %d\n", reaper_nd_load(NULL, 10));
	return 0;
}
'''

tmp = tempfile.mkdtemp(prefix="rnd_")
try:
    shutil.copy(C, tmp)
    shutil.copy(H, tmp)
    open(os.path.join(tmp, "main.c"), "w").write(MAIN)
    exe = os.path.join(tmp, "t")
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe,
                        os.path.join(tmp, "reaper_nd.c"), os.path.join(tmp, "main.c")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        die("host compile failed:\n" + r.stderr)
    ok("shared/reaper_nd.c compiles on the host with -Wall -Wextra -Werror")
    out = subprocess.run([exe], capture_output=True, text=True, timeout=20).stdout
finally:
    shutil.rmtree(tmp, ignore_errors=True)

def want(pat, msg):
    if not re.search(pat, out, re.M):
        die(msg + "\n--- harness output ---\n" + out)
    ok(msg)

want(r"^global fe80=0 gua=1 ula=1 mcast=0 mapped=0 loop=0$", "classifier: GUA and ULA are global; link-local, multicast, v4-mapped and loopback are not")
want(r"^mac_of_str 2001:db8:1::10 -> 1 aa:bb:cc:dd:ee:01 br0$", "address -> MAC and bridge from the printed form")
want(r"^mac_of_str miss -> 0$", "an unknown address is a miss")
want(r"^mac_of_str v4 -> 0$", "an IPv4 string is a miss, never a false hit")
want(r"^mac_of fd00::20 -> 1 aa:bb:cc:dd:ee:02$", "binary address -> MAC")
want(r"^addr_of ee:01 \(upper-case\) -> 1 2001:db8:1::10$", "MAC -> its GLOBAL address, skipping the link-local entry, case-insensitive MAC")
want(r"^addr_of ee:03 \(multicast only\) -> 0$", "a MAC whose only entry is multicast has no usable address")
want(r"^addr_of unknown -> 0$", "an unknown MAC is a miss")
want(r"^load -> \d+$", "reaper_nd_load() against the host kernel returns a count without crashing")
want(r"^load null -> 0$", "reaper_nd_load() refuses a NULL table")
print("PASS test_reaper_nd")
