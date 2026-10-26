#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Files that hold key material must never sit behind an unauthenticated httpd row.

WHY THIS EXISTS. Audit 2026-10-06 (V1): the stock handler row for wgs_client.png -
the QR code of a WireGuard server client's full configuration, private key
included - had no auth hook, so any host that could reach the GUI port downloaded
a working VPN peer while the WireGuard server was on. The row came in with the
GPL 45581 merge and had never been looked at. The fix is one word (do_auth); this
test keeps it, and keeps the other credential-bearing download rows gated too.

WHAT IT DOES. Reads the mime_handlers[] table in httpd/web.c and asserts that every
row named below ends in do_auth, and that no row serving the WireGuard client files
is unauthenticated.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WEB = os.path.join(SRC, "httpd", "web.c")
if not SRC or not os.path.isfile(WEB):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

src = open(WEB, encoding="utf-8", errors="replace").read()
start = src.find("struct mime_handler mime_handlers[] =")
if start < 0:
    die("mime_handlers[] table not found in httpd/web.c")
end = src.find("\n};", start)
table = src[start:end]

# rows whose payload is credential material: WireGuard client conf + QR, OpenVPN client profile,
# the OpenVPN server cert download, the Reaper backup export
MUST_AUTH = ["wgs_client.png", "wgs_client.conf", "**.ovpn", "server_ovpn.cert", "reaper_export.cgi*"]
ROW = re.compile(r'^\s*\{\s*"([^"]+)"\s*,(.*)\},\s*$', re.M)
rows = {m.group(1): m.group(2) for m in ROW.finditer(table)}
for name in MUST_AUTH:
    if name not in rows:
        die("row %r missing from mime_handlers[]" % name)
    fields = [f.strip() for f in rows[name].split(",")]
    if fields[-1] != "do_auth":
        die("row %r ends in %r, not do_auth" % (name, fields[-1]))
    ok("%s requires authentication" % name)

if re.search(r"do_wgs_client_(png|conf)\s*,\s*NULL\s*\}", table):
    die("a WireGuard client row is served without authentication")
ok("no unauthenticated WireGuard client row")

# Audit 2026-10-07 (G1, G3, and the 2026-10-06 V5 remainder): rows that must never be
# served without a login. Either the row is compiled out (inside "#if 0") or it ends in
# do_auth. G1 = the Instant Guard guest-enable CGI (writes configuration, closed blob,
# feature dead on this build) and the CTA info CGI; G3/V5 = WPAD/proxy-autoconfig rows
# over a /tmp symlink target, and the wildcard archive/plugin rows.
def compiled(text):
    """drop /* */ comments, then every #if 0 ... #endif block (nesting-aware).
    String literals are matched first and kept: row patterns such as "fonts/*.ttf"
    contain a /* that is not a comment, and a naive strip swallows whole rows."""
    text = re.sub(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/',
                  lambda m: m.group(0) if m.group(0).startswith('"') else "", text, flags=re.S)
    out, depth = [], 0
    for line in text.split("\n"):
        s = line.strip()
        if depth:
            if s.startswith("#if"):
                depth += 1
            elif s.startswith("#endif"):
                depth -= 1
            continue
        if re.match(r"#if\s+0\b", s):
            depth = 1
            continue
        out.append(line)
    return "\n".join(out)

live = compiled(table)
LROW = re.compile(r'^\s*\{\s*"([^"]+)"\s*,(.*)\}\s*,?\s*$', re.M)
live_rows = {}
for m in LROW.finditer(live):
    live_rows.setdefault(m.group(1), []).append([f.strip() for f in m.group(2).split(",")])
# 2026-10-23: register_app_cnonce.cgi - closed handler writes + commits app_cnonce_list (the nonces the
# app login trusts) before login; ASUS deleted it in GPL 102_40585 (CVE-2026-93489 class).
MUST_NOT_PREAUTH = ["enable_ig_guest.cgi*", "get_cta_info.cgi*", "**.pac", "wpad.dat",
                    "**.swf", "**.htc", "**.part.*", "**.gz", "**.tgz", "**.zip", "**.ipk",
                    "register_app_cnonce.cgi"]
for name in MUST_NOT_PREAUTH:
    for fields in live_rows.get(name, []):
        if fields[-1] != "do_auth":
            die("row %r is compiled in and served without authentication (ends in %r)" % (name, fields[-1]))
    ok("%s is %s" % (name, "authenticated" if name in live_rows else "compiled out"))

# these stay compiled in behind a login: the Feedback page downloads fb_data.tgz.gz
# through the archive wildcards, and stock admin pages load PIE.htc
EXPECT_AUTH = ["**.part.*", "**.gz", "**.tgz", "**.zip", "**.ipk", "**.swf", "**.htc"]
for name in EXPECT_AUTH:
    if name not in live_rows:
        die("row %r is missing from the compiled table (expected it behind do_auth)" % name)
ok("archive and component rows present behind do_auth")

