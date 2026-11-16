#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest isolation: guests reach only the WAN or their VPN client, the router only for DHCP/DNS/portal (2026-11-12).

WHY THIS EXISTS. Owner hard rule: a guest - every device on a Guest Portal network, and on any guest network whose
"Access Intranet" does not name the Main Network - must never see or reach non-guest devices or router features, on any path, including the
WAN fallback while its VPN client is down. Stock left it open (router services on every router address but
lan_ipaddr; signed-in portal guests accepted to anywhere via `-I FORWARD -i tun22 NEW ACCEPT`; new connections in
from a bound VPN client; a portal's IPv6 past the portal), and the Kill Switch did not hold for a portal network.

WHAT IT DOES. Compiles the REAPER-GUEST-PURE block of rc/reaper_guest.c on the host and generates the apply script
for sample network sets; checks the exact rules (a plain guest network, a Free Wi-Fi portal with its bridge, an
account portal, a VPN-bound network with the Kill Switch off and on, two WANs, no IPv6 WAN), that the layer never
ACCEPTs, the tear-down when no guest network is left, the vpnc_idx parser, and what an Access Intranet pair means
(2026-11-16: main-network access only from a pair with the Main Network; two guest networks paired = forwarding
between those two only, both still isolated). Then pins the
wiring: hook.sh, the firewall tail, the sdn / sdn_del handlers, the build, and (where the Network page has a Kill
Switch) the default-on for a new VPN binding. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree - argv[1]
or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
GC = os.path.join(SRC, "rc", "reaper_guest.c") if SRC else ""
if not GC or not os.path.isfile(GC):
    skip("no router tree with rc/reaper_guest.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

gsrc = read("rc/reaper_guest.c")
m = re.search(r"/\* REAPER-GUEST-PURE-BEGIN.*?\*/(.*?)/\* REAPER-GUEST-PURE-END \*/", gsrc, re.S)
check("reaper_guest.c carries the REAPER-GUEST-PURE block", m is not None)
if not m:
    print("\n1 check failed"); sys.exit(1)

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <net/if.h>
#define REAPER_AIMESH_SET "reaper_aimesh"
#define REAPER_HOOK_IN "REAPER_HOOK"
#define REAPER_HOOK_FWD "REAPER_HOOK_F"
@@PURE@@
static size_t rg_test_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
#define strlcpy rg_test_strlcpy
static void srv_fill(struct rg_net *g, int n)
{
	int k, u;
@@SRV@@
}
/* 2026-11-16 (bug review A1): the enabled networks of the pair cases (40, 41) */
static const struct rg_ref RT[] = {
	{ 0, "br0", "br0", 0 },		/* the Main Network */
	{ 0, "br0", "br0", 0 },		/* the AiMesh backhaul shares index 0 */
	{ 3, "br54", "br54", 0 },	/* guest A */
	{ 12, "br57", "br57", 0 },	/* guest B */
	{ 5, "br56", "br56", 0 },	/* guest C */
	{ 4, "tun22", "br55", 1 },	/* a Guest Portal */
	{ 9, "br0", "br0", 0 },		/* a network riding the LAN bridge */
};					/* index 8 names no enabled network */
#define NRT ((int)(sizeof(RT) / sizeof(RT[0])))
int main(int argc, char **argv)
{
	struct rg_net g[4]; char wan4[2][IFNAMSIZ] = { "eth0", "ppp0" }; char out[16];
	int s = atoi(argv[1]), n = 0, nw4 = 1; const char *wan6 = "eth0";
	memset(g, 0, sizeof(g));
	switch (s) {
	case 1: /* plain guest network */
		g[0].sdn_idx = 5; strcpy(g[0].ifname, "br56"); strcpy(g[0].brname, "br56"); strcpy(g[0].subnet, "192.168.53.0/24"); n = 1; break;
	case 2: /* Free Wi-Fi portal */
		g[0].sdn_idx = 4; strcpy(g[0].ifname, "tun22"); strcpy(g[0].brname, "br55"); strcpy(g[0].subnet, "192.168.52.0/24"); g[0].portal = 1; n = 1; break;
	case 3: /* account portal */
		g[0].sdn_idx = 6; strcpy(g[0].ifname, "tun23"); strcpy(g[0].brname, "br57"); g[0].portal = 2; n = 1; break;
	case 4: /* VPN-bound guest network, kill switch off, two WANs, no IPv6 WAN */
		g[0].sdn_idx = 7; strcpy(g[0].ifname, "br58"); strcpy(g[0].brname, "br58"); strcpy(g[0].vpnif, "wgc5"); n = 1; nw4 = 2; wan6 = ""; break;
	case 5: /* VPN-bound portal, kill switch on */
		g[0].sdn_idx = 4; strcpy(g[0].ifname, "tun22"); strcpy(g[0].brname, "br55"); g[0].portal = 1; strcpy(g[0].vpnif, "tun12"); g[0].killsw = 1; n = 1; break;
	case 6: /* nothing to guard */
		n = 0; break;
	case 8: /* 2026-11-13: Free Wi-Fi portal with Access Intranet on */
		g[0].sdn_idx = 4; strcpy(g[0].ifname, "tun22"); strcpy(g[0].brname, "br55"); g[0].portal = 1;
		g[0].lan_ok = 1; strcpy(g[0].lanif, "br0"); n = 1; break;
	case 9: /* 2026-11-13: plain guest network flagged lan_ok by mistake - only a portal may use it */
		g[0].sdn_idx = 5; strcpy(g[0].ifname, "br56"); strcpy(g[0].brname, "br56"); g[0].lan_ok = 1; strcpy(g[0].lanif, "br0"); n = 1; break;
	case 10: /* 2026-11-14: plain guest network, the router's own VPN servers named */
		g[0].sdn_idx = 5; strcpy(g[0].ifname, "br56"); strcpy(g[0].brname, "br56");
		strcpy(g[0].srvif[0], "wgs1"); strcpy(g[0].srvif[1], "tun21"); g[0].nsrv = 2; n = 1; break;
	case 11: /* 2026-11-14: a portal handed a server list by mistake - nothing opens into a portal */
		g[0].sdn_idx = 4; strcpy(g[0].ifname, "tun22"); strcpy(g[0].brname, "br55"); g[0].portal = 1;
		strcpy(g[0].srvif[0], "wgs1"); g[0].nsrv = 1; n = 1; break;
	case 12: /* 2026-11-14: VPN-bound guest network, kill switch ON, server list - the kill switch holds */
		g[0].sdn_idx = 7; strcpy(g[0].ifname, "br58"); strcpy(g[0].brname, "br58"); strcpy(g[0].vpnif, "wgc5"); g[0].killsw = 1;
		strcpy(g[0].srvif[0], "wgs1"); g[0].nsrv = 1; n = 1; break;
	case 13: /* 2026-11-14: VPN-bound guest network, kill switch off, server list */
		g[0].sdn_idx = 7; strcpy(g[0].ifname, "br58"); strcpy(g[0].brname, "br58"); strcpy(g[0].vpnif, "wgc5");
		strcpy(g[0].srvif[0], "wgs1"); g[0].nsrv = 1; n = 1; break;
	case 20: { /* 2026-11-14: the server list as rc builds it - a plain network, a portal on tun22, another plain one */
		int i, j;
		strcpy(g[0].ifname, "br56"); strcpy(g[0].brname, "br56");
		strcpy(g[1].ifname, "tun22"); strcpy(g[1].brname, "br55"); g[1].portal = 1;
		strcpy(g[2].ifname, "br58"); strcpy(g[2].brname, "br58");
		srv_fill(g, 3);
		for (i = 0; i < 3; i++) { printf("%s:", g[i].ifname); for (j = 0; j < g[i].nsrv; j++) printf("%s,", g[i].srvif[j]); printf(" "); }
		memset(g, 0, sizeof(g)); strcpy(g[0].ifname, "br56"); strcpy(g[0].brname, "br56"); srv_fill(g, 1);
		printf("| %s:", g[0].ifname); for (j = 0; j < g[0].nsrv; j++) printf("%s,", g[0].srvif[j]); printf("\n");
		return 0; }
	case 30: case 31: case 32: case 35: { /* 2026-11-15: VPN Director list argv[2], vpn_client1..5_rgw argv[3] "a,b,c,d,e" */
		int rgw[5] = { 0, 0, 0, 0, 0 }, i;
		if (argc > 3) sscanf(argv[3], "%d,%d,%d,%d,%d", &rgw[0], &rgw[1], &rgw[2], &rgw[3], &rgw[4]);
		/* the reporter's two VLANs: br54 192.168.54.0/24, br55 192.168.53.0/24 */
		g[0].sdn_idx = 3; strcpy(g[0].ifname, "br54"); strcpy(g[0].brname, "br54"); strcpy(g[0].subnet, "192.168.54.0/24");
		g[1].sdn_idx = 4; strcpy(g[1].ifname, "br55"); strcpy(g[1].brname, "br55"); strcpy(g[1].subnet, "192.168.53.0/24");
		n = 2;
		if (s == 31) { strcpy(g[0].vpnif, "wgc5"); g[0].killsw = 1; strcpy(g[1].vpnif, "tun12"); }	/* kill switch on / off */
		if (s == 32) { strcpy(g[0].ifname, "tun22"); g[0].portal = 1; n = 1; }	/* a portal on br54 */
		if (s == 35) { g[0].subnet[0] = 0; n = 1; }	/* no IPv4 subnet known */
		for (i = 0; i < n; i++) rg_policy_vpn(&g[i], argc > 2 ? argv[2] : "", rgw);
		if (argc > 4) { /* print the exits instead */
			for (i = 0; i < n; i++) { int k; printf("%s:", g[i].ifname); for (k = 0; k < g[i].npr; k++) printf("%s|%s|%s,", g[i].pr[k].ifname, g[i].pr[k].src, g[i].pr[k].dst); printf(" "); }
			printf("\n"); return 0;
		}
		break; }
	case 34: { /* rg_cidr4 */
		const char *t[] = { "192.168.54.0/24", "10.0.0.1", "0.0.0.0/0", "1.2.3.4/33", "1.2.3.4.5", "1.2.3", "256.1.1.1", "1.2.3.4/", "1.2.3.4/24/1", "a.b.c.d", "", "1.2.3.4/-1", "255.255.255.255/32" };
		unsigned int a; int p, i;
		for (i = 0; i < 13; i++) { a = 0; p = -1; printf("%d", rg_cidr4(t[i], &a, &p)); if (i == 0) printf(":%08x/%d", a, p); printf(" "); }
		printf("\n"); return 0; }
	case 40: { /* 2026-11-16: rg_main_access and rg_peers of network argv[3] under the pair list argv[2] */
		char pe[RG_PEER_MAX][IFNAMSIZ]; int i, idx = atoi(argv[3]), np;
		np = rg_peers(argv[2], idx, RT, NRT, "br0", pe, RG_PEER_MAX);
		printf("%d:", rg_main_access(argv[2], idx, RT, NRT, "br0"));
		for (i = 0; i < np; i++) printf("%s,", pe[i]);
		printf("\n"); return 0; }
	case 41: { /* 2026-11-16: the network set as reaper_guest_gen builds it from RT and the pair list argv[2];
		    * argv[3] "ks" = network 3 bound to WireGuard client 5 with the kill switch on */
		int i;
		for (i = 0; i < NRT && n < 4; i++) {
			const struct rg_ref *r = &RT[i];
			if (r->idx == 0 || !strcmp(r->br, "br0")) continue;
			if (!r->portal && rg_main_access(argv[2], r->idx, RT, NRT, "br0")) continue;
			g[n].sdn_idx = r->idx; strcpy(g[n].ifname, r->ifname); strcpy(g[n].brname, r->br); g[n].portal = r->portal;
			if (r->portal && rg_main_access(argv[2], r->idx, RT, NRT, "br0")) { g[n].lan_ok = 1; strcpy(g[n].lanif, "br0"); }
			g[n].npeer = rg_peers(argv[2], r->idx, RT, NRT, "br0", g[n].peer, RG_PEER_MAX);
			if (argc > 3 && !strcmp(argv[3], "ks") && r->idx == 3) { strcpy(g[n].vpnif, "wgc5"); g[n].killsw = 1; }
			n++;
		}
		break; }
	case 42: /* 2026-11-16: a portal handed a peer list by mistake - a portal has no peers */
		g[0].sdn_idx = 4; strcpy(g[0].ifname, "tun22"); strcpy(g[0].brname, "br55"); strcpy(g[0].subnet, "192.168.52.0/24"); g[0].portal = 1;
		strcpy(g[0].peer[0], "br54"); g[0].npeer = 1; n = 1; break;
	case 7: /* parsers */
		rg_vpnif(5, out, sizeof(out)); printf("%s ", out); rg_vpnif(6, out, sizeof(out)); printf("%s ", out);
		rg_vpnif(10, out, sizeof(out)); printf("%s ", out); rg_vpnif(0, out, sizeof(out)); printf("[%s] ", out);
		rg_vpnif(11, out, sizeof(out)); printf("[%s]\n", out);
		return 0;
	}
	rg_write(stdout, g, n, wan4, nw4, wan6, "HOOK_RUN\n");
	return 0;
}
'''
tmp = tempfile.mkdtemp()
try:
    c = os.path.join(tmp, "g.c"); exe = os.path.join(tmp, "g")
    msrv = re.search(r"/\* REAPER-GUEST-SRV-BEGIN[^\n]*\*/\n(.*?)\t/\* REAPER-GUEST-SRV-END \*/", gsrc, re.S)
    check("reaper_guest.c carries the REAPER-GUEST-SRV block (the VPN server list, run here as rc runs it)", msrv is not None)
    open(c, "w").write(HARNESS.replace("@@PURE@@", m.group(1)).replace("@@SRV@@", msrv.group(1) if msrv else ""))
    r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    check("the block compiles with -Wall -Werror", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n%d check(s) failed" % len(fails)); sys.exit(1)
    def gen(s, *a):
        return subprocess.run([exe, str(s)] + list(a), capture_output=True, text=True).stdout
    def rules(txt, fam=None):
        # 2026-11-15: the ten Policy Routing mark exits every plain guest network carries are checked on their own
        # (below); the exact-list checks of the earlier rules read the chain without them
        L = [l for l in txt.splitlines() if l.startswith("R ") and " -m mark --mark " not in l]
        # filter-table rules only; the nat DNS redirect (2026-11-13) is read through nat() below
        if fam == 4: L = [l for l in L if l.startswith("R iptables ") and not l.startswith("R iptables -t nat ")]
        if fam == 6: L = [l for l in L if l.startswith("R ip6tables ")]
        return L
    def nat(txt):
        return [l for l in txt.splitlines() if l.startswith("R iptables -t nat ")]

    p = gen(7).split()
    check("vpnc_idx -> interface: 1..5 wgcN, 6..10 tun1N, anything else none", p == ["wgc5", "tun11", "tun15", "[]", "[]"], p)

    # ---- 2026-11-16 (bug review A1, owner-approved): what an Access Intranet pair means ----
    # sdn_access_rl is "<a>b" pairs of network indexes; a pair is two-way forwarding between exactly those two networks
    # and index 0 is the Main Network. Until this fix "named in any pair" was read as "has intranet access", so two
    # guest networks paired with each other both left the layer and a portal named in any pair got the main-LAN route.
    # The networks of these cases (RT): 0 main (br0), 3 guest br54, 12 guest br57, 5 guest br56, 4 portal tun22 on
    # br55, 9 a network riding br0; 8 names no enabled network.
    def pr(rl, idx):
        return gen(40, rl, str(idx)).strip()
    check("two guest networks paired (<12>3): neither has main-network access; each is the other's peer",
          pr("<12>3", 12) == "0:br54," and pr("<12>3", 3) == "0:br57," and pr("<3>12", 3) == "0:br57,",
          (pr("<12>3", 12), pr("<12>3", 3), pr("<3>12", 3)))
    check("a pair with the Main Network, either way round (<0>5, <5>0): main-network access, no peers; others none",
          pr("<0>5", 5) == "1:" and pr("<5>0", 5) == "1:" and pr("<0>5<0>12", 12) == "1:" and pr("<0>5<0>12", 3) == "0:"
          and pr("", 5) == "0:", (pr("<0>5", 5), pr("<5>0", 5), pr("<0>5<0>12", 12), pr("<0>5<0>12", 3)))
    check("a network on the LAN bridge as the other end (<9>5, <5>9) is the main network too",
          pr("<9>5", 5) == "1:" and pr("<5>9", 5) == "1:", (pr("<9>5", 5), pr("<5>9", 5)))
    check("a pair end that names no enabled network (<8>5) is ignored; the rest of the list still counts",
          pr("<8>5", 5) == "0:" and pr("<5>8", 5) == "0:" and pr("<8>5<5>3", 5) == "0:br54," and pr("<8>5<0>5", 5) == "1:",
          (pr("<8>5", 5), pr("<8>5<5>3", 5), pr("<8>5<0>5", 5)))
    check("a portal has no peers and is nobody's peer; without the Main Network in its pair it has no main-network access",
          pr("<4>3", 4) == "0:" and pr("<4>3", 3) == "0:" and pr("<3>4", 4) == "0:" and pr("<0>4", 4) == "1:",
          (pr("<4>3", 4), pr("<4>3", 3), pr("<0>4", 4)))
    check("a network with main-network access is not a peer (it holds non-guest devices)",
          pr("<0>12<12>3", 3) == "0:" and pr("<0>12<12>3", 12) == "1:" and pr("<9>12<3>12", 3) == "0:",
          (pr("<0>12<12>3", 3), pr("<0>12<12>3", 12), pr("<9>12<3>12", 3)))
    check("several pairs: each isolated guest end is a peer once; a doubled pair, a self pair or a broken record adds nothing",
          pr("<12>3<3>5", 3) == "0:br57,br56," and pr("<12>3<3>12<3>3", 3) == "0:br57," and pr("<3>", 3) == "0:"
          and pr("junk<x>y<12>3", 3) == "0:br57," and pr("<12>3", 5) == "0:",
          (pr("<12>3<3>5", 3), pr("<12>3<3>12<3>3", 3), pr("junk<x>y<12>3", 3)))

    t1 = gen(1)		# a plain guest network (br56), the reference for "isolated as any guest network"
    tp = gen(41, "<12>3"); r4 = rules(tp, 4); r6 = rules(tp, 6)
    check("<12>3: both paired networks stay in the layer, with the third guest network and the portal",
          all(("# network %d: %s" % x) in tp for x in ((3, "br54"), (12, "br57"), (5, "br56"), (4, "tun22"))), tp[:400])
    for X, P in (("br54", "br57"), ("br57", "br54")):
        for fam, rr in (("iptables", r4), ("ip6tables", r6)):
            o_ = "R %s -A REAPER_GUF -i %s -o %s -j RETURN" % (fam, X, P)
            i_ = "R %s -A REAPER_GUF -o %s -i %s -j RETURN" % (fam, X, P)
            check("<12>3 %s (%s): out to the paired network before the network's DROP, in from it before the inbound DROP" % (X, fam),
                  rr.count(o_) == 1 and rr.count(i_) == 1
                  and rr.index(o_) < rr.index("R %s -A REAPER_GUF -i %s -j DROP" % (fam, X))
                  < rr.index(i_) < rr.index("R %s -A REAPER_GUF -o %s -j DROP" % (fam, X)), rr)
    check("<12>3: both stay closed to the router - REAPER_GUI exactly as for any guest network, v4 and v6",
          all([l for l in rules(tp, f_) if ("REAPER_GUI -i %s " % X) in l] == [l.replace("br56", X) for l in rules(t1, f_) if "REAPER_GUI" in l]
              for X in ("br54", "br57") for f_ in (4, 6)), [l for l in r4 if "REAPER_GUI -i br54 " in l])
    check("<12>3: both stay closed to the main LAN and to every other network - the pair is the only new way",
          "br0" not in tp and not [l for l in rules(tp) if "br54" in l and ("br56" in l or "br55" in l or "tun22" in l)]
          and [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i br54 -o")] ==
          ["R iptables -A REAPER_GUF -i br54 -o br54 -j RETURN", "R iptables -A REAPER_GUF -i br54 -o eth0 -j RETURN",
           "R iptables -A REAPER_GUF -i br54 -o br57 -j RETURN"], [l for l in r4 if "br54" in l])
    check("<12>3: without the pair rules the two networks' chains are exactly a plain guest network's (set 1)",
          all([l for l in rules(tp) if X in l and P not in l] == [l.replace("br56", X) for l in rules(t1) if "br56" in l]
              for X, P in (("br54", "br57"), ("br57", "br54"))))
    check("<12>3: a guest network that is not part of the pair is unchanged by it",
          [l for l in rules(tp) if "br56" in l] == [l for l in rules(t1) if "br56" in l])
    check("<12>3: the script names the pair on each network's line",
          "# network 3: br54\n#   paired with br57 (Access Intranet): devices of these networks reach each other; the router and the main network stay closed\n" in tp
          and "# network 12: br57\n#   paired with br54 (Access Intranet)" in tp and tp.count("#   paired with") == 2, tp[:700])
    for rl in ("<0>5", "<5>0", "<9>5"):
        t = gen(41, rl)
        check("%s: the network with main-network access is out of the layer (as before the fix); the others stay isolated" % rl,
              "br56" not in t and "# network 3: br54" in t and "# network 12: br57" in t and "# network 4: tun22" in t
              and "paired with" not in t and "br0" not in t, t[:400])
    t = gen(41, "<8>5")
    check("<8>5 (8 is not there): ignored - network 5 stays isolated with a plain guest network's rules",
          [l for l in rules(t) if "br56" in l] == [l for l in rules(t1) if "br56" in l] and "paired with" not in t)
    t = gen(41, "<4>3")
    check("a portal paired with a guest network, Main Network not ticked: no main-LAN route (the fix), no pair rule either way",
          "br0" not in t and "paired with" not in t
          and not [l for l in rules(t) if "br54" in l and ("tun22" in l or "br55" in l)]
          and [l for l in rules(t) if "tun22" in l or " br55 " in l] == [l for l in rules(gen(8)) if ("tun22" in l or " br55 " in l) and " -o br0 " not in l],
          [l for l in rules(t) if "tun22" in l])
    t = gen(41, "<0>4")
    check("a portal with Main Network ticked (<0>4) keeps its main-LAN route, exactly as before",
          "R iptables -A REAPER_GUF -i tun22 -o br0 -j RETURN" in rules(t, 4)
          and [l for l in rules(t) if "tun22" in l or " br55 " in l] == [l for l in rules(gen(8)) if "tun22" in l or " br55 " in l]
          and "paired with" not in t, [l for l in rules(t) if "tun22" in l])
    t = gen(41, "<0>12<12>3")
    check("paired with a network that has main-network access: that network is out of the layer and is not a peer - the guest stays closed to it",
          "br57" not in t and "paired with" not in t
          and [l for l in rules(t) if "br54" in l] == [l.replace("br56", "br54") for l in rules(t1) if "br56" in l], [l for l in rules(t) if "br54" in l])
    tk = gen(41, "<12>3", "ks"); r4 = rules(tk, 4); r6 = rules(tk, 6)
    check("kill switch on (br54 bound to wgc5): the pair rules stay, both ways and both families; the WAN stays closed",
          "R iptables -A REAPER_GUF -o br54 -i br57 -j RETURN" in r4 and "R ip6tables -A REAPER_GUF -i br54 -o br57 -j RETURN" in r6
          and "R ip6tables -A REAPER_GUF -o br54 -i br57 -j RETURN" in r6
          and [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i br54 -o")] ==
          ["R iptables -A REAPER_GUF -i br54 -o br54 -j RETURN", "R iptables -A REAPER_GUF -i br54 -o wgc5 -j RETURN",
           "R iptables -A REAPER_GUF -i br54 -o br57 -j RETURN"]
          and "-o br54 -i eth0" not in tk and "-i br54 -o eth0" not in tk
          and "# network 3: br54 - VPN client, kill switch on\n#   paired with br57 (Access Intranet)" in tk
          and "R iptables -A REAPER_GUF -i br57 -o br54 -j RETURN" in r4, [l for l in r4 if "br54" in l])
    t42 = gen(42)
    check("a portal handed a peer list by mistake gets no pair rule and no pair line (rg_iface, rg_write)",
          "br54" not in t42 and rules(t42) == rules(gen(2)))
    for rl in ("<12>3", "<0>5", "<9>5", "<8>5", "<4>3", "<0>4", "<0>12<12>3", "<12>3<3>5<4>5"):
        t = gen(41, rl)
        check("pair list %s: the layer never ACCEPTs (RETURN or DROP only)" % rl, " -j ACCEPT" not in t and rules(t), t[:200])
    if shutil.which("sh"):
        sc = os.path.join(tmp, "pair.sh"); open(sc, "w").write(tk)
        r = subprocess.run(["sh", "-n", sc], capture_output=True, text=True)
        check("the generated script with pair rules parses (sh -n)", r.returncode == 0, r.stderr)
        bb = shutil.which("busybox")
        if bb:
            r = subprocess.run([bb, "ash", "-n", sc], capture_output=True, text=True)
            check("the generated script with pair rules parses (busybox ash -n)", r.returncode == 0, r.stderr)

    for s in (1, 2, 3, 4, 5):
        t = gen(s)
        check("set %d: the layer never ACCEPTs (deny-only: RETURN or DROP)" % s, " -j ACCEPT" not in t and rules(t), t[:300])

    t1 = gen(1); r4 = rules(t1, 4); r6 = rules(t1, 6)
    check("guest network, to the router (v4): AiMesh, established/DNAT'd flows, DHCP, DNS to its own gateway only, then DROP",
          r4[:6] == ["R iptables -A REAPER_GUI -i br56 -m set --match-set reaper_aimesh src -j RETURN",
                     "R iptables -A REAPER_GUI -i br56 -m conntrack --ctstate RELATED,ESTABLISHED,DNAT -j RETURN",
                     "R iptables -A REAPER_GUI -i br56 -p udp --dport 67 -j RETURN",
                     "R iptables -A REAPER_GUI -i br56 -p udp --dport 53 -m addrtype --dst-type LOCAL --limit-iface-in -j RETURN",
                     "R iptables -A REAPER_GUI -i br56 -p tcp --dport 53 -m addrtype --dst-type LOCAL --limit-iface-in -j RETURN",
                     "R iptables -A REAPER_GUI -i br56 -j DROP"], r4[:6])
    check("guest network, through the router (v4): its own bridge, AiMesh, the WAN - nothing else out; established and port forwards in",
          r4[6:] == ["R iptables -A REAPER_GUF -i br56 -o br56 -j RETURN",
                     "R iptables -A REAPER_GUF -i br56 -m set --match-set reaper_aimesh src -j RETURN",
                     "R iptables -A REAPER_GUF -i br56 -p udp --dport 53 -m conntrack --ctstate DNAT -j RETURN",
                     "R iptables -A REAPER_GUF -i br56 -p tcp --dport 53 -m conntrack --ctstate DNAT -j RETURN",
                     "R iptables -A REAPER_GUF -i br56 -o eth0 -j RETURN",
                     "R iptables -A REAPER_GUF -i br56 -j DROP",
                     "R iptables -A REAPER_GUF -o br56 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN",
                     "R iptables -A REAPER_GUF -o br56 -i eth0 -j RETURN",
                     "R iptables -A REAPER_GUF -o br56 -j DROP"], r4[6:])
    check("guest network, IPv6: neighbour discovery / MLD and DHCPv6 kept, DNS only to its own addresses, out by the IPv6 WAN only",
          all(("--icmpv6-type %d -j RETURN" % k) in "\n".join(r6) for k in (133, 134, 135, 136, 130, 131, 132, 143))
          and "R ip6tables -A REAPER_GUI -i br56 -p udp --dport 547 -j RETURN" in r6
          and "R ip6tables -A REAPER_GUI -i br56 -p udp --dport 53 -m addrtype --dst-type LOCAL --limit-iface-in -j RETURN" in r6
          and "R ip6tables -A REAPER_GUF -i br56 -o eth0 -j RETURN" in r6 and r6[-1] == "R ip6tables -A REAPER_GUF -o br56 -j DROP", r6)
    check("the flows of the guest subnet are flushed after the rules, and the front chains re-pinned",
          "conntrack -D -s 192.168.53.0/24 >/dev/null 2>&1; conntrack -D -d 192.168.53.0/24 >/dev/null 2>&1" in t1
          and t1.index("HOOK_RUN") < t1.index("conntrack -D") and "fc flush" in t1)

    t2 = gen(2); r4 = rules(t2, 4); r6 = rules(t2, 6)
    check("portal: its sign-in ports (3990, 3991, 8083) on its own gateway, then DROP - on tun22",
          "R iptables -A REAPER_GUI -i tun22 -p tcp -m multiport --dports 3990,3991,8083 -m addrtype --dst-type LOCAL --limit-iface-in -j RETURN" in r4
          and r4.index("R iptables -A REAPER_GUI -i tun22 -j DROP") > r4.index("R iptables -A REAPER_GUI -i tun22 -p tcp -m multiport --dports 3990,3991,8083 -m addrtype --dst-type LOCAL --limit-iface-in -j RETURN"))
    check("portal: a signed-in guest goes out by the WAN only - not to the main LAN or other networks (the stock tun22 ACCEPT hole)",
          "R iptables -A REAPER_GUF -i tun22 -o eth0 -j RETURN" in r4 and "R iptables -A REAPER_GUF -i tun22 -j DROP" in r4
          and not [l for l in r4 if "-i tun22 -o br" in l])
    br55 = [l for l in r4 if " br55 " in l]
    check("portal bridge (v4): no DHCP / DNS / portal ports for the kernel (chilli reads it raw), nothing forwarded",
          br55 == ["R iptables -A REAPER_GUI -i br55 -m set --match-set reaper_aimesh src -j RETURN",
                   "R iptables -A REAPER_GUI -i br55 -m conntrack --ctstate RELATED,ESTABLISHED,DNAT -j RETURN",
                   "R iptables -A REAPER_GUI -i br55 -j DROP",
                   "R iptables -A REAPER_GUF -i br55 -j DROP",
                   "R iptables -A REAPER_GUF -o br55 -j DROP"], br55)
    check("portal IPv6 gets nothing (chilli is IPv4-only): neighbour discovery to the router, no DHCPv6, no DNS, no forwarding",
          not [l for l in r6 if "--dport" in l or "-j RETURN" in l and "REAPER_GUF" in l]
          and "R ip6tables -A REAPER_GUF -i br55 -j DROP" in r6 and "R ip6tables -A REAPER_GUF -i tun22 -j DROP" in r6
          and "R ip6tables -A REAPER_GUI -i br55 -p ipv6-icmp --icmpv6-type 135 -j RETURN" in r6, r6)

    t3 = gen(3)
    check("account portal: chilli-cp's ports (3998, 3991, 8083) on tun23",
          "R iptables -A REAPER_GUI -i tun23 -p tcp -m multiport --dports 3998,3991,8083 -m addrtype --dst-type LOCAL --limit-iface-in -j RETURN" in rules(t3, 4))

    t4 = gen(4); r4 = rules(t4, 4); r6 = rules(t4, 6)
    check("VPN-bound, kill switch off: out by the VPN client OR either WAN (fallback) - nothing else",
          [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i br58 -o")] ==
          ["R iptables -A REAPER_GUF -i br58 -o br58 -j RETURN", "R iptables -A REAPER_GUF -i br58 -o wgc5 -j RETURN",
           "R iptables -A REAPER_GUF -i br58 -o eth0 -j RETURN", "R iptables -A REAPER_GUF -i br58 -o ppp0 -j RETURN"], r4)
    check("VPN-bound: no NEW connection in from the VPN client (the WGCF hole) - only established and WAN port forwards",
          "R iptables -A REAPER_GUF -o br58 -i wgc5 -j RETURN" not in r4 and "R iptables -A REAPER_GUF -o br58 -i eth0 -j RETURN" in r4)
    check("no IPv6 WAN: IPv6 out by the VPN client only", [l for l in r6 if " -o " in l and l.startswith("R ip6tables -A REAPER_GUF -i br58")] ==
          ["R ip6tables -A REAPER_GUF -i br58 -o br58 -j RETURN", "R ip6tables -A REAPER_GUF -i br58 -o wgc5 -j RETURN"], r6)

    t5 = gen(5); r4 = rules(t5, 4)
    check("kill switch on (a portal bound to OpenVPN client 2): out by the VPN client ONLY - the WAN fallback is closed, for the portal too",
          [l for l in r4 if "REAPER_GUF -i tun22" in l] ==
          ["R iptables -A REAPER_GUF -i tun22 -o tun22 -j RETURN",
           "R iptables -A REAPER_GUF -i tun22 -m set --match-set reaper_aimesh src -j RETURN",
           "R iptables -A REAPER_GUF -i tun22 -p tcp --dport 853 -j DROP",
           "R iptables -A REAPER_GUF -i tun22 -p udp --dport 853 -j DROP",
           "R iptables -A REAPER_GUF -i tun22 -o tun12 -j RETURN", "R iptables -A REAPER_GUF -i tun22 -j DROP"]
          and not [l for l in r4 if "-o tun22 -i eth0" in l], r4)

    # 2026-11-13 (owner): a portal guest's DNS is the guest resolver's; Access Intranet on a portal = the main LAN only
    t2 = gen(2); r4 = rules(t2, 4)
    check("portal: every port-53 query is redirected to the guest resolver on the tunnel it arrived on (UDP and TCP)",
          nat(t2) == ["R iptables -t nat -I PREROUTING 1 -j REAPER_GUN",
                      "R iptables -t nat -A REAPER_GUN -i tun22 -p udp --dport 53 -j REDIRECT --to-ports 53",
                      "R iptables -t nat -A REAPER_GUN -i tun22 -p tcp --dport 53 -j REDIRECT --to-ports 53"], nat(t2))
    check("...through a chain hooked first in nat PREROUTING, re-hooked (not doubled) on every apply",
          "iptables -t nat -N REAPER_GUN 2>/dev/null; iptables -t nat -F REAPER_GUN" in t2
          and t2.index("iptables -t nat -D PREROUTING -j REAPER_GUN") < t2.index("R iptables -t nat -I PREROUTING 1 -j REAPER_GUN")
          and t2.index("R iptables -t nat -I PREROUTING 1 -j REAPER_GUN") < t2.index("REAPER_GUN -i tun22"), t2[:600])
    check("portal: DNS over TLS / QUIC (853) is dropped before anything is let out",
          r4.index("R iptables -A REAPER_GUF -i tun22 -p tcp --dport 853 -j DROP") < r4.index("R iptables -A REAPER_GUF -i tun22 -o eth0 -j RETURN")
          and "R iptables -A REAPER_GUF -i tun22 -p udp --dport 853 -j DROP" in r4)
    check("plain guest networks: no redirect, no 853 drop (DNS Director's own DNSFILTER covers bridges)",
          "REAPER_GUN -i" not in t1 and "--dport 853" not in t1 and nat(t1) == ["R iptables -t nat -I PREROUTING 1 -j REAPER_GUN"])
    t8 = gen(8); r4 = rules(t8, 4); r6 = rules(t8, 6)
    check("portal + Access Intranet: out to the main LAN (br0) as well as the WAN, after the 853 drop",
          [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i tun22 -o")] ==
          ["R iptables -A REAPER_GUF -i tun22 -o tun22 -j RETURN", "R iptables -A REAPER_GUF -i tun22 -o eth0 -j RETURN",
           "R iptables -A REAPER_GUF -i tun22 -o br0 -j RETURN"], r4)
    check("...still nothing to the router beyond DHCP / DNS / the portal's ports (REAPER_GUI unchanged)",
          [l for l in r4 if "REAPER_GUI -i tun22" in l] == [l for l in rules(t2, 4) if "REAPER_GUI -i tun22" in l])
    check("...nothing opens from the main LAN into the portal (only replies and WAN port forwards)",
          "R iptables -A REAPER_GUF -o tun22 -i br0 -j RETURN" not in r4
          and "R iptables -A REAPER_GUF -o tun22 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN" in r4)
    check("...no other guest network, no IPv6 path, and the portal's bridge stays closed",
          not [l for l in r4 if "-i tun22 -o br5" in l] and not [l for l in r6 if "-j RETURN" in l and "REAPER_GUF" in l]
          and [l for l in r4 if " br55 " in l] == [l for l in rules(t2, 4) if " br55 " in l])
    t9 = gen(9)
    check("Access Intranet route is for portals only (a plain guest network flagged lan_ok gets no br0 path here)",
          "-i br56 -o br0" not in t9)

    # ---- 2026-11-14 (field report, GT-BE98 v3.7.7): WireGuard server clients lost a Guest Network Pro VLAN ----
    # Until v3.7.7 a client of the router's own VPN server reached such a network through the stock WGSF / OVPNSF
    # chains; REAPER_GUF dropped it first (new connections in from the WAN only, replies out to the WAN only).
    t10 = gen(10); r4 = rules(t10, 4); r6 = rules(t10, 6)
    check("VPN servers (v4): their clients' new connections go on to the stock rules; the network may only ANSWER them",
          [l for l in r4 if "REAPER_GUF" in l] ==
          ["R iptables -A REAPER_GUF -i br56 -o br56 -j RETURN",
           "R iptables -A REAPER_GUF -i br56 -m set --match-set reaper_aimesh src -j RETURN",
           "R iptables -A REAPER_GUF -i br56 -p udp --dport 53 -m conntrack --ctstate DNAT -j RETURN",
           "R iptables -A REAPER_GUF -i br56 -p tcp --dport 53 -m conntrack --ctstate DNAT -j RETURN",
           "R iptables -A REAPER_GUF -i br56 -o eth0 -j RETURN",
           "R iptables -A REAPER_GUF -i br56 -o wgs1 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN",
           "R iptables -A REAPER_GUF -i br56 -o tun21 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN",
           "R iptables -A REAPER_GUF -i br56 -j DROP",
           "R iptables -A REAPER_GUF -o br56 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN",
           "R iptables -A REAPER_GUF -o br56 -i eth0 -j RETURN",
           "R iptables -A REAPER_GUF -o br56 -i wgs1 -j RETURN",
           "R iptables -A REAPER_GUF -o br56 -i tun21 -j RETURN",
           "R iptables -A REAPER_GUF -o br56 -j DROP"], r4)
    check("...a guest still cannot OPEN a connection to a VPN client (no stateless way out to a server interface)",
          not [l for l in rules(t10) if "-i br56 -o wgs1 -j RETURN" in l or "-i br56 -o tun21 -j RETURN" in l])
    check("...the same pair for IPv6",
          "R ip6tables -A REAPER_GUF -o br56 -i wgs1 -j RETURN" in r6
          and "R ip6tables -A REAPER_GUF -i br56 -o wgs1 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN" in r6
          and r6.index("R ip6tables -A REAPER_GUF -o br56 -i wgs1 -j RETURN") < r6.index("R ip6tables -A REAPER_GUF -o br56 -j DROP"))
    check("...nothing new toward the router itself (REAPER_GUI as for any guest network), still deny-only",
          [l for l in r4 if "REAPER_GUI" in l] == [l for l in rules(t1, 4) if "REAPER_GUI" in l] and " -j ACCEPT" not in t10)
    check("...and the script says so on the network's line",
          "# network 5: br56\n#   clients of the router's own VPN servers may open connections into it; it may only answer\n" in t10
          and "own VPN servers" not in t1)
    check("without a server list the rules are exactly the v3.7.7 ones (set 1 unchanged by this)",
          [l for l in rules(t10) if "wgs1" not in l and "tun21" not in l] == rules(t1))
    p20 = gen(20).strip()
    check("the list rc builds: a plain network gets wgs1, wgs2, tun21 - never tun22 while a portal uses that name; the portal gets none; with no portal, tun22 too",
          p20 == "br56:wgs1,wgs2,tun21, tun22: br58:wgs1,wgs2,tun21, | br56:wgs1,wgs2,tun21,tun22,", p20)
    # ---- 2026-11-14 (field reports, v3.7.7; owner "Yes"): DNS Director's redirect to a main-network resolver ----
    # The stock FORWARD rule accepts every connection the router redirected (DNAT), and before v3.7.7 that is how a
    # guest network's DNS Director rule to a Pi-hole / AdGuard Home on the main LAN worked; this chain ran first and
    # dropped it. The redirected DNS goes on to the stock rules again - port 53 only.
    for s_, X_ in ((1, "br56"), (4, "br58")):
        r4 = rules(gen(s_), 4); r6 = rules(gen(s_), 6)
        dd = ["R iptables -A REAPER_GUF -i %s -p udp --dport 53 -m conntrack --ctstate DNAT -j RETURN" % X_,
              "R iptables -A REAPER_GUF -i %s -p tcp --dport 53 -m conntrack --ctstate DNAT -j RETURN" % X_]
        check("DNS Director (set %d): a DNS query the router redirected goes on to the stock rules, v4 and v6, before the DROP" % s_,
              all(x in r4 for x in dd) and all(x.replace("R iptables", "R ip6tables") in r6 for x in dd)
              and max(r4.index(x) for x in dd) < r4.index("R iptables -A REAPER_GUF -i %s -j DROP" % X_), r4)
    t1x = gen(1)
    check("...port 53 only, and only a redirected (DNAT) connection: nothing else of the guest's reaches the main network",
          [l for l in rules(t1x) if "ctstate DNAT" in l and "REAPER_GUF" in l and "--dport 53 " not in l] == []
          and "-i br56 -o br0" not in t1x and " -j ACCEPT" not in t1x)
    check("...not on a portal (its DNS is held to its own resolver before DNS Director runs)",
          not [l for l in rules(gen(2)) + rules(gen(3)) + rules(gen(8)) if "REAPER_GUF" in l and "ctstate DNAT" in l])
    check("...not while the kill switch is on (the network's DNS stays in the tunnel)",
          not [l for l in rules(gen(12)) if "REAPER_GUF" in l and "ctstate DNAT" in l])
    t11 = gen(11)
    check("a portal: nothing opens into it from a VPN server either (a list handed to it is ignored)",
          "wgs1" not in t11 and rules(t11) == rules(gen(2)), [l for l in rules(t11) if l not in rules(gen(2))])
    t12 = gen(12)
    check("kill switch on: only the bound VPN client, in and out - no VPN server path", "wgs1" not in t12 and "-o wgc5 -j RETURN" in t12)
    t13 = gen(13); r4 = rules(t13, 4)
    check("VPN-bound network, kill switch off: the server path is there, beside the WAN and the bound client",
          "R iptables -A REAPER_GUF -o br58 -i wgs1 -j RETURN" in r4
          and "R iptables -A REAPER_GUF -i br58 -o wgs1 -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN" in r4
          and "R iptables -A REAPER_GUF -o br58 -i wgc5 -j RETURN" not in r4)

    # ---- 2026-11-15 (field report, v3.7.9 beta): two guest VLANs routed to OpenVPN client 1 (tun11) and WireGuard
    # client 2 (wgc2) by VPN Director lost the Internet - REAPER_GUF knew only the Network page's VPN binding, let them
    # out by the WAN only, and dropped everything the router routed into the tunnel.
    VD = "<1>Guest54>192.168.54.0/24>>OVPN1<1>Guest52>192.168.53.0/24>>WGC2"
    tr = gen(30, VD, "2,0,0,0,0"); r4 = rules(tr, 4); r6 = rules(tr, 6)
    check("the report: br54 (VPN Director -> OVPN1) goes out by tun11, br55 (-> WGC2) by wgc2, each with its rule's source",
          "R iptables -A REAPER_GUF -i br54 -s 192.168.54.0/24 -o tun11 -j RETURN" in r4
          and "R iptables -A REAPER_GUF -i br55 -s 192.168.53.0/24 -o wgc2 -j RETURN" in r4, r4)
    check("...each network only by its own client (br54 never by wgc2 through a rule, br55 never by tun11)",
          not [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i br54") and "wgc2" in l]
          and not [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i br55") and "tun11" in l], r4)
    gu = [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i br54 ")]
    check("...after the WAN exit and before the network's DROP; the WAN fallback stays (no kill switch)",
          gu.index("R iptables -A REAPER_GUF -i br54 -o eth0 -j RETURN")
          < gu.index("R iptables -A REAPER_GUF -i br54 -s 192.168.54.0/24 -o tun11 -j RETURN")
          < gu.index("R iptables -A REAPER_GUF -i br54 -j DROP"), gu)
    check("...IPv4 only (VPN Director writes IPv4 ip rules): the IPv6 chain has no rule exit",
          not [l for l in r6 if " -s 192.168." in l or ("-o tun11 -j RETURN" in l) or ("-o wgc2 -j RETURN" in l)], r6)
    check("...still deny-only, nothing toward a bridge or the router: every new exit leaves by a VPN client interface",
          " -j ACCEPT" not in tr and [l for l in r4 if "REAPER_GUI" in l and "br54" in l] == [l.replace("br56", "br54") for l in rules(t1, 4) if "REAPER_GUI" in l]
          and all(re.search(r" -o (tun1[1-5]|wgc[1-5]) ", l) for l in rules(tr) if (" -s " in l or " -d " in l) and "REAPER_GUF" in l))
    check("...the script names the route on the network's line",
          "#   VPN Director / redirect-all routes it to tun11 (from 192.168.54.0/24 to any)\n" in tr)
    check("the same list as before the fix routes nothing else: without a VPN Director list the chain is the v3.7.9 one",
          rules(gen(30, "", "0,0,0,0,0")) == [l for l in rules(tr) if " -s 192.168." not in l], rules(gen(30, "", "0,0,0,0,0")))

    def ex(lst, rgw="2,2,2,2,2", s=30):
        return gen(s, lst, rgw, "print").strip()
    check("an OpenVPN rule counts only while that client is in VPN Director mode (rgw 2/3; none 0 / all 1 write no Director rule)",
          ex(VD, "0,0,0,0,0") == "br54: br55:wgc2|192.168.53.0/24|," and ex(VD, "3,0,0,0,0").startswith("br54:tun11|192.168.54.0/24|,"),
          (ex(VD, "0,0,0,0,0"), ex(VD, "3,0,0,0,0")))
    check("OpenVPN 'redirect all' (rgw 1): every guest network out by that client, whole; 'none' (0) adds nothing",
          ex("", "0,0,1,0,0") == "br54:tun13||, br55:tun13||," and ex("", "0,0,0,0,0") == "br54: br55:",
          (ex("", "0,0,1,0,0"), ex("", "0,0,0,0,0")))
    check("a disabled rule, a WAN rule, an unknown target and a source on another network route nothing here",
          ex("<0>off>192.168.54.0/24>>OVPN1<1>w>192.168.54.0/24>>WAN<1>x>192.168.54.0/24>>OVPN6<1>y>>>WGC0<1>z>192.168.50.0/24>>WGC1") == "br54: br55:",
          ex("<0>off>192.168.54.0/24>>OVPN1<1>w>192.168.54.0/24>>WAN<1>x>192.168.54.0/24>>OVPN6<1>y>>>WGC0<1>z>192.168.50.0/24>>WGC1"))
    check("source any (\"\" or 0.0.0.0): every network, with the rule's destination; any/any = the whole client",
          ex("<1>a>>10.0.0.0/8>WGC1<1>b>0.0.0.0>0.0.0.0>OVPN2") == "br54:wgc1||10.0.0.0/8,tun12||, br55:wgc1||10.0.0.0/8,tun12||,",
          ex("<1>a>>10.0.0.0/8>WGC1<1>b>0.0.0.0>0.0.0.0>OVPN2"))
    check("a source that covers or sits inside the network counts with that source (a /16 over both, one device in br54)",
          ex("<1>a>192.168.0.0/16>>WGC3<1>b>192.168.54.10>>OVPN4") == "br54:wgc3|192.168.0.0/16|,tun14|192.168.54.10|, br55:wgc3|192.168.0.0/16|,",
          ex("<1>a>192.168.0.0/16>>WGC3<1>b>192.168.54.10>>OVPN4"))
    check("malformed: a bad source / destination, 4 or 6 fields - the rule is skipped (Merlin's ip rule fails on it too)",
          ex("<1>a>1.2.3.4.5>>WGC1<1>b>>abc>WGC1<1>c>192.168.54.0/24>WGC1<1>d>192.168.54.0/24>>WGC1>x<1>e>192.168.54.0/33>>WGC1") == "br54: br55:",
          ex("<1>a>1.2.3.4.5>>WGC1<1>b>>abc>WGC1<1>c>192.168.54.0/24>WGC1<1>d>192.168.54.0/24>>WGC1>x<1>e>192.168.54.0/33>>WGC1"))
    check("duplicates collapse, and a whole-client exit covers that client's later rules",
          ex("<1>a>192.168.54.0/24>>WGC1<1>a2>192.168.54.0/24>>WGC1<1>b>>>WGC1<1>c>192.168.54.5>>WGC1") == "br54:wgc1|192.168.54.0/24|,wgc1||, br55:wgc1||,",
          ex("<1>a>192.168.54.0/24>>WGC1<1>a2>192.168.54.0/24>>WGC1<1>b>>>WGC1<1>c>192.168.54.5>>WGC1"))
    many = "".join("<1>d%d>192.168.54.%d>>WGC%d" % (i, i, 1 + i % 5) for i in range(1, 60))
    pm = ex(many).split()[0][len("br54:"):].rstrip(",").split(",")
    check("budget: 59 device rules give at most %d exits, the overflow becomes whole-client exits (never dropped)" % 24,
          len(pm) <= 24 and sorted(set(p.split("|")[0] for p in pm if p.endswith("||"))) == ["wgc1", "wgc2", "wgc3", "wgc4", "wgc5"]
          and len([p for p in pm if not p.endswith("||")]) == 14, pm)
    check("no IPv4 subnet known: only a rule for every source names the network",
          ex("<1>a>192.168.54.0/24>>WGC1<1>b>>>WGC2", s=35) == "br54:wgc2||,", ex("<1>a>192.168.54.0/24>>WGC1<1>b>>>WGC2", s=35))
    p34 = gen(34).split()
    check("rg_cidr4: address or CIDR only, every part in range",
          p34 == ["1:c0a83600/24", "1", "1", "0", "0", "0", "0", "0", "0", "0", "0", "0", "1"], p34)

    tk = gen(31, VD + "<1>all>>>WGC4", "2,1,0,0,0"); r4 = rules(tk, 4)
    check("kill switch on (br54 bound to wgc5): the bound client ONLY - no VPN Director, redirect-all or mark exit",
          [l for l in r4 if l.startswith("R iptables -A REAPER_GUF -i br54 -o") or l.startswith("R iptables -A REAPER_GUF -i br54 -s")] ==
          ["R iptables -A REAPER_GUF -i br54 -o br54 -j RETURN", "R iptables -A REAPER_GUF -i br54 -o wgc5 -j RETURN"]
          and "-i br54 -o tun1" not in tk and "-i br54 -o wgc4" not in tk and not [l for l in tk.splitlines() if "-i br54" in l and "--mark" in l], r4)
    check("kill switch off (br55 bound to tun12): bound client, WAN fallback, and the Director / redirect-all exits for the fallback",
          "R iptables -A REAPER_GUF -i br55 -o tun12 -j RETURN" in r4 and "R iptables -A REAPER_GUF -i br55 -o eth0 -j RETURN" in r4
          and "R iptables -A REAPER_GUF -i br55 -s 192.168.53.0/24 -o wgc2 -j RETURN" in r4
          and "R iptables -A REAPER_GUF -i br55 -o tun12 -j RETURN" in r4 and "R iptables -A REAPER_GUF -i br55 -o wgc4 -j RETURN" in r4, r4)
    tp = gen(32, VD + "<1>all>>>WGC4", "2,1,0,0,0")
    check("a portal is unchanged: no VPN Director, redirect-all or mark exit (its rules as before)",
          rules(tp) == rules(gen(32, "", "0,0,0,0,0")) and "--mark" not in tp and "VPN Director" not in tp, rules(tp))

    # Policy Routing (rc/reaper_pbr.c): marks the flow in mangle PREROUTING with bits 16-19 = its target's code
    mk = [l for l in tr.splitlines() if " -m mark --mark " in l]
    want = []
    for fam in ("iptables", "ip6tables"):
        for X in ("br54", "br55"):
            want += ["R %s -A REAPER_GUF -i %s -o %s -m mark --mark 0x%x0000/0xf0000 -j RETURN" % (fam, X, ("tun1%d" % c) if c <= 5 else ("wgc%d" % (c - 5)), c) for c in range(1, 11)]
    check("Policy Routing: a packet carrying a client's code (1-5 OVPN1-5, 6-10 WGC1-5) may leave by that client only, v4 and v6",
          sorted(mk) == sorted(want), mk)
    full = [l for l in tr.splitlines() if l.startswith("R iptables -A REAPER_GUF -i br54")]
    check("...before the network's DROP, for every plain guest network (set 1 too)",
          max(full.index(l) for l in full if "--mark" in l) < full.index("R iptables -A REAPER_GUF -i br54 -j DROP")
          and len([l for l in gen(1).splitlines() if "-i br56 -o" in l and "--mark" in l]) == 20)
    pbr = read("rc/reaper_pbr.c")
    check("...the mask and codes are reaper_pbr.c's own (PPBR_MASK bits 16-19; OVPNn = n, WGCn = 5 + n)",
          '#define PPBR_MASK       "0x000F0000"' in pbr and "*code = t[4] - '0';" in pbr and "*code = 5 + (t[3] - '0');" in pbr
          and '#define RG_PBR_MASK\t"0xf0000"' in gsrc)
    if shutil.which("sh"):
        sc = os.path.join(tmp, "apply.sh"); open(sc, "w").write(tr)
        r = subprocess.run(["sh", "-n", sc], capture_output=True, text=True)
        check("the generated script parses (sh -n)", r.returncode == 0, r.stderr)
        bb = shutil.which("busybox")
        if bb:
            r = subprocess.run([bb, "ash", "-n", sc], capture_output=True, text=True)
            check("the generated script parses (busybox ash -n)", r.returncode == 0, r.stderr)

    t6 = gen(6)
    check("no guest network left: the layer is unhooked and removed, the front chains re-pinned",
          "-D REAPER_HOOK -j REAPER_GUI" in t6 and "-D REAPER_HOOK_F -j REAPER_GUF" in t6 and "$T -X $C" in t6
          and "HOOK_RUN" in t6 and "R " not in t6)
    check("...and the DNS redirect chain is unhooked and removed with it",
          "iptables -t nat -D PREROUTING -j REAPER_GUN 2>/dev/null" in t6 and "iptables -t nat -X REAPER_GUN" in t6)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- the network set (non-pure part)
check("membership: enabled, not the main LAN, not a guest SSID on the main subnet; a portal always, others unless paired with the Main Network",
      "if (m->enable != 1 || m->sdn_t.sdn_idx == 0 || m->nw_t.idx == 0)" in gsrc
      and 'if (!m->nw_t.br_ifname[0] || !strcmp(m->nw_t.br_ifname, "br0"))' in gsrc
      and "if (!portal && rg_main_access(acc, m->sdn_t.sdn_idx, refs, nref, lanif))" in gsrc and "if (is_routing_enabled() &&" in gsrc)
check("a portal's main-LAN route only from a pair with the Main Network, the bridge from lan_ifname (owner 2026-11-13; 2026-11-16)",
      "if (portal && rg_main_access(acc, m->sdn_t.sdn_idx, refs, nref, lanif)) {" in gsrc
      and 'strlcpy(g[n].lanif, nvram_safe_get("lan_ifname"), sizeof(g[n].lanif));' in gsrc)
# 2026-11-16 (bug review A1): the "named in any pair" test is gone everywhere, and one table feeds all three users
check("the old any-pair test is gone (rg_access_on)", "rg_access_on" not in gsrc)
check("the pair table: every enabled network (bridge, FORWARD interface, portal or not), loaded once per build",
      "\t\tnref = rg_refs_load(refs, MTLAN_MAXINUM);\n\t\tif (get_mtlan(pmtl, &sz)) {" in gsrc
      and "\t\t\tif (m->enable != 1)\n\t\t\t\tcontinue;\n\t\t\tmemset(&refs[n], 0, sizeof(refs[n]));" in gsrc
      and "strlcpy(refs[n].ifname, m->nw_t.ifname[0] ? m->nw_t.ifname : refs[n].br, sizeof(refs[n].ifname));" in gsrc
      and "refs[n].portal = (cpt.cp_type == 1 || cpt.cp_type == 2 || cpt.cp_type == 4);" in gsrc)
check("each network's peers come from rg_peers; the peer name is built like the network's own (the interface FORWARD sees)",
      "g[n].npeer = rg_peers(acc, m->sdn_t.sdn_idx, refs, nref, lanif, g[n].peer, RG_PEER_MAX);" in gsrc
      and "strlcpy(g[n].ifname, m->nw_t.ifname[0] ? m->nw_t.ifname : m->nw_t.br_ifname, sizeof(g[n].ifname));" in gsrc
      and "#define RG_PEER_MAX\t16" in gsrc and "char peer[RG_PEER_MAX][IFNAMSIZ];" in gsrc)
check("the resolver's hosts / encrypted-DNS offer (sdn.c) and mDNS use the same main-network test",
      'return rg_main_access(nvram_safe_get("sdn_access_rl"), sdn_idx, refs, nref, nvram_safe_get("lan_ifname"));' in gsrc
      and "!rg_main_access(acc, m->sdn_t.sdn_idx, refs, nref, lan))) {" in gsrc
      and 'reaper_guest_intranet(m->sdn_t.sdn_idx));' in read("rc/sdn.c"))
check("the stock pair rule this layer RETURNs to: two-way forwarding between exactly the two networks (rc/firewall_sdn.c)",
      'fprintf(fp, "-A %s -i %s -o %s -j %s\\n", SDN_INTERNAL_ACCESS_CHAIN, ifname1, ifname2, logaccept);' in read("rc/firewall_sdn.c")
      and 'fprintf(fp, "-A %s -i %s -o %s -j %s\\n", SDN_INTERNAL_ACCESS_CHAIN, ifname2, ifname1, logaccept);' in read("rc/firewall_sdn.c"))
check("WAN interfaces from get_wan_ifname() for every WAN unit (PPPoE and dual WAN), IPv6 from get_wan6face()",
      "for (u = WAN_UNIT_FIRST; u < WAN_UNIT_MAX; u++) {\n\t\tw = get_wan_ifname(u);" in gsrc and "(w = get_wan6face()) != NULL" in gsrc)
check("VPN servers by interface name (wgs1-2, tun21-22), never for a portal, never a name a guest network itself uses (a portal's tun22)",
      'static const char *const srv[RG_SRV_MAX] = { "wgs1", "wgs2", "tun21", "tun22" };' in gsrc
      and "\t\tif (g[k].portal)\n\t\t\tcontinue;\n\t\tfor (s = 0; s < RG_SRV_MAX; s++) {" in gsrc
      and "if (!strcmp(g[u].ifname, srv[s]) || !strcmp(g[u].brname, srv[s]))" in gsrc
      and "if (!c && g[k].nsrv < RG_SRV_MAX)" in gsrc
      and gsrc.count("if (!g->portal && !vpn_only)") == 3 and "#define RG_SRV_MAX\t4" in gsrc)
check("VPN Director's list and the OpenVPN clients' redirect mode are read for every network (2026-11-15)",
      'f_read_string(OVPN_FS_PATH "/vpndirector_rulelist", vd, sizeof(vd))' in gsrc
      and 'snprintf(key, sizeof(key), "vpn_client%d_rgw", u + 1);' in gsrc
      and "\t\tfor (k = 0; k < n; k++)\n\t\t\trg_policy_vpn(&g[k], vd, rgw);" in gsrc
      and gsrc.index("REAPER-GUEST-PURE-END") < gsrc.index("rg_policy_vpn(&g[k], vd, rgw);") < gsrc.index("rg_write(f, g, n, wan4, nw4, wan6, REAPER_HOOK_RUN);")
      and 'snprintf(filename, sizeof(filename), "%s/vpndirector_rulelist", OVPN_FS_PATH);' in read("libovpn/amvpn_routing.c"))
check("the script is root's own, published atomically, run under the firewall lock",
      "reaper_secure_dir(RG_DIR, 0700);" in gsrc and "rename(RG_APPLY \".tmp\", RG_APPLY)" in gsrc
      and 'lk = file_lock("firewall");' in gsrc and 'eval("sh", RG_APPLY);' in gsrc)

hook = read("rc/reaper_hook.c")
check("hook.sh: REAPER_GUI / REAPER_GUF right after Warden, ahead of Gatekeeper and the rules engine",
      hook.find("-j REAPER_WARDEN\\n\"\n\t  /* 2026-11-12: guest isolation") > 0
      and hook.find("-j REAPER_GUI\\n") < hook.find("if $T -nL REAPER_GKI >/dev/null") < hook.find("-j REAPER_FWI")
      and hook.find("-j REAPER_GUF\\n") < hook.find("if $T -nL REAPER_GKF >/dev/null") < hook.find("-j REAPER_FWF"))
fw = read("rc/firewall.c")
check("re-applied at the end of every firewall build, under the lock held there",
      "\treaper_guest_apply(1);\n#endif\n\tfile_unlock(llock);" in fw)
svc = read("rc/services.c")
check("re-applied after every guest-network change and delete",
      "\t\tif (action & RC_SERVICE_START)\n\t\t\treaper_guest_apply(0);" in svc and "\t\treaper_guest_apply(0);	/* 2026-11-12: a deleted network leaves" in svc)
check("built under MULTILAN_CFG, declared in rc.h",
      "OBJS += firewall_sdn.o\nOBJS += reaper_guest.o\nendif" in read("rc/Makefile")
      and "extern void reaper_guest_apply(int have_lock);" in read("rc/rc.h"))
sj = read("www/sysdep/FUNCTION/SDN/SDN/sdn.js")
if "kill_switch_parm" in sj:
    check("Network page: a VPN binding starts with the Kill Switch on (3 places), a saved network keeps its own",
          sj.count('if($killSwitchContainer.css("display") == "none")') == 3
          and '_profile_data.sdn_rl.kill_switch == "1" ? "on" : "off"' in sj)
else:
    print("note: this line's Network page has no Kill Switch control - the rc side still honours a saved one")
# 2026-11-16: the Network page says what a tick in the Access Intranet list means (token RSDN_2)
check("Network page: one note under the Access Intranet list, from the RSDN_2 token in a template literal (stock file stays ASCII)",
      sj.count(".html(`<#RSDN_2#>`).appendTo($access_intranet_cntr);") == 1 and "'<#RSDN_2#>'" not in sj
      and sj.index("<#RSDN_2#>") < sj.index("function Get_Component_SDN_CheckBox(_data){")
      and all(ord(ch) < 128 for ch in sj[sj.index("reaper 2026-11-16: say what a tick means"):sj.index("function Get_Component_SDN_CheckBox(_data){")]))
_www = os.path.join(SRC, "www")
_packs = sorted(f for f in os.listdir(_www) if re.match(r"^[A-Z]{2}\.dict$", f))
_miss, _lens = [], set()
for _f in _packs:
    _t = open(os.path.join(_www, _f), encoding="utf-8").read()
    _lens.add(_t.count("\n"))
    _m = re.search(r"^RSDN_2=(.+)$", _t, re.M)
    if not _m or len(re.findall(r"^RSDN_2=", _t, re.M)) != 1 or any(x in _m.group(1) for x in ('"', "'", "`", "\\", "${", "</")):
        _miss.append(_f)
check("RSDN_2 once in all %d packs, quote-safe, packs in lockstep" % len(_packs), len(_packs) == 25 and not _miss and len(_lens) == 1, (_miss, _lens))
_en = re.search(r"^RSDN_2=(.+)$", open(os.path.join(_www, "EN.dict"), encoding="utf-8").read(), re.M)
check("RSDN_2 (English): Main Network joins the admin's own devices; another network links only the two, both stay isolated",
      _en is not None and _en.group(1).startswith("Main Network: this network joins your own devices. Another network: ")
      and _en.group(1).endswith("can reach each other only; both stay isolated from the main network and from the router."), _en and _en.group(1))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
