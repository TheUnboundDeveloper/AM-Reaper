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

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")	# 2026-11-20: argv[1] like the other tests
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
    missing = [k for k in covered if not re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(k), t[t.rfind("<script>"):])]
    check(name + ": every covered setting is named in the page script, rp.changed posts it (%d)" % len(covered), not missing, missing)
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

# 2026-11-20 (item 9, REAPER-DUT-REDIR): the address the login redirect goes to
check("Tweaks: the redirect's address row (protocol, name, port) under the switch, shown while it is on",
      '<div class="frow off" id="r_dut_redir_to">' in T and 'id="s_dut_proto"' in T and 'id="i_dut_host" maxlength="57"' in T and 'id="i_dut_port" maxlength="5"' in T
      and "q('r_dut_redir_to').classList.toggle('off', chk('t_http_dut_redir') !== '1');" in T)
check("Tweaks: the three parts read with nvram_get_js, posted as reaper_dut_redir_proto / _host / _port, kept as they are while the row is hidden",
      all(('nvram_get_js("reaper_dut_redir_%s")' % k) in T for k in ("proto", "host", "port"))
      and "c.reaper_dut_redir_host = shown ? q('i_dut_host').value.trim().toLowerCase() : NV.reaper_dut_redir_host;" in T)
check("Tweaks: httpd's rules checked before Apply (name labels, 57 characters, no IP; port 1-65535 or empty), saved only (no restart)",
      "function redirHostOk(h){" in T and "function redirPortOk(p){" in T and "`<#RTWK_51#>`" in T and "`<#RTWK_52#>`" in T
      and "has('reaper_dut_redir" not in T)

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

# reaper 2026-11-16 (bug review A2 item 3): the factory connection limit equals the page's ceiling, so the limit can
# only be lowered - the help text must not tell the user to raise it. Parsed, so a later change of the default or of
# the cap without the text is caught too.
_dfl = rd(os.path.join(SRC, "shared", "defaults.c"))
m_def = re.search(r'\{ "ct_max", "(\d+)",', _dfl)
m_cap = re.search(r"rp\.v\.int\(c\.ct_max, (\d+), (\d+)\)", T)
check("Tweaks: the connection limit default (shared/defaults.c) and the page's range are found", m_def is not None and m_cap is not None)
ct_def = int(m_def.group(1)) if m_def else -1; ct_cap = int(m_cap.group(2)) if m_cap else -2
en09 = re.findall(r"^RTWK_09=(.*)$", rd(os.path.join(www, "EN.dict")), re.M)
en09 = en09[0] if len(en09) == 1 else ""
print("     ct_max default %d, page cap %d" % (ct_def, ct_cap))
check("Tweaks: the default never exceeds the page's cap (a higher default could not be saved back)", 0 < ct_def <= ct_cap, (ct_def, ct_cap))
if ct_def == ct_cap:
    check("Tweaks: default = cap, so EN RTWK_09 does not say to raise the limit - it says the limit can only be lowered",
          en09 != "" and "raise" not in en09.lower() and "increase" not in en09.lower()
          and "The default connection limit is also the maximum, so it can only be lowered." in en09, en09)
else:
    check("Tweaks: default below the cap - EN RTWK_09 must not claim the default is the maximum", en09 != "" and "is also the maximum" not in en09, en09)
check("Tweaks: EN RTWK_09 still explains the section and points at the idle timeouts; plain ASCII",
      en09.startswith("How many connections the router tracks, and how long an idle one is kept.") and "idle timeouts below" in en09
      and all(31 < ord(c) < 127 for c in en09), en09)
_p09 = {}
for p in PACKS:
    m = re.findall(r"^RTWK_09=(.*)$", open(os.path.join(www, p + ".dict"), encoding="utf-8").read(), re.M)
    if len(m) == 1 and m[0].strip() and not any(c in m[0] for c in ('"', "`", "${", "<", ">")): _p09[p] = m[0]
check("RTWK_09 once in every pack, translated (no pack carries the EN text) and not cut short",
      len(_p09) == len(PACKS) == 25 and not [p for p in PACKS if p != "EN" and _p09[p] == en09] and all(len(v) > 60 for v in _p09.values()),
      sorted(set(PACKS) - set(_p09)) or {p: len(v) for p, v in _p09.items()})

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

