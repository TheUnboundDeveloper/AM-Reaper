#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest networks bound to a VPN client: DNS after a tunnel recovery (B4), IPv6 into the tunnel (B5). 2026-11-14.

WHY THIS EXISTS. Field reports on Guest Network Pro networks bound to a WireGuard client (plan
docs/backlog guest-vpn-binding-robustness.md, parts B4 and B5):
  B4 rc/wireguard.c check_wgc_endpoint(): a connected tunnel whose route is missing (it dropped and came back) has its
     route re-added and vpnc_up() run - but vpnc_down() had cleared vpncN_dns, so vpnc_up() skipped the DNS servers and
     the client's resolv file (what a bound guest network's resolver reads) and VPN Director DNS were not rebuilt.
     Exists only on the 3006.102.10 base; the 3006.102.8 base has no such branch (checked: skipped there).
  B5 rc/sdn.c _handle_sdn_wan(): the IPv6 rule that sends a bound network's IPv6 into the tunnel was gated on the stock
     profile list (vpnc_clientlist), which Reaper's VPN Client page never writes - so it was never added and IPv6 left by
     the WAN. The protocol now comes from the fixed numbering (1-5 WireGuard, 6-10 OpenVPN).

WHAT IT CHECKS. Source pins for both; with gcc, the new helper reaper_vpnc_proto() is compiled out of sdn.c against a
stand-in of the numbering and run over 0..11. Exit 0 pass, 1 fail, 77 skip."""
import os, re, shutil, subprocess, sys, tempfile

SRC = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC")
       or os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router"))
sdn_p = os.path.join(SRC, "rc", "sdn.c"); wg_p = os.path.join(SRC, "rc", "wireguard.c")
if not (os.path.isfile(sdn_p) and os.path.isfile(wg_p)):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
sdn, wg = rd(sdn_p), rd(wg_p)
fails = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name); print("FAIL " + name + ((" :: " + str(detail)[:400]) if detail else ""))

# ---- B5
i = sdn.find("static int _handle_sdn_wan(const MTLAN_T *pmtl, const char *logdrop, const char *logaccept)\n{")
body = sdn[i:sdn.index("\n}\n", i)] if i >= 0 else ""
check("B5: _handle_sdn_wan no longer reads the stock profile list for the protocol",
      body and "vpnc_get_proto_in_profile_by_vpnc_id" not in body)
check("B5: both IPv6 rules (a bound network, the main LAN's default VPN) take the protocol from the fixed numbering",
      body.count("proto = reaper_vpnc_proto(") == 2
      and "proto = reaper_vpnc_proto(pmtl->sdn_t.vpnc_idx);" in body and "proto = reaper_vpnc_proto(vpnc_default_wan);" in body
      and body.count('eval("ip", "-6", "rule", "add", "iif", (char*)pmtl->nw_t.ifname, "table", table, "pref", pref);') >= 2)
m = re.search(r"#if defined\(RTCONFIG_IPV6\) && defined\(RTCONFIG_VPN_FUSION\)\n/\* reaper 2026-11-14 \(guest VPN binding B5\).*?\n(static VPNC_PROTO reaper_vpnc_proto\(int vpnc_idx\)\n\{.*?\n\})\n#endif\n", sdn, re.S)
check("B5: reaper_vpnc_proto() is defined under the same build options as its callers", m is not None)
gcc = shutil.which("gcc")
if m and gcc:
    harness = r'''
#include <stdio.h>
typedef enum { VPNC_PROTO_UNDEF = 0, VPNC_PROTO_PPTP, VPNC_PROTO_L2TP, VPNC_PROTO_OVPN, VPNC_PROTO_IPSEC, VPNC_PROTO_WG } VPNC_PROTO;
typedef enum { VPN_PROTO_UNKNOWN = 0, VPN_PROTO_OVPN, VPN_PROTO_WG } VPN_PROTO_T;
typedef struct { VPN_PROTO_T proto; int unit; } VPN_VPNX_T;
/* the numbering of shared/mtlan_utils.c get_vpnx_by_vpnc_idx (AMNG branch): 1-5 WireGuard, above 5 OpenVPN unit idx-5 */
static VPN_VPNX_T *get_vpnx_by_vpnc_idx(VPN_VPNX_T *v, int idx)
{ if (!v) return 0; if (idx > 5) { v->proto = VPN_PROTO_OVPN; v->unit = idx - 5; } else { v->proto = VPN_PROTO_WG; v->unit = idx; } return v; }
@@FN@@
int main(void) { int i; for (i = 0; i <= 11; i++) printf("%d%s", reaper_vpnc_proto(i), i < 11 ? " " : "\n"); return 0; }
'''
    d = tempfile.mkdtemp()
    try:
        c = os.path.join(d, "t.c"); exe = os.path.join(d, "t")
        open(c, "w").write(harness.replace("@@FN@@", m.group(1)))
        r = subprocess.run([gcc, "-Wall", "-Werror", "-o", exe, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check("B5: the helper compiles with -Wall -Werror", r.returncode == 0, r.stdout)
        if r.returncode == 0:
            out = subprocess.run([exe], stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
            check("B5: 0 and 11 are no client; 1-5 WireGuard (5); 6-10 OpenVPN (3)", out == "0 5 5 5 5 5 3 3 3 3 3 0", out)
    finally:
        shutil.rmtree(d, ignore_errors=True)

# ---- B4
j = wg.find("void check_wgc_endpoint()")
cw = wg[j:wg.index("\n}\n", j)] if j >= 0 else ""
if "if (!_wg_check_route_exist(prefix, wg_ifname, table))" not in cw:
    print("note: this base has no connected-but-route-missing branch in check_wgc_endpoint (3006.102.8) - B4 does not apply")
else:
    k = cw.index("if (!_wg_check_route_exist(prefix, wg_ifname, table))")
    br = cw[k:cw.index("}", cw.index("vpnc_up(vpnc_idx, wg_ifname);", k))]
    order = ["_wg_config_route(prefix, wg_ifname, table, WG_NF_ADD);", "_wg_client_dns_setup_vpnc(prefix, wg_ifname, vpnc_idx);",
             "_gen_vpnc_resolv_conf(vpnc_idx);", "vpnc_up(vpnc_idx, wg_ifname);"]
    check("B4: after a recovery the client's DNS and resolv file are rebuilt BEFORE vpnc_up (which reads vpncN_dns)",
          all(x in br for x in order) and [br.index(x) for x in order] == sorted(br.index(x) for x in order), br[:300])
    tail = cw[k:k + 1200]
    check("B4: ...and VPN Director DNS after it, as start_wgc() does",
          tail.index("vpnc_up(vpnc_idx, wg_ifname);") < tail.index("wgc_set_exclusive_dns(unit);") < tail.index("amvpn_update_exclusive_dns_rules();"))
    check("B4: the cause is still what the fix assumes - vpnc_down() clears vpncN_dns",
          "clean_vpnc_setting_value(vpnc_idx);" in rd(os.path.join(SRC, "rc", "vpnc_fusion.c")))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
