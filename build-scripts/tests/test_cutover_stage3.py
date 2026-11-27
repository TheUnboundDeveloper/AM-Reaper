#!/usr/bin/env python3
"""Native-UI cutover, stage 3 (2026-11-25): the Network page on the kit.

  Reaper_Network.asp  replaces SDN.asp + SDN/sdn.html + SDN/sdn.js (the Guest Network Pro editor). The owner's rule: the
                      stock behaviour and function, in a Reaper design and implementation. Same backends: nvram read
                      through appGet hooks, every save one POST /applyapp.cgi (JSON, with the page token) carrying the
                      whole lists the stock page sends (sdn_rl, vlan_rl, subnet_rl, radius_list, sdn_access_rl and the
                      apgN_ / apmN_ / cpN_ keys) and the stock service list; the sign-in page look goes to
                      /splash_page_SDN.cgi. No stock script is loaded: no jQuery, state.js, httpApi.js or sdn.js.
  two firmware lines  the stock page differs between the 102.10 and 102.8 lines (kill switch, VPN tab on a main-subnet
                      network, MLO band choices, the dual-5 GHz choice, the limiter question). The page follows the
                      line it runs on (nvram buildno, EV.build -> env.old).
  REAPER-CUT4         the menu tab, reaper_native[], the old guest / portal addresses and the links from the MLO,
                      RADIUS, Smart Connect pages and the dashboard. The stock page still ships and still opens by its
                      own address (no reaper_pagemap[] row for it): the reference until the owner's router check.
How it was proven: the maintainer's comparison rig runs the UNMODIFIED stock page (framed, as on a router) and the kit
page against the same scripted router states and compares what each parses, shows, refuses and sends (16 suites on each
line, about 4,300 comparisons a line, 25 language packs rendered). That rig needs a browser DOM and the stock page, so
it is not run here. This suite pins what the proof rests on:
  - the stock script the page was proven against, by hash: a firmware merge that changes it fails here, and the rig has
    to be run again before the hash is updated;
  - a replay (needs node; skipped without it): the page's rule modules, cut out of the page in the tree, answer a
    recorded set of questions exactly as they did when they matched the stock page (cutover_stage3_cases.json);
  - the source facts and the wiring.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree with httpd/reaper_inject.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
HERE = os.path.dirname(os.path.abspath(__file__))
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))
def rd(*p): return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()
def has(*p): return os.path.isfile(os.path.join(SRC, *p))

inj = rd("httpd", "reaper_inject.c"); web = rd("httpd", "web.c"); menu = rd("www", "reaper", "menu.js"); mk = rd("www", "Makefile")
pg = rd("www", "Reaper_Network.asp")
m = re.search(r"reaper_pagemap\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); tab = m.group(1) if m else ""
m = re.search(r"reaper_native\[\]\s*=\s*\{(.*?)\n\};", inj, re.S); native = m.group(1) if m else ""
EN = {}
for l in open(os.path.join(SRC, "www", "EN.dict"), encoding="utf-8", errors="replace"):
    if "=" in l: k, v = l.rstrip("\n").split("=", 1); EN[k] = v
head, js = pg.split("<script>\n(function(){", 1)
vc = os.path.join(SRC, "..", "..", "src-rt", "version.conf")
serial = ""
if os.path.isfile(vc):
    m = re.search(r"^SERIALNO=(\S+)", open(vc, encoding="utf-8", errors="replace").read(), re.M); serial = m.group(1) if m else ""
m = re.match(r"(\d+)\.(\d+)", serial)
OLD_LINE = bool(m) and int(m.group(2)) < 10        # the page's own rule (EV.build), from the same number the router reports

# ---------------------------------------------------------------- the page is a kit page
check("a Reaper-native kit page (meta, rp.css, rp.js, reaper_util.js; no other script file)",
      '<meta name="reaper-native" content="1">' in pg and 'href="/reaper/rp.css"' in pg
      and sorted(re.findall(r'<script src="([^"]+)"', pg)) == ["/reaper/rp.js", "/reaper_util.js"], re.findall(r'<script src="([^"]+)"', pg))
check("plain ASCII, LF line ends", all(ord(c) < 128 for c in pg) and "\r" not in pg)
check("one script, one strict closure", pg.count("<script>") - pg.count("<script>/*REAPER-CBMODE*/") == 1 and "'use strict';" in js[:40] and js.rstrip().endswith("</html>"))
toks = sorted(set(re.findall(r"<#([A-Za-z0-9_-]+)#>", pg)))
miss = [t for t in toks if t not in EN]
# httpd writes nothing for a key the dictionary lacks: one text exists on the 102.10 line only, and the page copes with it empty
check("every dictionary token exists (%d tokens; the limiter question may be absent on the older line)" % len(toks),
      set(miss) <= {"Gear_Accelerator_confirm"} and (not miss or OLD_LINE or not serial), miss)
check("...and the page asks the limiter question only when its text is there",
      "var t = `<#Gear_Accelerator_confirm#>`;" in js and pg.count("<#Gear_Accelerator_confirm#>") == 1)
out = [l.strip()[:90] for l in js.split("\n") if "<#" in re.sub(r"`[^`]*`", "", l)]
check("script: a dictionary token only inside a template literal (an apostrophe in a translation cannot end a string)", not out, out[:3])
check("script: no ${ in a template literal, no token text with a backtick", "${" not in js and not [t for t in toks if t in EN and ("`" in EN[t] or "${" in EN[t])])
check("names and router text go in as text: innerHTML only inside plain(), no eval, no document.write, no inline handler",
      js.count("innerHTML") == 1 and "d.innerHTML = String(s)" in js and "eval(" not in pg and "document.write" not in pg and not re.search(r'\son[a-z]+="', head))
ids = re.findall(r'id="([A-Za-z0-9_]+)"', head)
check("markup ids are unique", len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1][:5])
check("dialogs carry the class the shell anchors to the visible part of the frame", "el('div', 'ovl adlg')" in js)
parts = re.findall(r"/\* ==== part ([A-Za-z0-9_.]+) ==== \*/\n", pg)
check("the page keeps its part markers (the comparison rig splits an installed page back into its parts with them)",
      len(parts) == 23 and parts[0] == "n1_model.js" and parts[-1] == "q9_end.js" and len(set(parts)) == 23, parts)

# ---------------------------------------------------------------- the stock page it was proven against
STOCK = {"88e422bf2e5d318a4c1fc9529929f96833f2d6fa2dd7e80472f75dd382fd9476": "the 102.10 line",
         "70e282b77a527e1c6065439a6f4a8a6590d055315c1eaa7274c66504d663e0c7": "the 102.8 line"}
sj = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js")
if os.path.isfile(sj):
    h = hashlib.sha256(open(sj, "rb").read()).hexdigest()
    check("the stock script is the one the kit page was compared with (%s). If this fails after a firmware merge or an edit of "
          "sdn.js: run the comparison rig on both lines, port what changed, then update the hash here" % STOCK.get(h, "UNKNOWN version"),
          h in STOCK and (not serial or (STOCK[h] == "the 102.8 line") == OLD_LINE), h)
else:
    print("note: the stock script is gone (fine after the cutover's last stage); the replay below still holds the answers")
check("the line is told from the number the router reports: buildno minor below 10 = the older line",
      "n = /^(\\d+)\\.(\\d+)/.exec(g(nv, 'buildno')); e.old = !!n && parseInt(n[2], 10) < 10;" in js and "'buildno'" in js)

# ---------------------------------------------------------------- replay of the recorded answers
node = shutil.which("node"); cases = os.path.join(HERE, "cutover_stage3_cases.json")
if not node:
    print("note: node not found - the replay of the rule modules is skipped")
elif not os.path.isfile(cases):
    check("the recorded answers file is beside this test", False, cases)
else:
    C = json.load(open(cases, encoding="utf-8"))
    seg = re.split(r"/\* ==== part ([A-Za-z0-9_.]+) ==== \*/\n", pg)
    mods = "\n".join(seg[i + 1] for i in range(1, len(seg), 2) if re.match(r"n\d+b?_[a-z]+\.js$", seg[i]))
    check("the rule modules hold no server tag (they are plain JavaScript)", "<%" not in mods and mods.count("var ") > 50)
    prog = ("var D = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));\n"
            "var out = (function(D){\n" + mods + "\n" + C["driver"] + "\n})(D);\nprocess.stdout.write(JSON.stringify(out));\n")
    td = tempfile.mkdtemp(prefix="rcut3_")
    try:
        pj = os.path.join(td, "replay.js"); open(pj, "w", encoding="utf-8").write(prog)
        for line, key, buildno in (("the 102.10 line", "dev", "102.10"), ("the 102.8 line", "old", "102.8")):
            st = json.loads(json.dumps(C["state"])); st["nv"]["buildno"] = buildno
            ps = os.path.join(td, "state_%s.json" % key); json.dump(st, open(ps, "w", encoding="utf-8"))
            r = subprocess.run([node, pj, ps], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
            got = {}
            try: got = json.loads(r.stdout)
            except Exception: pass
            check("replay runs on %s" % line, r.returncode == 0 and bool(got), (r.stderr or r.stdout)[-400:])
            want = C["want"][key]
            for name in want:
                check("replay, %s: %s" % (line, name), json.dumps(got.get(name), sort_keys=True) == json.dumps(want[name], sort_keys=True),
                      "got %s" % json.dumps(got.get(name), sort_keys=True)[:300])
    finally:
        shutil.rmtree(td, ignore_errors=True)

# ---------------------------------------------------------------- reads and writes
check("the page token comes from the server tag that quotes for script", 'var HTTPID = <% nvram_get_js("http_id"); %>;' in js)
check("hooks are asked at most 30 a request and joined with %3B (httpd ends a GET parameter at a semicolon)",
      "var part = list.slice(i, i + 30);" in js and "getJSON('/appGet.cgi?hook=' + part.join('%3B')" in js)
check("one joined read of the live state",
      "hooks(['get_cfg_clientlist()', 'get_clientlist()', 'apg_wifi_sched_on()', 'apm_wifi_sched_on()', 'get_apg_wifi7_onoff()', 'utctimestamp()', 'reaper_sdn_defer()']" in js)
for hook in ("get_cfg_clientlist", "get_clientlist", "apg_wifi_sched_on", "apm_wifi_sched_on", "get_apg_wifi7_onoff", "utctimestamp", "reaper_sdn_defer",
             "reaper_devnames", "get_customized_attribute", "get_ui_support", "get_operation_mode", "get_default_reboot_time", "nvram_default_get",
             "nvram_get_js", "nvram_char_to_ascii"):
    check("httpd still has the hook %s" % hook, re.search(r'\{\s*"%s"' % hook, web) is not None)
check("requests complete exactly once (load, error, timeout and abort share one guard)",
      "function end(ok){ if (fired) return; fired = true;" in js and "x.onerror = x.ontimeout = x.onabort = function(){ end(false); };" in js)
check("every save goes through one function: POST /applyapp.cgi", js.count("'/applyapp.cgi'") == 1 and "function apply(o, done){" in js)
check("httpd still serves applyapp.cgi and the sign-in page upload", '"applyapp.cgi' in web and '"splash_page_SDN.cgi*"' in web
      and "x.open('POST', '/splash_page_SDN.cgi', true);" in js)
check("Hold Wi-Fi restarts until Apply: a save with a service list is marked while the switch is on, and a held save does not wait",
      "if (LIVE.defer && LIVE.defer.on && !r.now && typeof r.post.rc_service === 'string' && r.post.rc_service !== '') r.post.reaper_defer = '1';" in js
      and "var held = !!(j && j.reaper_deferred == '1');" in js and '"reaper_defer"' in web)
check("a save that failed does not wait and puts the control back", "if (j === null){ busy = false; q('applying').className = 'applying'; if (r.fail) r.fail(); return; }" in js)
check("after a save that rebuilt the LAN the page starts again; otherwise everything is read again",
      "if (r.disconnect && !held){ location.href = location.pathname; return; }" in js and "load(function(){ q('applying').className = 'applying'; if (after) after(); });" in js)
check("no stock script and no stock page is loaded (the stock app's data files are the only stock paths)",
      sorted(set(re.findall(r"'(/(?:SDN|ajax|js|require)/[^']+)'", js))) == ["/SDN/Captive_Portal/FreeWiFi_template.json", "/SDN/Captive_Portal/MessageBoard_template.json",
                                                                          "/ajax/DNS_List.json", "/ajax/freewifi_tos.json"],
      sorted(set(re.findall(r"'(/(?:SDN|ajax|js|require)/[^']+)'", js))))
for f in (("www", "sysdep", "FUNCTION", "SDN", "SDN", "Captive_Portal", "FreeWiFi_template.json"), ("www", "sysdep", "FUNCTION", "SDN", "SDN", "Captive_Portal", "MessageBoard_template.json"),
          ("www", "sysdep", "FUNCTION", "SDN", "ajax", "freewifi_tos.json"), ("www", "ajax", "DNS_List.json")):
    check("data file the page reads is in the source: %s (the last cutover stage must keep it)" % "/".join(f[1:]), has(*f))
pd = None
try: pd = json.loads(rd("www", "reaper", "network_portal.json"))
except Exception as e: pd = str(e)
check("the page's own portal defaults file: three texts (two pictures as data: addresses, the terms), plain ASCII",
      isinstance(pd, dict) and sorted(pd) == ["fwf", "mb", "tos"] and str(pd["fwf"]).startswith("data:image/") and str(pd["mb"]).startswith("data:image/")
      and len(str(pd["tos"])) > 200 and all(b < 128 for b in open(os.path.join(SRC, "www", "reaper", "network_portal.json"), "rb").read()),
      sorted(pd) if isinstance(pd, dict) else pd)

# ---------------------------------------------------------------- hand-offs from and to other pages
check("a wizard asked for from outside: only a kind this installation offers, under the same limit as the Add button",
      "function wizardAsked(kind){" in js and "if (kindsOffered().indexOf(kind) < 0) return;" in js)
check("the MLO page's Add a Network flag: read once, cleared before use, only the MLO wizard (as the stock host page did)",
      "try { m = sessionStorage.getItem('reaper_sdn_wizard') || ''; sessionStorage.removeItem('reaper_sdn_wizard'); } catch (e) { m = ''; }" in js
      and "if (m === 'MLO') wizardAsked('MLO');" in js)
LINKS = ("Reaper_WiFiSetup.asp", "Reaper_VLAN.asp", "Reaper_MLO.asp", "Reaper_VPNClient.asp", "Reaper_VPNServer.asp")
linked = sorted(set(re.findall(r"/reaper_shell\.asp#([A-Za-z0-9_]+\.asp)", pg)))
check("the stock page's buttons to other pages go to the Reaper pages (setup box, VLAN, MLO, VPN client, VPN server), and those ship",
      linked == sorted(LINKS) and all(has("www", p) for p in LINKS), linked)
mlo = rd("www", "Reaper_MLO.asp")
check("MLO page: Add a Network sets the flag and opens the kit page; so does a click on a network that is not a backhaul",
      "sessionStorage.setItem('reaper_sdn_wizard', 'MLO')" in mlo and mlo.count("top.location.href = '/reaper_shell.asp#Reaper_Network.asp';") == 2 and "#SDN.asp" not in mlo)
check("RADIUS and Smart Connect pages open the kit page",
      "'/reaper_shell.asp#Reaper_Network.asp'" in rd("www", "Reaper_RADIUS.asp") and "#SDN.asp" not in rd("www", "Reaper_RADIUS.asp")
      and "'/reaper_shell.asp#Reaper_Network.asp'" in rd("www", "Reaper_SmartConnect.asp") and "#SDN.asp" not in rd("www", "Reaper_SmartConnect.asp"))
dash = rd("www", "Main_ReaperDash.asp")
check("dashboard: the waiting-changes notice and the Wi-Fi encryption row open the kit page",
      'id="rsdn_wait_badge" href="/reaper_shell.asp#Reaper_Network.asp"' in dash and "enc.setAttribute('data-go', 'Reaper_Network.asp');" in dash and "#SDN.asp" not in dash)

# ---------------------------------------------------------------- wiring
check("menu: the guest menu's tab is the kit page, with the stock label rule",
      "T('Reaper_Network.asp', sup('sdn_mwl') ? `<#Network#>` : `<#Guest_Network#>`)]}," in menu and "T('SDN.asp'" not in menu)
check("httpd: the page is in reaper_native[] (the shell frames it; no stock stylesheet is injected)", '\t"Reaper_Network.asp",' in native)
old_rows = re.findall(r'\{ "([a-z_]+\.asp)", "Reaper_Network\.asp", 0 \}', tab)
check("httpd: the old guest / portal addresses go to the kit page (7 rows), none to the stock page",
      sorted(old_rows) == sorted(["captive_portal.asp", "guest_network.asp", "captive_portal_preview.asp", "captive_portal_advanced.asp",
                                  "captive_portal_advanced_preview.asp", "ajax_captive_portal.asp", "ajax_captive_portal_log.asp",
                                  "sdn.asp"]) and '"SDN.asp", 0 }' not in tab, old_rows)     # sdn.asp: REAPER-CUT8
check("REAPER-CUT8 (stage 5): the stock page no longer ships (copied in, then removed at the end of the install) and its address goes to the kit page",
      has("www", "sysdep", "FUNCTION", "SDN", "SDN.asp") and '{ "sdn.asp", "Reaper_Network.asp", 0 }' in tab
      and mk.find("cp $(TOP)/www/sysdep/FUNCTION/SDN/SDN.asp $(INSTALLDIR)/www/SDN.asp") < mk.find("\trm -f $(INSTALLDIR)/www/SDN.asp\n", mk.find("REAPER-CUT8-STOCK"))
      and '"SDN.asp"' not in inj)
check("Makefile: a build without the network editor ships neither the kit page nor its defaults file",
      re.search(r"\nelse\n\t# reaper 2026-11-25 \(cutover stage 3\) REAPER-CUT4[^\n]*\n\trm -f \$\(INSTALLDIR\)/www/Reaper_Network\.asp\n"
                r"\trm -f \$\(INSTALLDIR\)/www/reaper/network_portal\.json\n", mk) is not None)
check("Makefile: a build without the captive portal does not ship the portal defaults file",
      "ifneq ($(RTCONFIG_CAPTIVE_PORTAL), y)\n\trm -rf $(INSTALLDIR)/www/SDN/Captive_Portal\n\trm -rf $(INSTALLDIR)/www/ajax/freewifi_tos.json\n"
      "\trm -f $(INSTALLDIR)/www/reaper/network_portal.json\n" in mk)
check("rc: mtlancfg is added on every MULTILAN_CFG build (why the tab needs no build condition of its own)",
      re.search(r'#ifdef RTCONFIG_MULTILAN_CFG\n\tadd_rc_support\("mtlancfg"\);\n#endif', rd("rc", "init.c")) is not None)
pages = sorted(set(re.findall(r"T\('([A-Za-z0-9_]+\.(?:asp|htm|html))'", menu)))
left = [p for p in pages if not p.startswith(("Reaper_", "Main_ReaperDash"))]
check("menu: no stock page is listed any more - every tab is a Reaper page", left == [], left)

if fails:
    print("\n%d FAILED" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
