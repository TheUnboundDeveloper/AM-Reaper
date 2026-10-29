#!/usr/bin/env python3
"""Custom scripts keep their output and say when they fail (2026-10-26).

WHY. Field report: "/jffs/scripts/firewall-start is not loaded and honoured". rc runs it last in start_firewall(),
after Reaper's own chains, exactly as stock - but stock Merlin sends a custom script's output to /dev/null, so a
command that fails inside it (iptables -w, which this router's iptables 1.4 does not have; a BusyBox option it
lacks) leaves no trace and the script looks as if it never ran. shared/scripts.c now runs every custom script under
a watcher: the first 64 KB of its output is kept in /tmp/reaper/script-<name>.log (last run), and one syslog line
says when it exits non-zero, with the last thing it printed. A script with Windows line endings is named as such.

WHAT IT DOES. Lifts the runner (CS_LOG_CAP .. cs_run) out of shared/scripts.c, compiles it on the host with a
logmessage() stub that writes to a file, and runs real shell scripts through it:
  - a failing command: exit status + the last line in the log line, the output in the file;
  - timeout 0 returns at once while the script still runs (stock: not waited for);
  - timeout > 0 waits for the script and SIGALRM stops it at the timeout, with a "did not finish" line;
  - a script that leaves a chatty daemon behind: the caller returns when the SCRIPT exits, the file stays at the cap;
  - a silent script whose daemon holds the pipe: the caller still returns when the script exits;
  - success logs nothing; a script without #! still runs (execvp falls back to /bin/sh, as before);
  - CRLF line endings are detected.
"""
import os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "shared", "scripts.c") if SRC else ""
if not P or not os.path.isfile(P):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no C compiler"); sys.exit(77)
src = open(P, encoding="utf-8").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

i, j = src.find("#define CS_LOG_CAP"), src.find("\nvoid run_custom_script(")
check("the runner sits before run_custom_script()", 0 < i < j, (i, j))
body = src[i:j]
check("run_custom_script() uses the runner and the CRLF check, not _eval(cmd, NULL, ...)",
      "cs_run(cmd, name, timeout);" in src and "if (cs_crlf(script))" in src
      and "_eval( cmd, NULL, timeout, (timeout ? NULL : &pid));" not in src)

