#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A WAN event restarts Samba only when it changed what smbd binds to (2026-10-15).

WHY THIS EXISTS. Stock wan_up() (rc/wan.c) stopped and started Samba on every WAN up while
Samba is enabled - the first lease, a changed lease, each PPPoE reconnect, a dual-WAN switch -
dropping every open SMB session. And wan_up() restarts every WireGuard server, whose
_wg_server_update_service() (rc/wireguard.c) restarted Samba again whenever the server has LAN
access (wgs_lanaccess, default 1): two restarts per WAN event, plus one at boot and one per
peer edit.

The WAN reaches smb.conf only through the "interfaces =" line (libdisk/write_smb_conf.c):
wan0_ifname when SMB over the WAN (smbd_wanac) is on, and br0's IPv6 addresses, which no IPv6
path refreshes (the stock restart did that as a side effect). The WireGuard client subnets
appear only in a "hosts allow" block that is #if 0, so the WireGuard restart regenerated an
identical file.

THE FIX. wan_up() restarts Samba only when reaper_samba_wan_restart_needed() says so: SMB over
the WAN on, no /etc/smb.conf or no interfaces line (let start_samba() decide, as stock), or a
br0 IPv6 address (global or link-local) the running line does not list. The WireGuard hook no
longer touches Samba.

WHAT IT DOES. Static checks on the three files - including that the WireGuard subnet block in
write_smb_conf.c is still #if 0, the premise of dropping that restart - then compiles the helper
out of rc/wan.c with stub nvram/getifaddr and runs it over the cases. A negative self-test drops
the IPv6 check and expects the prefix-change case to fail.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or
REAPER_ROUTER_SRC). The compiled run is skipped, not failed, without a host gcc."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = lambda *a: os.path.join(SRC, *a)
if not SRC or not all(os.path.isfile(P(*f)) for f in (("rc", "wan.c"), ("rc", "wireguard.c"),
                                                        ("libdisk", "write_smb_conf.c"))):
    skip("no router source tree with rc/wan.c, rc/wireguard.c, libdisk/write_smb_conf.c")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

rd = lambda *a: open(P(*a), encoding="utf-8", errors="replace").read()
wan, wg, smb = rd("rc", "wan.c"), rd("rc", "wireguard.c"), rd("libdisk", "write_smb_conf.c")

# ---- static ----
check("static: wan_up() gates the Samba restart on the helper",
      re.search(r'if \(nvram_match\("enable_samba", "1"\) && reaper_samba_wan_restart_needed\(\)\)\s*\{\s*'
                r'stop_samba\(0\);\s*start_samba\(\);', wan) is not None)
check("static: no ungated Samba restart left in wan.c",
      re.search(r'if \(nvram_match\("enable_samba", "1"\)\)\s*\{\s*stop_samba', wan) is None)
fm = re.search(r"\nstatic int reaper_samba_wan_restart_needed\(void\)\n\{\n.*?\n\}\n", wan, re.S)
fn = fm.group(0) if fm else ""
check("static: reaper_samba_wan_restart_needed() found", bool(fn))
check("static: the helper keeps SMB over the WAN restarting", 'nvram_get_int("smbd_wanac")' in fn)

wm = re.search(r"static void _wg_server_update_service\(const char\* prefix\)\n\{\n(.*?)\n\}\n", wg, re.S)
check("static: the WireGuard server hook no longer restarts Samba",
      wm is not None and "start_samba" not in wm.group(1) and "stop_samba" not in wm.group(1))

# the premise: every WireGuard (and VPN) subnet use in write_smb_conf.c sits inside #if 0
def live_lines(text):
    out, stack = [], []
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("#if"):
            stack.append(s.startswith("#if 0")); continue
        if s.startswith("#endif") and stack:
            stack.pop(); continue
        if s.startswith("#else") and stack:
            stack[-1] = False if stack[-1] else stack[-1]; continue
        if not any(stack):
            out.append(ln)
    return "\n".join(out)
body = smb[smb.find("interfaces = lo br0"):]
live = live_lines(body)
check("premise: the WireGuard subnets never reach smb.conf (get_wgsc_subnet/wgsc_subnet only under #if 0)",
      "get_wgsc_subnet(" not in live and "wgsc_subnet" not in live and "hosts allow" not in live, live[:300])
