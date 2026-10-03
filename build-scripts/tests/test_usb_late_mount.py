#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The USB mount watchdog (rc/reaper_usbmon.c, v3.3.3): a partition whose one mount
event failed is asked for again; a flash that released the volumes and never happened
gives them back; a disk-less bus on a box that expects a volume is re-enumerated once.

WHY THIS EXISTS. The end-to-end review of the mount lifecycle (2026-10-02) left one
structural hole: the kernel's add event is the only thing that ever asks for a mount.
A disk check still holding the device, an EBUSY wait that runs out, an event dropped
while the action lock was busy - and the volume stays unmounted until a replug. Stock
re-sends the events only on `rc restart`. Beside it: an aborted flash leaves the
release flag set (dnsmasq check standing down, services-stop skipped) with the volumes
ejected; and RT-BE96U/RT-BE86U have no USB power control, so a wedged UAS enclosure is
never power-cycled at boot.

WHAT IT DOES.
  1. Compiles the libc-only helpers on the host and runs them on FAKE trees:
     candidates from a /sys/block-shaped tree against a /proc/mounts-shaped file and
     the mounted markers (a mounted partition, a marked one and a non-sd device are
     left out; a partition-less disk is a candidate by itself); the SCSI host from the
     device link; the minor from the dev file; the bus state from a
     /sys/bus/usb/devices-shaped tree (hubs only / storage / other); and the usb lock
     probe against a REAL fcntl write lock held by this process.
  2. Asserts on the source that every surface is wired: mount_partition marks a
     mount, the watchdog tick calls the check, the gates (release flag, usb_automount,
     action idle, lock busy, 3 tries, the window), the re-sent event carries the
     fields hotplug_usb's block branch reads, the aborted-flash restore, the recovery
     gates and its UNTESTED wording, Makefile and rc.h.

