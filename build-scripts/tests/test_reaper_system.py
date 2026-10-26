#!/usr/bin/env python3
"""Reaper_System.asp - Administration > System on the Reaper kit (Reaper-native UI wave 1, 2026-10-22).

WHY. The page replaces Advanced_System_Content.asp (51 posted settings, the credential flow, the certificate
buttons, the time-zone table). This pins what the parity harness cannot see: every hidden nvram input the
parity file calls "covered" exists on the form, every dict token the page uses exists, tokens sit only inside
backticks in JS (rule 29), the time-zone table was copied whole, the page is ASCII, its script parses, the
kit's rp.md5 is a correct MD5 (the /chpass.cgi contract), and the stock page is redirected + unlinked.

WHAT IT DOES. Source checks on www/Reaper_System.asp, www/reaper/rp.js, www/reaper/menu.js,
www/Main_ReaperDash.asp, www/reaper_shell.asp, httpd/reaper_inject.c; `node --check` on the page script and a
node run of rp.md5 against RFC 1321 vectors.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
www = os.path.join(SRC, "www")
P = os.path.join(www, "Reaper_System.asp")
if not os.path.exists(P):
    print("SKIP: Reaper_System.asp not found"); sys.exit(0)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
t = rd(P)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

check("ASCII only", not any(ord(c) > 127 for c in t))
check("on the kit: rp.css + rp.js, reaper-native meta, no jQuery / httpApi / state.js",
      '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
      and '<meta name="reaper-native" content="1">' in t and not re.search(r'src="/(js/jquery|js/httpApi|state)\.js"', t))

# every covered field of the parity file is a hidden input, disabled (changed-fields-only pattern)
par = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_parity", "Advanced_System_Content.json"), encoding="utf-8"))
covered = [k for k, v in par["fields"].items() if v == "covered"]
missing = [k for k in covered if '<input type="hidden" name="%s" value="" disabled>' % k not in t]
check("every covered setting is a disabled hidden input (%d)" % len(covered), not missing, missing)
check("the form posts to start_apply.htm with its own page name", 'name="current_page" value="Reaper_System.asp"' in t and 'name="next_page" value="Reaper_System.asp"' in t)
check("only changed settings are posted (rp.post with the diff) and the script is built per change",
      "rp.post(document.form, changed, script, wait, false)" in t and "if (has('ntpd_enable')) S.push('restart_dnsmasq');" in t
      and "S.push('restart_leds')" in t and "S.push('restart_usb_idle')" in t and "S.push('restart_httpd'); if (FTP_TLS) S.push('restart_ftpd');" in t
      and "var script = S.length ? S.join(';') : 'saveNvram'" in t)
check("credentials: the stock apply (saveNvram;restart_chpass) then rp.chpass against the current session (rule 28)",
      "f.action_script.value = 'saveNvram;restart_chpass'; f.action_wait.value = '0'; f.submit();" in t and "var rc = rp.chpass(post);" in t
      and "if (!IS_DEFAULT_PW){ post.cur_username = NV.http_username; post.cur_passwd = cur; }" in t)
check("access list: stock format <enable>ip>type, 4 entries, legacy http_client/http_clientlist kept in step",
      "return ACL.map(function(r){ return '<' + r.en + '>' + r.ip + '>' + r.type; }).join('');" in t
      and "if (ACL.length >= 4)" in t and "c.http_clientlist = ACL.map(function(r){ return '<' + r.ip; }).join('');" in t
      and "c.http_client = c.enable_acc_restriction;" in t)
check("time zone: the stock table copied whole (select + 100 zones), DST rule built as Mm.w.d/h,Mm.w.d/h, presets from /ajax/tz_db.json",
      len(re.findall(r'^\s+\["[A-Za-z0-9_.+-]+",\s*`', t, re.M)) >= 100 and '["select", `<#Select_menu_default#>`]' in t
      and "return 'M' + q('dst_start_m').value + '.' + q('dst_start_w').value" in t and "x.open('GET', '/ajax/tz_db.json', true);" in t)
check("reboot schedule: 7 day flags + HHMM, the V2 monthly form DDHHMM; like stock, only a type change resets the other field",
      "c.reboot_schedule_month = ('0' + q('s_rbmonthday').value).slice(-2) + hh + mm;" in t
      and "if (type !== NV.reboot_schedule_type){ if (type === '0') c.reboot_schedule_month = '000300'; else c.reboot_schedule = '00000000300'; }" in t)
check("SSH keys: one per line in the box, '>'-joined in nvram (what rc/ssh.c splits on)",
      "q('ta_sshd_authkeys').value = NV.sshd_authkeys.replace(/>/g, '\\n')" in t and ".filter(function(l){ return l; }).join('>');" in t)
check("shell timeout shown in minutes, stored in seconds; an untouched value keeps its exact seconds",
      "String((parseInt(m, 10) || 0) * 60)" in t and "? NV.shell_timeout :" in t)
check("mode gates: remote access, access list + WAN-down redirect router mode only; NTP server rows router/WISP; WAN SSH option dropped outside router mode",
      "if (!ROUTER){ q('p_remote').classList.add('off'); return; }" in t and "if (!ROUTER){ q('p_acl').classList.add('off'); return; }" in t
      and "show('r_natredir', ROUTER)" in t and "var ntpd = sup('ntpd') && ROUTING;" in t and "if (!ROUTER) q('o_ssh_wan').remove();" in t)
check("support gates: captcha, HTTPS, ssh, plc, dualwan, boostkey, pwrsave, pcache_ratio, hdspindown, usb3, reboot_schedule, REBOOT_SCHED_V2",
      all(("sup('%s')" % f) in t for f in ("captcha", "HTTPS", "ssh", "plc", "dualwan", "boostkey", "pwrsave", "pcache_ratio", "hdspindown", "usb3", "reboot_schedule", "REBOOT_SCHED_V2")))
check("certificate buttons follow le_enable / casignedcert / http_enable like the stock page; renew polls httpd_check.xml",
      "if (LE === '1'){ root = false; nsrv = false; nroot = false; }" in t and "else if (LE === '2'){ nroot = false; if (CAS !== '1'){ nsrv = false; root = false; } }" in t
      and "clear_file.cgi?clear_file_name=" in t and "/httpd_check.xml?_=" in t)
check("?af= deep links honoured (http_passwd2, reboot_schedule_enable_x)", "if (AF === 'http_passwd2'){ credOpen(); }" in t and "AF === 'reboot_schedule_enable_x'" in t)
check("after a protocol/port change the page follows the web interface to its new address",
      "top.location.href = base + '/reaper_shell.asp#Reaper_System.asp';" in t)
check("one-line clipped message surface with a title when clipped (rule 41)", "m.setAttribute('title', t)" in t and ".msg{font-size:12.5px;color:var(--amber);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" in t)
# r20 (2026-10-22): the r19 page declared a top-level `var esc = rp.esc`, which replaced reaper_util.js's window.esc;
# rp.esc delegated to window.esc and recursed forever, init() died at the first time-zone option, and every select
# filled after it (zone, DST, reboot day) stayed empty, so Apply refused with "Fields cannot be blank".
js_all = t[t.rfind("<script>"):]
check("the page script runs in a closure and declares no globals (a top-level var can shadow reaper_util.js's window.esc)",
      js_all.startswith("<script>\n(function(){\n'use strict';") and js_all.rstrip().endswith("boot();\n})();\n</script>\n</body>\n</html>")
      and js_all.count("<script>") == 1 and "onclick=" not in t)
check("each section initialises in its own guard; a section that failed to load is left out of Apply, not posted blank",
      "BROKEN[s.panel] = 1;" in t and "if (!BROKEN[s.panel]) s.collect(c);" in t and t.count('<div class="secerr"><#RADM_78#></div>') >= 12)
check("five tabs, empty ones hidden; a validation error opens the field's tab and marks the row",
      all(('data-t="%s"' % x) in t and ('id="tab_%s"' % x) in t for x in ("access", "ssh", "time", "hw", "maint"))
      and "w.classList.toggle('gone', !any);" in t and "if (t) showTab(t);" in t and "row.classList.add('bad');" in t)
check("access-list switch shows nvram's state (r19 handed setChk a boolean that never equalled '1')",
      "setChk('t_acl', isOn(NV.enable_acc_restriction) || isOn(NV.http_client));" in t and "setChk = rp.setChk" in t
      and "rp.setChk = function(id, on){ rp.q(id).checked = !!on; };" in rd(os.path.join(www, "reaper", "rp.js")))
check("hidden rows post nothing: the WPS-button row only when shown; an unset switch is not an edit",
      "if (shown('r_wpsbtn')){" in t and "if (was === '' && c[k] === '0' && /^t_/.test(FIELD_CTL[k] || '')) continue;" in t)

# tokens
en = rd(os.path.join(www, "EN.dict"))
toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
miss = [k for k in toks if ("\n%s=" % k) not in en]
check("every dict token the page uses exists in EN.dict (%d tokens)" % len(toks), not miss, miss)
js = t[t.rfind("<script>"):]
js_wo = re.sub(r"`[^`]*`", "", js)
check("tokens inside the script only within backticks (rule 29)", "<#" not in js_wo, [m.group(0) for m in re.finditer(r".{0,40}<#[A-Za-z0-9_]+#>", js_wo)][:3])
PACKS = "EN DE FR ES BR IT NL DA NO SV FI PL CZ SL HU RO RU UK TR MS TH JP KR CN TW".split()
# RADM_43 was never used and was pruned with the review 2026-10-24 dictionary sweep (Q-C2-9)
missing_packs = [p for p in PACKS if not all(("\nRADM_%02d=" % k) in rd(os.path.join(www, p + ".dict")) for k in range(1, 81) if k != 43)]
check("RADM_01-80 in all 25 packs (43 pruned as unused)", not missing_packs, missing_packs)
check("RADM_ does not collide with Sysinfo's RSYS_ family", "RSYS_" not in t)

# wiring
menu = rd(os.path.join(www, "reaper", "menu.js")); dash = rd(os.path.join(www, "Main_ReaperDash.asp")); shell = rd(os.path.join(www, "reaper_shell.asp"))
inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c")); rpjs = rd(os.path.join(www, "reaper", "rp.js")); rpcss = rd(os.path.join(www, "reaper", "rp.css"))
check("menu model, shell fallback rail and dashboard rows point at Reaper_System.asp; nothing Reaper-owned links the stock page",
      "T('Reaper_System.asp', `<#menu5_6_2#>`)" in menu and "Advanced_System_Content" not in menu
      and dash.count('data-go="Reaper_System.asp"') == 4 and "Advanced_System_Content" not in dash and "Advanced_System_Content" not in shell)
check("httpd SUP map redirects the stock page and keeps the query (?af=)",
      '{ "advanced_system_content.asp", "Reaper_System.asp", ' in inj
      and 'var q=location.search;if(q&&s&&s.indexOf(\\"?\\")>=0){q=\\"&\\"+q.slice(1);}' in inj   # 2026-10-24: & after a ?tab= target
      and 'top.location.replace(\\"/reaper_shell.asp#\\"+s+q);return;' in inj)
# 2026-10-23: r19/r20 were missing from reaper_native[], so httpd injected the stock skin (reaper_content.css)
# and its .tab rules drew a red border and a red hover fill on the page's tab containers.
check("httpd treats the page as native (bounce, no stock reaper_content.css)", '\t"Reaper_System.asp",' in inj
      and inj.index('\t"Reaper_System.asp",') > inj.index("static const char *reaper_native[]"))
check("each tab body sits in the kit's static crimson frame (.rframe, owner 2026-10-23), with no hover state",
      t.count('<div class="tab rframe" id="tab_') == 5 and ".rframe{background:rgba(225,6,0,.22);border:1px solid rgba(225,6,0,.30)}" in rpcss
      and not re.search(r"\.(tab|rframe)(\.on)?:hover\s*[,{]", t + rpcss))
unlisted = sorted(f for f in os.listdir(www) if f.endswith(".asp") and '<meta name="reaper-native" content="1">' in rd(os.path.join(www, f))
                  and ('"%s"' % f) not in inj)
check("every page with the reaper-native meta is on an httpd inject list (else it gets the stock skin)", not unlisted, unlisted)
check("rp.js carries rp.md5 and rp.chpass (hexMD5 current, base64 new, http_id, POST body, synchronous)",
      "rp.md5 = function(s){" in rpjs and "rp.chpass = function(post){" in rpjs and "p.http_id = '<% nvram_get(\"http_id\"); %>'" in rpjs
      and "x.open('POST', '/chpass.cgi', false);" in rpjs and "p.new_passwd = btoa(p.new_passwd);" in rpjs)
check("rp.esc delegates to reaper_util.js's ReaperEsc and never to window.esc (a page global could point that back at rp.esc)",
      "var f = window.ReaperEsc; return (typeof f === 'function' && f !== rp.esc) ? f(s)" in rpjs and "window.esc(s)" not in rpjs)

node = shutil.which("node")
if node:
    s = re.findall(r"<script>(.*?)</script>", t, re.S)[-1]
    s = re.sub(r"<%.*?%>", "0", s); s = re.sub(r"<#[A-Za-z0-9_-]+#>", "X", s)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(s); jp = f.name
    r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
    check("page script parses (node --check)", r.returncode == 0, r.stderr[-400:])
    # rp.md5 against RFC 1321 vectors, rp.js run under node with a stub DOM
    harness = ("var window = {}; var document = {readyState: 'complete', addEventListener: function(){}, querySelectorAll: function(){ return []; },"
               " getElementById: function(){ return null; }, body: {appendChild: function(){}} }; window.addEventListener = function(){};"
               " var XMLHttpRequest = function(){};\n" + re.sub(r"<%.*?%>", "", rpjs)
               + "\nconsole.log(JSON.stringify([window.rp.md5(''), window.rp.md5('abc'), window.rp.md5('message digest'), window.rp.md5('The quick brown fox jumps over the lazy dog')]));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(harness); jp = f.name
    r = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
    want = ["d41d8cd98f00b204e9800998ecf8427e", "900150983cd24fb0d6963f7d28e17f72", "f96b697d7cb7938d525a2f31aaf161d0", "9e107d9d372bb6826bd81d3542a419d6"]
    got = []
    try: got = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: pass
    check("rp.md5 matches the RFC 1321 vectors under node", got == want, (r.stderr[-300:] or got))
else:
    print("note: node not found - syntax and md5 checks skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
