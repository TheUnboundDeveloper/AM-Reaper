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

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
