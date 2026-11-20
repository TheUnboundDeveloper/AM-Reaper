#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A device cabled to an AiMesh node must not be shown as a Wi-Fi client (2026-11-14).

WHY THIS EXISTS. Owner report: "user connected to ethernet on an AiMesh node get shown as WiFi client". Two code
defects in Reaper's device view could do exactly that:
  A. httpd/web.c rdev_scan_amesh() returned as soon as the mesh WIRELESS list (/tmp/allwclientlist.json) was missing
     or broken - before it read the node WIRED list (/tmp/wiredclientlist.json). No node-cabled client then got its
     wired mark, and rdev_bh_resolve() called every one behind a wireless backhaul a Wi-Fi client;
  B. the gkd enrichment copied gkd's last band into rows already known to be wired, and two views that sort by band
     only (the dashboard client tiles on an AP / not-routing box, the AiMesh map overlay in AP mode) then counted the
     cabled device as Wi-Fi.
A third path - cfg_mnt / networkmap themselves listing the device as wireless - is closed-code data and is not
something a page can correct; this suite does not pretend otherwise.

WHAT IT CHECKS. Source pins for A and B in web.c (the wired list is read even with no wireless list; the wireless pass
is skipped, not the function; no band into a wired row), and a node run of the two page expressions: a wired device
with a stale band goes to the wired bucket / isWL 0, a Wi-Fi device keeps its band.
Exit 0 pass, 1 fail, 77 skip."""
import os, re, shutil, subprocess, sys, tempfile

SRC = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC")
       or os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router"))
web_p = os.path.join(SRC, "httpd", "web.c")
if not os.path.isfile(web_p):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
web = rd(web_p)
fails = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name); print("FAIL " + name + ((" :: " + str(detail)[:400]) if detail else ""))

i = web.find("static void rdev_scan_amesh(struct rdev *v, int *n)")
check("rdev_scan_amesh is present", i >= 0)
if i >= 0:
    body = web[i:web.index("\n}\n", i) + 3]
    check("A: no early return - a missing or broken wireless list only skips the wireless pass",
          "if (!wl) return;" not in body and "{ json_object_put(wl); return; }" not in body
          and "if (wl && !json_object_is_type(wl, json_type_object)) { json_object_put(wl); wl = NULL; }" in body
          and "\tif (wl) {\n\tjson_object_object_foreach(wl, nodemac, bands) {" in body)
    check("A: the node wired list is still read and applied after the wireless pass",
          body.index("wired = json_object_from_file(WIRED_CLIENT_LIST_JSON_PATH);") < body.index("json_object_object_foreach(wired, wnode, wmacs)")
          and body.index("}\t/* if (wl) */") < body.index("json_object_object_foreach(wired, wnode, wmacs)")
          and "v[idx].nwired = 1;" in body)
    check("A: the wireless list is released only when it was loaded", "\tif (wl) json_object_put(wl);\n}" in body
          and body.count("json_object_put(wl)") == 2)
check("B: gkd's band is not copied into a row already known to be wired",
      "if (!dev[idx].band[0] && seen[i].band[0] && !dev[idx].wired)" in web
      and "if (!dev[idx].band[0] && seen[i].band[0])\n" not in web)

dash = rd(os.path.join(SRC, "www", "Main_ReaperDash.asp"))
topo = rd(os.path.join(SRC, "www", "aimesh", "aimesh_topology.html"))
EXPR_D = "var k=d.wired?'eth':(d.band==='2.4')?'24':(d.band==='5')?'5':(d.band==='6')?'6':'eth';"
EXPR_T = "c.isWL = d.wired ? 0 : (wl[d.band] || 0);"
check("B: the dashboard client tiles test wired before the band", EXPR_D in dash)
check("B: the AiMesh map (AP mode) tests wired before the band", EXPR_T in topo)

node = shutil.which("node")
if node and EXPR_D in dash and EXPR_T in topo:
    js = ("var wl={'2.4':1,'5':2,'6':4};var out=[];\n"
          "[{wired:1,band:'5'},{wired:0,band:'5'},{wired:0,band:'2.4'},{wired:1,band:''},{wired:0,band:''}].forEach(function(d){\n"
          "  " + EXPR_D + "\n  var c={}; " + EXPR_T + "\n  out.push(k+'/'+c.isWL);});\n"
          "console.log(out.join(' '));\n")
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "t.js"); open(p, "w").write(js)
        r = subprocess.run([node, p], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        got = r.stdout.strip()
        check("node: wired with a stale 5 GHz band -> wired / isWL 0; Wi-Fi keeps its band; nothing known -> wired",
              got == "eth/0 5/2 24/1 eth/0 eth/0", got)
    finally:
        shutil.rmtree(d, ignore_errors=True)
else:
    print("note: node not found - the page expressions were pinned, not run")

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
