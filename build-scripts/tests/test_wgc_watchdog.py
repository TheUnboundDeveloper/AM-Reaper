#!/usr/bin/env python3
"""A WireGuard client used by a guest network: back after a reboot, started on demand (field report, 2026-11-14).

WHY. A Guest Portal network was bound to a WireGuard client (a commercial VPN). After a router reboot the tunnel never
came up, and joining the guest network did not start it; the Kill Switch then left the guests with no Internet until
the admin restarted the client by hand. Two causes in the code:
  - the every-minute check (rc/wireguard.c check_wgc_endpoint) restarted a client that is not connected only when its
    server NAME resolved to an address other than the stored one, and tested that with strstr(now, stored). When the
    name had not resolved at start (DNS not up yet at boot) nothing was stored, strstr(now, "") is always true, and
    that client was never restarted. A server given as an address was never looked at;
  - nothing started a bound client that was not running: not the Network page's save, not rc after a network change.

WHAT CHANGED. reaper_wgc_wd_reason() decides (interface gone / name resolves now / address changed / down 5 minutes),
restarts back off 1, 2, 4, 8, then 15 minutes. rc starts a client that an enabled network uses, that is switched on and
has no interface (reaper_wgc_start_bound, after restart_sdn; never before the clock is set; rc never switches a client
on itself). The Network page switches a chosen client on with the same save (reaper_vpnc_on_demand) and never off.

WHAT IT DOES. Compiles the REAPER-WGC-WD block on the host and runs the cases; pins the call site, the bound-client
start and its hook; runs the page's helper under node. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree -
argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WG = os.path.join(SRC, "rc", "wireguard.c") if SRC else ""
if not WG or not os.path.isfile(WG):
    skip("no router tree with rc/wireguard.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

wg = read("rc/wireguard.c")
m = re.search(r"/\* REAPER-WGC-WD-BEGIN.*?\*/(.*?)/\* REAPER-WGC-WD-END \*/", wg, re.S)
check("wireguard.c carries the REAPER-WGC-WD block", m is not None)

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
@@PURE@@
int main(int argc, char **argv)
{
	/* if_exists is_ip resolved now stored down_for */
	const char *r = reaper_wgc_wd_reason(atoi(argv[1]), atoi(argv[2]), atoi(argv[3]), argv[4], argv[5], atol(argv[6]));
	int i;
	printf("%s\n", r ? r : "-");
	for (i = 0; i <= 7; i++) printf("%ld ", reaper_wgc_wd_wait(i));
	printf("\n");
	return 0;
}
'''
if m:
    with tempfile.TemporaryDirectory() as td:
        c, exe = os.path.join(td, "w.c"), os.path.join(td, "w")
        open(c, "w").write(HARNESS.replace("@@PURE@@", m.group(1)))
        r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-Darm=1", "-o", exe, c], capture_output=True, text=True)
        check("the watchdog block compiles on the host (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            def why(if_exists, is_ip, resolved, now, stored, down):
                return subprocess.run([exe, str(if_exists), str(is_ip), str(resolved), now, stored, str(down)],
                                      capture_output=True, text=True).stdout.split("\n")
            check("interface gone: restart", why(0, 0, 1, "192.0.2.1", "192.0.2.1", 0)[0] == "its interface is missing")
            check("THE REPORT: the name resolves now and nothing was stored at start (boot before DNS): restart",
                  why(1, 0, 1, "192.0.2.1 192.0.2.2", "", 0)[0] == "its server name resolves now")
            check("the name resolves to other addresses than the stored one: restart (stock's case)",
                  why(1, 0, 1, "192.0.2.9 192.0.2.8", "192.0.2.1", 0)[0] == "its server address changed")
            check("the stored address is still among the answers: no restart for that",
                  why(1, 0, 1, "192.0.2.9 192.0.2.1", "192.0.2.1", 60)[0] == "-")
            check("whole addresses, not substrings: stored 192.0.2.1 is not found in 192.0.2.10 / 1192.0.2.1",
                  why(1, 0, 1, "192.0.2.10 1192.0.2.1", "192.0.2.1", 0)[0] == "its server address changed")
            check("a name that does not resolve yet: wait (nothing to gain from a restart)", why(1, 0, 0, "", "", 120)[0] == "-")
            check("down for 5 minutes: restart, also for a server given as an address (never checked by stock)",
                  why(1, 1, 0, "", "192.0.2.1", 300)[0] == "no handshake for 5 minutes" and why(1, 1, 0, "", "192.0.2.1", 299)[0] == "-"
                  and why(1, 0, 1, "192.0.2.1", "192.0.2.1", 301)[0] == "no handshake for 5 minutes")
            check("back-off after the n-th restart: 0, 1, 2, 4, 8, then 15 minutes",
                  why(1, 1, 0, "", "", 0)[1].split() == ["0", "60", "120", "240", "480", "900", "900", "900"])

body = wg[wg.find("void check_wgc_endpoint()"):]
body = body[:body.find("\n}\n")]
check("check_wgc_endpoint: the always-true strstr test is gone; the decision function is asked instead",
      "if (!strstr(buf, ep_addr_r))" not in wg
      and "why = reaper_wgc_wd_reason(_wg_if_exist(wd_if), is_ip, resolved, buf, ep_addr_r, now - since);" in body)
check("check_wgc_endpoint: the first restart is at once, later ones wait; one log line per restart; state kept per client",
      "if (why && (tries == 0 || now - last >= reaper_wgc_wd_wait(tries))) {" in body
      and 'logmessage("WireGuard", "client %d is not connected: %s - restarting it (try %d)", unit, why, tries);' in body
      and 'snprintf(wdf, sizeof(wdf), "%s/wd%d", WG_DIR_CONF, unit);' in body
      and "|| now < seen || now - seen > 100) {" in body and "!= 4\n" in body)
check("check_wgc_endpoint: a failed lookup at start keeps the last known address (it is the tunnel's endpoint)",
      'if (!_wg_resolv_ep(nvram_pf_safe_get(prefix, "ep_addr"), ep_addr_r, sizeof(ep_addr_r)))\n\t\tnvram_pf_set(prefix, "ep_addr_r", ep_addr_r);' in wg
      and 'nvram_pf_set(prefix, "ep_addr_r", "")' not in wg)

sb = wg[wg.find("void reaper_wgc_start_bound(void)"):]
sb = sb[:sb.find("\n}\n")]
check("reaper_wgc_start_bound: only after the clock is set, only an enabled network's WireGuard client",
      'if (!nvram_match("ntp_ready", "1"))\n\t\treturn;' in sb and "if (pmtl[i].enable != 1 || !pmtl[i].sdn_t.vpnc_idx)" in sb
      and "vpnx.proto != VPN_PROTO_WG" in sb)
check("reaper_wgc_start_bound: only a client that is switched on and has no interface; rc never switches one on",
      "if (!nvram_get_int(nv) || _wg_if_exist(ifn))\n\t\t\t\tcontinue;" in sb and "start_wgc(unit);" in sb
      and "nvram_set" not in sb and "done[unit] = 1;" in sb)
# ---- the state block of check_wgc_endpoint and reaper_wgc_start_bound, compiled from the real source and run
b0 = body.find("\t\t{\n\t\t\t/* reaper 2026-11-14 (field report: a client used by a guest network")
b1 = body.find("\n\t\t}\n", b0)
blk = body[b0:b1 + 5] if 0 < b0 < b1 else ""
check("check_wgc_endpoint: the state block can be cut out, and it leaves by falling through (no continue / return)",
      bool(blk) and "continue;" not in blk and "return" not in blk)
f0 = wg.find("void reaper_wgc_start_bound(void)")
fn = wg[f0:wg.find("\n}\n", f0) + 3] if f0 > 0 else ""
SIM = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <net/if.h>
static size_t t_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t k = l < n - 1 ? l : n - 1; memcpy(d, s, k); d[k] = 0; } return l; }
#define strlcpy t_strlcpy
#define WG_CLIENT_IF_PREFIX "wgc"
#define WG_CLIENT_NVRAM_PREFIX "wgc"
#define WG_DIR_CONF "/etc/wg"
#define WG_CLIENT_MAX 5
#define MTLAN_MAXINUM 8
#define VPN_PROTO_WG 3
#define VPN_PROTO_OVPN 2
static long T; static int IFX = 1, RES = 1, HAVE, NTP = 1;
static const char *NOW = "192.0.2.1", *STORED = "", *EP = "vpn.example";
static char WDS[96];
static long uptime(void) { return T; }
static const char *nvram_pf_safe_get(const char *p, const char *k) { return !strcmp(k, "ep_addr") ? EP : STORED; }
static int is_valid_ip(const char *s) { return s[0] >= '0' && s[0] <= '9'; }
static int _wg_resolv_ep(const char *a, char *buf, size_t len) { if (!RES) { buf[0] = 0; return -1; } snprintf(buf, len, "%s", NOW); return 0; }
static int IFS[8];
static int _wg_if_exist(char *i) { return (i[3] && IFS[i[3] - '0']) ? 1 : IFX; }
static int f_read_string(const char *f, char *b, int max) { if (!HAVE) return 0; snprintf(b, max, "%s", WDS); return strlen(b); }
static int f_write_string(const char *f, const char *b, unsigned fl, unsigned m) { snprintf(WDS, sizeof(WDS), "%s", b); HAVE = 1; return 0; }
static void logmessage(const char *tag, const char *fmt, ...) { }
static int notify_rc(const char *s) { printf("%ld ", T); return 0; }
@@PURE@@
static void minute(int unit)
{
	char prefix[8] = "wgc5_", ep_addr[64] = {0}, ep_addr_r[1024] = {0}, buf[1024] = {0}, *p;
@@BLK@@
}
/* ---- reaper_wgc_start_bound */
typedef struct { int idx; } SUBNET_T;
typedef struct { int sdn_idx, vpnc_idx; } SDNFT_T;
typedef struct { int enable; SUBNET_T nw_t; SDNFT_T sdn_t; } MTLAN_T;
typedef struct { int proto, unit; } VPN_VPNX_T;
static MTLAN_T NETS[MTLAN_MAXINUM]; static int NN, EN[8];
#define INIT_MTLAN(sz) calloc(MTLAN_MAXINUM, (sz))
#define FREE_MTLAN(p) free(p)
static MTLAN_T *get_mtlan(MTLAN_T *p, size_t *sz) { memcpy(p, NETS, sizeof(MTLAN_T) * NN); *sz = NN; return p; }
static VPN_VPNX_T *get_vpnx_by_vpnc_idx(VPN_VPNX_T *v, int idx) { if (idx < 1 || idx > 10) return NULL; v->proto = idx <= 5 ? VPN_PROTO_WG : VPN_PROTO_OVPN; v->unit = idx <= 5 ? idx : idx - 5; return v; }
static int nvram_match(const char *k, const char *v) { return NTP; }
static int nvram_get_int(const char *k) { return EN[k[3] - '0']; }
static void start_wgc(int unit) { printf("start%d ", unit); }
@@FN@@
int main(int argc, char **argv)
{
	int s = atoi(argv[1]);
	if (s == 9 || s == 10) {
		NTP = (s == 9); IFX = 0;
		NETS[NN].enable = 1; NETS[NN++].sdn_t.vpnc_idx = 5;	/* WG 5, on, not running */
		NETS[NN].enable = 1; NETS[NN++].sdn_t.vpnc_idx = 5;	/* the same client again */
		NETS[NN].enable = 1; NETS[NN++].sdn_t.vpnc_idx = 7;	/* OpenVPN 2 */
		NETS[NN].enable = 1; NETS[NN++].sdn_t.vpnc_idx = 2;	/* WG 2, switched off */
		NETS[NN].enable = 1; NETS[NN++].sdn_t.vpnc_idx = 3;	/* WG 3, on and running */
		NETS[NN].enable = 0; NETS[NN++].sdn_t.vpnc_idx = 4;	/* a disabled network's WG 4 */
		NETS[NN].enable = 1; NETS[NN++].sdn_t.vpnc_idx = 0;	/* no binding */
		EN[5] = EN[3] = EN[4] = 1; IFS[3] = 1;
		reaper_wgc_start_bound();
		printf("\n");
		return 0;
	}
	for (T = 0; T <= 2100; T += 60) {
		if (s == 2 && T >= 60 && T < 600)
			continue;			/* connected for ten minutes: the block is not reached */
		if (s == 3)
			IFX = 0;			/* the interface never comes back */
		if (s == 4)
			RES = 0;			/* the name does not resolve; nothing stored */
		minute(5);
		if (s != 4 && T == 0)
			STORED = "192.0.2.1";		/* the restart resolved and stored the address */
	}
	printf("\n");
	return 0;
}
'''
if m and blk and fn:
    with tempfile.TemporaryDirectory() as td:
        c, exe = os.path.join(td, "s.c"), os.path.join(td, "s")
        open(c, "w").write(SIM.replace("@@PURE@@", m.group(1)).replace("@@BLK@@", blk).replace("@@FN@@", fn))
        r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-Wno-unused-variable", "-Darm=1", "-o", exe, c],
                           capture_output=True, text=True)
        check("the state block and reaper_wgc_start_bound compile on the host from the real source (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            sim = lambda n: subprocess.run([exe, str(n)], capture_output=True, text=True).stdout.split()
            check("THE REPORT, minute by minute: restart at once when the name resolves, then (still no handshake) at 5 min and "
                  "after waits of 2, 4, 8, 15 minutes", sim(1) == ["0", "300", "420", "660", "1140", "2040"], sim(1))
            check("connected in between: the count starts again (next restart 5 minutes after it went down, as a first try)",
                  sim(2) == ["0", "900", "960", "1080", "1320", "1800"], sim(2))
            check("interface missing: restarts at 0, then after 1, 2, 4, 8, 15 minutes", sim(3) == ["0", "60", "180", "420", "900", "1800"], sim(3))
            check("a name that never resolves and nothing stored: only the 5-minute rule, with the same back-off",
                  sim(4) == ["300", "360", "480", "720", "1200", "2100"], sim(4))
            check("bound clients: WG 5 started once (two networks use it); OpenVPN, a switched-off client, a running one, a "
                  "disabled network and no binding are left alone", sim(9) == ["start5"], sim(9))
            check("bound clients: nothing before the clock is set", sim(10) == [], sim(10))

svc = read("rc/services.c")
check("rc sdn handler: bound clients are started after a network change (start half only)",
      svc.count("#if defined(RTCONFIG_WIREGUARD) && defined(RTCONFIG_MULTILAN_CFG)\n\t\tif (action & RC_SERVICE_START)\n\t\t\treaper_wgc_start_bound();") == 1
      and "extern void reaper_wgc_start_bound(void);" in read("rc/rc.h"))

# ---------------------------------------------------------------- the Network page
SJ = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js")
sj = open(SJ, encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")
h0 = sj.find("function reaper_vpnc_on_demand(_nvramSet_obj, _vpnc_idx){")
h1 = sj.find("\nfunction Get_VPNC_Profile(){", h0)
check("sdn.js: reaper_vpnc_on_demand is there, and both save paths call it where the client is chosen",
      0 < h0 < h1 and len(re.findall(r"sdn_profile\.sdn_rl\.vpnc_idx = vpn_idx;\n\t+reaper_vpnc_on_demand\(nvramSet_obj, vpn_idx\);", sj)) == 2)
NODE = shutil.which("node")
if NODE and 0 < h0 < h1:
    js = (sj[h0:h1] + r'''
var vpnc_profile_list = [{vpnc_idx: 5, activate: "0"}, {vpnc_idx: 2, activate: "1"}, {vpnc_idx: 7, activate: 0}, {vpnc_idx: 8, activate: 1}];
var httpApi = {nvramGet: function(){ return {vpn_clientx_eas: "3,"}; }};
function run(idx){ var o = {rc_service: "restart_sdn 4;"}; var r = reaper_vpnc_on_demand(o, idx); return [r, o]; }
console.log(JSON.stringify([run("5"), run("2"), run("7"), run("8"), run("0"), run("4"), run("x")]));
''')
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "h.js"); open(f, "w").write(js)
        r = subprocess.run([NODE, f], capture_output=True, text=True)
        try:
            o = json.loads(r.stdout)
        except Exception:
            o = None
        check("page helper runs under node", o is not None, r.stderr or r.stdout)
        if o:
            check("a chosen WireGuard client that is off: wgcN_enable=1 in the same save, no service added (rc starts it)",
                  o[0] == [True, {"rc_service": "restart_sdn 4;", "wgc5_enable": "1"}], o[0])
            check("a client that is already on: nothing changed", o[1] == [False, {"rc_service": "restart_sdn 4;"}] and o[3][0] is False, (o[1], o[3]))
            check("a chosen OpenVPN client that is off: added to vpn_clientx_eas and started",
                  o[2] == [True, {"rc_service": "restart_sdn 4;start_vpnclient2;", "vpn_clientx_eas": "3,2,"}], o[2])
            check("no binding, an unknown client, a bad value: nothing changed",
                  all(x == [False, {"rc_service": "restart_sdn 4;"}] for x in (o[4], o[5], o[6])), o[4:])
else:
    print("note: node not found - the page helper was not run")

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
