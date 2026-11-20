#!/usr/bin/env python3
"""Two small UI fixes (field reports passed on 2026-11-19): "2.4 GHz" on the AiMesh node panel, and the iPhone
Administration tabs that shrank to one tiny line.

WHY (1). AiMesh > select a node, MLO backhaul: the stock page builds each band row's title from the mlo_status key
(`rssi2g` -> "2 GHz") while every other page says "2.4 GHz". The Devices and Wallguard (Reaper_GK) pages join the
device feed's band with " GHz" too; their feed (httpd reaper_dev.cgi + gkd seen.tsv) already sends "2.4", so those
pages need no mapping - pinned here at the producers so a later "2" would be caught.

WHY (2). On an iPhone, a second after Administration > System opened, the shell's tab bar shrank to one line of
tiny cut labels; other pages and wider screens were fine. When a framed page is wider than the shell's stage the
shell widens its frame (meant for wide stock tables); the stage then overflows, and the shell's fit.js "shared the
overflow" out among the only labels in that clip box - the tab bar - and cut them further on every pass (once a
second, from the rail clock). No label can fix a frame's overflow. Measured in a WebKit mock of the stage: 30 px of
frame overflow cut the nine Administration tabs, 150 px cut them to 45-99 px on two lines; with the bar marked
data-rfit-keep they keep their size. The System page's own overflow (a long remote-access address, 341 px in a
319 px row at 375 px; 369 px of document at 320 px) is broken at any character now, and its access list keeps the
kit's phone scroll box (the page's 760 px cap came after the kit rule and replaced its max-width).

WHAT IT CHECKS. (1) the AiMesh title builder (REAPER-24GHZ) - a node run of the line cut out of the page:
rssi2g -> "2.4 GHz", rssi5g -> "5 GHz", rssi5gl -> "5 GHz-1", rssi6g -> "6 GHz" ...; the producers of the Devices /
Wallguard band values send "2.4"; (2) the shell tab bar carries data-rfit-keep (REAPER-TABBAR-KEEP) and a label is
capped by its own CSS; fit.js still honours data-rfit-keep in fitContainers; the System page CSS block
(REAPER-PHONEFIT) and its rules; viewport metas. Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import json, os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_System.asp")):
    print("SKIP: no router source tree with www/Reaper_System.asp (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

# ================================================================ (1) 2.4 GHz
aim = rd("www", "aimesh", "aimesh_topology.html")
STOCK = 'const wl_band = item.replace("rssi", "").replace("l", "-1").replace("h", "-2").toUpperCase().replace("G", " GHz");'
check("aimesh: the stock title builder is gone", STOCK not in aim)
check("aimesh: one REAPER-24GHZ title builder (the other wl_band, from a pap key, is a lookup key, not a label)",
      aim.count("REAPER-24GHZ") == 1 and aim.count('const wl_band = item.replace("rssi", "")') == 1)
m = re.search(r'\n(\t+)if\(item\.substring\(0,4\) == "rssi"\)\{\n\t+const wl_band = ([^;\n]+);[^\n]*REAPER-24GHZ[^\n]*\n'
              r'\t+if\(value == ""\) value = `--`;\n\t+result\.rssi_info\.push\(\{"title":wl_band, "rssi":value\}\);', aim)
check("aimesh: the builder sits in the mlo_status rssi loop and still feeds the row title", m is not None)
expr = m.group(2) if m else ""
check("aimesh: 2.4 only for a key that starts with the 2 GHz band (anchored), the rest of the stock chain kept",
      '.toUpperCase().replace(/^2G/, "2.4G").replace("G", " GHz")' in expr
      and expr.startswith('item.replace("rssi", "").replace("l", "-1").replace("h", "-2")'), expr)
CASES = {"rssi2g": "2.4 GHz", "rssi5g": "5 GHz", "rssi5gl": "5 GHz-1", "rssi5gh": "5 GHz-2", "rssi6g": "6 GHz",
         "rssi6gl": "6 GHz-1", "rssi6gh": "6 GHz-2", "rssi2gl": "2.4 GHz-1"}
node = shutil.which("node")
if node and expr:
    js = "var f = function(item){ return %s; }; var c = %s, o = {}; for (var k in c) o[k] = f(k); console.log(JSON.stringify(o));" % (
        expr, json.dumps(CASES))
    r = subprocess.run([node, "-e", js], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
    got = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("aimesh (node run of the cut-out builder): " + ", ".join("%s -> %s" % kv for kv in CASES.items()),
          got == CASES, (got, r.stderr[-300:]))
else:
    print("skip node run of the aimesh builder (no node)")

# the Devices / Wallguard feed: band values come out as "2.4", never "2"
web, gkd = rd("httpd", "web.c"), rd("gkd", "gkd.c")
check("gkd: the band a MAC is seen on is \"2.4\" / \"5\" / \"6\" (unit_band)",
      re.search(r'static const char \*unit_band\(int unit\)\n\{[^}]*case 2: return "2\.4";\n\tcase 1: return "5";\n\tcase 4: return "6";', gkd) is not None)
check("reaper_dev.cgi: radio bands map nband 2 -> \"2.4\" (the scan and the port table)",
      web.count('(nb == 2) ? "2.4" : (nb == 1) ? "5" : (nb == 4) ? "6" : ""') == 2)
check("reaper_dev.cgi: AiMesh live-list bands map '2' -> \"2.4\" (both readers)", web.count("case '2': bl = \"2.4\";") == 2)
check("reaper_dev.cgi: the MLO bands list writes \"2.4\" (bands = 2.4+5+6)", 'if (d->bandmask & 1) strlcat(bands, "2.4", sizeof(bands));' in web)
check("reaper_dev.cgi: a 2.4 GHz backhaul path is \"2.4\"",
      'if (path == 2)        { v[k].wifi = 1; v[k].wired = 0; snprintf(v[k].band, sizeof(v[k].band), "2.4"); v[k].bandmask |= 1; }' in web)
dev, gk = rd("www", "Reaper_Devices.asp"), rd("www", "Reaper_GK.asp")
check("Devices: the feed's band / bands are shown as sent, + ' GHz'",
      "('MLO &middot; ' + esc(d.bands) + ' GHz')" in dev and ": d.band ? (esc(d.band) + ' GHz')" in dev)
check("Wallguard: the feed's band / bands are shown as sent, + ' GHz'",
      "if(c.mlo && c.bands) return 'MLO &middot; ' + gkEsc(c.bands) + ' GHz';" in gk
      and "if(c.band) return `<#RGK_50#> &middot; ` + gkEsc(c.band) + ' GHz';" in gk)
mlo = rd("www", "Reaper_MLO.asp")
check("MLO page: maps its own 2g1 key to 2.4 GHz", "if (s === '2g1') return '2.4 GHz';" in mlo)

# ================================================================ (2) the shell tab bar + the System page
sh, fit = rd("www", "reaper_shell.asp"), rd("www", "reaper", "fit.js")
check("shell: one tab bar, marked data-rfit-keep (REAPER-TABBAR-KEEP)",
      sh.count('<div id="tabbar" data-rfit-keep></div>') == 1 and '<div id="tabbar"></div>' not in sh
      and sh.count("<!-- REAPER-TABBAR-KEEP") == 1)
i_c = sh.find("<!-- REAPER-TABBAR-KEEP"); j_c = sh.find("-->", i_c)
check("shell: the marker comment is a well-formed HTML comment (no -- inside)", 0 <= i_c < j_c and "--" not in sh[i_c + 4:j_c])
check("shell: the bar is still inside the stage, right before the frame",
      re.search(r'<main class="stage">\n\s*<!-- REAPER-TABBAR-KEEP[^>]*-->\n\s*<div id="tabbar" data-rfit-keep></div>\n\s*<iframe id="page_frame"', sh) is not None)
i_base, i_cap = sh.find("#tabbar a.rtab{font-family:"), sh.find("#tabbar a.rtab{max-width:100%;overflow:hidden;text-overflow:ellipsis}")
check("shell: a tab label is capped at the bar by its own CSS, after the base rule (the cascade keeps it)",
      0 <= i_base < i_cap and sh.count("#tabbar a.rtab{max-width:100%;overflow:hidden;text-overflow:ellipsis}") == 1, (i_base, i_cap))
check("shell: viewport meta width=device-width, initial-scale=1; the frame is width:100% (no fixed width)",
      '<meta name="viewport" content="width=device-width, initial-scale=1">' in sh
      and re.search(r"#page_frame\{width:100%;", sh) is not None)
fc = fit[fit.find("function fitContainers"):]
check("fit.js: fitContainers skips anything inside [data-rfit-keep] before it looks for a clip box",
      0 <= fc.find("if (el.closest && el.closest('[data-rfit-keep]')) continue;") < fc.find("a = clipAncestor(win, el);"))

sp = rd("www", "Reaper_System.asp")
b0, b1 = sp.find("/* REAPER-PHONEFIT-BEGIN"), sp.find("/* REAPER-PHONEFIT-END */")
st0, st1 = sp.find("<style>"), sp.find("</style>")
check("System: one REAPER-PHONEFIT block, last in the page <style> (after the 760 px table cap)",
      sp.count("REAPER-PHONEFIT-BEGIN") == 1 and sp.count("REAPER-PHONEFIT-END") == 1
      and st0 < sp.find("table.classes{max-width:760px}") < b0 < b1 < st1
      and sp[b1:st1].strip() == "/* REAPER-PHONEFIT-END */", (st0, b0, b1, st1))
BLK = sp[b0:b1]
check("System: a long value (remote address, LAN link, user name) breaks anywhere and never outgrows its row",
      ".frow .fc>.fv,.frow .fc>.link{min-width:0;max-width:100%;overflow-wrap:anywhere;word-break:break-word}" in BLK)
check("System: tab buttons keep their size and wrap (flex 0 0 auto, capped at the row)",
      ".wins .win{flex:0 0 auto;max-width:100%}" in BLK and ".wins{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 16px}" in sp)
check("System: buttons never outgrow their row", ".btns .btn{max-width:100%}" in BLK)
check("System: on a phone the access list keeps the kit's scroll box width",
      re.search(r"@media \(max-width:680px\)\{\s*table\.classes\{max-width:100%\}\s*\}", BLK) is not None)
check("System: the tab strip is never a scroll / clip box (fit.js would squeeze its buttons)",
      not re.search(r"\.wins\s*\{[^}]*overflow", sp))
check("System: viewport meta width=device-width, initial-scale=1",
      '<meta name="viewport" content="width=device-width, initial-scale=1">' in sp)
check("changed pages stay ASCII (System, shell, the AiMesh builder line)",
      all(ord(c) < 128 for c in sp + sh + expr + (m.group(0) if m else "")))

print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
