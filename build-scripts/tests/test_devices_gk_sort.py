#!/usr/bin/env python3
"""Sortable columns on the Devices and Gatekeeper pages (backlog [P3], owner 2026-10-23; built 2026-10-24).

WHY. Both lists refresh every few seconds and were drawn in the router's order only. The backlog note asks for
click-to-sort headers on both pages, one shared comparator (the kit's rp.cmp), IPs by octet, names without case,
offline devices after online ones on a name sort, the choice remembered per browser, and an order that survives a
refresh without rows jumping. The Devices page addresses its rows by their index in D.devices (edit / pin / access
actions), so the sort reorders indices and never the data.

WHAT IT DOES. Source pins on both pages, then the sort functions run under node with the kit comparator against
synthetic rows: online-first on a name sort, octet IP order, numbers largest first by default, direction flip,
and the stored order kept when nothing is chosen.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isdir(SRC):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
www = os.path.join(SRC, "www")
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

DV, GK, RP = rd(os.path.join(www, "Reaper_Devices.asp")), rd(os.path.join(www, "Reaper_GK.asp")), rd(os.path.join(www, "reaper", "rp.js"))
for name, t, pre, store, keys in (("Devices", DV, "", "rdev_sort", ("name", "mac", "ip", "conn", "gk", "last", "traf")),
                                  ("Gatekeeper", GK, "gk", "rgk_sort", ("name", "mac", "conn", "state", "last"))):
    check(name + ": loads the kit script (rp.cmp, one comparator for both pages)", '<script src="/reaper/rp.js"></script>' in t)
    check(name + ": every sortable header carries data-k", all(('data-k="%s"' % k) in t for k in keys))
    # review 2026-10-24 (Q-C2-11): the sort state, header marks and click handling are ONE kit copy, rp.sorter
    check(name + ": the kit sorter, remembered per browser under the page's own key; names without case",
          "rp.sorter('%s', {" % store in t and ".toLowerCase()" in t)
    check(name + ": header css for the sortable columns", "th[data-k]{cursor:pointer" in t)
check("kit: rp.sorter - click sorts, again reverses, saved (try/catch), numbers first, online ahead on a name sort, rp.cmp",
      "rp.sorter = function(storageKey, types, val, onChange){" in RP and "localStorage.setItem(storageKey" in RP
      and "localStorage.getItem(storageKey)" in RP and "S.dir = -S.dir" in RP and "'num' ? -1 : 1" in RP
      and "online !== !!" in RP and "online ? -1 : 1" in RP and "rp.cmp(types[S.k])" in RP)
check("Devices: rows are reordered by index (the actions keep addressing D.devices[i])",
      "devOrder().forEach(function(i){\n    var d = D.devices[i];" in DV and "function devOrder(){" in DV)
check("Devices: the sort is applied at every render (survives the poll refresh)", "function renderRows(){" in DV and "sortHead();" in DV)
check("Gatekeeper: the sort is applied inside gkRender (every 5 s repaint)", "var devs = gkOrder(j.devices || []);" in GK and "gkSortHead();" in GK)

node = shutil.which("node")
d0, d1 = DV.find("function sortVal(d, k){"), DV.find("function sortHead(){ SORTER.head(); }")
g0, g1 = GK.find("function gkSortVal(d, k){"), GK.find("function gkSortHead(){ GKSORTER.head(); }")
r0, r1 = RP.find("function ip4key(s)"), RP.find("/* ---- i18n overflow")
if node and d0 > 0 and d1 > d0 and g0 > 0 and g1 > g0 and r0 > 0 and r1 > r0:
    harness = ("var localStorage = {d:{}, getItem:function(k){ return this.d[k] || null; }, setItem:function(k, v){ this.d[k] = v; }};\n"
               "var document = {querySelector: function(){ return null; }, querySelectorAll: function(){ return []; }};\n"
               "var rp = {v: {}}; " + RP[r0:r1] + "\n"
               "var TRAF = {'00:00:5E:00:53:02': 500, '00:00:5E:00:53:01': 9000};\n"
               "var D = {devices: [\n"
               "  {name: 'zeta', mac: '00:00:5E:00:53:01', ip: '192.168.50.9', online: true, band: '5', last: 100, gk: 1},\n"
               "  {name: 'alpha', mac: '00:00:5E:00:53:02', ip: '192.168.50.100', online: false, wired: true, last: 50, gk: 0},\n"
               "  {name: 'Beta', mac: '00:00:5E:00:53:03', ip: '192.168.50.20', online: true, band: '2.4', last: 200, gk: 2},\n"
               "  {host: 'gamma', mac: '00:00:5E:00:53:04', ip: '', online: false, last: 10, gk: -1}]};\n"
               "function renderRows(){}\n" + DV[d0:d1] + "\n"
               "var out = {};\n"
               "out.dflt = devOrder();\n"
               "SORTER.set('name'); out.name = devOrder(); SORTER.set('name'); out.nameRev = devOrder();\n"
               "SORTER.set('ip'); out.ip = devOrder();\n"
               "SORTER.set('traf'); out.traf = devOrder(); out.trafDir = JSON.parse(localStorage.getItem('rdev_sort')).dir;\n"
               "SORTER.set('last'); out.last = devOrder();\n"
               "out.saved = JSON.parse(localStorage.getItem('rdev_sort'));\n"
               "function gkConn(d){ return d.band ? d.band + ' GHz' : 'Wired'; }\n"
               "function gkRender(){}\n" + GK[g0:g1] + "\n"
               "var devs = [{host: 'b', mac: '1', online: false, state: 1, last: 5, band: '5'}, {host: 'a', mac: '2', online: false, state: 0, last: 9}, {host: 'c', mac: '3', online: true, state: 3, last: 1, band: '2.4'}];\n"
               "out.gkDflt = gkOrder(devs).map(function(d){ return d.mac; });\n"
               "GKSORTER.set('name'); out.gkName = gkOrder(devs).map(function(d){ return d.mac; });\n"
               "GKSORTER.set('state'); out.gkState = gkOrder(devs).map(function(d){ return d.mac; });\n"
               "console.log(JSON.stringify(out));\n")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(harness); hp = f.name
    r = subprocess.run([node, hp], capture_output=True, text=True); os.unlink(hp)
    try: o = json.loads(r.stdout)
    except Exception: o = None
    check("sort functions run under node", o is not None, (r.stderr or r.stdout)[-300:])
    if o:
        check("Devices: no choice = the router's order", o["dflt"] == [0, 1, 2, 3], o["dflt"])
        check("Devices: name sort - online first (Beta, zeta), then offline (alpha, gamma by host), case ignored", o["name"] == [2, 0, 1, 3], o["name"])
        check("Devices: second click reverses (online still first)", o["nameRev"] == [0, 2, 3, 1], o["nameRev"])
        check("Devices: IP sort by octet (.9 < .20 < .100), empty last", o["ip"] == [0, 2, 1, 3], o["ip"])
        check("Devices: traffic sort starts largest first", o["trafDir"] == -1 and o["traf"] == [0, 1, 2, 3], (o["trafDir"], o["traf"]))
        check("Devices: last-seen sort - online rows first, then most recent", o["last"] == [0, 2, 1, 3], o["last"])
        check("Devices: the choice is saved", o["saved"] == {"k": "last", "dir": -1}, o["saved"])
        check("Gatekeeper: no choice = gkd's order; name sort online first; state sort largest first", o["gkDflt"] == ["1", "2", "3"] and o["gkName"] == ["3", "2", "1"] and o["gkState"] == ["3", "1", "2"], (o["gkDflt"], o["gkName"], o["gkState"]))
else:
    print("note: node not found or a sort block moved - vector checks skipped")

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + x) for x in fails]; sys.exit(1)
print("\nall checks passed")
