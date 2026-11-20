#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest networks bound to a VPN client keep their routing after a WAN event (guest VPN binding B2). 2026-11-19.

WHY THIS EXISTS. Every WAN event runs add_multi_routes(), which opens with `ip rule flush` (the open twin in rc/wan.c
shows it; the shipped DUALWAN build is a closed blob with the same prologue). That dropped the rule sending each
VPN-bound guest network into its client's table (`ip rule iif brN table T pref 1000+3n`) and br0's pref-999 rule when
the default WAN is a VPN client. Nothing re-added them until the VPN client restarted, so a bound network's traffic
left by the WAN meanwhile. _handle_sdn_wan() could not be reused: it is unlocked, deletes the kill-switch `prohibit`
rule (grep of `ip rule show` into a fixed /tmp file), and runs iptables. The new rc/sdn.c reaper_sdn_vpn_rules()
re-adds only those rules, deleting each in its exact form first (idempotent), under its own lock, after
reaper_pbr_reassert() and before amvpn_set_kilswitch_rules_all() at every add_multi_routes() site. The applet in
rc/rc.c had its kill-switch call after `return` (dead code): it now runs before the return. Two related fixes in
_handle_sdn_wan(): an unbound network drops the IPv6 binding rule an earlier binding left (the stock removal is
RTCONFIG_MULTIWAN_IF only), and br0's default-VPN path removes before it adds (each run added another copy).

WHAT IT CHECKS. Source pins on rc/sdn.c, rc/rc.h, rc/wan.c, rc/wanduck.c, rc/rc.c. With gcc, the helper's pure block
(REAPER-SDNVPN-PURE) is compiled against the real table / pref constants from shared/shared.h and run: one
WireGuard-bound network, one OpenVPN-bound network with IPv6, the main LAN bound, br0 with the default VPN, an
unbound network and a same-subnet network (nothing), and the IPv6 stale-rule matcher against the kill switch, Policy
Routing and look-alike lines, in the shape `ip -6 -N rule show` prints them (review 2026-11-19: the router's
rt_tables names tables 1-10, so the matcher reads numeric output; ` [detached]` sits between the iif name and
`lookup`; both pinned against the tree's iproute2 5.11 source). Tree from argv[1] or REAPER_ROUTER_SRC. Exit 0 pass, 1 fail, 77 skip."""
import os, re, shutil, subprocess, sys, tempfile

SRC = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC")
       or os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router"))
P = {k: os.path.join(SRC, *v) for k, v in {
    "sdn": ("rc", "sdn.c"), "rch": ("rc", "rc.h"), "wan": ("rc", "wan.c"), "duck": ("rc", "wanduck.c"),
    "rc": ("rc", "rc.c"), "sh": ("shared", "shared.h")}.items()}
if not all(os.path.isfile(p) for p in P.values()):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
S = {k: rd(p) for k, p in P.items()}
fails = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name); print("FAIL " + name + ((" :: " + str(detail)[:400]) if detail else ""))

sdn = S["sdn"]
# ---- the helper block
check("one REAPER-SDNVPN block and one pure block",
      sdn.count("/* REAPER-SDNVPN-BEGIN */") == 1 and sdn.count("/* REAPER-SDNVPN-END */") == 1
      and sdn.count("/* REAPER-SDNVPN-PURE-BEGIN */") == 1 and sdn.count("/* REAPER-SDNVPN-PURE-END */") == 1)
b0 = sdn.find("/* REAPER-SDNVPN-BEGIN */"); b1 = sdn.find("/* REAPER-SDNVPN-END */")
blk = sdn[b0:b1]
hsw = sdn.find("static int _handle_sdn_wan(const MTLAN_T *pmtl, const char *logdrop, const char *logaccept)\n{")
check("the block sits after reaper_vpnc_proto() and before _handle_sdn_wan() (both use it)",
      0 < sdn.find("static VPNC_PROTO reaper_vpnc_proto(int vpnc_idx)") < b0 < b1 < hsw)
