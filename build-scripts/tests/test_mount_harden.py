#!/usr/bin/env python3
"""nosuid,nodev on /tmp, /var and /jffs (security review 2026-11: "/tmp, /var tmpfs no nosuid/nodev; /jffs ubifs none").

WHY. dnsmasq, rednsd, avahi-daemon and lldpd run as nobody. Without the two flags a file one of them drops in /tmp,
/var or /jffs could be setuid-root or a device node. rc/reaper_mountflags.c adds the flags with a per-mount-point
remount (MS_REMOUNT | MS_BIND), which on the 4.19 kernel never calls the filesystem's own remount but REPLACES the
user-settable mount flags - so a flag the mount already had (ro, noexec, the atime mode) is lost unless it is passed
again, and a forced noexec would stop every script in /jffs/scripts and /tmp.

WHAT IT CHECKS.
  1. Compiles the real rc/reaper_mountflags.c on the host twice with -Wall -Wextra -Werror (with and without
     _GNU_SOURCE, so the ST_* fallbacks are exercised) against stub rc.h/shared.h.
  2. Runs reaper_mount_harden() with stat(), statvfs() and mount() intercepted: not a mount of its own -> no mount
     call; no such folder -> none; both flags already set -> none; otherwise exactly one call with source, type and
     data NULL and flags = REMOUNT|BIND|NOSUID|NODEV plus every flag the mount had (ro, noexec, noatime, nodiratime,
     relatime) and nothing else - never a noexec the mount did not have; a failing mount() or statvfs() logs one
     line as "reaper" naming the path and the errno, and returns.
  3. Pins the wiring: the call after EVERY /jffs mount in rc/ubifs.c (right behind the skip_mnt: label, where the
     found-mounted, the mounted-here and the mounted-after-format paths meet), one call each for /tmp, /var and
     /jffs in rc/init.c after start_logger() and before start_services(), the Makefile object outside any ifeq,
     the prototype in rc.h, and the fallback values against the host's own headers.
The real remount needs root and a real mount: that part is a router check (grep ' /tmp \\| /var \\| /jffs ' /proc/mounts).
Takes release/src/router as argv[1] or REAPER_ROUTER_SRC. Exit 0 pass, 1 fail, 77 skipped (no tree, no compiler).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "init.c")):
    print("SKIP: no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no host compiler"); sys.exit(77)
F = os.path.join(SRC, "rc", "reaper_mountflags.c")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:700] if detail else ""))
def rd(p):
    with open(os.path.join(SRC, p), encoding="utf-8", errors="replace") as f:
        return f.read()
def done():
    if fails:
        print("\n%d FAILED:" % len(fails))
        for f in fails: print("  " + f)
        sys.exit(1)
    print("\nall mount-hardening checks passed"); sys.exit(0)

CALL = "reaper_mount_harden("

# ---------------------------------------------------------------- 3. the wiring (needs no compiler)
ubifs = rd("rc/ubifs.c")
jcall = "reaper_mount_harden(UBIFS_MNT_DIR);"
check("ubifs.c: one reaper_mount_harden(UBIFS_MNT_DIR) call", ubifs.count(jcall) == 1, ubifs.count(jcall))
a = ubifs.find("void start_ubifs(void)"); b = ubifs.find("void stop_ubifs(int stop)")
check("ubifs.c: start_ubifs() and stop_ubifs() found", 0 <= a < b)
body = ubifs[a:b] if 0 <= a < b else ""
mounts = [m.start() for m in re.finditer(r"\bmount\(s, UBIFS_MNT_DIR\b", body)]
lab = body.find("\nskip_mnt:\n"); cj = body.find(jcall); prep = body.find("userfs_prepare(UBIFS_MNT_DIR)")
check("ubifs.c: start_ubifs() is the only place that mounts /jffs", len(mounts) >= 1 and len(re.findall(r"\bmount\(s, UBIFS_MNT_DIR\b", ubifs)) == len(mounts), mounts)
check("ubifs.c: the call is in start_ubifs(), after every mount() and the skip_mnt: label, before userfs_prepare()",
      mounts and 0 <= max(mounts) < lab < cj < prep, (mounts, lab, cj, prep))
between = body[lab + len("\nskip_mnt:\n"):cj] if 0 <= lab < cj else "x"
check("ubifs.c: nothing but the #endif and a comment between skip_mnt: and the call (every path reaches it)",
      re.fullmatch(r"#endif\n(\s*/\*.*?\*/)?\s*", between, re.S) is not None, between)
check("ubifs.c: the found-mounted path still jumps to skip_mnt", "goto skip_mnt;" in body[:lab] if lab > 0 else False)

init = rd("rc/init.c")
paths = ["/tmp", "/var", "/jffs"]
for p in paths:
    check("init.c: exactly one reaper_mount_harden(\"%s\")" % p, init.count('reaper_mount_harden("%s");' % p) == 1,
          init.count('reaper_mount_harden("%s");' % p))
check("init.c: no other reaper_mount_harden() call", init.count(CALL) == 3, init.count(CALL))
s2 = init.find("case SIGUSR2:")
lg = init.find("start_logger();", s2) if s2 >= 0 else -1
rep = init.find("reaper_jffs_perm_report();", lg) if lg >= 0 else -1
sv = init.find("start_services();", lg) if lg >= 0 else -1
pos = [init.find('reaper_mount_harden("%s");' % p) for p in paths]
check("init.c: the three calls sit after start_logger() and before start_services() in the START state",
      0 <= s2 < lg < rep < pos[0] < pos[1] < pos[2] < sv, (s2, lg, rep, pos, sv))
if 0 <= rep < pos[0] < pos[2]:
    gap = init[rep + len("reaper_jffs_perm_report();"):pos[0]]
    check("init.c: only a comment between reaper_jffs_perm_report(); and the first call (not under an if/else)",
          re.fullmatch(r"\n(\s*/\*.*?\*/)?\s*", gap, re.S) is not None, gap)
    mid = init[pos[0]:pos[2]]
    check("init.c: the three calls are consecutive statements",
          re.fullmatch(r'reaper_mount_harden\("/tmp"\);\s*reaper_mount_harden\("/var"\);\s*', mid) is not None, mid)

mk = rd("rc/Makefile")
obj = [i for i, l in enumerate(mk.split("\n")) if re.match(r"OBJS\s*\+=\s*reaper_mountflags\.o\b", l)]
check("Makefile: one OBJS += reaper_mountflags.o", len(obj) == 1, obj)
if len(obj) == 1:
    depth = 0
    for l in mk.split("\n")[:obj[0]]:
        s = l.strip()
        if re.match(r"(ifeq|ifneq|ifdef|ifndef)\b", s): depth += 1
        elif re.match(r"endif\b", s): depth -= 1
    check("Makefile: the object is built for every model (outside any ifeq)", depth == 0, depth)
rch = rd("rc/rc.h")
check("rc.h: the prototype", rch.count("extern void reaper_mount_harden(const char *path);") == 1)

if not os.path.isfile(F):
    check("rc/reaper_mountflags.c exists", False, F)
    done()
src = rd("rc/reaper_mountflags.c")
check("source: plain ASCII, LF line ends", all(ord(c) < 128 for c in src) and "\r" not in src)
code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
check("source: no loop and no goto (one attempt, never a retry)", not re.search(r"\b(while|for|do|goto)\b", code))
check("source: void reaper_mount_harden(const char *path)", "void reaper_mount_harden(const char *path)\n{" in code)
check("source: MS_NOEXEC only where the mount already had it",
      len(re.findall(r"\bMS_NOEXEC\b", code)) == 1 and re.search(r"if \(vf\.f_flag & ST_NOEXEC\)\s*fl \|= MS_NOEXEC;", code) is not None)
check("source: one mount() call", len(re.findall(r"\bmount\(", code)) == 1)

# ---------------------------------------------------------------- 1 + 2. compile and run
STUB_RC = "#ifndef T_RC_H\n#define T_RC_H\n#endif\n"
STUB_SHARED = ("#ifndef T_SHARED_H\n#define T_SHARED_H\n#define logmessage logmessage_normal\n"
               "extern void logmessage_normal(char *logheader, char *fmt, ...);\n#endif\n")
HARNESS = r'''#define _GNU_SOURCE
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statvfs.h>

static const char *g_path = "";
static int g_exists, g_is_mount, g_statvfs_errno, g_mount_errno;
static unsigned long g_fflag;
static int n_mount, n_log, n_badstat;
static unsigned long m_flags;
static char m_src[32] = "-", m_type[32] = "-", m_data[32] = "-", m_tgt[256] = "-", l_hdr[64] = "-", l_line[512] = "-";

static int t_stat(const char *p, struct stat *st)
{
	char up[300];

	memset(st, 0, sizeof(*st));
	snprintf(up, sizeof(up), "%s/..", g_path);
	if (!g_exists) { errno = ENOENT; return -1; }
	if (!strcmp(p, g_path)) { st->st_dev = g_is_mount ? 42 : 7; return 0; }
	if (!strcmp(p, up)) { st->st_dev = 7; return 0; }
	n_badstat++; errno = ENOENT; return -1;
}
static int t_statvfs(const char *p, struct statvfs *v)
{
	memset(v, 0, sizeof(*v));
	if (strcmp(p, g_path)) n_badstat++;
	if (g_statvfs_errno) { errno = g_statvfs_errno; return -1; }
	v->f_flag = g_fflag;
	return 0;
}
static int t_mount(const char *s, const char *t, const char *ty, unsigned long fl, const void *d)
{
	n_mount++;
	m_flags = fl;
	snprintf(m_src, sizeof(m_src), "%s", s ? "SET" : "NULL");
	snprintf(m_type, sizeof(m_type), "%s", ty ? "SET" : "NULL");
	snprintf(m_data, sizeof(m_data), "%s", d ? "SET" : "NULL");
	snprintf(m_tgt, sizeof(m_tgt), "%s", t ? t : "NULL");
	if (g_mount_errno) { errno = g_mount_errno; return -1; }
	return 0;
}
void logmessage_normal(char *logheader, char *fmt, ...)
{
	va_list ap;

	n_log++;
	snprintf(l_hdr, sizeof(l_hdr), "%s", logheader);
	va_start(ap, fmt);
	vsnprintf(l_line, sizeof(l_line), fmt, ap);
	va_end(ap);
}
/* function-like, so "struct stat" and "struct statvfs" in the source stay what they are */
#define stat(p, st) t_stat(p, st)
#define statvfs(p, v) t_statvfs(p, v)
#define mount(a, b, c, d, e) t_mount(a, b, c, d, e)
#include "@SOURCE@"
#undef stat
#undef statvfs
#undef mount

int main(int argc, char **argv)
{
	if (argc == 2 && !strcmp(argv[1], "consts")) {
		printf("MS_REMOUNT=%lu MS_BIND=%lu MS_NOSUID=%lu MS_NODEV=%lu MS_RDONLY=%lu MS_NOEXEC=%lu MS_NOATIME=%lu "
		       "MS_NODIRATIME=%lu MS_RELATIME=%lu MS_STRICTATIME=%lu ST_RDONLY=%lu ST_NOSUID=%lu ST_NODEV=%lu "
		       "ST_NOEXEC=%lu ST_NOATIME=%lu ST_NODIRATIME=%lu ST_RELATIME=%lu\n",
		       (unsigned long)MS_REMOUNT, (unsigned long)MS_BIND, (unsigned long)MS_NOSUID, (unsigned long)MS_NODEV,
		       (unsigned long)MS_RDONLY, (unsigned long)MS_NOEXEC, (unsigned long)MS_NOATIME,
		       (unsigned long)MS_NODIRATIME, (unsigned long)MS_RELATIME, (unsigned long)MS_STRICTATIME,
		       (unsigned long)ST_RDONLY, (unsigned long)ST_NOSUID, (unsigned long)ST_NODEV, (unsigned long)ST_NOEXEC,
		       (unsigned long)ST_NOATIME, (unsigned long)ST_NODIRATIME, (unsigned long)ST_RELATIME);
		return 0;
	}
	if (argc == 2 && !strcmp(argv[1], "null")) {
		g_exists = 1; g_is_mount = 1;
		reaper_mount_harden(NULL);
		reaper_mount_harden("");
		printf("mount=%d log=%d\n", n_mount, n_log);
		return 0;
	}
	if (argc != 7) return 2;
	g_path = argv[1]; g_exists = atoi(argv[2]); g_is_mount = atoi(argv[3]); g_fflag = strtoul(argv[4], NULL, 0);
	g_statvfs_errno = atoi(argv[5]); g_mount_errno = atoi(argv[6]);
	reaper_mount_harden(g_path);
	printf("mount=%d log=%d badstat=%d flags=%lu src=%s type=%s data=%s tgt=%s hdr=%s line=%s\n",
	       n_mount, n_log, n_badstat, m_flags, m_src, m_type, m_data, m_tgt, l_hdr, l_line);
	return 0;
}
'''

tmp = tempfile.mkdtemp(prefix="mountharden_")
try:
    stubs = os.path.join(tmp, "stubs"); os.mkdir(stubs)
    with open(os.path.join(stubs, "rc.h"), "w") as f: f.write(STUB_RC)
    with open(os.path.join(stubs, "shared.h"), "w") as f: f.write(STUB_SHARED)
    for label, extra in (("without _GNU_SOURCE (the ST_* fallbacks)", []), ("with _GNU_SOURCE (as rc.h builds it)", ["-D_GNU_SOURCE"])):
        p = subprocess.run([CC, "-Wall", "-Wextra", "-Werror", "-Os", "-c", "-I", stubs] + extra +
                           ["-o", os.path.join(tmp, "o.o"), F], capture_output=True, text=True)
        check("compiles clean with -Wall -Wextra -Werror, " + label, p.returncode == 0, p.stderr)
    csrc = os.path.join(tmp, "h.c"); cbin = os.path.join(tmp, "h")
    with open(csrc, "w") as f: f.write(HARNESS.replace("@SOURCE@", F.replace("\\", "/")))
    p = subprocess.run([CC, "-O0", "-Wall", "-I", stubs, "-o", cbin, csrc], capture_output=True, text=True)
    check("the harness builds around the real source", p.returncode == 0, p.stderr)
    if p.returncode != 0:
        done()
    K = dict((k, int(v)) for k, v in (kv.split("=") for kv in subprocess.run([cbin, "consts"], capture_output=True, text=True).stdout.split()))
    for name in ("ST_NODEV", "ST_NOEXEC", "ST_NOATIME", "ST_NODIRATIME", "ST_RELATIME"):
        m = re.search(r"#ifndef %s\n#define %s\t(\d+)\n#endif" % (name, name), src)
        check("fallback %s equals the host header's value" % name, m is not None and int(m.group(1)) == K[name], (m and m.group(1), K[name]))
    m = re.search(r"#ifndef MS_STRICTATIME\n#define MS_STRICTATIME\t\(1 << (\d+)\)\n#endif", src)
    check("fallback MS_STRICTATIME equals the host header's value", m is not None and (1 << int(m.group(1))) == K["MS_STRICTATIME"])
    BASE = K["MS_REMOUNT"] | K["MS_BIND"] | K["MS_NOSUID"] | K["MS_NODEV"]

    def run(path, exists=1, is_mount=1, fflag=0, statvfs_errno=0, mount_errno=0):
        r = subprocess.run([cbin, path, str(exists), str(is_mount), str(fflag), str(statvfs_errno), str(mount_errno)],
                           capture_output=True, text=True)
        out = r.stdout.strip()
        d = {}
        head, _, line = out.partition(" line=")
        for kv in head.split():
            k, _, v = kv.partition("="); d[k] = v
        d["line"] = line; d["rc"] = r.returncode; d["raw"] = out
        return d
    def quiet(name, d):
        check(name + ": no mount call, no log line", d["rc"] == 0 and d.get("mount") == "0" and d.get("log") == "0" and d.get("badstat") == "0", d["raw"])
    def remount(name, d, want, path):
        check(name + ": one mount call, flags exactly as expected, source/type/data NULL, no log line",
              d["rc"] == 0 and d.get("mount") == "1" and d.get("log") == "0" and d.get("badstat") == "0"
              and int(d.get("flags", "0")) == want and d.get("src") == "NULL" and d.get("type") == "NULL"
              and d.get("data") == "NULL" and d.get("tgt") == path,
              "want flags %d: %s" % (want, d["raw"]))

    REL = K["ST_RELATIME"]
    quiet("not a mount of its own (same device as the parent)", run("/jffs", is_mount=0, fflag=REL))
    quiet("no such folder", run("/jffs", exists=0))
    quiet("both flags already set", run("/tmp", fflag=K["ST_NOSUID"] | K["ST_NODEV"] | REL))
    quiet("a path too long for the parent buffer", run("/" + "x" * 100, fflag=REL))
    r = subprocess.run([cbin, "null"], capture_output=True, text=True)
    check("NULL and empty path: no mount call, no log line, no crash", r.returncode == 0 and r.stdout.strip() == "mount=0 log=0", r.stdout + r.stderr)
    for p in paths:
        remount("%s rw,relatime (the state on a router today)" % p, run(p, fflag=REL), BASE | K["MS_RELATIME"], p)
    remount("/jffs rw,noatime (as rc/ubifs.c mounts it)", run("/jffs", fflag=K["ST_NOATIME"]), BASE | K["MS_NOATIME"], "/jffs")
    remount("ro,noexec,noatime,nodiratime are all carried",
            run("/var", fflag=K["ST_RDONLY"] | K["ST_NOEXEC"] | K["ST_NOATIME"] | K["ST_NODIRATIME"]),
            BASE | K["MS_RDONLY"] | K["MS_NOEXEC"] | K["MS_NOATIME"] | K["MS_NODIRATIME"], "/var")
    remount("ro,relatime is carried", run("/jffs", fflag=K["ST_RDONLY"] | REL), BASE | K["MS_RDONLY"] | K["MS_RELATIME"], "/jffs")
    remount("nosuid alone still gets nodev", run("/tmp", fflag=K["ST_NOSUID"] | REL), BASE | K["MS_RELATIME"], "/tmp")
    remount("nodev alone still gets nosuid", run("/tmp", fflag=K["ST_NODEV"] | REL), BASE | K["MS_RELATIME"], "/tmp")
    remount("no atime flag (strictatime): none passed, the kernel keeps the mode", run("/tmp", fflag=0), BASE, "/tmp")
    remount("nodiratime alone: strictatime is said, so the kernel adds no relatime",
            run("/tmp", fflag=K["ST_NODIRATIME"]), BASE | K["MS_NODIRATIME"] | K["MS_STRICTATIME"], "/tmp")
    remount("nodiratime,relatime", run("/tmp", fflag=K["ST_NODIRATIME"] | REL), BASE | K["MS_NODIRATIME"] | K["MS_RELATIME"], "/tmp")
    d = run("/jffs", fflag=REL, mount_errno=1)
    check("a failing mount(): one call, ONE log line as \"reaper\" with the path and the errno, then it returns",
          d["rc"] == 0 and d.get("mount") == "1" and d.get("log") == "1" and d.get("hdr") == "reaper"
          and d["line"].startswith("cannot set nosuid,nodev on /jffs: ") and d["line"].endswith("(errno 1)"), d["raw"])
    check("a failing mount(): the flags asked for were still the right ones", int(d.get("flags", "0")) == BASE | K["MS_RELATIME"], d["raw"])
    d = run("/var", fflag=REL, statvfs_errno=5)
    check("a failing statvfs(): no mount call, one log line with the path and the errno",
          d["rc"] == 0 and d.get("mount") == "0" and d.get("log") == "1" and d.get("hdr") == "reaper"
          and "/var" in d["line"] and d["line"].endswith("(errno 5)"), d["raw"])
    lit = subprocess.run(["grep", "-aFc", "--", "cannot set nosuid,nodev on %s", os.path.join(tmp, "o.o")], capture_output=True, text=True)
    check("the verify_markers.txt literal is in the object as one string", lit.stdout.strip() == "1", lit.stdout + lit.stderr)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
done()
