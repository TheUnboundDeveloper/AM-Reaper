#!/usr/bin/env python3
"""UI audit items the owner approved 2026-11-05 (review 2026-10-24 Q-C1-6 / Q-C1-11 / Q-C2-8 / Q-C2-12, the Wireless
Log refresh decision of 2026-10-30, review 2026-11-03 INFO B-5).

WHY. Each item changes shipped behaviour or removes shipped code; these pins hold the new behaviour.
- Q-C1-6: the Internet page's WAN MAC clone check is the kit's rp.v.macUnicast (Tor and LAN use it), so an all-zero
  MAC is refused on its tab (stock accepted 00:00:00:00:00:00).
- Wireless Log: 10 s refresh by default; only a rate the user picks is stored (the old page stored 'rwlog_rate' = '5'
  on every load, so a legacy '5' is the old default, any other legacy value a choice); hidden tabs do not poll.
- B-5: the status endpoint is JSON (httpd get_wl_status_json rewrites the stock get_wl_status text) and the page
  JSON.parses it - no new Function. The rewrite is compiled on the host and run against producer-shaped text,
  checked against what the old page's new Function made of the same text.
- Q-C2-8: the ten stock rail glyphs no model menu emits and the dead firewall rail badge are gone.
- Q-C1-11: rp.changed creates the hidden input for a field the form lacks, so the kit pages no longer carry their
  key lists as disabled hidden inputs; the five apply inputs stay.
- Q-C2-12: Wallguard and Encrypted DNS use rp.css's base, buttons, pills and tokens; their own layout stays.

WHAT IT DOES. Source checks on the pages, the kit and httpd; a gcc + node run of the JSON rewrite.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_WLog.asp")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
node = shutil.which("node")

# ---------------- Q-C1-6 ----------------
INET = rd(os.path.join(www, "Reaper_Internet.asp"))
check("Q-C1-6: the WAN MAC is checked with rp.v.macUnicast (all-zero refused), the stock-only regex is gone",
      "!rp.v.macUnicast(c.wan_hwaddr_x)) return bad('i_mac', T.eMac);" in INET and "02468aceACE" not in INET)
RPJS = rd(os.path.join(www, "reaper", "rp.js"))
check("Q-C1-6: rp.v.macUnicast refuses group and all-zero addresses",
      "rp.v.macUnicast = function(s){ return rp.v.mac(s) && parseInt(s.substring(0, 2), 16) % 2 === 0 && !/^(00:){5}00$/.test(s); };" in RPJS)

# ---------------- Wireless Log ----------------
W = rd(os.path.join(www, "Reaper_WLog.asp"))
check("WLog: 10 s by default; a legacy 'rwlog_rate' other than the old auto-stored '5' is kept; only a pick is stored",
      "q('s_rate').value = r0 !== null ? r0 : (r1 !== null && r1 !== '5' ? r1 : '10');" in W
      and "localStorage.setItem('rwlog_refresh', q('s_rate').value)" in W and W.count("localStorage.setItem('rwlog_r") == 1
      and '<option value="10">10 s</option>' in W)
check("WLog: no poll while the tab is hidden, one refresh when it shows again",
      "timer = setInterval(function(){ if (!document.hidden) load(); }, r * 1000);" in W
      and "document.addEventListener('visibilitychange', function(){ if (!document.hidden && timer) load(); });" in W)

# ---------------- B-5 ----------------
AJ = rd(os.path.join(www, "ajax_reaper_wlstatus.asp"))
check("B-5: ajax_reaper_wlstatus.asp runs get_wl_status_json only", AJ.strip() == "<% get_wl_status_json(); %>")
check("B-5: the page JSON.parses the endpoint; nothing is evaluated",
      "var o = JSON.parse(txt), by = function(n){ return [0, 1, 2, 3].map(function(i){ return o[n + i]; }); };" in W
      and "new Function" not in W and "eval(" not in W)
WEB = rd(os.path.join(SRC, "httpd", "web.c")); C = WEB
STOCK = rd(os.path.join(SRC, "httpd", "sysdeps", "web-broadcom-am.c"))
check("B-5: get_wl_status_json registered next to get_wl_status (same #ifdef), defined in web.c (_GNU_SOURCE: open_memstream)",
      '\t{ "get_wl_status", ej_wl_status_array},\n\t{ "get_wl_status_json", ej_wl_status_json},' in WEB
      and "#ifdef RTCONFIG_BCMWL6\n/* reaper 2026-11-05 (review 2026-11-03 B-5)" in WEB and "\nstatic int\nej_wl_status_json(" in WEB
      and "#define _GNU_SOURCE" in WEB[:3000] and "reaper_wl_json" not in STOCK)
check("B-5: the stock producer still feeds the stock pages; the JSON ej captures it and replies {} on any odd shape",
      "ej_wl_status_array(eid, m, argc, argv);" in C and 'ret = websWrite(wp, "{}");' in C
      and "reaper_wl_json(txt, out) == 0" in C and "malloc(6 * len + 16)" in C)
m = re.search(r"\nstatic int\nreaper_wl_json\(const char \*s, char \*o\)\n\{.*?\n\}\n", C, re.S)
check("B-5: reaper_wl_json() found", m is not None)
gcc = shutil.which("gcc")
if m and gcc and node:
    # producer-shaped text: str_escape_quotes' \' \" \\, a guest SSID escaped by the Reaper loop, the trailing "-1",
    # a dataarray with no mode (trailing comma), a DFS line with spaces, a radio that is off (nothing), raw < > &,
    # a control byte and UTF-8 inside a hostname
    GOOD = [
        'dataarray0 = ["Home\\\'s \\"net\\" \\\\x","-55","20","-92","6/20","AA:BB:CC:DD:EE:FF","12","AP"];\n'
        'wificlients0 = [["11:22:33:44:55:66","192.168.50.2","O\\\'Brien <pc> & co","fe80::1","-40","866","1200","  1:02:03","2","ax","80","PSTAU","",""],'
        '["22:33:44:55:66:77","","","","?","??","??","","","","","_A_","Guest \\"x\\" \\\\","52"],"-1"];\n'
        '\n'
        'dataarray1 = ["Not associated. Last with <unknown>","0","0","0","0","","-1",];\n'
        'var dfs_statusarray1 = ["Idle", "0 s", "None"];\n'
        'wificlients1 = ["-1"];\n'
        'dataarray2 = ["caf\xc3\xa9\x01tab","-1","0","0","36/160","00:11:22:33:44:55","-1","Repeater ( SSID local: a\\\'b )"];\n'
        'wificlients2 = [];\n',
        '',
    ]
    BAD = ['dataarray0 = [foo];', 'dataarray0 = ["a" "b"];', 'dataarray0 = ["a",,"b"];', 'dataarray0 = ["a\\nb"];',
           'dataarray0 = ["a"]', 'x = [["a"];', 'dataarray0 = ["a"]; alert(1);', 'dataarray0 = ]', '= ["a"];']
    harness = ("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <ctype.h>\n" + m.group(0) +
               "int main(void){ static char in[1 << 16], out[6 << 16]; size_t n = fread(in, 1, sizeof(in) - 1, stdin); in[n] = 0;\n"
               "  if (reaper_wl_json(in, out)) { fputs(\"REFUSED\", stdout); return 0; } fputs(out, stdout); return 0; }\n")
    d = tempfile.mkdtemp()
    open(os.path.join(d, "t.c"), "w").write(harness)
    r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-o", os.path.join(d, "t"), os.path.join(d, "t.c")], capture_output=True, text=True)
    check("B-5: reaper_wl_json compiles clean on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr[-400:])
    if r.returncode == 0:
        def conv(s):
            return subprocess.run([os.path.join(d, "t")], input=s.encode("latin-1"), capture_output=True).stdout.decode("utf-8", "replace")
        OLD = r"""
