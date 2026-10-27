#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Firewall / Policy Routing list saves travel in a POST body (BACKLOG "hosts-list paste", 2026-10-10).

WHY THIS EXISTS. Field report (RT-BE88U, v2.7.1): pasting an IP list into a Firewall object left the
GUI broken. The current handlers are bounded and never block httpd (the 2026-08-24 review and the
2026-10-10 re-read agree), but the page sent every list save as a GET query: the WHOLE object list,
URL-encoded. The CGI accepts up to 8191 characters per list; encodeURIComponent grows a pasted
IP/CIDR or domain list 1.2-3x; httpd reads the request line into a 10000-byte buffer and answers a
longer one with 400 before the handler runs. The page had already put the row in its table, so it
showed an object the router never stored. Saves now go in a POST body (64 KB post_buf), the editors
refuse an over-full list before changing the table, and a failed save reloads the router's lists.

WHAT IT DOES. Derives the trigger from the source's own numbers (httpd's line buffer, the CGI caps,
post_buf) with encodeURIComponent semantics, then pins the fix on both pages and the CGI registration.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] or REAPER_ROUTER_SRC)."""
import glob, os, re, sys
from urllib.parse import quote

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
need = ["httpd/httpd.c", "httpd/web.c", "www/Reaper_Firewall.asp", "www/Reaper_VPNRouting.asp"]
if not SRC or not all(os.path.isfile(os.path.join(SRC, p)) for p in need):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def enc(s):   # JavaScript encodeURIComponent
    return quote(s, safe="-_.!~*'()")

hc = read("httpd/httpd.c"); wc = read("httpd/web.c")
m = re.search(r"handle_request\(void\)\s*\{.*?char line\[(\d+)\]", hc, re.S)
LINE = int(m.group(1)) if m else 0
FWMAX = int(re.search(r"#define RFW_LIST_MAX\s+(\d+)", wc).group(1))
PBRMAX = int(re.search(r"#define RPBR_LIST_MAX\s+(\d+)", wc).group(1))
POSTBUF = int(re.search(r"static char post_buf\[(\d+)\]", wc).group(1))
check("source numbers found (httpd request line, list caps, post_buf)", LINE > 0 and FWMAX and PBRMAX and POSTBUF,
      (LINE, FWMAX, PBRMAX, POSTBUF))

# the trigger, from those numbers: a list the CGI accepts, as the page used to send it
cidrs = ",".join("10.%d.%d.0/24" % (i // 256, i % 256) for i in range(2000))
obj = "<pasted>cidr>" + cidrs
obj = obj[:FWMAX - 1]
get_line = "GET /reaper_fw.cgi?action=save&k=obj&v=%s&http_id=%s&_=1760000000000 HTTP/1.1\r\n" % (enc(obj), "x" * 32)
check("an object list the CGI accepts (%d chars) overran httpd's %d-byte request line as a GET (%d bytes)"
      % (len(obj), LINE, len(get_line)), len(obj) < FWMAX and len(get_line) > LINE)
smallest = next((n for n in range(200, FWMAX, 50) if len("GET /reaper_fw.cgi?action=save&k=obj&v=%s&http_id=%s HTTP/1.1\r\n"
                 % (enc(obj[:n]), "x" * 32)) > LINE), None)
print("     (with a CIDR paste the GET overran from ~%s characters - %d%% of the CGI's cap)" % (smallest, 100 * (smallest or 0) // FWMAX))
worst = 3 * max(FWMAX, PBRMAX) + 256
check("the POST body fits post_buf even fully percent-encoded (%d of %d bytes)" % (worst, POSTBUF), worst < POSTBUF)
check("both CGIs read POST bodies (do_html_post_and_get) and keep their http_id gate",
      '"reaper_fw.cgi*", "application/json", no_cache, do_html_post_and_get, do_reaper_fw_cgi, do_auth' in wc
      and '"reaper_pbr.cgi*", "application/json", no_cache, do_html_post_and_get, do_reaper_pbr_cgi, do_auth' in wc)

fw = read("www/Reaper_Firewall.asp")
check("Firewall: fwpost() is a url-encoded POST, token in the URL, one-shot completion",
      "function fwpost(q,body,cb){" in fw and "x.open('POST','/reaper_fw.cgi?'+q+'&http_id='+encodeURIComponent(REAPER_HTTPID)" in fw
      and "x.setRequestHeader('Content-Type','application/x-www-form-urlencoded');" in fw and "x.send(body);" in fw
      and "function fin(j){if(done)return;done=true;cb(j);}" in fw)
check("Firewall: no list save left in a GET query", "fwcgi('action=save" not in fw and fw.count("fwpost('action=save&k=") == 2)
check("Firewall: a failed save reloads the router's lists (no row that exists only in the page)",
      re.search(r"if\(j&&j\.ok\)\{RFW\.dirty=1;rfwPendingUI\(\);\}\s*/\*.*?\*/\s*else rfwLoad\(\);", fw, re.S) is not None
      and "if(bad_){ showSaved($('io_saved'),false,`<#RFW_155#>`); rfwLoad(); }" in fw)
add = fw[fw.find("$('ob_add').onclick"):fw.find("$('ob_cancel').onclick")]
check("Firewall: an over-full object list is refused before the table changes, the paste kept in the form",
      "if(rfwJoin(cand).length>=RFW_LIST_MAX)return bad(`<#RFW_328#>`);" in add
      and add.find("RFW_LIST_MAX)return bad") < add.find("editCommit('obj'") and "var RFW_LIST_MAX=%d;" % FWMAX in fw)

vr = read("www/Reaper_VPNRouting.asp")
check("Policy Routing: both helpers POST when given a body (url-encoded, token in the URL)",
      "function pbrcgi(q,cb,body){" in vr and "x.open(post?'POST':'GET','/reaper_pbr.cgi?'+q+'&http_id='" in vr
      and "function fwcgi(q,cb,body){" in vr and "x.open(post?'POST':'GET','/reaper_fw.cgi?'+q+'&http_id='" in vr
      and vr.count("if(post) x.setRequestHeader('Content-Type','application/x-www-form-urlencoded');") == 2
      and vr.count("x.send(post?body:null);") == 2)
check("Policy Routing: the rule list rides in the body on apply",
      "var q='action=apply&enable='+(masterOn?'1':'0'), qb='rulelist='+encodeURIComponent(serialize());" in vr
      and "}, qb);" in vr and "&rulelist='+encodeURIComponent" not in vr)
check("Policy Routing: the domain-list save rides in the body",
      "fwcgi('action=save&k=obj',function(j){" in vr and "}, 'v='+encodeURIComponent(joinList(OBJ)));" in vr)
sv = vr[vr.find("function objSave(){"):vr.find("function objDelete(k){")]
check("Policy Routing: an over-full object list is refused before the table changes",
      "if(joinList(cand).length>=8192){ objMsg(false, `<#RFW_328#>`); return; }" in sv
      and sv.find("joinList(cand).length>=8192") < sv.find("OBJ.push(rec)") and FWMAX == 8192)

packs = [x for x in glob.glob(os.path.join(SRC, "www", "*.dict")) if not x.endswith("temp.dict")]
miss = [os.path.basename(x) for x in packs if "RFW_328=" not in open(x, encoding="utf-8", errors="replace").read()]
check("RFW_328 in all 25 language packs, packs in lockstep",
      len(packs) == 25 and not miss and len({sum(1 for _ in open(x, "rb")) for x in packs}) == 1, miss)

here = os.path.dirname(os.path.abspath(__file__))
mk = os.path.join(here, "..", "verify_markers.txt")
if os.path.isfile(mk):
    t = open(mk, encoding="utf-8").read()
    check("verify_markers pins the POST helper on both pages",
          "www/Reaper_Firewall.asp|function fwpost(q,body,cb){|1" in t and "www/Reaper_VPNRouting.asp|function pbrcgi(q,cb,body){|1" in t)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