check("premise: the only WAN name in smb.conf is wan0_ifname behind smbd_wanac",
      re.search(r'nvram_get_int\("smbd_wanac"\)\)\s*\?\s*nvram_safe_get\("wan0_ifname"\)', smb) is not None
      and smb.count("wan0_ifname") == 1)

# ---- compiled ----
HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#define GIF_LINKLOCAL 1
static size_t strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; } return l; }
static const char *e(const char *k) { const char *v = getenv(k); return v ? v : ""; }
static int nvram_get_int(const char *k) { return atoi(strcmp(k, "smbd_wanac") ? "0" : e("WANAC")); }
static const char *nvram_safe_get(const char *k) { return strcmp(k, "lan_ifname") ? "" : "br0"; }
static const char *getifaddr(const char *ifn, int fam, int fl) {
	const char *v = e(fl == GIF_LINKLOCAL ? "V6LL" : "V6G"); (void)ifn; (void)fam; return *v ? v : NULL;
}
@FN@
int main(void) { printf("%d\n", reaper_samba_wan_restart_needed()); return 0; }
'''

def build(td, name, fn_text):
    c = os.path.join(td, name + ".c")
    open(c, "w").write(HARNESS.replace("@FN@", fn_text.replace('"/etc/smb.conf"', '"%s"' % os.path.join(td, "smb.conf"))))
    exe = os.path.join(td, name)
    r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
    return exe, r

def run(exe, td, conf, wanac="0", v6g="", v6ll=""):
    p = os.path.join(td, "smb.conf")
    if conf is None:
        if os.path.exists(p): os.unlink(p)
    else:
        open(p, "w").write(conf)
    env = dict(os.environ, WANAC=wanac, V6G=v6g, V6LL=v6ll)
    return subprocess.run([exe], capture_output=True, text=True, env=env).stdout.strip()

G, LL = "2001:db8:1::1", "fe80::1"
CONF = ("[global]\nbind interfaces only = yes\n"
        "interfaces = lo br0 192.168.50.1/255.255.255.0  %s%%br0/64 %s%%br0/64\nuse sendfile = yes\n")
CASES = [
    ("SMB over the WAN on: restart", dict(conf=CONF % (LL, G), wanac="1", v6g=G, v6ll=LL), "1"),
    ("no smb.conf (Samba not started): restart, start_samba() decides", dict(conf=None), "1"),
    ("smb.conf without an interfaces line: restart", dict(conf="[global]\n"), "1"),
    ("IPv4 only, nothing changed: no restart", dict(conf=CONF.replace("  %s%%br0/64 %s%%br0/64", "")), "0"),
    ("IPv6 addresses listed: no restart", dict(conf=CONF % (LL, G), v6g=G, v6ll=LL), "0"),
    ("new br0 global IPv6 (prefix change): restart", dict(conf=CONF % (LL, G), v6g="2001:db8:2::1", v6ll=LL), "1"),
    ("br0 IPv6 appeared after Samba started: restart",
     dict(conf=CONF.replace("  %s%%br0/64 %s%%br0/64", ""), v6g=G, v6ll=LL), "1"),
]

gcc = shutil.which("gcc") or shutil.which("cc")
if gcc and fn:
    with tempfile.TemporaryDirectory() as td:
        exe, r = build(td, "t", fn)
        check("host gcc: the helper compiles clean with -Wall -Wextra -Werror", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            for name, kw, want in CASES:
                got = run(exe, td, **kw)
                check(name, got == want, got)
        bad = re.sub(r"\tif \(\(a = getifaddr\(lan, AF_INET6, 0\)\).*?\n\t\treturn 1;\n", "", fn, flags=re.S)
        exe2, r2 = build(td, "n", bad)
        if bad != fn and r2.returncode == 0:
            got = run(exe2, td, conf=CONF % (LL, G), v6g="2001:db8:2::1", v6ll=LL)
            check("self-test: without the global-IPv6 check a prefix change is missed (the case bites)", got == "0", got)
        else:
            check("self-test: mutation applied and compiled", False, r2.stderr if bad != fn else "no match")
else:
    print("note: no host gcc - the compiled helper run is skipped")

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
