#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A box that is not routing must still tune its sockets, count its clients and
name its own operation mode.

WHY THIS EXISTS. Field data (GT-BE19000 tester, 2026-09-13): a working router in
Access Point mode (sw_mode=3) reported a red "Disconnected" Internet card, zero
clients while sixteen stations were associated, socket ceilings still at the stock
212992, and an "rtrafd is enabled but not running" warning. None of it was
model-specific - all four were the same shape, a Reaper surface built on something
only a routing box has:

  * rc/firewall.c        start_firewall() returns at !is_routing_enabled() long
                         before the socket-buffer ceilings, so they never loaded.
  * Main_ReaperDash.asp  the Internet card derives its verdict from wan0_state_t,
                         which is structurally 0 with no WAN of its own.
  * Main_ReaperDash.asp  the client tiles filter on networkmap's isOnline, which is
                         derived from DHCP leases and conntrack - both empty on a
                         bridging box.
  * others/reaper_diag   12c warns when a routing-only daemon is idle, which on a
                         non-routing box is the designed state.

The fixes are cheap and the ways to lose them are cheaper: a sibling port that
drops a hunk, or a later refactor that "simplifies" the guard back. This test is
the tripwire.

WHAT IT DOES.
  1. Extracts reaper_socket_ceilings() from the real rc/firewall.c (brace-matched,
     not copied), compiles it on the host with fopen() redirected into a temp tree,
     runs it, and asserts the three /proc knobs get 16777216 / 16777216 / 4096.
  2. Asserts on the real source that BOTH paths reach it: the !is_routing_enabled()
     early return in start_firewall(), and the call in the body that routing mode
     still takes.
  3. Asserts www/Main_ReaperDash.asp resolves ROUTING from the operation mode, and
     that each of the three surfaces branches on it - the card, the live WAN poll
     and the client tiles - and that the non-routing collector reads reaper_dev.cgi
     WITH the CSRF token.
  4. Asserts others/reaper_diag's 12c svc() is operation-mode aware and that its
     routing-only note names the modes it applies to.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the
tree's release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("  ok  " + msg)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not src_root or not os.path.isdir(src_root):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")

FW   = os.path.join(src_root, "rc", "firewall.c")
DASH = os.path.join(src_root, "www", "Main_ReaperDash.asp")
DIAG = os.path.join(src_root, "others", "reaper_diag")
for p in (FW, DASH, DIAG):
    if not os.path.isfile(p):
        skip("missing %s" % p)

def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

def extract(src, signature, where):
    """Return the whole function whose body opens after `signature`."""
    i = src.find(signature)
    if i < 0:
        die("%s: signature not found: %r" % (where, signature))
    j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1
    die("%s: unbalanced braces after %r" % (where, signature))

fw_src   = read(FW)
dash_src = read(DASH)
diag_src = read(DIAG)

# ---------------------------------------------------------------------------
# 1. the ceilings function does what it says, compiled from the real source
# ---------------------------------------------------------------------------
print("1. rc/firewall.c reaper_socket_ceilings()")

CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fn = extract(fw_src, "static void reaper_socket_ceilings(void)", "firewall.c")

# fopen() is redirected by string-pasting the caller's absolute /proc path onto a
# temp root, so the real knob values in the real source are what gets exercised.
harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *g_root;

static FILE *redir_fopen(const char *path, const char *mode)
{
	char buf[512];
	char *p;
	snprintf(buf, sizeof(buf), "%s%s", g_root, path);
	/* create the parent chain so the real absolute paths can be used verbatim */
	for (p = buf + strlen(g_root) + 1; *p; p++) {
		if (*p != '/') continue;
		*p = 0;
		if (mkdir_p(buf)) return NULL;
		*p = '/';
	}
	return fopen(buf, mode);
}

#define fopen(p, m) redir_fopen((p), (m))

__FN__

#undef fopen

