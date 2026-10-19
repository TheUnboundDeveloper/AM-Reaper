#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The pinned USB volume for long-term storage (shared/reaper_store.h, 2026-10-18).

WHY THIS EXISTS. Field report (RT-BE86U, one SSD, partitions "asus" + "asustor"):
both partitions grew .reaper/ and reaper/, and the traffic history split in two.
Every resolver - rtrafd, httpd's rdev_store_base(), the rwatch tick's shell
rstore_base() - took "the first mounted /tmp/mnt entry" and created its folder
there, and two partitions mount in a different order on each boot (one hotplug
process each, whichever takes the usb lock first). The fix pins an IDENTITY:
store_set writes <vol>/.reaper/store.id + nvram reaper_store_vid, and every
resolver uses only the mounted volume whose id matches, creating nothing.

WHAT IT DOES.
  1. Compiles shared/reaper_store.h on the host (-Wall -Wextra -Werror) with a
     driver that builds two-volume trees in BOTH creation orders and checks: only
     the pinned volume resolves; the other never gains a folder; a symlinked
     .reaper or store.id is refused; a malformed id is refused; the legacy
     reaper/rtraf.db moves into .reaper/ on the pinned volume only and never over
     an existing db; history start/newest; label validation.
  2. Extracts the generated shell rstore_base() from rc/rwatch.c and runs it with
     sh on the same kind of tree: it must agree with the C resolver, fall back to
     RAM without a pin or with the pin unplugged, and create nothing on a volume.
  3. Asserts on the source that every surface is wired: rtrafd / httpd / rwatch
     use the pin and no longer create a folder on discovery; store_set pins via
     rstore_write_id only; rtrafd's exit save goes back to where it attached; the
     watchdog tick runs the adopt/last-seen check; defaults; the page sends vol=
     with the waiting-pin sentinel; the 23 new dict keys exist in all 25 packs in
     the same order.

