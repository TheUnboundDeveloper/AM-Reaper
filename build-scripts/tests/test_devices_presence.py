#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Devices page presence + refresh (httpd/web.c rdev_collect, www/Reaper_Devices.asp,
2026-10-18).

WHY THIS EXISTS. BACKLOG "[P3] Device Menu out of sync": devices occasionally
mislabelled wired/wireless, and online/offline not updating without a manual
refresh. Three causes, all in code:
  1. The page fetched once (devBoot -> loadAll) and never again.
  2. "Online" came from /proc/net/arp flag 0x2 and the IPv6 neighbour cache - set
     for every VALID entry, STALE included - and below gc_thresh1 (IPv4 default
     128; firewall.c's override is commented out) the kernel never collects a
     STALE entry. gkd's seen.tsv "online" is built the same way and was ORed in.
     A device that left an hour ago stayed online.
  3. Such a stale "online" device that no live source places fell to the
     last-resort "online and unplaced = Wired" rule - a phone that left Wi-Fi, or
     dozed off the assoclist, read as an online WIRED device, while gkd (which
     keeps a dozing client's band) called it wireless.
Presence now comes only from live evidence: assoclist, the bridge forwarding
tables (Broadcom's bcm_br_has_fdb_expired() asks the accelerator before ageing an
entry, so offloaded traffic keeps it), the AiMesh lists, a connected node.

WHAT IT DOES.
  1. Compiles rdev_live_touch()/rdev_live_get() EXTRACTED FROM web.c on the host
     (-Wall -Wextra -Werror) and checks record/update/lookup and full-table
     eviction of the longest-gone device.
  2. Asserts on rdev_collect() and the scanners: no presence from ARP, the
     neighbour cache or seen.tsv; FDB presence on every port kind and every
     bridge; a connected node is present; the Wired fallback is reached only by a
     present device; last-seen from httpd's own record, gkd's only once gkd lost
     the device too; an absent device keeps its last-known medium.
  3. Asserts on the page: a guarded 15 s refresh (dialog open / field focused /
     tab hidden), the refresh drops its result if the user started something
     while it was in flight, poll=1 lets httpd reuse a fresh snapshot, and an
     offline row never reads "online".

Exit 0 pass, 1 fail, 77 skipped (no gcc, not Linux, or no router source tree -
pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
if not sys.platform.startswith("linux"):
    skip("not Linux")
GCC = shutil.which("gcc") or shutil.which("cc")
if not GCC:
    skip("no host gcc")

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

web = read("httpd/web.c")
page = read("www/Reaper_Devices.asp")

def func(text, sig, what):
    m = re.search(re.escape(sig) + r"\n\{(.*?)\n\}\n", text, re.S)
    if not m:
        die("%s not found" % what)
    return m.group(1)

# ------------------------------------------------------------ 1. last-seen record
m = re.search(r"#define RDEV_MAX (\d+)", web)
if not m:
    die("RDEV_MAX not found")
rmax = int(m.group(1))
m = re.search(r"(static struct \{ char mac\[18\]; long t; \} rdev_live\[RDEV_MAX\];\n"
              r"static int rdev_live_n = 0;\n.*?\nstatic long rdev_live_get\(const char \*mac\)\n\{.*?\n\}\n)", web, re.S)
if not m:
    die("rdev_live helpers not found in httpd/web.c")
DRV = r'''
#include <stdio.h>
#include <string.h>
#define RDEV_MAX %d
static size_t strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
%s
int main(void)
{
	char mac[18];
	int i, fails = 0;
	rdev_live_touch("AA:BB:CC:00:00:01", 100);
	if (rdev_live_get("AA:BB:CC:00:00:01") != 100) { puts("FAIL record"); fails++; } else puts("ok record");
	rdev_live_touch("AA:BB:CC:00:00:01", 250);
	if (rdev_live_get("AA:BB:CC:00:00:01") != 250 || rdev_live_n != 1) { puts("FAIL update in place"); fails++; } else puts("ok update in place");
	if (rdev_live_get("AA:BB:CC:00:00:02") != 0) { puts("FAIL unknown = 0"); fails++; } else puts("ok unknown device = 0 (no last seen)");
	for (i = 2; i <= RDEV_MAX; i++) { snprintf(mac, sizeof(mac), "AA:BB:CC:00:%%02X:%%02X", i >> 8, i & 0xff); rdev_live_touch(mac, 1000 + i); }
	if (rdev_live_n != RDEV_MAX) { puts("FAIL fill"); fails++; }
	rdev_live_touch("DD:DD:DD:DD:DD:DD", 5000);	/* full: the longest-gone (t=250) makes room */
	if (rdev_live_get("AA:BB:CC:00:00:01") != 0 || rdev_live_get("DD:DD:DD:DD:DD:DD") != 5000 || rdev_live_n != RDEV_MAX)
		{ puts("FAIL eviction"); fails++; } else puts("ok full table evicts the longest-gone device");
	return fails ? 1 : 0;
}
''' % (rmax, m.group(1))
work = tempfile.mkdtemp(prefix="rdevlive_")
try:
    c = os.path.join(work, "d.c"); open(c, "w").write(DRV)
    exe = os.path.join(work, "d")
    cc = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", exe, c],
                        capture_output=True, text=True)
    if cc.returncode != 0:
        die("rdev_live helpers do not compile on the host:\n" + cc.stderr[-1500:])
    ok("rdev_live helpers (extracted from web.c) compile (-Wall -Wextra -Werror)")
    r = subprocess.run([exe], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        print(("ok   " if ln.startswith("ok ") else "FAIL ") + ln.split(" ", 1)[1])
    if r.returncode != 0:
        die("rdev_live helper checks failed")
finally:
    shutil.rmtree(work, ignore_errors=True)

# ------------------------------------------------------------ 2. presence rules
col = func(web, "static void rdev_collect(void)", "rdev_collect()")
arp = col[col.index("/* 2. ARP"):col.index("/* 2b.")]
nd = col[col.index("/* 2b."):col.index("/* 3. wireless")]
seen = col[col.index("/* 6. seen.tsv"):col.index("/* 7.")]
for name, blk in (("ARP", arp), ("the IPv6 neighbour cache", nd), ("gkd seen.tsv", seen)):
    if re.search(r"\.online\s*=\s*1", blk) or "seen[i].online) dev[idx].online" in blk:
        die("rdev_collect: %s still marks a device online" % name)
    ok("rdev_collect: %s gives rows/addresses, never presence" % name)

fdb = func(web, "static void rdev_scan_fdb_br(struct rdev *v, int *n, const char *br, int sdn)", "rdev_scan_fdb_br()")
if not re.search(r"\} else \{\n\t+/\* 2026-10-18: present behind a port that is neither eth\* nor\n.*?v\[idx\]\.online = 1;", fdb, re.S):
    die("rdev_scan_fdb_br: a MAC behind a non-eth/non-wl port is not marked present")
ok("FDB: a MAC behind any port kind is present (eth* wired, wl* wireless, other = decided later)")
sf = func(web, "static void rdev_scan_fdb(struct rdev *v, int *n)", "rdev_scan_fdb()")
if 'opendir("/sys/class/net")' not in sf or '/sys/class/net/%s/bridge' not in sf:
    die("rdev_scan_fdb: only the sdn_rl bridges are scanned")
ok("FDB: every bridge is scanned, not only the ones sdn_rl names")
if "if (path > 0) v[k].online = 1;" not in web:
    die("rdev_node_classify: a connected node is not present")
ok("a connected AiMesh node is present")

fb = col.index("/* last resort: a PRESENT device")
if "if (!(dev[i].online && !dev[i].wifi && !dev[i].wired))" not in col[fb:fb + 900]:
    die("the Wired fallback lost its online guard")
order = [col.index(s) for s in ("rdev_scan_wl(dev, &n, mlo_on);", "rdev_scan_fdb(dev, &n);",
                                "rdev_scan_amesh(dev, &n);", "rdev_node_classify(dev, n);", "/* last resort: a PRESENT device")]
if order != sorted(order):
    die("rdev_collect: the live passes must all run before the Wired fallback")
ok("the Wired fallback runs after every live pass and only for a present device")

# 2026-10-19 (field: an iPhone on the RT-AX92U read "Wired", and stayed "connected"
# in Airplane mode for the bridge's 300 s ageing). Backhaul sightings wait for the
# mesh lists; on wl and backhaul ports an entry older than RDEV_FDB_FRESH is the
# ageing tail of a device that left.
m = re.search(r"#define RDEV_FDB_FRESH (\d+)", web)
if not m or not (30 <= int(m.group(1)) < 300):
    die("RDEV_FDB_FRESH missing or not below the 300 s bridge ageing")
fresh = int(m.group(1))
if "if (!v[idx].online && age > RDEV_FDB_FRESH) break;" not in fdb:
    die("rdev_scan_fdb_br: a stale wl-port entry outside the assoclist still counts as present")
ok("FDB: a wl-port entry older than %d s and not in the assoclist is not presence" % fresh)
if "if (port[k].bh && !rdev_nm_owner(mac)) {" not in fdb:
    die("rdev_scan_fdb_br: a client behind a node backhaul is decided before the mesh lists")
ok("FDB: a client behind a node backhaul is held for rdev_bh_resolve (node MACs excepted)")
order = [col.index(s) for s in ("rdev_scan_amesh(dev, &n);", "rdev_node_classify(dev, n);",
                                "rdev_bh_resolve(dev, n);", "/* last resort: a PRESENT device")]
if order != sorted(order):
    die("rdev_collect: rdev_bh_resolve must run after the mesh passes and before the Wired fallback")
ok("rdev_bh_resolve runs after the mesh lists and before the Wired fallback")
m = re.search(r"(static void rdev_bh_resolve\(struct rdev \*v, int n\)\n\{.*?\n\}\n)", web, re.S)
if not m:
    die("rdev_bh_resolve() not found")
BH = r'''
#include <stdio.h>
#include <string.h>
#define RDEV_FDB_FRESH %d
struct rdev { int online, wifi, wired, node, bh_sta, fdb_bh, fdb_bhwl, fdb_age, nwired; char via[18], fdb_via[18]; };
static void rdev_set_via(struct rdev *d, const char *mac) { snprintf(d->via, sizeof(d->via), "%%s", mac); }
%s
#define NODE "02:00:5E:00:53:10"
int main(void)
{
	struct rdev v[7];
	int fails = 0;
	memset(v, 0, sizeof(v));
	/* 0 phone, node list missed it, WDS backhaul, fresh */
	v[0].fdb_bh = 1; v[0].fdb_bhwl = 1; v[0].fdb_age = 20; strcpy(v[0].fdb_via, NODE);
	/* 1 phone in Airplane mode: same port, entry 285 s old */
	v[1].fdb_bh = 1; v[1].fdb_bhwl = 1; v[1].fdb_age = 285; strcpy(v[1].fdb_via, NODE);
	/* 2 cabled to the node (its wired list), WDS backhaul */
	v[2].fdb_bh = 1; v[2].fdb_bhwl = 1; v[2].fdb_age = 5; v[2].nwired = 1; strcpy(v[2].fdb_via, NODE);
	/* 3 unlisted behind an ETHERNET backhaul */
	v[3].fdb_bh = 1; v[3].fdb_bhwl = 0; v[3].fdb_age = 5; strcpy(v[3].fdb_via, NODE);
	/* 4 listed by the node's Wi-Fi list already (online, wifi) */
	v[4].fdb_bh = 1; v[4].fdb_bhwl = 1; v[4].fdb_age = 200; v[4].online = 1; v[4].wifi = 1; strcpy(v[4].via, "AA:AA:AA:AA:AA:AA");
	/* 5 the node itself / 6 its backhaul station */
	v[5].fdb_bh = 1; v[5].fdb_age = 1; v[5].node = 4;
	v[6].fdb_bh = 1; v[6].fdb_age = 1; v[6].bh_sta = 1;
	rdev_bh_resolve(v, 7);
#define T(c, m) do { if (c) puts("ok " m); else { puts("FAIL " m); fails++; } } while (0)
	T(v[0].online && v[0].wifi && !v[0].wired && !strcmp(v[0].via, NODE), "unlisted client behind a WDS backhaul = Wi-Fi via that node, not Wired");
	T(!v[1].online && !v[1].wifi && !v[1].wired, "a backhaul entry past RDEV_FDB_FRESH is absent (Airplane mode)");
	T(v[2].online && v[2].wired && !v[2].wifi, "a client on the node's wired list is Wired");
	T(v[3].online && v[3].wired && !v[3].wifi, "unlisted behind an ethernet backhaul stays Wired");
	T(v[4].online && v[4].wifi && !strcmp(v[4].via, "AA:AA:AA:AA:AA:AA"), "a device a list already placed is left alone");
	T(!v[5].online && !v[6].online, "the node and its backhaul station are not decided here");
	return fails ? 1 : 0;
}
''' % (fresh, m.group(1))
work = tempfile.mkdtemp(prefix="rdevbh_")
try:
    c = os.path.join(work, "b.c"); open(c, "w").write(BH)
    exe = os.path.join(work, "b")
    cc = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", exe, c],
                        capture_output=True, text=True)
    if cc.returncode != 0:
        die("rdev_bh_resolve does not compile on the host:\n" + cc.stderr[-1500:])
    ok("rdev_bh_resolve (extracted from web.c) compiles (-Wall -Wextra -Werror)")
    r = subprocess.run([exe], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        print(("ok   " if ln.startswith("ok ") else "FAIL ") + ln.split(" ", 1)[1])
    if r.returncode != 0:
        die("rdev_bh_resolve checks failed")
finally:
    shutil.rmtree(work, ignore_errors=True)
if "rdev_live_touch(dev[i].mac, lnow);" not in col or "dev[i].last = rdev_live_get(dev[i].mac);" not in col:
    die("rdev_collect: last seen is not taken from httpd's own record")
ok("last seen = the last collect that found the device present")
if "if (!seen[i].online && seen[i].last > dev[idx].last) dev[idx].last = seen[i].last;" not in seen:
    die("seen.tsv: gkd's last is used while gkd still calls the device online")
ok("gkd's last seen counts only once gkd has lost the device too")
if "if (!dev[idx].online && !dev[idx].wifi && !dev[idx].wired && !dev[idx].band[0] && seen[i].wired)" not in seen:
    die("seen.tsv: an absent device does not keep its last-known medium")
ok("an absent device keeps its last-known medium (band, or gkd's wired verdict)")
if 'rdev_snapshot(get_cgi("poll") ? RDEV_TTL : 0);' not in web:
    die("status action: a background refresh cannot reuse a fresh snapshot")
ok("status action: poll=1 may reuse a snapshot up to RDEV_TTL old")

# ------------------------------------------------------------ 3. page
for needle, what in (
    ("var POLL_MS = 15000", "page: refreshes every 15 s"),
    ("setInterval(pollTick, POLL_MS);", "page: the refresh timer is started at boot"),
    ("document.addEventListener('visibilitychange', function(){ if(!document.hidden) pollTick(); });",
     "page: refreshes at once when the tab becomes visible"),
    ("if(document.hidden) return true;", "page: no refresh in a hidden tab"),
    ("if(document.getElementById('pin_ovl').className.indexOf('show') >= 0) return true;",
     "page: no refresh while a dialog (index-bound actions) is open"),
    ("return !!(a && a.id !== 'q' && /^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName));",
     "page: no refresh while a field (rename commits on blur) has focus; search excepted"),
    ("if(!j || pollBlocked()) return;", "page: a refresh drops its result if the user started something meanwhile"),
    ("(poll ? '&poll=1' : '')", "page: a refresh asks with poll=1"),
    ("if(keepQ){ var qi = document.getElementById('q'); qi.focus(); try{ qi.setSelectionRange(s0, s1); }catch(e){} }",
     "page: the search box keeps focus and caret across a refresh"),
):
    if needle not in page:
        die(what + " (missing %r)" % needle)
    ok(what)
m = re.search(r"function ago\(sec\)\{(.*?)\n\}\n", page, re.S)
if not m:
    die("page: ago() not found")
ag = m.group(1)
if "RDEV_29" in ag:
    die("page: ago() still answers 'online' for an offline row")
ok("page: an offline row never reads 'online'")
print("PASS")
