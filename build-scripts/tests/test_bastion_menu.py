#!/usr/bin/env python3
"""The Warden menu is Bastion (owner, 2026-10-26).

WHY. The menu holds four blocking layers - Warden (addresses), Dreadwatch (threat domains), Wallguard (ads and
trackers) and Encrypted DNS - and was named after the first of them. The menu is now Bastion; the Warden tab keeps
its name, and the menu's index (menu_ReaperWarden) stays so links, bookmarks and the icon map keep working.

WHAT IT DOES. menu.js labels the menu with RBST_00 and the first tab with RWDN_00; every one of the 25 packs carries
RBST_00=Bastion (a name, kept as is like Warden, Dreadwatch and Wallguard); the Guide's chapter 4.3 is Bastion and
no current doc gives a "Warden ›" menu path.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "reaper", "menu.js")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

m = open(os.path.join(SRC, "www", "reaper", "menu.js"), encoding="utf-8").read()
check("the menu is labelled Bastion; its index is unchanged",
      "{index: 'menu_ReaperWarden', when: routing, label: `<#RBST_00#>`, tabs: [" in m)
check("the first tab is still Warden", "T('Reaper_Warden.asp', `<#RWDN_00#>`)" in m)
www = os.path.join(SRC, "www")
packs = [f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict"]
bad = [f for f in packs if "\nRBST_00=Bastion\n" not in open(os.path.join(www, f), encoding="utf-8", errors="replace").read()]
check("all 25 packs carry RBST_00=Bastion", len(packs) == 25 and not bad, bad)
docs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs")
g = os.path.join(docs, "REAPER-GUIDE.md")
if os.path.isfile(g):
    t = open(g, encoding="utf-8").read()
    check("the Guide's chapter 4.3 is Bastion and names the four tabs",
          "### 4.3 Bastion\n" in t and "4.3 [Bastion](#43-bastion)" in t and "**The Bastion menu** holds" in t)
    check("no current doc gives a Warden menu path",
          not re.search(r"Warden ›", t) and not re.search(r"Warden ›", open(os.path.join(docs, "BACKLOG.md"), encoding="utf-8").read()))
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
