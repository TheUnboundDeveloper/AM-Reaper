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

node = shutil.which("node")
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
