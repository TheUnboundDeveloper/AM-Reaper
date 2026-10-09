#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reverse DNS across networks (2026-10-08) - helper on the host, wiring pinned.

WHY THIS EXISTS. Each dnsmasq instance answers PTR lookups only for its own leases, and with
bogus-priv on it answers NXDOMAIN for every other private range, so a DNS filter on a VLAN could
not name main-LAN devices (the owner's AdGuard on VLAN 52) and the main LAN could not name VLAN
ones. rc/sdn.c now gives the main instance one rev-server line per eligible VLAN and each eligible
VLAN instance one line for the main LAN. Owner decisions: main LAN <-> each VLAN only (never VLAN
<-> VLAN), Guest / Portal / captive-portal networks excluded, a switch that defaults to on, and
every instance refreshed when the set of networks changes.

WHAT IT DOES. Compiles shared/reaper_revzone.c on the host and proves the <net>/<len> conversion
(contiguous masks only, no /0, the network address not the gateway); then pins the wiring: the
policy, both emitters before their custom .add append, the switch and dns_fwd_local gates, the
change signature and the restart in both SDN service branches, the default, the page switch and
its strings in all 25 packs, and the markers. Exit 0 pass, 1 fail, 77 skipped."""
import glob, os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_revzone.c")):
    skip("no router source tree with shared/reaper_revzone.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
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
#include "reaper_revzone.h"
int main(int argc, char **argv)
{
	int a; char out[32];
	for (a = 1; a + 1 < argc; a += 2) {
		int r = reaper_rev_net(argv[a], argv[a + 1], out, sizeof(out));
		printf("%s|%s|%d|%s\n", argv[a], argv[a + 1], r, r > 0 ? out : "-");
	}
	{ char tiny[8]; printf("tiny|%d\n", reaper_rev_net("10.20.0.1", "255.255.255.0", tiny, sizeof(tiny))); }
	printf("null|%d\n", reaper_rev_net(NULL, "255.0.0.0", out, sizeof(out)));
	return 0;
}
'''
td = tempfile.mkdtemp(prefix="revzone-")
try:
    c = os.path.join(td, "t.c"); open(c, "w").write(MAIN)
    exe = os.path.join(td, "t")
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-o", exe, c, os.path.join(SRC, "shared", "reaper_revzone.c"),
                        "-I", os.path.join(SRC, "shared")], capture_output=True, text=True)
    if p.returncode != 0:
        die("host compile failed:\n" + p.stderr)
    if "warning" in p.stderr:
        die("host compile warnings:\n" + p.stderr)
    check("shared/reaper_revzone.c compiles clean with -Wall -Wextra", True)
    cases = [("10.20.0.1", "255.255.255.0", "24", "10.20.0.0/24"),
             ("192.168.50.1", "255.255.255.0", "24", "192.168.50.0/24"),
             ("172.16.5.1", "255.255.0.0", "16", "172.16.0.0/16"),
             ("10.20.1.1", "255.255.254.0", "23", "10.20.0.0/23"),
             ("10.20.0.9", "255.255.255.252", "30", "10.20.0.8/30"),
             ("10.20.0.9", "255.255.255.255", "32", "10.20.0.9/32"),
             ("10.20.0.1", "255.0.255.0", "-1", "-"),
             ("10.20.0.1", "0.0.0.0", "-1", "-"),
             ("10.20.0", "255.255.255.0", "-1", "-"),
             ("garbage", "255.255.255.0", "-1", "-"),
             ("10.20.0.1", "", "-1", "-")]
    args = []
    for a, m, _, _ in cases: args += [a, m]
    r = subprocess.run([exe] + args, capture_output=True, text=True)
    got = {tuple(l.split("|")[:2]): l.split("|")[2:] for l in r.stdout.splitlines() if l.count("|") == 3}
    for a, m, ln, net in cases:
        check("rev net %s %s -> %s %s" % (a, m or "''", ln, net), got.get((a, m)) == [ln, net], got.get((a, m)))
    extra = dict(l.split("|") for l in r.stdout.splitlines() if l.count("|") == 1)
    check("a too-small buffer and a NULL address are refused", extra.get("tiny") == "-1" and extra.get("null") == "-1", extra)
finally:
    shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- wiring
sdn = read("rc/sdn.c"); svc = read("rc/services.c"); sh = read("shared/shared.h"); mk = read("shared/Makefile")
check("libshared builds the helper and shared.h exposes it",
      "OBJS += reaper_revzone.o" in mk and '#include "reaper_revzone.h"' in sh)
check("policy: enabled, has its own dnsmasq, not the main subnet, not Guest/Portal, no captive portal",
      "static int revshare_eligible(const MTLAN_T *m)" in sdn and 'strcasecmp(m->name, "Guest")' in sdn
      and 'strcasecmp(m->name, "Portal")' in sdn and "m->sdn_t.cp_idx != 0" in sdn
      and 'strcmp(m->nw_t.addr, nvram_safe_get("lan_ipaddr"))' in sdn and "m->nw_t.idx == 0" in sdn)
check("gates: the switch and dns_fwd_local",
      'nvram_get_int("reaper_dns_revshare") == 1 && nvram_get_int("dns_fwd_local") != 1' in sdn)
i_sdn_emit = sdn.find("write_rev_servers_sdn(fp, pmtl);")
i_sdn_add = sdn.find('snprintf(buf, sizeof(buf), "dnsmasq-%d.conf", pmtl->sdn_t.sdn_idx);\n\t\tappend_custom_config(buf, fp);')
check("VLAN instance: main-LAN line written before its dnsmasq-<idx>.conf.add, only when the VLAN is eligible",
      0 < i_sdn_emit < i_sdn_add and "!revshare_eligible(self)" in sdn)
check("VLAN instance gets the MAIN LAN only - no VLAN-to-VLAN lines",
      sdn.count("rev-server=%s,%s") == 4		# IPv4 main/VLAN + (2026-10-08) IPv6 main/VLAN
      and 'reaper_rev_net(lip, nvram_safe_get("lan_netmask")' in sdn
      and 'br_v6_net(nvram_safe_get("lan_ifname"), net, sizeof(net))' in sdn)
i_main_emit = svc.find("write_rev_servers_main(fp);")
i_main_add = svc.find('append_custom_config("dnsmasq.conf",fp);')
check("main instance: VLAN lines written before dnsmasq.conf.add", 0 < i_main_emit < i_main_add)
check("start_dnsmasq records the signature after writing the main config",
      svc.find('use_custom_config("dnsmasq.conf","/etc/dnsmasq.conf");') < svc.find("revshare_sig_save();"))
n_restart = svc.count('if ((action & RC_SERVICE_START) && revshare_sig_changed()) {') + svc.count('if (revshare_sig_changed()) {')
check("restart_sdn and sdn_del restart dnsmasq once when the network set changed",
      n_restart == 2 and svc.count('notify_rc("restart_dnsmasq");') >= 2)
check("default on in defaults.c", '{ "reaper_dns_revshare", "1", CKN_STR1' in read("shared/defaults.c"))
pg = read("www/Reaper_Failover.asp")
check("DNS Failover page has the switch, saves it, and restarts dnsmasq when it changes",
      'id="revshare"' in pg and 'nvram_match("reaper_dns_revshare", "1", "checked")' in pg
      and "reaper_dns_revshare: on('revshare')" in pg and "v.reaper_dns_revshare !== ORIG.revshare" in pg and "svc += 'restart_dnsmasq;'" in pg)
packs = [x for x in glob.glob(os.path.join(SRC, "www", "*.dict")) if not x.endswith("temp.dict")]
miss = [os.path.basename(x) for x in packs if any(("RDHC_%d=" % k) not in open(x, encoding="utf-8", errors="replace").read() for k in (53, 54, 55))]
check("RDHC_53..55 exist in all 25 language packs", len(packs) == 25 and not miss, miss)
here = os.path.dirname(os.path.abspath(__file__))
mp = os.path.join(here, "..", "verify_markers.txt")
if os.path.isfile(mp):
    m = open(mp, encoding="utf-8").read()
    check("verify_markers pins the emitter and the restart line in the staged rc",
          "sbin/rc|rev-server=%s,%s|1" in m and "sbin/rc|so each one can name the others' devices|1" in m)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("all checks passed: main LAN and each eligible VLAN name each other's devices, guests never, kept current on change")
