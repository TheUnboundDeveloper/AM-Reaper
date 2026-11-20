#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USB filesystem probe (review 2026-11-17, P6-5-C2; batch p9, 2026-11-18) - the fixes RUN on crafted disk images.

WHY. probe_fs() (shared/volume_id.c over BusyBox's util-linux/volume_id) parses a drive's own boot sector and
superblock. It runs in rc's hotplug at plug-in, and - for a partition whose first mount failed - inside rc's
long-lived watchdog (rc/reaper_usbmon.c usbmon_mountable). Three faults a crafted or damaged drive could reach:
  - fat.c: a boot sector with a FAT magic string jumps past the cluster-size check -> divide by 0 sectors per cluster;
  - hfs.c: an HFS+ blocksize of 0 -> divide by zero; a leaf node size below the node structures -> reads past the
    buffer (and a label length taken from the drive);
  - util.c volume_id_get_buffer(): "off + len" wraps for an offset near 2^64 and hands back a pointer far outside
    the superblock buffer.
WHAT IT DOES. Compiles BusyBox's own util.c / fat.c / hfs.c from the router tree on the host (its generated
autoconf.h; xmalloc / full_read / md5 stubbed), builds disk images in a temp dir and probes them:
  - FAT32 and FAT16 boot sectors with their magic and 0 sectors per cluster: refused, no crash (x86 traps a divide by
    zero, so the old code dies here with SIGFPE);
  - a normal FAT32 volume: still detected, label read;
  - HFS+ with blocksize 0: no crash, still reported as HFS+ (label-less);
  - HFS+ whose leaf node is 16 bytes, far into the disk: clean under AddressSanitizer (when the host has it);
  - volume_id_get_buffer() at offset 2^64-16: NULL, never a pointer outside its buffers.
