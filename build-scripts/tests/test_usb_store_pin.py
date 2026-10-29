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
used = set(re.findall(r"<#(RDST_(?:79|8\d|9[0-8])|RDEVE_1[678])#>", page))	# 99+ = the 2026-10-21 rows
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

# ------------------------------------------- 4. the published location (2026-10-21)
# Long-Term Storage rows for Wallguard / Dreadwatch / Encrypted DNS. wallguard.sh and the Dreadwatch
# collector read no nvram, so the watchdog publishes the base + opted-in datasets (rstore_pub_text)
# and both carry the shell reader rstore_dir (RSTORE_SH_DIR). The rwatch tick writes the Encrypted
# DNS activity line itself.
PUB_DRIVER = r'''
#include "reaper_store.h"
int main(int c, char **v) { char out[256]; int r; (void)c;
  r = rstore_pub_text(v[1], v[2], v[3], v[4], 0, v[5], out, sizeof(out));
  fputs(r ? out : "-\n", stdout); return 0; }
'''
MACRO_DRIVER = '#include <stdio.h>\n#include "reaper_store.h"\nint main(void){fputs(RSTORE_SH_DIR, stdout);return 0;}\n'
wallguard_sh = read("wallguard/wallguard.sh")
rwarden = read("rc/rwarden.c")
wallguard_c = read("rc/wallguard.c")
work = tempfile.mkdtemp(prefix="rstore4_")
try:
    def build(name, text):
        p = os.path.join(work, name); open(p + ".c", "w").write(text)
        r = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-I", os.path.join(SRC, "shared"),
                            "-o", p, p + ".c"], capture_output=True, text=True)
        if r.returncode:
            die("driver %s does not compile: %s" % (name, r.stderr[-800:]))
        return p
    pub = build("pub", PUB_DRIVER)
    mnt, jf = os.path.join(work, "mnt"), os.path.join(work, "jffs"); os.makedirs(jf)
    for v, i in (("A", "fedcba9876543210"), ("B", "0123456789abcdef")):
        os.makedirs(os.path.join(mnt, v, ".reaper")); open(os.path.join(mnt, v, ".reaper", "store.id"), "w").write(i)
    def P(*a): return subprocess.run([pub] + list(a), capture_output=True, text=True).stdout
    base = os.path.join(mnt, "B", ".reaper")
    if P("usb", "0123456789abcdef", "dev,shl", mnt, jf) != "%s\n,dev,shl,\n" % base:
        die("publish: the pinned volume B with its datasets expected, got %r" % P("usb", "0123456789abcdef", "dev,shl", mnt, jf))
    if P("usb", "1111111111111111", "dev", mnt, jf) != "-\n" or P("ram", "", "dev", mnt, jf) != "-\n":
        die("publish: a pin that matches nothing, or RAM, must publish nothing")
    if P("jffs", "", "shh,dw", mnt, jf) != "%s\n,shh,dw,\n" % jf:
        die("publish: the JFFS base expected")
    if P("usb", "0123456789abcdef", "dev;rm -rf /,$(x)", mnt, jf) != "%s\n,devrmrf,x,\n" % base:
        die("publish: the dataset list must keep only [a-z0-9,]")
    ok("publish: pinned volume only, nothing for RAM / no match, JFFS base, dataset list reduced to [a-z0-9,]")

    mac = subprocess.run([build("mac", MACRO_DRIVER)], capture_output=True, text=True).stdout
    a, b = wallguard_sh.find("# rstore_dir: begin"), wallguard_sh.find("# rstore_dir: end\n")
    if a < 0 or b < 0 or wallguard_sh[a:b + len("# rstore_dir: end\n")] != mac:
        die("wallguard/wallguard.sh: its rstore_dir block differs from RSTORE_SH_DIR in shared/reaper_store.h")
    ok("wallguard.sh carries RSTORE_SH_DIR byte for byte")
    pf, mts = os.path.join(work, "store.base"), os.path.join(work, "mounts")
    open(mts, "w").write("/dev/sda1 %s/B ext4 rw 0 0\n" % mnt)
    def RD(ds, text, link=False):
        for p in (pf, pf + ".real"):
            if os.path.lexists(p): os.remove(p)
        if link:
            open(pf + ".real", "w").write(text); os.symlink(pf + ".real", pf)
        else:
            open(pf, "w").write(text)
        env = dict(os.environ, RSTORE_PUB_F=pf, RSTORE_MNT_D=mnt, RSTORE_MOUNTS=mts, RSTORE_JFFS_D=jf)
        return subprocess.run([SH, "-c", mac + 'rstore_dir "$1"', "x", ds], capture_output=True, text=True, env=env).stdout.strip()
    t = "%s\n,dev,shl,\n" % base
    if RD("shl", t) != base or RD("shh", t) != "" or RD("shl", t, link=True) != "":
        die("rstore_dir: an opted-in dataset resolves; one not ticked, or a symlinked store.base, does not")
    if RD("dw", "%s\n,dw,\n" % jf) != jf or RD("dw", "/etc\n,dw,\n") != "":
        die("rstore_dir: the JFFS base resolves; any other path is refused")
    open(mts, "w").write("")
    if RD("shl", t) != "":
        die("rstore_dir: an unmounted USB base must not resolve")
    ok("rstore_dir: ticked dataset only, never a symlinked file, only the JFFS base or a mounted pinned volume")

    m = re.search(r'(\t  "# 2b\) Encrypted DNS activity.*?)\t  "# 3\) syslog mirror', rwatch, re.S)
    if not m:
        die("rc/rwatch.c: the Encrypted DNS activity block is missing")
    body = []
    for ln in m.group(1).splitlines():
        s = re.match(r'\t  "(.*)\\n"$', ln)
        if not s:
            die("rc/rwatch.c: unexpected line in the Encrypted DNS block: " + ln)
        body.append(re.sub(r'\\(.)', lambda x: x.group(1), s.group(1)))
    body = "\n".join(body) + "\n"
    stj = os.path.join(work, "status.json")
    open(stj, "w").write('{"state":"running","pid":1,"up":5,"listen":[{"a":"192.168.50.1","p":853,"wan":0,"ok":1}],'
                         '"conns":2,"conns_total":9,"queries":40,"refused_peer":1,"refused_policy":2,"refused_busy":0,'
                         '"hs_fail":0,"servfail":0,"cert":{"x":1}}\n')
    fb = os.path.join(work, "bin"); os.makedirs(fb)
    for name, out in (("iptables", "Chain REAPER_EDNS (1 references)\n    pkts bytes target prot opt in out source destination\n"
                                    "       5   300 REJECT tcp -- * * 0.0.0.0/0 0.0.0.0/0 tcp dpt:853 reject-with tcp-reset\n"
                                    "       2   120 REJECT udp -- * * 0.0.0.0/0 0.0.0.0/0 udp dpt:853 reject-with icmp-port-unreachable\n"
                                    "       7   420 REJECT tcp -- * * 0.0.0.0/0 0.0.0.0/0 tcp dpt:443 match-set redns_doh dst reject-with tcp-reset\n"),
                      ("ip6tables", "       1    80 REJECT tcp -- * * ::/0 ::/0 tcp dpt:443 match-set redns_doh6 dst reject-with tcp-reset\n"),
                      ("ipset", "Name: x\nNumber of entries: 10\n")):
        open(os.path.join(fb, name), "w").write("#!/bin/sh\ncat <<'EOF'\n%sEOF\n" % out); os.chmod(os.path.join(fb, name), 0o755)
    hb = os.path.join(work, "base"); os.makedirs(hb)
    rsx = os.path.join(work, "rstore")
    rb = subprocess.run([GCC, "-std=gnu99", "-I", os.path.join(SRC, "shared"), '-DRSTORE_TRUST_MNT="%s"' % mnt,
                         '-DRSTORE_TRUST_JFFS="%s"' % hb, "-DRSTORE_NEED_MOUNT=0", "-o", rsx, os.path.join(SRC, "wallguard", "rstore.c")],
                        capture_output=True, text=True)
    if rb.returncode:
        die("rstore does not build on the host: " + rb.stderr[-400:])
    def edns(dot):
        sc = ('_nv() { case "$1" in reaper_dot_srv) echo %s;; *) echo 0;; esac; }\nDS=",edns,"; VOLATILE=0; BASE=%s; NOWH=1792800000\n'
              % (dot, hb)) + body.replace("/tmp/rednsd/run/status.json", stj).replace("/usr/sbin/rstore", rsx)
        return subprocess.run([SH, "-c", sc], capture_output=True, text=True, env=dict(os.environ, PATH=fb + ":" + os.environ["PATH"]))
    r = edns(1)
    got = open(os.path.join(hb, "ednshist.log")).read() if os.path.exists(os.path.join(hb, "ednshist.log")) else ""
    if got != "1792800000 conn=2 ans=40 ref=3 dot_refused=7 doh_refused=8 doh_ips=20\n":
        die("rwatch: Encrypted DNS activity line wrong: %r %s" % (got, r.stderr[-300:]))
    edns(0)
    if open(os.path.join(hb, "ednshist.log")).read() != got:
        die("rwatch: with Encrypted DNS and the block both off, no line may be written")
    ok("rwatch: one Encrypted DNS activity line per tick (rednsd counters, 853 / 443 refusals v4+v6, list size), none while both are off")