f0 = blk.find("void reaper_sdn_vpn_rules(void)\n{")
fn = blk[f0:]
check("reaper_sdn_vpn_rules() is exported (not static) and declared in rc/rc.h under RTCONFIG_MULTILAN_CFG",
      f0 > 0 and "static void reaper_sdn_vpn_rules" not in sdn
      and re.search(r"#ifdef RTCONFIG_MULTILAN_CFG\n(?:extern [^\n]*\n)*?extern void reaper_sdn_vpn_rules\(void\);[^\n]*\n(?:extern [^\n]*\n|#define [^\n]*\n)*#endif", S["rch"]) is not None
      and S["rch"].count("extern void reaper_sdn_vpn_rules(void);") == 1)
check("its own lock, released, and one syslog line with the count",
      'lock = file_lock("reaper_sdnvpn");' in fn and "file_unlock(lock);" in fn and fn.index('file_lock("reaper_sdnvpn")') < fn.index("file_unlock(lock);")
      and fn.count("logmessage(") == 1 and re.search(r'if \(rules\)\n\t\tlogmessage\("sdn", "[^"]*%d network\(s\)[^"]*%d rules\)", nets, rules\);', fn))
check("touches only ip rules: no grep-and-delete, no iptables, no kill-switch call, no shared tmp file",
      "_remove_sdn_routing_rule" not in blk and "iptables" not in blk.replace("no iptables", "")
      and "amvpn_" not in blk.replace("amvpn_set_kilswitch_rules_all()", "") and "/tmp/" not in blk and "system(" not in blk
      and "prohibit" not in blk.replace("`prohibit` rules", "").replace("kill switch, Policy", ""))
check("every rule is deleted in its exact form before it is added (idempotent)",
      'rsdnvpn_ip(&r[j], "del");\n\t\t\trsdnvpn_ip(&r[j], "add");' in fn
      and '_eval(argv, strcmp(op, "del") ? NULL : ">/dev/null", 0, NULL);' in blk)
check("enabled networks only (the main LAN always), skipped in client mode as handle_sdn_feature() does",
      "if (!pmtl[i].enable && pmtl[i].sdn_t.sdn_idx != 0)\n\t\t\tcontinue;" in fn
      and 'if (client_mode() && !nvram_match("re_mode", "1"))' in fn)
check("IPv6 rule only when IPv6 is on for the network and the client is WireGuard or OpenVPN (reaper_vpnc_proto)",
      re.search(r"static int rsdnvpn_v6ok\(const MTLAN_T \*pmtl, int vpnc_idx\)\n\{\n#if defined\(RTCONFIG_IPV6\) && defined\(RTCONFIG_VPN_FUSION\)\n"
                r".*?if \(!vpnc_idx \|\| !ipv6_enabled\(\) \|\| !pmtl->nw_t.v6_enable\)\n\t\treturn 0;\n\tproto = reaper_vpnc_proto\(vpnc_idx\);\n"
                r"\treturn proto == VPNC_PROTO_OVPN \|\| proto == VPNC_PROTO_WG;\n#else\n\treturn 0;\n#endif\n\}", blk, re.S) is not None)

# ---- _handle_sdn_wan fixes
hb = sdn[hsw:sdn.index("\n}\n", hsw)]
check("_handle_sdn_wan: an unbound network drops a stale IPv6 binding rule (REAPER-SDNVPN-V6UNBIND), under RTCONFIG_IPV6",
      sdn.count("REAPER-SDNVPN-V6UNBIND") == 1
      and re.search(r"\n\t\}\n#ifdef RTCONFIG_IPV6\n\telse \{\t/\* reaper 2026-11-19 \(B2, REAPER-SDNVPN-V6UNBIND\)[^\n]*\n[^\n]*\*/\n\t\trsdnvpn_v6_unbind\(pmtl->nw_t.ifname\);\n\t\}\n#endif\n\n#ifdef RTCONFIG_MULTIWAN_IF\n", hb) is not None
      and hb.index("if(pmtl->sdn_t.vpnc_idx != 0)") < hb.index("rsdnvpn_v6_unbind("))
check("the stale-rule remover reads `ip -6 -N rule show` itself (numeric tables, no shared /tmp file) and deletes only matched rules",
      'popen("ip -6 -N rule show", "r")' in blk and "ip -6 rule show\"" not in blk
      and "rsdnvpn_v6_stale(line, ifname, &r[n])" in blk and 'rsdnvpn_ip(&r[i], "del");' in blk)
