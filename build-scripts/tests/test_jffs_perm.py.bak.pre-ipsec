#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No file or folder under /jffs stays writable by every user - the boot sweep and the review notice.

WHY THIS EXISTS. Field report 2026-10-20 (RT-BE88U): rc has run with umask 022 since v3.3.8, but
that only shapes NEW files. A file created earlier keeps 0666 through every later rewrite, and a
full-backup restore untars old modes back; the reporter found 250+ such entries under /jffs -
/jffs/nvram/sshd_authkeys (which ssh.c turns into dropbear's authorized keys), the VPN and HTTPS
private keys, the ACME account, the rule lists. dnsmasq, avahi and lldpd run as nobody, so one
compromised daemon could plant an SSH key and become root. The fix: shared/reaper_jfile.c
reaper_jffs_perm_sweep(), called by rc/ubifs.c and rc/jffs2.c right after /jffs is mounted (before
any service or user script), removes the "other" write bit from every regular file and directory
on that file system - symlinks never followed or changed, FIFOs/sockets left alone, other mounts
not entered, sticky directories kept; one log line. The Security Review (rwatch _rv_ww) reports a
file or folder that has the bit again, as its own fields in review.json (ww, ww_p) the Firewall
card and the dashboard word; diag v1.3.45 counts it in section 3.

WHAT IT DOES. Compiles the sweep out of reaper_jfile.c with a logging stub and runs it over a
fixture tree; lifts _rv_ww and _rv_json out of rwatch.c's C literals and runs them under sh on the
same tree (the report line, the once-per-count log line, the JSON); pins the call sites, the
pages, the three tokens in all 25 packs, the diag line and the markers.
Exit 0 pass, 1 fail, 77 skipped (no router source tree; the compiled half also needs gcc and sh).
"""
import codecs, json, os, re, shutil, stat, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "reaper_jfile.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
def read(p): return open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

jf, rw = read("shared/reaper_jfile.c"), read("rc/rwatch.c")
def c_text_static(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "".join(codecs.decode(m.group(1), "unicode_escape") for m in re.finditer(r'"((?:\\.|[^"\\])*)"', text))

# ---------------------------------------------------------------- wiring
check("shared.h declares the sweep and its report", "extern int reaper_jffs_perm_sweep(const char *root);" in read("shared/shared.h")
      and "extern void reaper_jffs_perm_report(void);" in read("shared/shared.h"))
ini = read("rc/init.c")
k = ini.find("case SIGUSR2:\t\t/* START */\n\t\t\tstart_logger();\n")
check("init reports the sweep right after start_logger() on the START path (syslogd did not exist at the mount; r1 metal)",
      k >= 0 and ini.find("reaper_jffs_perm_report();", k) - k < 260, k)
check("neither the review nor the diag uses find on /jffs (this busybox find has no -type/-perm/-xdev; r1 metal read 0 with a 0666 file planted)",
      "find /jffs" not in c_text_static(rw[rw.index(r'"_rv_ww() {\n"'):rw.index(r'"_rv_run() {\n"')]) and "find /jffs" not in read("others/reaper_diag").split("v1.3.45 (2026-10-20, field)")[1].split("3b. NVRAM")[0])
check("diag reads the boot record", 'JSW="$(cat /tmp/reaper/jffs.sweep 2>/dev/null)"' in read("others/reaper_diag")
      and "/jffs boot sweep  :" in read("others/reaper_diag"))
for f, arg in (("rc/ubifs.c", "UBIFS_MNT_DIR"), ("rc/jffs2.c", '"/jffs"')):
    s = read(f)
    i, j = s.find("\tsetup_jffs_dirs();\n"), s.find("reaper_jffs_perm_sweep(%s);" % arg)
    check("%s sweeps right after setup_jffs_dirs() (after the mount, before any service or user script)" % f,
          i >= 0 and j > i and s[i:j].count("\n") <= 4, (i, j))
check("reaper_jfile.c: the walker never follows a link, stays on one device, keeps sticky dirs, touches files and dirs only",
      "lstat(path, &st) != 0 || st.st_dev != dev" in jf and "(S_ISREG(st.st_mode) || S_ISDIR(st.st_mode)) && (st.st_mode & S_IWOTH)" in jf
      and "!(S_ISDIR(st.st_mode) && (st.st_mode & S_ISVTX))" in jf and "(st.st_mode & 07777) & ~S_IWOTH" in jf and "depth >= 32" in jf)
check("rwatch: _rv_ww runs every review tick after the login watch, and the off switch clears its files",
      '"  _rv_auth\\n"\n\t  "  _rv_ww\\n"' in rw and "$RV_TMP/review.ww $RV_TMP/ww.said 2>/dev/null; return 0; fi" in rw)
fw, dash = read("www/Reaper_Firewall.asp"), read("www/Main_ReaperDash.asp")
check("Firewall card: its own box (not under Failed logins), reset on every render, textContent",
      '<div id="rv_wwrap" class="hidden"><p class="note" id="rv_ww"></p></div>' in fw
      and "$('rv_wwrap').classList.add('hidden');" in fw
      and "$('rv_ww').textContent=`<#RFW_384#>`.replace('%1',j.ww).replace('%2',j.ww_p||'');" in fw)
check("dashboard: the bar and the posture row word it with their own tokens, not as login notices",
      "if(ww>0)t.push(`<#RDSH_117#>`.replace('%1',ww));" in dash and "if(u>0||nn>0||ww>0){" in dash
      and "if(ww>0)p.push(`<#RDSH_118#>`.replace('%1',ww));" in dash)
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if f.endswith(".dict") and f != "temp.dict")
miss = [(p, k) for p in packs for k in ("RDSH_117", "RDSH_118", "RFW_384")
        if not re.search(r"^%s=.*%%1" % k, open(os.path.join(www, p), encoding="utf-8").read(), re.M)]
check("RDSH_117, RDSH_118 and RFW_384 in all %d packs, each carrying %%1" % len(packs), len(packs) == 25 and not miss, miss[:6])
miss2 = [p for p in packs if not re.search(r"^RFW_384=.*%2", open(os.path.join(www, p), encoding="utf-8").read(), re.M)]
check("RFW_384 carries %2 (the example path) in every pack", not miss2, miss2)
dg = read("others/reaper_diag")
check("reaper_diag v1.3.45 counts files and folders under /jffs in section 3, with a WARN finding",
      'VER="REAPER-DIAG v1.3.45"' in dg and 'echo "  /jffs world-write : files=${JWF:-0} folders=${JWD:-0}' in dg
      and "file(s) or folder(s) under /jffs are writable by any user, set since the last boot" in dg)
mk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_markers.txt"), encoding="utf-8").read()
check("markers pin the sweep in libshared and rc, the review line, both pages and the diag line",
      all(w in mk for w in ("usr/lib/libshared.so|jffs: write access for all users removed from|1", "sbin/rc|reaper_jffs_perm_sweep|1",
                            "sbin/rc|writable by any user (first:|1", "www/Reaper_Firewall.asp|rv_wwrap|2",
                            "www/Main_ReaperDash.asp|ww=j.ww|1", "usr/sbin/reaper_diag|/jffs world-write :|1")))

# ---------------------------------------------------------------- the fixture
def mk_tree(base):
    os.umask(0)
    root = os.path.join(base, "jffs"); os.mkdir(root, 0o755)
    def f(rel, mode, data="x"):
        p = os.path.join(root, rel); open(p, "w").write(data); os.chmod(p, mode); return p
    f("a.txt", 0o666); f("exec.sh", 0o777); f("ok.txt", 0o644); f("priv", 0o600)
    os.mkdir(os.path.join(root, "nvram")); os.chmod(os.path.join(root, "nvram"), 0o777)
    f("nvram/sshd_authkeys", 0o666)
    os.mkdir(os.path.join(root, "shared")); os.chmod(os.path.join(root, "shared"), 0o1777)
    f("shared/f", 0o666)
    out = os.path.join(base, "outside.txt"); open(out, "w").write("o"); os.chmod(out, 0o666)
    outd = os.path.join(base, "outsidedir"); os.mkdir(outd); os.chmod(outd, 0o777)
    open(os.path.join(outd, "g"), "w").write("g"); os.chmod(os.path.join(outd, "g"), 0o666)
    os.symlink(out, os.path.join(root, "link")); os.symlink(outd, os.path.join(root, "linkdir"))
    if hasattr(os, "mkfifo"):
        os.mkfifo(os.path.join(root, "fifo")); os.chmod(os.path.join(root, "fifo"), 0o666)
    return root
def mode(p): return stat.S_IMODE(os.lstat(p).st_mode)
WRITABLE = ["a.txt", "exec.sh", "nvram", "nvram/sshd_authkeys", "shared/f"]

CC, SH = shutil.which("gcc") or shutil.which("cc"), shutil.which("sh")
if not (CC and SH and sys.platform.startswith("linux")):
    print("note: no C compiler, sh or Linux file modes on this host - the compiled half is skipped")
else:
    td = tempfile.mkdtemp(prefix="jffsperm-")
    try:
        # ---- the sweep, compiled from the source
        a = jf.index("static void rjf_ww_walk(")
        b = jf.index("\n}\n", jf.index("void reaper_jffs_perm_report(void)")) + 3
        rec = os.path.join(td, "jffs.sweep")
        csrc = os.path.join(td, "t.c")
        with open(csrc, "w") as fh:
            fh.write("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <stdarg.h>\n#include <unistd.h>\n"
                     "#include <sys/stat.h>\n#include <dirent.h>\n#include <limits.h>\n"
                     "static void logmessage(const char *t, const char *fmt, ...) { va_list a; va_start(a, fmt); printf(\"LOG %s: \", t); vprintf(fmt, a); printf(\"\\n\"); va_end(a); }\n"
                     "static int fake_syslogd;\nstatic int pids(char *n) { (void)n; return fake_syslogd; }\n"
                     "static int reaper_write_atomic(const char *p, const void *d, size_t l, mode_t m) { FILE *f = fopen(p, \"w\"); if (!f) return -1; fwrite(d, 1, l, f); fclose(f); return chmod(p, m); }\n"
                     + jf[a:b] +
                     "\n/* argv: root, whether syslogd runs when the sweep does; it always runs by the report */\n"
                     "int main(int c, char **v) { (void)c; fake_syslogd = atoi(v[2]); printf(\"RET %d\\n\", reaper_jffs_perm_sweep(v[1]));\n"
                     "  fake_syslogd = 1; printf(\"REPORT\\n\"); reaper_jffs_perm_report(); return 0; }\n")
        exe = os.path.join(td, "t")
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", '-DRJF_WW_REC="%s"' % rec, "-o", exe, csrc], capture_output=True, text=True)
        check("the sweep and its report compile on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
        os.mkdir(os.path.join(td, "sweep"))
        root = mk_tree(os.path.join(td, "sweep"))
        base = os.path.dirname(root)
        def logs_of(out, after=None):
            ls = out.split("REPORT\n")
            return [l for l in ls[0].splitlines() if l.startswith("LOG ")], [l for l in (ls[1] if len(ls) > 1 else "").splitlines() if l.startswith("LOG ")]
        if r.returncode == 0:
            # the boot case: syslogd is not running when /jffs is mounted (r1 metal: the line was lost)
            p = subprocess.run([exe, root, "0"], capture_output=True, text=True)
            pre, post = logs_of(p.stdout)
            check("before syslogd runs the sweep logs nothing; the report after start_logger() logs it once, naming the count and the root",
                  "RET 5" in p.stdout and not pre and len(post) == 1 and "removed from 5 file(s) and folder(s) under %s" % root in post[0], p.stdout)
            check("the report writes the boot record '<changed> <failed>'", open(rec).read() == "5 0\n", open(rec).read() if os.path.exists(rec) else "absent")
            check("world-writable files and folders lose only the other-write bit (0666->0664, 0777->0775, dir 0777->0775)",
                  mode(os.path.join(root, "a.txt")) == 0o664 and mode(os.path.join(root, "exec.sh")) == 0o775
                  and mode(os.path.join(root, "nvram")) == 0o775 and mode(os.path.join(root, "nvram/sshd_authkeys")) == 0o664,
                  {k: oct(mode(os.path.join(root, k))) for k in ("a.txt", "exec.sh", "nvram", "nvram/sshd_authkeys")})
            check("a sticky shared folder keeps 1777; a file inside it is still fixed",
                  mode(os.path.join(root, "shared")) == 0o1777 and mode(os.path.join(root, "shared/f")) == 0o664)
            check("modes without the bit are untouched (0644, 0600)",
                  mode(os.path.join(root, "ok.txt")) == 0o644 and mode(os.path.join(root, "priv")) == 0o600)
            check("symlinks are never followed: the targets outside keep 0666 / 0777 and the folder behind a link is not entered",
                  mode(os.path.join(base, "outside.txt")) == 0o666 and mode(os.path.join(base, "outsidedir")) == 0o777
                  and mode(os.path.join(base, "outsidedir", "g")) == 0o666)
            if os.path.exists(os.path.join(root, "fifo")):
                check("a FIFO is left alone", mode(os.path.join(root, "fifo")) == 0o666)
            p2 = subprocess.run([exe, root, "1"], capture_output=True, text=True)
            check("a second run changes nothing, logs nothing and records '0 0' (ran, nothing to do)",
                  "RET 0" in p2.stdout and "LOG" not in p2.stdout and open(rec).read() == "0 0\n", p2.stdout)
            os.remove(rec)
            p3 = subprocess.run([exe, os.path.join(root, "a.txt"), "1"], capture_output=True, text=True)
            check("a root that is not a directory is refused (-1) and leaves no record", "RET -1" in p3.stdout and not os.path.exists(rec), p3.stdout)
            # a sweep that runs with syslogd already up logs at once, and the report does not repeat it
            os.mkdir(os.path.join(td, "sweep2"))
            root3 = mk_tree(os.path.join(td, "sweep2"))
            p4 = subprocess.run([exe, root3, "1"], capture_output=True, text=True)
            pre, post = logs_of(p4.stdout)
            check("with syslogd already running the sweep logs at once and the report does not log it again",
                  "RET 5" in p4.stdout and len(pre) == 1 and not post and open(rec).read() == "5 0\n", p4.stdout)

        # ---- the review half, lifted from the C literals and run under sh on a fresh tree
        def c_text(text):
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            return "".join(codecs.decode(m.group(1), "unicode_escape") for m in re.finditer(r'"((?:\\.|[^"\\])*)"', text))
        w0 = rw.index('"_rv_ww() {\\n"'); w1 = rw.index('"}\\n"', rw.index('"  return 0\\n"', w0)) + 6
        j0 = rw.index('"_rv_json() {\\n"'); j1 = rw.index('"}\\n"', rw.index('"    }\'\\n"', j0)) + 6
        fn_ww, fn_json = c_text(rw[w0:w1]), c_text(rw[j0:j1])
        check("the lifted _rv_ww and _rv_json are whole functions", fn_ww.startswith("_rv_ww() {") and fn_ww.rstrip().endswith("}")
              and fn_json.startswith("_rv_json() {") and fn_json.rstrip().endswith("}"), (fn_ww[-60:], fn_json[-60:]))
        os.mkdir(os.path.join(td, "rev"))
        root2 = mk_tree(os.path.join(td, "rev"))
        tmpd = os.path.join(td, "rv"); os.mkdir(tmpd)
        script = os.path.join(td, "ww.sh")
        with open(script, "w", newline="\n") as fh:
            fh.write("RV_TMP=%s\nlogger() { shift 2; echo \"$*\" >> $RV_TMP/syslog; }\n" % tmpd
                     + fn_ww.replace("ls -lanR /jffs ", "ls -lanR %s " % root2) + "\n" + fn_json + "\n"
                     + "_rv_ww\n_rv_json 1 < /dev/null > $RV_TMP/review.json\n")
        def run():
            return subprocess.run([SH, script], capture_output=True, text=True)
        r1 = run()
        ww = open(os.path.join(tmpd, "review.ww")).read() if os.path.exists(os.path.join(tmpd, "review.ww")) else ""
        check("_rv_ww lists the 5 entries (files, then non-sticky folders), the first path with it", r1.returncode == 0
              and ww.startswith("ww 5 %s/" % root2), (r1.stderr, ww))
        try:
            jj = json.load(open(os.path.join(tmpd, "review.json")))
        except Exception as e:
            jj = {"err": str(e)}
        check("review.json parses and carries ww=5 and the first path as ww_p, beside notices_n",
              jj.get("ww") == 5 and jj.get("ww_p", "").startswith(root2 + "/") and "notices_n" in jj, jj)
        sl = open(os.path.join(tmpd, "syslog")).read().splitlines() if os.path.exists(os.path.join(tmpd, "syslog")) else []
        check("one syslog line names the count and the first path", len(sl) == 1 and "security review: 5 file(s) or folder(s) under /jffs are writable by any user (first: %s/" % root2 in sl[0], sl)
        run()
        sl = open(os.path.join(tmpd, "syslog")).read().splitlines()
        check("the same count on the next tick logs nothing more", len(sl) == 1, sl)
        os.chmod(os.path.join(root2, "a.txt"), 0o644)
        run()
        sl = open(os.path.join(tmpd, "syslog")).read().splitlines()
        check("a changed count logs once more", len(sl) == 2 and "security review: 4 file(s)" in sl[1], sl)
        for rel in WRITABLE:
            p = os.path.join(root2, rel)
            os.chmod(p, mode(p) & ~0o002)
        run()
        jj = json.load(open(os.path.join(tmpd, "review.json")))
        check("when nothing is left the report file goes and the JSON says ww=0",
              not os.path.exists(os.path.join(tmpd, "review.ww")) and jj.get("ww") == 0 and jj.get("ww_p") == "", jj)
        # a path with a quote and a backslash must not break the JSON
        q = os.path.join(root2, 'we"ird\\name'); open(q, "w").write("q"); os.chmod(q, 0o666)
        run()
        try:
            jj = json.load(open(os.path.join(tmpd, "review.json"))); ok = jj.get("ww") == 1 and jj.get("ww_p") == q
        except Exception as e:
            ok, jj = False, str(e)
        check("a path with a quote and a backslash is escaped in the JSON", ok, jj)
    finally:
        shutil.rmtree(td, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
