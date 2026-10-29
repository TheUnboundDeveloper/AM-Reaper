#!/usr/bin/env python3
"""Parental Controls > Time Scheduling on the Reaper kit (Reaper-native UI, 2026-10-24).

Reaper_Parental.asp replaces ParentalControl.asp (MULTIFILTER_ALL / _BLOCK_ALL and the four parallel device lists
MULTIFILTER_ENABLE / _MAC / _DEVICENAME / _MACFILTER_DAYTIME_V2, applied by restart_firewall through rc/pc.c).

WHY. The stock page needed jQuery, state.js and the 2,272-line weekSchedule.js drag grid; it saved Block All Devices at
once from its switch; it let "Allow only" (M) schedules end up with no switched-on window (rc then leaves the device
unrestricted); and it stored an empty schedule as "", which httpd's block_device_internet CGI (foreach_62, skips empty
fields) reads one field short, shifting every later device's schedule. MULTIFILTER_MAC and _ENABLE are not
JFFS-whitelisted, so a long list silently stopped saving at the 1 KB nvram wall. rc/pc.c config_daytime_string set its
per-rule verdict (fftype) once before the device loop, so a device with no switched-on window listed after an M device
inherited that device's tail DROP and was blocked around the clock.
The Reaper page posts only changed keys with the stock restart, rewrites the four lists together only once a device was
added, removed, switched or rescheduled (untouched rows keep their stored text), stores an empty schedule as '<' as the
CGI does, enforces the nvram walls and rc's 64 rules per device, and asks before Block All Devices.

WHAT IT DOES. Source checks on the page, menu.js, reaper_inject.c, Reaper_Wallguard.asp, rc/pc.c and the 25 dicts;
`node --check` on the page script; and the page's own schedule functions run under node against the rc reading of
the rule format (shared/sched_v2.c, rc/pc.c config_daytime_string). Interactive behaviour (33 scenarios: add, switch,
delete, edit, refusals, walls, deep links, hostile names) was run in jsdom when the page was written.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(www, "Reaper_Parental.asp")
if not os.path.exists(PAGE):
    print("SKIP: Reaper_Parental.asp not found"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
def code_of(t):
    """the page without its HTML and JS comments (the comments cite the stock names they replace)"""
    return re.sub(r"/\*.*?\*/", "", re.sub(r"<!--.*?-->", "", t, flags=re.S), flags=re.S)

P = rd(PAGE); JS = P[P.rfind("<script>"):]; C = code_of(P)
en = rd(os.path.join(www, "EN.dict"))
PLUMB = {"current_page", "next_page", "action_mode", "action_script", "action_wait"}

# ---- page basics (same rules as every kit page) ----
check("ASCII only", not any(ord(c) > 127 for c in P))
check("on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame, SPDX header",
      '<link rel="stylesheet" href="/reaper/rp.css">' in P and '<script src="/reaper/rp.js"></script>' in P
      and '<meta name="reaper-native" content="1">' in P and 'class="rframe"' in P and "SPDX-License-Identifier: GPL-2.0-only" in P)
check("one closure, strict, no inline handlers (no page globals)",
      JS.startswith("<script>\n(function(){\n'use strict';") and JS.rstrip().endswith("})();\n</script>\n</body>\n</html>")
      and JS.count("<script>") == 1 and not re.search(r"\son[a-z]+\s*=", P) and "var esc" not in JS)
toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", P)))
miss = [x for x in toks if ("\n%s=" % x) not in en]
check("every dict token exists (%d)" % len(toks), not miss, miss)
own = sorted(int(x[5:]) for x in toks if x.startswith("RPAR_"))
check("own keys RPAR_01..N with no gap (%d)" % len(own), own == list(range(1, len(own) + 1)), own)
check("tokens in the script only inside backticks", "<#" not in re.sub(r"`[^`]*`", "", JS))
check("every nvram value read through nvram_char_to_ascii (no nvram_get into a JS string)",
      "nvram_get(" not in C and P.count("nvram_char_to_ascii(") >= 8 and ("U = rp.dec" in P or "function U(s){ try { return decodeURIComponent(s); }" in P))
check("no eval / Function / script-typed ajax, no immediate-save path (applyapp / nvramSet)",
      not re.search(r"\beval\s*\(|new Function|dataType", C) and "applyapp" not in C and "nvramSet" not in C)
check("operation-mode gate: get_operation_mode, router-mode hint, Apply off outside router / WISP",
      "get_operation_mode()" in P and 'id="modehint"' in P and "if (!ROUTING){ show('modehint', true); q('applybtn').disabled = true; }" in P)
hid = re.findall(r'<input type="hidden" name="([A-Za-z0-9_]+)" value="([^"]*)"( disabled)?>', P)
loose = [n for n, v, d in hid if n not in PLUMB and not d]
check("every setting input starts disabled (only changed keys post)", not loose, loose)
check("the six settings are the form's hidden inputs",
      sorted(n for n, v, d in hid if n not in PLUMB) == sorted(["MULTIFILTER_ALL", "MULTIFILTER_BLOCK_ALL", "MULTIFILTER_ENABLE",
                                                               "MULTIFILTER_MAC", "MULTIFILTER_DEVICENAME", "MULTIFILTER_MACFILTER_DAYTIME_V2"]))

# ---- what it posts ----
check("Apply: changed keys only, restart_firewall wait 5 (stock script), the one post in the page",
      "rp.post(document.form, changed, 'restart_firewall', 5);" in P and P.count("rp.post(") == 1
      and "if (!count(changed)){ msg(`<#RADM_63#>`); return; }" in P)
check("the four lists are rewritten together, and only after an edit",
      "if (!LEDITED) return;" in P and "c.MULTIFILTER_ENABLE = ser(ROWS, 'en'); c.MULTIFILTER_MAC = ser(ROWS, 'mac');" in P
      and "c.MULTIFILTER_DEVICENAME = ser(ROWS, 'name'); c.MULTIFILTER_MACFILTER_DAYTIME_V2 = ser(ROWS, 'sched');" in P)
check("rows read by index from the ENABLE list, as rc's get_all_pc_list; out-of-step lists flagged",
      "ROWS = en.map(function(v, i){ return {en: v, mac: mac[i] || '', name: nm[i] || '', sched: sc[i] || ''}; });" in P
      and "if (mac.length !== en.length || sc.length !== en.length){" in P)
check("a switch posts the stored text while it shows the stored state",
      "function keep(id, nv){ var on = q(id).checked; return on === (nv === '1') ? nv : (on ? '1' : '0'); }" in P)
check("Block All Devices saves at Apply and asks first",
      "if (changed.MULTIFILTER_BLOCK_ALL === '1' && !confirm(`<#RPAR_50#>`)) return;" in P)
check("Apply refused while the schedule editor is open", "if (ED){ msg(`<#RPAR_48#>`); return; }" in P)

# ---- limits ----
check("the nvram walls: MULTIFILTER_MAC 1 KB (not whitelisted), ENABLE CKN_STR128, DEVICENAME / DAYTIME_V2 CKN_STR4096",
      "var MAC_BYTES = 1006 - 'MULTIFILTER_MAC='.length;" in P and "var EN_BYTES = 127;" in P and "var LIST_BYTES = 4095;" in P
      and "if (ser(rows, 'mac').length > MAC_BYTES || ser(rows, 'en').length > EN_BYTES" in P)
check("device / rule caps: ui MaxRule_parentctrl (16), MaxRule_PC_DAYTIME (128), rc's 64 rules per device",
      "var MAX_DEV = uiNum('MaxRule_parentctrl', 16);" in P and "var MAX_WIN_ALL = uiNum('MaxRule_PC_DAYTIME', 128);" in P
      and "var MAX_WIN_DEV = 64;" in P and "if (ED.wins.length + ED.other.length > MAX_WIN_DEV) return edmsg(" in P)
check("one unicast device per row: multicast / broadcast / zero MAC refused, duplicate refused",
      "function macOk(s){ return rp.v.mac(s) && !(parseInt(s.slice(0, 2), 16) & 1) && s !== '00:00:00:00:00:00'; }" in P
      and "return edmsg('dmsg', `<#JS_duplicate#>`, 'd_mac');" in P)
check("names: no < > separators, no leading @ (PMS group marker), 31 chars (rc strlcpy 32)",
      "var NAME_MAX = 31;" in P and "replace(/[<>\\x00-\\x1f\\x7f]/g, '').replace(/^@+/, '').trim().slice(0, NAME_MAX)" in P)
check("allow-only (M) needs a switched-on window: refused in the editor and at Apply",
      "if (ED.mode === 'M' && !ED.wins.some(function(w){ return w.on; })) return edmsg('emsg', `<#RPAR_47#>`);" in P
      and "if (LEDITED && loose.length){ msg(sub(`<#RPAR_49#>`, devName(loose[0]))); return; }" in P)
check("an empty schedule is stored as '<' (block_device_internet CGI form), untouched schedules never re-encoded",
      "return t.length ? t.join('<') : '<';" in P and "if (s !== r.sched && !(s === '<' && r.sched === '')){" in P)
check("schedule entries the editor does not model are kept verbatim", "else out.other.push(t);" in P and ".concat(other)" in P)
check("stock hand-off kept: time_scheduling_mac cookie and ?mac= open that device",
      "time_scheduling_mac" in P and "/[?&]mac=([^&]*)/" in P)

# ---- the schedule functions, run under node against rc's reading of the rule format ----
node = shutil.which("node")
s0, s1 = JS.find("/* ---------- schedules"), JS.find("/* ---------- the device list")
if node and s0 > 0 and s1 > s0:
    fn = JS[s0:s1]
    harness = ("var DAYS = [1, 2, 3, 4, 5, 6, 0];\n" + fn + "\n"
      "var out = {};\n"
      "out.parse = parseSched('W13E21000700<W04122000800<D1123<M1010000');\n"
      "out.mixed = parseSched('W13E21000700<M17F08001700');\n"
      "out.empty = parseSched('<');\n"
      "out.ser = [serSched('M', [{on: true, d: 62, a: '0800', z: '1500'}, {on: false, d: 65, a: '2200', z: '2400'}], ['D1123']), serSched('W', [], [])];\n"
      "out.span = [['2100','0700'],['0000','2400'],['0000','0000'],['0800','0800'],['0800','1700'],['2100','0000']].map(function(p){ return span({a: p[0], z: p[1]}); });\n"
      "out.segs = [segs({d: 0x01, a: '2100', z: '0700'}), segs({d: 0x40, a: '2200', z: '0000'}), segs({d: 0x7F, a: '0000', z: '2400'}).length];\n"
      "out.count = [winCount('<'), winCount(''), winCount('W13E21000700<W14122000800')];\n"
      "out.io = [toInput('2400'), fromInput('00:00', true), fromInput('00:00', false), fromInput('7:5', false)];\n"
      "console.log(JSON.stringify(out));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(harness); hp = f.name
    r = subprocess.run([node, hp], capture_output=True, text=True); os.unlink(hp)
    try:
        o = json.loads(r.stdout)
    except Exception:
        o = None
    check("schedule functions run under node", o is not None, (r.stderr or r.stdout)[-300:])
    if o:
        check("parse: W rules (enable, hex weekday mask), other rule types and malformed entries kept aside",
              o["parse"]["mode"] == "W" and [(w["on"], w["d"], w["a"], w["z"]) for w in o["parse"]["wins"]] == [(True, 62, "2100", "0700"), (False, 65, "2200", "0800")]
              and o["parse"]["other"] == ["D1123", "M1010000"], o["parse"])
        check("parse: a second mode in one device is kept aside, not merged", o["mixed"]["mode"] == "W" and o["mixed"]["other"] == ["M17F08001700"], o["mixed"])
        check("parse: the '<' placeholder is an empty W schedule", o["empty"] == {"mode": "W", "wins": [], "other": []}, o["empty"])
        check("serialise: <mode><enable><2-hex mask><start><end>, others appended; empty = '<'",
              o["ser"] == ["M13E08001500<M04122002400<D1123", "<"], o["ser"])
        check("span: past midnight / whole day (0000-2400 and 0000-0000) / start = end refused / inside one day / until midnight",
              o["span"] == ["next", "all", "all", "same", "", ""], o["span"])
        check("segments as rc builds them: Sunday 21-07 = Sun 21:00-24:00 + Mon 00:00-07:00; Saturday 22-00 stays on Saturday",
              o["segs"][0] == [[0, 1260, 1440], [1, 0, 420]] and o["segs"][1] == [[6, 1320, 1440]] and o["segs"][2] == 7, o["segs"])
        check("counting: '<' and '' hold no rule", o["count"] == [0, 0, 2], o["count"])
        check("time inputs: end 00:00 stored as 2400 (midnight), start 00:00 as 0000, junk refused",
              o["io"] == ["00:00", "2400", "0000", None], o["io"])
    body = JS[len("<script>"):JS.rfind("</script>")]
    body = re.sub(r"<%.*?%>", "", body); body = re.sub(r"`[^`]*`", "''", body)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(body); jp = f.name
    r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
    check("page script parses (node --check)", r.returncode == 0, r.stderr[-300:])
else:
    print("note: node not found or the schedule block moved - function checks skipped")

# ---- wiring ----
mj = rd(os.path.join(www, "reaper", "menu.js"))
check("menu: the Time Scheduling tab opens Reaper_Parental.asp; the stock page is gone from the rail",
      "T('Reaper_Parental.asp', `<#Time_Scheduling#>`, sup('PARENTAL2'))" in mj and "T('ParentalControl.asp'" not in mj)
inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c"))
check("httpd: the page is native; ParentalControl.asp redirects to it",
      '\t"Reaper_Parental.asp",' in inj and '{ "parentalcontrol.asp", "Reaper_Parental.asp", ' in inj)
sh = rd(os.path.join(www, "Reaper_Wallguard.asp"))
check("Wallguard's time-scheduling link points at the Reaper page",
      "pl.href = '/reaper_shell.asp#Reaper_Parental.asp';" in sh and "#ParentalControl.asp" not in sh)
lc = os.path.join(HERE, "..", "reaper_langcheck.py")
check("langcheck OUR[] lists the page", os.path.exists(lc) and "'Reaper_Parental.asp'" in rd(lc))
packs = 'EN DE FR ES BR IT NL DA NO SV FI PL CZ SL HU RO RU UK TR MS TH JP KR CN TW'.split()
lost = [pk for pk in packs if not all(("\nRPAR_%02d=" % n) in rd(os.path.join(www, pk + ".dict")) for n in own)]
check("every RPAR_ key in all 25 packs", not lost, lost)

# ---- rc/pc.c: the per-device verdict ----
pc = rd(os.path.join(SRC, "rc", "pc.c"))
v3 = pc[pc.find("void config_daytime_string"):]
v3 = v3[:v3.find("\n}\n")]
loop = v3[v3.find("for(follow_pc = enabled_list;"):]
check("rc/pc.c config_daytime_string resets fftype for every device (no allow-only DROP leaking into the next device)",
      loop.find("fftype = logdrop;") >= 0 and loop.find("fftype = logdrop;") < loop.find("for(follow_e = follow_pc->events;"))

# ---- parity file ----
f = os.path.join(HERE, "ui_parity", "ParentalControl.json")
check("parity file ParentalControl.json -> Reaper_Parental.asp",
      os.path.exists(f) and json.load(open(f, encoding="utf-8")).get("replacement") == "Reaper_Parental.asp")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
