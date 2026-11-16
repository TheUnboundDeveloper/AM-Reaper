#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Several appGet hooks in one request are joined with %3B, never with a plain ';'.

WHY THIS EXISTS. httpd splits a request's parameters at '&' and at ';' alike (httpd/cgi.c init_cgi). A page that asks
for "hook=a();b()" therefore gets only a(): the rest becomes a parameter of its own and is dropped. Three Reaper
requests did that. The one that mattered was the shared device-name request (get_clientlist + reaper_devnames): the
Name / Hostname list was never produced on the router, so pages showed only the Devices-page names they start from,
and the dashboard Clients card - which had no such start - listed MAC addresses (owner report, 2026-11-16). The
OpenVPN server page read one status value out of four for the same reason. Stock code joins hooks with %3B.

WHAT IT DOES.
  1. Compiles httpd/cgi.c on the host and shows both facts with the real parser: a plain ';' cuts the hook value,
     %3B keeps it whole.
  2. Scans every page and script under www for an appGet request with a plain ';' between two hooks.
  3. Under node, with a stand-in web server that splits the request the way httpd does: the shared helper
     (www/reaper_util.js) receives both parts, and the dashboard card (www/Main_ReaperDash.asp) labels each device
     Name, else Hostname, else MAC - through the helper, with no request of its own.
  4. The OpenVPN server page's status request reaches httpd with all four values.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "cgi.c")):
    print("SKIP: no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)"); sys.exit(77)

