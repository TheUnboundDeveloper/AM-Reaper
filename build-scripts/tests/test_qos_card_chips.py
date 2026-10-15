#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The QoS engine cards' chips say what each engine does, in one colour scheme (2026-10-15).

WHY THIS EXISTS. Reaper_QoS.asp shows a card per engine with short chips. Plain chips were
drawn in the page's steel grey and read as switched off ("unlit"); and checked against rc the
cards had drifted:
  - the Bandwidth Limiter card did not say the accelerator goes off, although
    hnd_nat_ac_init() (rc/sysdeps/init-broadcom.c) sets fc_disable for every engine but
    off / 10 / 11, the limiter included;
  - HW QoS Classful said "Upload only", but it has an opt-in download cap (the ingress
    policer, start_hwqos_classful(), qos_ipolicer), which the page's own RQOS_08 names;
  - "Up + Down" was green on Cake and plain on Traditional, which shapes download too
    (imq0, start_tqos()) and has per-class minimums and ceilings like Classful;
  - "No control" (Off) was plain while "Not bufferbloat" (Limiter) was amber - the same cost.

THE SCHEME. green (good) = a strength, amber (warn) = a real cost, plain = a fact about scope,
drawn readable (bone-dim), not steel. Every card names the accelerator first; one token keeps
one colour on every card.

WHAT IT DOES. Parses the MODES table and the .tag CSS, derives the accelerator state per
engine from init-broadcom.c, and checks the rules above plus the new RQOS_126 token in all 25
packs. A negative self-test puts the old Limiter chips back and expects the accelerator rule to
fail.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or
REAPER_ROUTER_SRC)."""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PAGE = os.path.join(SRC, "www", "Reaper_QoS.asp") if SRC else ""
INIT = os.path.join(SRC, "rc", "sysdeps", "init-broadcom.c") if SRC else ""
if not PAGE or not os.path.isfile(PAGE) or not os.path.isfile(INIT):
    skip("no router source tree with www/Reaper_QoS.asp and rc/sysdeps/init-broadcom.c")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

page = open(PAGE, encoding="utf-8", errors="replace").read()
init = open(INIT, encoding="utf-8", errors="replace").read()

def modes(text):
    m = re.search(r"var MODES = \[(.*?)\n\];", text, re.S)
    out = {}
    for key, tags in re.findall(r"\{key:'([^']+)'.*?tags:\[(.*?)\]\}", m.group(1) if m else "", re.S):
        out[key] = re.findall(r"\[`<#(\w+)#>`,'(\w*)'\]", tags)
    return out

ACCEL_ON, ACCEL_OFF = ("RQOS_69", "good"), ("RQOS_79", "warn")

# accelerator per engine, from the rc decision: fc_disable for NON_AQOS unless HWQOS/HWQOS_CLASSFUL
check("rc: the accelerator rule is still 'every engine but 10/11 turns it off'",
      "IS_NON_AQOS() && !IS_HWQOS() && !IS_HWQOS_CLASSFUL()" in init)
def accel_expected(key):
    return ACCEL_ON if key in ("off", "10", "11") else ACCEL_OFF

def rules(M, label=""):
    bad = []
    for key, tags in M.items():
        if not tags or tags[0] != accel_expected(key):
            bad.append("%s first chip %s, want %s" % (key, tags[:1], accel_expected(key)))
    return bad

M = modes(page)
check("page: the six engine cards parsed", sorted(M) == sorted(["off", "11", "10", "9", "0", "2"]), sorted(M))
bad = rules(M)
check("every card names the accelerator first, matching rc", not bad, bad)
colour = {}
clash = []
for key, tags in M.items():
    for tok, cls in tags:
        if tok in colour and colour[tok] != cls:
            clash.append("%s: %s vs %s" % (tok, colour[tok], cls))
        colour.setdefault(tok, cls)
check("one token = one colour on every card", not clash, clash)
check("Classful: no 'Upload only' (it has the opt-in download cap) - RQOS_126 instead",
      ("RQOS_73", "") not in M.get("11", []) and ("RQOS_126", "") in M.get("11", []))
check("HW QoS (10) keeps 'Upload only' + 'No classes' (no download path at all)",
      ("RQOS_73", "") in M.get("10", []) and ("RQOS_77", "") in M.get("10", []))
check("Traditional: Up + Down and Classes + guarantees, like Cake / Classful",
      ("RQOS_80", "good") in M.get("0", []) and ("RQOS_74", "good") in M.get("0", []))
check("Off: 'No control' is a cost, like the Limiter's 'Not bufferbloat'",
      ("RQOS_70", "warn") in M.get("off", []) and ("RQOS_85", "warn") in M.get("2", []))

css = re.search(r"\n\.tag\{([^}]*)\}", page)
check("a plain chip is drawn readable (bone-dim), not steel",
      css is not None and "color:var(--bone-dim)" in css.group(1) and "--steel" not in css.group(1),
      css.group(1) if css else "")

packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if os.path.basename(p) != "temp.dict")
missing = [os.path.basename(p) for p in packs
           if not re.search(r"^RQOS_126=\S", open(p, encoding="utf-8", errors="replace").read(), re.M)]
check("RQOS_126 in all 25 packs", len(packs) == 25 and not missing, missing)
en = open(os.path.join(SRC, "www", "EN.dict"), encoding="utf-8").read()
check("EN RQOS_126 names the download cap as optional",
      re.search(r"^RQOS_126=Optional download cap$", en, re.M) is not None)

# self-test: the old Limiter card (no accelerator chip) must trip the accelerator rule
old = dict(M); old["2"] = [("RQOS_84", ""), ("RQOS_85", "warn")]
check("self-test: the pre-fix Limiter card fails the accelerator rule", bool(rules(old)))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
