#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AP Isolation per network: Off / Wi-Fi only (default) / Wi-Fi and LAN ports (2026-11-19, owner).

WHY THIS EXISTS. Since GPL 102.40585 the firmware marks WIRED bridge members isolated too: after apg_start() /
apg_create_vlan_for_lan() with a main-network Wi-Fi interface's <if>_ap_isolate=1, the wired LAN ports of the main
bridge read /sys/class/net/<port>/brport/isolated = 1, and a guest bridge's wired trunk VLAN members are isolated
while that network's switch is on. Isolated bridge ports never forward to each other: with the option on, a wired TV
could not reach a wired NAS (field report). The GPL 102_39274 objects of the 3006.102.8 line never isolate a wired
member. The owner made it a choice per network - reaper_ap_isolate_lan (main network) and
apgN_ap_isolate_lan (the others): "1" = Wi-Fi and LAN ports, anything else = Wi-Fi only - and both lines must behave
the same. rc/lan.c reaper_brport_wired_open() (REAPER-BRPORT-WIRED) runs after each of those closed calls.

WHAT IT DOES. Compiles the REAPER-BRPORT-WIRED block on the host (its get_mtlan() / cfg_relist part,
REAPER-BRPORT-NETS, is replaced by stubs that read the networks and the AiMesh node MACs from the environment) and
runs it against a fake sysfs tree (brif/<port>/isolated and port_no, brforward records, wireless/ and phy80211):
  - Wi-Fi only: wired members 1 -> 0; Wi-Fi members (wl*, wds*, wireless/, phy80211) never written;
  - Wi-Fi and LAN ports: wired members 0 -> 1 except the uplink / WAN names, VLAN trunk members and a port an AiMesh
    node is learned on (port_hi too); ports isolated by someone else are left; a port that becomes a node port is
    opened again when this helper isolated it; what it isolated is remembered (state file, never through a link);
  - isolation off: only what this helper isolated is opened again;
  - guest bridges follow their own switch and choice; VLAN port isolation, a Guest Portal, MAINBH, a disabled network
    and a bridge of no network are never touched; a network riding the main bridge turns the main switch on;
  - one bounded log line, only when something changed; odd lan_ifname values are refused.
