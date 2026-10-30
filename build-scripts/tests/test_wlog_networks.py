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

2026-10-30 (field, GT-BE98 v3.6.2): a box other than the main network is labelled with its Guest Network Pro type
(sdn_rl + apg<idx>_ssid -> Guest / IoT / Kids ...), not "Guest Network" for every one (a main + guest + IoT router read
as two guest networks); without profiles the stock slots wlN.2 / wlN.3 stay guest networks. Device names: your name
(custom_clientlist / the live list, by MAC then IP) first, the DHCP lease hostname after, "*" is none - the native page
had shown only the lease hostname. Both run under node from the page's own source.
Same day, the reporter's screenshot: on a box whose main network is not yet a MAINFH profile (sdn_rl without MAINFH
rows) the main network is the primary wlN and the others start at wlN.1 - the page had titled the guest as main,
called the IoT network a guest and filed the main network's clients under the backhaul. The layout now follows
MIGRATED; the cases below cover both, plus a scheduled network that is off.
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
# 2026-10-30 (field, GT-BE98: main + guest + IoT): a box is labelled with its Guest Network Pro type, not "Guest
# Network" for every network; the labels are the stock keys sdn.js uses, read from sdn_rl + apg<idx>_ssid
TYPEKEYS = ["Guest_Network", "GuestNetwork_Employee", "GuestNetwork_Portal", "GuestNetwork_Kid", "GuestNetwork_IoT",
            "GuestNetwork_VPN", "GuestNetwork_Customized", "WiFi_mlo_title", "GuestNetwork_Gaming"]
check("the type labels are the stock keys, in backticks", all(("`<#%s#>`" % k) in W for k in TYPEKEYS))
check("the profile list is read: sdn_rl and apg1..16 SSIDs through nvram_char_to_ascii",
      'nvram_char_to_ascii("","sdn_rl")' in W and len(set(re.findall(r'nvram_char_to_ascii\("","apg(\d+)_ssid"\)', W))) == 16)
check("the box shows its type tag; no blanket guest chip", "(n.type ? '<span class=\"tag\">' + hx(n.type)" in W
      and "(n.kind === 'guest'" not in W)
