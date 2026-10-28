#!/usr/bin/env python3
"""Wireless Log: one box per network inside each radio (owner, 2026-10-26).

WHY. Testers read the one mixed client table of a radio as one network: main and guest clients sat together, told
apart only by a Network column, and the main network was never named. On this firmware the primary BSS wlN is the
hidden AiMesh backhaul carrier (it beacons a hashed SSID), wlN.1 is the main network and wlN.2 / wlN.3 the guests;
get_wl_status tags a client "" (wlN.1), "Main BSS" (wlN) or the guest SSID.

WHAT IT DOES. Source checks on Reaper_WLog.asp: the names are read through nvram_char_to_ascii (an SSID may hold
' or \\), the Network column is gone, the guest chip uses the stock Guest_Network key (in every pack). Then a node run
of the page's own nets() (extracted, never copied): box order main / guests / backhaul, client placement, the
BSSID going to the box the radio SSID names, wlN.1 off (the primary is then the main network), and no boxes in a
mode that serves no clients.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_WLog.asp")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

www = os.path.join(SRC, "www")
W = open(os.path.join(www, "Reaper_WLog.asp"), encoding="utf-8").read()
reads = re.findall(r'nvram_char_to_ascii\("","wl([0-3])\.([1-3])_(ssid|bss_enabled)"\)', W)
check("the 24 network names and switches are read through nvram_char_to_ascii",
      len(set(reads)) == 24 and not re.search(r'nvram_get\("wl[0-3]\.[1-3]_', W), len(set(reads)))
check("the Network column is gone; each box carries its own name", "k: 'net'" not in W and "RLOG_76" not in W)
check("the guest chip uses the stock Guest_Network key", "hx(`<#Guest_Network#>`)" in W)
packs = [f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict"]
bad = [f for f in packs if not re.search(r"(?m)^Guest_Network=\S", open(os.path.join(www, f), encoding="utf-8", errors="replace").read())]
check("all 25 packs carry Guest_Network", len(packs) == 25 and not bad, bad)

m = re.search(r"\nvar RANK = .*?\n}\n(?=function netHtml\()", W, re.S)
check("nets() found", m is not None)
node = shutil.which("node")
if m and node:
    CASES = r"""
var out = {};
function cl(name, tag, vlan){ return {name: name, tag: tag, vlan: vlan || ''}; }
function view(ns){ return ns.map(function(n){ return [n.kind, n.name, n.vlan, n.bssid, n.list.map(function(c){ return c.name; })]; }); }
var VSSID = [["Home's \\", 'Guests', 'Old'], ['Home5', 'IoT', ''], ['', '', '', ''], ['', '', '']];
var VON = [['1', '1', '0'], ['1', '1', ''], ['0', '', ''], ['', '', '']];
var HASH = '6b1c2a0f9e8d7c6b5a4f3e2d1c0b9a88';
out.ap = view(nets(0, [HASH, '0', '0', '-92', '6/20', 'AA:00', '12', 'AP'],
  [cl('node', 'Main BSS'), cl('phone', ''), cl('visitor', 'Guests', '52'), cl('tv', 'Lab', '60')]));
out.same = view(nets(1, ['Home5', '0', '0', '-92', '36/160', 'BB:00', '3', 'AP'], []));
out.off = view(nets(2, ['Primary', '0', '0', '-92', '37/320', 'CC:00', '1', 'AP'], [cl('phone', 'Main BSS')]));
out.bridge = view(nets(1, ['Upstream', '-60', '30', '-95', '36/160', 'BB:00', '3', 'Media Bridge'], []));
out.rep = view(nets(1, ['Upstream', '-60', '30', '-95', '36/160', 'BB:00', '3', 'Repeater ( SSID local: Home5 )'], [cl('phone', '')]));
console.log(JSON.stringify(out));
"""
    fd, jp = tempfile.mkstemp(suffix=".js"); os.close(fd)
    open(jp, "w", encoding="utf-8").write(m.group(0) + CASES)
    r = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
    try:
        o = json.loads(r.stdout)
    except ValueError:
        o = {}
        check("nets() runs", False, r.stderr[-300:])
    if o:
        check("AP: main (wlN.1 name) first, then the guests in slot order, then a client-only network, backhaul last",
              o["ap"] == [["main", "Home's \\", "", "", ["phone"]], ["guest", "Guests", "52", "", ["visitor"]],
                          ["guest", "Lab", "60", "", ["tv"]], ["bh", "", "", "AA:00", ["node"]]], o["ap"])
        check("AP: the main box and an enabled guest show with no clients; the radio BSSID goes to the main box it names",
              o["same"] == [["main", "Home5", "", "BB:00", []], ["guest", "IoT", "", "", []]], o["same"])
        check("wlN.1 off: the primary is the main network (its clients, its name, its BSSID)",
              o["off"] == [["main", "Primary", "", "CC:00", ["phone"]]], o["off"])
        check("Media Bridge: no boxes", o["bridge"] == [], o["bridge"])
        check("Repeater: the local network (wlN.1) is the main box; no BSSID moved out of the radio facts",
              o["rep"] == [["main", "Home5", "", "", ["phone"]], ["guest", "IoT", "", "", []]], o["rep"])
elif not node:
    print("note: node not found - nets() run skipped")
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