function oldParse(txt){
  var src = 'var dataarray0, dataarray1, dataarray2, dataarray3, wificlients0, wificlients1, wificlients2, wificlients3,' +
    ' dfs_statusarray0, dfs_statusarray1, dfs_statusarray2, dfs_statusarray3;\n' + txt +
    '\n;return {d: [dataarray0, dataarray1, dataarray2, dataarray3], c: [wificlients0, wificlients1, wificlients2, wificlients3],' +
    ' f: [dfs_statusarray0, dfs_statusarray1, dfs_statusarray2, dfs_statusarray3]};';
  return (new Function(src))();
}
"""
        pm = re.search(r"\nfunction parse\(txt\)\{\n.*?\n\}\n", W, re.S)
        check("B-5: the page's parse() found", pm is not None)
        same = []
        for g in GOOD:
            js = conv(g)
            prog = OLD + (pm.group(0) if pm else "") + (
                "var a = oldParse(%s), b = parse(%s); console.log(JSON.stringify(a) === JSON.stringify(b) ? 'SAME' : 'DIFF ' + JSON.stringify(a) + ' || ' + JSON.stringify(b));"
                % (json.dumps(g.encode("latin-1").decode("utf-8")), json.dumps(js)))
            fd, jp = tempfile.mkstemp(suffix=".js"); os.close(fd); open(jp, "w", encoding="utf-8").write(prog)
            rr = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
            same.append(rr.stdout.strip() or rr.stderr[-300:])
        check("B-5: on producer-shaped text the JSON gives the page exactly what new Function gave it (%d cases)" % len(GOOD),
              all(x == "SAME" for x in same), same)
        js0 = conv(GOOD[0])
        check("B-5: the JSON carries no raw < > & and no raw control byte", not re.search(r"[<>&\x00-\x1f]", js0), js0[:200])
        refused = [b for b in BAD if conv(b) != "REFUSED"]
        check("B-5: any other shape is refused (the reply becomes {})", not refused, refused)
    shutil.rmtree(d, ignore_errors=True)
elif not (gcc and node):
    print("note: gcc or node not found - the JSON rewrite run skipped")

# ---------------- Q-C2-8 ----------------
MENU = rd(os.path.join(www, "reaper", "menu.js")); SHELL = rd(os.path.join(www, "reaper_shell.asp")); DASH = rd(os.path.join(www, "Main_ReaperDash.asp"))
mi = re.search(r"var ICONS\s*=\s*\{(.*?)\n\s*\};", MENU, re.S)
keys = re.findall(r"^\s*(\w+)\s*:\s*'<svg", mi.group(1), re.M) if mi else []
model = sorted(set(re.findall(r"index: '(menu_\w+)'", MENU)) - {"menu_Split"})
check("Q-C2-8: ICONS holds exactly the model's menus + menu_Addons + _default (the ten stock-only glyphs are gone)",
      mi is not None and sorted(keys) == sorted(model + ["menu_Addons", "_default"]), sorted(set(keys) ^ set(model + ["menu_Addons", "_default"])))
check("Q-C2-8: an index without a glyph draws _default", "icon: ICONS[m.index] || ICONS._default" in MENU and "var ic=ICONS[m.index]||ICONS._default;" in SHELL)
check("Q-C2-8: the firewall rail badge is gone from the model, the shell and the dashboard",
      not any(x in MENU for x in ("badge", "fwred")) and not any(x in SHELL for x in ("setFwBadge", "FW_RED", "nbadge", "fwred"))
      and not any(x in DASH for x in ("setFwBadge", "nbadge", "fwred")))
fb = re.search(r"\nfunction railFallback\(\)\{\n(.*?)\n\}\n", SHELL, re.S)
check("Q-C2-8: railFallback() only draws the static rail (buildRail), no setter is called",
      fb is not None and "buildRail({" in fb.group(1) and "set" not in re.sub(r"buildRail|tabName|__HIDE__", "", fb.group(1)).lower().replace("setting", ""))

# ---------------- Q-C1-11 ----------------
KIT = ["DDNS", "DNS", "IPTV", "IPv6Setup", "Internet", "LAN", "Log", "NAT", "Parental", "Routes", "SNMP", "System", "Tor", "Tweaks",
       "VPNClient", "VPNDirector", "VPNServer", "WOL"]
PLUMB = ["current_page", "next_page", "action_mode", "action_script", "action_wait"]
check("Q-C1-11: rp.changed creates the hidden input of a field the form lacks, then enables and sets it",
      "      el = form.elements.namedItem(k);\n      if (!el){ el = document.createElement('input'); el.type = 'hidden'; el.name = k; form.appendChild(el); }\n"
      "      el.disabled = false; el.value = fields[k]; }" in RPJS and "rp.changed(form, fields || {});" in RPJS)
bad = {}
for p in KIT:
    t = rd(os.path.join(www, "Reaper_%s.asp" % p))
    s = t.find('<form method="post" name="form" action="/start_apply.htm" target="hidden_frame">'); e = t.find("</form>", s)
    names = re.findall(r'<input type="hidden" name="([A-Za-z0-9_]+)"', t[s:e])
    extra = [n for n in names if n not in PLUMB and not (p == "Internet" and n == "wan_unit")]
    if s < 0 or extra or sorted(set(names) & set(PLUMB)) != sorted(PLUMB) or "rp.post(" not in t or "document.createElement('input'); x.type = 'hidden'" in t:
        bad[p] = extra or "shape"
check("Q-C1-11: the %d kit pages' settings forms hold only the five apply inputs (Internet: + wan_unit), post through rp.post and "
      "create no inputs themselves" % len(KIT), not bad, bad)
mc = re.search(r"\n  rp\.changed = function\(form, fields\)\{\n.*?\n  \};\n", RPJS, re.S)
if mc and node:
    prog = r"""
