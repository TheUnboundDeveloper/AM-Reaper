#!/usr/bin/env python3
"""Field report 2026-11-15 (v3.7.9): on a "Default IoT Network" (sdn_name LEGACY) any saved edit on the Network page
put the network's LAN ports back to All (Default); the other network types kept theirs, and a reboot lost nothing.

Cause: a LEGACY network's device list is "<*>band>" (every node). The LAN page's VLAN tab stores a port in Access
mode as a per-node row after it ("<MAC>>L3"). The Network page's edit rebuilt the list from get_legacy_dut_list()
alone - the "*" row - so the per-node rows, and with them the port assignment, were dropped on every save. The other
types rebuild from the stored rows (ori_dut_list_json) and keep the lanport field.

Fix: the edit appends the stored per-node rows unchanged (reaper_legacy_port_rows). This suite checks the source and
runs the two helpers under node. Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC =
.../release/src/router)."""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SJ = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js") if SRC else ""
if not SJ or not os.path.isfile(SJ):
    print("SKIP: no router tree with the Network page's sdn.js (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail) if detail != "" else ""))

sj = open(SJ, encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")

# ---------------------------------------------------------------- the edit path
m = re.search(r"else if\(is_sdn_legacy\)\{\n\t+dut_list \+= get_legacy_dut_list\(wifi_band\);\n(.*?)\n\t+\}\n\t+else\{", sj, re.S)
check("edit: the LEGACY branch is found", m is not None)
body = m.group(1) if m else ""
check("edit: the stored per-node rows follow the '*' row", "dut_list += reaper_legacy_port_rows(ori_dut_list_json);" in body, body[-120:])
a = sj.find('var ori_dut_list_json = convertRulelistToJson(["mac","wifiband","lanport"], sdn_profile.apg_rl.dut_list);')
b = sj.find("dut_list += reaper_legacy_port_rows(ori_dut_list_json);")
check("edit: the stored list is read before the rebuild, in the same handler", 0 < a < b and b - a < 9000, (a, b))
check("edit: one call site (the wizard makes a new network - nothing stored to carry)", sj.count("reaper_legacy_port_rows(") == 2)
check("other types still carry the port field themselves",
      sj.count("wifi_band_set.lanport = specific_node.lanport;") >= 3 and "get_unChecked_dut_list(_obj, ori_dut_list_json)" in sj)

# ---------------------------------------------------------------- the helpers, run for real
def cut(head):
    i = sj.find("\n" + head)
    j = sj.find("\n}\n", i)
    return sj[i + 1:j + 3] if i >= 0 and j > i else ""

conv, leg, keep = cut("function convertRulelistToJson("), cut("function get_legacy_dut_list("), cut("function reaper_legacy_port_rows(")
check("helpers can be cut out", bool(conv and leg and keep))
NODE = shutil.which("node")
if NODE and conv and leg and keep:
    js = r'''
var $ = { each: function(o, f){ if (Array.isArray(o)) { for (var i = 0; i < o.length; i++) if (f(i, o[i]) === false) break; } else Object.keys(o).forEach(function(k){ f(k, o[k]); }); } };
''' + conv + leg + keep + r'''
function edit(stored, band){ var ori = convertRulelistToJson(["mac","wifiband","lanport"], stored); return get_legacy_dut_list(band) + reaper_legacy_port_rows(ori); }
console.log(JSON.stringify([
  edit("<*>81><AA:BB:CC:DD:EE:01>>L3", "7"),
  edit("<*>81><AA:BB:CC:DD:EE:01>>L3,L4<aa:bb:cc:dd:ee:02>>", "7"),
  edit("<*>81>", "7"),
  edit("<*>81><AA:BB:CC:DD:EE:01>>L3", "1"),
  edit(edit("<*>81><AA:BB:CC:DD:EE:01>>L3", "7"), "7"),
  edit("<*>81><*>7>L1<AA:BB:CC:DD:EE:01>>L3", "7"),
  edit("<*>81><not-a-mac>>L3<AA:BB:CC:DD:EE:01>3>L2", "7"),
  reaper_legacy_port_rows(undefined), reaper_legacy_port_rows(null), reaper_legacy_port_rows([]),
  reaper_legacy_port_rows([{mac: "AA:BB:CC:DD:EE:01", wifiband: "", lanport: "L3<x"}, {mac: "AA:BB:CC:DD:EE:02"}])
]));
'''
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "h.js"); open(f, "w").write(js)
        r = subprocess.run([NODE, f], capture_output=True, text=True)
        try:
            o = json.loads(r.stdout)
        except Exception:
            o = None
        check("helpers run under node", o is not None, r.stderr or r.stdout)
        if o:
            check("the report: an edit keeps the Access port row", o[0] == "<*>81><AA:BB:CC:DD:EE:01>>L3", o[0])
            check("several ports and a node without one: every row kept as stored",
                  o[1] == "<*>81><AA:BB:CC:DD:EE:01>>L3,L4<aa:bb:cc:dd:ee:02>>", o[1])
            check("no port assigned: the list is the '*' row alone, as before", o[2] == "<*>81>", o[2])
            check("a band change rewrites the '*' row and keeps the port row", o[3] == "<*>1><AA:BB:CC:DD:EE:01>>L3", o[3])
            check("a second edit adds nothing (no row doubles)", o[4] == o[0], o[4])
            check("a stray second '*' row is not carried", o[5] == "<*>81><AA:BB:CC:DD:EE:01>>L3", o[5])
            check("only a hardware address passes; a stored band is kept with its row",
                  o[6] == "<*>81><AA:BB:CC:DD:EE:01>3>L2", o[6])
            check("nothing stored, or not a list: nothing added", o[7] == "" and o[8] == "" and o[9] == "", o[7:10])
            check("a row that would break the list is left out; missing fields read as empty",
                  o[10] == "<AA:BB:CC:DD:EE:02>>", o[10])
else:
    print("note: node not found - the helpers were not run")

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails:
        print("  " + x)
    sys.exit(1)
print("\nall checks passed")
