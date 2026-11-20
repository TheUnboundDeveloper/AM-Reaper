#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The header tooltip's LAN name check note says only what the System Log holds (2026-10-15).

WHY THIS EXISTS. The header tooltip (Main_ReaperDash.asp and reaper_shell.asp, both via
RDSH_101) ended in "Details: System Log." in every state but off, while rdnshc's LAN name check
(rc/rdnshc.c, landns_tick) logs only when it starts FAILING and when it is "restored" - nothing
at start and nothing while it works, so a user who followed the pointer found nothing. The
token was also English in all 25 packs.

THE FIX. RDSH_101 now says failures and recoveries are recorded there, translated in every
pack, each naming its own System Log menu entry (System_Log). No code change.

WHAT IT DOES. Checks rdnshc still logs exactly those two transitions (the promise the text
makes), both header copies still use RDSH_101, and the 25 packs: no "Details:" pointer left, no
pack still English, each names its System_Log title. A negative self-test feeds the old text.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or
REAPER_ROUTER_SRC)."""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RD = os.path.join(SRC, "rc", "rdnshc.c") if SRC else ""
if not RD or not os.path.isfile(RD):
    skip("no router source tree with rc/rdnshc.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

rd = open(RD, encoding="utf-8", errors="replace").read()
check("rdnshc logs the LAN name check going bad", rd.count('"LAN name resolution FAILING:') == 4)
check("rdnshc logs the recovery", '"LAN name resolution restored after %ld s"' in rd)
for page in ("Main_ReaperDash.asp", "reaper_shell.asp"):
    t = open(os.path.join(SRC, "www", page), encoding="utf-8", errors="replace").read()
    check(page + ": the tooltip note is RDSH_101", "every:`<#RDSH_101#>`" in t)

def val(text, key):
    m = re.search(r"^%s=(.*)$" % key, text, re.M)
    return m.group(1) if m else None

def pack_problems(lang, text, en101):
    v, log = val(text, "RDSH_101"), val(text, "System_Log")
    out = []
    if not v: out.append("missing")
    elif "Details:" in v: out.append("still a bare 'Details:' pointer")
    elif lang != "EN" and v == en101: out.append("still English")
    elif not log or log.lower()[:5] not in v.lower(): out.append("does not name its System Log (%s)" % log)
    return out

packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if os.path.basename(p) != "temp.dict")
texts = {os.path.basename(p)[:-5]: open(p, encoding="utf-8", errors="replace").read() for p in packs}
en101 = val(texts.get("EN", ""), "RDSH_101") or ""
check("EN RDSH_101 promises failures and recoveries, not 'details'",
      en101 == "Checked by the router once a minute. Problems and recoveries are recorded in the System Log.", en101)
bad = {l: pack_problems(l, t, en101) for l, t in texts.items()}
bad = {l: p for l, p in bad.items() if p}
check("25 packs: RDSH_101 translated, names the pack's System Log, no 'Details:'", len(texts) == 25 and not bad, bad)

old = re.sub(r"^RDSH_101=.*$", "RDSH_101=Checked by the router once a minute. Details: System Log.",
             texts.get("DE", ""), flags=re.M)
check("self-test: the old text is caught", bool(pack_problems("DE", old, en101)))

# 2026-11-10 (owner): the status word is Active / Inactive / Fault - in the header tooltip (both copies) and on
# the DNS Failover page's LAN name row, in every pack's own language.
en = texts.get("EN", "")
check("EN: Active, Fault, Inactive", (val(en, "RDSH_92"), val(en, "RDSH_93"), val(en, "RDSH_95")) == ("Active", "Fault", "Inactive"),
      (val(en, "RDSH_92"), val(en, "RDSH_93"), val(en, "RDSH_95")))
badw = {}
for l, t in texts.items():
    w = [val(t, k) for k in ("RDSH_92", "RDSH_93", "RDSH_95")]
    if not all(w) or len(set(w)) != 3: badw[l] = w
    elif l != "EN" and (w[0] == "Active" or w[1] == "Fault" or w[2] == "Inactive"): badw[l] = ["still English"] + w
    elif any(x in " ".join(w) for x in ("working", "FAILING", "switched off")): badw[l] = ["old words"] + w
check("25 packs: three different status words, none left in English, none of the old words", len(texts) == 25 and not badw, badw)
for page in ("Main_ReaperDash.asp", "reaper_shell.asp"):
    t = open(os.path.join(SRC, "www", page), encoding="utf-8", errors="replace").read()
    check(page + ": the tooltip takes the three words from RDSH_92 / 93 / 95",
          "working:`<#RDSH_92#>`" in t and "failing:`<#RDSH_93#>`" in t and "off:`<#RDSH_95#>`" in t
          and "else if(st==='off') line=NT.off;" in t and "line=NT.working" in t and "line=NT.failing+" in t)
fo = open(os.path.join(SRC, "www", "Reaper_Failover.asp"), encoding="utf-8", errors="replace").read()
check("DNS Failover page: the LAN name row uses the same three tokens, Inactive when off",
      "ldWorking: `<#RDSH_92#>`" in fo and "ldFailing: `<#RDSH_93#>`" in fo and "ldOff: `<#RDSH_95#>`" in fo
      and "st === ''){ txt = T.ldOff; cls = 'v dim'; }" in fo and "txt = T.ldWorking" in fo)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