# review 2026-11-19: on the router /rom/etc/iproute2/rt_tables names tables 1-10 (wgc1..ovpnc5) and iproute2 5.11
# prints names unless -N is given; it prints " [detached]" right after the iif name, before " lookup"
rt = os.path.join(SRC, "rom", "rom", "etc", "iproute2", "rt_tables")
if os.path.isfile(rt):
    check("rom rt_tables names the VPN client tables (why -N is needed)", re.search(r"^1\s+wgc1$", rd(rt), re.M) is not None)
ipd = os.path.join(SRC, "iproute2-5.11.0", "iproute2-5.11.0", "ip")
if os.path.isdir(ipd):
    ipc, ipr = rd(os.path.join(ipd, "ip.c")), rd(os.path.join(ipd, "iprule.c"))
    check("iproute2 5.11: `-N` is the -Numeric option", re.search(r'matches\(opt, "-Numeric"\) == 0\) \{\n\t+\+\+numeric;', ipc) is not None)
    k0 = ipr.find('"iif", "%s",'); k1 = ipr.find('" [detached]"', k0); k2 = ipr.find('" lookup %s"', k0)
    check("iproute2 5.11: rule output order is `iif NAME [detached] lookup N` (what the matcher parses)", 0 < k0 < k1 < k2, (k0, k1, k2))
else:
    print("note: no iproute2-5.11.0 source in this tree - the output-format pins are skipped")
check("the lock comment says it serialises the helper with itself only",
      "serialises this helper with itself only: stock _handle_sdn_wan() takes no lock" in fn
      and "never lose one" in fn)
lp = hb.find("snprintf(pref, sizeof(pref), \"%d\", IP_RULE_PREF_DEFAULT_CONN);\n\t\t\t{\t/* reaper 2026-11-19 (B2, REAPER-SDNVPN-LANDEL)")
check("_handle_sdn_wan: br0's default-VPN rule (both families) is removed before it is added (REAPER-SDNVPN-LANDEL)",
      sdn.count("REAPER-SDNVPN-LANDEL") == 1 and lp > 0
      and hb.find('rsdnvpn_ip(&dr, "del");\n\t\t\t\tdr.v6 = 1;\n\t\t\t\trsdnvpn_ip(&dr, "del");\n\t\t\t}\n\t\t\teval("ip", "rule", "add", "iif", (char*)pmtl->nw_t.ifname, "table", table, "pref", pref);', lp) > lp)
check("_handle_sdn_wan keeps its stock adds (both IPv6 adds, both reaper_vpnc_proto calls)",
      hb.count('eval("ip", "-6", "rule", "add", "iif", (char*)pmtl->nw_t.ifname, "table", table, "pref", pref);') >= 2
      and hb.count("proto = reaper_vpnc_proto(") == 2)

# ---- call sites: after every add_multi_routes(), reaper_pbr_reassert, then the helper, then the kill switch
CALL = "#ifdef RTCONFIG_MULTILAN_CFG\n{t}reaper_sdn_vpn_rules();"
KS = "#if defined(RTCONFIG_WIREGUARD) || defined(RTCONFIG_OPENVPN)\n{t}amvpn_set_kilswitch_rules_all();\n#endif\n"
def sites(txt):
    out = []
    for m in re.finditer(r"\n(\t+)(?:amr_rc = \(argc == 2\) \? )?add_multi_routes\([^;]*;", txt):
        out.append((m.start(), m.group(1)))
    return out
for key, fname, want in (("wan", "rc/wan.c", 2), ("duck", "rc/wanduck.c", 1), ("rc", "rc/rc.c", 1)):
    txt = S[key]; ss = sites(txt)
    check("%s: %d add_multi_routes() call site(s) found" % (fname, want), len(ss) == want, len(ss))
    for pos, tabs in ss:
        seg = txt[pos:pos + 2400]
        a = seg.find(tabs + "reaper_pbr_reassert();")
        b = seg.find(CALL.format(t=tabs))
        c = seg.find(KS.format(t=tabs))
        ln = txt.count("\n", 0, pos) + 2
        check("%s:%d: reaper_pbr_reassert -> reaper_sdn_vpn_rules (guarded) -> kill switch, in that order" % (fname, ln),
              0 < a < b < c and "\n#endif\n" in seg[b:c] and seg[b:c].count(";") == 1, (a, b, c))