var made = [];
var document = {createElement: function(t){ var e = {tag: t, disabled: true, value: ''}; made.push(e); return e; }};
function Form(names){ var els = {}; names.forEach(function(n){ els[n] = {name: n, disabled: true, value: ''}; });
  this.els = els; this.added = []; var self = this;
  this.elements = {namedItem: function(n){ return Object.prototype.hasOwnProperty.call(els, n) ? els[n] : (self.added.filter(function(e){ return e.name === n; })[0] || null); }};
  this.appendChild = function(e){ self.added.push(e); }; }
var rp = {};
""" + mc.group(0) + r"""
var f = new Form(['action_script', 'wan_unit']);
var fields = Object.create({inherited: 'x'}); fields.wan_unit = '0'; fields.wan_proto = 'pppoe'; fields.wans_mode = 'fo';
rp.changed(f, fields); rp.changed(f, {wan_proto: 'dhcp'});
console.log(JSON.stringify({unit: [f.els.wan_unit.disabled, f.els.wan_unit.value], added: f.added.map(function(e){ return [e.type, e.name, e.disabled, e.value]; }),
  other: f.els.action_script.disabled}));
"""
    fd, jp = tempfile.mkstemp(suffix=".js"); os.close(fd); open(jp, "w", encoding="utf-8").write(prog)
    rr = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
    try: got = json.loads(rr.stdout)
    except ValueError: got = rr.stderr[-300:]
    check("Q-C1-11: rp.changed under node - an existing input is enabled and set, a missing one created once (reused on the next "
          "post), inherited keys and untouched inputs left alone",
          got == {"unit": [False, "0"], "added": [["hidden", "wan_proto", False, "dhcp"], ["hidden", "wans_mode", False, "fo"]], "other": True}, got)

# ---------------- Q-C2-12 ----------------
CSS = rd(os.path.join(www, "reaper", "rp.css"))
ROOT = set(re.findall(r"(--[a-z0-9-]+):", CSS[CSS.find(":root{"):CSS.find("}", CSS.find(":root{"))]))
for p in ("Reaper_Wallguard.asp", "Reaper_EncryptedDNS.asp"):
    t = rd(os.path.join(www, p))
    st = t[t.find("<style>"):t.find("</style>")]
    check("Q-C2-12 %s: links rp.css before its own style block; ASCII only" % p,
          '<link rel="stylesheet" href="/reaper/rp.css">\n<style>' in t and not any(ord(c) > 127 for c in t))
    gone = [r for r in ("@font-face", ":root", "\n*{", "html,body", "\na{", "h1,h2,h3", "\n.pagehead{", "\n.statuspill", "\n.btn{", ".btng",
                        "\n.applying", "\n.duo", "--danger") if r in st]
    check("Q-C2-12 %s: none of rp.css's base is copied (fonts, tokens, *, html/body, a, h1-h3, head, pill, buttons, overlay, duo)" % p, not gone, gone)
    check("Q-C2-12 %s: only a body font size of its own (rp.css sets none), no other body rule" % p,
          st.count("body{") == 1 and "\nbody{font-size:13.5px;line-height:1.55}\n" in st)
    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", st))
    check("Q-C2-12 %s: every colour / font token it uses is one rp.css defines" % p, used and used <= ROOT, sorted(used - ROOT))
    check("Q-C2-12 %s: its own layout kept - cards, stat tiles, steps, .tg switches, warning banner" % p,
          all(x in st for x in ("\n.card{", "\n.stats{", "\n.stat{", "\nol.steps{", "\n.tg{", "\n.tg.on::after{")) and ('class="stats"' in t))
    check("Q-C2-12 %s: kit markup - .syswrap frame, Save is .btn.primary, secondary .btn.ghost, rp.css pill states, kit overlay" % p,
          '<div class="syswrap">' in t and '<button class="btn primary" data-act="save">' in t and 'class="btng' not in t and "'btng'" not in t
          and "statuspill off" not in t and ("'statuspill ok'" in t or "(running ? ' ok' : '')" in t)
          and '<div class="abox"><h2 id="ap_t"><#Reaper_c_applying#></h2><p id="ap_p">' in t)
    markup = re.sub(r"<script>.*?</script>|<!--.*?-->", "", t, flags=re.S)
    check("Q-C2-12 %s: still one closure, no inline handlers in the markup" % p,
          not re.search(r"\son[a-z]+\s*=", markup) and t.count("<script>\n(function(){") == 1)
WGP = rd(os.path.join(www, "Reaper_Wallguard.asp"))
check("Q-C2-12 Wallguard: script-made and pending-changes buttons are the kit's ghost buttons; the DNS rewrites card is kept",
      "b.className = 'btn ghost' + (sm ? ' small' : '');" in WGP and "btnClass: 'btn ghost'," in WGP and 'id="rwbody"' in WGP and '.tbl td.acts .btn{' in WGP)

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
