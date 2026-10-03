#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dnsmasq must survive a transient send failure instead of exiting and taking LAN
DNS and DHCP with it.

WHY THIS EXISTS. RT-BE96U metal, v3.3.1 WAN re-home and v3.3.2 first boot (2026-10-01):
the br0 dnsmasq logged `failed to send packet: Network is unreachable` and was gone,
with no "exiting" line; the watchdog respawned it ~20 s later and the LAN had no DNS
or DHCP in between. Cause: dnsmasq/src/forward.c send_from() carries an ASUS-added
`exit(0)` after that log line (upstream dnsmasq logs and returns 0). The trigger is
stock auto-WAN-port: eth0 is bridged into br0 for a moment and br0's address changes,
so the IP_PKTINFO source dnsmasq answers from is no longer a local address and the
kernel's route lookup returns ENETUNREACH (net/ipv4/route.c, the fl4->saddr check).

THE FIX (v3.3.3). A libc-only helper reaper_send_errno_transient() names the errnos
that mean "the route or address is in flux" - ENETUNREACH and EHOSTUNREACH. For those
send_from() logs (rate-limited to one line per 10 s) and returns 0, which is what
upstream does for every errno; for everything else the ASUS exit(0) stays. The
generated /etc/dnsmasq.conf uses bind-dynamic, so no restart is needed to re-track
the address.

WHAT IT DOES.
  1. Extracts reaper_send_errno_transient() from forward.c, compiles it on the host
     with -Wall -Wextra -Werror and checks the two transient errnos answer 1 and the
     rest (EINVAL, EPERM, ENETDOWN, EAGAIN, EACCES, 0) answer 0.
  2. Asserts on the source that send_from() still has exactly one exit(0), that the
     transient check sits before it inside the HAVE_LINUX_NETWORK block, that the
     transient branch returns 0, that the stock LOG_ERR line is still there, and that
     rc/services.c still writes bind-dynamic (the premise that no restart is needed).
  3. Cross-checks that the verify marker names the new log line (when the marker file
     is reachable from this script's location).

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "dnsmasq", "src")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

forward = read("dnsmasq/src/forward.c")
services = read("rc/services.c")

gcc = shutil.which("gcc") or shutil.which("cc")
if not gcc:
    skip("no host C compiler")

MARK = "transient, reply dropped, not exiting"

# ---------------------------------------------------------------- 1. the helper, compiled and run
a = forward.find("/* reaper v3.3.3: errnos sendmsg() returns")
if a < 0:
    die("forward.c: the reaper_send_errno_transient comment marker is missing")
b = forward.find("\n}\n", a)
if b < 0:
    die("forward.c: helper slice has no end")
helper = forward[a:b + 3]
if "static int reaper_send_errno_transient(int e)" not in helper:
    die("forward.c: helper signature not in the slice")

harness = r'''
#include <errno.h>
#include <stdio.h>
%s
int main(void)
{
    struct { int e; int want; const char *name; } c[] = {
        { ENETUNREACH, 1, "ENETUNREACH" }, { EHOSTUNREACH, 1, "EHOSTUNREACH" },
        { EINVAL, 0, "EINVAL" }, { EPERM, 0, "EPERM" }, { ENETDOWN, 0, "ENETDOWN" },
        { EAGAIN, 0, "EAGAIN" }, { EACCES, 0, "EACCES" }, { 0, 0, "0" },
    };
    unsigned i;
    for (i = 0; i < sizeof c / sizeof c[0]; i++)
        if (reaper_send_errno_transient(c[i].e) != c[i].want) {
            printf("%%s -> %%d, want %%d\n", c[i].name, reaper_send_errno_transient(c[i].e), c[i].want);
            return 1;
        }
    return 0;
}
''' % helper

tmp = tempfile.mkdtemp(prefix="reaper_sendexit_")
try:
    csrc = os.path.join(tmp, "h.c"); exe = os.path.join(tmp, "h")
    with open(csrc, "w") as f:
        f.write(harness)
    r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-O1", csrc, "-o", exe],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        die("helper does not compile on the host:\n" + r.stdout)
    r = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        die("helper classification wrong: " + r.stdout.strip())
    ok("reaper_send_errno_transient: ENETUNREACH/EHOSTUNREACH transient, six others not")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- 2. send_from() wiring
m = re.search(r"^int send_from\(", forward, re.M)
if not m:
    die("forward.c: send_from() not found")
e = forward.find("\n}\n", m.start())
fn = forward[m.start():e + 3]

if fn.count("exit(0);") != 1:
    die("forward.c send_from(): expected exactly one exit(0), found %d" % fn.count("exit(0);"))
if forward.count("exit(0);") != 1:
    die("forward.c: exit(0) appears %d times, expected 1 (send_from only)" % forward.count("exit(0);"))
i_ifdef = fn.find("#ifdef HAVE_LINUX_NETWORK")
i_einval = fn.find("if (errno != EINVAL)")
i_check = fn.find("if (reaper_send_errno_transient(errno))")
i_exit = fn.find("exit(0);")
i_endif = fn.find("#endif", i_ifdef)
if min(i_ifdef, i_einval, i_check, i_exit, i_endif) < 0:
    die("forward.c send_from(): one of the anchors is missing")
if not (i_ifdef < i_einval < i_check < i_exit < i_endif):
    die("forward.c send_from(): order must be #ifdef < EINVAL check < transient check < exit(0) < #endif")
i_ret = fn.find("return 0;", i_check)
if i_ret < 0 or i_ret > i_exit:
    die("forward.c send_from(): the transient branch does not return 0 before the exit")
branch = fn[i_check:i_ret + len("return 0;")]
if MARK not in branch or "LOG_WARNING" not in branch:
    die("forward.c send_from(): the transient branch does not log the marker line at LOG_WARNING")
if "strerror(errno)" in branch:
    die("forward.c send_from(): the transient branch must log the saved errno, not errno after dnsmasq_time()")
if 'my_syslog(LOG_ERR, _("failed to send packet: %s"), strerror(errno));' not in fn[i_exit - 200:i_exit]:
    die("forward.c send_from(): the stock LOG_ERR line before exit(0) is gone")
ok("send_from(): transient errnos return 0 with a rate-limited warning; every other errno still exits")

if "bind-dynamic" not in services:
    die("rc/services.c: the generated dnsmasq.conf no longer says bind-dynamic - re-examine whether the exit was needed to rebind")
ok("rc/services.c: dnsmasq.conf is bind-dynamic (the address is re-tracked without a restart)")

# ---------------------------------------------------------------- 3. the verify marker
mk = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verify_markers.txt")
if os.path.isfile(mk):
    with open(mk, encoding="utf-8", errors="replace") as f:
        markers = f.read()
    line = "usr/sbin/dnsmasq|%s|1" % MARK
    if line not in markers:
        die("verify_markers.txt lacks: " + line)
    ok("verify_markers.txt names the new dnsmasq log line")
else:
    print("note verify_markers.txt not reachable from here - marker cross-check skipped")

print("PASS: dnsmasq survives a transient send failure; the ASUS exit stays for the rest")