int main(int argc, char **argv)
{
	if (argc < 2) return 2;
	g_root = argv[1];
	reaper_socket_ceilings();
	return 0;
}
'''
mkdir_p = r'''
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
static int mkdir_p(const char *d)
{
	if (mkdir(d, 0755) == 0) return 0;
	return (errno == EEXIST) ? 0 : -1;
}
'''
prog = mkdir_p + harness.replace("__FN__", fn)

tmp = tempfile.mkdtemp(prefix="apmode_")
try:
    csrc = os.path.join(tmp, "ceilings.c")
    cbin = os.path.join(tmp, "ceilings")
    with open(csrc, "w", encoding="utf-8") as f:
        f.write(prog)
    p = subprocess.run([CC, "-O0", "-w", "-o", cbin, csrc], capture_output=True, text=True)
    if p.returncode != 0:
        die("the extracted reaper_socket_ceilings() does not compile:\n" + p.stderr[:1500])
    root = os.path.join(tmp, "root")
    os.makedirs(root)
    p = subprocess.run([cbin, root], capture_output=True, text=True)
    if p.returncode != 0:
        die("reaper_socket_ceilings() exited %d" % p.returncode)

    want = {
        "proc/sys/net/core/rmem_max": "16777216",
        "proc/sys/net/core/wmem_max": "16777216",
        "proc/sys/net/core/netdev_max_backlog": "4096",
    }
    for rel, val in want.items():
        f = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(f):
            die("reaper_socket_ceilings() never wrote /%s" % rel)
        got = read(f).strip()
        if got != val:
            die("/%s got %r, want %r" % (rel, got, val))
        ok("/%s <- %s" % (rel, val))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
# 2. both paths reach it
# ---------------------------------------------------------------------------
print("2. rc/firewall.c start_firewall() reaches it in every operation mode")

start_fw = extract(fw_src, "int start_firewall(int wanunit, int lanunit)", "firewall.c")
if start_fw.count("reaper_socket_ceilings();") != 2:
    die("start_firewall() should call reaper_socket_ceilings() exactly twice "
        "(the non-routing return, and the routing body); found %d"
        % start_fw.count("reaper_socket_ceilings();"))
ok("start_firewall() calls it on both paths")

# the early return must call it BEFORE returning -1, or a non-routing box gets nothing
guard = start_fw[start_fw.index("if (!is_routing_enabled())"):]
guard = guard[:guard.index("return -1;") + len("return -1;")]
if "reaper_socket_ceilings();" not in guard:
    die("the !is_routing_enabled() early return does not call reaper_socket_ceilings() "
        "- AP, repeater and media-bridge boxes keep the stock ceiling")
ok("the !is_routing_enabled() return tunes before it returns")

# ---------------------------------------------------------------------------
# 3. the dashboard branches on the operation mode on all three surfaces
# ---------------------------------------------------------------------------
print("3. www/Main_ReaperDash.asp")

need = [
    ("var ROUTING=",
     "the page never resolves ROUTING from the operation mode"),
    ("function paintOpmodeWan()",
     "no non-routing painter for the Internet card"),
    ("if(!ROUTING){",
     "the Internet card render does not branch on the operation mode - it would "
     "paint a bridging box red again"),
    ("if(ROUTING) schedule(FAST); else paintOpmodeWan();",
     "the live WAN poll does not branch - it would re-paint Disconnected over the "
     "card every four seconds"),
    ("function pollClientsDev()",
     "no non-routing client collector"),
    ("var clientTick = ROUTING ? pollClients : pollClientsDev;",
     "the client tiles never dispatch to the non-routing collector"),
]
for token, why in need:
    if token not in dash_src:
        die("%s (missing: %s)" % (why, token))
    ok(token)

# the non-routing collector must read Reaper's own store, with the token
dev = extract(dash_src, "function pollClientsDev()", "Main_ReaperDash.asp")
if "/reaper_dev.cgi?action=status" not in dev:
    die("pollClientsDev() does not read reaper_dev.cgi - networkmap's isOnline is "
        "exactly what does not work here")
if "http_id=" not in dev:
    die("pollClientsDev() omits http_id - reaper_dev.cgi's action=status is gated "
        "and every request would be refused")
ok("pollClientsDev() reads reaper_dev.cgi with the CSRF token")

# it must not re-introduce the isOnline filter, and must fold what the Devices page folds
if "isOnline" in dev:
    die("pollClientsDev() consults isOnline - that is the networkmap flag this whole "
        "path exists to avoid")
for tok in ("d.mlo_link", "d.node"):
    if tok not in dev:
        die("pollClientsDev() does not fold %s - an MLO link or an AiMesh node would "
            "be counted as a client" % tok)
ok("no isOnline; MLO links and AiMesh nodes folded")

# ---------------------------------------------------------------------------
# 4. the diag does not warn about a routing-only daemon on a bridging box
# ---------------------------------------------------------------------------
print("4. others/reaper_diag 12c")

if "_ROUTING=1" not in diag_src:
    die("reaper_diag does not resolve the operation mode for 12c")
if 'case "$(nvram get sw_mode 2>/dev/null)" in 2|3)' not in diag_src:
    die("reaper_diag's 12c mode test does not name sw_mode 2 (repeater/media bridge) "
        "and 3 (access point)")
svc = diag_src[diag_src.index("svc() {"):]
svc = svc[:svc.index("\n}\n") + 3]
if 'if [ "$_ROUTING" = 0 ]; then' not in svc:
    die("svc() does not take a non-routing path - rtrafd, gkd and rchqd are all "
        "started behind !is_routing_enabled(), so idle is designed, not a fault")
if "routing-only" not in svc:
    die("svc()'s non-routing line does not say why the daemon is idle")
ok("svc() is operation-mode aware")

print("PASS: the non-routing paths are present on all four surfaces")
sys.exit(0)