work = tempfile.mkdtemp(prefix="csrun_")
try:
    logd = os.path.join(work, "logs"); os.makedirs(logd)
    syslog = os.path.join(work, "syslog")
    c = os.path.join(work, "t.c")
    open(c, "w").write(r'''#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <errno.h>
#include <poll.h>
#include <time.h>
#include <sys/wait.h>
#include <sys/stat.h>
#define CS_LOG_DIR "%s"
static void logmessage(const char *tag, const char *fmt, ...)
{
	FILE *f = fopen("%s", "a"); va_list ap;
	if (!f) return;
	fprintf(f, "%%s: ", tag); va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap); fputc('\n', f); fclose(f);
}
static int _eval(char *const argv[], const char *path, int timeout, int *ppid) { (void)argv; (void)path; (void)timeout; (void)ppid; return -1; }
''' % (logd, syslog) + body + r'''
int main(int argc, char **argv)
{
	struct timespec a, b;
	char *cmd[3] = { argv[1], NULL, NULL };
	if (argc > 4 && !strcmp(argv[4], "crlf")) { printf("crlf=%%d\n", cs_crlf(argv[1])); return 0; }
	clock_gettime(CLOCK_MONOTONIC, &a);
	cs_run(cmd, argv[2], atoi(argv[3]));
	clock_gettime(CLOCK_MONOTONIC, &b);
	printf("returned_after=%%.2f\n", (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / 1e9);
	return 0;
}
'''.replace("%%", "%"))
    exe = os.path.join(work, "t")
    r = subprocess.run([CC, "-Wall", "-O1", "-o", exe, c], capture_output=True, text=True)
    check("the runner compiles on its own", r.returncode == 0, r.stderr[-1500:])
    if r.returncode != 0:
        raise SystemExit
    def script(name, text, crlf=False):
        p = os.path.join(work, name)
        data = text.replace("\n", "\r\n") if crlf else text
        open(p, "w", newline="").write(data); os.chmod(p, 0o755); return p
    def run(path, name, timeout, *extra):
        r = subprocess.run([exe, path, name, str(timeout)] + list(extra), capture_output=True, text=True, timeout=60)
        m = re.search(r"returned_after=([\d.]+)", r.stdout)
        return (float(m.group(1)) if m else None), r
    def syslines():
        return open(syslog).read() if os.path.exists(syslog) else ""
    def waitfor(pred, secs=8):
        end = time.time() + secs
        while time.time() < end:
            if pred(): return True
            time.sleep(0.1)
        return pred()

    # 1. a failing command, timeout 0 (firewall-start's way)
    s = script("fs.sh", "#!/bin/sh\necho adding rules\necho 'iptables v1.4.18: unknown option \"-w\"' >&2\nexit 2\n")
    t, _ = run(s, "firewall-start", 0)
    check("timeout 0 returns at once", t is not None and t < 1.0, t)
    ok = waitfor(lambda: "exited with status 2" in syslines())
    sl = syslines()
    check("a failing script logs its status and its last line", ok and 'iptables v1.4.18: unknown option "-w"' in sl
          and os.path.join(logd, "script-firewall-start.log") in sl, sl[-400:])
    lf = os.path.join(logd, "script-firewall-start.log")
    check("its output is kept in script-<name>.log, mode 0600", os.path.exists(lf) and "adding rules" in open(lf).read()
          and (os.stat(lf).st_mode & 0o777) == 0o600, os.path.exists(lf) and oct(os.stat(lf).st_mode))

    # 2. success logs nothing; no #! still runs
    open(syslog, "w").close()
    s = script("ok.sh", "#!/bin/sh\necho fine\n")
    run(s, "ok", 5)
    s2 = script("noshebang.sh", "echo ran-without-shebang\nexit 0\n")
    t, _ = run(s2, "noshebang", 5)
    time.sleep(0.5)
    check("a script that succeeds logs nothing", syslines() == "", syslines())
    check("a script without #! still runs under /bin/sh", "ran-without-shebang" in open(os.path.join(logd, "script-noshebang.log")).read())

    # 3. timeout > 0 waits for the script, and the timeout stops it
    s = script("slow.sh", "#!/bin/sh\nsleep 1\necho done\nexit 3\n")
    t, _ = run(s, "slow", 5)
    check("timeout > 0 waits for the script", t is not None and 0.9 < t < 3.0, t)
    s = script("hang.sh", "#!/bin/sh\necho start\nsleep 30\n")
    t, _ = run(s, "hang", 2)
    check("the timeout stops a script that runs too long", t is not None and 1.8 < t < 4.0, t)
    check("... and says so", waitfor(lambda: "did not finish in 2 s" in syslines()), syslines()[-300:])

    # 4. a daemon left behind: the caller returns with the script, the file stays at the cap
    s = script("daemon.sh", "#!/bin/sh\n( i=0; while [ $i -lt 400000 ]; do echo daemon-line-$i; i=$((i+1)); done; sleep 3 ) &\nexit 0\n")
    t, _ = run(s, "daemon", 10)
    check("a chatty daemon does not hold up a waiting caller", t is not None and t < 3.0, t)
    dl = os.path.join(logd, "script-daemon.log")
    waitfor(lambda: os.path.exists(dl) and os.path.getsize(dl) >= 65536, 10)
    time.sleep(1.0)
    check("its output file stops at 64 KB", os.path.exists(dl) and os.path.getsize(dl) == 65536, os.path.exists(dl) and os.path.getsize(dl))
    s = script("silentd.sh", "#!/bin/sh\n( sleep 6 ) &\nexit 0\n")
    t, _ = run(s, "silentd", 10)
    check("a silent daemon holding the pipe does not hold up a waiting caller", t is not None and t < 2.5, t)

    # 5. CRLF
    s = script("crlf.sh", "#!/bin/sh\necho hi\n", crlf=True)
    _, r = run(s, "crlf", 0, "crlf")
    check("Windows line endings are detected", "crlf=1" in r.stdout, r.stdout)
    s = script("lf.sh", "#!/bin/sh\necho hi\n")
    _, r = run(s, "lf", 0, "crlf")
    check("Unix line endings are not flagged", "crlf=0" in r.stdout, r.stdout)
finally:
    time.sleep(0.2)
    shutil.rmtree(work, ignore_errors=True)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
