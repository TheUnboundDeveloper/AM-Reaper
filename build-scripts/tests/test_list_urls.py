#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dreadwatch and Wallguard show each built-in list's address on its row (forum request, 2026-11-02).

WHY THIS EXISTS. A user asked to read a list before ticking it; the addresses were only inside the
firmware. They now live in ONE table, shared/reaper_lists.h: rc downloads from it (rwarden.c RW_DFEEDS in the
generated Dreadwatch update script, wallguard.c presets[]) and httpd hands the same strings to the pages
(<% reaper_list_urls(); %>). A copy anywhere else could drift and show an address the router does not use.

WHAT IT CHECKS:
  (1) the header: every Dreadwatch id in RW_DIDS order (ThreatFox excluded - a bundled snapshot), every
      Wallguard preset, https only;
  (2) rc: RW_DFEEDS resolves to exactly "<id> <url>" per header pair; presets[] pairs each id with its header
      macro, bits 1..N in httpd's sh_presets order; no header address is spelled out in rc or httpd;
  (3) httpd: the page function compiles on the host and prints JSON equal to the header;
  (4) the pages: both read reaper_list_urls, open links in a new tab without a referrer, stay ASCII; Dreadwatch
      paints the rows at start-up and reads row names from the label text only; the ThreatFox note (RDWT_68)
      is in every language pack right after RDWT_67.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
HDR = os.path.join(SRC, "shared", "reaper_lists.h") if SRC else ""
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwarden.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()

check("shared/reaper_lists.h exists", os.path.isfile(HDR))
if not os.path.isfile(HDR):
    print("\n".join(fails)); sys.exit(1)
hdr, rw, wg, web = rd("shared/reaper_lists.h"), rd("rc/rwarden.c"), rd("rc/wallguard.c"), rd("httpd/web.c")
dwp, wgp = rd("www/Reaper_Dreadwatch.asp"), rd("www/Reaper_Wallguard.asp")

# ---- (1) the header
defs = dict(re.findall(r'^#define\s+(R(?:DW|WG)_URL_[A-Z0-9_]+)\s+"([^"]+)"', hdr, re.M))
def pairs(name):
    m = re.search(r'#define %s\(X\) \\\n((?:[^\n]*\\\n)*[^\n]*\n)' % name, hdr)
    return re.findall(r'X\("([a-z0-9_]+)", (R(?:DW|WG)_URL_[A-Z0-9_]+)\)', m.group(1)) if m else []
dw, wgl = pairs("RDW_LIST"), pairs("RWG_LIST")
check("every X() pair names a defined address", dw and wgl and all(mac in defs for _, mac in dw + wgl), [p for p in dw + wgl if p[1] not in defs])
check("every address is https", defs and all(u.startswith("https://") for u in defs.values()))
dids = re.search(r'#define RW_DIDS_STR\s+"([^"]+)"', rw)
check("Dreadwatch ids follow RW_DIDS order without threatfox",
      dids and [i for i, _ in dw] == [x for x in dids.group(1).split() if x != "threatfox"], (dids and dids.group(1), [i for i, _ in dw]))

# ---- (2) rc
blk = re.search(r'"RW_DFEEDS=\\"(.*?)"threatfox ', rw, re.S)
got = re.findall(r'"([a-z0-9_]+) " (RDW_URL_[A-Z0-9_]+) "\\n"', "\"" + blk.group(1)) if blk else []
check("RW_DFEEDS = one '<id> <url>' line per header pair, in order", got == dw, got)
check("rwarden.c and wallguard.c include the header", "#include <reaper_lists.h>" in rw and "#include <reaper_lists.h>" in wg)
pre = re.search(r'presets\[\] = \{(.*?)\n\};', wg, re.S)
prs = re.findall(r'\{\s*(\d+),\s*"([a-z0-9_]+)",\s*(RWG_URL_[A-Z0-9_]+)\s*\}', pre.group(1)) if pre else []
check("presets[] pairs each id with its header address", [(i, m) for _, i, m in prs] == wgl, prs)
shp = re.search(r'static const char \*sh_presets\[\] = \{(.*?)NULL \};', web, re.S)
shids = re.findall(r'"([a-z0-9_]+)"', shp.group(1)) if shp else []
check("httpd sh_presets = the presets in bit order (bit = position + 1)",
      prs and shids == [i for _, i, _ in prs] and [int(b) for b, _, _ in prs] == list(range(1, len(prs) + 1)), (shids, prs))
