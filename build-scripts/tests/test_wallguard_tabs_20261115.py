#!/usr/bin/env python3
"""Wallguard page in five tabs, the Devices tab and devcounts (owner-chosen concept B, 2026-11-15).

WHY. The owner's pain: Paramount+ on the Fire TV broke and the Wallguard page, one long wall of cards, showed nothing
useful where he looked. Of three mockups (docs/mockups/wallguard-2026-11-15) he picked B: the Firewall page's tab row
(Overview / Lists / Rules / Devices / Activity), Save at the right end of it, an amber dot on a tab with an unsaved
change, "N problems" on Lists when the last build lacked lists, help in a "?" fly-out. Overview carries Fix a device
(Unbreak), Pause (with a new 10-minute choice - the CGI always took minutes) and Why?. The Devices tab is one row per
device and guest network whose profile menu REPLACES the separate assignment table (same cfg.asg data, same save
field), with the blocked lookups of the last 15 minutes - a new router query, wallguard.sh devcounts, behind the CGI's
own gate.

WHAT IT DOES.
  - page pins: the five tabs and panels, the tab remembered in localStorage (try/catch), Save in the tab row, the dot
    and problem count, the Devices table (no assignment table left, the menu writes cfg.asg, Save's assign line
    unchanged), the devcounts request, the 10-minute pause, the help fly-out, ASCII only, no inline handlers, new
    tokens in template literals only, no centring of the frame.
  - wallguard.sh: devcounts (and ip_macs) under sh -n / busybox ash -n, no apostrophe inside their awk programs, run on
    the host with a fake ip/arp/leases: MAC records count under the MAC, "-" records under the MAC their address holds
    now, else the address; old records and bad lines left out; a bad minutes argument falls back to 15.
  - web.c: the devcounts action inside do_reaper_wallguard_cgi (after reaper_gate), digits-only minutes 1-60, only %d
    on the command line.
  - the 25 packs: RSHD_192..207 right after RSHD_191, non-empty, all packs the same line count.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile, time, json

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PAGE = os.path.join(SRC, "www", "Reaper_Wallguard.asp") if SRC else ""
SH_FILE = os.path.join(SRC, "wallguard", "wallguard.sh") if SRC else ""
if not SRC or not os.path.isfile(PAGE) or not os.path.isfile(SH_FILE):
    print("SKIP: no router tree with www/Reaper_Wallguard.asp and wallguard/wallguard.sh (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail != "" else ""))
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

pg = rd("www/Reaper_Wallguard.asp")
TABS = ["overview", "lists", "rules", "devices", "activity"]
# ============================================================ page: the tab row
w0 = pg.find('<div class="wins" id="wins"'); w1 = pg.find("\n</div>", w0)
row = pg[w0:w1]
check("five tabs in the tab row, in order, each with its amber-dot span",
      w0 > 0 and re.findall(r'data-t="([a-z]+)"', row) == TABS and row.count('<span class="cdot"></span>') == 5, row[:400])
check("each tab has its panel (.tab#tab_<name>)", all(('<div class="tab" id="tab_%s"' % t) in pg for t in TABS))
check("Save sits at the right end of the tab row (the only Save button)",
      '<span class="savebar"><button class="btn primary" data-act="save"><#RWDN_28#></button></span>' in row
      and re.sub(r"<script>.*?</script>", "", pg, flags=re.S).count('data-act="save"') == 1 and ".wins .savebar{margin-left:auto;" in pg)
check("the tab switch: the Firewall page's classes, the last tab remembered per browser with try/catch",
      "var TABS = ['overview', 'lists', 'rules', 'devices', 'activity']" in pg
      and "try{ localStorage.setItem('reaper_wg_tab', t); }catch(e){}" in pg
      and "try{ t0 = localStorage.getItem('reaper_wg_tab') || ''; }catch(e){}" in pg
      and "$('tab_' + x).classList.toggle('on', x === t);" in pg)
check("a tab with an unsaved change gets the dot (the save snapshot against the loaded one, per tab)",
      "w.classList.toggle('dirty', !!on[w.getAttribute('data-t')]);" in pg and "function shArm(){ shBase = cfg ? shSnap() : null; shDots(); }" in pg
      and "shParseConfig(j); shPaint(); ReaperPending.arm(); shArm();" in pg
      and all(("%s: '%s'" % (k, v)) in pg for k, v in (("assign", "devices"), ("profiles", "devices"), ("lists", "lists"), ("rewrite", "rules"))))
check("the Lists tab says how many lists the build status lacks (RSHD_196 / 197)",
      '<span class="wcnt" id="listprob"></span>' in row and "`<#RSHD_196#>`" in pg and "`<#RSHD_197#>`.replace('%1', np)" in pg)
check("the build warning heads the Overview too, with a jump to Lists",
      'id="buildban"' in pg and "$('buildbantext').textContent = t;" in pg and 'data-act="golists"' in pg and "golists: function(){ shTab('lists'); }" in pg)
# ============================================================ page: where things moved
def panel(t):
    a = pg.find('<div class="tab" id="tab_%s"' % t); b = pg.find('<!-- =====', a + 10)
    return pg[a:b if b > 0 else pg.find("<!-- reaper 2026-11-15 (concept B): the help fly-out")]
P = {t: panel(t) for t in TABS}
check("Overview: Fix a device (Unbreak), Pause, Why?, the counters and the banners",
      all(x in P["overview"] for x in ('id="ubdev"', 'id="ubbody"', 'id="ptarget"', 'id="pmins"', 'id="pauses"', 'id="whyname"', 'id="s_q"', 'id="banner"', 'id="bypass"', "<#RSHD_198#>")))
check("Lists: the lists table, your own sources, update, storage line, build warning, blocked answer",
      all(x in P["lists"] for x in ('id="listbody"', 'id="srcform"', 'data-act="update"', 'id="storeline"', 'id="buildwarn"', 'id="mode"')))
check("Rules: my rules, advanced rules, rewrites, the services / schedule / safe-search editor",
      all(x in P["rules"] for x in ('id="block"', 'id="allow"', 'id="adv"', 'id="rwbody"', 'id="svcprof"', 'id="pedit"')))
check("Devices: the device rows, then the profile grid", P["devices"].find('id="devrows"') > 0 and P["devices"].find('id="devrows"') < P["devices"].find('id="profbody"'))
check("Activity: live view with its device filter, most-blocked names and devices, Reset counters",
      all(x in P["activity"] for x in ('id="livebtn"', 'id="livedev"', 'id="livebody"', 'id="topbody"', 'id="devbody"', 'data-act="reset"')))
check("help: How to use and How it works in the fly-out, opened by the ? button (no inline handlers)",
      '<aside class="flyout" id="flyout"' in pg and '<ol class="steps">' in pg[pg.find('id="flyout"'):] and "<#RSHD_91#>" in pg[pg.find('id="flyout"'):]
      and "$('helpbtn').addEventListener('click', function(){ shHelp(true); });" in pg)
# ============================================================ page: the Devices table replaces the assignment table
check("the separate assignment table and its controls are gone",
      not any(x in pg for x in ('id="assignbody"', 'id="newtarget"', 'id="newpid"', 'data-act="addasg"', "function shAddAssign", "function shPaintAssign")))
check("a row's profile menu writes cfg.asg (replace the key's line; no profile of its own removes it)",
      "function shSetAsg(kind, key, pid){\n  cfg.asg = cfg.asg.filter(function(a){ return !(a.kind === kind && a.key === key); });\n  if(pid) cfg.asg.push({kind: kind, key: key, pid: pid});" in pg
      and "shSelect(opts, a ? a.pid : '', function(v){ shSetAsg(r.kind, r.key, v); shPaintDevs(); });" in pg
      and "var opts = [['', `<#RSHD_203#>`]].concat(cfg.prof.map(" in pg)
check("Save still sends the assignments as before ('mac <MAC> <id>' / 'net <idx> <id>')",
      "var asg = cfg.asg.map(function(a){ return a.kind + ' ' + a.key + ' ' + a.pid; });" in pg and "assign: asg.join('\\n')" in pg)
check("rows: devices (names through ReaperNames), assigned / paused / counted MACs, then guest networks and assigned networks",
      "add({kind: 'mac', key: d.mac, name: ReaperNames.byMac(d.mac, d.name)});" in pg and "shNetworks().forEach(function(n){ nets[n.idx] = 1; rows.push({kind: 'net'" in pg
      and "if(a.kind === 'net' && !nets[a.key])" in pg and "(cfg.pause || []).forEach(function(x){ var k = String(x.t).toLowerCase(); if(k !== 'all') add(" in pg)
check("Fix jumps to Fix a device with the device picked; Pause pauses it 10 minutes; a paused device offers Resume",
      "function shFix(key){" in pg and "u.value = key; shTab('overview'); shUnbreak();" in pg and "shPause(r.key, 10);" in pg and "shResume(r.key);" in pg
      and "encodeURIComponent(typeof arguments[0] === 'string' ? arguments[0] : $('ptarget').value)" in pg)
check("the 15-minute counts come from devcounts, asked only on the Overview and Devices tabs",
      "shReq('GET', 'action=devcounts&minutes=15', null," in pg and "if(!cfg || (shCur !== 'devices' && shCur !== 'overview')) return;" in pg)
check("a pause keeps the page's unsaved edits when nothing else in the config changed",
      "if(cfg && sig === shCfgSig){ cfg.pause = j.pause || [];" in pg)
# ============================================================ page: pause, live filter, hygiene
check("Pause offers 10 minutes (preselected) beside 5 min, 1 h and until 06:00",
      '<select id="pmins"><option value="5"><#RSHD_58#></option><option value="10" selected><#RSHD_199#></option><option value="60"><#RSHD_59#></option><option value="six"><#RSHD_60#></option></select>' in pg)
check("the live view's device filter is page-only (filters the rows it already has)",
      "rows = (f ? liveRows.filter(function(r){ return r.ip === f; }) : liveRows).slice(-150).reverse();" in pg)
markup = re.sub(r"<script>.*?</script>|<!--.*?-->", "", pg, flags=re.S)
scripts = "\n".join(re.findall(r"<script>(.*?)</script>", pg, re.S))
check("ASCII only, no inline on*= handlers, one closure", all(ord(c) < 128 for c in pg) and not re.search(r"\son[a-z]+\s*=", markup)
      and pg.count("<script>\n(function(){") == 1)
newk = ["RSHD_%d" % k for k in range(192, 208)]
check("every new key is used; in the script only inside template literals",
      all(("<#%s#>" % k) in pg for k in newk)
      and all(scripts.count("<#%s#>" % k) == scripts.count("`<#%s#>`" % k) for k in newk), [k for k in newk if ("<#%s#>" % k) not in pg])
check("the page fills the frame from the left (no margin:0 auto)", "margin:0 auto" not in pg and "margin: 0 auto" not in pg)

# ============================================================ wallguard.sh
sh = rd("wallguard/wallguard.sh")
r = run(["sh", "-n", SH_FILE]); check("wallguard.sh passes sh -n", r.returncode == 0, r.stderr)
BB = shutil.which("busybox")
if BB and run([BB, "ash", "-c", "true"]).returncode != 0: BB = None
if BB:
    r = run([BB, "ash", "-n", SH_FILE]); check("wallguard.sh passes busybox ash -n", r.returncode == 0, r.stderr)
for fn in ("devcounts", "ip_macs"):
    m = re.search(r"^%s\(\) \{\n(.*?)^\}\n" % fn, sh, re.S | re.M)
    body = m.group(1) if m else ""
    progs = re.findall(r"awk [^']*'(.*?)'", body, re.S)
    check("%s(): present, its awk programs carry no apostrophe" % fn, m is not None and progs and all("'" not in p for p in progs))
check("wallguard.sh: the devcounts action, minutes digits-only 1-60 (else 15), folded first",
      '  devcounts) devcounts "$2" ;;\n' in sh and "case \"$mins\" in ''|*[!0-9]*|???*) mins=15 ;; esac" in sh
      and '[ "$mins" -ge 1 ] && [ "$mins" -le 60 ] || mins=15' in sh and "devcounts <min>" in sh)

if not shutil.which("flock"):
    print("SKIP (runtime part): needs flock")
else:
    work = tempfile.mkdtemp(prefix="wgdc_")
    try:
        b, d, j = (os.path.join(work, x) for x in ("bin", "d", "j"))
        for x in (b, d, j): os.makedirs(x)
        now = int(time.time())
        with open(os.path.join(b, "ip"), "w") as f:
            f.write('#!/bin/sh\ncase "$*" in\n  "neigh show") echo "192.168.50.31 dev br0 lladdr 02:00:5E:00:53:31 REACHABLE" ;;\n'
                    '  "-6 neigh show") echo "fe80::1 dev br0 lladdr 02:00:5e:00:53:31 STALE" ;;\nesac\n')
        with open(os.path.join(b, "arp"), "w") as f:
            f.write('#!/bin/sh\necho "? (192.168.50.44) at 02:00:5e:00:53:07 [ether] on br0"\n')
        for x in ("ip", "arp"): os.chmod(os.path.join(b, x), 0o755)
        leases = os.path.join(work, "leases")
        with open(leases, "w") as f:
            f.write("%d 02:00:5e:00:53:9e 192.168.50.70 ring *\n%d 1234 fd00::5 host 00:01\n" % (now + 3000, now + 3000))
        with open(os.path.join(d, "recent"), "w") as f:
            f.write("\n".join([
                "%d 192.168.50.31 2 q 02:00:5e:00:53:31 ads.example.com" % (now - 60),
                "%d 192.168.50.31 2 q - ads.example.com" % (now - 50),
                "%d 192.168.50.31 2 c - saa.paramountplus.com saa.cbsi.com.ssl.sc.omtrdc.net" % (now - 40),
                "%d 192.168.50.44 4 q - x.tiktok.com" % (now - 30),
                "%d 192.168.50.70 4 q - y.example.net" % (now - 20),
                "%d 192.168.50.99 4 q - z.example.net" % (now - 10),
                "%d 192.168.50.99 4 q - old.example.net" % (now - 5000),
                "garbage line",
                "%d 192.168.50.31 2 q 02:00:5e:00:53:31 bad$name" % (now - 5),
                "%d 192.168.50.31 2 q not-a-mac ads.example.com" % (now - 5)]) + "\n")
        env = dict(os.environ, PATH=b + ":" + os.environ.get("PATH", ""), WALLGUARD_DIR=d, WALLGUARD_JFFS=j, WALLGUARD_LEASES=leases)
        def dc(arg):
            r = run(["sh", SH_FILE, "devcounts", arg], env=env, cwd=work)
            try: return json.loads(r.stdout)
            except Exception: return {"raw": r.stdout, "err": r.stderr}
        o = dc("15")
        got = {x["dev"]: x["n"] for x in o.get("devs", [])}
        check("devcounts: the JSON shape {ok, mins, devs:[{dev, n, t}]}", o.get("ok") == 1 and o.get("mins") == 15
              and all(set(x) == {"dev", "n", "t"} and isinstance(x["t"], int) for x in o.get("devs", [])), o)
        check("devcounts: MAC records under the MAC; '-' records under the MAC their address holds now (neigh, arp, leases); "
              "unknown addresses under the address; old, malformed and bad-name records left out",
              got == {"02:00:5e:00:53:31": 3, "02:00:5e:00:53:07": 1, "02:00:5e:00:53:9e": 1, "192.168.50.99": 1}, got)
        o2 = dc("1;id")
        check("devcounts: a bad minutes argument falls back to 15", o2.get("mins") == 15, o2)
        o3 = dc("99")
        check("devcounts: minutes above 60 fall back to 15", o3.get("mins") == 15, o3)
        check("devcounts: its temporary file is removed", not [x for x in os.listdir(d) if x.startswith("devcounts.")], os.listdir(d))
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ============================================================ web.c
web = rd("httpd/web.c")
a = web.find("do_reaper_wallguard_cgi(char *url, FILE *stream)\n{")
e = web.find("\n}\n", a)
cgi = web[a:e]
i = cgi.find('if (!strcmp(action, "devcounts")) {')
blk = cgi[i:cgi.find("\n\t}\n", i)]
check("CGI: the devcounts action lives in do_reaper_wallguard_cgi, after its reaper_gate() check",
      a > 0 and i > cgi.find("int why = reaper_gate(), i;") > 0 and cgi.find("if (why != RGATE_OK) {") < i)
check("CGI: minutes are digits only, 1-60 (absent = 15); anything else is refused",
      'strspn(mins, "0123456789") != strlen(mins)' in blk and "(m = atoi(mins)) < 1 || m > 60" in blk and "strlen(mins) > 2" in blk
      and 'websWrite(stream, "{\\"ok\\":0,\\"ek\\":\\"RSHD_E2\\"}");' in blk and "int m = 15;" in blk)
check("CGI: only the checked number reaches the command line (the script by its fixed path, %d)",
      'snprintf(cmd, sizeof(cmd), "sh " SH_SCRIPT " devcounts %d 2>/dev/null", m);' in blk and "%s" not in blk.split("snprintf", 1)[1].split(";", 1)[0]
      and 'sh_popen(stream, cmd, "{\\"ok\\":1,\\"devs\\":[]}");' in blk)

# ============================================================ the 25 packs
packs = "BR CN CZ DA DE EN ES FI FR HU IT JP KR MS NL NO PL RO RU SL SV TH TR TW UK".split()
lens, bad = set(), []
for pk in packs:
    p = os.path.join(SRC, "www", pk + ".dict")
    if not os.path.isfile(p): bad.append(pk + " missing"); continue
    lines = open(p, encoding="utf-8").read().split("\n")
    lens.add(len(lines))
    i = [n for n, l in enumerate(lines) if l.startswith("RSHD_191=")]
    ok = len(i) == 1 and all(lines[i[0] + 1 + n].startswith("RSHD_%d=" % k) and len(lines[i[0] + 1 + n]) > len("RSHD_%d=" % k)
                             for n, k in enumerate(range(192, 208)))
    ok = ok and "%1" in lines[i[0] + 6]
    if not ok: bad.append(pk)
check("packs: RSHD_192..207 right after RSHD_191 in all 25, non-empty, RSHD_197 keeps %%1, same line count (%s)" % sorted(lens),
      not bad and len(lens) == 1, bad)

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