Exit 0 pass, 1 fail, 77 skipped (no gcc/sh, not Linux, or no router source tree -
pass release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
if not sys.platform.startswith("linux"):
    skip("not Linux")
GCC = shutil.which("gcc") or shutil.which("cc")
SH = shutil.which("sh")
if not GCC or not SH:
    skip("no host gcc or sh")

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

hdr = read("shared/reaper_store.h")
rtrafd = read("rtrafd/rtrafd.c")
web = read("httpd/web.c")
rwatch = read("rc/rwatch.c")
usbmon = read("rc/reaper_usbmon.c")
watchdog = read("rc/watchdog.c")
rc_h = read("rc/rc.h")
defaults = read("shared/defaults.c")
page = read("www/Reaper_Storage.asp")

# ------------------------------------------------------------------ 1. C helper
DRIVER = r'''
#include "reaper_store.h"
#include <assert.h>
static int fails = 0;
#define CHECK(c, m) do { if (!(c)) { printf("FAIL %s\n", m); fails++; } else printf("ok %s\n", m); } while (0)
static void mk(const char *p) { mkdir(p, 0755); }
static void put(const char *p, const char *t) { FILE *f = fopen(p, "w"); fputs(t, f); fclose(f); }
static int exists(const char *p) { struct stat st; return lstat(p, &st) == 0; }

int main(int argc, char **argv)
{
	char root[256], a[300], b[300], p[400], name[64], base[256], id[40];
	const char *VID = "0123456789abcdef", *OTHER = "fedcba9876543210";
	long newest = 0, h;
	int order;
	(void)argc;

	CHECK(rstore_name_ok("asus") && rstore_name_ok("My Disk") && rstore_name_ok("sda1"), "labels accepted");
	CHECK(!rstore_name_ok("") && !rstore_name_ok(".reaper") && !rstore_name_ok("a/b") && !rstore_name_ok("..")
	      && !rstore_name_ok("x\"y") && !rstore_name_ok("tab\tx"), "bad labels refused");
	CHECK(rstore_vid_ok(VID) && !rstore_vid_ok("0123") && !rstore_vid_ok("0123456789ABCDEF")
	      && !rstore_vid_ok("0123456789abcdeg") && !rstore_vid_ok(""), "id format");

	/* both creation orders: readdir order must not matter */
	for (order = 0; order < 2; order++) {
		snprintf(root, sizeof(root), "%s/mnt%d", argv[1], order);
		mk(root);
		snprintf(a, sizeof(a), "%s/asus", root);
		snprintf(b, sizeof(b), "%s/asustor", root);
		if (order == 0) { mk(a); mk(b); } else { mk(b); mk(a); }
		CHECK(rstore_find(root, 0, VID, name, sizeof(name), base, sizeof(base)) == 0, "no id anywhere = not found");
		CHECK(rstore_write_id(b, VID) == 0, "pin asustor (writes store.id)");
		CHECK(rstore_read_id(b, id, sizeof(id)) == 0 && !strcmp(id, VID), "store.id round trip");
		CHECK(rstore_find(root, 0, VID, name, sizeof(name), base, sizeof(base)) == 1 && !strcmp(name, "asustor"),
		      order ? "pinned volume found (reverse order)" : "pinned volume found (forward order)");
		snprintf(p, sizeof(p), "%s/.reaper", a);
		CHECK(!exists(p), "the other volume gained no folder");
		CHECK(rstore_find(root, 0, OTHER, name, sizeof(name), base, sizeof(base)) == 0, "a different pin is not found");
		/* the other volume carries an old pin of its own: still ignored */
		CHECK(rstore_write_id(a, OTHER) == 0 && rstore_find(root, 0, VID, name, sizeof(name), NULL, 0) == 1
		      && !strcmp(name, "asustor"), "an old id on another volume is ignored");
	}

	/* symlinks are refused (a share user could plant them) */
	snprintf(root, sizeof(root), "%s/sym", argv[1]); mk(root);
	snprintf(a, sizeof(a), "%s/real", root); mk(a);
	snprintf(b, sizeof(b), "%s/evil", root); mk(b);
	CHECK(rstore_write_id(a, VID) == 0, "pin real");
	snprintf(p, sizeof(p), "%s/.reaper", b);
	if (symlink("../real/.reaper", p) != 0) { perror("symlink"); return 2; }
	CHECK(rstore_find(root, 0, VID, name, sizeof(name), NULL, 0) == 1 && !strcmp(name, "real"),
	      "a symlinked .reaper never resolves");
	snprintf(root, sizeof(root), "%s/sym2", argv[1]); mk(root);
	snprintf(b, sizeof(b), "%s/evil", root); mk(b);
	snprintf(p, sizeof(p), "%s/.reaper", b); mk(p);
	snprintf(p, sizeof(p), "%s/.reaper/store.id", b);
	snprintf(a, sizeof(a), "%s/real/.reaper/store.id", argv[1]);
	{ char t[300]; snprintf(t, sizeof(t), "%s/sym/real/.reaper/store.id", argv[1]);
	  if (symlink(t, p) != 0) { perror("symlink"); return 2; } }
	CHECK(rstore_find(root, 0, VID, NULL, 0, NULL, 0) == 0, "a symlinked store.id is refused");

	/* malformed id file */
	snprintf(root, sizeof(root), "%s/bad", argv[1]); mk(root);
	snprintf(a, sizeof(a), "%s/v", root); mk(a);
	snprintf(p, sizeof(p), "%s/.reaper", a); mk(p);
	snprintf(p, sizeof(p), "%s/.reaper/store.id", a); put(p, "0123456789abcdef0\n");
	CHECK(rstore_find(root, 0, "0123456789abcdef", NULL, 0, NULL, 0) == 0, "an over-long id never matches");

	/* legacy rtrafd folder moves on the pinned volume only, never over a db */
	snprintf(root, sizeof(root), "%s/mig", argv[1]); mk(root);
	snprintf(a, sizeof(a), "%s/asus", root); mk(a);
	snprintf(p, sizeof(p), "%s/reaper", a); mk(p);
	snprintf(p, sizeof(p), "%s/reaper/rtraf.db", a); put(p, "OLD");
	CHECK(rstore_write_id(a, VID) == 0 && rstore_migrate_rtraf(a) == 1, "legacy db moved");
	snprintf(p, sizeof(p), "%s/.reaper/rtraf.db", a);
	CHECK(exists(p), "db now under .reaper/");
	snprintf(p, sizeof(p), "%s/reaper", a);
	CHECK(!exists(p), "empty legacy folder removed");
	snprintf(p, sizeof(p), "%s/reaper", a); mk(p);
	snprintf(p, sizeof(p), "%s/reaper/rtraf.db", a); put(p, "OLDER");
	CHECK(rstore_migrate_rtraf(a) == 0, "never moves over an existing db");
	snprintf(p, sizeof(p), "%s/reaper/rtraf.db", a);
	CHECK(exists(p), "the un-moved legacy db is left alone");

	/* history facts */
	snprintf(root, sizeof(root), "%s/hist", argv[1]); mk(root);
	snprintf(a, sizeof(a), "%s/h", root); mk(a);
	CHECK(rstore_hist(a, &newest) == 0 && newest == 0, "empty volume has no history");
	snprintf(p, sizeof(p), "%s/.reaper", a); mk(p);
	snprintf(p, sizeof(p), "%s/.reaper/dev.since", a); put(p, "1754600000\n");
	CHECK(rstore_hist(a, NULL) == 0, "a since stamp alone is not history");
	snprintf(p, sizeof(p), "%s/.reaper/devhist.log", a); put(p, "x\n");
	h = rstore_hist(a, &newest);
	CHECK(h == 1754600000 && newest > 0, "history starts at the oldest since stamp");
	snprintf(p, sizeof(p), "%s/.reaper/dev.since", a); unlink(p);
	h = rstore_hist(a, &newest);
	CHECK(h > 0 && h == newest, "no stamp: history starts at the data file");

	CHECK(rstore_new_id(id, sizeof(id)) == 0 && rstore_vid_ok(id), "fresh id is well formed");
	return fails ? 1 : 0;
}
'''

work = tempfile.mkdtemp(prefix="rstore_")
try:
    drv = os.path.join(work, "drv.c")
    open(drv, "w").write(DRIVER)
    exe = os.path.join(work, "drv")
    cc = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "shared"),
                         "-o", exe, drv], capture_output=True, text=True)
    if cc.returncode != 0:
        die("shared/reaper_store.h does not compile clean on the host:\n" + cc.stderr[-2000:])
    ok("shared/reaper_store.h compiles on the host (-Wall -Wextra -Werror)")
    tree = os.path.join(work, "t"); os.mkdir(tree)
    r = subprocess.run([exe, tree], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        print(("ok   " if ln.startswith("ok ") else "FAIL ") + ln.split(" ", 1)[1])
    if r.returncode != 0:
        die("C helper checks failed")

    # ---------------------------------------------------------- 2. shell twin
    m = re.search(r'\t  "rstore_base\(\) \{\\n"\n(.*?)\t  "\}\\n"\n', rwatch, re.S)
    if not m:
        die("rc/rwatch.c: rstore_base() not found in the generated script")
    body = []
    for ln in m.group(1).splitlines():
        s = re.match(r'\t  "(.*)\\n"$', ln)
        if not s:
            die("rc/rwatch.c: unexpected line in rstore_base(): " + ln)
        body.append(s.group(1).replace('\\"', '"').replace("\\\\", "\\"))
    fn = "rstore_base() {\n" + "\n".join(body) + "\n}\n"
    mnt = os.path.join(work, "mnt"); os.mkdir(mnt)
    tmpr = os.path.join(work, "tmpreaper")
    fn = fn.replace("/tmp/mnt", mnt).replace("/proc/mounts", os.path.join(work, "mounts")).replace("/tmp/reaper", tmpr)
    for v in ("asus", "asustor", "bare"):
        os.mkdir(os.path.join(mnt, v))
    # asus + asustor are "mounted"; bare is a leftover mountpoint directory
    open(os.path.join(work, "mounts"), "w").write(
        "/dev/sda1 %s/asus ext4 rw 0 0\n/dev/sda2 %s/asustor ext4 rw 0 0\n" % (mnt, mnt))
    def run_sh(vid, mode="usb"):
        script = ('_nv() { case "$1" in reaper_store) echo %s;; reaper_store_vid) echo "%s";; esac; }\n%s'
                  'rstore_base\n') % (mode, vid, fn)
        rr = subprocess.run([SH, "-c", script], capture_output=True, text=True)
        if rr.returncode != 0:
            die("shell rstore_base() failed: " + rr.stderr)
        return rr.stdout.strip()
    VID = "0123456789abcdef"
    if run_sh(VID) != tmpr:
        die("shell: no store.id anywhere must fall back to RAM, got %r" % run_sh(VID))
    if os.listdir(os.path.join(mnt, "asus")) or os.listdir(os.path.join(mnt, "asustor")):
        die("shell: rstore_base() created something on a volume")
    ok("shell: no pin match = RAM, and nothing is created on any volume")
    for v, i in (("asus", "fedcba9876543210"), ("asustor", VID), ("bare", VID)):
        os.makedirs(os.path.join(mnt, v, ".reaper"))
        open(os.path.join(mnt, v, ".reaper", "store.id"), "w").write(i + "\n")
    got = run_sh(VID)
    if got != os.path.join(mnt, "asustor", ".reaper"):
        die("shell: expected the pinned asustor, got %r" % got)
    ok("shell: the pinned volume resolves, an older pin on the other volume does not")
    if run_sh("") != tmpr:
        die("shell: an empty pin must fall back to RAM")
    ok("shell: no pin in nvram = RAM (never 'the first volume')")
    open(os.path.join(work, "mounts"), "w").write("/dev/sda1 %s/asus ext4 rw 0 0\n" % mnt)
    if run_sh(VID) != tmpr:
        die("shell: the pinned volume unplugged must fall back to RAM, not another volume")
    ok("shell: pinned volume unplugged = RAM; the leftover mountpoint is never used")
    shutil.rmtree(os.path.join(mnt, "asustor", ".reaper"))
    os.symlink(os.path.join(mnt, "bare", ".reaper"), os.path.join(mnt, "asustor", ".reaper"))
    open(os.path.join(work, "mounts"), "w").write(
        "/dev/sda1 %s/asus ext4 rw 0 0\n/dev/sda2 %s/asustor ext4 rw 0 0\n" % (mnt, mnt))
    if run_sh(VID) != tmpr:
        die("shell: a symlinked .reaper must never resolve")
    ok("shell: a symlinked .reaper is refused")
finally:
    shutil.rmtree(work, ignore_errors=True)

# ------------------------------------------------------------------ 3. wiring
def must(text, needle, n, what):
    c = text.count(needle)
    if (n is None and c == 0) or (n is not None and c != n):
        die("%s (found %d x %r)" % (what, c, needle))
    ok(what)

def must_not(text, needle, what):
    if needle in text:
        die(what + " (%r still present)" % needle)
    ok(what)

rs = re.search(r'static const char \*resolve_store\(char \*buf, size_t len\)\n\{(.*?)\n\}\n', rtrafd, re.S)
if not rs:
    die("rtrafd: resolve_store() not found")
must(rs.group(1), "rstore_find(RSTORE_MNT, 1, vid", 1, "rtrafd: usb resolves the pinned volume only")
must_not(rs.group(1), "opendir(\"/tmp/mnt\")", "rtrafd: no first-mounted-volume scan left")
must(rs.group(1), "rstore_migrate_rtraf(", 1, "rtrafd: legacy reaper/rtraf.db migrates into .reaper/")
must(rtrafd, "strlcpy(att_path, dbpath, sizeof(att_path));", 3, "rtrafd: all three attach points record where they attached")
must(rtrafd, "if (!want_store)", 1, "rtrafd: a run never asked for a store writes none on exit")
must(rtrafd, "else if (db_attached && att_path[0] && strcmp(att_path, dbpath))", 1,
     "rtrafd: the exit save goes back to where this run attached")

sb = re.search(r'static const char \*rdev_store_base\(char \*buf, size_t len\)\n\{(.*?)\n\}\n', web, re.S)
if not sb:
    die("httpd: rdev_store_base() not found")
must(sb.group(1), "rstore_find(RSTORE_MNT, 1, vid, NULL, 0, buf, len)", 1, "httpd: rdev_store_base() uses the pin")
must_not(sb.group(1), "/.reaper\", e->d_name", "httpd: no first-mounted-volume scan left")
must(web, "rstore_write_id(vdir, nid)", 1, "httpd: store_set is the one place that pins (writes store.id)")
for ek in ("RDEVE_16", "RDEVE_17", "RDEVE_18"):
    must(web, '\\"ek\\":\\"%s\\"' % ek, 1, "httpd: store_set error key %s" % ek)
for f in ('\\"state\\":', '\\"vols\\":[', '\\"pin\\":', '\\"present\\":%d,\\"seen\\":%ld}'):
    must(web, f, None, "httpd: store_status emits %s" % f)

must(rwatch, 'V=\\"$(_nv reaper_store_vid)\\"', 1, "rwatch: rstore_base() reads the pin")
must_not(rwatch, 'mkdir -p \\"$b\\"', "rwatch: rstore_base() creates no folder on a volume")

must(usbmon, "void reaper_store_check(void)", 1, "rc: reaper_store_check() defined")
must(usbmon, "rstore_write_id(vdir, nid)", 1, "rc: adoption pins by writing store.id")
must(usbmon, "RSTORE_ADOPT_QUIET_SECS", None, "rc: adoption waits for mounts to settle")
must(watchdog, "reaper_store_check();", 1, "rc/watchdog.c: the check is on the tick, once")
must(rc_h, "extern void reaper_store_check(void);", 1, "rc/rc.h: prototype")
must(defaults, '{ "reaper_store_vid", ""', 1, "defaults: reaper_store_vid (empty)")
must(defaults, '{ "reaper_store_vname", ""', 1, "defaults: reaper_store_vname (empty)")

must(page, "var PINKEY = '/pin';", 1, "page: the waiting pin has its own chip value")
must(page, "&vol=", 1, "page: store_set carries vol=")
must(page, "selVol !== PINKEY ? '&vol='", 1, "page: keeping the waiting pin sends no vol=")
for k in ("RDEVE_16", "RDEVE_17", "RDEVE_18"):
    must(page, "%s:`<#%s#>`" % (k, k), 1, "page: maps error key %s" % k)

NEW = ["RDST_%d" % n for n in range(79, 99)] + ["RDEVE_16", "RDEVE_17", "RDEVE_18"]
used = set(re.findall(r"<#(RDST_(?:79|8\d|9\d)|RDEVE_1[678])#>", page))
if used != set(NEW):
    die("page: new keys used %s != added %s" % (sorted(used), sorted(NEW)))
ok("page: uses exactly the 23 new keys")
LANGS = "BR CN CZ DA DE EN ES FI FR HU IT JP KR MS NL NO PL RO RU SL SV TH TR TW UK".split()
orders, lines = set(), set()
for lg in LANGS:
    t = read("www/%s.dict" % lg)
    keys = [ln.split("=", 1)[0] for ln in t.splitlines() if "=" in ln]
    pos = [k for k in keys if k in NEW]
    if pos != NEW:
        die("www/%s.dict: new keys missing or out of order: %s" % (lg, pos))
    orders.add(tuple(keys)); lines.add(t.count("\n"))
if len(orders) != 1 or len(lines) != 1:
    die("dicts are not in lockstep (%d key orders, line counts %s)" % (len(orders), sorted(lines)))
ok("all 25 dicts carry the 23 keys, same order, lockstep %d lines" % lines.pop())
print("PASS")
