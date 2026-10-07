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
print("PASS test_preauth_rows")
