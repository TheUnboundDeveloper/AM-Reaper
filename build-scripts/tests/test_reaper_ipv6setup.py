#!/usr/bin/env python3
"""WAN > IPv6 on the Reaper kit (Reaper-native UI, 2026-10-23): Reaper_IPv6Setup.asp replaces Advanced_IPv6_Content.asp
and Advanced_IPv61_Content.asp.

WHY. The stock page is 66 KB of jQuery/state.js driving eight connection types through hidden rows. The Reaper page
keeps the same types, the same row-by-row visibility and every stock check, and posts only the changed settings with
restart_net (plus restart_ftpd when FTP is on). The second-WAN page is not carried: rc reads ipv61_* only on
RTCONFIG_MULTIWAN_CFG / MULTIWAN_IF builds and no Reaper model builds either (ui_parity/Advanced_IPv61_Content.json).
Every nvram value reaches the page through nvram_char_to_ascii: httpd's nvram_get passes ' and \\ through, which
could end the JS string a value is written into.

WHAT IT DOES. Source checks on the page, menu.js and reaper_inject.c; `node --check` on the page script.
The per-type visibility and POST set were checked in jsdom against the owner's live values when the page was written.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
www = os.path.join(SRC, "www")
PG = os.path.join(www, "Reaper_IPv6Setup.asp")
if not os.path.exists(PG):
    print("SKIP: Reaper_IPv6Setup.asp not found"); sys.exit(0)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

t = rd(PG)
en = rd(os.path.join(www, "EN.dict"))
js = t[t.rfind("<script>"):]
check("ASCII only", not any(ord(c) > 127 for c in t))
check("on the kit (plain rp.css link, rp.js, reaper-native meta) inside the crimson frame",
      '<link rel="stylesheet" href="/reaper/rp.css">' in t and '<script src="/reaper/rp.js"></script>' in t
      and '<meta name="reaper-native" content="1">' in t and '<div class="rframe">' in t)
check("one closure, strict, no inline handlers", js.startswith("<script>\n(function(){\n'use strict';") and js.count("<script>") == 1 and "onclick=" not in t)
toks = sorted(set(re.findall(r"<#([A-Za-z0-9_]+)#>", t)))
miss = [k for k in toks if ("\n%s=" % k) not in en]
check("every dict token exists (%d)" % len(toks), not miss, miss)
check("tokens in the script only inside backticks (rule 29)", "<#" not in re.sub(r"`[^`]*`", "", js))
check("every nvram value read through nvram_char_to_ascii (no raw nvram_get into a JS string)",
      "nvram_get(" not in t and t.count("nvram_char_to_ascii(") >= 40 and ("U = rp.dec" in t or "function U(s){ try { return decodeURIComponent(s); }" in t))
check("all eight stock connection types, passthrough + FLET'S only with ipv6pt",
      all('<option value="%s">' % v in t for v in ("disabled", "dhcp6", "other", "ipv6pt", "flets", "6to4", "6in4", "6rd"))
      and "if (!sup('ipv6pt')){ ['ipv6pt', 'flets']" in t)
check("legacy static6 shown as Static", "NV.ipv6_service === 'static6' ? 'other'" in t)
check("S46 WAN types (v6plus, OCN, DS-Lite, IPv6 Option) lock the type selector like stock",
      "var S46 = {v6plus:" in t and "q('s_service').disabled = true;" in t)
check("ifdev rule: flets forces eth, a hidden selector posts ppp",
      "c.ipv6_ifdev = v === 'flets' ? 'eth' : (R.ifdev ? q('s_ifdev').value : 'ppp');" in t)
check("the _s copies only for Static and 6in4 (where rc/services.c reads them)",
      "if (v === 'other'){ c.ipv6_prefix_length_s = val('i_plen'); c.ipv6_rtr_addr_s = val('i_rtr'); }" in t
      and "if (v === '6in4'){ c.ipv6_prefix_length_s = val('i_plen'); c.ipv6_prefix_s = val('i_prefix'); }" in t)
check("stateful pool stored as prefix::hex (rc reads the last group); stock limits kept",
      "c.ipv6_dhcp_start = pp + '::' + val('i_start')" in t and "rng('i_life', 120, 604800)" in t
      and "q('s_ac').value === '1' ? 112 : 126" in t and "/^[0-9A-Fa-f]{1,4}$/" in t)
check("tunnel limits kept: MTU 0 or 1280-1480, TTL 0-255, 6rd prefix length 3 to 126-(32-ip4size)",
      "val('i_mtu') === '0' || rng('i_mtu', 1280, 1480)" in t and "rng('i_ttl', 0, 255)" in t and "var mx = 126 - (32 - parseInt(val('i_6rdip4size'), 10));" in t)
check("Apply: only changed keys, restart_net (+restart_ftpd with FTP on), 30 s like stock",
      "rp.post(document.form, changed, 'restart_net' + (FTP_ON ? ';restart_ftpd' : ''), 30);" in t)
check("live prefix from update_IPv6state.asp only while the saved type is selected (textContent, never HTML)",
      "x.open('GET', '/update_IPv6state.asp', true);" in t and "if (document.hidden || svc() !== ORIG || ORIG === 'disabled')" in t and "innerHTML" not in t)
check("never posts the second-WAN or IPv6-only names", not re.search(r'name="ipv6(1_|_unit|_only)', t))

mj = rd(os.path.join(www, "reaper", "menu.js"))
check("menu: WAN > IPv6 opens the Reaper page under the stock condition",
      "{index: 'menu_IPv6', label: 'IPv6', when: sup('ipv6') && routing, tabs: [T('Reaper_IPv6Setup.asp', 'IPv6')]}," in mj
      and "Advanced_IPv6_Content.asp" not in mj and "Advanced_IPv61_Content.asp" not in mj)
inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c"))
check("httpd: native list + both stock pages redirect to it",
      '"Reaper_IPv6Setup.asp",' in inj and '{ "advanced_ipv6_content.asp", "Reaper_IPv6Setup.asp", ' in inj
      and '{ "advanced_ipv61_content.asp", "Reaper_IPv6Setup.asp", ' in inj)

# ---------------------------------------------------------------------------------------------------------------------
# reaper 2026-11-16 (bug review A6 item 1): WAN Prefix Length with Native + prefix delegation is the DHCP-PD size hint.
# rc sends 48 to 64 and asks for no size otherwise; the page saved any text for it and the log said it was requested.
udh = rd(os.path.join(SRC, "rc", "udhcpc.c"))
check("PD branch: Native with prefix delegation accepts empty, 0 or the window; an untouched stored value is not judged",
      "function pdLenOk(s){ return s === '' || s === '0' || rp.v.int(s, PD_MIN, PD_MAX); }" in t
      and "  if (v === 'dhcp6' && q('t_pd').checked && val('i_plenwan') !== NV.ipv6_prefix_len_wan && !pdLenOk(val('i_plenwan')))\n"
          "    return eN('i_plenwan', PD_MIN, PD_MAX);\n" in t)
st0 = t.find("  if (v === 'other'){\n    if (!v6('i_ipaddr')) return e6('i_ipaddr');")
check("Static keeps its own range (3 to 128) in its own branch",
      st0 > 0 and "    if (!rng('i_plenwan', 3, 128)) return eN('i_plenwan', 3, 128);\n" in t[st0:t.find("\n  }\n", st0)] and t.count("rng('i_plenwan'") == 1)
hm = re.search(r"/\* REAPER-PD-HINT-BEGIN \*/\n(.*?)/\* REAPER-PD-HINT-END \*/", udh, re.S)
check("rc: the one size-hint helper is found", hm is not None and udh.count("/* REAPER-PD-HINT-BEGIN */") == 1)
helper = hm.group(1) if hm else ""
pw = re.search(r"\nvar PD_MIN = (\d+), PD_MAX = (\d+);\n", t)
rw = re.search(r"static int dhcp6c_pd_hint\(int len\)\n\{\n\treturn \(len >= (\d+) && len <= (\d+)\) \? len : 0;\n\}\n", helper)
check("the page window is the rc helper's window (48 to 64)", pw is not None and rw is not None and pw.groups() == rw.groups() == ("48", "64"),
      (pw and pw.groups(), rw and rw.groups()))
check("rc: both request sites use the helper (no second copy of the range)",
      udh.count('\t\ti = dhcp6c_pd_hint(nvram_get_int(ipv6_nvname("ipv6_prefix_len_wan")));\n') == 2
      and "(i < 48) || (i > 64)" not in udh and udh.count('"%d:%lx", i, iaid') == 2 and udh.index("/* REAPER-PD-HINT-END */") < udh.index("\nbound6(char *wan_ifname, int bound)\n"))
check("rc: the log line says what was really asked for (the helper's answer), or that nothing was",
      'int hint = dhcp6c_pd_hint(nvram_get_int(ipv6_nvname_by_unit("ipv6_prefix_len_wan", wan_unit)));' in udh
      and 'logmessage("dhcp6 client", "WAN Prefix Size Requested:/%d, Received:/%d", hint, size);' in udh
      and 'logmessage("dhcp6 client", "WAN Prefix Size Requested: none (provider default), Received:/%d", size);' in udh
      and udh.count("WAN Prefix Size Requested") == 2
      and not re.search(r'WAN Prefix Size Requested:/%d, Received:/%d",\s*nvram_get_int', udh))
check("hint row: RIP6_37 and the stored-value line RIP6_38 sit under the field, hidden until the page shows them",
      '<div class="fh off" id="h_plenwan"><#RIP6_37#></div><div class="fh warn off" id="h_plenwan_old"><#RIP6_38#></div></div>' in t
      and ".frow .fh.off{display:none}" in t)
check("hint shown only for Native + prefix delegation; the stored-value line only while that value is untouched and out of range",
      "  var pdm = v === 'dhcp6' && q('t_pd').checked;\n"
      "  show('h_plenwan', pdm); show('h_plenwan_old', pdm && val('i_plenwan') === NV.ipv6_prefix_len_wan && !pdLenOk(val('i_plenwan')));\n" in t
      and "on('i_plenwan', 'input', sync);" in t)
packs = sorted(f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict")
pv = {}
for p in packs:
    d = open(os.path.join(www, p), encoding="utf-8").read()
    for k in ("RIP6_37", "RIP6_38"):
        m = re.findall(r"^%s=(.*)$" % k, d, re.M)
        if len(m) == 1 and m[0].strip() and not any(c in m[0] for c in ('"', "'", "`", "${", "<", ">")): pv[(p, k)] = m[0]
check("RIP6_37 and RIP6_38 once in all %d packs" % len(packs), len(packs) == 25 and len(pv) == 50, sorted(set((p, k) for p in packs for k in ("RIP6_37", "RIP6_38")) - set(pv))[:6])
e37, e38 = pv.get(("EN.dict", "RIP6_37"), ""), pv.get(("EN.dict", "RIP6_38"), "")
check("EN wording names the window, the empty / 0 choice and the /56 note; plain ASCII",
      "48 to 64" in e37 and "Leave empty or 0" in e37 and "/56" in e37 and e38 == "The stored value is outside 48 to 64, so no size is requested."
      and all(31 < ord(c) < 127 for c in e37 + e38), (e37, e38))
check("both strings are translated in every other pack", not [p for p in packs if p != "EN.dict" and (pv.get((p, "RIP6_37")) == e37 or pv.get((p, "RIP6_38")) == e38)])

gcc = shutil.which("gcc")
if gcc and helper:
    td = tempfile.mkdtemp(prefix="pdhint_")
    try:
        open(os.path.join(td, "t.c"), "w").write("#include <stdio.h>\n" + helper + "int main(void){ int v[] = {-1, 0, 3, 47, 48, 56, 60, 64, 65, 127, 128, 200}, i;\n"
            " for (i = 0; i < 12; i++)\n  printf(\"%d \", dhcp6c_pd_hint(v[i]));\n printf(\"\\n\");\n return 0; }\n")
        r = subprocess.run([gcc, "-Wall", "-Werror", "-o", os.path.join(td, "t"), os.path.join(td, "t.c")], capture_output=True, text=True)
        check("rc helper compiles on the host without a warning", r.returncode == 0, r.stderr[-400:])
        if r.returncode == 0:
            out = subprocess.run([os.path.join(td, "t")], capture_output=True, text=True).stdout.split()
            check("rc helper: 48 to 64 pass, everything else (0, an old Static 127 / 128) asks for no size",
                  out == ["0", "0", "0", "0", "48", "56", "60", "64", "0", "0", "0", "0"], out)
    finally:
        shutil.rmtree(td, ignore_errors=True)
else:
    print("note: gcc not found - the rc helper run is skipped")

node = shutil.which("node")
v0 = js.find("function validate(c){"); v1 = js.find("\n}\n", v0)
p0 = js.find("var PD_MIN = "); p1 = js.find("\n", js.find("function pdLenOk(s){", p0))
if node and v0 > 0 and p0 > 0:
    # the page's real validate() and pdLenOk, with the kit's real rp.v (rp.js under a stub DOM)
    rpjs = rd(os.path.join(www, "reaper", "rp.js"))
    harness = ("var window = {}; var document = {readyState: 'complete', addEventListener: function(){}, querySelectorAll: function(){ return []; },"
               " getElementById: function(){ return null; }, body: {appendChild: function(){}} }; window.addEventListener = function(){};"
               " var XMLHttpRequest = function(){};\n" + re.sub(r"<%.*?%>", "", re.sub(r"<%\s*nvram_get_js\([^%]*%>", '""', rpjs)) + r"""
