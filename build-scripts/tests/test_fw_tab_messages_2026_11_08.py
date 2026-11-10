#!/usr/bin/env python3
"""Firewall page: each add row reports on its own tab (field report 2026-11-08, RT-BE88U v3.7.4_BETA).

"Firewall > Objects > Address groups: Add does nothing." The button did act: an IP typed as a member is refused
(members are address object NAMES), but every Objects / Zones / Egress / Forwards message went to #rf_saved,
which sits on the Rules tab - shown on a hidden tab, gone after 4 s. Now:
  - each add row carries its own line (rfs_obj ... rfs_icpt); rfwStat(list) picks it, falling back to rf_saved
  - initRfw: bad() writes to B, the add row in use, which every handler sets first; S stays rf_saved for the
    Rules tab (Preview, Apply / Settle, engine switch); a delete reports on its own tab
  - a group member that is not an address object is named (RFW_412, 25 packs); empty entries are dropped
The real gr_add handler is lifted out of the page and run under node.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_Firewall.asp")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
def rd(rel): return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

fw = rd("www/Reaper_Firewall.asp")

# ---------------------------------------------------------------- markup: one line per add row, on its own tab
tabs = {m.group(1): m.start() for m in re.finditer(r'<div class="tab" id="(tab_[a-z]+)">', fw)}
order = sorted(tabs.items(), key=lambda kv: kv[1])
def tab_of(pos):
    t = None
    for name, start in order:
        if start <= pos: t = name
    return t
want = {"obj": "tab_objects", "grp": "tab_objects", "svc": "tab_objects", "zone": "tab_zones", "zpol": "tab_zones",
        "edef": "tab_egress", "nat": "tab_nat", "icpt": "tab_nat"}
btn = {"obj": "ob", "grp": "gr", "svc": "sv", "zone": "zn", "zpol": "zp", "edef": "eg", "nat": "nt", "icpt": "ic"}
wrong = []
for lst, tab in want.items():
    span = '<button class="btn ghost sm cancel" id="%s_cancel"><#CTL_Cancel#></button><span class="saved hidden" id="rfs_%s"></span>' % (btn[lst], lst)
    if fw.count(span) != 1 or tab_of(fw.index(span)) != tab: wrong.append(lst)
check("8 add rows carry their own message line, each on its own tab", not wrong, wrong)
check("rf_saved stays on the Rules tab, once", fw.count('id="rf_saved"') == 1 and tab_of(fw.index('id="rf_saved"')) == "tab_rules")
check("an add-row line may wrap (a refusal names the entry)", ".addrow .saved:not(.hidden){white-space:normal;max-width:360px}" in fw)

# ---------------------------------------------------------------- script
check("rfwStat: the row's own line, rf_saved as the fallback",
      "function rfwStat(list){return $('rfs_'+list)||$('rf_saved');}" in fw)
check("initRfw: bad() writes to B; S stays the Rules tab line",
      "  var S=$('rf_saved'), B=S;\n  function bad(m){showSaved(B,false,m);}\n" in fw and "showSaved(S,false,m)" not in fw)
heads = {lst: ("  $('%s_add').onclick=function(){\n    B=rfwStat('%s');\n" % (btn[lst], lst)) for lst in ("obj", "grp", "svc", "zone", "edef", "nat", "zpol")}
heads["icpt"] = "    $('ic_add').onclick=function(){\n      B=rfwStat('icpt');\n"
check("every add handler points B at its own row first", all(fw.count(h) == 1 for h in heads.values()),
      [k for k, h in heads.items() if fw.count(h) != 1])
check("the Rules add handler points B back at rf_saved", "  $('rf_add').onclick=function(){\n    B=S;\n" in fw)
check("Preview / Settle still report on the Rules tab (S)", fw.count("showSaved(S,") >= 2)
saves = re.findall(r"rfwSave\('(\w+)',RFW\.\w+,([^)]*\)?)\)", fw)
stale = [k for k, el in saves if el == "$('rf_saved'" and k != "rules"]
check("no list but rules saves to rf_saved; handlers save to B", not stale and fw.count(",B);") == 8, (stale, fw.count(",B);")))
check("each delete reports on its own tab", all("rfwStat('%s'));}," % l in fw for l in ("obj", "grp", "svc", "zone", "zpol", "edef", "nat", "icpt")))
check("the group check names the member and keeps the 16 cap",
      "return bad(`<#RFW_412#>`.replace('%1',members[i]));" in fw and "members.length>16" in fw
      and "if(known.indexOf(members[i])<0)return bad(`<#RFW_67#>`)" not in fw)

# ---------------------------------------------------------------- packs
wd = os.path.join(SRC, "www")
dicts = sorted(f for f in os.listdir(wd) if f.endswith(".dict") and f != "temp.dict")
bad, lines = [], set()
for d in dicts:
    t = open(os.path.join(wd, d), encoding="utf-8").read()
    lines.add(t.count("\n"))
    m = re.search(r"^RFW_411=.+\n^RDSH_120=.+\n^RFW_412=(.+)$", t, re.M)
    if not m or t.count("\nRFW_412=") != 1 or "%1" not in m.group(1) or "`" in m.group(1) or "${" in m.group(1):
        bad.append(d)
check("all %d packs: RFW_412 after the RFW_411 / RDSH_120 pair, with %%1, safe in a template literal" % len(dicts),
      len(dicts) == 25 and not bad, bad)
check("packs stay in lockstep", len(lines) == 1, lines)
en = open(os.path.join(wd, "EN.dict"), encoding="utf-8").read()
check("EN wording", "\nRFW_412=%1 is not an address object. Add it under Address objects first, then use its name here.\n" in en)

# ---------------------------------------------------------------- node: the real gr_add handler
node = shutil.which("node")
h0 = fw.find("  $('gr_add').onclick=function(){\n")
h1 = fw.find("\n  };\n", h0)
if not node or h0 < 0 or h1 < 0:
    print("skip: node not found - the gr_add run" if not node else "")
    if h0 < 0 or h1 < 0: fails.append("gr_add handler not found")
else:
    body = fw[h0:h1 + 5]
    DICT = dict(l.split("=", 1) for l in en.splitlines() if "=" in l and not l.startswith("#"))
    body = re.sub(r"<#([A-Za-z0-9_]+)#>", lambda m: DICT.get(m.group(1), "<?" + m.group(1) + "?>"), body)
    js = r"""
