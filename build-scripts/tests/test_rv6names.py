#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IPv6 device names (2026-10-08) - helpers on the host, wiring pinned.

WHY THIS EXISTS. LAN devices ask DNS over IPv6 from SLAAC / privacy addresses the router never
handed out, so dnsmasq has no name for them and a DNS filter (AdGuard) lists them as bare
addresses. rc/rv6names.c maps each LAN neighbour's IPv6 address to its DHCPv4 lease name and writes
"<ipv6> <name>" into /tmp/rv6names/<bridge>/hosts, which that bridge's dnsmasq reads via addn-hosts= (re-read on SIGHUP).
r26 used hostsdir= and took DNS, DHCP and RA down: this dnsmasq is built -DNO_INOTIFY and refuses to
START with it, while `dnsmasq --test` passes it - so the build flags are read from source here.
What must never happen: an IPv4 line (it could take a DHCPv4 lease's name - dnsmasq compares names
per family), a name that also holds a DHCPv6 lease (dnsmasq would refuse that lease its name), an
unsafe name, or a reverse zone that is forwarded (the LAN filter treats the prefix as private and
asks the gateway again - a loop).

WHAT IT DOES. Compiles shared/reaper_v6names.c and shared/reaper_revzone.c on the host and proves
the name filter, the lease-line parser, the renderer and the /64 helper; then pins the wiring:
daemon registered and started, files written atomically and only on change, own-bridge addn-hosts file +
local-only own zone before the .add, cross-network IPv6 lines eligible-only and gated on both
switches, IPv6-off writes nothing, default on, the page switch and its strings in 25 packs, the
markers. Exit 0 pass, 1 fail, 77 skipped."""
import glob, os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)
def die(msg):
    print("FAIL: " + msg); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_v6names.c")):
    skip("no router source tree with shared/reaper_v6names.c (argv[1] or REAPER_ROUTER_SRC)")
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
#include <string.h>
#include "reaper_v6names.h"
#include "reaper_revzone.h"
int main(int argc, char **argv)
{
	int a;
	for (a = 1; a < argc; a++) {
		char *s = argv[a];
		if (!strncmp(s, "name=", 5)) printf("name|%s|%d\n", s + 5, rv6n_name_ok(s + 5));
		else if (!strncmp(s, "lease=", 6)) {
			char mac[18], nm[RV6N_NAME_MAX];
			int k = rv6n_lease_line(s + 6, mac, sizeof(mac), nm, sizeof(nm));
			printf("lease|%d|%s|%s\n", k, mac, nm);
		} else if (!strncmp(s, "net6=", 5)) {
			char o[64]; int r = reaper_rev_net6(s + 5, o, sizeof(o));
			printf("net6|%s|%d|%s\n", s + 5, r, r > 0 ? o : "-");
		}
	}
	{
		struct rv6n_pair p[8];
		char out[1024];
		int n = 0, r;
		strcpy(p[n].addr, "2001:db8:8cd0::20"); strcpy(p[n++].name, "zeta");
		strcpy(p[n].addr, "2001:db8:8cd0::10"); strcpy(p[n++].name, "alpha");
		strcpy(p[n].addr, "192.168.50.5");      strcpy(p[n++].name, "v4line");
		strcpy(p[n].addr, "2001:db8:8cd0::11"); strcpy(p[n++].name, "bad name");
		strcpy(p[n].addr, "2001:db8:8cd0::10"); strcpy(p[n++].name, "alpha");
		strcpy(p[n].addr, "2001:db8:8cd0::9");  strcpy(p[n++].name, "alpha");
		r = rv6n_render(p, n, 10, out, sizeof(out));
		printf("render|%d\n%s", r, out);
		printf("cap|%d\n", rv6n_render(p, n, 1, out, sizeof(out)));
		printf("small|%d\n", rv6n_render(p, n, 10, out, 8));
	}
	{	/* 2026-10-13: the hold table (15 min) and the reload pacing (5 min) */
		struct rv6n_held t[3], f[4];
		int n = 0, i;
		char row[256];
		memset(t, 0, sizeof(t)); memset(f, 0, sizeof(f));
#define F(k, a, nm, s) do { strcpy(f[k].br, "br0"); strcpy(f[k].addr, a); strcpy(f[k].name, nm); f[k].seen = s; } while (0)
#define ROW() do { row[0] = 0; for (i = 0; i < n; i++) { strcat(row, t[i].addr); strcat(row, "="); strcat(row, t[i].name); strcat(row, ","); } } while (0)
		F(0, "2001:db8::1", "alpha", 100); F(1, "2001:db8::2", "beta", 100);
		n = rv6n_hold_merge(t, n, 3, f, 2, 100, 900); ROW(); printf("hold|start|%d|%s\n", n, row);
		n = rv6n_hold_merge(t, n, 3, f, 1, 400, 900); ROW(); printf("hold|gone300|%d|%s\n", n, row);
		n = rv6n_hold_merge(t, n, 3, f, 1, 999, 900); ROW(); printf("hold|gone899|%d|%s\n", n, row);
		n = rv6n_hold_merge(t, n, 3, f, 1, 1000, 900); ROW(); printf("hold|gone900|%d|%s\n", n, row);
		F(0, "2001:db8::1", "gamma", 1060);
		n = rv6n_hold_merge(t, n, 3, f, 1, 1060, 900); ROW(); printf("hold|rename|%d|%s\n", n, row);
		F(0, "2001:db8::1", "gamma", 1120); F(1, "2001:db8::3", "c", 1120); F(2, "2001:db8::4", "d", 1120);
		n = rv6n_hold_merge(t, n, 3, f, 3, 1120, 900); ROW(); printf("hold|full|%d|%s\n", n, row);
		F(0, "2001:db8::5", "e", 1180);
		n = rv6n_hold_merge(t, n, 3, f, 1, 1180, 900); ROW(); printf("hold|evict|%d|%s\n", n, row);
		F(0, "2001:db8::6", "f", 1240); F(1, "2001:db8::7", "g", 1240); F(2, "2001:db8::8", "h", 1240); F(3, "2001:db8::9", "i", 1240);
		n = rv6n_hold_merge(t, n, 3, f, 4, 1240, 900); ROW(); printf("hold|sametick|%d|%s\n", n, row);
		printf("hup|%d|%d|%d|%d|%d|%d\n", rv6n_hup_due(0, 0, 100, 300), rv6n_hup_due(1, 0, 100, 300),
		       rv6n_hup_due(1, 100, 220, 300), rv6n_hup_due(1, 100, 399, 300), rv6n_hup_due(1, 100, 400, 300),
		       rv6n_hup_due(1, 500, 100, 300));
	}
	return 0;
}
'''
td = tempfile.mkdtemp(prefix="v6names-")
try:
    c = os.path.join(td, "t.c"); open(c, "w").write(MAIN)
    exe = os.path.join(td, "t")
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-o", exe, c, os.path.join(SRC, "shared", "reaper_v6names.c"),
                        os.path.join(SRC, "shared", "reaper_revzone.c"), "-I", os.path.join(SRC, "shared")], capture_output=True, text=True)
    if p.returncode != 0: die("host compile failed:\n" + p.stderr)
    if "warning" in p.stderr: die("host compile warnings:\n" + p.stderr)
    check("reaper_v6names.c + reaper_revzone.c compile clean with -Wall -Wextra", True)
    args = ["name=DESKTOP-EXAMPL1", "name=PIHOST1", "name=a", "name=", "name=*", "name=-lead", "name=trail-",
            "name=has.dot", "name=has space", "name=" + "x" * 63, "name=" + "x" * 64,
            "lease=86043 00:00:5E:00:53:AE 10.20.0.98 PIHOST1 ff:5d:cb",
            "lease=86400 34:5a:11:22:33:44 192.168.50.210 * 01:34",
            "lease=duid 00:03:00:01:2e:16:7e:19:47:12",
            "lease=86400 12345 2001:db8:8cd0::50 Laptop 00:01:00:01",
            "lease=86400 zz:5a:11:22:33:44 192.168.50.5 Bad 01",
            "lease=garbage",
            "net6=2001:db8:8cd0:100::4", "net6=2001:db8:8cd0::1", "net6=fe80::1", "net6=ff02::1", "net6=::1",
            "net6=192.168.50.1", "net6=fd12:3456:789a:1::9"]
    out = subprocess.run([exe] + args, capture_output=True, text=True).stdout
    names = {l.split("|")[1]: l.split("|")[2] for l in out.splitlines() if l.startswith("name|")}
    good = ["DESKTOP-EXAMPL1", "PIHOST1", "a", "x" * 63]
    bad = ["", "*", "-lead", "trail-", "has.dot", "has space", "x" * 64]
    check("name filter accepts one DNS label of [A-Za-z0-9-] up to 63", all(names.get(n) == "1" for n in good), names)
    check("name filter refuses empty, *, edge hyphens, dots, spaces, 64 chars", all(names.get(n) == "0" for n in bad), names)
    leases = [l.split("|")[1:] for l in out.splitlines() if l.startswith("lease|")]
    check("DHCPv4 lease -> MAC (lower-case) + name", leases[0] == ["4", "00:00:5e:00:53:ae", "PIHOST1"], leases[0])
    check("a lease with no name (*) is skipped", leases[1][0] == "0", leases[1])
    check("the duid line is skipped", leases[2][0] == "0", leases[2])
    check("DHCPv6 lease -> name only (kept out of the hosts file)", leases[3] == ["6", "", "Laptop"], leases[3])
    check("a malformed MAC and garbage are skipped", leases[4][0] == "0" and leases[5][0] == "0", leases[4:6])
    nets = {l.split("|")[1]: l.split("|")[2:] for l in out.splitlines() if l.startswith("net6|")}
    check("net6: a bridge address -> its /64", nets.get("2001:db8:8cd0:100::4") == ["64", "2001:db8:8cd0:100::/64"]
          and nets.get("2001:db8:8cd0::1") == ["64", "2001:db8:8cd0::/64"] and nets.get("fd12:3456:789a:1::9") == ["64", "fd12:3456:789a:1::/64"], nets)
    check("net6: link-local, multicast, loopback and IPv4 are refused",
          all(nets.get(k, ["x"])[0] == "-1" for k in ("fe80::1", "ff02::1", "::1", "192.168.50.1")), nets)
    lines = out.split("render|", 1)[1].splitlines()
    check("render: IPv6 only, valid names only, sorted by name then address, duplicates dropped",
          lines[0] == "3" and lines[1:4] == ["2001:db8:8cd0::10 alpha", "2001:db8:8cd0::9 alpha", "2001:db8:8cd0::20 zeta"], lines[:5])
    tail = dict(l.split("|") for l in out.splitlines() if l.startswith(("cap|", "small|")))
    check("render: the cap holds and a too-small buffer yields nothing (-1), never half a file", tail.get("cap") == "1" and tail.get("small") == "-1", tail)
    # 2026-10-13: hold table + reload pacing (dnsmasq's SIGHUP empties its whole cache)
    hold = {l.split("|")[1]: l.split("|")[2:] for l in out.splitlines() if l.startswith("hold|")}
    check("hold: a departed address keeps its name under 900 s (seen 300 s and 899 s ago)",
          hold.get("gone300") == ["2", "2001:db8::1=alpha,2001:db8::2=beta,"] and hold.get("gone899", ["0"])[0] == "2", hold)
    check("hold: at 900 s it leaves", hold.get("gone900") == ["1", "2001:db8::1=alpha,"], hold.get("gone900"))
    check("hold: an address that now carries another name takes it at once", hold.get("rename") == ["1", "2001:db8::1=gamma,"], hold.get("rename"))
    ev = hold.get("evict", ["", ""])
    check("hold: the table never exceeds its cap; a newcomer replaces the entry seen longest ago",
          hold.get("full", ["0"])[0] == "3" and ev[0] == "3" and "2001:db8::5=e" in ev[1] and "2001:db8::1=gamma" not in ev[1],
          (hold.get("full"), ev))
    check("hold: a table full of pairs seen this tick drops the extra newcomer, not a live pair",
          hold.get("sametick", ["0", ""])[0] == "3"
          and sorted(hold.get("sametick", ["0", ""])[1].strip(",").split(",")) == ["2001:db8::6=f", "2001:db8::7=g", "2001:db8::8=h"], hold.get("sametick"))
    hup = [l.split("|")[1:] for l in out.splitlines() if l.startswith("hup|")]
    check("pacing: nothing pending -> no signal; first change -> at once; +120 s and +299 s -> wait; +300 s -> signal; clock back -> signal",
          hup == [["0", "1", "0", "0", "1", "1"]], hup)
finally:
    shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- wiring
d = read("rc/rv6names.c"); sdn = read("rc/sdn.c"); svc = read("rc/services.c")
check("daemon: gate = switch AND IPv6 AND router mode; idles otherwise",
      'nvram_get_int("reaper_dns_v6names") == 1 && ipv6_enabled() && is_routing_enabled()' in d)
check("daemon: reads the shared neighbour cache and every dnsmasq lease file",
      "reaper_nd_load(nd, V6N_ND_MAX)" in d and 'opendir("/var/lib/misc")' in d and "rv6n_lease_line(" in d)
check("daemon: skips non-global neighbours and DHCPv6-lease names",
      "!reaper_nd_global(nd[i].ip)" in d and "is_v6lease_name(held[i].name, n6)" in d)
check("daemon: writes only on change, atomically - temp created 0600, opened to 0644 only when complete (2026-10-09 audit V3)",
      "if (!strcmp(curbuf, content))" in d and "reaper_write_atomic(path, content, strlen(content), 0644)" in d and 'fopen(tmp, "w")' not in d)
check("daemon: switch off or IPv6 off empties every file", "if (!on)\n\t\t\t\tclear_all();" in d)
check("applet registered, built, linked and started/stopped beside rdnshc",
      '{ "rv6names",' in read("rc/rc.c") and "OBJS += rv6names.o" in read("rc/Makefile") and "ln -sf rc rv6names" in read("rc/Makefile")
      and "start_rv6names();" in svc and "stop_rv6names();" in svc and 'strcmp(script, "rv6names") == 0' in svc)
check("instances: own-bridge addn-hosts file (created first) + local-only own /64 (address-less rev-server)",
      'fprintf(fp, "addn-hosts=%s\\n", hf);' in sdn and "open(hf, O_WRONLY | O_CREAT | O_NOFOLLOW, 0644)" in sdn and 'fprintf(fp, "rev-server=%s\\n", net);' in sdn)
i_main = svc.find("write_v6names_main(fp);"); i_add = svc.find('append_custom_config("dnsmasq.conf",fp);')
check("main instance: IPv6 names written before dnsmasq.conf.add", 0 < i_main < i_add)
i_sdn = sdn.find("write_v6names_sdn(fp, pmtl);"); i_sadd = sdn.find('snprintf(buf, sizeof(buf), "dnsmasq-%d.conf", pmtl->sdn_t.sdn_idx);\n\t\tappend_custom_config(buf, fp);')
check("VLAN instance: IPv6 names written before dnsmasq-<idx>.conf.add", 0 < i_sdn < i_sadd)
check("cross-network IPv6 lines: eligible networks only, both switches, never VLAN to VLAN",
      "revshare_eligible(&pmtl[i]) && br_v6_net(pmtl[i].nw_t.ifname, net, sizeof(net))" in sdn
      and "revshare_on() && revshare_eligible(self) && br_v6_net(nvram_safe_get(\"lan_ifname\")" in sdn)
check("IPv6 off writes nothing", 'return nvram_get_int("reaper_dns_v6names") == 1 && ipv6_enabled();' in sdn
      and sdn.count("!v6names_on()") >= 2)
check("the /64s join the r24 signature (a prefix change restarts the resolvers)", '"on=%d v6=%d lan=%s/%s %s"' in sdn)
check("off at factory in defaults.c (owner 2026-10-12; was on)", '{ "reaper_dns_v6names", "0", CKN_STR1' in read("shared/defaults.c"))
# r26 outage guard: options this dnsmasq build refuses at START (not at --test)
top = read("Makefile")
noinot = "-DNO_INOTIFY" in top
emit = read("rc/sdn.c") + read("rc/services.c") + d
check("dnsmasq is built -DNO_INOTIFY here, and no Reaper config writer emits hostsdir= / dhcp-hostsdir= / dhcp-optsdir=",
      (not noinot) or not any(('"%s=' % o) in emit or ('\n%s=' % o) in emit for o in ("hostsdir", "dhcp-hostsdir", "dhcp-optsdir")),
      "NO_INOTIFY=%s" % noinot)
# 2026-10-13: dnsmasq's SIGHUP empties its whole DNS cache, so the old "every instance on any change"
# (reload_dnsmasq(ALL_SDN), once per tick) emptied every cache every 1-3 minutes (owner's _r7 syslog)
check("reload: only the instance whose file changed - LAN_IN_SDN_IDX for lan_ifname, the SDN index for its bridge, never ALL_SDN",
      "ALL_SDN" not in d and "reload_dnsmasq(LAN_IN_SDN_IDX);" in d and 'if (!strcmp(br, nvram_safe_get("lan_ifname")))' in d
      and "if (!strcmp(pmtl[i].nw_t.ifname, br)) {\n\t\t\t\treload_dnsmasq(pmtl[i].sdn_t.sdn_idx);" in d)
check("reload: a rewritten file marks its bridge pending; signals are paced (300 s, on uptime); the hold is 900 s",
      "#define V6N_HOLD\t900" in d and "#define V6N_MIN_HUP\t300" in d and "bst[k].pending = 1;" in d
      and "rv6n_hup_due(bst[k].pending, bst[k].last, now, V6N_MIN_HUP)" in d and "long now = up_s();" in d
      and "sysinfo(&si)" in d and "time(NULL)" not in d)
check("reload: the file is built from the hold table, folded every tick",
      "nheld = rv6n_hold_merge(held, nheld, V6N_ND_MAX, fresh, nf, now, V6N_HOLD);" in d)
check("reload: switch-off withdraws names at once and resets the pacing",
      "if (e->d_name[0] != '.' && put_file(e->d_name, \"\"))\n\t\t\tv6n_reload_br(e->d_name);" in d
      and "nheld = 0;" in d and "bst[i].last = 0;" in d)
pg = read("www/Reaper_Failover.asp")
check("DNS Failover page: the switch, saved, restarting rv6names + dnsmasq, a note while IPv6 is off",
      'id="v6names"' in pg and "reaper_dns_v6names: on('v6names')" in pg and "svc += 'restart_rv6names;'" in pg
      and "$id('v6names_off').style.display = ''" in pg)
packs = [x for x in glob.glob(os.path.join(SRC, "www", "*.dict")) if not x.endswith("temp.dict")]
miss = [os.path.basename(x) for x in packs if any(("RDHC_%d=" % k) not in open(x, encoding="utf-8", errors="replace").read() for k in (56, 57, 58))]
check("RDHC_56..58 exist in all 25 language packs", len(packs) == 25 and not miss, miss)
here = os.path.dirname(os.path.abspath(__file__))
mp = os.path.join(here, "..", "verify_markers.txt")
if os.path.isfile(mp):
    m = open(mp, encoding="utf-8").read()
    check("verify_markers pins the daemon and the addn-hosts emitter in the staged rc",
          "sbin/rc|IPv6 device names on - |1" in m and "sbin/rc|addn-hosts=%s|1" in m and "sbin/rc|hostsdir=" not in m)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("all checks passed: IPv6 device names - IPv6 lines only, no DHCPv6 name clash, atomic writes, local zones, gated")