finally:
    shutil.rmtree(work, ignore_errors=True)

must(usbmon, "rstore_publish();", 1, "rc: the watchdog check publishes the location")
must(usbmon, "wallguard_store_attached();", 1, "rc: a USB base that appears wakes Wallguard")
must(rc_h, "extern void wallguard_store_attached(void);", 1, "rc/rc.h: prototype")
must(wallguard_c, 'sh_run_bg("restore");', 1, "rc/wallguard.c: the attach hook runs restore")
must(rwarden, "\t  RSTORE_SH_DIR\n", 1, "rc/rwarden.c: the Dreadwatch collector carries the reader")
must(rwatch, "for _ds in dev traf watch chq slog shl shh dw edns; do", 1, "rwatch: collecting-since for the new rows")
must(rwatch, '/usr/sbin/rstore stamp \\"$BASE\\" \\"$_ds.since\\" \\"$NOWH\\"', 1, "rwatch: the since stamps never follow a link (rstore stamp)")
must(rwatch, '[ -f \\"$BASE/$_ds.since\\" ] || /usr/sbin/rstore stamp', 1, "rwatch: a stamp that exists is not re-offered every tick (review 2026-10-24 Q-A-7)")
must_not(rwatch, '> \\"$BASE/ednshist.log', "rwatch: the Encrypted DNS line is never written by path")
# owner "fix them" (2026-10-21): the OLDER store writers go through rstore too (guest shares map to uid 0
# on the volume, so a planted link redirected root's writes by path)
must_not(rwatch, '>> \\"$BASE/devhist.log', "rwatch: device history is never appended by path")
must(rwatch, 'rstore ring \\"$BASE\\" - devhist.log 5000', 1, "rwatch: device history = rstore ring, the last 5000 lines")
must(rwatch, 'rstore ring \\"$BASE\\" - chqhist.log 20000', 1, "rwatch: channel-quality history = rstore ring, the last 20000 lines")
must_not(rwatch, '>> \\"$BASE/syslog.mirror', "rwatch: the syslog mirror is never appended by path")
must(rwatch, 'rstore append \\"$BASE\\" - syslog.mirror 8388608', 2, "rwatch: the syslog mirror = rstore append with the 8 MB rotation (both branches)")
must(rwatch, 'rstore put \\"$BASE\\" \\"rwatch/inc-$NOWD\\"', 1, "rwatch: an incident dump onto the store is assembled in RAM and put file by file")
must(rwatch, 'rstore rmtree \\"$BASE\\" rwatch', 1, "rwatch: old dumps on the store are removed with rstore rmtree")
must(rwatch, "DUMPROOT=/jffs/rwatch; DUMPST=0", 1, "rwatch: /jffs/rwatch (root's alone) keeps the direct path")
must(web, 'rstore_append_buf(base, "-", "audit.log", 512 * 1024, line, (size_t)n);', 1, "httpd: the audit ring is appended without following a link")
must_not(web, 'snprintf(path, sizeof(path), "%s/audit.log", base);\n\tif ((f = fopen(path, "a")) == NULL) return;', "httpd: the audit log is no longer fopen(path, \"a\")")
must(web, 'rstore_stamp(base, "dev.since", line);', 1, "httpd: the devices collecting-since stamp is created once, never through a link")
must_not(web, 'snprintf(since, sizeof(since), "%s/dev.since", base);', "httpd: the since stamp is no longer fopen by path (the build break of 2026-10-21 22:01)")
must(rtrafd, 'rstore_append(g_store_dir, "-", "healthhist.log", HLOG_MAX, in);', 1, "rtrafd: the health history append is relative to the no-follow store folder")
must(rtrafd, "static int db_dir(const char *path)", 1, "rtrafd: the db folder is opened with no link followed at any level")
must(rtrafd, 'openat(dfd, DB_LEAF ".new", O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW | O_CLOEXEC, 0600);', 1, "rtrafd: the db temp is created in that folder, O_EXCL")
must(rtrafd, 'renameat(dfd, DB_LEAF ".new", dfd, DB_LEAF);', 1, "rtrafd: the db is published with renameat in that folder")
must(rtrafd, 'fd = openat(dfd, DB_LEAF, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);', 1, "rtrafd: the db is loaded relative to the folder; a FIFO is refused")
must_not(rtrafd, 'fd = open(path, O_RDONLY | O_NOFOLLOW);', "rtrafd: the old path-based db open is gone")
must(rwatch, "sh /usr/sbin/wallguard.sh restore", 1, "rwatch: Wallguard's no-table heal restores from the volume first")
must(web, '"slog", "shl", "shh", "dw", "edns", NULL', 2, "httpd: store_status since + store_set accept the new rows")
must(web, '\\"edoh_bytes\\"', 2, "httpd: the locked Encrypted DNS list row reports its facts")
for k in ("shl", "shh", "dw", "edns", "edoh"):
    must(page, "{k:'%s'," % k, 1, "page: row %s" % k)
NEW2 = ["RDST_%d" % n for n in range(99, 113)] + ["RSHD_131", "RSHD_132", "RDWT_52", "RDWT_53"]
orders, ref = set(), None
for lg in ["EN"] + LANGS:
    t = read("www/%s.dict" % lg)
    keys = [ln.split("=", 1)[0] for ln in t.splitlines() if "=" in ln]
    pos = [k for k in keys if k in NEW2]	# three groups, each after its family's last key
    ref = ref or pos
    if sorted(pos) != sorted(NEW2) or pos != ref:
        die("www/%s.dict: the 2026-10-21 keys missing or out of order" % lg)
    orders.add(tuple(keys))
if len(orders) != 1:
    die("dicts are not in lockstep after the 2026-10-21 keys")
ok("all 25 dicts carry the 18 Long-Term Storage keys in lockstep")
print("PASS")