packs = [f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict"]
bad = [f + ":" + k for f in packs for k in TYPEKEYS
       if not re.search(r"(?m)^%s=\S" % k, open(os.path.join(www, f), encoding="utf-8", errors="replace").read())]
check("all 25 packs carry every type label", len(packs) == 25 and not bad, bad[:6])
# 2026-10-30 (field, GT-BE98 v3.6.2): the device name - yours first, the lease hostname after ("*" is none)
check("names resolve through ReaperNames with custom_clientlist, refreshed with the log (once a minute)",
      "name: nameOf(r[0], r[1], r[2])" in W and 'nvram_char_to_ascii("", "custom_clientlist")' in W
      and "ReaperNames.refresh(CUSTOM_CL" in W and "function load(){\n  names();" in W)
nm = re.search(r"\nfunction nameOf\(mac, ip, lease\)\{.*?\n\}\n", W, re.S)
check("nameOf() found", nm is not None)

m = re.search(r"\nvar RANK = .*?\n}\n(?=function netHtml\()", W, re.S)
check("nets() found", m is not None)
node = shutil.which("node")
if m and node:
    CASES = r"""
var out = {};
function cl(name, tag, vlan){ return {name: name, tag: tag, vlan: vlan || ''}; }
function view(ns){ return ns.map(function(n){ return [n.kind, n.name, n.type, n.vlan, n.bssid, n.list.map(function(c){ return c.name; })]; }); }
var VSSID = [["Home's \\", 'Guests', 'Old'], ['Home5', 'IoT', ''], ['', '', '', ''], ['Main3', 'Guests', 'Things']];
var VON = [['1', '1', '0'], ['1', '1', ''], ['0', '', ''], ['1', '1', '1']];
/* a migrated box: the main network is a MAINFH profile on wlN.1, wlN the hidden backhaul carrier */
var SDN_RL = '<3>MAINFH>1>0>0>1', NETTYPE = {}, HAS_PROF = false, MIGRATED = true, PSSID = ['', '', '', ''];
var HASH = '6b1c2a0f9e8d7c6b5a4f3e2d1c0b9a88';
out.ap = view(nets(0, [HASH, '0', '0', '-92', '6/20', 'AA:00', '12', 'AP'],
  [cl('node', 'Main BSS'), cl('phone', ''), cl('visitor', 'Guests', '52'), cl('tv', 'Lab', '60')]));
out.same = view(nets(1, ['Home5', '0', '0', '-92', '36/160', 'BB:00', '3', 'AP'], []));
out.off = view(nets(2, ['Primary', '0', '0', '-92', '37/320', 'CC:00', '1', 'AP'], [cl('phone', 'Main BSS')]));
out.bridge = view(nets(1, ['Upstream', '-60', '30', '-95', '36/160', 'BB:00', '3', 'Media Bridge'], []));
out.rep = view(nets(1, ['Upstream', '-60', '30', '-95', '36/160', 'BB:00', '3', 'Repeater ( SSID local: Home5 )'], [cl('phone', '')]));
/* a router with Guest Network Pro profiles: main + guest + IoT (the field case); a client on an unprofiled name */
SDN_RL = '<1>Guest>1>2>2>1<2>IoT>1>3>3>2<3>MAINFH>1>0>0>1'; NETTYPE = {Guests: 'GUEST', Things: 'IOT'}; HAS_PROF = true;
out.sdn = view(nets(3, ['Main3', '0', '0', '-92', '36/160', 'DD:00', '3', 'AP'], [cl('cam', 'Things', '53'), cl('x', 'Other')]));
/* NOT migrated (no MAINFH row - the field GT-BE98): main on the primary wlN, guest on wlN.1, IoT on wlN.2; httpd reads
   the radio SSID / BSSID from wlN.1 (the guest) and tags wlN's clients "Main BSS", wlN.1's "" */
MIGRATED = false; SDN_RL = '<1>Guest>1>2>2>1<2>IoT>1>3>3>2'; NETTYPE = {'Home-Guest': 'GUEST', 'Home-IoT': 'IOT'}; HAS_PROF = true;
PSSID = ['Home', '', '', '']; VSSID[0] = ['Home-Guest', 'Home-IoT', '']; VON[0] = ['1', '1', '0'];
out.un = view(nets(0, ['Home-Guest', '0', '0', '-92', '6/20', 'GG:00', '12', 'AP'], [cl('phone', 'Main BSS'), cl('tablet', '', '52'), cl('cam', 'Home-IoT', '53')]));
/* the IoT network on a schedule, off right now (wlN.2 disabled): no IoT box, nothing shifts */
VON[0] = ['1', '0', '0'];
out.sched = view(nets(0, ['Home-Guest', '0', '0', '-92', '6/20', 'GG:00', '12', 'AP'], [cl('phone', 'Main BSS')]));
/* not migrated and no profile list: everything from wlN.1 up is a guest network (the stock layout) */
NETTYPE = {}; HAS_PROF = false; VON[0] = ['1', '1', '0'];
out.unbare = view(nets(0, ['Home-Guest', '0', '0', '-92', '6/20', 'GG:00', '12', 'AP'], []));
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
        G = "<#Guest_Network#>"   # the token as the page source holds it (the dict fills it in on the router)
        check("AP: main (wlN.1 name) first, then the other networks in slot order, then a client-only network, backhaul last",
              o["ap"] == [["main", "Home's \\", "", "", "", ["phone"]], ["net", "Guests", G, "52", "", ["visitor"]],
                          ["net", "Lab", "", "60", "", ["tv"]], ["bh", "", "", "", "AA:00", ["node"]]], o["ap"])
        check("AP: the main box and an enabled network show with no clients; the radio BSSID goes to the main box it names",
              o["same"] == [["main", "Home5", "", "", "BB:00", []], ["net", "IoT", G, "", "", []]], o["same"])
        check("wlN.1 off: the primary is the main network (its clients, its name, its BSSID)",
              o["off"] == [["main", "Primary", "", "", "CC:00", ["phone"]]], o["off"])
        check("Media Bridge: no boxes", o["bridge"] == [], o["bridge"])
        check("Repeater: the local network (wlN.1) is the main box; no BSSID moved out of the radio facts",
              o["rep"] == [["main", "Home5", "", "", "", ["phone"]], ["net", "IoT", G, "", "", []]], o["rep"])
        check("profiles: main + guest + IoT each get their own box and label; an unprofiled name gets no guest label",
              o["sdn"] == [["main", "Main3", "", "", "DD:00", []], ["net", "Guests", "GUEST", "", "", []],
                           ["net", "Things", "IOT", "53", "", ["cam"]], ["net", "Other", "", "", "", ["x"]]], o["sdn"])
        check("not migrated (field GT-BE98): main is the primary wlN by its own name, then the guest on wlN.1, the IoT on "
              "wlN.2; the BSSID goes to the guest box whose SSID httpd read; no backhaul box",
              o["un"] == [["main", "Home", "", "", "", ["phone"]], ["net", "Home-Guest", "GUEST", "52", "GG:00", ["tablet"]],
                          ["net", "Home-IoT", "IOT", "53", "", ["cam"]]], o["un"])
        check("a scheduled network that is off has no box; the others keep their places",
              o["sched"] == [["main", "Home", "", "", "", ["phone"]], ["net", "Home-Guest", "GUEST", "", "GG:00", []]], o["sched"])
        check("not migrated, no profile list: wlN.1 and up are guest networks",
              o["unbare"] == [["main", "Home", "", "", "", []], ["net", "Home-Guest", G, "", "GG:00", []],
                              ["net", "Home-IoT", G, "", "", []]], o["unbare"])
    if nm and node:
        NAMES = r"""
var N = {'00:00:5e:00:53:01': 'Kitchen speaker'}, I = {'192.168.50.9': 'Office PC'};
var ReaperNames = {byMac: function(m, fb){ return N[String(m).toLowerCase()] || fb; }, byIp: function(ip, fb){ return I[ip] || fb; }};
console.log(JSON.stringify([nameOf('00:00:5E:00:53:01', '192.168.50.8', 'esp-1a2b'), nameOf('00:00:5e:00:53:02', '192.168.50.9', 'android-77'),
  nameOf('00:00:5e:00:53:03', '192.168.50.10', 'android-77'), nameOf('00:00:5e:00:53:04', '', '*'), nameOf('00:00:5e:00:53:05', '', '')]));
"""
        fd, jp = tempfile.mkstemp(suffix=".js"); os.close(fd)
        open(jp, "w", encoding="utf-8").write(nm.group(0) + NAMES)
        r = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
        try: got = json.loads(r.stdout)
        except ValueError: got = None
        check("names: your name over the device's own, by MAC then IP; the lease hostname only as the fallback; '*' is no name",
              got == ["Kitchen speaker", "Office PC", "android-77", "", ""], got or r.stderr[-200:])
elif not node:
    print("note: node not found - nets() run skipped")
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
