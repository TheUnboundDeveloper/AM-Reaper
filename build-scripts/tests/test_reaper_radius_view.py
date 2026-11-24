#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wireless > RADIUS Setting shows the main network's real server (httpd/web.c REAPER-MAINRADIUS,
www/Reaper_RADIUS.asp, 2026-11-20).

WHY THIS EXISTS. Bug review 2026-11-16 #13: once the main network is a Network-page profile (sdn_rl has a MAINFH
row) it runs on wlN.1 and its RADIUS server is the MAINFH row of radius_list. The RADIUS tab edited wlN_radius_*
of the hidden primary interface and read wlN_auth_mode_x for its "in use" line, so it said "Not in use" while the
main network was Enterprise, and a secret rotated there changed nothing. radius_list carries four secrets per row,
so a dedicated hook prints the servers, ports, the main network's mode and only whether each secret is set.

WHAT IT DOES.
  1. Compiles reaper_main_radius_fmt() and its helpers EXTRACTED FROM web.c on the host (-Wall -Wextra -Werror)
     and feeds it fixture rows whose secrets (and Wi-Fi password) are distinctive strings: none may appear in the
     output; servers / ports / set flags / modes are right; one row per MAINFH row; a secret holding '>' or '<'
     makes the whole list "bad" with no server printed; unknown mode words are dropped.
  2. The hook is registered in ej_handlers[] and never prints a key field.
  3. The page: reads sdn_rl, takes the server from the hook, never reads radius_list or posts apm* / radius_list,
     the stale "No Reaper page sets those modes" comment is gone.
  4. Runs the page script in node with stubbed DOM: migrated -> read-only panel, no inputs, a Network-page link,
     Apply hidden, no secret in the HTML; not migrated -> today's per-band editor.

