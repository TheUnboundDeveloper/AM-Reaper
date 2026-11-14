#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traffic Analyzer: an accelerated guest-network upload is not counted as the router's own traffic (2026-11-13).

WHY THIS EXISTS. Found reading rtrafd (owner asked to investigate and fix if simple). The flow-cache pass decided "LAN
client" by the main subnet only, so an accelerated upload from a guest network on its own subnet (brNN) landed in the
router's own bucket (its device is the WAN, no bridge) while the conntrack pass also filed it under brNN: counted
twice, inflating the Router row in Top Devices. A Guest Portal guest's flow (tun22 / tun23) would take the same branch.

WHAT IT DOES. Compiles the real REAPER-FCLAN block with a stubbed bridge table and checks: main subnet, a guest bridge
subnet and a portal tunnel subnet are LAN sources; an Internet address and the router's WAN-side are not. Pins the
bridge refresh (portal tunnels read into their own list, never into the bridge list, which would make portal guests
devices), the flow-cache LAN flag, and the portal branch of the "not the router's own" test.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "rtrafd", "rtrafd.c") if SRC else ""
if not SRC or not os.path.isfile(P):
    print("SKIP: no router tree with rtrafd/rtrafd.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
src = open(P, encoding="latin-1").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

check("exactly one REAPER-FCLAN block", src.count("/* REAPER-FCLAN-BEGIN") == 1)
check("the flow-cache LAN flag uses it (not the main subnet alone)",
      "fl[nfl].lan = fc_src_is_lan(fl[nfl].sip);" in src and "fl[nfl].lan = ((fl[nfl].sip & lan_mask) == lan_net);" not in src)
check("a flow towards a portal tunnel is not filed as the router's own",
      "} else if ((br[0] == 'b' && br[1] == 'r') || portal_is_tun(br) >= 0) {" in src)
b = re.search(r"\nstatic void brsub_refresh\(void\)\n\{.*?\n\}\n", src, re.S)
br = b.group(0) if b else ""
check("bridge refresh reads the portal tunnels into their own list and skips the bridge list for them",
      "nptsub = 0;" in br and "if (!pt && strncmp(buf[i].ifr_name, \"br\", 2) != 0) continue;" in br
      and br.find("if (pt) {") < br.find("strlcpy(brsub[nbrsub].br") and "\t\t\tcontinue;\n\t\t}" in br)

blk = re.search(r"/\* REAPER-FCLAN-BEGIN.*?\*/(.*?)/\* REAPER-FCLAN-END \*/", src, re.S)
CC = shutil.which("gcc") or shutil.which("cc")
if blk and CC:
    prog = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
static uint32_t lan_net = 0xC0A83200u, lan_mask = 0xFFFFFF00u;	/* 192.168.50.0/24 */
static struct { char br[16]; uint32_t net, mask; } brsub[4] = { { "br0", 0xC0A83200u, 0xFFFFFF00u }, { "br56", 0xC0A83500u, 0xFFFFFF00u } };
static int nbrsub = 2;
static struct { uint32_t net, mask; } ptsub[2] = { { 0xC0A83400u, 0xFFFFFF00u } };	/* tun22 192.168.52.0/24 */
static int nptsub = 1;
static const char *ip_bridge(uint32_t ip)
{ int i; for (i = 0; i < nbrsub; i++) if ((ip & brsub[i].mask) == brsub[i].net) return brsub[i].br; return NULL; }
''' + blk.group(1) + r'''
int main(void)
{
	printf("%d %d %d %d %d\n", fc_src_is_lan(0xC0A83261u), fc_src_is_lan(0xC0A83505u), fc_src_is_lan(0xC0A83405u),
	       fc_src_is_lan(0x08080808u), fc_src_is_lan(0x2FCB98BFu));
	nbrsub = 0; nptsub = 0;
	printf("%d %d\n", fc_src_is_lan(0xC0A83261u), fc_src_is_lan(0xC0A83505u));
	return 0;
}
'''
    tmp = tempfile.mkdtemp()
    try:
        c, exe = os.path.join(tmp, "t.c"), os.path.join(tmp, "t")
        open(c, "w").write(prog)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("the block compiles clean", r.returncode == 0, r.stderr[-500:])
        if r.returncode == 0:
            o = subprocess.run([exe], capture_output=True, text=True).stdout.splitlines()
            check("LAN sources: main subnet, a guest bridge subnet, a portal tunnel subnet; not an Internet or WAN address",
                  o[0] == "1 1 1 0 0", o)
            check("with no other networks the main subnet still counts (unchanged for single-LAN routers)", o[1] == "1 0", o)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
elif not blk:
    check("REAPER-FCLAN block present", False)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