Then pins the wiring (every open-code apg_start() / apg_create_vlan_for_lan() call is followed by the helper, all
under RTCONFIG_MULTILAN_CFG; rc.h prototype; marker counts) and the keys (defaults.c rows, rc/init.c apgx_default[],
httpd/web.c rcfg_flags). The same file runs against every line's tree.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, struct, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
LAN = os.path.join(SRC, "rc", "lan.c") if SRC else ""
if not LAN or not os.path.isfile(LAN):
    skip("no router tree with rc/lan.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

def done():
    print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
    if fails:
        print("\n".join(fails))
    sys.exit(1 if fails else 0)

def rd(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read()

LOGSTR = "AP Isolation: wired ports opened / isolated: "
src = rd(LAN)
for mk in ("REAPER-BRPORT-WIRED-BEGIN", "REAPER-BRPORT-WIRED-END", "REAPER-BRPORT-PURE-BEGIN", "REAPER-BRPORT-PURE-END",
           "REAPER-BRPORT-NETS-BEGIN", "REAPER-BRPORT-NETS-END"):
    check("lan.c carries %s exactly once" % mk, src.count("/* %s */" % mk) == 1, src.count("/* %s */" % mk))
m = re.search(r"#ifdef RTCONFIG_MULTILAN_CFG\n/\* REAPER-BRPORT-WIRED-BEGIN \*/\n(.*?)/\* REAPER-BRPORT-WIRED-END \*/\n#endif\n", src, re.S)
check("the block sits inside its own #ifdef RTCONFIG_MULTILAN_CFG ... #endif", m is not None)
if not m:
    done()
block = m.group(1)
nets = re.search(r"/\* REAPER-BRPORT-NETS-BEGIN \*/\n(.*?)/\* REAPER-BRPORT-NETS-END \*/\n", block, re.S)
check("the network / node list part is marked", nets is not None)
if not nets:
    done()
check("the block is ASCII", all(ord(c) < 128 for c in block))
check("defined once: void reaper_brport_wired_open(void)", src.count("\nvoid reaper_brport_wired_open(void)\n{") == 1)
check("the block never writes nvram, runs a command or a shell",
      not re.search(r"\bnvram_(set|unset|commit|set_int|pf_set)\b|\beval\(|\bsystem\(|doSystem|_eval\(", block))
check("the log literal is in lan.c exactly once", src.count(LOGSTR) == 1)
check("the sysfs base and the state file are macros the test can move",
      '#ifndef REAPER_BRPORT_SYSFS\n#define REAPER_BRPORT_SYSFS\t"/sys/class/net"' in block
      and '#define REAPER_BRPORT_STATE\tREAPER_TMPDIR "/brport_iso"' in block)
check("the state file is read without following a link and written atomically in a checked directory",
      "open(REAPER_BRPORT_STATE, O_RDONLY | O_NOFOLLOW)" in block
      and "reaper_secure_dir(REAPER_BRPORT_STATE_DIR, 0700) == 0" in block
      and "reaper_write_atomic(REAPER_BRPORT_STATE, x.nstate, x.nsl, 0600)" in block)
check('the choice keys are read as "1" only: reaper_ap_isolate_lan, apgN_ap_isolate_lan',
      'return strcmp(nvram_safe_get(key), "1") == 0;' in block and 'reaper_brport_nv1("reaper_ap_isolate_lan")' in block
      and '"apg%d_ap_isolate_lan"' in block)
check("the main switch: every radio's wlN_ap_isolate", 'for (u = 0; u < MAX_NR_WL_IF; u++) {' in block
      and '"wl%d_ap_isolate"' in block)
check("the WAN names are never isolated; eth_ifnames / sta_* only outside router mode (in router mode eth_ifnames lists "
      "AiMesh backhaul CANDIDATES that are real LAN ports)",
      '{ "wan_ifnames", "wan0_ifname", "wan1_ifname", "wan2_ifname", "wan3_ifname",\n\t\t\t\t     "autowan_detected_ifname", NULL };' in block
      and '{ "eth_ifnames", "sta_ifnames", "sta_phy_ifnames", NULL };' in block
      and "for (u = 0; sw_mode() != SW_MODE_ROUTER && upl_nr[u]; u++)" in block)
_fn = block[block.find("\nvoid reaper_brport_wired_open(void)\n{"):]
check("an AiMesh node (re_mode) is left to the firmware: the helper returns before its lock, sysfs or log",
      re.search(r"\n\tif \(re_mode\(\)\)\n\t\treturn;\n\tif \(!\*l\)", _fn) is not None
      and 0 <= _fn.find("if (re_mode())") < _fn.find('file_lock("reaper_brport")'))
nb = nets.group(1)
check("networks come from get_mtlan(); disabled ones are marked", "get_mtlan(pmtl, &sz)" in nb and "m->enable == 1" in nb)
check("each network's switch: apmN for MAINFH and MAINBH, apgN for the others; no apg choice read for an apm network",
      'int apm = !strcmp(m->name, "MAINFH") || nw[n].mainbh;' in nb and '"%s%d_ap_isolate", apm ? "apm" : "apg"' in nb
      and 'if (!apm) {\n\t\t\t\t\tsnprintf(key, sizeof(key), "apg%d_ap_isolate_lan", m->sdn_t.apg_idx);' in nb)
check("VLAN port isolation, MAINBH and the portal profile (types 1, 2, 4; unreadable = portal) are read",
      "m->port_isolation" in nb and '"MAINBH"' in nb and "get_cp_type_byidx(m->sdn_t.cp_idx, &cpt)" in nb
      and "cpt.cp_type == 1 || cpt.cp_type == 2 || cpt.cp_type == 4" in nb and "nw[n].portal = 1;" in nb)
check("a network without a bridge of its own rides the main bridge", "m->nw_t.br_ifname[0] ? m->nw_t.br_ifname : lan" in nb)
check("the list is freed", "FREE_MTLAN((void *)pmtl);" in nb)
check("the AiMesh nodes come from the shared cfg_relist parser", "reaper_aimesh_macs(macs, REAPER_BRPORT_NODES, NULL)" in nb)
body = block[:nets.start()] + block[nets.end():]
check("nothing outside the marked part calls a closed AiMesh-group helper (both lines link the same code)",
      not re.search(r"\b(get_ap_iso_mode|get_port_iso_mode|get_fh_eth_ifnames|is_ap_group_if|set_brport_isolated|"
                    r"get_vlan_trunk_isolation)\(",re.sub(r"/\*.*?\*/", "", block, flags=re.S)))

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
#include <stdarg.h>
#include <sys/types.h>
/* nvram: T_NV = "key=value;key=value" */
static const char *nvram_safe_get(const char *k)
{
	static char out[8][256]; static int slot; const char *v = getenv("T_NV"), *p; size_t l = strlen(k);
	char *o = out[slot++ & 7];
	o[0] = 0;
	for (p = v; p && *p; ) {
		if (!strncmp(p, k, l) && p[l] == '=') {
			const char *e = strchr(p + l + 1, ';'); size_t n = e ? (size_t)(e - p - l - 1) : strlen(p + l + 1);
			if (n > 255) n = 255;
			memcpy(o, p + l + 1, n); o[n] = 0; return o;
		}
		p = strchr(p, ';'); if (p) p++;
	}
	return o;
}
static void logmessage(const char *h, const char *fmt, ...)
{ va_list ap; va_start(ap, fmt); printf("LOG %s: ", h); vprintf(fmt, ap); printf("\n"); va_end(ap); }
static int reaper_secure_dir(const char *path, int mode) { (void)path; (void)mode; return 0; }
#define SW_MODE_ROUTER 1
static int sw_mode(void) { const char *v = nvram_safe_get("sw_mode"); return *v ? atoi(v) : SW_MODE_ROUTER; }
static int re_mode(void) { return sw_mode() == 3 && !strcmp(nvram_safe_get("re_mode"), "1"); }
static int t_locked;
static int file_lock(const char *tag)
{ if (strcmp(tag, "reaper_brport") || t_locked) printf("LOCKERR %s\n", tag); t_locked = 1; return 7; }
static void file_unlock(int fd) { if (fd != 7 || !t_locked) printf("UNLOCKERR\n"); t_locked = 0; }
static int reaper_write_atomic(const char *path, const void *data, size_t len, int mode)
{ FILE *f = fopen(path, "w"); (void)mode; if (!f) return -1; fwrite(data, 1, len, f); fclose(f); return 0; }
struct reaper_brnet;
static int reaper_brport_nets(const char *lan, struct reaper_brnet *nw, int max);
static int reaper_brport_nodes(unsigned char (*nodes)[6], int max);
@BODY@
/* T_NETS = "br:enable:portal:port_iso:mainbh:ap_iso:lan_iso;..." (an empty br = rides the main bridge) */
static int reaper_brport_nets(const char *lan, struct reaper_brnet *nw, int max)
{
	char buf[1024], *p, *s, br[32]; int n = 0, f[6];
	const char *v = getenv("T_NETS");
	if (!v) return 0;
	snprintf(buf, sizeof(buf), "%s", v);
	for (p = strtok_r(buf, ";", &s); p && n < max; p = strtok_r(NULL, ";", &s)) {
		br[0] = 0;
		if (p[0] == ':') { if (sscanf(p, ":%d:%d:%d:%d:%d:%d", &f[0], &f[1], &f[2], &f[3], &f[4], &f[5]) != 6) continue; }
		else if (sscanf(p, "%31[^:]:%d:%d:%d:%d:%d:%d", br, &f[0], &f[1], &f[2], &f[3], &f[4], &f[5]) != 7) continue;
		memset(&nw[n], 0, sizeof(nw[n]));
		snprintf(nw[n].br, sizeof(nw[n].br), "%s", br[0] ? br : lan);
		nw[n].enable = f[0]; nw[n].portal = f[1]; nw[n].port_iso = f[2]; nw[n].mainbh = f[3];
		nw[n].ap_iso = f[4]; nw[n].lan_iso = f[5];
		n++;
	}
	return n;
}
/* T_NODES = "aa:bb:cc:dd:ee:ff;..." */
static int reaper_brport_nodes(unsigned char (*nodes)[6], int max)
{
	char buf[1024], *p, *s; unsigned int b[6]; int c = 0, k;
	const char *v = getenv("T_NODES");
	if (!v) return 0;
	snprintf(buf, sizeof(buf), "%s", v);
	for (p = strtok_r(buf, ";", &s); p && c < max; p = strtok_r(NULL, ";", &s)) {
		if (sscanf(p, "%2x:%2x:%2x:%2x:%2x:%2x", &b[0], &b[1], &b[2], &b[3], &b[4], &b[5]) != 6) continue;
		for (k = 0; k < 6; k++) nodes[c][k] = (unsigned char)b[k];
		c++;
	}
	return c;
}
int main(int argc, char **argv)
{
	if (argc > 1 && !strcmp(argv[1], "plan")) {
		struct reaper_brnet nw[REAPER_BRPORT_NETS]; struct reaper_brplan out[REAPER_BRPORT_NETS + 1];
		static const char *an[] = { "keep", "open", "close", "off", "openg" };
		int n = reaper_brport_nets("br0", nw, REAPER_BRPORT_NETS), k, i;
		k = reaper_brport_plan("br0", atoi(argv[2]), atoi(argv[3]), nw, n, out, REAPER_BRPORT_NETS + 1);
		for (i = 0; i < k; i++) printf("%s%s:%s", i ? " " : "", out[i].br, an[out[i].act]);
		printf("\n");
		return 0;
	}
	if (argc > 1 && !strcmp(argv[1], "tick")) {
		reaper_brport_tick_main(argc, argv);
	} else
		reaper_brport_wired_open();
	if (t_locked)
		printf("LOCKERR still held\n");
	return 0;
}
'''

tmp = tempfile.mkdtemp()
try:
    c = os.path.join(tmp, "b.c"); exe = os.path.join(tmp, "b"); root = os.path.join(tmp, "sys")
    state = os.path.join(tmp, "st", "brport_iso")
    os.makedirs(os.path.dirname(state))
    open(c, "w").write(MAIN.replace("@BODY@", body))
    r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-format-truncation", "-o", exe,
                        '-DREAPER_BRPORT_SYSFS="%s"' % root, '-DREAPER_BRPORT_STATE="%s"' % state,
                        '-DREAPER_BRPORT_STATE_DIR="%s"' % os.path.dirname(state),
                        "-DREAPER_BRPORT_NETS=32", "-DMAX_NR_WL_IF=4", c], capture_output=True, text=True)
    check("the block compiles with -Wall -Werror", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        done()

    def run(nv="", nets=None, nodes=None, *args):
        env = dict(os.environ); env["T_NV"] = nv
        for k, v in (("T_NETS", nets), ("T_NODES", nodes)):
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v
        p = subprocess.run([exe] + list(args), capture_output=True, text=True, env=env, timeout=20)
        return p.returncode, p.stdout

    def logs(out):
        return re.findall(r"^LOG reaper: " + re.escape(LOGSTR) + r"(\d+) / (\d+) \((.*)\)$", out, re.M)

    OLD = 1000000000
    def mk(br, members):
        """members: (name, value or None, kind, port_no) - kind wired / wireless (has wireless/) / phy (has phy80211)"""
        for mem in members:
            name, val, kind = mem[0], mem[1], mem[2]
            d = os.path.join(root, br, "brif", name)
            os.makedirs(d, exist_ok=True)
            os.makedirs(os.path.join(root, name), exist_ok=True)
            if val is not None:
                f = os.path.join(d, "isolated")
                open(f, "w").write(val)
                os.utime(f, (OLD, OLD))
            if len(mem) > 3:
                open(os.path.join(d, "port_no"), "w").write("0x%x\n" % mem[3])
            if kind == "wireless":
                os.makedirs(os.path.join(root, name, "wireless"), exist_ok=True)
            elif kind == "phy":
                os.makedirs(os.path.join(tmp, "phy0"), exist_ok=True)
                if not os.path.lexists(os.path.join(root, name, "phy80211")):
                    os.symlink(os.path.join(tmp, "phy0"), os.path.join(root, name, "phy80211"))

    def setf(br, name, v):
        f = os.path.join(root, br, "brif", name, "isolated")
        open(f, "w").write(v)
        os.utime(f, (OLD, OLD))

    def flag(br, name):
        f = os.path.join(root, br, "brif", name, "isolated")
        return open(f).read()[:1], os.stat(f).st_mtime == OLD

    def fdb(br, entries):
        """entries: (mac, port, local)"""
        b = b""
        for mac, port, local in entries:
            b += bytes(int(x, 16) for x in mac.split(":")) + struct.pack("<BBIBBH", port & 0xff, local, 0, port >> 8, 0, 0)
        open(os.path.join(root, br, "brforward"), "wb").write(b)

    def st():
        return open(state).read() if os.path.exists(state) else ""

    ON = "wl0_ap_isolate=1"
    # ---------------------------------------------------------------- no sysfs at all
    rc, out = run(ON, None)
    check("no sysfs tree: exit 0, no log line", rc == 0 and "LOG" not in out, out)

    # ---------------------------------------------------------------- main bridge, Wi-Fi only (the default)
    mk("br0", [("eth0", "1\n", "wired"), ("eth1", "1\n", "wired"), ("eth2", "0\n", "wired"), ("eth3", None, "wired"),
               ("eth4", "x\n", "wired"), ("wl0", "1\n", "wired"), ("wl0.1", "1\n", "wired"), ("wds0.0.1", "1\n", "wired"),
               ("ethW", "1\n", "wireless"), ("ethP", "1\n", "phy"), ("eth0.7", "1\n", "wired")])
    mk("br1", [("eth9", "1\n", "wired")])
    rc, out = run(ON, None)
    check("Wi-Fi only: exit 0", rc == 0, out)
    check("Wi-Fi only: wired eth0 / eth1 opened (1 -> 0)", flag("br0", "eth0")[0] == "0" and flag("br0", "eth1")[0] == "0")
    check("Wi-Fi only: an already-open port is not written", flag("br0", "eth2") == ("0", True))
    check("Wi-Fi only: an unreadable flag is left alone", flag("br0", "eth4") == ("x", True))
    check("Wi-Fi only: a member without the flag file is safe", not os.path.exists(os.path.join(root, "br0", "brif", "eth3", "isolated")))
    for w in ("wl0", "wl0.1", "wds0.0.1", "ethW", "ethP"):
        check("Wi-Fi only: Wi-Fi member %s keeps isolated=1, never written" % w, flag("br0", w) == ("1", True))
    check("Wi-Fi only: a bridge of no network (br1) is never touched", flag("br1", "eth9") == ("1", True))
    lm = logs(out)
    check("Wi-Fi only, main bridge: a VLAN trunk member is opened too (the owner's NAS case; Wi-Fi clients of different "
          "AiMesh nodes reach each other on the main network - the accepted trade-off)", flag("br0", "eth0.7")[0] == "0")
    check("Wi-Fi only: one log line, 3 opened / 0 isolated, names br0:-eth0,-eth1,-eth0.7 (any order)",
          len(lm) == 1 and lm[0][:2] == ("3", "0") and lm[0][2].startswith("br0:")
          and sorted(lm[0][2][4:].split(",")) == ["-eth0", "-eth0.7", "-eth1"], out)
    check("the run took and released the one leaf lock", "LOCKERR" not in out and "UNLOCKERR" not in out, out)
    check("Wi-Fi only: nothing remembered", st() == "")
    rc, out = run(ON, None)
    check("Wi-Fi only: a second run changes nothing and logs nothing", rc == 0 and "LOG" not in out, out)
    rc, out = run(ON + ";reaper_ap_isolate_lan=yes", None)
    check('a choice other than "1" is Wi-Fi only', rc == 0 and "LOG" not in out and flag("br0", "eth0")[0] == "0", out)

    # ---------------------------------------------------------------- main bridge, Wi-Fi and LAN ports
    shutil.rmtree(root)
    NODE1, NODE2, NODE3, OTHER = "02:aa:00:00:00:01", "02:aa:00:00:00:02", "02:aa:00:00:00:03", "02:bb:00:00:00:09"
    mk("br0", [("eth0", "0\n", "wired", 1), ("eth1", "0\n", "wired", 2), ("eth2", "0\n", "wired", 3),
               ("eth3", "0\n", "wired", 4), ("eth0.5", "0\n", "wired", 5), ("eth6", "0\n", "wired", 6),
               ("eth7", "1\n", "wired", 7), ("eth8", "0\n", "wired", 0x101), ("wl0", "0\n", "wired", 8),
               ("ethW", "0\n", "wireless", 9)])
    fdb("br0", [(NODE1, 6, 0), (NODE2, 7, 0), (NODE1, 1, 1), (OTHER, 2, 0), (NODE3, 0x101, 0)])
    # router mode: eth_ifnames = AiMesh Ethernet-backhaul candidates, real LAN ports (RT-BE96U "eth0 eth5")
    LANM = ON + ";reaper_ap_isolate_lan=1;wan_ifnames=eth3;wan0_ifname=eth4;eth_ifnames=eth0 eth2"
    NODES = ";".join([NODE1, NODE2, NODE3])
    rc, out = run(LANM, None, NODES)
    check("LAN ports: exit 0", rc == 0, out)
    check("LAN ports: wired eth0 / eth1 / eth2 isolated (0 -> 1)",
          all(flag("br0", p)[0] == "1" for p in ("eth0", "eth1", "eth2")), out)
    check("LAN ports, router mode: ports named in eth_ifnames (AiMesh backhaul candidates, eth0 eth2) are isolated "
          "like any LAN port - the AiMesh check is the forwarding table", flag("br0", "eth0")[0] == "1" and flag("br0", "eth2")[0] == "1")
    check("LAN ports: a WAN name (wan_ifnames) is never isolated", flag("br0", "eth3") == ("0", True))
    check("LAN ports: a VLAN trunk member is never isolated", flag("br0", "eth0.5") == ("0", True))
    check("LAN ports: a port an AiMesh node is learned on is never isolated", flag("br0", "eth6") == ("0", True))
    check("LAN ports: a node port above 255 (port_hi) is recognised", flag("br0", "eth8") == ("0", True))
    check("LAN ports: the bridge's own entry with a node MAC does not exclude a port, another MAC does not either",
          flag("br0", "eth0")[0] == "1" and flag("br0", "eth1")[0] == "1")
    check("LAN ports: a node port someone else isolated is left as it is", flag("br0", "eth7") == ("1", True))
    check("LAN ports: Wi-Fi members never written", flag("br0", "wl0") == ("0", True) and flag("br0", "ethW") == ("0", True))
    lm = logs(out)
    check("LAN ports: one log line, 0 opened / 3 isolated", len(lm) == 1 and lm[0][:2] == ("0", "3")
          and sorted(lm[0][2][4:].split(",")) == ["+eth0", "+eth1", "+eth2"] and lm[0][2].startswith("br0:"), out)
    check("LAN ports: the isolated ports are remembered, the excluded ones are not",
          sorted(st().split("\n")) == ["", "br0 eth0", "br0 eth1", "br0 eth2"], st())
    rc, out = run(LANM, None, NODES)
    check("LAN ports: a second run changes nothing", rc == 0 and "LOG" not in out, out)
    # a node now learned on eth1: this helper isolated it -> opened again, forgotten
    fdb("br0", [(NODE1, 6, 0), (NODE2, 7, 0), (NODE3, 0x101, 0), (NODE2, 2, 0)])
    rc, out = run(LANM, None, NODES)
    lm = logs(out)
    check("LAN ports: a port that becomes a node port is opened again when this helper isolated it",
          flag("br0", "eth1")[0] == "0" and len(lm) == 1 and lm[0] == ("1", "0", "br0:-eth1")
          and "br0 eth1" not in st(), out)
    # isolation switched off: only what this helper isolated is opened
    setf("br0", "eth3", "1\n")      # somebody else's isolation
    rc, out = run("wl0_ap_isolate=0;reaper_ap_isolate_lan=1", None, NODES)
    lm = logs(out)
    check("off: the ports this helper isolated are opened, nothing else",
          flag("br0", "eth0")[0] == "0" and flag("br0", "eth2")[0] == "0" and flag("br0", "eth3") == ("1", True)
          and flag("br0", "eth7") == ("1", True) and len(lm) == 1 and lm[0][:2] == ("2", "0") and st() == "", out)
    rc, out = run("", None, NODES)
    check("off: a second run changes nothing", rc == 0 and "LOG" not in out, out)
    # LAN ports again, then Wi-Fi only: everything wired opens, ASUS's eth7 too
    rc, out = run(LANM, None, NODES)
    check("LAN ports again: eth0 / eth2 isolated", flag("br0", "eth0")[0] == "1" and flag("br0", "eth2")[0] == "1", out)
    rc, out = run(ON, None, NODES)
    check("then Wi-Fi only: every wired member opens (the ones isolated by someone else too), nothing remembered",
          all(flag("br0", p)[0] == "0" for p in ("eth0", "eth2", "eth3", "eth7")) and st() == "", out)
    # the state file is never read through a link
    setf("br0", "eth0", "1\n")
    if os.path.lexists(state):
        os.unlink(state)
    os.symlink(os.path.join(tmp, "elsewhere"), state)
    open(os.path.join(tmp, "elsewhere"), "w").write("br0 eth0\n")
    rc, out = run("", None, None)
    check("a state file that is a link is not read (off: eth0 stays isolated)", flag("br0", "eth0") == ("1", True), out)
    os.unlink(state)

    # ---------------------------------------------------------------- the other networks' bridges
    shutil.rmtree(root)
    mk("br0", [("eth0", "1\n", "wired", 1)])
    mk("br52", [("eth0.52", "1\n", "wired", 2), ("wl0.2", "1\n", "wired", 3), ("eth5", "1\n", "wired", 4)])  # on, Wi-Fi only
    mk("br60", [("eth2.60", "0\n", "wired", 2), ("eth9", "0\n", "wired", 3), ("wl0.3", "0\n", "wired", 4)])  # on, LAN ports
    mk("br53", [("eth1.53", "1\n", "wired", 2), ("eth5", "1\n", "wired", 3)])        # VLAN port isolation
    mk("br54", [("eth0.54", "1\n", "wired", 2), ("eth6", "0\n", "wired", 3)])        # Guest Portal
    mk("br55", [("eth0.55", "1\n", "wired", 2)])                                      # disabled
    mk("br56", [("eth0.56", "1\n", "wired", 2)])                                      # shared with port isolation
    mk("br57", [("eth0.57", "1\n", "wired", 2), ("eth8", "0\n", "wired", 3)])        # MAINBH
    mk("br59", [("eth10", "0\n", "wired", 2)])                                        # two networks, one LAN ports
    mk("br61", [("eth0.61", "1\n", "wired", 2), ("eth11", "1\n", "wired", 3)])       # switch off
    NETS = ";".join([":1:0:0:0:0:0",                     # the main network
                     "br52:1:0:0:0:1:0", "br60:1:0:0:0:1:1", "br53:1:0:1:0:1:1", "br54:1:1:0:0:1:1",
                     "br55:0:0:0:0:1:1", "br56:1:0:0:0:1:1", "br56:1:0:1:0:0:0", "br57:1:0:0:1:1:1",
                     "br58:1:0:0:0:1:0", "br59:1:0:0:0:0:0", "br59:1:0:0:0:1:1", "br61:1:0:0:0:0:1"])
    rc, out = run("", NETS, None, "plan", "0", "0")
    check("plan: main first (off), then each eligible bridge once with its own switch and choice",
          out.split() == ["br0:off", "br52:openg", "br60:close", "br58:openg", "br59:close", "br61:off"], out)
    rc, out = run("", ":1:0:0:0:0:0;:1:0:1:0:1:0", None, "plan", "0", "1")
    check("plan: a network riding the main bridge with its switch on turns the main switch on (and port isolation "
          "there does not keep the main bridge)", out.split() == ["br0:close"], out)
    rc, out = run("", NETS, None, "plan", "1", "0")
    check("plan: the main switch and choice", out.split()[0] == "br0:open", out)
    rc, out = run("", ":1:0:0:0:0:0;:1:0:0:1:1:1", None, "plan", "0", "1")
    check("plan: MAINBH riding the main bridge with its apm switch on does not turn the main switch on",
          out.split() == ["br0:off"], out)
    rc, out = run("", NETS, None)
    check("nets: exit 0 (br58 has no sysfs directory - safe)", rc == 0, out)
    check("nets: main switch off - the main bridge is left as it is", flag("br0", "eth0") == ("1", True))
    check("nets: Wi-Fi only guest bridge - the wired access port opened, the VLAN trunk (to an AiMesh node or a switch) "
          "left as the firmware set it (Wi-Fi guests of different nodes stay apart), Wi-Fi member kept",
          flag("br52", "eth5")[0] == "0" and flag("br52", "eth0.52") == ("1", True) and flag("br52", "wl0.2") == ("1", True))
    check("nets: LAN ports guest bridge - the access port isolated, the trunk and Wi-Fi left",
          flag("br60", "eth9")[0] == "1" and flag("br60", "eth2.60") == ("0", True) and flag("br60", "wl0.3") == ("0", True))
    check("nets: a network with VLAN port isolation is left alone",
          flag("br53", "eth1.53") == ("1", True) and flag("br53", "eth5") == ("1", True))
    check("nets: a Guest Portal bridge is left alone", flag("br54", "eth0.54") == ("1", True) and flag("br54", "eth6") == ("0", True))
    check("nets: a disabled network's bridge is left alone", flag("br55", "eth0.55") == ("1", True))
    check("nets: a bridge shared with a port-isolated network is left alone", flag("br56", "eth0.56") == ("1", True))
    check("nets: the AiMesh backhaul network (MAINBH) is left alone",
          flag("br57", "eth0.57") == ("1", True) and flag("br57", "eth8") == ("0", True))
    check("nets: a bridge two networks share follows the one with its switch on", flag("br59", "eth10")[0] == "1")
    check("nets: switch off and nothing remembered - left as it is",
          flag("br61", "eth0.61") == ("1", True) and flag("br61", "eth11") == ("1", True))
    lm = logs(out)
    check("nets: one log line, 1 opened / 2 isolated, per-bridge names",
          len(lm) == 1 and lm[0] == ("1", "2", "br52:-eth5 br60:+eth9 br59:+eth10"), out)
    check("nets: remembered per bridge", sorted(st().split("\n")) == ["", "br59 eth10", "br60 eth9"], st())
    NETS_OFF = NETS.replace("br60:1:0:0:0:1:1", "br60:1:0:0:0:0:1")
    rc, out = run("", NETS_OFF, None)
    check("nets: a guest network's switch turned off opens only what this helper isolated there",
          flag("br60", "eth9")[0] == "0" and flag("br59", "eth10")[0] == "1" and logs(out)[0][:2] == ("1", "0"), out)

    # ---------------------------------------------------------------- the rwatch tick (/sbin/reaper_brport)
    shutil.rmtree(root)
    if os.path.lexists(state):
        os.unlink(state)
    mk("br0", [("eth0", "1\n", "wired", 1), ("eth1", "0\n", "wired", 2)])
    mk("br52", [("eth5", "0\n", "wired", 4)])
    TN = ":1:0:0:0:0:0;br52:1:0:0:0:1:1"
    for nv, why in (("wl0_ap_isolate=1", "switch on, Wi-Fi only"),
                    ("reaper_ap_isolate_lan=1", "main LAN ports chosen, no switch on"),
                    ("apg3_ap_isolate_lan=1", "a network's LAN ports chosen, its switch off"),
                    ("wl0_ap_isolate=1;apg3_ap_isolate_lan=1;reaper_ap_isolate_lan=0", "LAN ports only where the switch is off")):
        rc, out = run(nv, TN, None, "tick")
        check("tick: does nothing when no network has its switch on with Wi-Fi and LAN ports (%s)" % why,
              rc == 0 and "LOG" not in out and "LOCK" not in out and flag("br0", "eth0") == ("1", True)
              and flag("br52", "eth5") == ("0", True), out)
    rc, out = run("wl1_ap_isolate=1;reaper_ap_isolate_lan=1", ":1:0:0:0:0:0;br52:1:0:0:0:0:0", None, "tick")
    lm = logs(out)
    check("tick: main switch on (a radio) with Wi-Fi and LAN ports - runs (eth1 isolated, eth0 left, br52 off)",
          flag("br0", "eth1")[0] == "1" and flag("br0", "eth0") == ("1", True) and flag("br52", "eth5") == ("0", True)
          and len(lm) == 1 and lm[0][:2] == ("0", "1") and "LOCK" not in out, out)
    rc, out = run("apg2_ap_isolate=1;reaper_ap_isolate_lan=1", ":1:0:0:0:0:0;:1:0:0:0:1:0", None, "tick")
    check("tick: a network riding the main bridge with its switch on counts for the main choice (runs, nothing new)",
          rc == 0 and "LOCK" not in out and "LOG" not in out and flag("br0", "eth1")[0] == "1", out)
    rc, out = run("apg3_ap_isolate=1;apg3_ap_isolate_lan=1", TN, None, "tick")
    lm = logs(out)
    check("tick: a network with its own choice - runs (br52 eth5 isolated; main switch off: eth0 and eth1, both remembered "
          "from the Wi-Fi and LAN ports run, opened)",
          flag("br52", "eth5")[0] == "1" and flag("br0", "eth1")[0] == "0" and flag("br0", "eth0")[0] == "0"
          and len(lm) == 1 and lm[0][:2] == ("2", "1"), out)
    rc, out = run("apg3_ap_isolate=1;apg3_ap_isolate_lan=1", TN, None, "tick")
    check("tick: a second tick changes nothing and logs nothing", rc == 0 and "LOG" not in out, out)

    # ---------------------------------------------------------------- operation modes
    shutil.rmtree(root)
    if os.path.lexists(state):
        os.unlink(state)
    mk("br0", [("eth0", "0\n", "wired", 1), ("eth5", "0\n", "wired", 2), ("eth6", "1\n", "wired", 3), ("wl0", "1\n", "wired", 4)])
    rc, out = run("sw_mode=3;wl0_ap_isolate=1;reaper_ap_isolate_lan=1;eth_ifnames=eth5", None, None)
    check("AP mode, LAN ports: the uplink (eth_ifnames) is never isolated, the other LAN port is",
          flag("br0", "eth5") == ("0", True) and flag("br0", "eth0")[0] == "1", out)
    setf("br0", "eth0", "0\n")
    for nv, why in (("sw_mode=3;re_mode=1;wl0_ap_isolate=1", "Wi-Fi only"),
                    ("sw_mode=3;re_mode=1;wl0_ap_isolate=1;reaper_ap_isolate_lan=1", "Wi-Fi and LAN ports")):
        before = st()
        rc, out = run(nv, None, None)
        check("AiMesh node (re_mode), %s: nothing touched, nothing logged, no lock, no state written" % why,
              rc == 0 and "LOG" not in out and "LOCK" not in out and flag("br0", "eth0") == ("0", True)
              and flag("br0", "eth6") == ("1", True) and st() == before, out)
        rc, out = run(nv, None, None, "tick")
        check("AiMesh node (re_mode), %s: the tick does nothing either" % why,
              rc == 0 and "LOG" not in out and "LOCK" not in out and flag("br0", "eth0") == ("0", True)
              and flag("br0", "eth6") == ("1", True), out)
    rc, out = run("sw_mode=1;re_mode=1;wl0_ap_isolate=1", None, None)
    check("a stale re_mode=1 in router mode is not a node (re_mode() needs AP mode): Wi-Fi only opens eth6",
          flag("br0", "eth6")[0] == "0", out)

    # ---------------------------------------------------------------- odd lan_ifname values are refused safely
    rc, out = run(ON + ";lan_ifname=../etc", None)
    check("lan_ifname with a slash: nothing touched, no log", rc == 0 and "LOG" not in out, out)
    rc, out = run(ON + ";lan_ifname=br0123456789abcdef", None)
    check("an over-long lan_ifname: nothing touched, no log", rc == 0 and "LOG" not in out, out)

    # ---------------------------------------------------------------- many ports: the log line stays bounded
    shutil.rmtree(root)
    mk("br0", [("eth%02d" % i, "1\n", "wired") for i in range(40)])
    rc, out = run(ON, None)
    lm = logs(out)
    check("40 ports: all opened, 40 / 0, names bounded and marked ' ...'",
          len(lm) == 1 and lm[0][:2] == ("40", "0") and len(lm[0][2]) < 128 and lm[0][2].endswith(" ...")
          and all(flag("br0", "eth%02d" % i)[0] == "0" for i in range(40)), out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- wiring
def guarded(text, pos, sym="RTCONFIG_MULTILAN_CFG"):
    """True when the line at pos sits in an #if branch that requires sym."""
    stack = []
    for ln in text[:pos].split("\n"):
        t = ln.strip()
        if re.match(r"#\s*if(n?def)?\b", t):
            neg = t.startswith("#ifndef") or bool(re.match(r"#\s*if\s+!", t))
            stack.append([t, neg])
        elif re.match(r"#\s*elif\b", t) and stack:
            stack[-1] = [t, False]
        elif re.match(r"#\s*else\b", t) and stack:
            stack[-1][1] = not stack[-1][1]
        elif re.match(r"#\s*endif\b", t) and stack:
            stack.pop()
    return any(sym in c and not neg for c, neg in stack)

calls = 0
for fn in sorted(os.listdir(os.path.join(SRC, "rc"))):
    if not fn.endswith(".c"):
        continue
    t = rd(os.path.join(SRC, "rc", fn))
    for mm in re.finditer(r"\n([ \t]*)(apg_start|apg_create_vlan_for_lan)\(\);[^\n]*\n([ \t]*)([^\n]*)", t):
        nxt = mm.group(4).strip()
        check("rc/%s: %s() at line %d is followed by reaper_brport_wired_open()"
              % (fn, mm.group(2), t.count("\n", 0, mm.start()) + 2), nxt == "reaper_brport_wired_open();", nxt)
        check("rc/%s: that call is under RTCONFIG_MULTILAN_CFG" % fn, guarded(t, mm.end()))
    if fn == "lan.c":
        t = t.replace(m.group(0), "")	# the tick applet inside the block calls it too: not a call site
    calls += len(re.findall(r"\n[ \t]+reaper_brport_wired_open\(\);", t))
check("five call sites in rc/*.c (lan.c 2, rc.c 1, services.c 2)", calls == 5, calls)
for fn, want in (("lan.c", 2), ("rc.c", 1), ("services.c", 2)):
    t = rd(os.path.join(SRC, "rc", fn)).replace(m.group(0), "")
    check("rc/%s carries %d call(s)" % (fn, want), len(re.findall(r"\n[ \t]+reaper_brport_wired_open\(\);", t)) == want)
rch = rd(os.path.join(SRC, "rc", "rc.h"))
pp = rch.find("extern void reaper_brport_wired_open(void);")
check("rc.h: prototype exactly once", rch.count("extern void reaper_brport_wired_open(void);") == 1)
check("rc.h: prototype under RTCONFIG_MULTILAN_CFG", pp >= 0 and guarded(rch, pp))
check("rc.h: REAPER-BRPORT-WIRED exactly once", rch.count("REAPER-BRPORT-WIRED") == 1)
check("no file keeps the first draft's name", all("reaper_main_brport_wired_open" not in rd(os.path.join(SRC, "rc", f))
                                                  for f in ("lan.c", "rc.c", "services.c", "rc.h")))

# ---------------------------------------------------------------- the rwatch tick and its lock
check("the helper runs under file_lock(\"reaper_brport\"), released before the log line; no other lock inside the block",
      block.count('lock = file_lock("reaper_brport");') == 1 and block.count("file_unlock(lock);") == 1
      and re.sub(r"/\*.*?\*/", "", block, flags=re.S).count("file_lock(") == 1
      and block.index('file_lock("reaper_brport")') < block.index("file_unlock(lock);") < block.index(LOGSTR))
check("the tick applet runs the helper only behind the nvram gate",
      "int reaper_brport_tick_main(int argc, char *argv[])" in block
      and "if (reaper_brport_lan_wanted())\n\t\treaper_brport_wired_open();" in block)
gate = block[block.index("static int reaper_brport_lan_wanted(void)"):block.index("int reaper_brport_tick_main(")]
check("the gate reads nvram only (no sysfs, no file, no lock)",
      not re.search(r"\b(open|fopen|opendir|access|file_lock|reaper_brport_bridge|REAPER_BRPORT_SYSFS)\b", gate), gate)
rcc = rd(os.path.join(SRC, "rc", "rc.c"))
ap = rcc.find('\t{ "reaper_brport",\t\treaper_brport_tick_main\t\t\t},')
check("rc.c: the reaper_brport applet, once, under RTCONFIG_MULTILAN_CFG",
      rcc.count('"reaper_brport"') == 1 and ap >= 0 and guarded(rcc, ap))
check("rc.h: the applet's prototype under RTCONFIG_MULTILAN_CFG",
      rch.count("extern int reaper_brport_tick_main(int argc, char *argv[]);") == 1
      and guarded(rch, rch.find("extern int reaper_brport_tick_main")))
mkf = rd(os.path.join(SRC, "rc", "Makefile"))
check("rc/Makefile: /sbin/reaper_brport symlink only where the applet exists (RTCONFIG_MULTILAN_CFG)",
      re.search(r"\nifeq \(\$\(RTCONFIG_MULTILAN_CFG\),y\)\n#[^\n]*\n\t@cd \$\(INSTALLDIR\)/sbin && ln -sf rc reaper_brport\nendif\n", mkf)
      is not None and mkf.count("ln -sf rc reaper_brport\n") == 1)
rw = rd(os.path.join(SRC, "rc", "rwatch.c"))
check("rwatch.c: the tick runs /sbin/reaper_brport once, guarded by -x, output dropped",
      rw.count('"[ -x /sbin/reaper_brport ] && /sbin/reaper_brport >/dev/null 2>&1\\n"') == 1
      and rw.count("/sbin/reaper_brport") == 2)

# ---------------------------------------------------------------- the keys
dfl = rd(os.path.join(SRC, "shared", "defaults.c"))
check('defaults.c: template row apg_ap_isolate_lan "0" (httpd saves apgN_* only with a template row)',
      len(re.findall(r'\n\t\{ "apg_ap_isolate_lan", "0", CKN_STR1, CKN_TYPE_DEFAULT,', dfl)) == 1)
check('defaults.c: reaper_ap_isolate_lan "0" (main network)',
      len(re.findall(r'\n\t\{ "reaper_ap_isolate_lan", "0", CKN_STR1, CKN_TYPE_DEFAULT,', dfl)) == 1)
ini = rd(os.path.join(SRC, "rc", "init.c"))
tbl = re.search(r"apgx_default\[\] = \{(.*?)\{\s*NULL,\s*NULL", ini, re.S)
check('rc/init.c: apgx_default[] seeds ap_isolate_lan "0" (and restore unsets it)',
      tbl is not None and len(re.findall(r'\{\s*"ap_isolate_lan",\s*"0"\s*\}', tbl.group(1))) == 1)
web = rd(os.path.join(SRC, "httpd", "web.c"))
rf = re.search(r"rcfg_flags\[\] = \{(.*?)\n\};", web, re.S)
check("httpd/web.c: rcfg_flags carries reaper_ap_isolate_lan (misc, 0 / 1)",
      rf is not None and rf.group(1).count('{ "misc",   "reaper_ap_isolate_lan", 2 }') == 1)
done()
