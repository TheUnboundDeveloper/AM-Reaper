#!/usr/bin/env python3
"""System Info › Capabilities by name (owner, 2026-11-05).

WHY. The card printed the router's raw rc_support tokens: build markers (bcmhnd, nandflash, ...) and tokens for things
Reaper does not offer - the ASUS app, telemetry, EULA and ASUS-update hooks the firmware still sets for closed programs.
The owner: "things still shown that we have removed". The page now names the features Reaper offers and nothing else;
rc_support itself is untouched (AiMesh and closed programs read it).

WHAT IT CHECKS. The page maps tokens to names (CAPN) and shows only mapped ones, one chip per name, Wi-Fi 6 only on a
router that is not Wi-Fi 7; the removed tokens have no entry; every menu string the map reuses exists in all 25
language packs and is safe inside a JS template literal.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys
SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "www", "Reaper_Sysinfo.asp")
if not SRC or not os.path.isfile(P):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
page = open(P, encoding="utf-8").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

m = re.search(r"  var CAPN=\{\n(.*?)\n  \};\n", page, re.S)
check("the page has the token -> name map", m)
body = m.group(1) if m else ""
keys = set(re.findall(r"(?:^|[\s,])'?([A-Za-z0-9_-]+)'?:", body))
for t in ("app", "appnet", "analytics", "eula", "update", "nordvpn", "bcmhnd", "nandflash", "no_finiwl"):
    check("no chip for '%s'" % t, t not in keys)
check("only mapped tokens are shown, one chip per name",
      "Object.prototype.hasOwnProperty.call(CAPN,c)" in page and "if(n && !seen[n]){ seen[n]=1; caps.push(n); }" in page
      and "caps.map(function(c){return '<span>'+esc(c)+'</span>';})" in page)
check("Wi-Fi 6 only where the router is not Wi-Fi 7", "if(tok.indexOf('wifi7')<0) CAPN['11AX']='Wi-Fi 6';" in page)
check("the raw token chips are gone", "split(/\\s+/).filter(Boolean).sort();" not in page)
check("page: plain ASCII", all(ord(c) < 0x7f for c in page))
used = sorted(set(re.findall(r"`<#([A-Za-z0-9_]+)#>`", body)))
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if re.fullmatch(r"[A-Z]{2}\.dict", f))
bad = {}
for pk in packs:
    d = {}
    for l in open(os.path.join(www, pk), encoding="utf-8", errors="replace"):
        if "=" in l:
            k, v = l.rstrip("\n").split("=", 1); d.setdefault(k, v)
    for k in used:
        if k not in d or not d[k].strip() or "`" in d[k] or "${" in d[k]:
            bad.setdefault(pk, []).append(k)
check("every reused menu string (%d) is in all %d packs and safe in a template literal" % (len(used), len(packs)),
      len(packs) == 25 and not bad, bad)
print("%d failure(s)" % len(fails))
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
