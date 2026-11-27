#!/usr/bin/env python3
"""Colour-blind mode (REAPER-CBMODE, owner request 2026-11-26): Administration > System > Accessibility switches the whole
interface to a colour-blind-safe palette; only colours change.

How it works, and what this suite pins:
  - reaper/reaper_cb.css defines the palette (--cb-<role> and --cb-<role>-rgb) under html.cb ONLY. The six self-contained
    pages read before sign-in carry an identical inline copy (they load no stylesheet of the kit).
  - every Reaper colour is written var(--cb-<role>,<today's colour>) (rgba(var(--cb-<role>-rgb,R,G,B),A) for alpha): with the
    mode off the property is undefined and the fallback - today's colour - applies, so nothing changes; with the mode on
    the palette applies. A red that means "wrong / down / denied" takes the alert role (orange), the accent red the accent
    role (blue), as the owner's table says.
  - each Reaper page sets class "cb" on <html> from nvram reaper_cbmode (one line in its head); httpd adds the palette and
    the class to a stock page while the mode is on (authenticated responses only).
  - nvram reaper_cbmode: default "0" (an optional feature is off by default and has a GUI switch), carried by the settings
    backup (rcfg_flags).
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, sys, colorsys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree with httpd/reaper_inject.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:700] if detail else ""))
def rd(*p): return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()
W = os.path.join(SRC, "www")

# ---------------------------------------------------------------- the palette
css = rd("www", "reaper", "reaper_cb.css")
m = re.search(r"html\.cb\{([^}]*)\}", css)
check("reaper_cb.css: one html.cb block", m is not None and len(re.findall(r"html\.cb\{", css)) == 1)
decl = m.group(1) if m else ""
roles = dict(re.findall(r"--cb-([a-z0-9-]+):(#[0-9A-Fa-f]{6}|[0-9]+,[0-9]+,[0-9]+|rgba\([^)]*\))", decl))
OWNER = {"acc": "#3B82F6", "ok": "#38BDF8", "data": "#7DD3FC", "warn": "#FACC15", "alert": "#FB923C", "tint": "#1E293B"}
check("the owner's six colours, as given", all(roles.get(k, "").upper() == v for k, v in OWNER.items()),
      dict((k, roles.get(k)) for k in OWNER))
def rgb(h): return "%d,%d,%d" % (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))
bad_rgb = [k for k, v in roles.items() if v.startswith("#") and roles.get(k + "-rgb") != rgb(v)]
check("every role has a matching -rgb twin", not bad_rgb, bad_rgb)
check("the palette sheet holds nothing outside html.cb (no rule that applies with the mode off)",
      re.sub(r"/\*.*?\*/", "", css, flags=re.S).strip() == "html.cb{" + decl + "}")

# ---------------------------------------------------------------- pages
SELF = ["Main_Login.asp", "Main_Password.asp", "Logout.asp", "error_page.htm", "blocking.asp", "message.htm"]
LINE = '<script>/*REAPER-CBMODE*/if(<% nvram_get_js("reaper_cbmode"); %>==="1")document.documentElement.classList.add("cb");</script>'
pages = sorted(f for f in os.listdir(W) if (f.startswith("Reaper_") and f.endswith(".asp")) or f in ("Main_ReaperDash.asp", "reaper_shell.asp")) + SELF
miss, twice, nolink, inl = [], [], [], []
for f in pages:
    t = rd("www", f)
    if not re.search(r"var\(--|#[0-9a-fA-F]{6}\b|rgba?\(", t):
        continue                                   # a page with no colour of its own (e.g. a text fragment)
    n = t.count(LINE)
    if n == 0: miss.append(f)
    elif n > 1: twice.append(f)
    head = t[:t.lower().find("</head>")]
    if LINE not in head and n: miss.append(f + " (not in the head)")
    if f in SELF:
        im = re.search(r"<style>html\.cb\{([^}]*)\}</style>", head)
        if not im or im.group(1) != decl: inl.append(f)
    elif '<link rel="stylesheet" href="/reaper/reaper_cb.css">' not in head:
        nolink.append(f)
check("every Reaper page with colours sets the class from reaper_cbmode, once, in its head", not miss and not twice, (miss, twice))
check("the kit and native pages load reaper/reaper_cb.css", not nolink, nolink)
check("the six self-contained pages carry the palette inline, identical to reaper_cb.css", not inl, inl)

# ---------------------------------------------------------------- every colour can switch
HEX = re.compile(r"(?<![\w&-])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![\w-])")
RGBX = re.compile(r"\brgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})")
KEEP = {"ECE7DB", "B7B1A4", "71767B", "7EA6C9", "8AA6BE", "8894A0", "2597FF", "248DFF", "006CE1", "3366FF", "0091FF", "4CB4FF",
        "569AC7", "279FD9", "00BFFF", "2ED3F1", "00FBBD", "45FFF0", "CCE4FF", "1F2D35", "1E2A41", "283A46", "192229"}
def chromatic(h):
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    _, l, s = colorsys.rgb_to_hls(r, g, b)
    return not (s < 0.18 or l < 0.06 or l > 0.95)
def strip(css_text):
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    css_text = re.sub(r"html\.cb\{[^}]*\}", "", css_text)
    css_text = re.sub(r"\{(\s*--cb-[a-z0-9-]+:[^;{}]*;?)+\s*\}", "{}", css_text)   # rules that only set the palette
    css_text = re.sub(r"\[[^\]]*\]", "", css_text)              # attribute selectors quote stock colours
    return re.sub(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|url\([^)]*\)", "", css_text)
loose = []
def scan(where, text):
    for mm in HEX.finditer(text):
        h = mm.group(1).upper(); h = "".join(c * 2 for c in h) if len(h) == 3 else h
        if chromatic(h) and h not in KEEP and not re.search(r"var\(--cb-[a-z0-9-]+,\s*$", text[:mm.start()]):
            loose.append("%s #%s" % (where, h))
    for mm in RGBX.finditer(text):
        h = "%02X%02X%02X" % tuple(min(255, int(mm.group(i))) for i in (1, 2, 3))
        if chromatic(h) and h not in KEEP and not text[mm.start():mm.start() + 40].startswith(("rgba(var(--cb-", "rgb(var(--cb-")):
            loose.append("%s rgb(%s)" % (where, h))
for f in pages:
    t = rd("www", f)
    t = re.sub(r"<script[^>]*>.*?</script>", "", t, flags=re.S | re.I)
    for b in re.findall(r"<style[^>]*>(.*?)</style>", t, re.S | re.I):
        scan(f, strip(b))
    for a in re.findall(r'\sstyle="([^"]*)"', t):
        scan(f + " style=", a)
sheets = ["reaper/rp.css", "reaper/reaper_content.css", "reaper/reaper_content_aimesh.css", "reaper/reaper_content_network.css",
          "reaper/internet_speed_reaper.css", "reaper_qis.css"]
for s in sheets:
    if os.path.isfile(os.path.join(W, s)):
        scan(s, strip(rd("www", s)))
check("no colour left that cannot switch (stylesheets, style blocks, style attributes)", not loose, loose[:12])
used = set()
for f in pages + sheets + ["reaper_util.js", "reaper/reaper_pending.js", "reaper/reaper_sdn_defer.js"]:
    if os.path.isfile(os.path.join(W, f)):
        used |= set(re.findall(r"--cb-([a-z0-9-]+)", rd("www", f)))
used |= set(re.findall(r'cbv\("([a-z0-9-]+)"', rd("www", "Reaper_QoSDiag.asp")))
used |= set(re.findall(r'wqc\("([a-z0-9-]+)"', rd("www", "Reaper_Wireless.asp")))
undef = sorted(u for u in used if u not in roles and u not in ("alert-wash",))
check("every --cb-* name the pages use is defined by the palette", not undef, undef)
check("alert-wash defined (the wash behind an error box)", "--cb-alert-wash:" in decl)

# ---------------------------------------------------------------- meanings: red that means wrong takes the alert role
sysp = rd("www", "Reaper_System.asp")
check("an invalid field is marked with the alert colour", ".frow.bad input,.frow.bad select,.frow.bad textarea{border-color:var(--cb-alert,var(--crimson))!important" in sysp)
tr = rd("www", "Reaper_Traffic.asp")
check("Traffic: download = data (Sky Ice), upload = alert (orange) in the tiles, the legend and the chart",
      ".tile .v.up{color:var(--cb-alert,var(--jade))} .tile .v.dn{color:var(--cb-data,var(--s1))}" in tr
      and "new LiveChart('wanchart',[],['var(--cb-data,var(--jade))','var(--cb-alert,var(--crimson))'," in tr
      and "{data:rxbps,color:'var(--cb-data,var(--jade))'},{data:txbps,color:'var(--cb-alert,var(--crimson))'}" in tr)
wl = rd("www", "Reaper_Wireless.asp")
check("Wireless: channel quality resolved for the report window too", wl.count("function wqc(") == 1 and 'wqc("alert-deep","#c1121f")' in wl)
qd = rd("www", "Reaper_QoSDiag.asp")
check("QoS diagnostics: canvas colours come from the palette while the mode is on", qd.count("function cbv(") == 1 and 'c.x.strokeStyle=cbv("alert","#E10600")' in qd)

# ---------------------------------------------------------------- the switch
check("Accessibility tab right of Maintenance",
      re.search(r'data-t="maint"><span class="cdot"></span><#RADM_75#></button>\n  <button type="button" class="win" data-t="a11y"><span class="cdot"></span><#RADM_82#></button>', sysp) is not None)
check("the switch posts reaper_cbmode and the tab is in the tab list",
      'id="t_reaper_cbmode"' in sysp and "c.reaper_cbmode = chk('t_reaper_cbmode')" in sysp and "'maint', 'a11y'];" in sysp
      and "reaper_cbmode: <% nvram_get_js(\"reaper_cbmode\"); %>" in sysp)
check("Apply reloads the whole window (the chrome changes colour too)", "else if (has('reaper_cbmode')) top.location.reload();" in sysp)
# the before / after preview (owner 2026-11-26): the same samples twice, the left pane always today's colours, the right
# pane always colour-blind mode, whatever the mode is
pb = re.search(r"\.cbd\.before\{([^}]*)\}", sysp); pa = re.search(r"\.cbd\.after\{([^}]*)\}", sysp)
reset_ok = bool(pb) and all(("--cb-%s:initial" % k) in pb.group(1) for k in roles) and "--cb-alert-wash:initial" in pb.group(1)
check("preview: the standard pane resets every palette role (today's colours in either mode)", reset_ok,
      [k for k in roles if pb and ("--cb-%s:initial" % k) not in pb.group(1)])
check("preview: the colour-blind pane sets exactly the palette", bool(pa) and pa.group(1) == decl)
panes = re.findall(r'<div class="cbd (before|after)"><div class="cbt"><#(RADM_86|RADM_84)#></div>(.*?)</div>\n', sysp)
check("preview: two panes with the same samples, under the switch", 'id="r_cbdemo"' in sysp and len(panes) == 2
      and panes[0][0] == "before" and panes[1][0] == "after" and panes[0][2] == panes[1][2]
      and sysp.index('id="t_reaper_cbmode"') < sysp.index('id="r_cbdemo"'))
missing = []
for lang in ("BR CN CZ DA DE EN ES FI FR HU IT JP KR MS NL NO PL RO RU SL SV TH TR TW UK".split()):
    d = rd("www", lang + ".dict")
    missing += ["%s:%s" % (lang, k) for k in ("RADM_82", "RADM_83", "RADM_84", "RADM_85", "RADM_86") if ("\n%s=" % k) not in d]
check("the five new texts are in all 25 language packs", not missing, missing)
dfl = rd("shared", "defaults.c")
check("nvram reaper_cbmode defaults to off", re.search(r'\{ "reaper_cbmode", "0",', dfl) is not None)
web = rd("httpd", "web.c")
check("the settings backup carries it (rcfg_flags)", re.search(r'\{ "misc",\s+"reaper_cbmode", 2 \}', web) is not None)
inj = rd("httpd", "reaper_inject.c")
check("httpd adds the palette + class to a stock page while the mode is on, signed-in answers only",
      re.search(r'if \(reaper_req_authed && nvram_match\("reaper_cbmode", "1"\)\)[^\n]*\n\s*RP_PUT\(conn_fp, RP_CB\);', inj) is not None
      and 'href=\\"/reaper/reaper_cb.css\\"' in inj)
check("the injected link floor and the banner switch too",
      "text-decoration-color:var(--cb-acc,#E10600)" in inj and "background:var(--cb-warn,#E0A93B)" in inj)

print("\n%d failing" % len(fails))
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
