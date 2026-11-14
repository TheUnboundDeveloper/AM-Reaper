#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest isolation: guests reach only the WAN or their VPN client, the router only for DHCP/DNS/portal (2026-11-12).

WHY THIS EXISTS. Owner hard rule: a guest - every device on a Guest Portal network, and on any guest network whose
"Access Intranet" is off - must never see or reach non-guest devices or router features, on any path, including the
WAN fallback while its VPN client is down. Stock left it open (router services on every router address but
lan_ipaddr; signed-in portal guests accepted to anywhere via `-I FORWARD -i tun22 NEW ACCEPT`; new connections in
from a bound VPN client; a portal's IPv6 past the portal), and the Kill Switch did not hold for a portal network.

WHAT IT DOES. Compiles the REAPER-GUEST-PURE block of rc/reaper_guest.c on the host and generates the apply script
for sample network sets; checks the exact rules (a plain guest network, a Free Wi-Fi portal with its bridge, an
account portal, a VPN-bound network with the Kill Switch off and on, two WANs, no IPv6 WAN), that the layer never
ACCEPTs, the tear-down when no guest network is left, and the sdn_access_rl / vpnc_idx parsers. Then pins the
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
	case 7: /* parsers */
		printf("%d %d %d %d %d\n", rg_access_on("<0>5<0>7", 5), rg_access_on("<0>5<0>7", 7), rg_access_on("<0>5<0>7", 6),
		       rg_access_on("", 5), rg_access_on("<12>3", 12));
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
    open(c, "w").write(HARNESS.replace("@@PURE@@", m.group(1)))
    r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    check("the block compiles with -Wall -Werror", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n%d check(s) failed" % len(fails)); sys.exit(1)
    def gen(s):
        return subprocess.run([exe, str(s)], capture_output=True, text=True).stdout
    def rules(txt, fam=None):
        L = [l for l in txt.splitlines() if l.startswith("R ")]
        # filter-table rules only; the nat DNS redirect (2026-11-13) is read through nat() below
        if fam == 4: L = [l for l in L if l.startswith("R iptables ") and not l.startswith("R iptables -t nat ")]
        if fam == 6: L = [l for l in L if l.startswith("R ip6tables ")]
        return L
    def nat(txt):
        return [l for l in txt.splitlines() if l.startswith("R iptables -t nat ")]

    p = gen(7).split()
    check("sdn_access_rl: a network named in any pair has intranet access, on either side; others none",
          p[:5] == ["1", "1", "0", "0", "1"], p)
    check("vpnc_idx -> interface: 1..5 wgcN, 6..10 tun1N, anything else none", p[5:] == ["wgc5", "tun11", "tun15", "[]", "[]"], p)

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

    t6 = gen(6)
    check("no guest network left: the layer is unhooked and removed, the front chains re-pinned",
          "-D REAPER_HOOK -j REAPER_GUI" in t6 and "-D REAPER_HOOK_F -j REAPER_GUF" in t6 and "$T -X $C" in t6
          and "HOOK_RUN" in t6 and "R " not in t6)
    check("...and the DNS redirect chain is unhooked and removed with it",
          "iptables -t nat -D PREROUTING -j REAPER_GUN 2>/dev/null" in t6 and "iptables -t nat -X REAPER_GUN" in t6)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- the network set (non-pure part)
check("membership: enabled, not the main LAN, not a guest SSID on the main subnet; a portal always, others only without intranet access",
      "if (m->enable != 1 || m->sdn_t.sdn_idx == 0 || m->nw_t.idx == 0)" in gsrc
      and 'if (!m->nw_t.br_ifname[0] || !strcmp(m->nw_t.br_ifname, "br0"))' in gsrc
      and "if (!portal && rg_access_on(acc, m->sdn_t.sdn_idx))" in gsrc and "if (is_routing_enabled() &&" in gsrc)
check("a portal's Access Intranet (sdn_access_rl) sets the main-LAN route, the bridge from lan_ifname (owner 2026-11-13)",
      "if (portal && rg_access_on(acc, m->sdn_t.sdn_idx)) {" in gsrc
      and 'strlcpy(g[n].lanif, nvram_safe_get("lan_ifname"), sizeof(g[n].lanif));' in gsrc)
check("WAN interfaces from get_wan_ifname() for every WAN unit (PPPoE and dual WAN), IPv6 from get_wan6face()",
      "for (u = WAN_UNIT_FIRST; u < WAN_UNIT_MAX; u++) {\n\t\tw = get_wan_ifname(u);" in gsrc and "(w = get_wan6face()) != NULL" in gsrc)
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

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
