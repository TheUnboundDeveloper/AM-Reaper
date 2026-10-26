#!/usr/bin/env python3
"""WAN > NAT and Port Forwarding + WAN > DDNS on the Reaper kit (Reaper-native UI, LAN/WAN wave, 2026-10-23).

Reaper_NAT.asp replaces Advanced_VirtualServer_Content.asp, Advanced_PortTrigger_Content.asp, Advanced_Exposed_Content.asp
and Advanced_NATPassThrough_Content.asp (four tabs); Reaper_DDNS.asp replaces Advanced_ASUSDDNS_Content.asp.

WHY. The stock port-forward page saved every rule edit and its enable switch the moment they were clicked (applyapp.cgi),
the switch restarted the firewall twice, an edited rule skipped the duplicate check, and the NAT Passthrough and DDNS
pages posted stray wl_* fields. The DDNS page cleared ddns_return_code just by being read (ej nvram_get_ddns) and still
carried the asuscomm (WWW.ASUS.COM) provider the owner removed from the firmware. The Reaper pages keep the stock record
formats (vts_rulelist <name>ext>ip>lport>proto>src, autofw_rulelist <desc>port>proto>port>proto) and every stock check,
post only the changed settings on Apply with the narrowest restart, and write nothing on load.
Every nvram value reaches the pages through nvram_char_to_ascii: httpd's nvram_get passes ' and \\ through.

WHAT IT DOES. Source checks on both pages (and, once wired, menu.js and reaper_inject.c); `node --check` on the page
scripts. Behaviour (what each Apply posts, which check refuses what) was run in jsdom when the pages were written.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
NAT, DDNS = os.path.join(www, "Reaper_NAT.asp"), os.path.join(www, "Reaper_DDNS.asp")
if not (os.path.exists(NAT) and os.path.exists(DDNS)):
    print("SKIP: Reaper_NAT.asp / Reaper_DDNS.asp not found"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

en = rd(os.path.join(www, "EN.dict"))
PLUMB = {"current_page", "next_page", "action_mode", "action_script", "action_wait"}
pages = {"Reaper_NAT.asp": (rd(NAT), "RNAT_"), "Reaper_DDNS.asp": (rd(DDNS), "RDDN_")}
def code_of(t):
    """the page without its HTML and JS comments (the comments cite the stock names they replace)"""
    return re.sub(r"/\*.*?\*/", "", re.sub(r"<!--.*?-->", "", t, flags=re.S), flags=re.S)
for name, (t, pfx) in pages.items():
    js = t[t.rfind("<script>"):]
    code = code_of(t)
    check(name + ": ASCII only", not any(ord(c) > 127 for c in t))
    check(name + ": on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame",
          '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
          and '<meta name="reaper-native" content="1">' in t and 'rframe' in t)
    check(name + ": one closure, strict, no inline handlers", js.startswith("<script>\n(function(){\n'use strict';")
          and js.count("<script>") == 1 and not re.search(r"\son[a-z]+=", t))
    toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
    miss = [k for k in toks if ("\n%s=" % k) not in en]
    check(name + ": every dict token exists (%d)" % len(toks), not miss, miss)
    own = sorted(int(k[len(pfx):]) for k in toks if k.startswith(pfx))
    check(name + ": own keys numbered 01..N with no gap", own == list(range(1, len(own) + 1)), own)
    check(name + ": tokens in the script only inside backticks", "<#" not in re.sub(r"`[^`]*`", "", js))
    check(name + ": every nvram value read through nvram_char_to_ascii (no nvram_get / nvram_get_ddns into JS)",
          "nvram_get(" not in code and "nvram_get_ddns" not in code and t.count("nvram_char_to_ascii(") >= 15
          and ("U = rp.dec" in t or "function U(s){ try { return decodeURIComponent(s); }" in t))
    hid = re.findall(r'<input type="hidden" name="([A-Za-z0-9_]+)" value="[^"]*"( disabled)?>', t)
    check(name + ": every setting input starts disabled (only changed ones are enabled by rp.changed)",
          hid and all(d or n in PLUMB for n, d in hid), [n for n, d in hid if not d and n not in PLUMB])
    check(name + ": no stray wl_* field and no immediate-save path (applyapp / httpApi.nvramSet)",
          not re.search(r'name="wl_', t) and "applyapp" not in code and "nvramSet" not in code)
    check(name + ": one rp.post per Apply path, nothing posted from boot()", "rp.post(" in t
          and "rp.post(" not in t[t.find("function boot()"):])
    check(name + ": untouched Apply says nothing changed", "if (!count(changed)" in t and "`<#RADM_63#>`" in t)

t = pages["Reaper_NAT.asp"][0]
check("NAT: four tabs (port forwarding, trigger, DMZ, passthrough) in the Reaper_System tab pattern",
      all('id="tab_%s"' % x in t for x in ("pf", "pt", "dmz", "alg")) and 'class="tab rframe"' in t and "var TABS = ['pf', 'pt', 'dmz', 'alg'];" in t)
check("NAT: stock record formats (vts 6 fields, autofw 5 fields) and untouched rows written back byte for byte",
      "row([r.name, r.ext, r.ip, r.lport, r.proto, r.src])" in t and "var r = [val('pt_desc'), val('pt_out'), q('pt_outp').value, val('pt_in'), q('pt_inp').value]" in t
      # review 2026-10-24 (Q-C1-7): the raw-preserving serialiser is the kit's one copy, bound by the page
      and "ser = rp.list.ser" in t
      and "ser: function(rows){ return rows.map(function(r){ return '<' + r.raw; }).join(''); }" in open(os.path.join(SRC, "www", "reaper", "rp.js"), encoding="utf-8").read()
      and "if (PF_T) c.vts_rulelist = ser(PF);" in t and "if (PT_T) c.autofw_rulelist = ser(PT);" in t)
check("NAT: stock caps (64 / 32 rows) and the nvram sizes (8192 / 2048 bytes) enforced",
      "PF_MAX = 64, PT_MAX = 32, PF_BYTES = 8192, PT_BYTES = 2048" in t and "ser(list).length > PF_BYTES" in t and "ser(list).length > PT_BYTES" in t)
check("NAT: port grammar rc accepts (normalised -/~ to :, ascending ranges, 1-65535); OTHER = protocol 1-255",
      "replace(/[-~]/g, ':')" in t and "+ab[1] > +ab[0]" in t and "rp.v.int(r.ext, 1, 255)" in t)
check("NAT: duplicate check on add AND edit (stock skipped edit); trigger duplicate ignores the description",
      "if (pfDup(r, pfEdit))" in t and "o.f.slice(1).join('>') === r.slice(1).join('>')" in t)
check("NAT: internal / DMZ address - router and LAN network/broadcast refused, off-subnet asks",
      "function hostCheck(ip)" in t and "if (hc === 'self')" in t and "hostCheck(changed.dmz_ip) === 'off' && !confirm(" in t)
check("NAT: restarts - restart_firewall, restart_pppoe_relay only for the relay, SIP on keeps restart_net_and_phy behind a confirm",
      "fw ? 'restart_firewall' : ''" in t and "relay ? 'restart_pppoe_relay' : ''" in t
      and re.search(r"if \(changed\.fw_pt_sip === '1'\)\{[\s\S]{0,600}?if \(!confirm\(`<#RNAT_\d+#>`\)\) return;\s*script = 'restart_net_and_phy'; wait = 30;", t))
check("NAT: no second-WAN lists, no BRT-AC828 SIP mode", not any(x in code_of(t) for x in ("vts1_rulelist", "dmz1_ip", "fw_pt_sip_mode")))
check("NAT: the FTP deep link fills the editor and never saves on load",
      "param('af') === 'KnownApps' && param('item') === 'ftp'" in t and "pfPreset(); }" in t)
check("NAT: the live port-forward view is linked", 'href="/reaper_shell.asp#Reaper_PortFwd.asp" target="_top"' in t)

d = pages["Reaper_DDNS.asp"][0]
check("DDNS: asuscomm never offered and never re-posted; a saved one is 'not configured'",
      "WWW.ASUS.COM" not in code_of(d) and "var ASUS_SAVED = /^WWW\\.ASUS\\.COM/.test(NV.ddns_server_x);" in d
      and "if (v === '' && NV.ddns_server_x !== '') return;" in d and "DDNSName" not in code_of(d))
check("DDNS: the password never enters the page (nvram_match tells whether one is saved)",
      'nvram_char_to_ascii("","ddns_passwd_x")' not in d and "nvram_match(\"ddns_passwd_x\", \"\", \"0\")" in d
      and "if (R.pass && q('i_pass').value !== '') c.ddns_passwd_x" in d)
check("DDNS: status from ddns_return_code(_chk) without clearing it; /ajax_ddnscode.asp parsed, not evaluated",
      'nvram_char_to_ascii("","ddns_return_code")' in d and "x.open('GET', '/ajax_ddnscode.asp" in d and "eval(" not in d)
check("DDNS: stock restarts per change (ddns, ddns_le+prepare_cert, prepare_cert, ftpd for FTP-TLS), no restart_webdav",
      "S = ['restart_ddns_le', 'prepare_cert']" in d and "S.push('restart_ddns')" in d and "S.push('prepare_cert')" in d
      and "S.push('restart_ftpd')" in d and "restart_webdav'" not in d and "'saveNvram'" in d)
check("DDNS: stock checks kept (server required, refresh 0-365, period >= 30, host / user / password per provider, LE terms)",
      "`<#LANHostConfig_x_DDNS_alarm_server#>`" in d and "rp.v.int(val('i_refresh'), 0, 365)" in d and "rp.v.int(val('i_period'), 30, 99999)" in d
      and "`<#LANHostConfig_x_DDNS_alarm_14#>`" in d and "v !== 'DNS.HE.NET' && val('i_user') === ''" in d
      and "`<#LANHostConfig_x_DDNSLetsEncrypt_Disagree#>`" in d)
check("DDNS: certificate upload goes to upload_cert_key.cgi with the stock extension check",
      'action="upload_cert_key.cgi"' in d and "ke !== 'pem' && ke !== 'key'" in d and "ce !== 'pem' && ce !== 'crt' && ce !== 'cer'" in d)

mj = rd(os.path.join(www, "reaper", "menu.js"))
inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c")) if os.path.exists(os.path.join(SRC, "httpd", "reaper_inject.c")) else ""
if True:  # wired 2026-10-23
    check("menu: WAN tabs open the Reaper pages and no longer the five stock pages",
          "T('Reaper_NAT.asp'," in mj and "T('Reaper_DDNS.asp'," in mj
          and not any(p in mj for p in ("Advanced_VirtualServer_Content.asp", "Advanced_PortTrigger_Content.asp", "Advanced_Exposed_Content.asp",
                                        "Advanced_NATPassThrough_Content.asp", "Advanced_ASUSDDNS_Content.asp")))
    check("httpd: both pages native, the five stock pages redirect",
          '"Reaper_NAT.asp",' in inj and '"Reaper_DDNS.asp",' in inj
          and all('{ "%s", "%s", ' % (s, r) in inj for s, r in (("advanced_virtualserver_content.asp", "Reaper_NAT.asp"),
              ("advanced_porttrigger_content.asp", "Reaper_NAT.asp?tab=pt"), ("advanced_exposed_content.asp", "Reaper_NAT.asp?tab=dmz"),
              ("advanced_natpassthrough_content.asp", "Reaper_NAT.asp?tab=alg"), ("advanced_asusddns_content.asp", "Reaper_DDNS.asp"))))
    check("httpd: every ?tab= deep link names a tab Reaper_NAT reads",
          all(x in t for x in ("var TABS = ['pf', 'pt', 'dmz', 'alg'];", "param('tab')")))

node = shutil.which("node")
if node:
    for name, (t, _) in pages.items():
        js = t[t.rfind("<script>"):]
        body = js[len("<script>"):js.rfind("</script>")]
        body = re.sub(r"<%.*?%>", "", body); body = re.sub(r"`[^`]*`", "''", body)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(body); jp = f.name
        r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
        check(name + ": page script parses (node --check)", r.returncode == 0, r.stderr[-300:])
else:
    print("note: node not found - syntax check skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