for f, t in (("rc/rwarden.c", rw), ("rc/wallguard.c", wg), ("httpd/web.c", web)):
    check("%s spells out no header address" % f, not [u for u in defs.values() if u in t], [u for u in defs.values() if u in t])

# ---- (3) httpd
check("httpd includes the header and registers the page function",
      '#include "reaper_lists.h"' in web and '{ "reaper_list_urls", ej_reaper_list_urls},' in web)
fn = re.search(r'\nstatic int\nej_reaper_list_urls\(int eid, webs_t wp, int argc, char_t \*\*argv\)\n\{.*?\n\}\n', web, re.S)
check("ej_reaper_list_urls is there", fn is not None)
CC = shutil.which("gcc") or shutil.which("cc")
if fn and CC:
    w = tempfile.mkdtemp(prefix="lurl_")
    try:
        c = os.path.join(w, "t.c")
        open(c, "w").write('#include <stdio.h>\ntypedef void *webs_t;\ntypedef char char_t;\n#define websWrite(wp, ...) printf(__VA_ARGS__)\n'
                           + hdr + fn.group(0) + "int main(void) { return ej_reaper_list_urls(0, 0, 0, 0) > 0 ? 0 : 1; }\n")
        r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-parameter", "-o", os.path.join(w, "t"), c], capture_output=True, text=True)
        check("the page function compiles on the host", r.returncode == 0, r.stderr[-600:])
        if r.returncode == 0:
            out = subprocess.run([os.path.join(w, "t")], capture_output=True, text=True).stdout
            try: j = json.loads(out)
            except ValueError: j = None
            check("it prints JSON equal to the header",
                  j == {"dw": {i: defs[m] for i, m in dw}, "wg": {i: defs[m] for i, m in wgl}}, out[:300])
    finally:
        shutil.rmtree(w, ignore_errors=True)
else:
    print("note: no C compiler - the JSON run skipped")

# ---- (4) the pages
for name, p in (("Dreadwatch", dwp), ("Wallguard", wgp)):
    check(name + ": reads the addresses from httpd", "var LURL = <% reaper_list_urls(); %>;" in p)
    check(name + ": links open in a new tab without a referrer", "a.target = '_blank'; a.rel = 'noopener noreferrer';" in p)
    check(name + ": no address typed into the page", not [u for u in defs.values() if u in p])
    check(name + ": pure ASCII", all(ord(ch) < 0x80 for ch in p))
check("Dreadwatch: rows painted at start-up", "dwPaintSrc();\ndwPaintUrls();\n" in dwp)
check("Dreadwatch: Basics shows its three lists and the ThreatFox note",
      "(id === 'basics' ? DNS_BASICS : [id])" in dwp and "`<#RDWT_68#>`" in dwp)
check("Dreadwatch: a row's name is read from its label, not the whole cell",
      "tr.cells[0].firstChild.textContent : id" in dwp and "cells[0].textContent" not in dwp)
check("Wallguard: each preset row gets its address", "if(r.preset && LURL && LURL.wg && LURL.wg[r.id]) td.appendChild(lsLink(LURL.wg[r.id]));" in wgp)
packs = sorted(f[:-5] for f in os.listdir(os.path.join(SRC, "www")) if re.match(r"^[A-Z]{2}\.dict$", f))
bad = []
for pk in packs:
    t = rd("www/%s.dict" % pk)
    if not re.search(r"^RDWT_67=[^\n]*\r?\nRDWT_68=ThreatFox.*2026", t, re.M): bad.append(pk)
check("RDWT_68 follows RDWT_67 in all %d packs and names ThreatFox and 2026" % len(packs), packs and not bad, bad)

print("\n%d failure(s)" % len(fails) if fails else "\nall checks passed")
if fails:
    print("\n".join(fails)); sys.exit(1)
