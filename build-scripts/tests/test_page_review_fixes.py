#!/usr/bin/env python3
"""Checks restored by the stock-vs-Reaper page review (2026-10-24).

WHY. Three reviewers compared every stock page a Reaper page replaces against its replacement, function by function,
before the stock pages leave the image. Six Reaper pages had let a check the stock page made go missing:
- Reaper_Firewall: Network Services weekday / weekend times were packed without a range check (rc timematch_conv2 checks
  only the length, and a 25:99 made iptables-restore refuse the whole filter table); rule addresses were not validated
  (rc ipt_addr_compact skips what it cannot parse, so a typo silently did nothing); IPv6 inbound rules took any text for
  the addresses, port and OTHER protocol number (ip6tables-restore could fail); the IPv4 inbound source could be empty
  (a rule with no -s, broader than stock allowed).
- Reaper_QoS: the Bandwidth Limiter accepted MAC targets only; stock and rc (qos.c address_format_checker) also take an
  IPv4 address, a.b.c.*, a.b.c.d-N or a CIDR block.
- Reaper_System (+ the kit's rp.pingPresets, shared with Reaper_Analysis): the ping-target presets read keys that
  ajax/DNS_List.json does not have (dns1 / name instead of ServiceIP1 / DNSService), so the list offered index numbers;
  the new password was not refused when it equalled the factory default although RADM_07 says so; a WAN HTTPS port
  equal to the SSH port was not refused.
- httpd reaper_inject.c: a bounce onto a target that already carries ?tab= appended the request's query with a second
  ?, which lost the tab.

WHAT IT DOES. Source pins on the five files, and the Firewall / QoS validators run under node against vectors that
mirror what rc accepts.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

FW, QS, SY, RP = (rd(os.path.join(www, f)) for f in ("Reaper_Firewall.asp", "Reaper_QoS.asp", "Reaper_System.asp", "reaper/rp.js"))
INJ = rd(os.path.join(SRC, "httpd", "reaper_inject.c"))

# ---- Firewall ----
check("Firewall loads the kit script (rp.v validators)", '<script src="/reaper/rp.js"></script>' in FW)
check("Firewall: address validators present (v4ok / v6ok / addrFam)", all(x in FW for x in ("function v4ok(s){", "function v6ok(s){", "function addrFam(s){")))
check("Firewall: Network Services times are range-checked HH:MM (no p4/pk packing)",
      "function tm(id,dflt){" in FW and "if(t1===null||t2===null||t3===null||t4===null){alert(`<#RADM_71#>`);return;}" in FW
      and "filter_lw_time_x:t1+t2,filter_lw_time2_x:t3+t4" in FW and "function p4(v)" not in FW)
check("Firewall: Network Services rule addresses validated, v4/v6 mix refused",
      "var fs=addrFam(sip),fd=addrFam(dip);" in FW and "if(fs&&fd&&fs!==fd){alert(" in FW)
check("Firewall: IPv4 inbound source required and valid, port required",
      "if(!v4ok(src)){alert((src||'?')+' '+`<#JS_validip#>`);return;}" in FW and "if(port===''){alert(`<#JS_fieldblank#>`);return;}" in FW)
check("Firewall: IPv6 inbound rule addresses, port list and OTHER protocol number validated",
      "if(rip&&!v6ok(rip)){alert(" in FW and "if(!lip||!v6ok(lip)){alert(" in FW
      and "if(proto==='OTHER'){ if(!/^\\d{1,3}$/.test(port)||+port<1||+port>255)" in FW and "var np=normPort(port); if(np===null)" in FW)

# ---- QoS ----
check("QoS: Bandwidth Limiter takes MAC, IPv4, a.b.c.*, a.b.c.d-N or CIDR (stock forms)",
      "if(mac.indexOf(':') >= 0){ if(!/^([0-9A-F]{2}:){5}[0-9A-F]{2}$/.test(mac)){ alert(`<#RQOS_113#>`); return; } }" in QS
      and "RX_IP.test(mac) || RX_IPSTAR.test(mac) || RX_IPMASK.test(mac)" in QS and "RX_IPRANGE.test(mac)" in QS
      and "ReaperNames.byIp(mac, mac)" in QS)

# ---- System + kit ----
check("rp.pingPresets reads ServiceIP1 / DNSService (the keys ajax/DNS_List.json has)",
      "e.ServiceIP1 || e.dns1 || e.ip || k" in RP and "e.DNSService || e.name || k" in RP)
check("Reaper_System presets come from the kit loader (review 2026-10-24 Q-C2-8: its own copy is gone)",
      "rp.pingPresets(q('pinglist'))" in SY and "function pingPresets(" not in SY)
dl = os.path.join(www, "ajax", "DNS_List.json")
if os.path.exists(dl):
    try:
        d = json.loads(rd(dl).lstrip("\ufeff"))
        check("ajax/DNS_List.json carries ServiceIP1 + DNSService on a ping target",
              any(v.get("ping_target") == "Yes" and v.get("ServiceIP1") and v.get("DNSService") for v in d.values() if isinstance(v, dict)))
    except Exception as e:
        check("ajax/DNS_List.json parses", False, e)
check("Reaper_System refuses the factory-default password (RADM_07's promise) by its MD5 - the default itself never in the page (review 2026-10-24)",
      "var DEFAULT_PW_MD5 = '<% reaper_default_pw_md5(); %>';" in SY and "(DEFAULT_PW_MD5 && rp.md5(p1) === DEFAULT_PW_MD5)){ credFail(`<#RADM_07#>`)" in SY
      and 'nvram_default_get("http_passwd")' not in SY)
check("Reaper_System refuses a WAN HTTPS port equal to the SSH port",
      "c.misc_httpsport_x === c.sshd_port) return bad('i_misc_httpsport_x', `<#RADM_34#>`)" in SY)

# ---- Connections: filter + sort (owner, 2026-10-24: add them, then the stock page goes) ----
CN = rd(os.path.join(www, "Reaper_Conn.asp"))
check("Reaper_Conn: text filter box (stock CTL_search token, no new key) and the filter / sort helpers",
      'id="qfilter" type="text" placeholder="<#CTL_search#>"' in CN
      and all(x in CN for x in ("function sorted(list){", "function filtered(list){", "function hay(c){", "function hcell(k,label,cls){", "function setSort(k){")))
# 2026-10-25 (owner): a long destination (03s0.signaling.access.vivint.ai) no longer stretches the flow detail panel
check("Reaper_Conn: the detail panel keeps its width - title and destination cut with an ellipsis (whole on hover), badge never shrinks, no sideways scroll",
      ".split{display:grid;grid-template-columns:minmax(0,1fr) 340px;" in CN and ".dside{align-self:stretch;min-width:0}" in CN
      and "overflow-x:hidden;overflow-y:auto" in CN and ".dhd>div:first-child{flex:1 1 auto;min-width:0}" in CN
      and ".dhd .chip{flex:0 0 auto;white-space:nowrap}" in CN and "white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" in CN
      and '<div class="n" title="\'+esc(dn||c.srv)+\'">' in CN and "drow(`<#AiProtection_event_Destination#>`,esc(dst),dst)" in CN
      and "function drow(k,v,full){" in CN)
check("Reaper_Conn: both views draw sortable headers and sort the filtered list",
      'hcell("dev",`<#Clientlist_device#>`)' in CN and 'hcell("rate",`<#RTRF_25#>`,"r")' in CN
      and "var all=state.conns, conns=sorted(filtered(all));" in CN and "var shown=sorted(filtered(conns.filter(" in CN)
check("Reaper_Conn: filter input and header clicks wired; sort remembered per browser",
      'getElementById("qfilter").addEventListener("input"' in CN and 'closest(".qhead [data-k]")' in CN and 'closest(".fhead [data-k]")' in CN
      and 'localStorage.setItem("reaper_conn_sort"' in CN)

# ---- httpd bounce ----
check("httpd bounce keeps the query with & when the target already has ?tab=",
      'var q=location.search;if(q&&s&&s.indexOf(\\"?\\")>=0){q=\\"&\\"+q.slice(1);}' in INJ
      and "strchr(to, '?') ? \"&\" : \"?\"" in INJ and 'top.location.replace(\\"/reaper_shell.asp#%s\\"+(q?\\"%s\\"+q:\\"\\"))' in INJ)

# ---- the validators under node, against the forms rc accepts ----
node = shutil.which("node")
f0, f1 = FW.find("function v4ok(s){"), FW.find("/* extended blocklist closing")
r0, r1 = RP.find("var OCT = "), RP.find("/* ---- custom select")
if node and f0 > 0 and f1 > f0 and r0 > 0 and r1 > r0:
    rpv = RP[r0:r1].replace("rp.v = {", "var rp = {}; rp.v = {")
    harness = (rpv + "\n" + FW[f0:f1] + "\n"
      "var ok4 = ['192.168.50.20', '192.168.50.0/24', '192.168.50.*', '192.168.50.2-100', '10.0.0.1-10.0.0.9'];\n"
      "var bad4 = ['', '192.168.50', '192.168.50.300', '192.168.50.*.1', '192.168.50.100-2', '192.168.50.2-256', '10.0.0.9-10.0.0.1', 'host', '2001:db8::1'];\n"
      "var ok6 = ['2001:db8::1', '2001:db8::/64', '::1', '2001:db8::1-2001:db8::9'];\n"
      "var bad6 = ['', '2001:db8::/129', '2001:db8', '192.168.50.1', 'x::y'];\n"
      "var out = {ok4: ok4.map(v4ok), bad4: bad4.map(v4ok), ok6: ok6.map(v6ok), bad6: bad6.map(v6ok),\n"
      "  fam: ['', '192.168.50.1', '2001:db8::1', 'nope'].map(addrFam)};\n"
      "console.log(JSON.stringify(out));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(harness); hp = f.name
    r = subprocess.run([node, hp], capture_output=True, text=True); os.unlink(hp)
    try: o = json.loads(r.stdout)
    except Exception: o = None
    check("validators run under node", o is not None, (r.stderr or r.stdout)[-300:])
    if o:
        check("v4ok accepts host / CIDR / a.b.c.* / a.b.c.d-N / a-b range", all(o["ok4"]), o["ok4"])
        check("v4ok refuses empty, short, >255, bad star, descending or >255 ranges, names, IPv6", not any(o["bad4"]), o["bad4"])
        check("v6ok accepts host / prefix / ::1 / range", all(o["ok6"]), o["ok6"])
        check("v6ok refuses empty, prefix >128, short, IPv4, junk", not any(o["bad6"]), o["bad6"])
        check("addrFam: 0 empty, 4, 6, -1", o["fam"] == [0, 4, 6, -1], o["fam"])
else:
    print("note: node not found or the validator block moved - vector checks skipped")

# 2026-10-25 (owner): a page that opens another menu page itself (the USB Application list) marks it in the shell
SH = rd(os.path.join(www, "reaper_shell.asp"))
lp = SH[SH.find("function loadPage(page){"):SH.find("function markPage(base){")]
check("loadPage marks through markPage(); the frame's own navigation to a menu page marks it too, hash in frameUrl's allow-list",
      "markPage(page.split('?')[0]);" in lp and "function inMenu(base){" in SH
      and "if(base===(location.hash||'').replace('#', '').split('?')[0] || !inMenu(base)) return;" in SH
      and "if(frameUrl(page)!=='/'+page) page=base;" in SH and "markPage(base);\n    }catch(e){}" in SH)
# 2026-10-25 (owner): Gatekeeper's connection type follows the Devices page's data and order
GKP = rd(os.path.join(www, "Reaper_GK.asp"))
gc = GKP[GKP.find("function gkConn(d){"):GKP.find("function gkEditing(){")]
check("gkConn labels from reaper_dev.cgi's entry (MLO, wired, band) and falls back to gkd's record wired first",
      "var c = GK.conn[String(d.mac || '').toUpperCase()];" in gc
      and gc.find("if(c.mlo && c.bands)") < gc.find("if(c.wired)") < gc.find("if(c.band)")
      and gc.find("if(d.wired)") < gc.find("if(d.band)")
      and "gkGet('/reaper_dev.cgi?action=status&poll=1&http_id=' + encodeURIComponent(REAPER_HTTPID)" in GKP
      and "conn:{}, connAt:0" in GKP)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + x) for x in fails]; sys.exit(1)
print("\nall checks passed")
