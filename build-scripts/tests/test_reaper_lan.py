#!/usr/bin/env python3
"""LAN on the Reaper kit (Reaper-native UI, LAN/WAN wave, 2026-10-23): Reaper_LAN.asp, Reaper_DNS.asp and the static-route
editor in Reaper_Routes.asp.

WHY. Reaper_LAN.asp replaces Advanced_LAN_Content.asp, Advanced_DHCP_Content.asp and Advanced_SwitchCtrl_Content.asp (+ the
multicast rows of the IPTV page); Reaper_DNS.asp replaces DNSDirector.asp and takes the DNS rows of the DHCP page and of the
WAN page (DoT client included); Reaper_Routes.asp gains a Static routes tab replacing Advanced_GWStaticRoute_Content.asp.
The stock pages restarted the whole network for a hostname or a DHCP DNS change, posted the live WAN address into
unindexed wan_* keys from the LAN page, re-posted the whole sdn_rl from page-load state, and let 64 static routes be
entered into a 1 KB nvram value that silently dropped the save past ~20. The Reaper pages post only what changed, with
the narrowest restart rc needs, ask before anything that drops connections, and follow the browser to a new LAN address.

WHAT IT DOES. Source checks on the three pages (kit, ASCII, closure, dict tokens, nvram read path, posting and restart
pins, the stock bugs that must stay fixed) and the five parity files; `node --check` on each page script. Behaviour per
scenario was checked in jsdom when the pages were written (scen_Reaper_*.txt in the wave's scratch folder).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = {"lan": "Reaper_LAN.asp", "dns": "Reaper_DNS.asp", "rte": "Reaper_Routes.asp"}
if not all(os.path.exists(os.path.join(www, p)) for p in PAGES.values()):
    print("SKIP: Reaper_LAN.asp / Reaper_DNS.asp / Reaper_Routes.asp not found"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

en = rd(os.path.join(www, "EN.dict"))
T = {k: rd(os.path.join(www, p)) for k, p in PAGES.items()}
JS = {k: t[t.rfind("<script>"):] for k, t in T.items()}
PLUMB = {"current_page", "next_page", "action_mode", "action_script", "action_wait"}
for k, p in PAGES.items():
    t, js = T[k], JS[k]
    check(p + ": ASCII only", not any(ord(c) > 127 for c in t))
    check(p + ": on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame",
          '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
          and '<meta name="reaper-native" content="1">' in t and 'rframe' in t and "SPDX-License-Identifier: GPL-2.0-only" in t)
    check(p + ": one closure, strict, no inline handlers (no page globals)",
          js.startswith("<script>\n(function(){\n'use strict';") and js.rstrip().endswith("})();\n</script>\n</body>\n</html>")
          and js.count("<script>") == 1 and not re.search(r"\son[a-z]+\s*=", t))
    toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
    miss = [x for x in toks if ("\n%s=" % x) not in en]
    check(p + ": every dict token exists (%d)" % len(toks), not miss, miss)
    check(p + ": tokens in the script only inside backticks (rule 29)", "<#" not in re.sub(r"`[^`]*`", "", js))
    # every nvram value through nvram_char_to_ascii; Reaper_Routes keeps its http_id line (a hex token, pinned by test_reaper_syslog_pages)
    raw = [m.group(0) for m in re.finditer(r"nvram_get\(\"[^\"]+\"\)", t) if m.group(0) != 'nvram_get("http_id")']
    check(p + ": no nvram_get into a JS string (nvram_char_to_ascii + decodeURIComponent)", not raw and ("U = rp.dec" in t or "function U(s){ try { return decodeURIComponent(s); }" in t), raw)
    hid = re.findall(r'<input type="hidden" name="([A-Za-z0-9_]+)" value="([^"]*)"( disabled)?>', t)
    loose = [n for n, v, d in hid if n not in PLUMB and not d]
    check(p + ": every setting input starts disabled (only changed keys post)", hid and not loose, loose)
    check(p + ": no wan_unit / generic wan_* key is ever posted", not re.search(r'name="wan_', t))

L, D, R = T["lan"], T["dns"], T["rte"]
# ---- Reaper_LAN ----
check("LAN: posts only the diff, nothing on load", "var c = collect(), changed = diff(c)" in L and "rp.post(document.form, changed, S.join(';'), wait, false);" in L
      and "function keep(id, nv, now){ return snap(id) === INIT[id] ? nv : now; }" in L)
check("LAN: restarts - reboot (jumbo/LACP), restart_net_and_phy (address, AP client, STP), restart_net (multicast), dnsmasq (DHCP), name services (hostname/domain)",
      "S = ['reboot']" in L and "S = ['restart_net_and_phy']" in L and "S.push('restart_net')" in L and "S.push('restart_dnsmasq')" in L
      and "S.push('restart_ftpsamba', 'restart_mdns', 'restart_media')" in L and "S.push('restart_httpd')" in L)
check("LAN: an address change asks first, lists what is still on the old subnet, then follows the browser to the new address",
      "ask = `<#RLAN_" in L and "staleList(nip, nm)" in L and "if (ask && !confirm(ask)) return;" in L
      and "top.location.href = location.protocol + '//' + changed.lan_ipaddr" in L)
check("LAN: stale list covers reservations, port forwards, static routes, DMZ and VPN Fusion",
      all(x in L for x in ("F.vts_rulelist.split('<')", "F.sr_rulelist.split('<')", "old(F.dmz_ip)", "Object.keys(POLICY_IPS)")))
check("LAN: the pool and _rt copies follow a new router-mode address (stock calculatorIPPoolRange)",
      "c.dhcp_start = p[0]; c.dhcp_end = p[1]; c.lan_ipaddr_rt = c.lan_ipaddr; c.lan_netmask_rt = c.lan_netmask;" in L)
check("LAN: WAN conflict checks WAN 0 and WAN 1, SDN overlap checked (B-LAN-3)", "if (DUAL) wans.push([F.wan1_ipaddr, F.wan1_netmask]);" in L and "overlap(ip, m, f[2], f[3])" in L)
check("LAN: reservations - stock 64 cap, MAC / in-subnet / duplicate checks, router address refused, CSV hostname validated (B-DHCP-2)",
      "var MAXRES = 64;" in L and "!inSub(r.ip, lip, m)" in L and "if (r.ip === lip) return" in L
      and "e = resCheck(r, out, L.ip, L.m);" in L and "if (r.host && !hostOk(r.host))" in L)
check("LAN: the reservation list is re-serialised only after an edit (no phantom change)", "c.dhcp_staticlist = RES_EDITED ? serRes(RES) : NV.dhcp_staticlist;" in L)
check("LAN: DHCP DNS / WINS rows are not on this page (moved to Reaper_DNS)", not re.search(r'name="(dhcp_dns1_x|dhcp_dns2_x|dhcp_wins_x|dhcpd_dns_router|ipv6_dns1_x)"', L))
check("LAN: LACP conflicts block turning it on; auto-WAN refused instead of rewriting wans_dualwan / autowan_enable",
      "if (LACP_WHY) return bad('t_lacp', LACP_WHY);" in L and "F.autowan_enable === '1') return bad('t_lacp'" in L and not re.search(r'name="(wans_dualwan|autowan_enable|wans_extwan)"', L))
check("LAN: tab conditions copied from menu.js (DHCP, Switch in every mode, Multicast)",
      "dhcp: !sup('tagged_based_vlan') && !is('rp', 'mb') && (!is('ap') || sup('dhcp_override'))" in L and "'switch': sup('switchctrl')," in L
      and "mcast: !sup('noiptv') && ROUTING" in L)

# ---- Reaper_DNS ----
check("DNS: WAN servers per unit (wan0_/wan1_ via httpd validate_instance), restart_wan_dns <unit>",
      'name="wan0_dns1_x"' in D and 'name="wan1_dns1_x"' in D and "S.push('restart_wan_dns ' + u)" in D)
check("DNS: DoT client restarts stubby; switching it also refreshes resolv + dnsmasq",
      "S.push('restart_stubby')" in D and "if (has('dnspriv_enable') && S.indexOf('restart_wan_dns 0') < 0) S.push('restart_wan_dns 0');" in D)
check("DNS: dnsmasq options and client DNS restart dnsmasq, DNS Director restart_dnsfilter",
      "S.push('restart_dnsmasq')" in D and "if (dd) S.push('restart_dnsfilter');" in D)
check("DNS: carries the rows moved off the DHCP page", all('name="%s"' % n in D for n in ("dhcp_dns1_x", "dhcp_dns2_x", "dhcp_wins_x", "dhcpd_dns_router", "ipv6_dns1_x")))
check("DNS: dhcp_dns2_x and the IPv4 custom servers validated (B-DHCP-1, B-DNSD-1); duplicate MAC refused (B-DNSD-2)",
      "has('dhcp_dns2_x') && c.dhcp_dns2_x && !unicast(c.dhcp_dns2_x)" in D and "if (has(k) && c[k] && !unicast(c[k]))" in D
      and "DDL.some(function(r){ return r.mac === mac; })" in D)
check("DNS: sdn_rl column written into a fresh read at Apply, never re-posted from page load (B-DNSD-3)",
      "'/appGet.cgi?hook=nvram_char_to_ascii(sdn_rl,sdn_rl)" in D and "f[SDN_COL] = e.mode" in D)
check("DNS: DoT rows validated and byte-capped (B-WAN-5); Encrypted DNS settings linked, not duplicated",
      "rp.v.hostname(r.host)" in D and "var DOT_BYTES = 1006 - 'dnspriv_rulelist='.length;" in D
      and "#Reaper_EncryptedDNS.asp" in D and "reaper_dot_srv" not in D and "reaper_doh_block" not in D)
check("DNS: hnd rule list split in 255-char chunks, unedited chunks kept", "s.substring(i * 255, (i + 1) * 255)" in D and "DD_EDITED ? " in D)

# ---- Reaper_Routes ----
check("Routes: the read-only view is kept (reaper_pbr.cgi routes, local table folded)",
      "'/reaper_pbr.cgi?action=routes&http_id=' + encodeURIComponent(HTTPID)" in R and "if (t === 'local' && !showLocal) return;" in R)
check("Routes: editor posts sr_enable_x / sr_rulelist only when changed, restart_net after a confirm",
      'name="sr_enable_x" value="" disabled' in R and 'name="sr_rulelist" value="" disabled' in R
      and "if (!confirm(`<#RRTE_" in R and "rp.post(document.form, ch, 'restart_net', 10);" in R)
check("Routes: the nvram size limit is shown and enforced (B-SR-1); host bits refused (B-SR-2); serialised from the model (B-SR-3)",
      "var MAXBYTES = Math.min(1024, 1006 - 'sr_rulelist='.length);" in R and "srSer(SR.concat([r])).length > MAXBYTES" in R
      and "((ip2n(r.ip) & ~ip2n(r.mask)) >>> 0) !== 0" in R and "cells[" not in R)

# ---- wiring ----
mj = rd(os.path.join(www, "reaper", "menu.js"))
inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c"))
check("menu: LAN > LAN and LAN > DNS open the Reaper pages; no stock LAN/DHCP/Director/Route/Switch tab left",
      "T('Reaper_LAN.asp'" in mj and "T('Reaper_DNS.asp'" in mj
      and not any(p in mj for p in ("Advanced_LAN_Content.asp", "Advanced_DHCP_Content.asp", "DNSDirector.asp",
                                    "Advanced_GWStaticRoute_Content.asp", "Advanced_SwitchCtrl_Content.asp")))
check("httpd: both pages native; the five stock pages redirect, deep links name tabs the pages read",
      '"Reaper_LAN.asp",' in inj and '"Reaper_DNS.asp",' in inj
      and all('{ "%s", "%s", ' % sr in inj for sr in (("advanced_lan_content.asp", "Reaper_LAN.asp"),
          ("advanced_dhcp_content.asp", "Reaper_LAN.asp?tab=dhcp"), ("advanced_switchctrl_content.asp", "Reaper_LAN.asp?tab=switch"),
          ("dnsdirector.asp", "Reaper_DNS.asp?tab=dd"), ("advanced_gwstaticroute_content.asp", "Reaper_Routes.asp?tab=edit")))
      and "tab=(addr|dhcp|switch|mcast)" in T["lan"] and "tab=dd/" in T["dns"] and "tab=edit/" in T["rte"])

# ---- parity files ----
for name, rep in (("Advanced_LAN_Content", "Reaper_LAN.asp"), ("Advanced_DHCP_Content", "Reaper_LAN.asp"), ("Advanced_SwitchCtrl_Content", "Reaper_LAN.asp"),
                  ("DNSDirector", "Reaper_DNS.asp"), ("Advanced_GWStaticRoute_Content", "Reaper_Routes.asp")):
    f = os.path.join(HERE, "ui_parity", name + ".json")
    ok = os.path.exists(f) and json.load(open(f, encoding="utf-8")).get("replacement") == rep
    check("parity file %s.json -> %s" % (name, rep), ok)
pf = os.path.join(HERE, "ui_parity", "Advanced_DHCP_Content.json")
if os.path.exists(pf):
    moved = [k for k, v in json.load(open(pf, encoding="utf-8"))["fields"].items() if "moved to Reaper_DNS.asp" in v]
    check("parity: every DHCP field marked moved is on Reaper_DNS.asp", moved and all('name="%s"' % k in D for k in moved), moved)

node = shutil.which("node")
if node:
    for k, p in PAGES.items():
        js = JS[k]; body = js[len("<script>"):js.rfind("</script>")]
        body = re.sub(r"<%.*?%>", "", body); body = re.sub(r"`[^`]*`", "''", body)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(body); jp = f.name
        r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
        check(p + ": page script parses (node --check)", r.returncode == 0, r.stderr[-300:])
else:
    print("note: node not found - syntax check skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