check("the four sites carry their tags once each",
      all(S[k].count(t) == 1 for k, t in (("wan", "REAPER-SDNVPN-WANUP"), ("wan", "REAPER-SDNVPN-WANLB"),
                                          ("duck", "REAPER-SDNVPN-WANDUCK"), ("rc", "REAPER-SDNVPN-APPLET"))))
rc = S["rc"]; a0 = rc.find('else if (!strcmp(base, "add_multi_routes")) {'); a1 = rc.find("\n\t}\n", a0)
ap = rc[a0:a1 + 4]
check("rc.c applet: the kill-switch call is no longer dead code - it runs before `return amr_rc;`, nothing after it",
      a0 > 0 and ap.count("amvpn_set_kilswitch_rules_all();") == 1
      and ap.index("amvpn_set_kilswitch_rules_all();") < ap.index("return amr_rc;")
      and ap.endswith("\t\treturn amr_rc;\n\t}\n") and "left as-is" not in ap)
check("no add_multi_routes() site elsewhere in rc/ was missed",
      all(len(sites(S[k])) == n for k, n in (("wan", 2), ("duck", 1), ("rc", 1))))

# ---- the pure block, compiled and run
gcc = shutil.which("gcc")
pm = re.search(r"/\* REAPER-SDNVPN-PURE-BEGIN \*/\n(.*?)/\* REAPER-SDNVPN-PURE-END \*/", sdn, re.S)
def const(name, txt, after=None):
    t = txt if after is None else txt[txt.index(after):]
    m = re.search(r"#define %s\s+(\d+)" % name, t)
    return int(m.group(1)) if m else None
sh = S["sh"]
vif = const("IP_RULE_PREF_VPNC_POLICY_IF", sh); dc = const("IP_RULE_PREF_DEFAULT_CONN", sh)
mb = re.search(r"#ifdef RTCONFIG_MULTIWAN_IF\n#define IP_ROUTE_TABLE_ID_VPNC_BASE\s+\d+\n(?:#define [^\n]*\n)*#else\n#define IP_ROUTE_TABLE_ID_VPNC_BASE\s+(\d+)\n", sh)
base = int(mb.group(1)) if mb else None
check("constants found in shared/shared.h (pref 1000 / 999, table base of a build without RTCONFIG_MULTIWAN_IF)",
      vif == 1000 and dc == 999 and base is not None, (vif, dc, base))
cfg = os.path.join(SRC, ".config")
if os.path.isfile(cfg):
    check(".config: RTCONFIG_MULTIWAN_IF is off (the table base used below is the right one)",
          "# RTCONFIG_MULTIWAN_IF is not set" in rd(cfg) or "RTCONFIG_MULTIWAN_IF=y" not in rd(cfg))
vf = os.path.join(SRC, "rc", "vpnc_fusion.h")
if os.path.isfile(vf):
    check("RSDNVPN_IDX_MAX equals MAX_VPNC_PROFILE", const("MAX_VPNC_PROFILE", rd(vf)) == const("RSDNVPN_IDX_MAX", sdn))
if pm and gcc and base is not None:
    harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <net/if.h>
