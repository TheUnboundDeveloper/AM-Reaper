#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A box that is not routing must still tune its sockets, count its clients and
name its own operation mode.

WHY THIS EXISTS. Field data (GT-BE19000 tester, 2026-09-13): a working router in
Access Point mode (sw_mode=3) reported a red "Disconnected" Internet card, zero
clients while sixteen stations were associated, socket ceilings still at the stock
212992, and an "rtrafd is enabled but not running" warning. None of it was
model-specific - all four were the same shape, a Reaper surface built on something
only a routing box has:

  * rc/firewall.c        start_firewall() returns at !is_routing_enabled() long
                         before the socket-buffer ceilings, so they never loaded.
  * Main_ReaperDash.asp  the Internet card derives its verdict from wan0_state_t,
                         which is structurally 0 with no WAN of its own.
  * Main_ReaperDash.asp  the client tiles filter on networkmap's isOnline, which is
                         derived from DHCP leases and conntrack - both empty on a
                         bridging box.
  * others/reaper_diag   12c warns when a routing-only daemon is idle, which on a
                         non-routing box is the designed state.
  * aimesh_topology.html (v3.3.1) the stock AiMesh node card counts clientList rows
                         built from the same networkmap isOnline flag, so every
                         node card read 0 on the same box.

The fixes are cheap and the ways to lose them are cheaper: a sibling port that
drops a hunk, or a later refactor that "simplifies" the guard back. This test is
the tripwire.

WHAT IT DOES.
  1. Extracts reaper_socket_ceilings() from the real rc/firewall.c (brace-matched,
     not copied), compiles it on the host with fopen() redirected into a temp tree,
     runs it, and asserts the three /proc knobs get 16777216 / 16777216 / 4096.
  2. Asserts on the real source that BOTH paths reach it: the !is_routing_enabled()
     early return in start_firewall(), and the call in the body that routing mode
     still takes.
  3. Asserts www/Main_ReaperDash.asp resolves ROUTING from the operation mode, and
     that each of the three surfaces branches on it - the card, the live WAN poll
     and the client tiles - and that the non-routing collector reads reaper_dev.cgi
     WITH the CSRF token.
  4. Asserts others/reaper_diag's 12c svc() is operation-mode aware and that its
     routing-only note names the modes it applies to.
  5. Asserts the node-card path end to end: httpd/web.c records and emits the node
     each device hangs off ("via") from both cfg_mnt lists with this router as the
     default; aimesh_topology.html routes every client-list rebuild through the
     overlay, which is gated on the operation mode, reads reaper_dev.cgi with the
     token AiMesh.asp provides, and folds MLO links and nodes.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the
tree's release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("  ok  " + msg)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not src_root or not os.path.isdir(src_root):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")

FW   = os.path.join(src_root, "rc", "firewall.c")
DASH = os.path.join(src_root, "www", "Main_ReaperDash.asp")
DIAG = os.path.join(src_root, "others", "reaper_diag")
WEB  = os.path.join(src_root, "httpd", "web.c")
TOPO = os.path.join(src_root, "www", "aimesh", "aimesh_topology.html")
HOST = os.path.join(src_root, "www", "AiMesh.asp")
for p in (FW, DASH, DIAG, WEB, TOPO, HOST):
    if not os.path.isfile(p):
        skip("missing %s" % p)

def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

def extract(src, signature, where):
    """Return the whole function whose body opens after `signature`."""
    i = src.find(signature)
    if i < 0:
        die("%s: signature not found: %r" % (where, signature))
    j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1
    die("%s: unbalanced braces after %r" % (where, signature))

fw_src   = read(FW)
dash_src = read(DASH)
diag_src = read(DIAG)

# ---------------------------------------------------------------------------
# 1. the ceilings function does what it says, compiled from the real source
# ---------------------------------------------------------------------------
print("1. rc/firewall.c reaper_socket_ceilings()")

CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fn = extract(fw_src, "static void reaper_socket_ceilings(void)", "firewall.c")

# fopen() is redirected by string-pasting the caller's absolute /proc path onto a
# temp root, so the real knob values in the real source are what gets exercised.
harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *g_root;

