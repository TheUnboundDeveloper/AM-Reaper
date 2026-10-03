#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A firmware flash must release the USB volumes before it ejects them, and a
fresh boot must not start with a service still marked pending.

WHY THIS EXISTS. Field data (RT-BE86U, Entware on a USB SSD, 2026-10-01): a GUI
firmware upgrade logged ~40 s of

    ejusb: USB partition unmounted from /tmp/mnt/asus fail. (Device or resource busy)
    USB partition busy - will unmount ASAP from /tmp/mnt/asus

then flashed with the volume lazily detached, never cleanly unmounted. On the
next boot the SSD mounted late (journal replay), dnsmasq - its log under /opt by
the user's dnsmasq.postconf - exited "cannot open log", and every restart_dnsmasq
was refused with "rc could not be informed (rc_last:restart_upgrade)". Cause, in
canon: every flash path ran `ejusb -1 0` FIRST (httpd's upload handlers, the rc
"upgrade" service, the update-check script) while Entware's daemons, dnsmasq and
rtrafd still held files on the volume; only the normal reboot path ever ran the
user's services-stop. And nothing on a boot cleared a leftover rc_service.

THE FIX (rc/reaper_usbrel.c): an applet, `reaper_usb_release`, that runs just
before each of those ejects - services-stop, rtrafd, then a sweep that stops every
process holding anything under /tmp/mnt/ (cwd, exe, an open file, a mapped
library); watchdog's dnsmasq_check stands down while its flag exists; init clears
rc_service / rc_service_pid / last_rc_service on every boot.

WHAT IT DOES.
  1. Extracts the three libc-only helpers from the real rc/reaper_usbrel.c
     (brace-matched by marker, not copied), compiles them on the host with a tiny
     main, and runs them against two real holder processes under a temp prefix:
     one that honours SIGTERM, one that ignores it. Asserts both are found, both
     are gone afterwards, and exactly the TERM-ignoring one needed SIGKILL.
  2. Asserts on the real source that every flash-path eject is preceded by the
     release: the four httpd sites that call upgrade_rc("stop"), httpd's factory
     reset, the rc "upgrade" service, and reaper_webs_upgrade.sh.
  3. Asserts the applet is registered (rc.c, rc.h, rc/Makefile OBJS + symlink),
     is a no-op without a mounted volume, runs services-stop only once per flash,
     that watchdog's dnsmasq_check honours the flag, and that init clears the
     three rc_service keys.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the
tree's release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

applet = read("rc/reaper_usbrel.c")
web = read("httpd/web.c")
services = read("rc/services.c")
watchdog = read("rc/watchdog.c")
init = read("rc/init.c")
rc_c = read("rc/rc.c")
rc_h = read("rc/rc.h")
mk = read("rc/Makefile")
webs = read("rom/webs_scripts/reaper_webs_upgrade.sh")

# ---------------------------------------------------------------- 1. the sweep, for real
gcc = shutil.which("gcc") or shutil.which("cc")
if not gcc:
    skip("no host C compiler")
if not sys.platform.startswith("linux"):
    skip("the sweep reads /proc - Linux only")

a = applet.find("/* 1 when the process is a zombie")
b = applet.find("/* 1 when a filesystem is mounted")
if a < 0 or b < 0 or b <= a:
    die("rc/reaper_usbrel.c: helper markers not found (usbrel_gone .. reaper_kill_usb_holders)")
helpers = applet[a:b]
for fn in ("static int usbrel_gone(", "static int usbrel_holds(", "int reaper_kill_usb_holders(",
           "static int usbrel_swaps_under("):
    if fn not in helpers:
        die("rc/reaper_usbrel.c: %s not in the helper slice" % fn)

harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <signal.h>
#include <limits.h>
#include <sys/types.h>
%s
int main(int argc, char **argv) {
    char names[512]; int killed = -1;
    if (argc > 3 && !strcmp(argv[1], "swaps")) {	/* swaps <file> <prefix>: the /proc/swaps reader */
        char out[1024], *p;
        int k = usbrel_swaps_under(argv[2], argv[3], out, sizeof out);
        for (p = out; *p; p++) if (*p == '\n') *p = '|';
        printf("k=%%d out=%%s\n", k, out);
        return 0;
    }
    int n = reaper_kill_usb_holders(argv[1], 3, names, sizeof names, &killed);
    printf("n=%%d killed=%%d names=%%s\n", n, killed, names);
    return 0;
}
''' % helpers

tmp = tempfile.mkdtemp(prefix="usbrel-")
try:
    prefix = os.path.join(tmp, "mnt") + "/"
    hold = os.path.join(prefix, "vol")
    os.makedirs(hold)
    csrc = os.path.join(tmp, "h.c"); exe = os.path.join(tmp, "h")
    with open(csrc, "w") as f:
        f.write(harness)
    r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-O1", csrc, "-o", exe],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        die("helpers do not compile on the host:\n" + r.stdout)
    ok("rc/reaper_usbrel.c helpers compile on the host (-Wall -Wextra -Werror)")

    # holder 1: honours SIGTERM, holds the volume as its cwd
    h1 = subprocess.Popen(["sleep", "300"], cwd=hold)
    # holder 2: ignores SIGTERM (so it must be SIGKILLed), holds an OPEN FILE there
    h2 = subprocess.Popen(["sh", "-c", 'trap "" TERM; exec 3>"%s/held"; cd /; while :; do sleep 1; done' % hold])
    time.sleep(0.5)
    out = subprocess.run([exe, prefix], stdout=subprocess.PIPE, text=True, timeout=30).stdout.strip()
    m = re.match(r"n=(\d+) killed=(\d+) names=(.*)", out)
    if not m:
        die("harness output unexpected: %r" % out)
    n, killed, names = int(m.group(1)), int(m.group(2)), m.group(3)
    # holder 2's `sleep 1` children come and go; the two long-lived holders must be found
    if n < 2:
        die("sweep found %d holder(s), expected at least the two long-lived ones (%s)" % (n, out))
    if "sleep" not in names or "sh" not in names:
        die("sweep did not name both holders: %s" % out)
    if killed < 1:
        die("the SIGTERM-ignoring holder should have needed SIGKILL: %s" % out)
    deadline = time.time() + 5
    while time.time() < deadline and (h1.poll() is None or h2.poll() is None):
        time.sleep(0.1)
    if h1.poll() is None or h2.poll() is None:
        die("a holder survived the sweep (sleep=%s sh=%s)" % (h1.poll(), h2.poll()))
    ok("sweep found both holders (cwd and an open file), SIGTERM then SIGKILL, both gone: %s" % out)
    # a process that merely LOOKS similar (same binary, elsewhere) is left alone
    bystander = subprocess.Popen(["sleep", "300"], cwd=tmp)
    time.sleep(0.3)
    out2 = subprocess.run([exe, prefix], stdout=subprocess.PIPE, text=True, timeout=30).stdout.strip()
    time.sleep(0.3)
    if bystander.poll() is not None:
        die("a process outside the prefix was stopped: %s" % out2)
    bystander.kill(); bystander.wait()
    ok("a process outside the prefix is left alone: %s" % out2)

    # v3.3.3: swap files on the volume are found from /proc/swaps (header skipped, other swaps ignored)
    sw = os.path.join(tmp, "swaps")
    with open(sw, "w") as f:
        f.write("Filename\t\t\t\tType\t\tSize\tUsed\tPriority\n"
                "/tmp/mnt/sda1/myswap.swp                file\t\t2097148\t40960\t-2\n"
                "/dev/zram0                              partition\t262140\t0\t100\n"
                "/tmp/mnt/sdb1/.swap                     file\t\t524284\t0\t-3\n")
    out3 = subprocess.run([exe, "swaps", sw, "/tmp/mnt/"], stdout=subprocess.PIPE, text=True, timeout=10).stdout.strip()
    if out3 != "k=2 out=/tmp/mnt/sda1/myswap.swp|/tmp/mnt/sdb1/.swap|":
        die("swaps reader: unexpected %r" % out3)
    out4 = subprocess.run([exe, "swaps", sw, "/mnt/nothing/"], stdout=subprocess.PIPE, text=True, timeout=10).stdout.strip()
    if out4 != "k=0 out=":
        die("swaps reader with no match: unexpected %r" % out4)
    ok("swap files under the prefix are listed from /proc/swaps; the header and other swaps are not")
finally:
    for p in ("h1", "h2"):
        proc = locals().get(p)
        if proc is not None and proc.poll() is None:
            proc.kill(); proc.wait()
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- 2. every flash eject is preceded by the release
EJECT = 'eval("/sbin/ejusb", "-1", "0");'
REL = 'eval("/sbin/reaper_usb_release");'

def preceded(text, idx, window=400):
    return REL in text[max(0, idx - window):idx]

flash_sites = [m.start() for m in re.finditer(re.escape(EJECT) + r'\s*\n\s*upgrade_rc\("stop"', web)]
if len(flash_sites) != 4:
    die("httpd/web.c: expected 4 flash-path ejects followed by upgrade_rc(\"stop\"), found %d" % len(flash_sites))
for i in flash_sites:
    if not preceded(web, i):
        die("httpd/web.c: a flash-path eject at offset %d is not preceded by %s" % (i, REL))
ok("httpd/web.c: all 4 flash-path ejects are preceded by the release")

fr = web.find('nvram_set("lan_ipaddr", nvram_default_safe_get("lan_ipaddr"));')
if fr < 0 or not preceded(web, fr):
    die("httpd/web.c: the factory-reset eject is not preceded by the release")
ok("httpd/web.c: the factory-reset eject is preceded by the release")

su = services.find('else if(strcmp(script, "upgrade") == 0)')
if su < 0:
    die("rc/services.c: the \"upgrade\" service block was not found")
ej = services.find(EJECT, su)
if ej < 0 or ej - su > 6000:
    die("rc/services.c: no eject inside the \"upgrade\" STOP branch")
if not preceded(services, ej):
    die("rc/services.c: the upgrade service's eject is not preceded by the release")
ok("rc/services.c: the upgrade service's eject is preceded by the release")

we = webs.find("/sbin/ejusb -1 0")
if we < 0 or "/sbin/reaper_usb_release" not in webs[:we]:
    die("reaper_webs_upgrade.sh: ejusb is not preceded by /sbin/reaper_usb_release")
ok("reaper_webs_upgrade.sh: the release runs before ejusb")

# ---------------------------------------------------------------- 3. registration, gates, boot clear
for text, needle, where in (
    (rc_c, '"reaper_usb_release"', "rc/rc.c applet table"),
    (rc_c, "reaper_usb_release_main", "rc/rc.c applet table"),
    (rc_h, "extern int reaper_usb_release_main(", "rc/rc.h"),
    (rc_h, '#define REAPER_USBREL_FLAG', "rc/rc.h"),
    (mk, "OBJS += reaper_usbrel.o", "rc/Makefile OBJS"),
    (mk, "ln -sf rc reaper_usb_release", "rc/Makefile install symlink"),
):
    if needle not in text:
        die("%s: missing %r" % (where, needle))
ok("applet registered: rc.c, rc.h, Makefile OBJS and symlink")

main_at = applet.find("int reaper_usb_release_main(")
if main_at < 0:
    die("rc/reaper_usbrel.c: no reaper_usb_release_main")
body = applet[main_at:]
gate = body.find("usbrel_volume_mounted()")
first_use = min(x for x in (body.find("run_custom_script("), body.find("reaper_kill_usb_holders("), body.find("f_write_string(")) if x >= 0)
if gate < 0 or gate > first_use:
    die("rc/reaper_usbrel.c: the mounted-volume check must come before anything is written or stopped")
if not re.search(r'if \(first\) \{[^}]*run_custom_script\("services-stop"', body):
    die("rc/reaper_usbrel.c: services-stop must run only on the first call of a flash (if (first) {...})")
if 'stop_rtraf();' not in body:
    die("rc/reaper_usbrel.c: rtrafd is not stopped (its history store may be on the volume)")
ok("applet: no-op without a mounted volume; services-stop once per flash; rtrafd stopped")
ks = body.find('reaper_kill_usb_holders("/tmp/mnt/"')
sw = body.find('usbrel_swaps_under("/proc/swaps", "/tmp/mnt/"')
if ks < 0 or sw < 0 or sw < ks or 'eval("swapoff", p)' not in body[sw:]:
    die("rc/reaper_usbrel.c: swap on the volume must be turned off AFTER the holder sweep (RAM freed first)")
ok("applet: swap files on the volume are turned off after the holders are gone")

dc = watchdog.find("void dnsmasq_check()")
if dc < 0 or "f_exists(REAPER_USBREL_FLAG)" not in watchdog[dc:dc + 1200]:
    die("rc/watchdog.c: dnsmasq_check does not stand down on REAPER_USBREL_FLAG")
ok("rc/watchdog.c: dnsmasq_check stands down while a flash is releasing the volumes")

# v3.3.3: a plain reboot/halt releases first too - init's SIGTERM branch ran services-stop
# in the background (stop_services) and unmounted seconds later with Entware still up
i_case = init.find("case SIGTERM:\t\t/* REBOOT */")
i_rel = init.find('eval("/sbin/reaper_usb_release", "reboot");', i_case)
i_stop = init.find("stop_services();", i_case)
i_rsm = init.find("remove_storage_main(1);", i_case)
if i_case < 0 or not (0 <= i_rel < i_stop < i_rsm):
    die("rc/init.c: the reboot path must run `reaper_usb_release reboot` before stop_services() and the unmount")
if "state == SIGTERM /* REBOOT */ || state == SIGQUIT /* HALT */" not in init[i_case:i_rel]:
    die("rc/init.c: the reboot release must be limited to reboot and halt (SIGHUP keeps the volumes)")
ok("rc/init.c: reboot/halt release the USB volumes before stop_services() and remove_storage_main(1)")

ss = services.find("stop_services(void)")
blk = services[ss:ss + 800] if ss >= 0 else ""
if 'if (!f_exists(REAPER_USBREL_FLAG))\n\t\trun_custom_script("services-stop", 0, NULL, NULL);' not in blk:
    die("rc/services.c: stop_services() must skip its background services-stop once the release has run it")
ok("rc/services.c: stop_services() does not re-run services-stop after a release")

if 'reboot: releasing USB volumes before the unmount' not in applet or 'flash: releasing USB volumes before the eject' not in applet:
    die("rc/reaper_usbrel.c: both log lines (flash and reboot) must be present - verify markers pin them")
ok("rc/reaper_usbrel.c: logs say whether a flash or a reboot released the volumes")

sc = init.find("nvram_unset(ASUS_STOP_COMMIT);")
if sc < 0:
    die("rc/init.c: ASUS_STOP_COMMIT unset not found")
tail = init[sc:sc + 1500]
for key in ("rc_service", "rc_service_pid", "last_rc_service"):
    if 'nvram_unset("%s");' % key not in tail:
        die("rc/init.c: boot does not clear %s next to the ASUS_STOP_COMMIT unset" % key)
ok("rc/init.c: a boot clears rc_service, rc_service_pid and last_rc_service")

print("PASS: usb-flash-release")
