#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The apply-token hook keeps a space a space (field report 2026-11-16: an SSID saved as "My+Wifi+Network").

WHY THIS EXISTS. httpd adds a script to every stock page that puts the session token into each save
(httpd/reaper_inject.c, REAPER_TOKEN_TAIL). For a JSON body it decodes the body, adds http_id and encodes it again.
The stock pages save through jQuery, which sends a form-encoded body with every space written as "+". The hook
decoded with decodeURIComponent, which leaves "+" alone, and encoded again, which made it "%2B": the router then
stored a literal "+" for every space (a network name, a service list such as "restart_sdn 4"). The hook now reads
"+" as a space before it decodes.

WHAT IT DOES. Takes the hook out of the C source, runs it under node with a stub page, sends a save the way jQuery
does ("+") and the way a plain encodeURIComponent body does ("%20"), decodes the result the way httpd does and
compares every value. A copy of the hook without the fix must reproduce the fault (the test can see it).
Exit 0 pass, 1 fail, 77 skipped (no router tree, or no node).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
INJ = os.path.join(SRC, "httpd", "reaper_inject.c") if SRC else ""
if not INJ or not os.path.isfile(INJ):
    print("SKIP: no router source tree"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(INJ, encoding="utf-8").read()
BS = chr(92)
FIX_C = "decodeURIComponent(s.replace(/" + BS + BS + "+/g,'%20'))"     # the C source text (two backslashes)
check("the hook reads '+' as a space before it decodes a JSON body", src.count(FIX_C) == 1, src.count(FIX_C))
check("the bare decode is gone", "if(enc)s=decodeURIComponent(s);" not in src)

def c_string(macro):
    """the JS a C macro of adjacent string literals stands for"""
    m = re.search(r"#define " + macro + r"\b(.*?)\n(?!\t\")", src, re.S)
    lits = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1)) if m else []
    out = []
    for lit in lits:
        out.append(re.sub(r"\\(.)", lambda k: {"n": "\n", "t": "\t"}.get(k.group(1), k.group(1)), lit))
    return "".join(out)

head, tail = c_string("REAPER_TOKEN_HEAD"), c_string("REAPER_TOKEN_TAIL")
check("the hook is found in the source", head.startswith("<script>") and tail.endswith("</script>") and "function add(b)" in tail,
      (head[:30], tail[-30:]))
FIX_JS = "decodeURIComponent(s.replace(/" + BS + "+/g,'%20'))"
check("the JS the browser gets holds the pattern /\\+/g", FIX_JS in tail)

node = shutil.which("node")
if not node:
    print("note: node not found - the hook was checked statically only")
elif head.startswith("<script>") and tail.endswith("</script>"):
    def harness(js_tail):
        hook = head[len("<script>"):] + "TOK123" + js_tail[:-len("</script>")]
        return r'''
var sent = [];
function XMLHttpRequest(){}
XMLHttpRequest.prototype.open = function(m, u){ this.m = m; this.u = u; };
XMLHttpRequest.prototype.send = function(b){ sent.push(b); };
function HTMLFormElement(){}
HTMLFormElement.prototype.submit = function(){};
var location = {href: 'http://192.0.2.1/SDN.asp', host: '192.0.2.1'};
var document = {
  addEventListener: function(){},
  createElement: function(){ var a = {}; Object.defineProperty(a, 'href', {set: function(v){
    var p = String(v).replace(/^https?:\/\/[^\/]+/, ''); this.host = '192.0.2.1'; this.pathname = p.split('?')[0]; }}); return a; }
};
var window = {};
''' + hook + r'''
function httpd(b){ return JSON.parse(decodeURIComponent(String(b).replace(/\+/g, '%20'))); }   /* '+' = space, %XX decoded */
var data = {apg1_ssid: 'My Wifi Network', odd: "a+b & 50% it's", rc_service: 'restart_wireless;restart_sdn 4', action_mode: 'apply'};
var plain = encodeURIComponent(JSON.stringify(data));          /* a body as httpApi.js builds it */
var jq = plain.replace(/%20/g, '+');                           /* what jQuery's $.ajax then sends */
var out = {};
[['jq', jq], ['plain', plain]].forEach(function(c){
  var x = new XMLHttpRequest(); x.open('POST', '/applyapp.cgi'); x.send(c[1]);
  try { out[c[0]] = httpd(sent[sent.length - 1]); } catch (e) { out[c[0]] = {err: String(e)}; }
  out[c[0] + '_raw'] = String(sent[sent.length - 1]);
});
var x2 = new XMLHttpRequest(); x2.open('POST', '/start_apply.htm'); x2.send('a=1&b=x+y'); out.form = String(sent[sent.length - 1]);
var x3 = new XMLHttpRequest(); x3.open('POST', '/other.cgi'); x3.send(jq); out.other = String(sent[sent.length - 1]) === jq;
var x4 = new XMLHttpRequest(); x4.open('POST', '/applyapp.cgi'); x4.send(null); out.empty = String(sent[sent.length - 1]);
console.log(JSON.stringify(out));
'''
    def run(js):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js); p = f.name
        try:
            r = subprocess.run([node, p], capture_output=True, text=True, timeout=30)
            return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"err": r.stderr[-400:]}
        except Exception as e:
            return {"err": str(e)}
        finally:
            os.unlink(p)

    want = {"apg1_ssid": "My Wifi Network", "odd": "a+b & 50% it's", "rc_service": "restart_wireless;restart_sdn 4",
            "action_mode": "apply", "http_id": "TOK123"}
    o = run(harness(tail))
    check("a jQuery save ('+' for spaces): every value arrives as typed, with the token", o.get("jq") == want, o.get("jq") or o)
    check("a plain encoded save ('%20'): every value arrives as typed, with the token", o.get("plain") == want, o.get("plain"))
    check("the body the hook sends holds no literal plus for a space (%2B only for a typed '+')",
          o.get("jq_raw", "").count("%2B") == 1 and "My%2BWifi" not in o.get("jq_raw", "x"), o.get("jq_raw", "")[:160])
    check("a form body only gains the token", o.get("form") == "a=1&b=x+y&http_id=TOK123", o.get("form"))
    check("a save to another address is not touched", o.get("other") is True)
    check("an empty body becomes the token alone", o.get("empty") == "http_id=TOK123", o.get("empty"))
    # negative control: the hook as it was (2026-11-03 .. 2026-11-16) reproduces the report
    old = run(harness(tail.replace(FIX_JS, "decodeURIComponent(s)")))
    check("control: without the fix the same save stores 'My+Wifi+Network' (the test sees the fault)",
          (old.get("jq") or {}).get("apg1_ssid") == "My+Wifi+Network", old.get("jq") or old)

print("\n%d failure(s)" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