And rc/reaper_usbmon.c usbmon_mountable(), extracted and compiled with stand-in probes, under a SIGCHLD reaper like
the watchdog's: a probe that answers gives its verdict; one that CRASHES or HANGS leaves the caller alive, logs one
line, and retires the partition (retry count at its maximum); the source value of the wait is 10 s.
Exit 0 pass, 1 fail, 77 skipped (no router source, no BusyBox autoconf.h, or no compiler).
"""
import os, re, shutil, struct, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
BB = os.path.join(SRC, "busybox") if SRC else ""
VID = os.path.join(BB, "util-linux", "volume_id")
if not SRC or not os.path.isfile(os.path.join(VID, "fat.c")) or not os.path.isfile(os.path.join(SRC, "rc", "reaper_usbmon.c")):
    print("SKIP: no router source tree"); sys.exit(77)
if not os.path.isfile(os.path.join(BB, "include", "autoconf.h")):
    print("SKIP: BusyBox is not configured in this tree (include/autoconf.h missing - build it once)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no host C compiler"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def read(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read()

def extract(src, signature):
    i = src.index(signature); j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    raise ValueError(signature)

STUBS = r'''
#include "libbb.h"
void* FAST_FUNC xmalloc(size_t s) { void *p = malloc(s); if (!p) abort(); return p; }
void* FAST_FUNC xrealloc(void *p, size_t s) { p = realloc(p, s); if (!p && s) abort(); return p; }
ssize_t FAST_FUNC full_read(int fd, void *buf, size_t len) { size_t t = 0; while (t < len) { ssize_t r = read(fd, (char *)buf + t, len - t); if (r <= 0) break; t += r; } return t; }
void FAST_FUNC md5_begin(md5_ctx_t *ctx) { (void)ctx; }
void FAST_FUNC md5_hash(md5_ctx_t *ctx, const void *buffer, size_t len) { (void)ctx; (void)buffer; (void)len; }
void FAST_FUNC md5_end(md5_ctx_t *ctx, void *resbuf) { (void)ctx; memset(resbuf, 0, 16); }
'''
MAIN = r'''
#include "volume_id_internal.h"
int main(int argc, char **argv)
{
	struct volume_id id;
	int fd = open(argv[2], O_RDONLY), r;
	memset(&id, 0, sizeof(id));
	id.fd = fd;
	if (!strcmp(argv[1], "fat")) r = volume_id_probe_vfat(&id);
	else if (!strcmp(argv[1], "hfs")) r = volume_id_probe_hfs_hfsplus(&id);
	else {
		const uint8_t *p = volume_id_get_buffer(&id, ~(uint64_t)0 - 0x10, 0x200);
		const char *w = !p ? "null" : (id.sbbuf && p >= id.sbbuf && p < id.sbbuf + SB_BUFFER_SIZE) ? "inside"
			: (id.seekbuf && p >= id.seekbuf && p < id.seekbuf + id.seekbuf_len) ? "inside" : "OUTSIDE";
		printf("wrap=%s\n", w); return 0;
	}
	printf("r=%d label=[%s]\n", r, id.label);
	return 0;
}
'''
td = tempfile.mkdtemp(prefix="p9usb-")
try:
    flags = ["-O0", "-w", "-D_GNU_SOURCE", "-include", os.path.join(BB, "include", "autoconf.h"),
             "-I", os.path.join(BB, "include"), "-I", VID]
    with open(os.path.join(td, "stubs.c"), "w") as fh: fh.write(STUBS)
    with open(os.path.join(td, "main.c"), "w") as fh: fh.write(MAIN)
    srcs = [os.path.join(VID, n) for n in ("util.c", "fat.c", "hfs.c")] + [os.path.join(td, "stubs.c"), os.path.join(td, "main.c")]
    exe = os.path.join(td, "probe")
    r = subprocess.run([CC] + flags + ["-o", exe] + srcs, capture_output=True, text=True)
    check("BusyBox's util.c / fat.c / hfs.c from the router tree compile on the host", r.returncode == 0, r.stderr[-1500:])
    asan = os.path.join(td, "probe_asan")
    ra = subprocess.run([CC] + flags + ["-g", "-fsanitize=address", "-fno-omit-frame-pointer", "-o", asan] + srcs, capture_output=True, text=True)
    has_asan = ra.returncode == 0
    if r.returncode != 0:
        print("\n%d check(s) failed" % len(fails))
        for f in fails: print("  - " + f)
        sys.exit(1)

    def img(name, size, writes):
        p = os.path.join(td, name)
        with open(p, "wb") as fh:
            fh.truncate(size)
            for off, data in writes:
                fh.seek(off); fh.write(data)
        return p
    # GCC 9's AddressSanitizer runtime on a recent kernel (WSL2 6.x) hangs at start-up in about 1 run in 4,
    # printing "AddressSanitizer:DEADLYSIGNAL" for ever, when address randomisation is on. Run the ASan probe
    # with randomisation off (setarch -R): 0 hangs in 60 runs, and it still reports a heap overflow.
    SETARCH = shutil.which("setarch")
    def probe(mode, path, exe_=exe):
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:abort_on_error=0:exitcode=99")
        cmd = [exe_, mode, path]
        if exe_ != exe and SETARCH:
            cmd = [SETARCH, os.uname().machine, "-R"] + cmd
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
        return p.returncode, p.stdout.strip(), p.stderr

    def fat_bs(spc, magic, magic_off, fat32=True, label=b"NO NAME    "):
        b = bytearray(512)
        b[0:3] = b"\xeb\x58\x90"; b[3:11] = b"MSWIN4.1"
        # FAT32 needs 65525+ clusters for the probe to take its FAT32 path: 2,000,000 sectors / 8 per cluster
        struct.pack_into("<HBHBHHBHHHII", b, 11, 512, spc, 32, 2, 0 if fat32 else 512, 0, 0xf8, 0 if fat32 else 200, 63, 255, 0,
                         2000000 if fat32 else 200000)
        if fat32:
            struct.pack_into("<IHHI", b, 36, 200, 0, 0, 2)
            b[71:82] = label
        else:
            b[43:54] = label
        b[magic_off:magic_off + len(magic)] = magic
        b[510:512] = b"\x55\xaa"
        return bytes(b)
    # ---- FAT: a magic string and 0 sectors per cluster (the old divide by zero)
    for nm, magic, off, f32 in (("FAT32 magic", b"FAT32   ", 82, True), ("MSWIN magic", b"MSWIN", 82, True), ("FAT16 magic", b"FAT16   ", 54, False)):
        rc, out, err = probe("fat", img("fat0.img", 1 << 20, [(0, fat_bs(0, magic, off, f32))]))
        check("FAT, %s, 0 sectors per cluster: refused (r=-1), the prober lives (it died with SIGFPE before)" % nm,
              rc == 0 and out.startswith("r=-1"), "exit %d %s %s" % (rc, out, err[-300:]))
    rc, out, err = probe("fat", img("fatok.img", 1 << 20, [(0, fat_bs(8, b"FAT32   ", 82, True, b"MYDISK     "))]))
    check("FAT32, a normal volume: still detected, its label read", rc == 0 and out == "r=0 label=[MYDISK]", "exit %d %s %s" % (rc, out, err[-300:]))

    # ---- HFS+: the volume header at 1024 (blocksize at +40, catalog extents at +288), the catalog header node at 0
    def hfs_img(name, blocksize, cat_start, ext1, leaf_head, node_size, size):
        vh = bytearray(512); vh[0:2] = b"H+"
        struct.pack_into(">I", vh, 40, blocksize)
        struct.pack_into(">II", vh, 288, cat_start, 1)
        if ext1: struct.pack_into(">II", vh, 296, ext1[0], ext1[1])
        hdr = bytearray(64)                        # node descriptor (14) + header record
        struct.pack_into(">HIIIIH", hdr, 14, 1, 1, 1, leaf_head, leaf_head, node_size)
        writes = [(0, bytes(hdr)), (1024, bytes(vh))]
        if ext1 and blocksize:
            # the leaf node where the probe will look: a LEAF descriptor with one record, so the key after it is read
            leaf_block = (leaf_head * node_size) // blocksize - 1
            leaf_off = (ext1[0] + leaf_block) * blocksize
            node = bytearray(64); node[8] = 0xff; struct.pack_into(">H", node, 10, 1)
            struct.pack_into(">HIH", node, 14, 6, 1, 4); node[22:30] = "Mac1".encode("utf-16-be")
            writes.append((leaf_off, bytes(node)))
        return img(name, size, writes)
    rc, out, err = probe("hfs", hfs_img("hfs0.img", 0, 0, None, 1, 4096, 1 << 20))
    check("HFS+, blocksize 0: no crash; still reported as HFS+ (r=0), label-less", rc == 0 and out == "r=0 label=[]", "exit %d %s %s" % (rc, out, err[-300:]))
    small = hfs_img("hfssmall.img", 512, 0, (0x200, 0x1000), 0x2000, 16, 1 << 20)
    rc, out, err = probe("hfs", small)
    check("HFS+, a 16-byte leaf node far into the disk: no crash, reported as HFS+", rc == 0 and out.startswith("r=0"), "exit %d %s %s" % (rc, out, err[-300:]))
    if has_asan:
        rc, out, err = probe("hfs", small, asan)
        check("HFS+, the same image under AddressSanitizer: no read past the leaf buffer", rc == 0 and "AddressSanitizer" not in err, err[-900:])
    else:
        print("note: no AddressSanitizer on this host - the HFS+ over-read case ran without it")

    # ---- volume_id_get_buffer at an offset near 2^64
    rc, out, err = probe("wrap", img("wrap.img", 1 << 16, []))
    check("volume_id_get_buffer at 2^64-16: NULL - never a pointer outside its buffers (it returned sbbuf + 4 GB before)",
          rc == 0 and out == "wrap=null", "exit %d %s %s" % (rc, out, err[-300:]))

    # ---- source pins
    fat = read(os.path.join(VID, "fat.c")); util = read(os.path.join(VID, "util.c")); hfs = read(os.path.join(VID, "hfs.c"))
    check("fat.c: the zero check sits right before the division, on the path both branches take",
          re.search(r"if \(vs->sectors_per_cluster == 0\)\s*return -1;\s*cluster_count = sect_count", fat) is not None
          and fat.index("REAPER-VOLID-FAT0") > fat.index("\n valid:"))
    check("util.c: both buffer tests are written so they cannot wrap",
          "if (off <= SB_BUFFER_SIZE && len <= SB_BUFFER_SIZE - off) {" in util and "(len <= id->seekbuf_len - (off - id->seekbuf_off))" in util
          and "if (off + len <= SB_BUFFER_SIZE" not in util)
    check("hfs.c: blocksize, leaf node size and label length are checked before use",
          "if (blocksize < 512 || (blocksize & (blocksize - 1)))" in hfs and "if (leaf_node_size < 512)" in hfs
          and hfs.index("if (blocksize < 512") < hfs.index("leaf_block = (leaf_node_head * leaf_node_size) / blocksize;")
          and "label_len = leaf_node_size - (unsigned)((const uint8_t *)key->unicode - buf);" in hfs)

    # ---- rc/reaper_usbmon.c: the probe in a child
    um = read(os.path.join(SRC, "rc", "reaper_usbmon.c"))
    fn = extract(um, "static int usbmon_mountable(const char *part)")
    mw = re.search(r"#define USBMON_PROBE_SECS\s+(\d+)", um)
    check("usbmon: the watchdog waits for the probe at most 10 s (source)", mw is not None and mw.group(1) == "10")
    check("usbmon: <sys/wait.h> is included (r9 built with waitpid implicitly declared - a compiler warning)",
          "#include <sys/wait.h>" in um)
    check("usbmon: probe_fs is called only inside the child (source)",
          fn.count("probe_fs(") == 1 and fn.index("pid = fork();") < fn.index("if (pid == 0) {") < fn.index("probe_fs(") < fn.index("_exit(1);"))
    rk = os.path.join(td, "retry_")
    H = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <sys/wait.h>
#include <errno.h>
#define REAPER_USB_RETRY_MARK "%(rk)s"
#define REAPER_USB_RETRY_MAX 3
#define USBMON_PROBE_SECS 1
static void logmessage(const char *t, const char *fmt, ...) { va_list ap; va_start(ap, fmt); printf("LOG %%s: ", t); vprintf(fmt, ap); printf("\n"); va_end(ap); }
static int f_write_string(const char *p, const char *s, unsigned f, unsigned m) { FILE *o = fopen(p, "w"); (void)f; (void)m; if (!o) return -1; fputs(s, o); fclose(o); return 0; }
static int probe_fs(char *device, char **type, char *label, char *uuid) {
	const char *m = getenv("PROBE"); volatile int z = 0; (void)device; (void)label; (void)uuid;
	if (!strcmp(m, "crash")) return 1 / z;
	if (!strcmp(m, "segv")) { volatile int *q = 0; return *q; }
	if (!strcmp(m, "hang")) { sleep(30); return -1; }
	if (!strcmp(m, "fail")) return -1;
	*type = (char *)m; return 1;
}
static int reaped = 0;
static void chld(int s) { (void)s; while (waitpid(-1, NULL, WNOHANG) > 0) reaped++; }	/* like the watchdog's chld_reap_local */
%(fn)s
int main(void) {
	struct sigaction sa; memset(&sa, 0, sizeof(sa)); sa.sa_handler = chld; sigaction(SIGCHLD, &sa, NULL);
	int r = usbmon_mountable("sdz1");
	printf("RESULT %%d\n", r); return 0; }
''' % {"rk": rk, "fn": fn}
    hc = os.path.join(td, "um.c"); he = os.path.join(td, "um")
    with open(hc, "w") as fh: fh.write("#include <stdarg.h>\n" + H)
    r = subprocess.run([CC, "-std=gnu99", "-w", "-o", he, hc], capture_output=True, text=True)
    check("usbmon_mountable compiles on the host with stand-in probes", r.returncode == 0, r.stderr[-900:])
    if r.returncode == 0:
        def um_run(mode):
            mk = rk + "sdz1"
            if os.path.exists(mk): os.unlink(mk)
            t0 = time.time()
            p = subprocess.run([he], capture_output=True, text=True, env=dict(os.environ, PROBE=mode), timeout=60)
            return p.returncode, p.stdout, (open(mk).read().strip() if os.path.exists(mk) else ""), time.time() - t0
        for mode, want in (("vfat", "RESULT 1"), ("ntfs", "RESULT 1"), ("swap", "RESULT 0"), ("unknown", "RESULT 0"), ("fail", "RESULT 0")):
            rc, out, mark, dt = um_run(mode)
            check("usbmon: a probe that answers '%s' gives its verdict (%s), no log line, the retry count untouched" % (mode, want[-1]),
                  rc == 0 and want in out and "LOG" not in out and mark == "", out + "|" + mark)
        for mode, sig in (("crash", "signal 8"), ("segv", "signal 11")):
            rc, out, mark, dt = um_run(mode)
            check("usbmon: a probe that CRASHES (%s) leaves the caller alive: not mountable, one log line naming the signal, retired" % sig,
                  rc == 0 and "RESULT 0" in out and out.count("LOG ") == 1 and sig in out and "not tried again" in out and mark == "3", out + "|" + mark)
        rc, out, mark, dt = um_run("hang")
        check("usbmon: a probe that HANGS is given up after the wait (1 s here), logged and retired; the caller goes on",
              rc == 0 and "RESULT 0" in out and "did not answer within 1 s" in out and mark == "3" and dt < 10, "%s|%s|%.1fs" % (out, mark, dt))
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
