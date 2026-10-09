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
MUST_NOT_PREAUTH = ["enable_ig_guest.cgi*", "get_cta_info.cgi*", "**.pac", "wpad.dat",
                    "**.swf", "**.htc", "**.part.*", "**.gz", "**.tgz", "**.zip", "**.ipk"]
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
print("PASS test_preauth_rows")