static FILE *redir_fopen(const char *path, const char *mode)
{
	char buf[512];
	char *p;
	snprintf(buf, sizeof(buf), "%s%s", g_root, path);
	/* create the parent chain so the real absolute paths can be used verbatim */
	for (p = buf + strlen(g_root) + 1; *p; p++) {
		if (*p != '/') continue;
		*p = 0;
		if (mkdir_p(buf)) return NULL;
		*p = '/';
	}
	return fopen(buf, mode);
}

#define fopen(p, m) redir_fopen((p), (m))

__FN__

#undef fopen

int main(int argc, char **argv)
{
	if (argc < 2) return 2;
	g_root = argv[1];
	reaper_socket_ceilings();
	return 0;
}
'''
mkdir_p = r'''
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
static int mkdir_p(const char *d)
{
	if (mkdir(d, 0755) == 0) return 0;
	return (errno == EEXIST) ? 0 : -1;
}
'''
prog = mkdir_p + harness.replace("__FN__", fn)

tmp = tempfile.mkdtemp(prefix="apmode_")
try:
    csrc = os.path.join(tmp, "ceilings.c")
    cbin = os.path.join(tmp, "ceilings")
    with open(csrc, "w", encoding="utf-8") as f:
        f.write(prog)
    p = subprocess.run([CC, "-O0", "-w", "-o", cbin, csrc], capture_output=True, text=True)
    if p.returncode != 0:
        die("the extracted reaper_socket_ceilings() does not compile:\n" + p.stderr[:1500])
    root = os.path.join(tmp, "root")
    os.makedirs(root)
    p = subprocess.run([cbin, root], capture_output=True, text=True)
    if p.returncode != 0:
        die("reaper_socket_ceilings() exited %d" % p.returncode)

    want = {
        "proc/sys/net/core/rmem_max": "16777216",
        "proc/sys/net/core/wmem_max": "16777216",
        "proc/sys/net/core/netdev_max_backlog": "4096",
    }
    for rel, val in want.items():
        f = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(f):
            die("reaper_socket_ceilings() never wrote /%s" % rel)
        got = read(f).strip()
        if got != val:
            die("/%s got %r, want %r" % (rel, got, val))
        ok("/%s <- %s" % (rel, val))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
# 2. both paths reach it
# ---------------------------------------------------------------------------
print("2. rc/firewall.c start_firewall() reaches it in every operation mode")

start_fw = extract(fw_src, "int start_firewall(int wanunit, int lanunit)", "firewall.c")
if start_fw.count("reaper_socket_ceilings();") != 2:
    die("start_firewall() should call reaper_socket_ceilings() exactly twice "
        "(the non-routing return, and the routing body); found %d"
        % start_fw.count("reaper_socket_ceilings();"))
ok("start_firewall() calls it on both paths")

# the early return must call it BEFORE returning -1, or a non-routing box gets nothing
guard = start_fw[start_fw.index("if (!is_routing_enabled())"):]
guard = guard[:guard.index("return -1;") + len("return -1;")]
if "reaper_socket_ceilings();" not in guard:
    die("the !is_routing_enabled() early return does not call reaper_socket_ceilings() "
        "- AP, repeater and media-bridge boxes keep the stock ceiling")
ok("the !is_routing_enabled() return tunes before it returns")

# ---------------------------------------------------------------------------
# 3. the dashboard branches on the operation mode on all three surfaces
# ---------------------------------------------------------------------------
print("3. www/Main_ReaperDash.asp")

need = [
    ("var ROUTING=",
     "the page never resolves ROUTING from the operation mode"),
    ("function paintOpmodeWan()",
     "no non-routing painter for the Internet card"),
    ("if(!ROUTING){",
     "the Internet card render does not branch on the operation mode - it would "
     "paint a bridging box red again"),
    ("if(ROUTING) schedule(FAST); else paintOpmodeWan();",
     "the live WAN poll does not branch - it would re-paint Disconnected over the "
     "card every four seconds"),
    ("function pollClientsDev()",
     "no non-routing client collector"),
    ("var clientTick = ROUTING ? pollClients : pollClientsDev;",
     "the client tiles never dispatch to the non-routing collector"),
]
for token, why in need:
    if token not in dash_src:
        die("%s (missing: %s)" % (why, token))
    ok(token)

# the non-routing collector must read Reaper's own store, with the token
dev = extract(dash_src, "function pollClientsDev()", "Main_ReaperDash.asp")
if "/reaper_dev.cgi?action=status" not in dev:
    die("pollClientsDev() does not read reaper_dev.cgi - networkmap's isOnline is "
        "exactly what does not work here")
if "http_id=" not in dev:
    die("pollClientsDev() omits http_id - reaper_dev.cgi's action=status is gated "
        "and every request would be refused")
ok("pollClientsDev() reads reaper_dev.cgi with the CSRF token")

# it must not re-introduce the isOnline filter, and must fold what the Devices page folds
if "isOnline" in dev:
    die("pollClientsDev() consults isOnline - that is the networkmap flag this whole "
        "path exists to avoid")
for tok in ("d.mlo_link", "d.node"):
    if tok not in dev:
        die("pollClientsDev() does not fold %s - an MLO link or an AiMesh node would "
            "be counted as a client" % tok)
ok("no isOnline; MLO links and AiMesh nodes folded")

# ---------------------------------------------------------------------------
# 4. the diag does not warn about a routing-only daemon on a bridging box
# ---------------------------------------------------------------------------
print("4. others/reaper_diag 12c")

if "_ROUTING=1" not in diag_src:
    die("reaper_diag does not resolve the operation mode for 12c")
if 'case "$(nvram get sw_mode 2>/dev/null)" in 2|3)' not in diag_src:
    die("reaper_diag's 12c mode test does not name sw_mode 2 (repeater/media bridge) "
        "and 3 (access point)")
svc = diag_src[diag_src.index("svc() {"):]
svc = svc[:svc.index("\n}\n") + 3]
if 'if [ "$_ROUTING" = 0 ]; then' not in svc:
    die("svc() does not take a non-routing path - rtrafd, gkd and rchqd are all "
        "started behind !is_routing_enabled(), so idle is designed, not a fault")
if "routing-only" not in svc:
    die("svc()'s non-routing line does not say why the daemon is idle")
ok("svc() is operation-mode aware")

# ---------------------------------------------------------------------------
# 5. the AiMesh node card (v3.3.1)
# ---------------------------------------------------------------------------
print("5. AiMesh node card: httpd/web.c + www/aimesh/aimesh_topology.html + www/AiMesh.asp")
web_src, topo_src, host_src = read(WEB), read(TOPO), read(HOST)

s = web_src.index("struct rdev {")
if "char via[18];" not in web_src[s:web_src.index("};", s)]:
    die("struct rdev has no via field - the device store cannot say which node a "
        "client hangs off, and the node card has nothing to count against")
setter = extract(web_src, "static void rdev_set_via(struct rdev *d, const char *mac)", "web.c")
if "gk_valid_mac(" not in setter:
    die("rdev_set_via() does not validate the MAC - via is written into the JSON unescaped")
# the real definition of the scan (not a stub): the one carrying the station loop
i = web_src.find("static void rdev_scan_amesh(struct rdev *v, int *n)\n{")
if i < 0:
    die("rdev_scan_amesh() definition not found")
scan = extract(web_src[i:], "static void rdev_scan_amesh(struct rdev *v, int *n)", "web.c")
if "rdev_set_via(&v[idx], nodemac);" not in scan:
    die("rdev_scan_amesh() does not record the node a Wi-Fi client is listed under")
if "rdev_set_via(&v[idx], wnode);" not in scan:
    die("rdev_scan_amesh() does not record the node a wired client is cabled to")
if scan.index("rdev_set_via(&v[idx], nodemac);") > scan.index("if (v[idx].wifi) continue;"):
    die("via is recorded after the own-radio skip - clients of this router never get one")
if "rdev_set_via(&dev[i], self);" not in web_src or "get_lan_hwaddr();" not in web_src:
    die("the status action does not default via to this router")
if '\\"via\\":\\"%s\\"}' not in web_src:
    die("the status JSON does not emit via")
ok("web.c records via (Wi-Fi, wired, default) and emits it")

if topo_src.count("genClientList();") != 1:
    die("aimesh_topology.html calls genClientList() outside the overlay wrapper - "
        "that rebuild drops the non-routing rows and the card reads 0 again")
if topo_src.count("reaper_gen_client_list();") != 3:
    die("expected the three stock rebuild sites to route through reaper_gen_client_list()")
wrap = extract(topo_src, "function reaper_gen_client_list(){", "aimesh_topology.html")
if "reaper_ap_apply();" not in wrap:
    die("reaper_gen_client_list() does not apply the overlay after the rebuild")
gate = topo_src[topo_src.index("var reaperAp = {"):]
gate = gate[:gate.index("};")]
if 'sw_mode == "1"' not in gate or 'sw_mode == "4"' not in gate:
    die("the overlay is not gated on routing (sw_mode 1|4) - a routing box would take it")
fetch = extract(topo_src, "function reaper_ap_fetch(){", "aimesh_topology.html")
if '"/reaper_dev.cgi"' not in fetch or "http_id: REAPER_HTTPID" not in fetch or 'action: "status"' not in fetch:
    die("the overlay does not read reaper_dev.cgi action=status with the token")
if "30000" not in fetch:
    die("the overlay fetch is not cached - action=status popen()s wl per station on a "
        "single-flight httpd and the tree refreshes every 10 s")
apply_ = extract(topo_src, "function reaper_ap_apply(){", "aimesh_topology.html")
for tok in ("d.mlo_link", "d.node", "d.via", "amesh_papMac"):
    if tok not in apply_:
        die("reaper_ap_apply() does not handle %s" % tok)
if "d.isOnline" in apply_:
    die("reaper_ap_apply() consults networkmap's isOnline - the flag this path avoids")
if "var REAPER_HTTPID = '<% nvram_get(\"http_id\"); %>';" not in host_src:
    die("AiMesh.asp does not provide REAPER_HTTPID - every overlay request would be refused")
ok("topology overlay: every rebuild wrapped, mode-gated, cached, token-carrying, folds links and nodes")

# ---------------------------------------------------------------------------
# 6. v3.3.3: the get_clientlist hook itself carries the device store on a box that
#    is not routing, so the Network page cards, Parental Controls and the QoS
#    pickers fill without a per-page overlay; each device names its network.
# ---------------------------------------------------------------------------
print("6. get_clientlist hook: httpd/web.c merges the device store when not routing")

s = web_src.index("struct rdev {")
rdev_struct = web_src[s:web_src.index("};", s)]
for fld in ("char vif[16];", "int  unit;", "int  sdn;"):
    if fld not in rdev_struct:
        die("struct rdev lacks %r - a device cannot say which network it is on" % fld)
hook = extract(web_src, "static int ej_get_clientlist(int eid, webs_t wp, int argc, char_t **argv)", "web.c")
if "if(!have_nmp && !rdev_nonrouting()){" not in hook:
    die("the hook still answers empty without networkmap on a box that is not routing")
if "if (have_nmp)\n\t\tget_client_detail_info(clients, macArray, SHMKEY_LAN);" not in hook:
    die("the hook reads networkmap's shm even when networkmap is not running")
m = hook.find("if (rdev_nonrouting())\n\t\trdev_merge_clientlist(clients, macArray);")
if m < 0 or m > hook.index('json_object_object_add(clients, "maclist", macArray);'):
    die("the device store is not merged before the maclist is sealed")
# the DEFINITION, not the early prototype that shares its signature
i = web_src.find("static void rdev_merge_clientlist(struct json_object *clients, struct json_object *macArray)\n{")
if i < 0:
    die("rdev_merge_clientlist() definition not found")
merge = extract(web_src[i:], "static void rdev_merge_clientlist(struct json_object *clients, struct json_object *macArray)", "web.c")
if "rdev_snapshot(RDEV_TTL);" not in merge:
    die("the merge does not take the cached snapshot - the hook is polled every 10 s and the scan popen()s wl per VIF")
if "if (!d->online || d->node || d->bh_sta) continue;" not in merge or "if (mlo_link) continue;" not in merge:
    die("the merge does not leave nodes, backhaul stations and affiliated MLO links out")
for tok in ('"from", json_object_new_string("reaper_dev")', '"isOnline", json_object_new_string("1")',
            '"sdn_idx", json_object_new_string(sdn)', '"amesh_papMac", json_object_new_string(d->via)',
            "rdev_maclist_has(macArray, d->mac)"):
    if tok not in merge:
        die("the merge lacks %s" % tok)
i = web_src.find("static int rdev_nonrouting(void)\n{")
if i < 0:
    die("rdev_nonrouting() definition not found")
gate = extract(web_src[i:], "static int rdev_nonrouting(void)", "web.c")
if "SW_MODE_ROUTER" not in gate or "SW_MODE_HOTSPOT" not in gate:
    die("rdev_nonrouting() is not the routing-modes gate the tiles and the topology overlay use")
status = web_src[web_src.index("static void do_reaper_dev_cgi(char *url, FILE *stream)"):]
status = status[:status.index('/* ---------------- SET_NAME')]
if "rdev_snapshot(0);" not in status:
    die("the status action no longer takes a fresh pass")
if '\\"sdn\\":%d,\\"node\\":%d,\\"via\\":\\"%s\\"}' not in status:
    die("the status JSON does not emit the device's network")
fdb = extract(web_src, "static void rdev_scan_fdb(struct rdev *v, int *n)", "web.c")
if "get_mtlan(pmtl, &sz)" not in fdb or 'rdev_scan_fdb_br(v, n, "br0"' not in fdb:
    die("the bridge scan does not walk br0 plus every SDN bridge")
i = web_src.find("static void rdev_scan_amesh(struct rdev *v, int *n)\n{")
scan = extract(web_src[i:], "static void rdev_scan_amesh(struct rdev *v, int *n)", "web.c")
if "rdev_sta_sdn(staval)" not in scan or "rdev_sta_sdn(wval)" not in scan:
    die("the mesh scan does not record cfg_mnt's own network index for Wi-Fi and wired node clients")
ok("hook merges the store when not routing; nodes/links left out; snapshot cached; status fresh; sdn emitted")

# the three pure helpers, compiled from the real source against the in-tree json-c
jsonc = os.path.join(src_root, "json-c")
jsonc_srcs = [os.path.join(jsonc, f) for f in ("json_object.c", "json_tokener.c", "json_util.c", "linkhash.c",
              "arraylist.c", "printbuf.c", "debug.c", "random_seed.c", "json_c_version.c", "json_object_iterator.c")]
if all(os.path.isfile(p) for p in jsonc_srcs):
    bridge_fn = extract(web_src, "static int rdev_sdn_of_bridge(const char *br, MTLAN_T *pmtl, size_t sz)", "web.c")
    vif_in_fn = extract(web_src, "static int rdev_sdn_of_vif_in(json_object *list, const char *vif)", "web.c")
    i = web_src.find("static int rdev_sta_sdn(json_object *staval)\n{")
    sta_fn = extract(web_src[i:], "static int rdev_sta_sdn(json_object *staval)", "web.c")
    harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "json.h"
typedef struct { int enable; char name[64]; struct { char br_ifname[16]; } nw_t; struct { int sdn_idx; } sdn_t; } MTLAN_T;
''' + bridge_fn + "\n" + vif_in_fn + "\n" + sta_fn + r'''
static void row(MTLAN_T *m, int en, const char *name, const char *br, int idx)
{ m->enable = en; snprintf(m->name, sizeof(m->name), "%s", name); snprintf(m->nw_t.br_ifname, 16, "%s", br); m->sdn_t.sdn_idx = idx; }
int main(void)
{
	MTLAN_T t[5]; int fails = 0;
	row(&t[0], 1, "LAN", "br0", 0); row(&t[1], 1, "MAINFH", "br0", 4); row(&t[2], 1, "MAINFH", "br0", 3);
	row(&t[3], 1, "Guest", "br55", 5); row(&t[4], 0, "IoT", "br56", 6);
	if (rdev_sdn_of_bridge("br0", t, 5) != 3) { puts("br0 should map to the lowest MAINFH row (3)"); fails++; }
	if (rdev_sdn_of_bridge("br55", t, 5) != 5) { puts("br55 should map to its guest row (5)"); fails++; }
	if (rdev_sdn_of_bridge("br56", t, 5) != -1) { puts("a disabled row must not place a device"); fails++; }
	if (rdev_sdn_of_bridge("br99", t, 5) != -1) { puts("an unknown bridge must stay unknown"); fails++; }
	if (rdev_sdn_of_bridge("br0", t, 1) != 0) { puts("without a MAINFH row br0 is the LAN row (0)"); fails++; }
	{
		const char *js = "{\"vif_used\":{\"AA:BB:CC:DD:EE:FF\":[{\"sdn_idx\":\"3\",\"sdn_vid\":\"1\",\"sdn_band\":[{\"band_idx\":\"1\",\"wl_prefix\":\"wl0.1\",\"wl_ifname\":\"wl0.1\"},{\"wl_ifname\":\"wl1.1\"}]},{\"sdn_idx\":5,\"sdn_band\":[{\"wl_ifname\":\"wl0.2\"}]},{\"sdn_idx\":\"9\"}]}}";
		json_object *root = json_tokener_parse(js), *used = NULL, *list = NULL;
		if (!root || !json_object_object_get_ex(root, "vif_used", &used) || !json_object_object_get_ex(used, "AA:BB:CC:DD:EE:FF", &list)) { puts("fixture parse"); return 2; }
		if (rdev_sdn_of_vif_in(list, "wl1.1") != 3) { puts("wl1.1 should resolve to 3 (string sdn_idx)"); fails++; }
		if (rdev_sdn_of_vif_in(list, "wl0.2") != 5) { puts("wl0.2 should resolve to 5 (int sdn_idx)"); fails++; }
		if (rdev_sdn_of_vif_in(list, "wl9.9") != -1) { puts("an unmapped VIF must stay unknown"); fails++; }
		if (rdev_sdn_of_vif_in(NULL, "wl1.1") != -1 || rdev_sdn_of_vif_in(root, "wl1.1") != -1) { puts("a missing or non-array list must be rejected"); fails++; }
		json_object_put(root);
	}
	{
		json_object *a = json_tokener_parse("{\"sdn_idx\":\"5\"}"), *b = json_tokener_parse("{\"sdn_idx\":7}"), *c = json_tokener_parse("{\"mld_mac\":\"x\"}"), *d = json_tokener_parse("[1]");
		if (rdev_sta_sdn(a) != 5 || rdev_sta_sdn(b) != 7) { puts("sdn_idx as string and as int must both resolve"); fails++; }
		if (rdev_sta_sdn(c) != -1 || rdev_sta_sdn(d) != -1 || rdev_sta_sdn(NULL) != -1) { puts("a station without sdn_idx, a non-object or NULL must stay unknown"); fails++; }
		json_object_put(a); json_object_put(b); json_object_put(c); json_object_put(d);
	}
	return fails ? 1 : 0;
}
'''
    td = tempfile.mkdtemp(prefix="apmode-sdn-")
    csrc = os.path.join(td, "h.c"); cbin = os.path.join(td, "h")
    with open(csrc, "w") as f:
        f.write(harness)
    p = subprocess.run([CC, "-O0", "-w", "-I", jsonc, "-o", cbin, csrc] + jsonc_srcs + ["-lm"], capture_output=True, text=True)
    if p.returncode != 0:
        die("the extracted sdn helpers do not compile against the in-tree json-c:\n" + p.stderr[:2000])
    p = subprocess.run([cbin], capture_output=True, text=True)
    if p.returncode != 0:
        die("the sdn helpers misbehave:\n" + p.stdout)
    ok("rdev_sdn_of_bridge / rdev_sdn_of_vif_in / rdev_sta_sdn compiled from source: 13 checks pass")
    shutil.rmtree(td, ignore_errors=True)
else:
    ok("json-c sources absent - helper compile skipped, static checks above stand")

print("PASS: the non-routing paths are present on all six surfaces")
sys.exit(0)
