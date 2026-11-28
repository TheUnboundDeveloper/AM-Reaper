#!/usr/bin/env python3
"""A User-Agent that names the ASUS phone app earns nothing by itself (REAPER-NOAPP, review 2026-11-24).

The app is not a supported way to manage a Reaper router (owner, 2026-11-21) and nothing in an image sends its
User-Agent; any client can claim it. Before this change such a request skipped the cross-site refusal, the Referer
rule, the per-boot page token on an apply, and the "an apply is a POST" rule on apply.cgi.

2026-11-28 (REAPER-APP-OPTIN, field request): the admin may switch an exemption on (off at factory). The five places
then read ONE per-request decision, reaper_req_app - the switch, the app's User-Agent kind and a peer on the main
network together - and never the User-Agent alone. test_app_optin_20261128.py tests that decision; this test keeps
pinning that no place looks at the app flag on its own.

Checked in httpd.c / web.c of the tree:
  - the cross-site refusal is skipped only by reaper_req_app, never by the app flag;
  - the Referer rule of a page is looked up for every request, outside the browser-only block, and the two closed
    Referer checks are told "this is the app" only when reaper_req_app is set;
  - reaper_apply_token_ok() does not read the User-Agent;
  - apply.cgi refuses an apply by GET for every User-Agent (reaper_req_app aside);
  - what is left alone on purpose is still there (the app's reply headers and login reply, the browser-only
    lock page) - a change there belongs to its own review.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "httpd.c")):
    print("SKIP: no router source tree with httpd/httpd.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

hc = rd("httpd", "httpd.c"); wc = rd("httpd", "web.c")

# ---- cross-site refusal
check("cross-site refusal: called once; only the opt-in decision stands in front of it, never the app flag",
      hc.count("if (!reaper_req_app && reaper_xsite_cgi_refused(url, file, method, sec_fetch_site, useragent, do_ssl)) {") == 1
      and hc.count("reaper_xsite_cgi_refused(url,") == 1
      and "fromapp && reaper_xsite_cgi_refused" not in hc)

# ---- Referer rule
blk = re.search(r"\n\tif\(!fromapp\) \{\n#endif\n(.*?)\n\t\}\n", hc, re.S)
check("the browser-only block (lock page, login state) is found", blk is not None)
body = blk.group(1) if blk else ""
check("...and it no longer holds the Referer rule lookup", "mime_referers" not in body and "do_referer" not in body, body[-300:])
loop = hc.find("\tfor (doreferer = &mime_referers[0]; doreferer->pattern; doreferer++) {\n")
check("the Referer rule lookup is at function level (one tab), after that block and before the exception table",
      blk is not None and loop > blk.end() - 1 and loop < hc.find("\tfor (exhandler = &except_mime_handlers[0]; exhandler->pattern; exhandler++) {")
      and hc.count("for (doreferer = &mime_referers[0]") == 1)
check("do_referer is still cleared before the lookup", 0 < hc.find("\tdo_referer = 0;\n") < loop)
check("the rule is dropped after the lookup only for a request the opt-in applies to",
      hc.count("\tif (reaper_req_app)\t/* REAPER-APP-OPTIN: the app sends no Referer */\n\t\tdo_referer = 0;\n") == 1
      and loop < hc.find("\tif (reaper_req_app)\t/* REAPER-APP-OPTIN: the app sends no Referer */") < hc.find("\tfor (exhandler = &except_mime_handlers[0]")
      and len(re.findall(r"\bdo_referer = 0;", hc)) == 2)
check("the closed Referer checks get the app flag only with the opt-in decision, 0 otherwise",
      hc.count("referer_check(referer, reaper_req_app ? fromapp : 0);") == 1
      and hc.count("check_noauth_referrer(referer, reaper_req_app ? fromapp : 0);") == 1
      and "referer_check(referer, fromapp)" not in hc and "check_noauth_referrer(referer, fromapp)" not in hc)

# ---- page token and POST-only
m = re.search(r"\nstatic int reaper_apply_token_ok\(const char \*hid, const char \*where\)\n\{.*?\n\}\n", wc, re.S)
tok = m.group(0) if m else ""
check("page token: reaper_apply_token_ok() does not read the User-Agent", bool(tok) and "check_user_agent" not in tok and "user_agent" not in tok)
check("...and still compares the request's http_id with the router's", 'want = nvram_safe_get("http_id");' in tok and "strcmp(hid, want) == 0" in tok)
check("...and is still asked on start_apply and apply.cgi", wc.count("!reaper_apply_token_ok(") == 2)
check("apply.cgi: an apply by GET is refused for every User-Agent (the opt-in decision aside)",
      'if (!strcmp(action_mode, "apply") && !reaper_req_app && reaper_apply_needs_post("apply.cgi")) {' in wc
      and "FROM_BROWSER && reaper_apply_needs_post" not in wc)
check("web.c never classifies the User-Agent to skip a check (it reads reaper_req_app in two places only)",
      len(re.findall(r"\breaper_req_app\b", re.sub(r"/\*.*?\*/", "", wc, flags=re.S))) == 2)

# ---- left alone on purpose
check("left alone: the app's own reply headers and login reply format", "if(fromapp == FROM_DUTUtil || fromapp == FROM_MyASUS){" in hc
      and "send_login_page(fromapp, auth_result, url, file, auth_check_dt, add_try);" in hc)
check("left alone: authentication itself (auth_check gets the real flag)", "auth_result = auth_check(url, file, cookies, fromapp, &add_try);" in hc)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: a User-Agent that names the ASUS app skips no check by itself")
