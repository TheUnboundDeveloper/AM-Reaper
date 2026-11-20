#!/usr/bin/env python3
"""The OUI (MAC -> vendor) table ships once (2026-11-01).

WHY. networkmap installs /usr/networkmap/ieee.oui.json and www/ajax/ouiDB.json was the same 40,335-entry
table a second time (1.4 MB raw, ~310 KB of flash), with its accented vendor names stripped by the web
minifier. The pages only look a vendor up by OUI, so on a tree whose networkmap ships the table the web
path becomes a link to it.

WHAT IT DOES. Pins the www/Makefile block: after the minifier and the comment stripper (so nothing
rewrites the table through the link), gated on networkmap's table being in the tree (the 102.8 GPL ships
none and keeps the www copy), relative so it resolves inside the image; networkmap still installs the
table where it exists; httpd still serves the path; every page reads it by OUI only.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "www")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

mk = rd("www/Makefile")
BLOCK = ("ifneq ($(wildcard $(TOP)/networkmap/db/ieee.oui.json),)\n"
         "\trm -f $(INSTALLDIR)/www/ajax/ouiDB.json\n"
         "\tln -sf ../../usr/networkmap/ieee.oui.json $(INSTALLDIR)/www/ajax/ouiDB.json\n"
         "endif\n")
check("www/Makefile links the web OUI path to networkmap's table, only when that table is in the tree", BLOCK in mk)
check("the link is made after the vendor minifier and Reaper's comment stripper",
      BLOCK in mk and mk.index("sh $(SRCBASE)/image/compress.sh") < mk.index(BLOCK)
      and mk.index("-python3 $(TOP)/tools/reaper_strip.py $(INSTALLDIR)/www || true") < mk.index(BLOCK))
has_db = os.path.exists(os.path.join(SRC, "networkmap", "db", "ieee.oui.json"))
nm = rd("networkmap/Makefile") if os.path.exists(os.path.join(SRC, "networkmap", "Makefile")) else ""
check("networkmap installs the table wherever the tree has it",
      (not has_db) or "cp -f db/ieee.oui.json $(INSTALLDIR)/usr/networkmap/ieee.oui.json" in nm)
check("the www copy stays in the source tree (merges; the fallback for a tree without networkmap's table)",
      os.path.exists(os.path.join(SRC, "www", "ajax", "ouiDB.json")))
check("httpd still serves the path", '{ "ajax/ouiDB.json", "text/javascript", cache_object, NULL, do_file, NULL },' in rd("httpd/web.c"))
uses = []
for p in ("www/client_function.js", "www/index.asp"):
    t = rd(p)
    for m in re.finditer(r'\$\.getJSON\("/ajax/ouiDB\.json", function\(data\)\{(.{0,160})', t, re.S):
        uses.append(m.group(1))
check("every page reads the table by OUI only (data[queryStr]; no timestamp or other key)",
      uses and all("data[queryStr]" in u for u in uses) and "data.timestamp" not in rd("www/client_function.js"), len(uses))

if fails:
    print("\n%d failure(s)" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\n0 failure(s)")
