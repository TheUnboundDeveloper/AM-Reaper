#!/usr/bin/env python3
"""rwatch takes write-for-everyone off /jffs/nvram files each tick (2026-10-26).

WHY. The boot sweep clears the bit under /jffs once, but ASUS's prebuilt device discovery rewrites the JFFS-backed
setting asus_device_list with mode 0666 again (seen on metal an hour after boot), so the Security Review and the
dashboard flagged it for good. There is no source for that writer. rwatch's tick now removes the bit from
/jffs/nvram files that carry it, before the review looks.

WHAT IT DOES. Lifts step 3g2 out of rc/rwatch.c, points it at a scratch folder and runs it under sh (and busybox ash
when present): a 0666 file loses other-write, a 0664 file is not touched (its ctime stays - no flash write), a symlink
to a 0666 file is not followed, the log line comes once per boot, and the step sits before the review (3h).
"""
import ast, os, re, shutil, stat, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwatch.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rw = open(os.path.join(SRC, "rc", "rwatch.c"), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

i, j = rw.find('"# 3g2) /jffs/nvram'), rw.find('"# 3h) security review')
check("step 3g2 is present and runs before the security review (3h)", 0 < i < j, (i, j))
lines = re.findall(r'^\s*("(?:[^"\\]|\\.)*")\s*$', rw[i:j], re.M)
script = "".join(ast.literal_eval(l) for l in lines)
check("the step changes only files that carry the bit, never through a link",
      "$1 ~ /^-.......w/" in script and 'chmod o-w "/jffs/nvram/$_f"' in script and '[ ! -L "/jffs/nvram/$_f" ]' in script)

BB = shutil.which("busybox")
work = tempfile.mkdtemp(prefix="nvheal_")
try:
    for shell in ["sh"] + (["busybox"] if BB else []):
        tag = "sh" if shell == "sh" else "ash"
        nv, tmp = os.path.join(work, tag, "nvram"), os.path.join(work, tag, "tmp")
        os.makedirs(nv); os.makedirs(tmp)
        open(os.path.join(nv, "asus_device_list"), "w").write("x"); os.chmod(os.path.join(nv, "asus_device_list"), 0o666)
        open(os.path.join(nv, "custom_clientlist"), "w").write("y"); os.chmod(os.path.join(nv, "custom_clientlist"), 0o664)
        tgt = os.path.join(work, tag, "outside"); open(tgt, "w").write("z"); os.chmod(tgt, 0o666)
        os.symlink(tgt, os.path.join(nv, "planted"))
        logf = os.path.join(work, tag, "log")
        body = script.replace("/jffs/nvram", nv)
        sp = os.path.join(work, tag, "run.sh")
        open(sp, "w").write('logger() { shift 2; printf "%%s\\n" "$*" >> "%s"; }\nRV_TMP="%s"\n%s' % (logf, tmp, body))
        ct0 = os.stat(os.path.join(nv, "custom_clientlist")).st_ctime_ns
        time.sleep(0.05)
        cmd = ([shell, sp] if shell == "sh" else [BB, "ash", sp])
        r = subprocess.run(cmd, capture_output=True, text=True)
        mode = lambda p: stat.S_IMODE(os.stat(p).st_mode)
        check("[%s] the step runs" % tag, r.returncode == 0, r.stderr)
        check("[%s] the 0666 setting file is 0664 after the tick" % tag, mode(os.path.join(nv, "asus_device_list")) == 0o664, oct(mode(os.path.join(nv, "asus_device_list"))))
        check("[%s] a 0664 file is not touched (ctime unchanged - no flash write)" % tag,
              os.stat(os.path.join(nv, "custom_clientlist")).st_ctime_ns == ct0)
        check("[%s] a symlink planted in the folder is not followed" % tag, mode(tgt) == 0o666, oct(mode(tgt)))
        log = open(logf).read().splitlines() if os.path.exists(logf) else []
        check("[%s] one log line naming the file" % tag, len(log) == 1 and "asus_device_list" in log[0] and "planted" not in log[0], log)
        os.chmod(os.path.join(nv, "asus_device_list"), 0o666)
        subprocess.run(cmd, capture_output=True, text=True)
        log = open(logf).read().splitlines()
        check("[%s] the next rewrite is fixed again, with no second log line this boot" % tag,
              mode(os.path.join(nv, "asus_device_list")) == 0o664 and len(log) == 1, log)
finally:
    shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