var EL={}; function $(id){ return EL[id]||(EL[id]={id:id,value:'',onclick:null}); }
var RFW={obj:[['nas','cidr','192.168.2.50',''],['cam','cidr','192.168.2.60','']],grp:[]}, EDIT={grp:-1};
var LOG=[]; function rfwStat(l){ return 'rfs_'+l; } var S='rf_saved', B=S;
function bad(m){ LOG.push(['bad',B,m]); }
function rfwName(v){return /^[A-Za-z0-9_]{1,25}$/.test(v||'');}
function editCommit(l,rec){ RFW.grp.push(rec); LOG.push(['commit',l,rec]); return true; }
function rfwRenderGrp(){} function rfwFillSelects(){} function rfwSave(k,rows,el){ LOG.push(['save',k,el]); }
""" + body + r"""
function run(name, mem){ LOG=[]; B=S; $('gr_name').value=name; $('gr_mem').value=mem; $('gr_cmt').value=''; $('gr_add').onclick(); return LOG; }
var out={};
out.ip=run('lan_hosts','192.168.2.50');
out.two=run('lan_hosts','192.168.2.60, nas');
out.stray=run('cams',' cam , ');
out.empty=run('none',' , ');
console.log(JSON.stringify(out));
"""
    td = tempfile.mkdtemp()
    try:
        jp = os.path.join(td, "gr.js")
        open(jp, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, jp], capture_output=True, text=True, timeout=30)
        try: o = json.loads(r.stdout)
        except Exception: o = {}
        ip = o.get("ip", [])
        check("node: an IP as a member is refused on the group row, naming it",
              ip == [["bad", "rfs_grp", "192.168.2.50 is not an address object. Add it under Address objects first, then use its name here."]], (r.stderr, ip))
        check("node: the first non-object member of a list is the one named",
              o.get("two", [[None, None, ""]])[0][2].startswith("192.168.2.60 is not"), o.get("two"))
        st = o.get("stray", [])
        check("node: a stray comma is dropped, the group saves and reports on its own row",
              st == [["commit", "grp", ["cams", "cam", ""]], ["save", "grp", "rfs_grp"]], st)
        check("node: commas only = fill in a field, on the group row",
              o.get("empty") == [["bad", "rfs_grp", DICT.get("RFW_66", "?")]], o.get("empty"))
    finally:
        shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