var rp = window.rp, EL = {}, SVC = 'dhcp6', NV = {ipv6_prefix_len_wan: '64'};
function q(id){ return EL[id] || (EL[id] = {value: '', checked: false, focus: function(){}, closest: function(){ return null; }}); }
function val(id){ return q(id).value.trim(); }
function svc(){ return SVC; }
""" + js[p0:p1 + 1] + js[v0:v1 + 3] + r"""
function run(s, pd, stored, typed){
  SVC = s; NV.ipv6_prefix_len_wan = stored; q('t_pd').checked = pd; q('i_plenwan').value = typed; q('s_ac').value = '0';
  q('i_ipaddr').value = '2001:db8::2'; q('i_gw').value = ''; q('i_plen').value = '64'; q('i_rtr').value = '2001:db8:1::1';
  return validate({}) === '' ? 'ok' : 'no';
}
var o = {};
o.pd = ['', '0', '48', '56', '64', ' 60 ', '47', '65', 'abc', '-1', '128', '3', '4 8'].map(function(x){ return run('dhcp6', true, '64', x); });
o.untouched = [run('dhcp6', true, '128', '128'), run('dhcp6', true, 'abc', 'abc'), run('dhcp6', true, '3', '3')];
o.touched = [run('dhcp6', true, '128', '127'), run('dhcp6', true, '128', '56'), run('dhcp6', true, '128', '')];
o.nopd = [run('dhcp6', false, '64', '200'), run('dhcp6', false, '64', 'abc')];
o.stat = ['3', '64', '128', '2', '129', '', 'abc'].map(function(x){ return run('other', true, '64', x); });
console.log(JSON.stringify(o));
""")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(harness); jp = f.name
    r = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
    import json
    try: o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: o = {}
    check("node: Native + PD takes empty, 0 and 48 to 64; refuses 47, 65, text, a negative number, 128",
          o.get("pd") == ["ok"] * 6 + ["no"] * 7, (r.stderr[-300:], o.get("pd")))
    check("node: an untouched stored value never blocks a save (an old Static 128, even text)", o.get("untouched") == ["ok", "ok", "ok"], o.get("untouched"))
    check("node: once the field is touched it is judged (127 refused; 56 or empty accepted)", o.get("touched") == ["no", "ok", "ok"], o.get("touched"))
    check("node: Native without prefix delegation does not judge the hidden field", o.get("nopd") == ["ok", "ok"], o.get("nopd"))
    check("node: Static still needs 3 to 128", o.get("stat") == ["ok", "ok", "ok", "no", "no", "no", "no"], o.get("stat"))
elif node:
    check("validate() and the PD window found for the node run", False, (v0, p0))

if node:
    body = js[len("<script>"):js.rfind("</script>")]
    body = re.sub(r"<%.*?%>", "", body); body = re.sub(r"`[^`]*`", "''", body)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(body); jp = f.name
    r = subprocess.run([node, "--check", jp], capture_output=True, text=True); os.unlink(jp)
    check("page script parses (node --check)", r.returncode == 0, r.stderr[-300:])
else:
    print("note: node not found - syntax check skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