Exit 0 pass, 1 fail, 77 skipped (no gcc, not Linux, or no router source tree).
"""
import json, os, re, shutil, subprocess, sys, tempfile, urllib.parse

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

FAILS = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        print("FAIL " + name + ((": " + str(detail)[:600]) if detail else ""))
        FAILS.append(name)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
if not sys.platform.startswith("linux"):
    skip("not Linux")
GCC = shutil.which("gcc") or shutil.which("cc")
if not GCC:
    skip("no host gcc")

def rd(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

web = rd("httpd/web.c")
page = rd("www/Reaper_RADIUS.asp")

# ------------------------------------------------------------ 1. the formatter, compiled
m = re.search(r"(#define RMR_FIELDS\b.*?\n)static const char \*rmr_apm_security\(", web, re.S)
if not m:
    check("REAPER-MAINRADIUS formatter found in httpd/web.c", False)
    print("%d FAILED" % len(FAILS)); sys.exit(1)
FMT = m.group(1)

SECRETS = ["K1sekritAuthOne", "K2sekritAcctOne", "K3sekritAuthTwo", "K4sekritAcctTwo", "PSKwifiPassw0rd", "Q9other"]
CASES = {
    # name: (sdn_rl, radius_list, {apm_idx: security})
    "basic": ("<0>DEFAULT>1>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0<1>MAINFH>1>0>1>2>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
              "<3>Employee>1>3>3>5>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0",
              "<1>192.168.50.10>1812>K1sekritAuthOne>10.0.0.9>1813>K2sekritAcctOne>radius2.lan>1814>K3sekritAuthTwo>fd00::9>1815>>"
              "<3>10.9.9.9>1812>Q9other>>>>>>>>>>",
              {"2": "<3>wpa2wpa3>aes>>1<13>wpa2wpa3>aes>>1<16>wpa3>aes>>1<96>wpa3>aes>>1", "5": "<3>psk2>aes>PSKwifiPassw0rd>3"}),
    "personal": ("<1>MAINFH>1>0>1>4>0", "", {"4": "<3>psk2sae>aes>PSKwifiPassw0rd>1<16>sae>aes>PSKwifiPassw0rd>1"}),
    "gt_in_key": ("<1>MAINFH>1>0>1>2>0", "<1>192.168.50.10>1812>K1sekr>itAuthOne>>>>>>>>>>", {"2": "<3>wpa2>aes>>1"}),
    "lt_in_key": ("<1>MAINFH>1>0>1>2>0", "<1>192.168.50.10>1812>K1sekr<itAuthOne>>>>>>>>>>", {"2": "<3>wpa2>aes>>1"}),
    # a last secret typed as a whole row for the main network: the cut row loses its trailing '>' (form mismatch)
    "lt_crafted": ("<4>MAINFH>1>0>1>2>0", "<2>10.2.2.2>1812>>>>>>>>>>x<4>evil.host>1812>K2sekritAcctOne>>>>>>>>>>",
                   {"2": "<3>wpa2>aes>>4"}),
    # the same index twice (a crafted row next to the real one)
    "dup_idx": ("<1>MAINFH>1>0>1>2>0", "<1>10.1.1.1>1812>K1sekritAuthOne>>>>>>>>>><1>evil.host>1812>>>>>>>>>>>",
                {"2": "<3>wpa2>aes>>1"}),
    "pw_forged_row": ("<1>MAINFH>1>0>1>2>0", "<1>10.1.1.1>1812>K1sekritAuthOne>>>>>>>>>>",
                      {"2": "<3>psk2>aes>PSKwifi<7>PSKwifiPassw0rd>x>1"}),
    "two_main": ("<1>MAINFH>1>0>1>2>0<4>MAINFH>1>0>1>6>0", "<4>10.4.4.4>1812>K1sekritAuthOne>>>>>>>>>><1>10.1.1.1>>>>>>>>>>>>",
                 {"2": "<3>wpa2>aes>>1", "6": "<16>wpa3>aes>>4"}),
    "bad_host": ("<1>MAINFH>1>0>1>2>0", "<1>a b\"c>18x12>K1sekritAuthOne>>>>>>>>>>", {"2": "<3>wpa2>aes>>1"}),
    # the owner's router, 2026-11-20 (read-only): four MAINFH rows, radius_list empty (no Enterprise network), apmN_security
    # one group per band "<band>auth>cipher>password>flag", apm1 / apm2 set, apm3 empty
    "router_1120": ("<0>DEFAULT>1>0>0>0>0<1>MAINFH>1>0>1>1>0<2>MAINFH>1>0>1>2>0<3>MAINFH>1>0>1>3>0<4>MAINFH>1>0>1>1>0<5>MAINBH>1>0>1>4>0",
                    "",
                    {"1": "<3>psk2sae>aes+gcmp256>PSKwifiPassw0rd>0<13>psk2sae>aes+gcmp256>PSKwifiPassw0rd>0<16>sae>aes+gcmp256>PSKwifiPassw0rd>0",
                     "2": "<3>psk2sae>aes+gcmp256>PSKwifiPassw0rd>0<16>sae>aes+gcmp256>PSKwifiPassw0rd>0", "3": ""}),
    "not_migrated": ("<0>DEFAULT>1>0>0>0>0", "<1>10.1.1.1>1812>K1sekritAuthOne>>>>>>>>>>", {}),
}

def cstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

body = []
for name, (sdn, rl, secs) in CASES.items():
    tbl = "".join("\t\tif (!strcmp(i, %s)) return %s;\n" % (cstr(k), cstr(v)) for k, v in secs.items())
    body.append("static const char *sec_%s(const char *i)\n{\n\t(void)i;\n%s\treturn \"\";\n}\n" % (name, tbl))
calls = "".join('\tmemset(out, \'Z\', sizeof(out)); n = reaper_main_radius_fmt(%s, %s, sec_%s, out, sizeof(out)); '
                'printf("%s\\t%%d\\t%%s\\n", n, out);\n' % (cstr(sdn), cstr(rl), name, name)
                for name, (sdn, rl, secs) in CASES.items())
DRV = ("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <ctype.h>\n" + FMT + "\n" + "\n".join(body) +
       "int main(void)\n{\n\tchar out[4096], tiny[24];\n\tint n;\n" + calls +
       '\tn = reaper_main_radius_fmt(%s, %s, sec_basic, tiny, sizeof(tiny)); printf("tiny\\t%%d\\t%%s\\n", n, tiny);\n'
       % (cstr(CASES["basic"][0]), cstr(CASES["basic"][1])) +
       "\treturn 0;\n}\n")
work = tempfile.mkdtemp(prefix="rmr_")
res = {}
try:
    c = os.path.join(work, "d.c"); open(c, "w").write(DRV)
    exe = os.path.join(work, "d")
    cc = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-fsanitize=address,undefined",
                         "-o", exe, c], capture_output=True, text=True)
    if cc.returncode != 0:   # no sanitizer runtime on this host: plain build
        cc = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", exe, c],
                            capture_output=True, text=True)
    check("reaper_main_radius_fmt (extracted from web.c) compiles (-Wall -Wextra -Werror)", cc.returncode == 0, cc.stderr[-1500:])
    if cc.returncode == 0:
        r = subprocess.run(["setarch", "x86_64", "-R", exe] if shutil.which("setarch") else [exe],
                           capture_output=True, text=True, timeout=60)
        check("the formatter runs clean (no sanitizer report)", r.returncode == 0 and "ERROR" not in r.stderr, r.stderr[-800:])
        for ln in r.stdout.splitlines():
            k, n, out = ln.split("\t", 2)
            res[k] = (int(n), out)
finally:
    shutil.rmtree(work, ignore_errors=True)

def rows(k):
    return [x.split(">") for x in res.get(k, (0, ""))[1].split("<") if x]

if res:
    allout = "\n".join(v[1] for v in res.values())
    leaked = [s for s in SECRETS if s in allout] + [s for s in ("sekrit", "PSKwifi", "itAuthOne", "evil.host") if s in allout]
    check("no secret, no Wi-Fi password and no fragment of either in any output", not leaked, leaked)
    b = rows("basic")
    check("basic: one row for the one MAINFH row (sdn idx 1, apm 2), list ok", res["basic"][0] == 1 and len(b) == 1
          and b[0][:3] == ["1", "2", "ok"], b)
    check("basic: modes from apm2_security, known words, no duplicates", b and b[0][3] == "wpa2wpa3,wpa3", b)
    check("basic: auth / acct / second auth / second acct servers, ports and set flags",
          b and b[0][4:] == ["192.168.50.10", "1812", "1", "10.0.0.9", "1813", "1", "radius2.lan", "1814", "1",
                             "fd00::9", "1815", "0"], b)
    check("basic: the Employee row (idx 3) is not shown", b and "10.9.9.9" not in res["basic"][1])
    p = rows("personal")
    check("personal main network, no radius row: modes shown, servers empty, secrets not set",
          p and p[0][2:] == ["ok", "psk2sae,sae"] + ["", "", "0"] * 4, p)
    for k in ("gt_in_key", "lt_in_key", "lt_crafted", "dup_idx"):
        g = rows(k)
        check("%s: a secret with a separator makes the list bad and prints no server" % k,
              g and g[0][2] == "bad" and all(x in ("", "0") for x in g[0][4:]), g)
    f = rows("pw_forged_row")
    check("a '<' in the Wi-Fi password cannot inject a mode word", f and f[0][3] == "psk2", f)
    t = rows("two_main")
    check("two MAINFH rows (Smart Connect off): two rows, each with its own server and mode",
          len(t) == 2 and t[0][:5] == ["1", "2", "ok", "wpa2", "10.1.1.1"] and t[1][:7] == ["4", "6", "ok", "wpa3", "10.4.4.4", "1812", "1"], t)
    h = rows("bad_host")
    check("a server / port with odd characters is printed empty", h and h[0][4] == "" and h[0][5] == "" and h[0][6] == "1", h)
    rt = rows("router_1120")
    check("router read 2026-11-20 (4 MAINFH rows, radius_list empty): 4 rows, modes per apm from field 2 only, no server, "
          "every secret not set, MAINBH ignored",
          len(rt) == 4 and [r[:4] for r in rt] == [["1", "1", "ok", "psk2sae,sae"], ["2", "2", "ok", "psk2sae,sae"],
                                                   ["3", "3", "ok", ""], ["4", "1", "ok", "psk2sae,sae"]]
          and all(r[4:] == ["", "", "0"] * 4 for r in rt), rt)
    check("not migrated (no MAINFH row): nothing printed", res["not_migrated"] == (0, ""), res["not_migrated"])
    check("a short buffer is cut, terminated, and still holds no secret", len(res["tiny"][1]) == 23 and "sekrit" not in res["tiny"][1],
          res["tiny"])

# ------------------------------------------------------------ 2. the hook
hook = re.search(r"static int ej_reaper_main_radius\(int eid, webs_t wp, int argc, char_t \*\*argv\)\n\{(.*?)\n\}\n", web, re.S)
check("ej_reaper_main_radius exists, prints the formatter's output URL-encoded",
      hook is not None and "reaper_main_radius_fmt(" in hook.group(1) and "char_to_ascii_safe(enc, out, n)" in hook.group(1))
check("registered in ej_handlers[]", '{ "reaper_main_radius", ej_reaper_main_radius},' in web)
check("the formatter never copies a key field: secrets only as set flags",
      "*v ? \"1\" : \"0\"" in FMT and "j % 3 == 0" in FMT and FMT.count("rmr_cat(out, cap, v)") == 0)

# ------------------------------------------------------------ 3. the page
script = page.split("<script>\n(function(){", 1)[-1]
check("page reads sdn_rl via nvram_char_to_ascii and the server via the hook",
      '<% nvram_char_to_ascii("","sdn_rl"); %>' in page and "<% reaper_main_radius(); %>" in page)
check("page never reads radius_list or apm* itself", not re.search(r"<%[^%]*(radius_list|apm\d*_)", page))
check("page never posts apm* / radius_list; apply stays restart_wireless",
      not re.search(r"ch\[?\.?['\"]?(apm|radius_list)", script) and "ch.rc_service = 'restart_wireless'" in page)
check("migrated: render() hands over to the read-only view first", "if (MIGRATED){ renderMain(); return; }" in page)
check("the stale comment is gone", "No Reaper page" not in page and "sets those modes today" not in page)
check("ASCII only", not re.search(r"[^\x00-\x7f]", page))

# ------------------------------------------------------------ 4. the page script in node
node = shutil.which("node")
if not node:
    print("skip node run (no node)")
else:
    sm = re.search(r"<script>\n(\(function\(\)\{.*?\}\)\(\);)\n</script>", page, re.S)
    check("page script found", sm is not None)
    def enc(s):
        return urllib.parse.quote(s, safe="")
    def js_for(sdn, hook_out):
        s = sm.group(1)
        s = s.replace('<% nvram_char_to_ascii("","sdn_rl"); %>', enc(sdn))
        s = s.replace("<% reaper_main_radius(); %>", enc(hook_out))
        s = re.sub(r'<% nvram_get_js\("wl0_nband"\); %>', '"2"', s)
        s = re.sub(r'<% nvram_get_js\("wl1_nband"\); %>', '"1"', s)
        s = re.sub(r'<% nvram_get_js\("wl_ifnames"\); %>', '"eth7 eth8"', s)
        s = re.sub(r'<% nvram_get_js\("sw_mode"\); %>', '"1"', s)
        s = re.sub(r'<% nvram_get_js\("[^"]+"\); %>', '""', s)
        s = re.sub(r"<% nvram_match\([^%]*\); %>", "", s)
        s = re.sub(r"<#(RNW_1[12])#>", r"\1 %1", s)   # the two lines that carry the mode label
        s = re.sub(r"<#([A-Za-z0-9_]+)#>", r"\1", s)
        return s
    STUB = r'''
var els = {};
function El(id){ this.id = id; this.style = {}; this.innerHTML = ''; this.textContent = ''; this.value = ''; this.type = '';
  this.classList = {add: function(){}, remove: function(){}, toggle: function(){}}; this.l = {}; }
El.prototype.addEventListener = function(e, f){ this.l[e] = f; };
El.prototype.focus = function(){};
var top = {location: {href: ''}}, location = {reload: function(){}};
var rp = {q: function(id){ return els[id] || (els[id] = new El(id)); },
  esc: function(s){ return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); },
  dec: function(s){ try { return decodeURIComponent(s); } catch (e) { return s; } },
  sub: function(t){ var a = arguments; return String(t).replace(/%(\d)/g, function(m, n){ return a[+n]; }); },
  pill: function(){}, count: function(o){ return Object.keys(o).length; }, applying: function(){},
  v: {ipv4: function(){ return true; }, ipv6: function(){ return true; }, int: function(){ return true; }}};
'''
    TAIL = r'''
var b = els.b_sdn; if (b && b.l.click) b.l.click();
console.log(JSON.stringify({html: els.bands.innerHTML, apply: els.applybtn.style.display || '', href: top.location.href}));
'''
    def run(sdn, hook_out):
        work = tempfile.mkdtemp(prefix="rmrjs_")
        try:
            jf = os.path.join(work, "p.js")
            open(jf, "w").write(STUB + js_for(sdn, hook_out) + TAIL)
            r = subprocess.run([node, jf], capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return None, r.stderr[-800:]
            return json.loads(r.stdout.strip().splitlines()[-1]), ""
        finally:
            shutil.rmtree(work, ignore_errors=True)
    if sm:
        sdn = CASES["basic"][0]
        o, err = run(sdn, res.get("basic", (0, ""))[1])
        check("migrated page script runs", o is not None, err)
        if o:
            h = o["html"]
            check("migrated: the main network's server, port and mode are shown read-only",
                  "192.168.50.10" in h and "1812" in h and "RNW_11" in h and "WPA2/WPA3-Enterprise / WPA3-Enterprise" in h, h[:400])
            check("migrated: second servers shown with their set state", "[fd00::9]:1815" in h and "10.0.0.9:1813" in h, h[:600])
            check("migrated: no input field, Apply hidden, the button opens the Network page",
                  "<input" not in h and o["apply"] == "none" and o["href"] == "/reaper_shell.asp#SDN.asp", (o["apply"], o["href"]))
            check("migrated: no secret in the HTML", not any(s in h for s in SECRETS))
        o, err = run(sdn, res.get("personal", (0, ""))[1])
        check("migrated, Personal mode: says not in use", o is not None and "RNW_12" in o["html"] and "WPA2/WPA3-Personal" in o["html"], err)
        o, err = run(sdn, res.get("gt_in_key", (0, ""))[1])
        check("migrated, bad list: the could-not-read line, no server rows", o is not None and "RNW_17" in o["html"]
              and "WLANAuthentication11a_ExAuthDBIPAddr_itemname" not in o["html"], err)
        o, err = run(CASES["router_1120"][0], res.get("router_1120", (0, ""))[1])
        check("router state 2026-11-20: ONE main-network panel (alike rows merged, the bandless one dropped), Personal = not "
              "in use, the no-server line, no server rows", o is not None and o["html"].count("<h2>RMOD_11") == 2
              and "RNW_12 WPA2/WPA3-Personal / WPA3-Personal" in o["html"] and "RNW_18" in o["html"]
              and "WLANAuthentication11a_ExAuthDBIPAddr_itemname" not in o["html"], (err, o and o["html"][:500]))
        o, err = run("<0>DEFAULT>1>0>0>0>0", "")
        check("not migrated: the per-band editor as before", o is not None and 'id="ip0"' in o["html"] and 'id="ky1"' in o["html"]
              and o["apply"] != "none", err)

# ------------------------------------------------------------ 5. strings
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if re.match(r"^[A-Z]{2}\.dict$", f))
miss = []
for f in packs:
    t = open(os.path.join(www, f), encoding="utf-8").read()
    for k in ["RNW_%d" % n for n in range(10, 19)] + ["RNT_80", "RMOD_11", "RFW_198"]:
        mm = re.search(r"^%s=(.+)$" % k, t, re.M)
        if not mm or any(x in mm.group(1) for x in ('"', "`", "\\", "${", "</")) or (k in ("RNW_11", "RNW_12") and "%1" not in mm.group(1)):
            miss.append(f + ":" + k)
check("RNW_10-18 (and the reused RNT_80 / RMOD_11 / RFW_198) in every pack, quote-safe, %1 kept", packs and not miss, miss[:8])

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