# ---- 2026-11-16 (review): SNMP SET is kept (owner 2026-08-19) but reaches only the three descriptive system objects.
# "rwuser" made every writable object settable: interface state, the agent's user and access tables, and the module
# loader (ucd-snmp/dlmod), which loads a library by path as root. The loader leaves the build.
snmpc = rd(os.path.join(SRC, "rc", "snmpd.c"))
code = re.sub(r"/\*.*?\*/", "", snmpc, flags=re.S)
check("rc/snmpd.c writes no rwuser line", "rwuser" not in code)
check("the user gets explicit group / view / access lines: read everything, write the system view only",
      'fprintf(fp, "group reaper_g usm %s\\n", user);' in code and 'fprintf(fp, "view reaper_all included .1\\n");' in code
      and 'fprintf(fp, "access reaper_g \\"\\" usm %s exact reaper_all %s none\\n", level,' in code)
wv = re.findall(r'view reaper_set included (\S+?)\\n', code)
check("the write view is sysContact, sysName and sysLocation and nothing else",
      sorted(wv) == [".1.3.6.1.2.1.1.4", ".1.3.6.1.2.1.1.5", ".1.3.6.1.2.1.1.6"], wv)
check("nothing is writable while the agent is opened to the WAN",
      'nvram_match("snmpd_wan", "1") ? "none" : "reaper_set"' in code)
check("both security levels go through the one helper", code.count('snmp_write_access(fp, user, "priv");') == 1
      and code.count('snmp_write_access(fp, user, "auth");') == 1)
CC = shutil.which("gcc") or shutil.which("cc")
mfn = re.search(r"static void snmp_write_access\(.*?\n}\n", snmpc, re.S)
if CC and mfn:
    td = tempfile.mkdtemp(prefix="snmpacc_")
    try:
        with open(os.path.join(td, "t.c"), "w") as f:
            f.write('#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n'
                    'static int nvram_match(const char *k, const char *v) { const char *e = getenv(k); return e && !strcmp(e, v); }\n'
                    + mfn.group(0) + 'int main(int c, char **v) { snmp_write_access(stdout, v[1], v[2]); return 0; }\n')
        r = subprocess.run([CC, "-Wall", "-Werror", "-o", os.path.join(td, "t"), os.path.join(td, "t.c")], capture_output=True, text=True)
        check("the helper compiles on the host without a warning", r.returncode == 0, r.stderr[-400:])
        if r.returncode == 0:
            out = subprocess.run([os.path.join(td, "t"), "admin", "priv"], capture_output=True, text=True).stdout
            check("snmpd.conf lines for a LAN-only agent: SET on the system view",
                  out.splitlines() == ["group reaper_g usm admin", "view reaper_all included .1",
                                       "view reaper_set included .1.3.6.1.2.1.1.4", "view reaper_set included .1.3.6.1.2.1.1.5",
                                       "view reaper_set included .1.3.6.1.2.1.1.6",
                                       'access reaper_g "" usm priv exact reaper_all reaper_set none'], out)
            out = subprocess.run([os.path.join(td, "t"), "admin", "auth"], capture_output=True, text=True,
                                 env=dict(os.environ, snmpd_wan="1")).stdout
            check("snmpd.conf lines for an agent opened to the WAN: no write view",
                  out.splitlines()[-1] == 'access reaper_g "" usm auth exact reaper_all none none', out)
    finally:
        shutil.rmtree(td, ignore_errors=True)
# ---- 2026-11-16 (owner): "Allow access from WAN" must work. The firewall opened UDP 161 on the WAN while the agent
# listened on the LAN address only. With the switch on, the agent also binds each WAN address that is up (never an
# address the router does not hold: snmpd gives up when one entry cannot be bound), and wan_up() starts it again.
check("the agent's address list is built once, with the WAN addresses only under the WAN switch",
      'if (lan_ip[0] && nvram_match("snmpd_wan", "1"))' in code and "n = snmp_wan_binds(aa, sizeof(aa), n, lan_ip);" in code
      and 'fprintf(fp, "agentAddress %s\\n", aa[0] ? aa : "udp:161");' in code)
wanc = rd(os.path.join(SRC, "rc", "wan.c"))
check("wan_up() starts the agent again when the WAN has its address (only with SNMP and WAN access on)",
      re.search(r'#ifdef RTCONFIG_SNMPD\n(?:\t\t/\*.*?\*/\n)\t\tif \(nvram_match\("snmpd_enable", "1"\) && nvram_match\("snmpd_wan", "1"\)\) \{\n'
                r'\t\t\tstop_snmpd\(\);\n\t\t\tstart_snmpd\(\);\n\t\t\}\n#endif\n', wanc, re.S) is not None)
