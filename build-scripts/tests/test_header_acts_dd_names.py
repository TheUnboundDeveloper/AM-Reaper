#!/usr/bin/env python3
"""Header buttons hold still on a phone; DNS Director rules show device names (owner, 2026-10-31).

WHY (header). On an iPhone 17 in portrait the Reboot and Logout buttons bounced and changed size as the dashboard
updated. fit.js shares a container's overflow among the labels inside it, and on the dashboard the header's nearest
clipping ancestor is the page body (overflow-x:hidden): any live tile that spilled past the phone screen for a
moment shrank the two buttons to fit.js's 36 px floor, and the next pass sprang them back. The first header line
was also exactly full (logo + "?"), so a few pixels of difference moved the buttons to another row. Measured in the
mock with WebKit at 402 x 874 (scratchpad hdr/stress.js): before, every disturbance moved them; after, none does.

WHAT IT DOES (header). On the dashboard and the shell, "?" / Reboot / Logout sit in one group (.acts) marked
data-rfit-keep: it wraps as a unit, fit.js never squeezes it for another element's overflow, and on a phone
(<= 430 px) it takes its own row with Reboot / Logout splitting it evenly (flex-basis 0), cut by CSS when a
translation is longer than its half.

WHY / WHAT (DNS Director). Per-device rules showed only the MAC. Each row now shows the device's name beside it:
ReaperNames (the user's own custom_clientlist name, kept for an offline device, then the live networkmap name),
then the name a stock-era rule carries; blank only when none exists. Names are client-chosen text, so they are set
with textContent, never markup, and re-run once the live names load.
"""
import os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "reaper", "fit.js")):
    print("SKIP: no router source tree with www/reaper/fit.js (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

f = rd("www", "reaper", "fit.js")
fc = f[f.find("function fitContainers"):f.find("function pass(")]
check("fit.js: a data-rfit-keep group is skipped by the container fit",
      "if (el.closest && el.closest('[data-rfit-keep]')) continue;" in fc)

def group(page, html):
    m = re.search(r'<div class="acts" data-rfit-keep>(.*?)</div>', html, re.S)
    body = m.group(1) if m else ""
    check(page + ": ? / Reboot / Logout are one data-rfit-keep group, in that order",
          m is not None and 0 <= body.find('id="btn_guide"') < body.find('id="btn_reboot"') < body.find('id="btn_logout"'))
    return m

d = rd("www", "Main_ReaperDash.asp")
group("dashboard", d)
check("dashboard: the group never grows or shrinks with the row",
      ".acts{display:flex;align-items:center;gap:inherit;flex:0 0 auto}" in d)
m430 = d[d.find("@media (max-width:430px)"):]
m430 = m430[:m430.find("\n}") + 2]
check("dashboard phone: own row, Reboot / Logout split it evenly, cut by CSS, ? keeps its size",
      ".acts{flex:1 1 100%}" in m430 and ".acts .btn{flex:1 1 0;min-width:0;overflow:hidden;text-overflow:ellipsis}" in m430
      and ".acts #btn_guide{flex:0 0 auto}" in m430, m430)

sh = rd("www", "reaper_shell.asp")
group("shell", sh)
check("shell: the group never grows or shrinks with the row",
      ".top .acts{display:flex;align-items:center;gap:inherit;flex:0 0 auto}" in sh)
s430 = sh[sh.find("@media (max-width:430px)"):]
s430 = s430[:s430.find("\n}") + 2]
check("shell phone: own row, Reboot / Logout split it evenly, cut by CSS, ? keeps its size",
      ".top .acts{flex:1 1 100%}" in s430 and ".top .acts .btn{flex:1 1 0;min-width:0;overflow:hidden;text-overflow:ellipsis" in s430
      and ".top .acts #btn_guide{flex:0 0 auto}" in s430, s430)
check("the buttons keep their ids (the logout / reboot handlers find them)",
      all(("id=\"%s\"" % i) in d and ("id=\"%s\"" % i) in sh for i in ("btn_guide", "btn_reboot", "btn_logout")))

dn = rd("www", "Reaper_DNS.asp")
check("DNS Director: a Device column before the MAC",
      "<thead><tr><th><#Clientlist_device#></th><th><#MAC_Address#></th><th><#RDNS_23#></th><th></th></tr></thead><tbody id=\"ddtbody\">" in dn)
check("DNS Director: each row has a name cell; the empty row spans all four columns",
      "'<tr><td class=\"ddnm\" data-i=\"' + i + '\"></td><td class=\"mono\">' + hx(r.mac) + '</td>" in dn
      and '<tr><td colspan="4" class="empty">' in dn)
nm = dn[dn.find("function ddNames(){"):]
nm = nm[:nm.find("\n}") + 2]
check("DNS Director: name = ReaperNames (custom, then live), then the stock-era rule name, else blank",
      "var nm = ReaperNames.byMac(r.mac, '') || r.name || '';" in nm, nm)
check("DNS Director: a name goes in as text, never markup",
      "td.textContent = nm;" in nm and "innerHTML" not in nm)
check("DNS Director: names drawn with every redraw and again once the live names load",
      "ddNames();\n  ddPickDraw();" in dn and "DD_DEVS = out; ddNames(); ddPickDraw();" in dn)
check("DNS Director: stored rules are unchanged (no name written into dnsfilter_rulelist)",
      "DDL.push({name: '', mac: mac, mode: q('s_ddnew').value});" in dn)
check("edited files stay ASCII", all(ord(c) < 128 for c in d + sh + dn + f))

node = shutil.which("node")
if node:
    r = subprocess.run([node, "--check", os.path.join(SRC, "www", "reaper", "fit.js")], capture_output=True, text=True)
    check("fit.js parses (node --check)", r.returncode == 0, r.stderr[-300:])
print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
