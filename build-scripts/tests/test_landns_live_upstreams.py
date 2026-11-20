#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LAN name resolution check: the upstreams it names are the ones dnsmasq is running with (2026-11-13).

WHY THIS EXISTS. Field report (GT-BE98, 2026-10-21): an add-on had left a /jffs/configs/dnsmasq.conf that replaced
the router's whole DNS configuration with one upstream, a resolver on the router itself that was no longer
installed. No new name resolved. The check asked the servers in the file the firmware writes - which that
configuration never loads - found them answering and logged "every upstream answered when asked directly". It now
reads the running configuration first: its own server= lines are upstreams, and the servers file counts only when
the configuration names it. The log line says when every silent upstream is on the router itself, and when a
custom configuration file is in use.

WHAT IT DOES. Compiles the LANDNS-LIVE block of rc/rdnshc.c on the host and runs its line readers and the
all-local test; then pins the wiring in landns_silent_upstreams() and the log line. Exit 0 pass, 1 fail,
77 skipped (no gcc, or no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RD = os.path.join(SRC, "rc", "rdnshc.c") if SRC else ""
if not RD or not os.path.isfile(RD):
    skip("no router tree with rc/rdnshc.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def done():
    print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
    if fails:
        print("\n".join(fails))
    sys.exit(1 if fails else 0)

rd = open(RD, encoding="utf-8", errors="surrogateescape").read()
m = re.search(r"/\* LANDNS-LIVE-BEGIN.*?\*/(.*?)/\* LANDNS-LIVE-END \*/", rd, re.S)
check("rdnshc.c carries the LANDNS-LIVE block", m is not None)
if not m:
    done()

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
%s
int main(int argc, char **argv)
{
	char addr[46]; int port = -1;
	if (argc < 3) return 2;
	if (argv[1][0] == 'u') {
		if (landns_conf_upstream(argv[2], addr, sizeof(addr), &port)) printf("%%s %%d\n", addr, port); else printf("-\n");
	} else if (argv[1][0] == 'f') printf("%%d\n", landns_conf_names_file(argv[2], argv[3]));
	else if (argv[1][0] == 'l') printf("%%d\n", landns_addr_local(argv[2]));
	else if (argv[1][0] == 'a') printf("%%d\n", landns_all_local(argv[2]));
	return 0;
}
'''
tmp = tempfile.mkdtemp()
try:
    c = os.path.join(tmp, "l.c"); exe = os.path.join(tmp, "l")
    open(c, "w").write(MAIN % m.group(1))
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("the block compiles with -Wall -Wextra -Werror", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        def run(*a):
            return subprocess.run([exe] + list(a), capture_output=True, text=True).stdout.strip()
        up = {
            "server=127.0.0.1#5354\n": "127.0.0.1 5354",       # the field case: a local resolver on its own port
            "server=192.0.2.53\n": "192.0.2.53 53",
            "server=192.0.2.53#53\n": "192.0.2.53 53",
            "server=2001:db8::53#5300\n": "2001:db8::53 5300",
            "server=192.0.2.53@eth0\n": "192.0.2.53 53",
            "server=fe80::1%br0\n": "fe80::1 53",
            "  server=192.0.2.9\n": "192.0.2.9 53",            # leading blanks
            "server=192.0.2.9#0\n": "192.0.2.9 53",            # a port that is not one
            "server=192.0.2.9#70000\n": "192.0.2.9 53",
            "server=/lan/192.0.2.1\n": "-",                    # a domain route is not an upstream
            "server=/example.com/\n": "-",
            "#server=192.0.2.53\n": "-",                       # commented out
            "servers-file=/tmp/resolv.dnsmasq\n": "-",
            "no-resolv\n": "-",
            "server=\n": "-",
            "server=" + "9" * 60 + "\n": "-",                  # longer than an address can be
        }
        got = {k: run("u", k) for k in up}
        check("configuration lines: plain server= lines are upstreams (address, port); domain routes, comments and others are not",
              got == up, [(k, got[k]) for k in up if got[k] != up[k]])
        P = "/tmp/resolv.dnsmasq"
        nf = {"servers-file=/tmp/resolv.dnsmasq\n": "1", "servers-file=/tmp/resolv.dnsmasq": "1", "  servers-file=/tmp/resolv.dnsmasq \n": "1",
              "servers-file=/tmp/resolv.dnsmasq.old\n": "0", "servers-file=/jffs/x\n": "0", "#servers-file=/tmp/resolv.dnsmasq\n": "0",
              "resolv-file=/tmp/resolv.dnsmasq\n": "0"}
        got = {k: run("f", k, P) for k in nf}
        check("the servers file counts only when the configuration names exactly that file", got == nf, [(k, got[k]) for k in nf if got[k] != nf[k]])
        loc = {"127.0.0.1": "1", "127.0.1.1": "1", "127.255.255.254": "1", "::1": "1", "192.0.2.1": "0", "198.51.100.127": "0", "::10": "0", "2001:db8::1": "0"}
        got = {k: run("l", k) for k in loc}
        check("on the router itself = 127.0.0.0/8 or ::1", got == loc, got)
        al = {"127.0.0.1#5354": "1", "127.0.0.1#5354,127.0.1.1": "1", "::1#5300": "1", "127.0.0.1#5354,192.0.2.53": "0",
              "192.0.2.53": "0", "-": "0", "": "0", ",": "0", "127.0.0.1,": "1"}
        got = {k: run("a", k) for k in al}
        check("the list of silent servers is 'all local' only when it is not empty and every entry is on the router",
              got == al, [(k, got[k]) for k in al if got[k] != al[k]])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# wiring
fn = rd[rd.find("static void landns_silent_upstreams("):rd.find("/* Called once per loop pass; does nothing until a check is due. */")]
check("landns_silent_upstreams() found", len(fn) > 200)
i_conf = fn.find('fopen(LDNS_CONF, "r")'); i_file = fn.find('fopen(HC_DNSMASQ, "r")'); i_ask = fn.find("dns_ask_many(")
check("the running configuration is read first, then the servers file, then the servers are asked", 0 <= i_conf < i_file < i_ask, (i_conf, i_file, i_ask))
check("the running configuration is /etc/dnsmasq.conf", '#define LDNS_CONF\t"/etc/dnsmasq.conf"' in rd)
check("the servers file is used only when the configuration names it (or the configuration cannot be read)",
      "if (landns_conf_names_file(line, HC_DNSMASQ)) { named = 1; continue; }" in fn
      and 'if ((!conf || named) && (fp = fopen(HC_DNSMASQ, "r")) != NULL) {' in fn)
check("the servers file is still read under the resolv lock",
      0 <= fn.find('lock = file_lock("resolv");') < i_file < fn.find("file_unlock(lock);"))
check("an upstream is taken once, with a usable address family, four at most",
      fn.count("landns_take(addr, port, fam, n)") == 2 and fn.count("n < LDNS_UP_MAX") == 2
      and "if (port[i] == port[n] && !strcmp(addr[i], addr[n])) return 0;" in rd and "hc_v6_usable()" in rd[rd.find("static int landns_take("):rd.find("static void landns_silent_upstreams(")])
tick = rd[rd.find("static void landns_tick("):rd.find("int rdnshc_main(")]
check("the log line says when the silent upstreams are on the router itself, and when a custom configuration is in use",
      "landns_all_local(ld->silent) ?" in tick and "on the router itself" in tick
      and '(f_exists(LDNS_CUSTOM) && !nvram_match("jffs2_scripts", "0")) ?' in tick
      and '#define LDNS_CUSTOM\t"/jffs/configs/dnsmasq.conf"' in rd)
check("still four FAILING lines and one line per change of state", tick.count('logmessage(HC_TAG, "LAN name resolution FAILING') == 4)
check("status only: nothing is moved or reloaded by the new code", "update_resolvconf" not in fn and "hc_reload" not in fn and "nvram_set" not in fn)

done()