svc = rd(os.path.join(SRC, "rc", "services.c"))
check("a login-name change starts the agent again (the SNMPv3 user is the login name)",
      re.search(r'strcmp\(script, "chpass"\) == 0\) \{\n\t+setup_passwd\(\);\n#ifdef RTCONFIG_SNMPD\n(?:\t+/\*.*?\*/\n)\t+if \(nvram_match\("snmpd_enable", "1"\)\) \{\n'
                r'\t+stop_snmpd\(\);\n\t+start_snmpd\(\);\n\t+\}\n#endif\n', svc, re.S) is not None)
dfl = rd(os.path.join(SRC, "shared", "defaults.c"))
check("SNMP and its WAN access are off at factory", re.search(r'\{ "snmpd_enable", "0",', dfl) is not None
      and re.search(r'\{ "snmpd_wan", "0",', dfl) is not None)
mw = re.search(r"/\* REAPER-SNMP-WAN-BEGIN.*?/\* REAPER-SNMP-WAN-END \*/", snmpc, re.S)
check("the WAN bind helpers are found", mw is not None)
if CC and mw and sys.platform.startswith("linux"):
    td = tempfile.mkdtemp(prefix="snmpwan_")
    try:
        with open(os.path.join(td, "t.c"), "w") as f:
            f.write('#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n#include <arpa/inet.h>\n#include <ifaddrs.h>\n'
                    '#include <netinet/in.h>\n#define WAN_UNIT_FIRST 0\n#define WAN_UNIT_MAX 2\n'
                    'static const char *nvram_safe_get(const char *k) { const char *e = getenv(k); return e ? e : ""; }\n'
                    + mw.group(0) + '\nint main(int c, char **v) { char aa[320]; size_t n = snprintf(aa, sizeof(aa), "udp:%s:161", v[1]);\n'
                    ' n = snmp_wan_binds(aa, sizeof(aa), n, v[1]); printf("%s %d\\n", aa, (int)(n == strlen(aa))); return 0; }\n')
        r = subprocess.run([CC, "-Wall", "-Werror", "-o", os.path.join(td, "t"), os.path.join(td, "t.c")], capture_output=True, text=True)
        check("the WAN bind helpers compile on the host without a warning", r.returncode == 0, r.stderr[-500:])
        if r.returncode == 0:
            def binds(lan, **nv):
                return subprocess.run([os.path.join(td, "t"), lan], capture_output=True, text=True, env=dict(os.environ, **nv)).stdout.strip()
            # 127.0.0.1 is an address this host holds; 203.0.113.9 (documentation range) is on no interface
            check("a WAN address that is up is added", binds("192.0.2.1", wan0_ipaddr="127.0.0.1") == "udp:192.0.2.1:161,udp:127.0.0.1:161 1")
            check("a WAN address the router does not hold is left out (snmpd would not start on it)",
                  binds("192.0.2.1", wan0_ipaddr="203.0.113.9") == "udp:192.0.2.1:161 1")
            check("no WAN address, 0.0.0.0 or a malformed value: nothing added",
                  binds("192.0.2.1") == "udp:192.0.2.1:161 1" and binds("192.0.2.1", wan0_ipaddr="0.0.0.0") == "udp:192.0.2.1:161 1"
                  and binds("192.0.2.1", wan0_ipaddr="127.0.0.1;x") == "udp:192.0.2.1:161 1")
            check("two WAN units with one address list it once; the LAN address is never listed twice",
                  binds("192.0.2.1", wan0_ipaddr="127.0.0.1", wan1_ipaddr="127.0.0.1") == "udp:192.0.2.1:161,udp:127.0.0.1:161 1"
                  and binds("127.0.0.1", wan0_ipaddr="127.0.0.1") == "udp:127.0.0.1:161 1")
    finally:
        shutil.rmtree(td, ignore_errors=True)
rmk = os.path.join(SRC, "Makefile")
if os.path.exists(rmk):
    check("the net-snmp build carries no module loader (ucd-snmp/dlmod)", "ucd-snmp/dlmod" not in rd(rmk))

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