Exit 0 pass, 1 fail, 77 skipped (no gcc, not Linux, or no router source tree - pass
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import fcntl, os, re, shutil, subprocess, sys, tempfile

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

mon = read("rc/reaper_usbmon.c")
usb = read("rc/usb.c")
watchdog = read("rc/watchdog.c")
rc_h = read("rc/rc.h")
mk = read("rc/Makefile")

gcc = shutil.which("gcc") or shutil.which("cc")
if not gcc:
    skip("no host C compiler")
if not sys.platform.startswith("linux"):
    skip("fcntl locks and sysfs shapes - Linux only")

# ---------------------------------------------------------------- 1. the helpers, on fake trees
a = mon.find("/* ---- libc only, from here")
b = mon.find("/* ---- rc side ---- */")
if a < 0 or b < 0 or b <= a:
    die("rc/reaper_usbmon.c: helper markers not found")
helpers = mon[a:b]
for fn in ("int reaper_usbmon_candidates(", "int reaper_usbmon_host_of(", "int reaper_usbmon_minor_of(",
           "int reaper_usbmon_usb_state(", "int reaper_usbmon_lock_busy("):
    if fn not in helpers:
        die("rc/reaper_usbmon.c: %s not in the helper slice" % fn)

harness = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <dirent.h>
#include <fcntl.h>
#include <limits.h>
#include <sys/types.h>
#include <sys/stat.h>
%s
int main(int argc, char **argv)
{
    char out[1024], *p; int n, nd = 0;
    if (argc < 2) return 2;
    if (!strcmp(argv[1], "cand") && argc > 4) {
        n = reaper_usbmon_candidates(argv[2], argv[3], argv[4], out, sizeof out, &nd);
        for (p = out; *p; p++) if (*p == '\n') *p = '|';
        printf("n=%%d disks=%%d list=%%s\n", n, nd, out);
    } else if (!strcmp(argv[1], "host") && argc > 3) {
        printf("r=%%d host=%%s\n", reaper_usbmon_host_of(argv[2], argv[3], out, sizeof out), out);
    } else if (!strcmp(argv[1], "minor") && argc > 4) {
        printf("minor=%%d\n", reaper_usbmon_minor_of(argv[2], argv[3], argv[4]));
    } else if (!strcmp(argv[1], "usb") && argc > 2) {
        printf("st=%%d dev=%%s\n", reaper_usbmon_usb_state(argv[2], out, sizeof out), out);
    } else if (!strcmp(argv[1], "lock") && argc > 2) {
        printf("busy=%%d\n", reaper_usbmon_lock_busy(argv[2]));
    } else return 2;
    return 0;
}
''' % helpers

def w(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(body)

tmp = tempfile.mkdtemp(prefix="usbmon-")
try:
    csrc = os.path.join(tmp, "h.c"); exe = os.path.join(tmp, "h")
    with open(csrc, "w") as f:
        f.write(harness)
    r = subprocess.run([gcc, "-Wall", "-Wextra", "-Werror", "-O1", csrc, "-o", exe],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        die("helpers do not compile on the host:\n" + r.stdout)
    ok("rc/reaper_usbmon.c helpers compile on the host (-Wall -Wextra -Werror)")

    def run(*args):
        return subprocess.run([exe] + list(args), stdout=subprocess.PIPE, text=True, timeout=20).stdout.strip()

    # a fake /sys/block: sda with two partitions on host 3, sdb with none, a non-sd device
    blk = os.path.join(tmp, "block")
    w(os.path.join(blk, "sda", "sda1", "dev"), "8:1\n")
    w(os.path.join(blk, "sda", "sda2", "dev"), "8:2\n")
    w(os.path.join(blk, "sda", "dev"), "8:0\n")
    os.symlink("../../../devices/platform/8000d000.usb/usb2/2-1/2-1:1.0/host3/target3:0:0/3:0:0:0",
               os.path.join(blk, "sda", "device"))
    w(os.path.join(blk, "sdb", "dev"), "8:16\n")
    os.makedirs(os.path.join(blk, "mmcblk0"))
    w(os.path.join(blk, "mmcblk0", "dev"), "179:0\n")
    mounts = os.path.join(tmp, "mounts")
    w(mounts, "rootfs / rootfs rw 0 0\n/dev/sda1 /tmp/mnt/ssd ext4 rw,nodev 0 0\ntmpfs /tmp tmpfs rw 0 0\n")
    markp = os.path.join(tmp, ".mounted_")
    w(markp + "sdb", "1")

    out = run("cand", blk, mounts, markp)
    if out != "n=1 disks=2 list=sda2|":
        die("(a) candidates: expected sda2 only (sda1 mounted, sdb marked, mmcblk0 not sd), got %r" % out)
    ok("(a) a mounted partition, a marked one and a non-sd device are not candidates; disks counted")
    os.unlink(markp + "sdb")
    out = run("cand", blk, mounts, markp)
    m = re.match(r"n=2 disks=2 list=(.*)", out)
    if not m or sorted(x for x in m.group(1).split("|") if x) != ["sda2", "sdb"]:	# readdir order is not sorted
        die("(b) without the marker a partition-less disk is a candidate by itself; got %r" % out)
    ok("(b) a partition-less disk is a candidate by itself once unmarked")
    w(markp + "sda2", "1")
    out = run("cand", blk, mounts, markp)
    if out != "n=1 disks=2 list=sdb|":
        die("(c) a marked partition drops out: %r" % out)
    ok("(c) marking a partition (mount_partition's done path) removes it from the retry")
    out = run("cand", os.path.join(tmp, "nope"), mounts, markp)
    if out != "n=0 disks=0 list=":
        die("(d) a missing tree: %r" % out)
    ok("(d) no /sys/block: nothing to do, zero disks")

    out = run("host", blk, "sda")
    if out != "r=1 host=3":
        die("(e) host from the device link: %r" % out)
    out2 = run("host", blk, "sdb")
    if out2 != "r=0 host=":
        die("(e) a disk without a device link: %r" % out2)
    ok("(e) the SCSI host is read from the device link; absent link = unknown")

    if run("minor", blk, "sda", "sda2") != "minor=2" or run("minor", blk, "sdb", "sdb") != "minor=16" \
            or run("minor", blk, "sda", "sda9") != "minor=-1":
        die("(f) minors: %r %r %r" % (run("minor", blk, "sda", "sda2"), run("minor", blk, "sdb", "sdb"), run("minor", blk, "sda", "sda9")))
    ok("(f) partition and whole-disk minors from the dev file; unknown = -1")

    # a fake /sys/bus/usb/devices
    ud = os.path.join(tmp, "usbdev")
    w(os.path.join(ud, "usb1", "bDeviceClass"), "09\n")
    w(os.path.join(ud, "usb2", "bDeviceClass"), "09\n")
    w(os.path.join(ud, "1-1", "bDeviceClass"), "09\n")          # an external hub
    if run("usb", ud) != "st=0 dev=":
        die("(g) hubs only should be state 0: %r" % run("usb", ud))
    w(os.path.join(ud, "1-2", "bDeviceClass"), "03\n")          # a HID gadget
    if run("usb", ud) != "st=2 dev=":
        die("(g) other device should be state 2: %r" % run("usb", ud))
    w(os.path.join(ud, "2-1", "bDeviceClass"), "00\n")
    w(os.path.join(ud, "2-1:1.0", "bInterfaceClass"), "08\n")   # mass storage interface
    if run("usb", ud) != "st=1 dev=2-1":
        die("(g) a storage interface should win with its device name: %r" % run("usb", ud))
    ok("(g) bus state: hubs only = 0, other devices = 2, a storage-class interface = 1 with its device")

    # the usb lock probe against a real fcntl write lock
    lf = os.path.join(tmp, "usb.lock")
    fd = os.open(lf, os.O_RDWR | os.O_CREAT, 0o666)
    if run("lock", lf) != "busy=0":
        die("(h) an unlocked lock file reads busy")
    fcntl.lockf(fd, fcntl.LOCK_EX)
    if run("lock", lf) != "busy=1":
        die("(h) a held write lock was not seen")
    fcntl.lockf(fd, fcntl.LOCK_UN)
    if run("lock", lf) != "busy=0":
        die("(h) a released lock still reads busy")
    os.close(fd)
    if run("lock", os.path.join(tmp, "absent.lock")) != "busy=0":
        die("(h) a missing lock file should read free")
    ok("(h) the usb lock probe sees a held fcntl write lock, and only then")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- 2. every surface is wired
checks = [
    (usb, "reaper_usb_mounted_mark(pt_name);", 1, "rc/usb.c: a successful mount is marked"),
    (usb, 'run_custom_script_bounded("pre-mount", 300, dev_name, type);', 1, "rc/usb.c: the pre-mount cap is 300 s"),
    (watchdog, "reaper_usbmon_check();", 1, "rc/watchdog.c: the check is on the tick, once"),
    (rc_h, '#define REAPER_USB_MOUNTED_MARK\t"/tmp/.reaper_usb_mounted_"', 1, "rc/rc.h: the mounted marker"),
    (rc_h, '#define REAPER_USB_RETRY_MARK\t"/tmp/.reaper_usb_retry_"', 1, "rc/rc.h: the retry counter"),
    (rc_h, "#define REAPER_USB_RETRY_MAX\t3", 1, "rc/rc.h: three tries"),
    (rc_h, "extern void reaper_usbmon_check(void);", 1, "rc/rc.h: prototype"),
    (rc_h, "extern void reaper_usb_mounted_mark(const char *part);", 1, "rc/rc.h: prototype"),
    (mk, "OBJS += reaper_usbmon.o", 1, "rc/Makefile: built into rc"),
    (mon, "if (f_exists(REAPER_USBREL_FLAG))\n\t\treturn;", 1, "usbmon: nothing while a flash is releasing the volumes"),
    (mon, 'nvram_get_int("usb_automount")', 1, "usbmon: honours usb_automount"),
    (mon, "if (check_action() != ACT_IDLE)\n\t\treturn;", 1, "usbmon: nothing while the box is busy (flash, restore)"),
    (mon, 'reaper_usbmon_lock_busy("/var/lock/usb.lock")', 1, "usbmon: a mount in progress is left to finish"),
    (mon, ">= REAPER_USB_RETRY_MAX", 1, "usbmon: bounded tries"),
    (mon, '"/sbin/hotplug", "block"', 1, "usbmon: the re-sent event goes to the stock handler"),
    (mon, "_eval(argv, NULL, 0, &pid);", 1, "usbmon: the re-send is backgrounded"),
    (mon, "unlink(REAPER_USBREL_FLAG);", 1, "usbmon: an aborted flash clears the release flag"),
    (mon, "start_rtraf();", 1, "usbmon: and brings rtrafd back"),
    (mon, 'add_remove_usbhost("-1", 1);', 1, "usbmon: and remounts the way stock does on rc restart"),
    (mon, 'f_exists("/jffs/scripts/post-mount")', 1, "usbmon: the bus recovery only on a box that expects a volume"),
    (mon, '"wans_dualwan"), "usb")', 1, "usbmon: never with a USB WAN"),
    (mon, "UNTESTED recovery", 2, "usbmon: both recovery lines say they are untested"),
]
for text, needle, want, what in checks:
    n = text.count(needle)
    if n != want:
        die("%s: %r found %d times, expected %d" % (what, needle, n, want))
    ok(what)

# the re-sent event carries every field hotplug_usb's block branch reads
for env in ("SUBSYSTEM", "ACTION", "DEVICENAME", "MAJOR", "MINOR", "SCSI_HOST"):
    if 'setenv("%s"' % env not in mon or 'unsetenv("%s")' % env not in mon:
        die("usbmon: the re-sent event does not set and clear %s" % env)
ok("usbmon: the re-sent event sets and clears SUBSYSTEM/ACTION/DEVICENAME/MAJOR/MINOR/SCSI_HOST")
hb = usb[usb.index("void hotplug_usb(void)"):]
for g in ('getenv("DEVICENAME")', 'getenv("SUBSYSTEM")', 'getenv("MAJOR")', 'getenv("SCSI_HOST")', 'getenv("MINOR")'):
    if g not in hb:
        die("rc/usb.c hotplug_usb no longer reads %s - the re-sent event would be ignored" % g)
ok("rc/usb.c: hotplug_usb still reads exactly those fields")

# the mark sits in mount_partition's success branch, after the chmod
i_mp = usb.index("int mount_partition(char *dev_name")
i_ch = usb.index("chmod(mountpoint, 0775);", i_mp)
i_mk = usb.index("reaper_usb_mounted_mark(pt_name);", i_mp)
if not (i_ch < i_mk < i_ch + 300):
    die("rc/usb.c: the mounted mark is not in the success branch beside the chmod")
ok("rc/usb.c: the mark is written only when the mount succeeded")

# the check runs after the soft-lockup arm check on the same tick
fn = watchdog.index("void watchdog(int sig)")
i_arm = watchdog.index("reaper_softlockup_arm_check();", fn)
i_mon = watchdog.index("reaper_usbmon_check();", fn)
if not (i_arm < i_mon < i_arm + 200):
    die("rc/watchdog.c: the usb check is not beside the arm check on the tick")
ok("rc/watchdog.c: the usb check runs on the tick beside the arm check")

# order inside the check: aborted flash first, then the flag gate, then the retry, then the recovery
body = mon[mon.index("void reaper_usbmon_check(void)"):]
seq = [body.index("usbmon_aborted_flash_check();"), body.index("if (f_exists(REAPER_USBREL_FLAG))"),
       body.index("reaper_usbmon_candidates("), body.index("usbmon_resend_add(p);"), body.index("usbmon_recover_bus();")]
if seq != sorted(seq):
    die("usbmon: the check's order is not restore -> gate -> retry -> recovery")
ok("usbmon: restore an aborted flash, gate on the flag, retry, and only then the once-per-boot recovery")

print("PASS: usb-late-mount")
