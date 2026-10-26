#!/usr/bin/env python3
"""Reaper_SNMP.asp + Reaper_Tweaks.asp - Administration > SNMP and > Tweaks on the Reaper kit (wave 1, 2026-10-23).

WHY. The two pages replace Advanced_SNMP_Content.asp and Tools_OtherSettings.asp. This pins what the parity
harness cannot see: every covered setting is a disabled hidden input (changed-fields-only), the page is ASCII,
runs in one closure with no globals, uses only existing dict tokens and only inside backticks in JS, the
SNMPv3 password rule matches rc/snmpd.c (one token, net-snmp's 8-character floor) and is checked only while SNMP
is on, each Tweaks change restarts what reads it, the conntrack strings keep rc/common.c's layout, and the
wiring (menu, httpd SUP redirect + native list, www Makefile) is in place. Also: the dead Notification tab is
gone from the menu and the image.

WHAT IT DOES. Source checks on www/Reaper_SNMP.asp, www/Reaper_Tweaks.asp, www/reaper/menu.js, www/Makefile,
httpd/reaper_inject.c and the 25 dicts; `node --check` on both page scripts.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
www = os.path.join(SRC, "www")
HERE = os.path.dirname(os.path.abspath(__file__))
PS, PT = os.path.join(www, "Reaper_SNMP.asp"), os.path.join(www, "Reaper_Tweaks.asp")
if not (os.path.exists(PS) and os.path.exists(PT)):
    print("SKIP: Reaper_SNMP.asp / Reaper_Tweaks.asp not found"); sys.exit(0)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
S, T = rd(PS), rd(PT)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

for name, t, stock in (("Reaper_SNMP.asp", S, "Advanced_SNMP_Content.json"), ("Reaper_Tweaks.asp", T, "Tools_OtherSettings.json")):
    check(name + ": ASCII only", not any(ord(c) > 127 for c in t))
    check(name + ": on the kit (rp.css + rp.js, reaper-native meta, no jQuery / httpApi / state.js)",
          '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
          and '<meta name="reaper-native" content="1">' in t and not re.search(r'src="/(js/jquery|js/httpApi|state)\.js"', t))
    par = json.load(open(os.path.join(HERE, "ui_parity", stock), encoding="utf-8"))
    covered = [k for k, v in par["fields"].items() if v == "covered"]
    missing = [k for k in covered if '<input type="hidden" name="%s" value="" disabled>' % k not in t]
    check(name + ": every covered setting is a disabled hidden input (%d)" % len(covered), not missing, missing)
    check(name + ": the form posts to start_apply.htm with its own page name",
          ('name="current_page" value="%s"' % name) in t and ('name="next_page" value="%s"' % name) in t)
    js = t[t.rfind("<script>"):]
    check(name + ": one closure, no globals, no inline handlers, sections in guards",
          js.startswith("<script>\n(function(){\n'use strict';") and js.rstrip().endswith("boot();\n})();\n</script>\n</body>\n</html>")
          and js.count("<script>") == 1 and "onclick=" not in t and "BROKEN[s.panel] = 1;" in t and "if (!BROKEN[s.panel]) s.collect(c);" in t)
    check(name + ": the settings sections sit in the kit's crimson frame (.rframe), like the System page",
          t.count('<div class="rframe">') == 1 and t.index('<div class="rframe">') < t.index('<div class="panel"'))
    check(name + ": only changed settings are posted", "rp.post(document.form, changed, script, wait, false)" in t and "changed = diff(c)" in t)
    en = rd(os.path.join(www, "EN.dict"))
    toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
    miss = [k for k in toks if ("\n%s=" % k) not in en]
    check(name + ": every dict token exists in EN.dict (%d tokens)" % len(toks), not miss, miss)
    js_wo = re.sub(r"`[^`]*`", "", js)
    check(name + ": tokens inside the script only within backticks (rule 29)", "<#" not in js_wo,
          [m.group(0) for m in re.finditer(r".{0,40}<#[A-Za-z0-9_]+#>", js_wo)][:3])

# SNMP behaviour
check("SNMP: v3 password rule = rc/snmpd.c (one token: no spaces/control chars) + net-snmp's 8-char floor, max 64",
      "function pwOk(p){ return /^[\\x21-\\x7e]{8,64}$/.test(p); }" in S)
check("SNMP: passwords are checked only while SNMP is on (the stock privacy check blocked Apply with SNMP off)",
      "if (c.snmpd_enable !== '1') return '';" in S and "if (c.v3_priv_type !== 'NONE' && (c.v3_priv_passwd !== '' ? !pwOk(c.v3_priv_passwd) : !NV.v3_priv_set))" in S)
check("SNMP: restart_snmpd only when the agent is or was on, else saveNvram",
      "var live = c.snmpd_enable === '1' || NV.snmpd_enable === '1';" in S and "var script = live ? 'restart_snmpd' : 'saveNvram'" in S)
check("SNMP: the WAN switch is router-mode only (a WAN firewall rule); the value is kept elsewhere",
      "c.snmpd_wan = ROUTER ? chk('t_snmpd_wan') : NV.snmpd_wan;" in S and "show('r_wan', ROUTER)" in S)
check("SNMP: text values read through nvram_char_to_ascii (quotes and markup cannot break the script); the passphrases only as presence flags (review 2026-10-24 S-C2-2)",
      all(('nvram_char_to_ascii("","%s")' % k) in S for k in ("sysName", "sysLocation", "sysContact", "http_username"))
      and 'nvram_match("v3_auth_passwd", "", "0")' in S and 'nvram_match("v3_priv_passwd", "", "0")' in S and 'nvram_char_to_ascii("","v3_' not in S
      and "q('i_v3_auth_passwd').placeholder = NV.v3_auth_set ? '********' : ''" in S
      and "if (c.v3_auth_passwd !== '' ? !pwOk(c.v3_auth_passwd) : !NV.v3_auth_set)" in S)
check("SNMP: password inputs are type=password with a show switch", S.count('type="password"') == 2 and "id=\"c_showpw\"" in S)

# Tweaks behaviour
check("Tweaks: conntrack strings keep rc/common.c's layout (0 + 8 TCP values + 0; unreplied assured)",
      "function tcpStr(){ return '0 ' + TCP.map(function(f){ return val(f[0]); }).join(' ') + ' 0'; }" in T
      and "function udpStr(){ return val('udp_unreplied') + ' ' + val('udp_assured'); }" in T)
check("Tweaks: an untouched pair keeps nvram's exact spelling; an all-zero or empty value shows the kernel defaults",
      "c.ct_tcp_timeout = (t === SEEN.tcp) ? NV.ct_tcp_timeout : t;" in T and "a.some(function(x){ return x !== '0'; })" in T)
check("Tweaks: each change restarts what reads it (conntrack / rwarden / firewall / dnsmasq), saveNvram otherwise",
      "if (has('ct_max', 'ct_tcp_timeout', 'ct_udp_timeout')) S.push('restart_conntrack');" in T and "if (has('rwarden_sched')) S.push('restart_rwarden');" in T
      and "if (has('ipv6_ns_drop')) S.push('restart_firewall');" in T and "if (has('dhcpd_send_wpad')) S.push('restart_dnsmasq');" in T
      and "var script = S.length ? S.join(';') : 'saveNvram'" in T)
check("Tweaks: ranges as stock (limit 256-300000, established 1-432000, others 1-86400) and rw_valid_sched's alphabet",
      "rp.v.int(c.ct_max, 256, 300000)" in T and "2400, 432000]" in T and T.count(", 86400]") == 9 and "/^[0-9 *\\/,-]{1,64}$/" in T)
check("Tweaks: Warden schedule shown only where Warden runs (routing modes), value kept elsewhere",
      "if (!ROUTING){ q('p_warden').classList.add('off'); return; }" in T and "c.rwarden_sched = ROUTING ? q('i_rwarden_sched').value.trim() : NV.rwarden_sched;" in T)

# dicts
PACKS = "EN DE FR ES BR IT NL DA NO SV FI PL CZ SL HU RO RU UK TR MS TH JP KR CN TW".split()
keys = ["RSNM_%02d" % i for i in range(1, 22)] + ["RTWK_%02d" % i for i in range(8, 32)]
def keyline(t):
    return {l.split("=", 1)[0]: n for n, l in enumerate(t.split("\n")) if "=" in l}
en_pos = keyline(rd(os.path.join(www, "EN.dict")))
bad_packs = []
for p in PACKS:
    pos = keyline(rd(os.path.join(www, p + ".dict")))
    if any(pos.get(k) is None or pos.get(k) != en_pos.get(k) for k in keys): bad_packs.append(p)
check("RSNM_01-21 and RTWK_08-31 in all 25 packs at the same line (lockstep)", not bad_packs and all(k in en_pos for k in keys), bad_packs)

# wiring
menu = rd(os.path.join(www, "reaper", "menu.js")); inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c")); mk = rd(os.path.join(www, "Makefile"))
check("menu: SNMP and Tweaks tabs point at the Reaper pages; the stock pages and the Notification tab are gone",
      "T('Reaper_SNMP.asp', 'SNMP', sup('snmp'))" in menu and "T('Reaper_Tweaks.asp', `<#Reaper_c_tweaks#>`)" in menu
      and "Advanced_SNMP_Content" not in menu and "Tools_OtherSettings" not in menu and "Advanced_Notification_Content" not in menu)
check("httpd: SUP map redirects both stock pages; both Reaper pages are native (no stock skin)",
      '{ "advanced_snmp_content.asp", "Reaper_SNMP.asp", ' in inj and '{ "tools_othersettings.asp", "Reaper_Tweaks.asp", ' in inj
      and all(inj.index('\t"%s",' % p) > inj.index("static const char *reaper_native[]") for p in ("Reaper_SNMP.asp", "Reaper_Tweaks.asp")))
# review 2026-10-24 (Q-B-10): the two `ifneq ($(RTCONFIG_SNMPD),y)` blocks test the same thing in one recipe; the page's
# rm stays in the first only
check("image: Reaper_SNMP.asp follows the stock page's RTCONFIG_SNMPD gate; the Notification page is removed",
      mk.count("\trm -f $(INSTALLDIR)/www/Reaper_SNMP.asp\n") == 1
      and "ifneq ($(RTCONFIG_SNMPD),y)\n\trm -rf $(INSTALLDIR)/www/Advanced_SNMP_Content.asp\n\trm -f $(INSTALLDIR)/www/Reaper_SNMP.asp\n" in mk
      and "\trm -f $(INSTALLDIR)/www/Advanced_Notification_Content.asp\n" in mk)

node = shutil.which("node")
if node:
    for name, t in (("Reaper_SNMP.asp", S), ("Reaper_Tweaks.asp", T)):
        s = re.findall(r"<script>(.*?)</script>", t, re.S)[-1]
        s = re.sub(r"<%.*?%>", "0", s); s = re.sub(r"<#[A-Za-z0-9_-]+#>", "X", s)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(s); jp = f.name
        r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
        check(name + ": page script parses (node --check)", r.returncode == 0, r.stderr[-400:])
else:
    print("note: node not found - syntax checks skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
