#!/usr/bin/env python3
"""System Info shows "off" for a radio that is off, not "<i>off</i>" (field report, GT-BE98 v3.6.1, 2026-10-29).

WHY. httpd sysinfo.c answers conn.wifi.N.* with the literal markup "<i>off</i>" when the radio is off (count -1).
The stock page put it into innerHTML; Reaper_Sysinfo.asp escapes every count, so the tags showed as text in the
Wireless clients table. wlCount() shows the translated word (RDSH_49, the dashboard's "off") for that one value
and keeps escaping everything else.

WHAT IT DOES. Source checks on Reaper_Sysinfo.asp (all three counts go through wlCount, none through a bare esc),
that httpd still sends that markup and that RDSH_49 is in all 25 packs; then runs esc() + wlCount() from the page
under node: the off markup becomes the label, numbers pass through, any other markup stays escaped.
"""
import json, os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_Sysinfo.asp")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="replace").read()

t = rd("www", "Reaper_Sysinfo.asp")
check("all three client counts go through wlCount()", t.count("wlCount(a[0])") == 1 and t.count("wlCount(a[1])") == 1
      and t.count("wlCount(a[2])") == 1)
check("no client count is escaped raw any more", not re.search(r"esc\(a\[[0-2]\]\)", t))
check("httpd still answers an off radio with the <i>off</i> markup (what wlCount matches)",
      'strcpy(result,"<i>off</i>");' in rd("httpd", "sysinfo.c"))
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict")
missing = [f for f in packs if not re.search(r"(?m)^RDSH_49=\S", open(os.path.join(www, f), encoding="utf-8", errors="replace").read())]
check("RDSH_49 is in all %d packs" % len(packs), len(packs) == 25 and not missing, missing)

m_esc = re.search(r"function esc\(s\)\{.*?\}\);\}\n", t, re.S)
m_wl = re.search(r"function wlCount\(v\)\{\n.*?\n\}\n", t, re.S)
check("esc() and wlCount() found in the page", bool(m_esc and m_wl))
node = shutil.which("node")
if m_esc and m_wl and node:
    js = (m_esc.group(0) + m_wl.group(0)).replace("`<#RDSH_49#>`", "'OFF_LABEL'")
    js += ("console.log(JSON.stringify(['<i>off</i>', '<I> off </I>', '0', '12', '<b>x</b>', 'a\"b', '', null]"
           ".map(wlCount)));\n")
    r = subprocess.run([node, "-e", js], capture_output=True, text=True)
    check("wlCount runs under node", r.returncode == 0, r.stderr[-300:])
    if r.returncode == 0:
        o = json.loads(r.stdout.strip().splitlines()[-1])
        want = ['<span class="sub">OFF_LABEL</span>', '<span class="sub">OFF_LABEL</span>', '0', '12',
                '&lt;b&gt;x&lt;/b&gt;', 'a&quot;b', '', '']
        check("off markup -> label, numbers unchanged, other markup escaped", o == want, o)
elif not node:
    print("note: node not found - the runtime check is skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