#define IP_RULE_PREF_VPNC_POLICY_IF @@VIF@@
#define IP_RULE_PREF_DEFAULT_CONN @@DC@@
#define IP_ROUTE_TABLE_ID_VPNC_BASE @@BASE@@
@@PURE@@
static void show(const char *name, const char *ifname, int sdn_idx, int nw_idx, int vpnc, int v6b, int lan, int dflt, int v6d)
{
	RSDNVPN_RULE r[RSDNVPN_RULES_MAX];
	char *argv[11];
	int n, i, j;
	const char *ops[2] = {"del", "add"};

	n = rsdnvpn_rules(ifname, sdn_idx, nw_idx, vpnc, v6b, lan, dflt, v6d, r, RSDNVPN_RULES_MAX);
	printf("%s:%d", name, n);
	for (i = 0; i < n; i++)
		for (j = 0; j < 2; j++) {
			rsdnvpn_argv(&r[i], ops[j], argv);
			printf("|");
			for (int k = 0; argv[k]; k++)
				printf("%s%s", k ? " " : "", argv[k]);
		}
	printf("\n");
}
static void stale(const char *name, const char *line, const char *ifname)
{
	RSDNVPN_RULE r;
	char *argv[11];

	memset(&r, 0, sizeof(r));
	if (!rsdnvpn_v6_stale(line, ifname, &r)) { printf("%s:-\n", name); return; }
	rsdnvpn_argv(&r, "del", argv);
	printf("%s:", name);
	for (int k = 0; argv[k]; k++)
		printf("%s%s", k ? " " : "", argv[k]);
	printf("\n");
}
int main(void)
{
	show("wg", "br52", 2, 3, 1, 0, 0, 0, 0);
	show("wg6", "br52", 2, 3, 1, 1, 0, 0, 0);
	show("ovpn6", "br53", 3, 4, 6, 1, 0, 0, 0);
	show("lanbound", "br0", 0, 0, 3, 0, 1, 0, 0);
	show("landflt", "br0", 0, 0, 0, 0, 1, 2, 1);
	show("landflt4", "br0", 0, 0, 0, 0, 1, 7, 0);
	show("unbound", "br54", 4, 5, 0, 0, 0, 0, 0);
	show("unbound_dflt", "br54", 4, 5, 0, 0, 0, 2, 1);
	show("samesub", "br55", 5, 0, 1, 1, 0, 0, 0);
	show("badidx", "br56", 6, 6, 17, 1, 0, 0, 0);
	show("noif", "", 6, 6, 1, 1, 0, 0, 0);
	/* `ip -6 -N rule show` lines as iproute2 5.11 prints them (iprule.c: "%u:\t", "from all", " iif %s",
	   " [detached]" when the device is down, " lookup %s", then "\n") */
	stale("s_guest", "1003:\tfrom all iif br52 lookup @@T1@@\n", "br52");
	stale("s_guest_sp", "1003:\tfrom all iif br52 lookup @@T1@@ \n", "br52");
	stale("s_lan", "999:\tfrom all iif br0 lookup @@T2@@\n", "br0");
	stale("s_det", "1018:\tfrom all iif br53 [detached] lookup @@T6@@\n", "br53");
	stale("s_det_end", "1018:\tfrom all iif br53 lookup @@T6@@ [detached]\n", "br53");
	stale("s_det_tail", "1003:\tfrom all iif br52 [detached] lookup @@T1@@ proto static\n", "br52");
	stale("s_prefix", "1003:\tfrom all iif br520 lookup @@T1@@\n", "br52");
	stale("s_pref", "1004:\tfrom all iif br52 lookup @@T1@@\n", "br52");
	stale("s_ks", "@@KSPREF@@:\tfrom all iif br52 prohibit\n", "br52");
	stale("s_pbr", "9001:\tfrom all fwmark 0x1000/0xf000 lookup @@T1@@\n", "br52");
	stale("s_main", "32766:\tfrom all lookup 254\n", "br52");
	stale("s_junk", "1003:\tfrom all iif br52 lookup 1x\n", "br52");
	stale("s_big", "1051:\tfrom all iif br52 lookup @@T17@@\n", "br52");
	stale("s_src", "1003:\tfrom 192.168.52.0/24 iif br52 lookup @@T1@@\n", "br52");
	stale("s_tail", "1003:\tfrom all iif br52 lookup @@T1@@ proto static\n", "br52");
	return 0;
}
'''
    T = lambda n: str(base + n)
    rep = {"@@VIF@@": str(vif), "@@DC@@": str(dc), "@@BASE@@": str(base), "@@PURE@@": pm.group(1),
           "@@T1@@": T(1), "@@T2@@": T(2), "@@T6@@": T(6), "@@T17@@": T(17), "@@KSPREF@@": "1013"}
    for k, v in rep.items():
        harness = harness.replace(k, v)
    d = tempfile.mkdtemp(prefix="sdnvpn_")
    try:
        c = os.path.join(d, "t.c"); exe = os.path.join(d, "t")
        open(c, "w").write(harness)
        r = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check("pure block compiles on the host with -Wall -Wextra -Werror", r.returncode == 0, r.stdout[-600:])
        if r.returncode == 0:
            out = dict(l.split(":", 1) for l in subprocess.run([exe], stdout=subprocess.PIPE, universal_newlines=True).stdout.splitlines())
            def rule(fam, op, ifn, t, p):
                return "ip%s rule %s iif %s table %s pref %d" % (" -6" if fam == 6 else "", op, ifn, T(t), p)
            def pair(fam, ifn, t, p):
                return [rule(fam, "del", ifn, t, p), rule(fam, "add", ifn, t, p)]
            def exp(*rules):
                flat = []
                for x in rules: flat += pair(*x)
                return "%d|%s" % (len(rules), "|".join(flat)) if rules else "0"
            cases = [
                ("WireGuard-bound guest (client 1), IPv6 off: one IPv4 rule, pref 1000 + 3n", "wg", exp((4, "br52", 1, vif + 3))),
                ("WireGuard-bound guest with IPv6: the same rule in both families", "wg6", exp((4, "br52", 1, vif + 3), (6, "br52", 1, vif + 3))),
                ("OpenVPN-bound guest (client 6) with IPv6", "ovpn6", exp((4, "br53", 6, vif + 18), (6, "br53", 6, vif + 18))),
                ("main LAN bound to a client: pref 999", "lanbound", exp((4, "br0", 3, dc))),
                ("br0 with the default VPN (client 2), IPv6 on: pref 999 both families", "landflt", exp((4, "br0", 2, dc), (6, "br0", 2, dc))),
                ("br0 with the default VPN, client without an IPv6 route: IPv4 only", "landflt4", exp((4, "br0", 7, dc))),
                ("unbound guest network: nothing", "unbound", "0"),
                ("the default VPN is br0's only: an unbound guest gets nothing", "unbound_dflt", "0"),
                ("a network sharing the main LAN subnet is skipped (as _handle_sdn_wan does)", "samesub", "0"),
                ("an index outside 1-16 adds nothing", "badidx", "0"),
                ("no interface name: nothing", "noif", "0"),
                ("stale matcher: a guest binding rule is matched and deleted in its exact form", "s_guest", rule(6, "del", "br52", 1, vif + 3)),
                ("stale matcher: the same with a trailing space", "s_guest_sp", rule(6, "del", "br52", 1, vif + 3)),
                ("stale matcher: br0's pref-999 rule", "s_lan", rule(6, "del", "br0", 2, dc)),
                ("stale matcher: a rule on a down bridge (`iif br53 [detached] lookup 6`)", "s_det", rule(6, "del", "br53", 6, vif + 18)),
                ("stale matcher: [detached] anywhere else is not the iproute2 shape", "s_det_end", "-"),
                ("stale matcher: [detached] with unknown trailing words is left alone", "s_det_tail", "-"),
                ("stale matcher: br520 is not br52", "s_prefix", "-"),
                ("stale matcher: a pref that is not the binding's own is left alone", "s_pref", "-"),
                ("stale matcher: the kill switch (prohibit) is left alone", "s_ks", "-"),
                ("stale matcher: a Policy Routing fwmark rule is left alone", "s_pbr", "-"),
                ("stale matcher: the main table rule is left alone", "s_main", "-"),
                ("stale matcher: a table that is not a plain number is left alone", "s_junk", "-"),
                ("stale matcher: a table beyond the VPN client range is left alone", "s_big", "-"),
                ("stale matcher: a source-limited rule is left alone", "s_src", "-"),
                ("stale matcher: unknown trailing words are left alone", "s_tail", "-"),
            ]
            for name, key, want in cases:
                check(name, out.get(key) == want, (out.get(key), want))
            check("no generated command carries `prohibit` (kill-switch rules are never touched)",
                  not any("prohibit" in v for v in out.values()))
    finally:
        shutil.rmtree(d, ignore_errors=True)
elif not gcc:
    print("note: gcc not found - the pure block run is skipped")
else:
    check("pure block found for the host run", False)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
