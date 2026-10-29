#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The USB boot chain: a late or absent USB volume must cost an addon its log, not the
LAN its resolver; a pre-mount hook that outlives its cap must take its children with it;
a busy device must be waited for; a soft lockup must log, not reboot; rtrafd's store
windows must survive the NTP step.

WHY THIS EXISTS. Field data (RT-BE86U, v3.3.1/v3.3.2, Entware on a USB SSD, 2026-10-02):
the stock boot order loads usb-storage/uas AFTER services-start, so a dnsmasq whose
postconf logs under /opt exited "cannot open log" on every boot and the LAN had no DNS
until the volume mounted (~60 s: amtm's disk check waits for NTP first) - or for good,
on the boots where the SSD never enumerated. Latent beside it: the 120 s pre-mount cap
is alarm() in the child, which kills the shell only; an e2fsck left behind holds the
device O_EXCL, mount() fails EBUSY and nothing ever retries. The kernel is built with
BOOTPARAM_SOFTLOCKUP_PANIC=y, so a long I/O stall is a PANIC and a reboot with no trace.

THE FIX (v3.3.3). rc/services.c: reaper_dnsmasq_log_guard() drops a log-facility whose
directory is missing or not writable after the postconf, logs it and leaves a flag;
rc/watchdog.c restarts dnsmasq once the directory exists. shared/scripts.c:
run_custom_script_bounded() + reaper_wait_pgrp() - pre-mount's cap now TERMs, then
KILLs the whole process group. rc/usb.c: mount_r() waits out EBUSY on an ext volume.
rc/init.c: kernel.softlockup_panic=0. rtrafd: STORE_RETRY_SECS/LATE_LOAD_SECS on
CLOCK_MONOTONIC.

WHAT IT DOES.
  1. Extracts reaper_logdir_unusable() + reaper_dnsmasq_log_guard() from rc/services.c,
     compiles them on the host and runs them on real files: a missing directory is
     dropped (path reported, the rest byte-identical, mode 0644), an existing one is
     kept and the file is not touched, facility names and `-` pass, leading whitespace
     is handled, a read-only directory is dropped, a missing conf is -1; v3.3.3: a
     missing conf-file / conf-dir is dropped the same way (one "<kind> <path>" line
     each), and reaper_dnsmasq_dep_missing() - the predicate the watchdog shares -
     judges L/F/D exactly as the guard does.
  2b. (v3.3.3) Extracts reaper_slp_should_arm() from rc/watchdog.c and runs it: the
     soft-lockup panic is armed only after REAPER_SLP_FLOOR_SECS of uptime and
     REAPER_SLP_GRACE_SECS after the last USB mount activity (rc/usb.c stamps every
     mount and drops the panic itself); a USB that never enumerates still arms at
     the floor.
  2. Extracts reaper_wait_pgrp() from shared/scripts.c and runs it against a real
     session leader the way _eval() makes one (fork, setsid, sh -c): a script that
     outlives the cap is stopped with its background child; one that exits in time
     returns at once; a child it leaves behind on a normal exit is left alone.
  3. Asserts on the source that every hook is wired: pre-mount on the bounded runner,
     post-mount/unmount still stock, the EBUSY wait inside mount_r's ext branch, the
     guard between run_postconf and chmod, the watchdog check inside dnsmasq_check
     after the flash-flag gate, the flag in rc.h, the sysctl after panic_on_oops, and
     rtrafd on the monotonic clock with no wall-clock window left.

Exit 0 pass, 1 fail, 77 skipped (no gcc, not Linux, or no router source tree - pass
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, stat, subprocess, sys, tempfile

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

services = read("rc/services.c")
scripts = read("shared/scripts.c")
shared_h = read("shared/shared.h")
usb = read("rc/usb.c")
watchdog = read("rc/watchdog.c")
init = read("rc/init.c")
rc_h = read("rc/rc.h")
rtrafd = read("rtrafd/rtrafd.c")

def slice_fn(text, start_marker, end_marker, what):
    a = text.find(start_marker)
    b = text.find(end_marker, a + 1) if a >= 0 else -1
    if a < 0 or b < 0:
        die("%s: markers not found (%r .. %r)" % (what, start_marker[:40], end_marker[:40]))
    return text[a:b + len(end_marker)]

gcc = shutil.which("gcc") or shutil.which("cc")
if not gcc:
    skip("no host C compiler")
if not sys.platform.startswith("linux"):
    skip("process groups and /proc - Linux only")

def compile_c(src, name, tmp):
    csrc = os.path.join(tmp, name + ".c")
    exe = os.path.join(tmp, name)
    with open(csrc, "w") as f:
        f.write(src)
    r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-O1", csrc, "-o", exe],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        die("%s does not compile on the host:\n%s" % (name, r.stdout))
    return exe

# ---------------------------------------------------------------- 1. the dnsmasq log guard, on real files
guard_src = slice_fn(services, "/* reaper v3.3.3: a `log-facility=/path` whose directory",
                     "\treturn n;\n}\n", "rc/services.c log guard")
for fn in ("static int reaper_logdir_unusable(const char *path)",
           "int reaper_dnsmasq_dep_missing(char kind, const char *path)",
           "static int reaper_dnsmasq_log_guard(const char *conf, char *dropped, size_t dsz)"):
    if fn not in guard_src:
        die("rc/services.c: %s not in the guard slice" % fn)

guard_harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
static size_t rlg_strlcpy(char *d, const char *s, size_t n)
{
    size_t l = strlen(s);
    if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = '\0'; }
    return l;
}
#define strlcpy rlg_strlcpy
%s
int main(int argc, char **argv)
{
    char dropped[1024], *p;
    int n;
    if (argc < 2) return 2;
    n = reaper_dnsmasq_log_guard(argv[1], dropped, sizeof dropped);
    for (p = dropped; *p; p++)
        if (*p == '\n') *p = '|';
    printf("n=%%d dropped=%%s\n", n, dropped);
    if (argc > 3)	/* dep <kind> <path>: the predicate the watchdog shares */
        printf("missing=%%d\n", reaper_dnsmasq_dep_missing(argv[2][0], argv[3]));
    return 0;
}
''' % guard_src

pgrp_src = slice_fn(scripts, "/* reaper v3.3.3: wait for `pid`", "\treturn 1;\n}\n", "shared/scripts.c reaper_wait_pgrp")
if "int reaper_wait_pgrp(pid_t pid, int timeout, int grace)" not in pgrp_src:
    die("shared/scripts.c: reaper_wait_pgrp not in the slice")

pgrp_harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/wait.h>
%s
/* what _eval() does with ppid set: fork, setsid in the child, exec */
static pid_t spawn(const char *cmd)
{
    pid_t p = fork();
    if (p == 0) {
        setsid();
        execl("/bin/sh", "sh", "-c", cmd, (char *)NULL);
        _exit(127);
    }
    return p;
}
int main(int argc, char **argv)
{
    pid_t p;
    int r, alive;
    if (argc < 2) return 2;
    if (!strcmp(argv[1], "timeout")) {
        p = spawn("sleep 300 & exec sleep 300");	/* leader + one child in the group */
        usleep(200000);
        r = reaper_wait_pgrp(p, 1, 2);
        alive = (kill(-p, 0) == 0);
    } else if (!strcmp(argv[1], "quick")) {
        p = spawn("exit 0");
        r = reaper_wait_pgrp(p, 5, 2);
        alive = (kill(-p, 0) == 0);
    } else {	/* leaves: the leader exits in time and leaves a child behind */
        p = spawn("sleep 300 & exit 0");
        r = reaper_wait_pgrp(p, 5, 2);
        usleep(200000);
        alive = (kill(-p, 0) == 0);
        kill(-p, SIGKILL);	/* clean up */
    }
    printf("r=%%d alive=%%d\n", r, alive);
    return 0;
}
''' % pgrp_src

tmp = tempfile.mkdtemp(prefix="usbboot-")
try:
    exe = compile_c(guard_harness, "guard", tmp)
    ok("rc/services.c log guard compiles on the host (-Wall -Wextra -Werror)")

    def run_guard(conf):
        out = subprocess.run([exe, conf], stdout=subprocess.PIPE, text=True, timeout=20).stdout.strip()
        m = re.match(r"n=(-?\d+) dropped=(.*)", out)
        if not m:
            die("guard harness output unexpected: %r" % out)
        return int(m.group(1)), m.group(2)

    def write(name, body):
        p = os.path.join(tmp, name)
        with open(p, "w") as f:
            f.write(body)
        os.chmod(p, 0o666)	# rc runs umask 0; a rewritten file must still come back 0644
        return p

    missing = os.path.join(tmp, "no_such_dir", "sub")
    good = os.path.join(tmp, "logdir")
    os.makedirs(good)

    # (a) missing directory: dropped, the rest byte-identical, 0644, no temp file
    c = write("a.conf", "pid-file=/var/run/dnsmasq.pid\nlog-facility=%s/dnsmasq.log\ncache-size=1500\n" % missing)
    n, d = run_guard(c)
    if n != 1 or d != "L " + missing + "/dnsmasq.log|":
        die("(a) expected n=1 with the path, got n=%d dropped=%s" % (n, d))
    body = open(c).read()
    if body != "pid-file=/var/run/dnsmasq.pid\ncache-size=1500\n":
        die("(a) rewritten conf wrong: %r" % body)
    mode = stat.S_IMODE(os.stat(c).st_mode)
    if mode != 0o644:
        die("(a) rewritten conf mode %o, expected 0644" % mode)
    if os.path.exists(c + ".rlg"):
        die("(a) temp file left behind")
    ok("(a) a log-facility into a missing directory is dropped; other lines intact; 0644; no temp file")

    # (b) existing writable directory: kept, file not touched at all
    c = write("b.conf", "log-facility=%s/dnsmasq.log\ncache-size=1500\n" % good)
    st0 = os.stat(c)
    before = (open(c, "rb").read(), st0.st_mtime_ns, st0.st_ino, stat.S_IMODE(st0.st_mode))
    n, d = run_guard(c)
    st1 = os.stat(c)
    after = (open(c, "rb").read(), st1.st_mtime_ns, st1.st_ino, stat.S_IMODE(st1.st_mode))
    if n != 0 or d != "" or before != after:
        die("(b) existing directory: n=%d dropped=%r touched=%s" % (n, d, before != after))
    ok("(b) a log-facility into an existing directory is kept and the file is not touched")

    # (c) syslog facility names and stderr pass
    c = write("c.conf", "log-facility=DAEMON\nlog-facility=-\nlog-queries\n")
    n, d = run_guard(c)
    if n != 0 or open(c).read() != "log-facility=DAEMON\nlog-facility=-\nlog-queries\n":
        die("(c) facility/stderr forms were touched (n=%d)" % n)
    ok("(c) syslog facility names and `-` pass through")

    # (d) leading whitespace; two bad, one good; first dropped path reported
    c = write("d.conf", "  \tlog-facility=%s/x.log\nlog-facility=%s/y.log\nlog-facility=%s/z.log\n" % (missing, good, missing))
    n, d = run_guard(c)
    body = open(c).read()
    if n != 2 or d != "L %s/x.log|L %s/z.log|" % (missing, missing) or body != "log-facility=%s/y.log\n" % good:
        die("(d) n=%d dropped=%s body=%r" % (n, d, body))
    ok("(d) leading whitespace handled; two dropped, the good one kept; both reported, one line each")

    # (e) read-only directory (root passes access(W_OK) on a 0555 dir, so not as root)
    if os.geteuid() != 0:
        ro = os.path.join(tmp, "ro")
        os.makedirs(ro)
        os.chmod(ro, 0o555)
        c = write("e.conf", "log-facility=%s/dnsmasq.log\n" % ro)
        n, d = run_guard(c)
        os.chmod(ro, 0o755)
        if n != 1:
            die("(e) read-only directory not dropped (n=%d)" % n)
        ok("(e) a read-only directory is dropped too (dnsmasq could not open the log there either)")
    else:
        print("note (e) skipped: running as root, access(W_OK) always passes")

    # (f) missing conf
    n, d = run_guard(os.path.join(tmp, "nope.conf"))
    if n != -1:
        die("(f) missing conf should be -1, got %d" % n)
    ok("(f) an unreadable conf is reported, not rewritten")

    # (g) conf-file / conf-dir (v3.3.3): dnsmasq dies on a missing one exactly like a bad log dir
    inc = write("inc.conf", "address=/x.test/0.0.0.0\n")
    c = write("g.conf", "conf-file=%s/extra.conf\nconf-file=%s\nconf-dir=%s,.bak\nconf-dir=%s,*.conf\ncache-size=1500\n"
              % (missing, inc, missing, good))
    n, d = run_guard(c)
    body = open(c).read()
    want_d = "F %s/extra.conf|D %s|" % (missing, missing)
    want_b = "conf-file=%s\nconf-dir=%s,*.conf\ncache-size=1500\n" % (inc, good)
    if n != 2 or d != want_d or body != want_b:
        die("(g) n=%d dropped=%r body=%r" % (n, d, body))
    ok("(g) a missing conf-file and conf-dir are dropped (suffix list ignored for the judgement); present ones kept")

    # (h) one conf with all three kinds missing: one line per kind, in file order
    c = write("h.conf", "conf-dir=%s\nlog-facility=%s/l.log\nconf-file=%s/f.conf\n" % (missing, missing, missing))
    n, d = run_guard(c)
    if n != 3 or d != "D %s|L %s/l.log|F %s/f.conf|" % (missing, missing, missing) or open(c).read() != "":
        die("(h) n=%d dropped=%r" % (n, d))
    ok("(h) all three kinds in one conf: three lines, kinds L/F/D, file order")

    # (i) the shared predicate the watchdog uses agrees with the guard
    def dep(kind, path):
        out = subprocess.run([exe, os.path.join(tmp, "b.conf"), kind, path], stdout=subprocess.PIPE,
                             text=True, timeout=20).stdout
        m = re.search(r"missing=(\d)", out)
        if not m:
            die("(i) predicate output unexpected: %r" % out)
        return int(m.group(1))
    cases = [("L", missing + "/a.log", 1), ("L", good + "/a.log", 0), ("F", missing + "/f", 1), ("F", inc, 0),
             ("D", missing, 1), ("D", good, 0), ("D", inc, 1)]
    for kind, path, want in cases:
        if dep(kind, path) != want:
            die("(i) dep_missing(%s, %s) != %d" % (kind, path, want))
    ok("(i) reaper_dnsmasq_dep_missing: L/F/D judged as the guard judges (a file is not a conf-dir)")

    # ------------------------------------------------------------ 2. the process-group wait, for real
    exe2 = compile_c(pgrp_harness, "pgrp", tmp)
    ok("shared/scripts.c reaper_wait_pgrp compiles on the host (-Wall -Wextra -Werror)")

    def run_pgrp(case):
        out = subprocess.run([exe2, case], stdout=subprocess.PIPE, text=True, timeout=30).stdout.strip()
        m = re.match(r"r=(\d+) alive=(\d+)", out)
        if not m:
            die("pgrp harness output unexpected for %s: %r" % (case, out))
        return int(m.group(1)), int(m.group(2))

    r, alive = run_pgrp("timeout")
    if r != 1 or alive != 0:
        die("timeout case: expected r=1 alive=0 (group stopped), got r=%d alive=%d" % (r, alive))
    ok("a script that outlives the cap is stopped together with its background child (r=1, group gone)")
    r, alive = run_pgrp("quick")
    if r != 0:
        die("quick case: expected r=0, got %d" % r)
    ok("a script that exits in time returns 0 at once")
    r, alive = run_pgrp("leaves")
    if r != 0 or alive != 1:
        die("leaves case: expected r=0 alive=1 (child left alone), got r=%d alive=%d" % (r, alive))
    ok("a child a script leaves behind on a normal exit is left alone (documented behaviour)")

    # ------------------------------------------------------------ 2b. v3.3.3: when the soft-lockup panic may be armed
    slp_src = slice_fn(watchdog, "/* reaper v3.3.3: when the soft-lockup panic may be on", "\treturn 1;\n}\n",
                       "rc/watchdog.c reaper_slp_should_arm")
    if "int reaper_slp_should_arm(unsigned long up, unsigned long stamp, int have_stamp, unsigned long floor, unsigned long grace)" not in slp_src:
        die("rc/watchdog.c: reaper_slp_should_arm not in the slice")
    slp_harness = r'''
#include <stdio.h>
#include <stdlib.h>
%s
int main(int argc, char **argv)
{
    if (argc < 6) return 2;
    printf("%%d\n", reaper_slp_should_arm(strtoul(argv[1], 0, 10), strtoul(argv[2], 0, 10), atoi(argv[3]),
                                          strtoul(argv[4], 0, 10), strtoul(argv[5], 0, 10)));
    return 0;
}
''' % slp_src
    exe3 = compile_c(slp_harness, "slp", tmp)
    ok("rc/watchdog.c reaper_slp_should_arm compiles on the host (-Wall -Wextra -Werror)")
    def arm(up, stamp, have):
        out = subprocess.run([exe3, str(up), str(stamp), str(have), "600", "300"], stdout=subprocess.PIPE,
                             text=True, timeout=10).stdout.strip()
        if out not in ("0", "1"):
            die("slp harness output unexpected: %r" % out)
        return int(out)
    for up, stamp, have, want, what in (
        (599, 0, 0, 0, "below the floor, no mount ever: stays off"),
        (600, 0, 0, 1, "at the floor, no mount ever (USB never enumerated): armed"),
        (900, 700, 1, 0, "200 s after a mount: still off"),
        (1000, 700, 1, 1, "300 s after a mount: armed"),
        (1000, 1500, 1, 0, "a stamp from the future counts as activity"),
        (100000, 99999, 1, 0, "a replug hours in: off again"),
        (10000, 0, 1, 1, "an ancient stamp: armed"),
    ):
        if arm(up, stamp, have) != want:
            die("reaper_slp_should_arm(%d, %d, %d) != %d: %s" % (up, stamp, have, want, what))
    ok("reaper_slp_should_arm: floor, grace after the last mount, future stamp, replug - all as specified")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- 3. every surface is wired
checks = [
    (usb, 'run_custom_script_bounded("pre-mount", 300, dev_name, type);', 1, "rc/usb.c: pre-mount runs on the bounded runner, 300 s (v3.3.3: the cap cancels the disk check too)"),
    (usb, 'run_custom_script("post-mount", 120, mountpoint, NULL);', 1, "rc/usb.c: post-mount still on the stock runner"),
    (usb, 'run_custom_script("unmount", 120, mnt->mnt_dir, NULL);', 1, "rc/usb.c: unmount still on the stock runner"),
    (usb, "#define REAPER_MOUNT_BUSY_SECS 120", 1, "rc/usb.c: the EBUSY wait is bounded at 120 s"),
    (usb, "static int reaper_mount_wait_busy(", 1, "rc/usb.c: reaper_mount_wait_busy defined"),
    (usb, "if (ret != 0 && errno == EBUSY)", 1, "rc/usb.c: the EBUSY hook"),
    (scripts, "int run_custom_script_bounded(char *name, int timeout, char *arg1, char *arg2)", 1, "shared/scripts.c: run_custom_script_bounded defined"),
    (scripts, "int reaper_wait_pgrp(pid_t pid, int timeout, int grace)", 1, "shared/scripts.c: reaper_wait_pgrp defined"),
    (scripts, "did not finish in %d s - stopped it and everything it started", 1, "shared/scripts.c: the timeout is logged"),
    (shared_h, "extern int run_custom_script_bounded(", 1, "shared/shared.h: prototype"),
    (shared_h, "extern int reaper_wait_pgrp(", 1, "shared/shared.h: prototype"),
    (rc_h, '#define REAPER_DNSMASQ_LOGDROP_FLAG\t"/tmp/reaper/.reaper_dnsmasq_logdrop"', 1, "rc/rc.h: the logdrop flag"),
    (services, "static int reaper_dnsmasq_log_guard(const char *conf, char *dropped, size_t dsz)", 1, "rc/services.c: guard defined"),
    (services, "f_write_string(REAPER_DNSMASQ_LOGDROP_FLAG, lg, 0, 0);", 1, "rc/services.c: the flag carries the dropped items"),
    (rc_h, "extern int reaper_dnsmasq_dep_missing(char kind, const char *path);", 1, "rc/rc.h: the shared predicate's prototype"),
    (watchdog, "!reaper_dnsmasq_dep_missing(p[0], p + 2)", 1, "rc/watchdog.c: the restart uses the guard's predicate"),
    (services, "unlink(REAPER_DNSMASQ_LOGDROP_FLAG);", 1, "rc/services.c: a clean start clears the flag"),
    (watchdog, "static void reaper_dnsmasq_logdrop_check(void)", 1, "rc/watchdog.c: logdrop check defined"),
    (watchdog, "reaper_dnsmasq_logdrop_check();", 1, "rc/watchdog.c: called once"),
    (init, 'f_write_string("/proc/sys/kernel/softlockup_panic", "0", 0, 0);', 1, "rc/init.c: softlockup_panic=0"),
    (rc_h, '#define REAPER_USB_MOUNT_STAMP\t"/tmp/reaper/.reaper_usb_mount_at"', 1, "rc/rc.h: the mount stamp"),
    (rc_h, "#define REAPER_SLP_FLOOR_SECS", 1, "rc/rc.h: the arm floor"),
    (rc_h, "#define REAPER_SLP_GRACE_SECS", 1, "rc/rc.h: the arm grace"),
    (usb, "void reaper_usb_mount_stamp(void)", 1, "rc/usb.c: reaper_usb_mount_stamp defined"),
    (usb, "reaper_usb_mount_stamp();", 2, "rc/usb.c: stamped twice (entry, after post-mount)"),
    (watchdog, "static void reaper_softlockup_arm_check(void)", 1, "rc/watchdog.c: arm check defined"),
    (watchdog, "reaper_softlockup_arm_check();", 1, "rc/watchdog.c: arm check called once"),
    (watchdog, 'f_write_string("/proc/sys/kernel/softlockup_panic", want ? "1" : "0", 0, 0);', 1, "rc/watchdog.c: the arm writes the sysctl"),
    (rtrafd, "static time_t mono_secs(void)", 1, "rtrafd: mono_secs defined"),
    (rtrafd, "now_m - boot_m <= STORE_RETRY_SECS", 1, "rtrafd: the retry window is monotonic"),
    (rtrafd, "now_m - boot_m <= LATE_LOAD_SECS", 1, "rtrafd: the late-load window is monotonic"),
    (rtrafd, "boot_t", 0, "rtrafd: no wall-clock boot_t left"),
]
for text, needle, want, what in checks:
    n = text.count(needle)
    if n != want:
        die("%s: %r found %d times, expected %d" % (what, needle, n, want))
    ok(what)

# order: guard sits between the postconf and the chmod, in start_dnsmasq's main path
i_post = services.index('run_postconf("dnsmasq","/etc/dnsmasq.conf");')
i_guard = services.index('reaper_dnsmasq_log_guard("/etc/dnsmasq.conf", lg, sizeof(lg))')
i_chmod = services.index('chmod("/etc/dnsmasq.conf", 0644);', i_post)
if not (i_post < i_guard < i_chmod):
    die("rc/services.c: the guard is not between run_postconf and chmod")
ok("rc/services.c: the guard runs after the postconf and before the chmod")

# order: the watchdog check sits inside dnsmasq_check after the flash-flag gate, before the per-SDN scan
fn = watchdog.index("void dnsmasq_check()")
i_rel = watchdog.index("REAPER_USBREL_FLAG", fn)
i_call = watchdog.index("reaper_dnsmasq_logdrop_check();", fn)
i_scan = watchdog.index("#ifdef RTCONFIG_MULTILAN_CFG", fn)
if not (i_rel < i_call < i_scan):
    die("rc/watchdog.c: the logdrop check is not gated by the flash flag inside dnsmasq_check")
ok("rc/watchdog.c: the logdrop check runs inside dnsmasq_check, after the flash-flag gate")
# and the watchdog restarts the main LAN instance only
if "start_dnsmasq(0);" not in watchdog[i_call - 2000:i_call]:
    die("rc/watchdog.c: the logdrop check does not restart the main LAN instance (start_dnsmasq(0))")
ok("rc/watchdog.c: the restart targets the main LAN instance")

# order: the sysctl follows the stock panic_on_oops write
i_oops = init.index('f_write_string("/proc/sys/kernel/panic_on_oops", "3", 0, 0);')
i_sl = init.index("/proc/sys/kernel/softlockup_panic")
if not (i_oops < i_sl < i_oops + 1500):
    die("rc/init.c: softlockup_panic is not written beside panic_on_oops")
ok("rc/init.c: softlockup_panic=0 sits beside the stock panic policy")

# the EBUSY hook is on the FIRST ext mount inside mount_r, before the ext3/ext2 fallbacks
i_mr = usb.index("int mount_r(char *mnt_dev")
i_ext = usb.index('if(!strncmp(type, "ext", 3)){\n\t\t\t\tret = mount(', i_mr)
i_hook = usb.index("if (ret != 0 && errno == EBUSY)", i_mr)
i_fb = usb.index('snprintf(type, 16, "ext3");', i_ext)
if not (i_ext < i_hook < i_fb):
    die("rc/usb.c: the EBUSY wait is not on the first ext mount before the fallbacks")
ok("rc/usb.c: the EBUSY wait precedes the ext3/ext2/ext fallbacks")

# the bounded pre-mount is the one in mount_partition
i_mp = usb.index("int mount_partition(char *dev_name")
if usb.index('run_custom_script_bounded("pre-mount"', i_mp) > i_mp + 3000:
    die("rc/usb.c: the bounded pre-mount is not at the top of mount_partition")
ok("rc/usb.c: the bounded pre-mount is at the top of mount_partition")

# v3.3.3: the stamp (and the panic drop) comes before pre-mount, and again right after post-mount
i_pre = usb.index('run_custom_script_bounded("pre-mount"', i_mp)
i_s1 = usb.index("reaper_usb_mount_stamp();", i_mp)
i_post = usb.index('run_custom_script("post-mount", 120, mountpoint, NULL);', i_mp)
i_s2 = usb.index("reaper_usb_mount_stamp();", i_post)
if not (i_mp < i_s1 < i_pre and i_post < i_s2 < i_post + 200):
    die("rc/usb.c: the mount stamps are not before pre-mount and right after post-mount")
i_def = usb.index("void reaper_usb_mount_stamp(void)")
if not ('f_write_string("/proc/sys/kernel/softlockup_panic", "0", 0, 0);' in usb[i_def:i_def + 600]
        and "REAPER_USB_MOUNT_STAMP" in usb[i_def:i_def + 600]):
    die("rc/usb.c: reaper_usb_mount_stamp must drop the panic and write the stamp")
ok("rc/usb.c: every mount drops the soft-lockup panic itself and stamps the time, before pre-mount and after post-mount")
fn = watchdog.index("void watchdog(int sig)")
i_dc = watchdog.index("dnsmasq_check();", fn)
i_arm = watchdog.index("reaper_softlockup_arm_check();", fn)
if not (i_dc < i_arm < i_dc + 200):
    die("rc/watchdog.c: the arm check is not on the 1 s tick beside dnsmasq_check")
ok("rc/watchdog.c: the arm check runs on the watchdog tick")

print("PASS: the USB boot chain fixes are present on all six surfaces")
