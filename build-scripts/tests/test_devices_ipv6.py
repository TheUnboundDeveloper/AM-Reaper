#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Devices page's IPv6 side (IPv6 remediation 2026-10-07, finding A3) - parser on the host, wiring pinned.

WHY THIS EXISTS. Until this pass the Devices page had no IPv6 at all: an IPv6-only client was
"No lease" and a DHCPv6 lease line (which names the address and a DUID, never a MAC) was
silently skipped by the lease reader. The fix adds a neighbour-cache pass, a DHCPv6 lease
bridge, an ip6 column, and DHCPv6 reservations kept as "<MAC>::suffix" records in a /jffs
list (the nvram cap rule) that dnsmasq receives as dhcp-host=<MAC>,[::suffix]. The record
parser is shared by httpd (the page's read-modify-write and the backup import) and rc (the
dnsmasq emitter), so a slip there would corrupt reservations on every boot with a green build.

WHAT IT DOES. Compiles shared/reaper_dhcp6.c on the host behind a small main and asserts the
suffix validator (:: + one to four hex groups, nothing else) and the record walker (MAC
canonicalised upper-case, suffix lower-case, malformed records skipped, both halves bounded);
then pins the wiring: struct rdev carries ip6/resv6, the collector reads the neighbour cache
and bridges DHCPv6 lease lines through it, nolease excludes IPv6-only clients, the JSON emits
ip6/v6only/resv6, the CGI has set_reserve6/unpin6 behind the existing gate, the backup flags
carry rdev_dhcp6 with the printable charset + structural rewrite, services.c emits the
dhcp-host lines for the main LAN under RTCONFIG_IPV6, the page shows the address, chips
IPv6-only, pins/unpins with a validated suffix, exports an ipv6 column, every RDEV/RDEVE
token it uses exists in all 25 dictionaries, and the markers pin the staged binaries.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - argv[1] or REAPER_ROUTER_SRC)."""
import glob, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_dhcp6.c")):
    skip("no router source tree with shared/reaper_dhcp6.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
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
#include "reaper_dhcp6.h"
static void cb(const char *mac, const char *sfx, void *arg) { (void)arg; printf("rec %s %s\n", mac, sfx); }
int main(int argc, char **argv)
{
	int a;
	for (a = 1; a < argc; a++) {
		if (!strncmp(argv[a], "--sfx=", 6)) printf("sfx %s %d\n", argv[a] + 6, reaper_dhcp6_sfx_valid(argv[a] + 6));
		else if (!strncmp(argv[a], "--walk=", 7)) printf("walk %d\n", reaper_dhcp6_walk(argv[a] + 7, cb, NULL));
	}
	return 0;
}
'''
td = tempfile.mkdtemp(prefix="dhcp6-")
try:
    csrc = os.path.join(td, "t.c")
    with open(csrc, "w") as f:
        f.write(MAIN)
    exe = os.path.join(td, "t")
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-o", exe, csrc, os.path.join(SRC, "shared", "reaper_dhcp6.c"),
                        "-I", os.path.join(SRC, "shared")], capture_output=True, text=True)
    if p.returncode != 0:
        die("host compile failed:\n" + p.stderr)
    if "warning" in p.stderr:
        die("host compile warnings:\n" + p.stderr)
    check("shared/reaper_dhcp6.c compiles clean with -Wall -Wextra", True)

    def run(args):
        r = subprocess.run([exe] + args, capture_output=True, text=True)
        if r.returncode != 0:
            die("test binary failed: %s %s" % (r.stdout, r.stderr))
        return r.stdout.splitlines()

    good = ["::10", "::1", "::ffff", "::1a2b:3c4d", "::1:2:3:4", "::A", "::dead:beef:cafe:1"]
    bad = ["", "::", ":10", "10", "::10:", "::1:2:3:4:5", "::12345", "::g1", "::1::2", "2001:db8::1", "::1 ", "::-1", ":::1"]
    out = run(["--sfx=" + s for s in good + bad])
    # the suffix may be empty or carry a trailing blank, so split from the right
    res = dict(tuple(l[4:].rsplit(" ", 1)) for l in out if l.startswith("sfx "))
    check("suffix validator accepts :: plus one to four hex groups", all(res.get(s) == "1" for s in good), res)
    check("suffix validator refuses empty, bare ::, missing ::, a 5th group, a 5-digit group, non-hex, double ::, a full address, a trailing blank",
          all(res.get(s, "0") == "0" for s in bad), res)

    lst = "<aa:bb:cc:dd:ee:01>::10<AA:BB:CC:DD:EE:02>::1A2B:3c4d<zz:bb:cc:dd:ee:03>::11<aa:bb:cc:dd:ee:04>::12345<aa:bb:cc:dd:ee:05><aa:bb:cc:dd:ee:06>::6<00:00:00:00:00:00>::7<aa:bb:cc:dd:ee:07"
    out = run(["--walk=" + lst])
    recs = [l[4:] for l in out if l.startswith("rec ")]
    n = [l for l in out if l.startswith("walk ")]
    check("walker: MACs canonicalised upper-case, suffixes lower-case",
          recs[:2] == ["AA:BB:CC:DD:EE:01 ::10", "AA:BB:CC:DD:EE:02 ::1a2b:3c4d"], recs)
    check("walker: a bad MAC, a bad suffix, an empty suffix, the all-zero MAC and a record without '>' are skipped; the good one after them is kept",
          recs == ["AA:BB:CC:DD:EE:01 ::10", "AA:BB:CC:DD:EE:02 ::1a2b:3c4d", "AA:BB:CC:DD:EE:06 ::6"] and n == ["walk 3"], (recs, n))
    out = run(["--walk=", "--walk=garbage without brackets", "--walk=<>", "--walk=<aa:bb:cc:dd:ee:01>"])
    check("walker: empty, bracketless, '<>' and a MAC without a suffix deliver nothing",
          all(l == "walk 0" for l in out if l.startswith("walk ")) and not [l for l in out if l.startswith("rec ")], out)
finally:
    shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- wiring
hdr = read("shared/reaper_dhcp6.h")
check("reaper_dhcp6.h names the /jffs store and both entry points",
      '#define REAPER_DHCP6_FILE "/jffs/reaper/dhcp6_static"' in hdr and "reaper_dhcp6_sfx_valid(" in hdr and "reaper_dhcp6_walk(" in hdr)
check("libshared builds it and shared.h exposes it",
      "OBJS += reaper_dhcp6.o" in read("shared/Makefile") and '#include "reaper_dhcp6.h"' in read("shared/shared.h"))

web = read("httpd/web.c")
for want in ("\tchar ip6[46];", "\tchar resv6[24];", "ndn = reaper_nd_load(ndt, RDEV_ND);",
             "if (!reaper_nd_mac_of_str(ndt, ndn, ip, mac6, sizeof(mac6), NULL, 0)) continue;",
             "if (!reaper_nd_global(ndt[i].ip)) continue;",
             "int nolease = (d->wifi && !d->ip[0] && !d->ip6[0]) ? 1 : 0;",
             'websWrite(stream, ",\\"ip6\\":");', ',\\"v6only\\":%d,\\"resv6\\":',
             'reaper_dhcp6_walk(v, rdev_resv6_cb, &w);',
             '!strcmp(action, "set_reserve6") || !strcmp(action, "unpin6")',
             'if (!reaper_dhcp6_sfx_valid(sfx)) {', '"ek\\":\\"RDEVE_14\\"', '"ek\\":\\"RDEVE_15\\"',
             'rjf_set(REAPER_DHCP6_FILE, out, "reaper_dev")', 'rdev_audit(pin ? "pin6" : "unpin6", umac, pin ? lsfx : "");',
             '{ "dev",    "rdev_dhcp6",      8192 },', 'static int rdev_dhcp6_import(const char *v)',
             '} else if (!strcmp(rcfg_flags[i].nv, "rdev_dhcp6")) {\t/* IPv6 A3: a /jffs list */',
             'if (rdev_dhcp6_import(v) != 0) { rejected++; continue; }'):
    if want not in web:
        die("web.c lacks %s" % want)
check("web.c: struct, collector (neighbour cache + DHCPv6 lease bridge), nolease, JSON, the two actions, the backup flag", True)
gate = web.index('static void do_reaper_dev_cgi(char *url, FILE *stream)')
body = web[gate:gate + 60000]
check("the DHCPv6 actions sit behind the CGI's token gate (only store_status is exempt)",
      body.index('if (strcmp(action, "store_status") != 0) {') < body.index('"set_reserve6"'), "")
check("the import validation of rdev_dhcp6 uses the printable charset, not the flag charset",
      '!strcmp(rcfg_flags[i].nv, "rwarden_cfeeds") || !strcmp(rcfg_flags[i].nv, "rdev_dhcp6")) {' in web)

svc = read("rc/services.c")
for want in ('void write_static_leases6(FILE *fp)', 'fprintf((FILE *)arg, "dhcp-host=%s,[%s]\\n", mac, sfx);',
             'reaper_dhcp6_walk(v, rdhcp6_emit, fp);', '\tif (ipv6_enabled())\n\t\twrite_static_leases6(fp);'):
    if want not in svc:
        die("services.c lacks %s" % want)
check("services.c emits dhcp-host=<MAC>,[::suffix] for the main LAN when IPv6 is on", True)
check("rc.h declares write_static_leases6", "extern void write_static_leases6(FILE *fp);" in read("rc/rc.h"))

page = open(os.path.join(SRC, "www", "Reaper_Devices.asp"), "rb").read()
if any(b > 0x7f for b in page): die("Reaper_Devices.asp is not pure ASCII")
page = page.decode("ascii")
for want in ("td.ip .ip6{", ".chip.v6{", "if(d.resv6) ipHtml +=", "if(d.ip6) ipHtml +=", "d.v6only ?", "data-pin6=", "data-unpin6=",
             "function sfx6Of(ip6)", "function pin6Ask(i)", "function pin6Do(i, sfx)", "function unpin6(i)",
             "/^::[0-9a-fA-F]{1,4}(:[0-9a-fA-F]{1,4}){0,3}$/", "action=set_reserve6&mac=", "action=unpin6&mac=",
             "RDEVE_14:`<#RDEVE_14#>`, RDEVE_15:`<#RDEVE_15#>`", "ip6: (d.ip6 || '')", "name,mac,ip,ipv6,reserved_ip,state",
             "csvCell(rows[i].ip6)", "<th>IPv6</th>", "esc(rows[i].ip6)"):
    if want not in page:
        die("Reaper_Devices.asp lacks %s" % want)
check("page: ip6 cell + chips, pin/unpin IPv6 with a validated suffix, error texts, ipv6 export column", True)
if re.search(r"'[^'\n]*<#[A-Za-z_0-9]+#>[^'\n]*'", re.sub(r"`[^`\n]*`", "``", page)):
    die("a dict token sits inside a single-quoted JS string (rule 29)")
toks = sorted(set(re.findall(r"<#(RDEVE?_\d+)#>", page)))
need = {"RDEV_97", "RDEV_98", "RDEV_99", "RDEV_100", "RDEV_101", "RDEV_102", "RDEV_103", "RDEVE_14", "RDEVE_15"}
check("the page uses the new tokens through its L/DERR tables", need <= set(toks), sorted(need - set(toks)))
dicts = [d for d in glob.glob(os.path.join(SRC, "www", "*.dict")) if not d.endswith("temp.dict")]
if len(dicts) != 25: die("expected 25 dictionaries, found %d" % len(dicts))
for d in dicts:
    keys = set(re.findall(r"^(RDEVE?_\d+)=", open(d, encoding="utf-8", errors="surrogateescape").read(), re.M))
    missing = [t for t in toks if t not in keys]
    if missing: die("%s lacks %s" % (os.path.basename(d), ", ".join(missing)))
check("every RDEV/RDEVE token the page uses exists in all 25 dictionaries (%d tokens)" % len(toks), True)
mk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_markers.txt"), encoding="utf-8").read()
check("markers pin the staged httpd, rc and page",
      all(w in mk for w in ('usr/sbin/httpd|"v6only":|1', "usr/sbin/httpd|/jffs/reaper/dhcp6_static|1",
                            "sbin/rc|dhcp-host=%s,[%s]|1", "www/Reaper_Devices.asp|data-pin6|1")))

if fails:
    print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
print("all checks passed: the Devices page shows IPv6, bridges DHCPv6 leases to their devices, and keeps DHCPv6 reservations as validated host suffixes that dnsmasq honours")
