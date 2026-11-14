#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal DNS: the guest resolver, its names and its upstream (owner decisions 2026-11-13).

WHY THIS EXISTS. Owner: guests must not look up bad or inappropriate things, and must stay isolated from the main
network. Found the same day: (1) a signed-in portal guest's DNS went wherever the guest sent it (DNS Director only
covers br* interfaces; portal traffic arrives on tun22) - fixed in rc/reaper_guest.c, tested by
test_guest_isolation.py; (2) every guest resolver read the router's hosts file, which lists every DHCP reservation by
name and address, so a guest could look up the owner's devices; (3) the guest resolver forwarded to the main
upstream - owner chose Cloudflare for Families, encrypted, for Guest Portal networks.

WHAT IT DOES. Compiles the REAPER-GUESTDNS-PURE block on the host and runs it: which networks hide main-LAN names
(no intranet access and not on the main subnet), which get the family forwarder (portal, no VPN binding, own
resolver), the forwarder's listen address, and its stubby config (TLS only; certificate required once the clock is
set; Cloudflare for Families on 853 by name; IPv6 servers only with IPv6). Then pins the wiring: `no-hosts` /
`server=` in the resolver config, the forwarder started before and stopped with the resolver and with a removed
network, its own process name, the watchdog call, the declarations.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "sdn.c")):
    print("SKIP: no router tree with rc/sdn.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="latin-1").read()

sdn, wd, rch, gst = read("rc/sdn.c"), read("rc/watchdog.c"), read("rc/rc.h"), read("rc/reaper_guest.c")

# ---- pins
check("exactly one REAPER-GUESTDNS block", sdn.count("/* REAPER-GUESTDNS-PURE-BEGIN") == 1
      and sdn.count("\nvoid reaper_guest_dot_watch(void)\n") == 1, sdn.count("/* REAPER-GUESTDNS-PURE-BEGIN"))
m = re.search(r"\nstatic int _gen_sdn_dnsmasq_conf\([^;{]*?\)\n\{.*?\n\}\n", sdn, re.S)
gen = m.group(0) if m else ""
check("guest resolver config found", bool(gen))
check("a network without intranet access gets no-hosts; ahs_sw's hosts file only otherwise",
      "\t\tif (reaper_sdn_hide_lan_names(pmtl))\t/* 2026-11-13 (owner): REAPER-GUESTDNS */\n\t\t\tfprintf(fp, \"no-hosts\\n\");\n"
      "\t\telse if(pmtl->sdn_t.ahs_sw)\n\t\t\tfprintf(fp, \"addn-hosts=/etc/hosts\\n\");\n" in gen)
check("a portal without VPN: its own forwarder (default / known DoT provider) or the admin's own server(s) as plain DNS; "
      "every other network keeps its servers file",
      "int gn, gi, gm = reaper_guest_dns_mode(pmtl, gu, &gn);" in gen
      and "if (gm == RGD_DEFAULT || gm == RGD_DOT) {" in gen and "fprintf(fp, \"server=%s\\n\", ga);" in gen
      and "} else if (gm == RGD_PLAIN) {" in gen and "fprintf(fp, \"server=%s\\n\", gu[gi].addr);" in gen
      and "\t\t\t} else\n\t\t\t\tfprintf(fp, \"servers-file=%s\\n\", resolv_flag ? resolv_path : dmservers);\n" in gen)
check("the guest upstream follows the network's own DNS Server setting (nw_t.dns[0..1])",
      "return rgd_pick(m->nw_t.dns[0], m->nw_t.dns[1], u, n);" in sdn)
check("an encrypted forwarder only for the default or a known DoT provider (an admin's plain server needs none)",
      "return md == RGD_DEFAULT || md == RGD_DOT;" in sdn)
check("the default adds Cloudflare's IPv6 pair when IPv6 is on",
      "if (reaper_guest_dns_mode(m, ups, &nup) == RGD_DEFAULT && ipv6_enabled()) {" in sdn and "2606:4700:4700::1113" in sdn)
sj_p = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js")
sj = open(sj_p, encoding="latin-1").read() if os.path.isfile(sj_p) else ""
check("Network page: a note under DNS Server on portal networks only, from the RGPD_1 token",
      "_profile_data.sdn_rl.cp_idx != \"0\")" in sj and ".html(`<#RGPD_1#>`).insertAfter($(_obj).find(\"#dns\").closest(\".profile_setting_item\"));" in sj
      and sj.count("$(_obj).find(\"#dns_portal_note\").remove();") == 1)
import json as _json
_dot_p = os.path.join(SRC, "www", "dot-servers.json")
if os.path.isfile(_dot_p):
    _dot = {}
    for _it in _json.load(open(_dot_p, encoding="utf-8-sig")).get("IPv4", []):
        _dot.setdefault(_it.get("dnspriv_server"), set()).add(_it.get("dnspriv_hostname"))
    _tbl = re.findall(r'\{ "([0-9.]+)", "([0-9.]+)", "([a-z0-9.-]+)" \}', sdn)
    _bad = [(p, d, h) for p, d, h in _tbl if d in _dot and h not in _dot[d]]
    _cf = [(p, d, h) for p, d, h in _tbl if d not in _dot and not h.endswith("cloudflare-dns.com")]
    check("every DoT name in the provider table matches the firmware's own dot-servers.json (Cloudflare's filtered pair aside)",
          len(_tbl) >= 20 and not _bad and not _cf, (_bad, _cf, len(_tbl)))
import glob as _g
_packs = [p for p in _g.glob(os.path.join(SRC, "www", "*.dict")) if not p.endswith("temp.dict")]
_miss = [os.path.basename(p) for p in _packs if not re.search(r"^RGPD_1=\S", open(p, encoding="utf-8").read(), re.M)]
check("RGPD_1 in all %d packs" % len(_packs), _packs and not _miss, _miss)
h = re.search(r"\nstatic int _handle_sdn_dnsmasq\([^;{]*?\)\n\{.*?\n\}\n", sdn, re.S)	# the definition, not the prototype
hd = h.group(0) if h else ""
check("the forwarder is started before the resolver and stopped with it",
      hd.find("reaper_guest_dot_start(pmtl);") >= 0 and hd.find("reaper_guest_dot_start(pmtl);") < hd.find("_gen_sdn_dnsmasq_conf(")
      and "kill_pidfile_tk(config_path);\n\t\treaper_guest_dot_stop(pmtl->sdn_t.sdn_idx);" in hd)
check("a removed network's forwarder goes too", "kill_pidfile_tk(path);\n\t\treaper_guest_dot_stop(pmtl[i].sdn_t.sdn_idx);" in sdn)
check("its own process name (a link to stubby): stock killall / pids(\"stubby\") leave it alone",
      '#define RGD_EXE\t\tRGD_DIR "/rgdot"' in sdn and 'symlink("/usr/sbin/stubby", RGD_EXE)' in sdn
      and 'alive = !strncmp(comm, "rgdot", 5);' in sdn)
check("the watchdog checks the forwarders every pass (not tied to the main DoT switch)",
      "\treaper_guest_dot_watch();" in wd
      and wd.find("reaper_guest_dot_watch();") < wd.find('if (nvram_get_int("dnspriv_enable") && !pids("stubby")) {'))
check("...and restarts a dead one, or one started before the clock was set",
      "if (!alive || (unauth && nvram_get_int(\"ntp_ready\") == 1)) {" in sdn)
check("declared in rc.h; intranet access read through the isolation layer's own parser",
      "extern int reaper_guest_intranet(int sdn_idx);" in rch and "extern void reaper_guest_dot_watch(void);" in rch
      and 'return rg_access_on(nvram_safe_get("sdn_access_rl"), sdn_idx);' in gst)

# ---- the pure block, compiled and run
blk = re.search(r"/\* REAPER-GUESTDNS-PURE-BEGIN.*?\*/(.*?)/\* REAPER-GUESTDNS-PURE-END \*/", sdn, re.S)
CC = shutil.which("gcc") or shutil.which("cc")
if blk and not CC:
    print("SKIP (part): no host C compiler - the block was not run")
elif blk:
    prog = r'''
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
''' + blk.group(1) + r'''
static void pick(const char *tag, const char *a, const char *b)
{
	struct rgd_up u[4]; int n = 0, i, m = rgd_pick(a, b, u, &n);
	printf("pick-%s %d", tag, m);
	for (i = 0; i < n; i++) printf(" %s/%s", u[i].addr, u[i].host ? u[i].host : "-");
	printf("\n");
}
int main(int argc, char **argv)
{
	char a[24];
	struct rgd_up dflt[4] = { { "1.1.1.3", RGD_HOST }, { "1.0.0.3", RGD_HOST }, { "2606:4700:4700::1113", RGD_HOST }, { "2606:4700:4700::1003", RGD_HOST } };
	if (argc > 1 && !strcmp(argv[1], "conf0")) { rgd_conf(stdout, "127.0.2.4", 0, dflt, 2); return 0; }
	if (argc > 1 && !strcmp(argv[1], "conf1")) { rgd_conf(stdout, "127.0.2.4", 1, dflt, 4); return 0; }
	if (argc > 1 && !strcmp(argv[1], "confplain")) { struct rgd_up p[1] = { { "192.168.50.5", NULL } }; rgd_conf(stdout, "127.0.2.4", 1, p, 1); return 0; }
	pick("empty", "", "");
	pick("null", NULL, NULL);
	pick("cbfamily", "185.228.168.168", "185.228.169.168");
	pick("quad9one", "9.9.9.9", "");
	pick("controld", "76.76.2.4", "76.76.10.4");
	pick("controldsame", "76.76.2.1", "76.76.2.1");
	pick("pihole", "192.168.50.5", "");
	pick("mixed", "9.9.9.9", "192.168.50.5");
	pick("junk", "not.an.ip", "");
	pick("dup", "192.168.50.5", "192.168.50.5");
	printf("hide %d %d %d %d %d %d\n", rgd_hide("br55", "br0", 0), rgd_hide("br55", "br0", 1), rgd_hide("br0", "br0", 0),
	       rgd_hide("", "br0", 0), rgd_hide(NULL, "br0", 0), rgd_hide("br56", "", 0));
	printf("want %d %d %d %d %d\n", rgd_wanted(1, 2, 0, 3), rgd_wanted(1, 2, 7, 3), rgd_wanted(1, 0, 0, 3),
	       rgd_wanted(0, 2, 0, 3), rgd_wanted(1, 2, 0, 0));
	rgd_addr(4, a, sizeof(a)); printf("addr %s", a); rgd_addr(0, a, sizeof(a)); printf(" %s", a);
	rgd_addr(300, a, sizeof(a)); printf(" %s\n", a);
	return 0;
}
'''
    tmp = tempfile.mkdtemp()
    try:
        c, exe = os.path.join(tmp, "t.c"), os.path.join(tmp, "t")
        open(c, "w", encoding="latin-1").write(prog)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("the pure block compiles clean (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr[-600:])
        if r.returncode == 0:
            run = lambda *a: subprocess.run([exe] + list(a), capture_output=True, text=True, timeout=30).stdout
            o = run()
            print(o, end="")
            check("names hidden: own subnet without intranet access only (not with access, not on the main subnet)",
                  "hide 1 0 0 0 0 1" in o, o)
            check("family forwarder: enabled portal, no VPN binding, own resolver - nothing else", "want 1 0 0 0 0" in o, o)
            check("listen address per network on loopback, out-of-range clamped", "addr 127.0.2.4 127.0.2.254 127.0.2.254" in o, o)
            c0, c1 = run("conf0"), run("conf1")
            check("forwarder: TLS only, before the clock is set too (encrypted, certificate not yet checkable)",
                  "dns_transport_list:\n  - GETDNS_TRANSPORT_TLS\ntls_authentication: GETDNS_AUTHENTICATION_NONE\n" in c0
                  and "TRANSPORT_UDP" not in c0 and "TRANSPORT_TCP" not in c0, c0)
            check("forwarder: certificate required once the clock is set", "tls_authentication: GETDNS_AUTHENTICATION_REQUIRED\n" in c1, c1)
            check("forwarder listens on its own loopback address only", "listen_addresses:\n  - 127.0.2.4@53\n" in c0)
            up = re.findall(r"  - address_data: (\S+)\n    tls_port: 853\n    tls_auth_name: \"family.cloudflare-dns.com\"\n", c1)
            check("upstreams written as given, each by name on 853",
                  up == ["1.1.1.3", "1.0.0.3", "2606:4700:4700::1113", "2606:4700:4700::1003"]
                  and re.findall(r"address_data: (\S+)", c0) == ["1.1.1.3", "1.0.0.3"], (up, c0))
            check("a plain (admin's own) server is never written as a DoT upstream",
                  "address_data" not in run("confplain"), run("confplain"))
            P = lambda tag: next((l for l in o.splitlines() if l.startswith("pick-" + tag + " ")), "")
            check("DNS Server empty: Cloudflare for Families over DoT (the default)",
                  P("empty") == "pick-empty 1 1.1.1.3/family.cloudflare-dns.com 1.0.0.3/family.cloudflare-dns.com"
                  and P("null").startswith("pick-null 1 "), (P("empty"), P("null")))
            check("a known provider (CleanBrowsing Family preset): that provider over DoT, its own name",
                  P("cbfamily") == "pick-cbfamily 2 185.228.168.168/family-filter-dns.cleanbrowsing.org 185.228.169.168/family-filter-dns.cleanbrowsing.org", P("cbfamily"))
            check("one address set: just that one", P("quad9one") == "pick-quad9one 2 9.9.9.9/dns.quad9.net", P("quad9one"))
            check("Control D: the plain preset addresses map to its DoT service (.11, profile in the name)",
                  P("controld") == "pick-controld 2 76.76.2.11/family.freedns.controld.com 76.76.10.11/family.freedns.controld.com", P("controld"))
            check("... and the same address twice is one upstream", P("controldsame") == "pick-controldsame 2 76.76.2.11/p1.freedns.controld.com", P("controldsame"))
            check("an admin's own server (a LAN Pi-hole): plain DNS to it", P("pihole") == "pick-pihole 3 192.168.50.5/-", P("pihole"))
            check("a known provider with an own server: both as plain DNS (one transport per forwarder)",
                  P("mixed") == "pick-mixed 3 9.9.9.9/- 192.168.50.5/-", P("mixed"))
            check("not an address: ignored (the default applies)", P("junk").startswith("pick-junk 1 "), P("junk"))
            check("the same own server twice: one line", P("dup") == "pick-dup 3 192.168.50.5/-", P("dup"))
            check("ordered primary + standby, not round-robin", "round_robin_upstreams: 0\n" in c0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
else:
    check("REAPER-GUESTDNS-PURE block present", False)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
