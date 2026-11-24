#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wireless > Settings, "Auto channel options": the four options are boxed switches whose text fits the column.

WHY THIS EXISTS. Owner report 2026-11-21 (v3.8.3 test image): the options showed as text running out of both
sides of the band column, with no checkbox to be seen. Cause: each option was a <label> holding a long stock
sentence ("Auto select channel including DFS channels") as its OWN text. The shell's label fitter
(www/reaper/fit.js) holds any LABEL of 60 characters or less that wraps to one line (nowrap + overflow hidden);
that label was a centred flex row, so the text was cut at both ends and the checkbox pushed out of sight.

WHAT IT DOES. Pins the replacement on the page source: each option is a <label class="sw"> with NO text of its
own (the short label sits in span.swl, the full sentence in the tooltip), the hidden input is still a checkbox
with the same data-g key (the read / dirty / mirror / apply code tests el.type==="checkbox"), the classes used are
not ones fit.js treats as controls, and the four short labels exist in every language pack and stay short.
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WWW = os.path.join(SRC, "www")
P = os.path.join(WWW, "Reaper_WiFiSettings.asp")
FIT = os.path.join(WWW, "reaper", "fit.js")
if not SRC or not os.path.isfile(P) or not os.path.isfile(FIT):
    print("SKIP: no router source tree with www/Reaper_WiFiSettings.asp and www/reaper/fit.js"); sys.exit(77)
page = open(P, encoding="utf-8", errors="replace").read()
fit = open(FIT, encoding="utf-8", errors="replace").read()

fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

# ---------------------------------------------------------------- the row's data
m = re.search(r'key:"acs",type:"chks".*?\n(?:\s*/\*.*?\*/\n)?\s*chk:(\{.*?\}\}),\n', page, re.S)
row = m.group(1) if m else ""
check("the Auto channel options row is found", bool(row))
ents = re.findall(r'\["(\w+)",`<#([\w-]+)#>`,`<#([\w-]+)#>`\]', row)
check("four options, each [setting, short label, full sentence]", len(ents) == 4 and row.count('["') == 4)
keys = [e[0] for e in ents]
check("the settings are acs_ch13, acs_dfs, acs_unii4, psc6g", keys == ["acs_ch13", "acs_dfs", "acs_unii4", "psc6g"])
shorts = [e[1] for e in ents]
check("the short labels are the page's own strings RWFP_140..143", shorts == ["RWFP_140", "RWFP_141", "RWFP_142", "RWFP_143"])
check("the full sentences are kept for the tooltips",
      [e[2] for e in ents] == ["WLANConfig11b_EChannel_acs_ch13", "WLANConfig11b_EChannel_dfs",
                               "WLANConfig11b_EChannel_U-NII-4", "RWFP_50"])

# ---------------------------------------------------------------- the cell markup
i = page.find('if(row.type==="chks"){')
cell = page[i:page.find("\n    }\n", i)] if i >= 0 else ""
check("the chks cell renderer is found", bool(cell))
check("each option is a label.sw with the full sentence as its title", "'<label class=\"sw\" title=\"'+esc(c[2])+'\">" in cell)
check("the input is still a checkbox carrying the setting in data-g",
      "<input type=\"checkbox\" data-g=\"'+c[0]+'\" data-nv=\"'+esc(g)+'\"" in cell)
check("the short label sits in its own span, after the switch track",
      "'<span class=\"trk\"></span><span class=\"swl\">'+esc(c[1])+'</span></label>'" in cell)
lab = re.search(r"'<label class=\\?\"sw\\?\".*?</label>'", cell, re.S)
own = re.sub(r"<span.*?</span>", "", re.sub(r"<input[^>]*>", "", lab.group(0))) if lab else "x" * 9
own = re.sub(r"'\+[^']*\+'|<label[^>]*>|</label>|'|\+|\s", "", own)
check("the label has no text of its own (fit.js only holds an element with own text)", own == "")
check("no option is rendered the old way", 'class="chk"' not in page and ".chk{" not in page and ".chk input{" not in page)

# ---------------------------------------------------------------- the styles
css = page[page.find("<style>"):page.find("</style>")]
sw = re.search(r"\n\.sw\{(.*?)\}", css, re.S)
check("the switch box fills the cell and may shrink (width 100%, min-width 0)",
      bool(sw) and "width:100%" in sw.group(1) and "min-width:0" in sw.group(1))
swl = re.search(r"\n\.sw \.swl\{(.*?)\}", css, re.S)
check("a long translation wraps inside the box instead of running out of it",
      bool(swl) and "white-space:normal" in swl.group(1) and "overflow-wrap:anywhere" in swl.group(1) and "min-width:0" in swl.group(1))
check("the real checkbox is hidden but stays focusable (not display:none)",
      bool(re.search(r"\n\.sw input\{[^}]*opacity:0[^}]*\}", css)) and not re.search(r"\n\.sw input\{[^}]*display:none", css))
check("on / off and keyboard focus are drawn from the checkbox state",
      ".sw input:checked+.trk{" in css and ".sw input:checked+.trk::after{" in css and ".sw input:focus-visible+.trk{" in css)

# ---------------------------------------------------------------- fit.js must not take these as controls
check("fit.js still decides by own text (the rule this fix relies on)",
      "ownText(el).length < 2) return false" in fit)
mc = re.search(r"var CTRL_CLS = /(.*?)/;", fit)
mt = re.search(r"var CTRL_TAG = /(.*?)/;", fit)
check("fit.js's control lists are found", bool(mc and mt))
if mc and mt:
    cls_re, tag_re = re.compile(mc.group(1).replace(r"\w", r"[A-Za-z0-9_]")), re.compile(mt.group(1))
    check("span.swl and span.trk are not control classes for fit.js", not cls_re.search("swl") and not cls_re.search("trk"))
    check("a SPAN is not a control tag for fit.js", not tag_re.search("SPAN"))

# ---------------------------------------------------------------- the strings
packs = sorted(f for f in os.listdir(WWW) if f.endswith(".dict") and f != "temp.dict")
check("language packs are present", len(packs) >= 25)
miss, longs = [], []
for f in packs:
    d = {}
    for ln in open(os.path.join(WWW, f), encoding="utf-8", errors="replace"):
        if ln.startswith("RWFP_14"):
            k, _, v = ln.rstrip("\r\n").partition("=")
            d[k] = v
    for k in shorts:
        if not d.get(k): miss.append(f + ":" + k)
        elif len(d[k]) > 24: longs.append("%s:%s=%d" % (f, k, len(d[k])))
check("every pack has the four short labels" + (" - missing " + ", ".join(miss[:6]) if miss else ""), not miss)
check("the short labels stay short (24 characters at most)" + (" - " + ", ".join(longs[:6]) if longs else ""), not longs)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