fails = []
def check(label, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        fails.append(label + ((": " + str(detail)) if detail else ""))

def rd(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="replace").read()

OLD_REQ = "hook=get_clientlist();reaper_devnames()&_=1"
NEW_REQ = "hook=get_clientlist()%3Breaper_devnames()&_=1"

# ------------------------------------------------------------------ 1. the real parser
cgi = rd("httpd/cgi.c")
check("httpd/cgi.c: a request's parameters end at '&' and at ';'", 'while (strsep(&q, "&;"))' in cgi)
cc = shutil.which("gcc") or shutil.which("cc")
if not cc:
    print("note: no host C compiler - the parser was checked by its source only")
else:
    w = tempfile.mkdtemp(prefix="rcgi_")
    try:
        open(os.path.join(w, "json.h"), "w").write(r'''#ifndef T_JSON_H
#define T_JSON_H
typedef struct json_object json_object;
enum json_type { json_type_null, json_type_boolean, json_type_double, json_type_int, json_type_object, json_type_array, json_type_string };
static inline int json_object_get_type(const json_object *o){ return 0; }
static inline int json_object_object_length(const json_object *o){ return 0; }
static inline int json_object_object_get_ex(const json_object *o, const char *k, json_object **v){ return 0; }
static inline int json_object_is_type(const json_object *o, int t){ return 0; }
static inline const char *json_object_to_json_string(json_object *o){ return ""; }
static inline const char *json_object_get_string(json_object *o){ return ""; }
static inline int json_object_get_int(const json_object *o){ return 0; }
static inline int json_object_object_add(json_object *o, const char *k, json_object *v){ return 0; }
static inline json_object *json_object_new_string(const char *s){ return 0; }
#endif
''')
        for h in ("rtconfig.h", "shared.h"):
            open(os.path.join(w, h), "w").write("/* test stand-in */\n")
        shutil.copy(os.path.join(SRC, "httpd", "cgi.c"), os.path.join(w, "cgi_under_test.c"))
        open(os.path.join(w, "t.c"), "w").write(r'''#include "cgi_under_test.c"
int main(int argc, char **argv)
{
	char *q = strdup(argv[1]), *v;

	init_cgi(q);
	v = get_cgi("hook");
	printf("%s\n", v ? v : "(none)");
	return 0;
}
''')
        exe = os.path.join(w, "t")
        r = subprocess.run([cc, "-w", "-I", w, "-o", exe, os.path.join(w, "t.c")], capture_output=True, text=True)
        check("httpd/cgi.c compiles on the host", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            T = lambda a: subprocess.run([exe, a], capture_output=True, text=True, timeout=20).stdout.strip()
            check("the real parser: a plain ';' ends the hook value - the second hook is lost", T(OLD_REQ) == "get_clientlist()", T(OLD_REQ))
            check("the real parser: %3B keeps both hooks in the value", T(NEW_REQ) == "get_clientlist();reaper_devnames()", T(NEW_REQ))
    finally:
        shutil.rmtree(w, ignore_errors=True)

# ------------------------------------------------------------------ 2. no page joins hooks with a plain ';'
RAW = re.compile(r"appGet\.cgi\?hook=[^'\"` ]*\);[A-Za-z_]+\(")
bad = []
for root, dirs, files in os.walk(os.path.join(SRC, "www")):
    for fn in files:
        if not fn.endswith((".asp", ".js", ".htm", ".html")):
            continue
        p = os.path.join(root, fn)
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "appGet.cgi?hook=" in t and RAW.search(t):
            bad.append(os.path.relpath(p, SRC))
check("no page or script under www joins appGet hooks with a plain ';'", not bad, ", ".join(sorted(bad)[:8]))

# ------------------------------------------------------------------ static shape of the three fixed requests
ut = rd("www/reaper_util.js")
dash = rd("www/Main_ReaperDash.asp")
vs = rd("www/Reaper_VPNServer.asp")
check("shared helper: one request, the two hooks joined with %3B", ut.count("'/appGet.cgi?hook=get_clientlist()%3Breaper_devnames()&_='") == 1)
i, j = dash.find("function pollClients(){"), dash.find("/* v3.1.6: the same tiles on a box that is not routing.")
poll = dash[i:j] if 0 < i < j else ""
check("dashboard: the Clients card poller is found", bool(poll))
check("dashboard: the card has no name request or lookup of its own", "reaper_devnames" not in dash and "XMLHttpRequest" not in poll and "appGet.cgi" not in poll)
check("dashboard: the card asks the shared helper, seeded with the Devices-page names",
      "ReaperNames.refresh('<% nvram_char_to_ascii(\"\", \"custom_clientlist\"); %>',function(cl){" in poll and "ReaperNames.byMac(macs[i],macs[i])" in poll)
check("dashboard: the shared helper's script is loaded by the page", '<script src="/reaper_util.js"></script>' in dash)
check("OpenVPN server page: the four status values are joined with %3B",
      "hook=nvram_get(vpn_server1_state)%3Bnvram_get(vpn_server1_errno)%3Bnvram_get(vpn_server2_state)%3Bnvram_get(vpn_server2_errno)'" in vs)

# ------------------------------------------------------------------ 3 + 4. the pages against a server that splits like httpd
node = shutil.which("node")
if not node:
    print("note: node not found - the pages were checked statically only")
elif poll:
    A, B, C, D, E = ("00:00:5E:00:53:%02X" % n for n in (1, 2, 3, 4, 5))
    fixture = {
        "cl": {"maclist": [A, B, C, D, E],
               A: {"isOnline": "1", "isWL": "4", "ip": "192.0.2.11", "ip6": "2001:db8::11"},
               B: {"isOnline": "1", "isWL": "2", "ip": "192.0.2.12"},
               C: {"isOnline": "1", "isWL": "0", "ip": "192.0.2.13"},
               D: {"isOnline": "0", "isWL": "1", "ip": "192.0.2.14"},
               E: {"isOnline": "1", "isWL": "1", "ip": "192.0.2.15"}},
        "dn": {A: {"n": "Den-PC", "h": "DESKTOP-EXAMPL1", "ip": "192.0.2.11"},
               B: {"n": "", "h": "Tablet-Example", "ip": "192.0.2.12"},
               E: {"n": "", "h": "", "ip": "192.0.2.15"}},
        # the Devices-page list as the page receives it: <name>MAC>group>type>...
        "custom": "<Den-PC>%s>0>0>>>><Shed-Cam>%s>0>0>>>>" % (A, C),
        "macs": [A, B, C, D, E],
    }
    m = re.search(r"xget\('(/appGet\.cgi\?hook=nvram_get\(vpn_server1_state\)[^']*)'", vs)
    fixture["vpn_url"] = m.group(1) if m else ""
    js = r'''
var fs = require('fs'), vm = require('vm');
var F = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
var URLS = [];
/* the web server's side: parameters end at '&' and at ';', then %xx and '+' are decoded (httpd/cgi.c) */
function httpdQuery(url){
  var q = url.split('?')[1] || '', out = {};
  q.split(/[&;]/).forEach(function(a){
    var u = a.replace(/\+/g, ' ').replace(/%([0-9a-fA-F]{2})/g, function(_, h){ return String.fromCharCode(parseInt(h, 16)); });
    var i = u.indexOf('='); if(i >= 0) out[u.slice(0, i)] = u.slice(i + 1);
  });
  return out;
}
function XHR(){ this.readyState = 0; this.status = 0; }
XHR.prototype.open = function(m, u){ this._u = u; URLS.push(u); };
XHR.prototype.send = function(){
  var o = {};
  (httpdQuery(this._u).hook || '').split(';').forEach(function(f){
    if(f === 'get_clientlist()') o.get_clientlist = F.cl;
    else if(f === 'reaper_devnames()') o.reaper_devnames = F.dn;
  });
  this.readyState = 4; this.status = 200; this.responseText = JSON.stringify(o);
  if(this.onreadystatechange) this.onreadystatechange();
};
global.window = global; global.XMLHttpRequest = XHR;
global.document = { addEventListener: function(){}, getElementById: function(){ return null; }, querySelectorAll: function(){ return []; } };
vm.runInThisContext(fs.readFileSync(process.argv[3], 'utf8'));
var painted = null;
global.paintClients = function(b){ painted = b; };
var poll = fs.readFileSync(process.argv[4], 'utf8').split('<% nvram_char_to_ascii("", "custom_clientlist"); %>').join(encodeURIComponent(F.custom));
vm.runInThisContext(poll);
pollClients();
var names = function(k){ return (painted && painted[k] || []).map(function(r){ return r.n; }); };
console.log(JSON.stringify({
  urls: URLS,
  model_old: httpdQuery('/appGet.cgi?hook=get_clientlist();reaper_devnames()&_=1').hook,
  g6: names('6'), g5: names('5'), g24: names('24'), eth: names('eth'),
  rows6: painted ? painted['6'] : null,
  helper_host: ReaperNames.host(F.macs[0]), helper_name: ReaperNames.name(F.macs[0]), by_ip: ReaperNames.byIp('192.0.2.12', ''),
  vpn_hook: httpdQuery(F.vpn_url).hook || ''
}));
'''
    w = tempfile.mkdtemp(prefix="rhook_")
    try:
        pj, pf, pp = os.path.join(w, "t.js"), os.path.join(w, "f.json"), os.path.join(w, "poll.js")
        open(pj, "w").write(js); open(pf, "w").write(json.dumps(fixture)); open(pp, "w").write(poll)
        r = subprocess.run([node, pj, pf, os.path.join(SRC, "www", "reaper_util.js"), pp], capture_output=True, text=True, timeout=60)
        check("node: the helper and the dashboard poller run", r.returncode == 0 and r.stdout.strip().startswith("{"), (r.stderr or r.stdout)[-800:])
        if r.returncode == 0 and r.stdout.strip().startswith("{"):
            o = json.loads(r.stdout.strip().splitlines()[-1])
            check("the stand-in server loses the second hook after a plain ';', as httpd does", o["model_old"] == "get_clientlist()", o["model_old"])
            check("one request per tick, with no plain ';' in it", len(o["urls"]) == 1 and ";" not in o["urls"][0], o["urls"])
            check("the Name / Hostname list arrives in the helper", o["helper_name"] == "Den-PC" and o["helper_host"] == "DESKTOP-EXAMPL1" and o["by_ip"] == "Tablet-Example", o)
            check("card: a device with a Name shows the Name", o["g6"] == ["Den-PC"], o["g6"])
            check("card: a device with no Name shows the Hostname the router sent", o["g5"] == ["Tablet-Example"], o["g5"])
            check("card: a device the router sent no names for keeps its Devices-page Name", o["eth"] == ["Shed-Cam"], o["eth"])
            check("card: a device with neither shows its MAC; an offline device is not listed", o["g24"] == [E], o["g24"])
            r6 = (o["rows6"] or [{}])[0]
            check("card: the row keeps its addresses", r6.get("ip") == "192.0.2.11" and r6.get("ip6") == "2001:db8::11" and r6.get("m") == A, r6)
            check("OpenVPN server page: all four status values reach httpd",
                  o["vpn_hook"] == "nvram_get(vpn_server1_state);nvram_get(vpn_server1_errno);nvram_get(vpn_server2_state);nvram_get(vpn_server2_errno)", o["vpn_hook"])
    finally:
        shutil.rmtree(w, ignore_errors=True)

if fails:
    print("FAIL test_appget_hook_separator (%d)" % len(fails))
    for f in fails:
        print("  - " + f[:900])
    sys.exit(1)
print("PASS test_appget_hook_separator")