# audit 2026-10-06 V4 (2026-10-08): the retired QIS / repeater pages require a login; the offline page's
# WAN poll carries only the WAN state it reads (no dual-WAN list, auto-detect state or dual_wanstate)
for name in ("gotoHomePage.htm", "ure_success.htm", "ureip.asp"):
    if name not in live_rows:
        die("row %r is missing from the compiled table" % name)
ok("retired pre-login pages gotoHomePage.htm, ure_success.htm, ureip.asp are behind do_auth")
wi = open(os.path.join(SRC, "www", "WAN_info.asp"), encoding="utf-8", errors="replace").read()
tags = re.findall(r"<%[^%]*%>", wi)
if tags != ["<% wanstate(); %>"]:
    die("WAN_info.asp is served before login and must evaluate only wanstate(); found %r" % tags)
ok("WAN_info.asp evaluates only wanstate()")

# the login-exception table must not keep a no-password entry for the compiled-out IG CGI
exc_start = src.find("except_mime_handlers[] =")
if exc_start >= 0:
    exc = compiled(src[exc_start:src.find("\n};", exc_start)])
    if '"enable_ig_guest.cgi"' in exc:
        die("except_mime_handlers[] still lists enable_ig_guest.cgi as MIME_EXCEPTION_NOPASS")
    ok("no NOPASS exception for enable_ig_guest.cgi")

# security review 2026-10-20 (F-4): the session cookie carries SameSite=Lax. The cookie text comes
# from the closed gen_asus_token_cookie() and ends in ';'; the two OPEN emitters - send_token_headers()
# in httpd.c and login_cgi() in web.c - append the attribute. Nothing else may emit a Set-Cookie. The
# stock referer whitelist (closed, mime_referers[]) covers only 38 CGIs; the Reaper CGIs add the
# per-boot http_id, and since 2026-10-23 httpd.c refuses a cross-site request to ANY authenticated
# CGI (test_xsite_cgi_guard.py).
hc = open(os.path.join(SRC, "httpd", "httpd.c"), encoding="utf-8", errors="replace").read()
emitters = re.findall(r'"Set-Cookie: [^"]*"', hc) + re.findall(r'"Set-Cookie: [^"]*"', src)
if len(emitters) != 2 or any(e != '"Set-Cookie: %s%s\\r\\n"' for e in emitters):
    die("expected exactly two Set-Cookie emitters of the form \"Set-Cookie: %%s%%s\\r\\n\", found %r" % emitters)
if hc.count('token_cookie[0] ? " SameSite=Lax" : ""') != 1 or src.count('token_cookie[0] ? " SameSite=Lax" : ""') != 1:
    die("SameSite=Lax is not appended by both emitters (httpd.c %d, web.c %d)"
        % (hc.count('" SameSite=Lax"'), src.count('" SameSite=Lax"')))
ok("the session cookie is emitted with SameSite=Lax by both open emitters and by nothing else")

# ASUS bulletin 2026-10-23, CVE-2026-93489 (a nearby, unauthenticated client forges an "access
# ticket" and gets admin): the closed web_hook.o handler do_asusrouter_request_access_token_cgi
# AES-decrypts a caller-supplied access_ticket and mints an asus_token from it. It - and its three
# sibling pre-login token CGIs - is only routed under RTCONFIG_ACCOUNT_BINDING, which no Reaper model
# turns on. Keep both halves: the rows stay inside that #ifdef, and no target.mak line enables it.
TOKEN_CGIS = ["get_eptoken.cgi*", "asusrouter_request_token.cgi*",
              "asusrouter_request_access_token.cgi*", "endpoint_request_token.cgi*"]
blk = re.search(r"#ifdef RTCONFIG_ACCOUNT_BINDING\n(.*?)\n#endif", table, re.S)
if not blk:
    die("the RTCONFIG_ACCOUNT_BINDING block is gone from mime_handlers[]")
outside = table[:blk.start()] + table[blk.end():]
for name in TOKEN_CGIS:
    if '"%s"' % name not in blk.group(1):
        die("row %r is no longer inside #ifdef RTCONFIG_ACCOUNT_BINDING" % name)
    if '"%s"' % name in outside:
        die("row %r also appears outside #ifdef RTCONFIG_ACCOUNT_BINDING" % name)
ok("the pre-login token CGIs (CVE-2026-93489) stay inside #ifdef RTCONFIG_ACCOUNT_BINDING")
rel = os.path.dirname(os.path.dirname(os.path.abspath(SRC)))
maks = [os.path.join(rel, d, "target.mak") for d in sorted(os.listdir(rel))
        if d.startswith("src-rt") and os.path.isfile(os.path.join(rel, d, "target.mak"))]
for mk in maks:
    if re.search(r"\bACCOUNT_BINDING=y\b", open(mk, encoding="utf-8", errors="replace").read()):
        die("%s enables ACCOUNT_BINDING - CVE-2026-93489's pre-login token CGIs would be routed" % mk)
ok("no target.mak enables ACCOUNT_BINDING (%d checked)" % len(maks) if maks else "no target.mak beside the tree - ACCOUNT_BINDING half not checked")
print("PASS test_preauth_rows")
