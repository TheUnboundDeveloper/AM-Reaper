#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USB hotplug restarts the NAS apps once per mount wave, not once per partition (2026-10-15).

WHY THIS EXISTS. Stock hotplug_usb() (rc/usb.c) ran a full restart_nasapps - Samba, FTP, the
media server, NFS, Time Machine, and UPnP with them (the nasapps service handler bounces a
running miniupnpd) - after EVERY partition that mounted, and blocked on it while holding the
"usb" lock, so the next partition could not mount until the restart finished. A disk with two
mountable partitions (a Mac disk's FAT EFI partition + data, a Linux multi-partition disk), or
two disks at boot, ran the whole stop + start back to back. A physical unplug did the same per
partition; only the GUI eject-and-remove path coalesced (remove_usb_disk presets the
ignore_nas_service_ counter and ejusb_main restarts once).

THE FIX. Both per-partition sites set a flag; after file_unlock(lock) reaper_nasapps_settle()
stamps /tmp/reaper/nasapps.settle with a per-event token and leaves a detached waiter that
restarts the apps after a settle window only if its token is still the newest. Any failure
(the directory, the stamp, fork) falls back to the stock immediate restart.

WHAT IT DOES. Static checks on the hotplug block, then compiles reaper_nasapps_settle() out of
rc/usb.c with stub helpers (settle window scaled to 1 s) and runs each hotplug event as its own
process, as the kernel does: one event = one restart and the event returns at once; a wave of
three = one restart; two waves = two; the fallback restarts at once. A negative self-test drops
the "still the newest" comparison and expects the wave case to fail.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or
REAPER_ROUTER_SRC). The compiled run is skipped, not failed, without a host gcc."""
import os, re, shutil, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
USB = os.path.join(SRC, "rc", "usb.c") if SRC else ""
if not USB or not os.path.isfile(USB):
    skip("no router source tree with rc/usb.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

src = open(USB, encoding="utf-8", errors="replace").read()

# ---- static: the hotplug partition block ----
m = re.search(r'snprintf\(nv_name, sizeof\(nv_name\), "ignore_nas_service_%s", dev\);(.*?)#ifdef RTCONFIG_FRS_FEEDBACK',
              src, re.S)
blk = m.group(1) if m else ""
check("static: hotplug partition block found", bool(blk))
check("static: no blocking per-partition notify_rc_and_wait(\"restart_nasapps\") left",
      'notify_rc_and_wait("restart_nasapps")' not in blk)
t5 = blk.find("test 5."); t6 = blk.find("test 6.")
check("static: the mount site (test 5) only flags the settle",
      t5 >= 0 and "nas_settle = 1;" in blk[t5:t5 + 200] and "restart_nasapps" not in blk[t5:t5 + 200])
check("static: the unplug site (test 6) only flags the settle",
      t6 >= 0 and "nas_settle = 1;" in blk[t6:t6 + 200] and "restart_nasapps" not in blk[t6:t6 + 200])
u = blk.find("file_unlock(lock);\n\t\tif (nas_settle)\n\t\t\treaper_nasapps_settle();")
check("static: the settle runs after file_unlock(lock) (the waiter must not inherit the usb lock)", u >= 0)
check("static: the ignore_nas_service_ counter path (GUI eject) is untouched",
      "if ((c = nvram_get_int(nv_name)) >= 1)" in blk)
check("static: ejusb_main still restarts once after an eject (test 7)",
      re.search(r'test 7\.\\n", getpid\(\)\);\s*//restart_nas_services\(1, 1, 0\);\s*notify_rc_after_wait\("restart_nasapps"\);', src)
      is not None)
check("static: the stamp lives in REAPER_TMPDIR (tmp hardening)",
      re.search(r'#define REAPER_NAS_STAMP\s+REAPER_TMPDIR "/nasapps\.settle"', src) is not None)

fm = re.search(r"\nstatic void reaper_nasapps_settle\(void\)\n\{\n.*?\n\}\n", src, re.S)
fn = fm.group(0) if fm else ""
check("static: reaper_nasapps_settle() found", bool(fn))
check("static: every failure path falls back to an immediate restart",
      fn.count('notify_rc_after_wait("restart_nasapps")') == 2 and "(pid = fork()) < 0" in fn
      and "reaper_secure_dir(REAPER_TMPDIR, 0700) != 0" in fn)

# ---- compiled: the settle logic itself ----
HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#define REAPER_TMPDIR TMPD
long uptime(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (long)t.tv_sec; }
int reaper_secure_dir(const char *p, mode_t m) {
#ifdef FAIL_DIR
	(void)p; (void)m; return -1;
#else
	mkdir(p, m); return 0;
#endif
}
int f_write_string(const char *p, const char *b, unsigned fl, unsigned cm) {
	FILE *f = fopen(p, "w"); (void)fl; (void)cm;
	if (!f) return -1;
	fputs(b, f); fclose(f); return (int)strlen(b);
}
int f_read_string(const char *p, char *b, int max) {
	FILE *f = fopen(p, "r"); int n;
	if (!f) return -1;
	n = (int)fread(b, 1, max - 1, f); b[n > 0 ? n : 0] = '\0'; fclose(f); return n;
}
int notify_rc_after_wait(const char *ev) {
	FILE *f = fopen(LOGF, "a"); if (!f) return -1;
	fprintf(f, "%s\n", ev); fclose(f); return 0;
}
@DEFS@
@FN@
int main(void) { reaper_nasapps_settle(); return 0; }
'''

def build(td, name, fn_text, extra=()):
    defs = "\n".join(re.findall(r"^#define REAPER_NAS_(?:STAMP|SETTLE_S)\b.*$", src, re.M))
    defs = re.sub(r"(#define REAPER_NAS_SETTLE_S\s+)\d+", r"\g<1>1", defs)
    c = os.path.join(td, name + ".c")
    open(c, "w").write(HARNESS.replace("@DEFS@", defs).replace("@FN@", fn_text))
    exe = os.path.join(td, name)
    r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", '-DTMPD="%s"' % os.path.join(td, "reaper"),
                        '-DLOGF="%s"' % os.path.join(td, "log")] + list(extra) + ["-o", exe, c],
                       capture_output=True, text=True)
    return exe, r

def restarts(td):
    p = os.path.join(td, "log")
    return open(p).read().split() if os.path.exists(p) else []

def scenario(td, exe, gaps):
    """one process per event, `gaps` seconds before each; returns (restart count, slowest event)"""
    if os.path.exists(os.path.join(td, "log")):
        os.unlink(os.path.join(td, "log"))
    slow = 0.0
    for g in gaps:
        time.sleep(g)
        t = time.time(); subprocess.run([exe]); slow = max(slow, time.time() - t)
    time.sleep(2.2)  # settle window (1 s) + margin
    return len(restarts(td)), slow

gcc = shutil.which("gcc") or shutil.which("cc")
if gcc and fn:
    with tempfile.TemporaryDirectory() as td:
        exe, r = build(td, "t", fn)
        check("host gcc: reaper_nasapps_settle() compiles clean with -Wall -Wextra -Werror", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            n, slow = scenario(td, exe, [0])
            check("one event: one restart", n == 1, n)
            check("one event: the hotplug process returns at once (the wait is detached)", slow < 0.5, slow)
            n, _ = scenario(td, exe, [0, 0.2, 0.2])
            check("a wave of three mounts: one restart", n == 1, n)
            n, _ = scenario(td, exe, [0, 2.5])
            check("two waves: two restarts", n == 2, n)
            # the stamp must be written before the waiter is armed and be per-event
            check("the stamp file holds the newest event's token",
                  os.path.isfile(os.path.join(td, "reaper", "nasapps.settle")))
        exe2, r2 = build(td, "f", fn, ["-DFAIL_DIR"])
        if r2.returncode == 0:
            if os.path.exists(os.path.join(td, "log")):
                os.unlink(os.path.join(td, "log"))
            subprocess.run([exe2])
            check("fallback: no usable /tmp/reaper = immediate restart, as stock", len(restarts(td)) == 1,
                  restarts(td))
        # negative self-test: without the "still the newest" comparison the wave restarts 3x
        bad = fn.replace("strcmp(seen, mine) == 0", "1")
        exe3, r3 = build(td, "n", bad)
        if bad != fn and r3.returncode == 0:
            n, _ = scenario(td, exe3, [0, 0.2, 0.2])
            check("self-test: a settle without the newest-token check restarts per event (the wave check bites)",
                  n == 3, n)
        else:
            check("self-test: mutation applied and compiled", False, r3.stderr if bad != fn else "no match")
else:
    print("note: no host gcc - the compiled settle run is skipped")

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
