#!/usr/bin/env python3
"""Host test for the interference-mitigation pass of the puncturing applier
(release/src/router/rc/reaper_punct.c, mit_pass(); reaper v3.3.1) and a syntax
compile of the minimum-width watcher (rc/reaper_bwfloor.c).

The applier is compiled from a copy of the real source against a stub rc.h and
run against a fake `wl` on PATH that keeps each radio's interference mode in a
file. Its /tmp state paths are redirected into a temp dir. Checked:
  - Driver default everywhere: no state file and not one wl command;
  - "hwaci" adds 16 to the driver's own mode (75 -> 91), records the base, and
    a second run writes nothing;
  - a wireless restart (driver back at 75) is re-applied;
  - back to Driver default restores the recorded base, then goes fully idle;
  - a driver already running 16 is reported "driver" and never written, and
    returning to Driver default then writes nothing (not ours);
  - a refused mode is reported and not recorded; malformed / radio-off skip;
  - two mutants (no restore; Driver default touches the radio) must fail.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, shutil, subprocess, sys, tempfile


def skip(msg):
    print("SKIP: " + msg); sys.exit(77)


def die(msg):
    print("FAIL: " + msg); sys.exit(1)


src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
punct = os.path.join(src_root, "rc", "reaper_punct.c") if src_root else ""
floor = os.path.join(src_root, "rc", "reaper_bwfloor.c") if src_root else ""
if not punct or not os.path.isfile(punct) or not os.path.isfile(floor):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no C compiler")
if "mit_pass" not in open(punct, encoding="utf-8").read():
    die("reaper_punct.c has no mit_pass() - the mitigation pass is missing")

STUB_RC = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <errno.h>
#include <stdarg.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <net/if.h>
size_t strlcpy(char *d, const char *s, size_t n);
size_t strlcat(char *d, const char *s, size_t n);
char *nvram_safe_get(const char *k);
int nvram_get_int(const char *k);
int nvram_match(const char *k, const char *v);
int nvram_set(const char *k, const char *v);
int _eval_stub(char *const argv[]);
#define eval(cmd, ...) ({ char *const _a[] = { cmd, __VA_ARGS__, NULL }; _eval_stub(_a); })
void logmessage(const char *tag, const char *fmt, ...);
int f_exists(const char *p);
int notify_rc(const char *s);
#define pids(x) 0
#define killall_tk(x) ((void)0)
#define xstart(...) ((void)0)
#define foreach(word, wordlist, next) \
	for (next = &wordlist[strspn(wordlist, " ")], \
	     strncpy(word, next, sizeof(word)), \
	     word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', \
	     next = strchr(next, ' '); \
	     strlen(word); \
	     next = next ? &next[strspn(next, " ")] : "", \
	     strncpy(word, next, sizeof(word)), \
	     word[strcspn(word, " ")] = '\0', \
	     word[sizeof(word) - 1] = '\0', \
	     next = strchr(next, ' '))
'''
STUB_WLUTILS = r'''
int wl_iovar_getint(char *ifname, char *iovar, int *val);
'''
STUBS_C = r'''
#include "rc.h"
size_t strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
size_t strlcat(char *d, const char *s, size_t n) { size_t l = strlen(d); return l + strlcpy(d + l, s, n > l ? n - l : 0); }
static char nvbuf[64][160]; static int nvn = -1;
static void nvload(void) {
	FILE *f; nvn = 0;
	if ((f = fopen(getenv("NVFILE"), "r")) == NULL) return;
	while (nvn < 64 && fgets(nvbuf[nvn], sizeof(nvbuf[0]), f)) { nvbuf[nvn][strcspn(nvbuf[nvn], "\n")] = 0; nvn++; }
	fclose(f);
}
char *nvram_safe_get(const char *k) {
	int i; size_t l = strlen(k);
	if (nvn < 0) nvload();
	for (i = 0; i < nvn; i++) if (!strncmp(nvbuf[i], k, l) && nvbuf[i][l] == '=') return nvbuf[i] + l + 1;
	return "";
}
int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
int nvram_match(const char *k, const char *v) { return !strcmp(nvram_safe_get(k), v); }
int _eval_stub(char *const argv[]) {
	pid_t p = fork(); int st = 0;
	if (p == 0) { execvp(argv[0], argv); _exit(127); }
	waitpid(p, &st, 0); return WEXITSTATUS(st);
}
void logmessage(const char *tag, const char *fmt, ...) { va_list a; va_start(a, fmt); printf("LOG %s: ", tag); vprintf(fmt, a); printf("\n"); va_end(a); }
int f_exists(const char *p) { struct stat s; return stat(p, &s) == 0; }
int notify_rc(const char *s) { (void)s; return 0; }
int reaper_punct_main(int argc, char *argv[]);
int main(void) { return reaper_punct_main(0, NULL); }
'''
FAKE_WL = r'''#!/bin/sh
D="$FAKEWL"
echo "$*" >> "$D/calls"
IF=""
[ "$1" = "-i" ] && { IF="$2"; shift 2; }
case "$1" in
  isup) echo 1;;
  bss) echo up;;
  chanspec) echo "36/80 (0xe02a)";;
  eht) echo "Puncture pattern: 0x0";;
  interference)
    f="$D/$IF.mode"; [ -f "$f" ] || echo 75 > "$f"
    if [ -n "$2" ]; then
      grep -qx "$2" "$D/refuse" 2>/dev/null || echo "$2" > "$f"
      exit 0
    fi
    echo; echo "Mode = $(cat "$f"). Following ACI modes are enabled:";;
esac
exit 0
'''

tmp = tempfile.mkdtemp(prefix="wlmit_")
fails = []


def build(name, mutate=None):
    d = os.path.join(tmp, name); os.makedirs(d)
    src = open(punct, encoding="utf-8").read().replace('"/tmp/reaper_', '"' + d + '/reaper_')
    if mutate:
        new = mutate(src)
        if new == src:
            die("mutant %s did not change the source - its anchor is stale" % name)
        src = new
    for fn, body in (("rc.h", STUB_RC), ("wlutils.h", STUB_WLUTILS), ("stubs.c", STUBS_C), ("reaper_punct.c", src)):
        open(os.path.join(d, fn), "w", encoding="utf-8").write(body)
    exe = os.path.join(d, "applier")
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror=implicit-function-declaration",
                        "-Wno-unused-parameter", "-I" + d, "-o", exe,
                        os.path.join(d, "reaper_punct.c"), os.path.join(d, "stubs.c")],
                       capture_output=True, text=True)
    if r.returncode:
        die("compile %s failed:\n%s" % (name, r.stderr))
    own = [l for l in r.stderr.splitlines() if "reaper_punct.c:" in l and "warning" in l]
    if own:
        die("compile %s warnings in reaper_punct.c:\n%s" % (name, "\n".join(own)))
    return d, exe


def scenarios(d, exe):
    """Return a list of failure strings for one build."""
    bad = []
    wl = os.path.join(d, "wlbin"); os.makedirs(wl, exist_ok=True)
    open(os.path.join(wl, "wl"), "w").write(FAKE_WL); os.chmod(os.path.join(wl, "wl"), 0o755)
    fake = os.path.join(d, "fake"); os.makedirs(fake, exist_ok=True)
    env = dict(os.environ, PATH=wl + os.pathsep + os.environ["PATH"], FAKEWL=fake, NVFILE=os.path.join(d, "nv"))
    state = os.path.join(d, "reaper_wlmit.state")

    def nv(**kw):
        base = {"wl0_ifname": "wl0", "wl0_vifs": "wl0.1", "wl0_radio": "1", "wl0_nband": "2",
                "wl1_ifname": "wl1", "wl1_vifs": "wl1.1", "wl1_radio": "1", "wl1_nband": "1"}
        base.update(kw)
        open(env["NVFILE"], "w").write("".join("%s=%s\n" % kv for kv in base.items()))

    def run():
        open(os.path.join(fake, "calls"), "w").close()
        r = subprocess.run([exe], env=env, capture_output=True, text=True, timeout=30)
        calls = open(os.path.join(fake, "calls")).read().splitlines()
        st = open(state).read() if os.path.exists(state) else ""
        return r, calls, st

    def mode(i): return open(os.path.join(fake, i + ".mode")).read().strip() if os.path.exists(os.path.join(fake, i + ".mode")) else "75"
    def set_mode(i, m): open(os.path.join(fake, i + ".mode"), "w").write("%d\n" % m)
    def writes(calls): return [c for c in calls if c.split()[-2:-1] == ["interference"] and c.split()[-1].isdigit()]
    def line(st, u): return next((l for l in st.splitlines() if l.startswith("wl%d " % u)), "")
    def check(cond, what):
        if not cond: bad.append(what)

    # 1. Driver default everywhere: nothing at all
    nv(); r, calls, st = run()
    check(not calls, "S1 driver default issued wl commands: %r" % calls)
    check(not os.path.exists(state), "S1 driver default left a state file")
    # 2. hwaci on wl0: 75 -> 91, base recorded
    nv(wl0_rmit="hwaci"); r, calls, st = run()
    check(mode("wl0") == "91", "S2 mode is %s, want 91" % mode("wl0"))
    check("base=75" in line(st, 0) and "set=91" in line(st, 0) and "result=applied" in line(st, 0), "S2 state %r" % line(st, 0))
    check(not line(st, 1), "S2 wl1 (driver default) got a line: %r" % line(st, 1))
    check(not any("wl1" in c for c in calls), "S2 touched wl1: %r" % calls)
    # 3. second run: no write
    r, calls, st = run()
    check(not writes(calls), "S3 re-wrote an applied mode: %r" % writes(calls))
    check("result=applied" in line(st, 0), "S3 state %r" % line(st, 0))
    # 4. wireless restart put the driver back at 75: re-applied
    set_mode("wl0", 75); r, calls, st = run()
    check(mode("wl0") == "91" and "base=75" in line(st, 0), "S4 not re-applied: mode %s state %r" % (mode("wl0"), line(st, 0)))
    # 5. back to driver default: restores 75, then idle
    nv(); r, calls, st = run()
    check(mode("wl0") == "75", "S5 not restored: mode %s" % mode("wl0"))
    check("result=off" in line(st, 0), "S5 state %r" % line(st, 0))
    r, calls, st = run()
    check(not calls and not os.path.exists(state), "S5b not idle after restore: calls %r state %r" % (calls, st))
    # 6. driver already runs 16: "driver", never written, and not undone later
    set_mode("wl0", 91); nv(wl0_rmit="hwaci"); r, calls, st = run()
    check("result=driver" in line(st, 0) and not writes(calls), "S6 state %r writes %r" % (line(st, 0), writes(calls)))
    nv(); r, calls, st = run()
    check(mode("wl0") == "91" and not writes(calls), "S6b undid a mode it never set: mode %s writes %r" % (mode("wl0"), writes(calls)))
    set_mode("wl0", 75)
    # 7. refused
    open(os.path.join(fake, "refuse"), "w").write("91\n")
    nv(wl0_rmit="hwaci"); r, calls, st = run()
    check("result=refused" in line(st, 0) and "set=-" in line(st, 0), "S7 state %r" % line(st, 0))
    os.remove(os.path.join(fake, "refuse"))
    nv(); run(); run()
    # 8. malformed value: skipped, no mode command at all
    nv(wl0_rmit="foo"); r, calls, st = run()
    check("result=skipped-malformed" in line(st, 0) and not any("interference" in c for c in calls), "S8 state %r calls %r" % (line(st, 0), calls))
    # 9. radio off
    nv(wl0_rmit="hwaci", wl0_radio="0"); r, calls, st = run()
    check("result=skipped-radio-off" in line(st, 0) and not writes(calls), "S9 state %r" % line(st, 0))
    return bad


d, exe = build("real")
fails = scenarios(d, exe)
if fails:
    die("real applier:\n  " + "\n  ".join(fails))
print("PASS: mitigation pass, 9 scenarios")

mutants = {
    "no-restore": lambda s: s.replace("set_mitmode(ifn, base[u]);", ";", 1),
    "touch-default": lambda s: s.replace("if (!want[0] && set[u] < 0)\n\t\t\tcontinue;", "", 1),
}
for name, mut in mutants.items():
    d, exe = build("mut-" + name, mut)
    if not scenarios(d, exe):
        die("mutant %s passed every scenario - the suite cannot see that defect" % name)
    print("PASS: mutant %s caught" % name)

# reaper_bwfloor.c: syntax against the same stubs (it is a daemon loop; behaviour is covered on metal)
d = os.path.join(tmp, "floor"); os.makedirs(d)
for fn, body in (("rc.h", STUB_RC), ("wlutils.h", STUB_WLUTILS)):
    open(os.path.join(d, fn), "w", encoding="utf-8").write(body)
shutil.copy(floor, os.path.join(d, "reaper_bwfloor.c"))
r = subprocess.run([CC, "-std=gnu99", "-fsyntax-only", "-Wall", "-Wextra", "-Wno-unused-parameter",
                    "-Werror=implicit-function-declaration", "-I" + d, os.path.join(d, "reaper_bwfloor.c")],
                   capture_output=True, text=True)
own = [l for l in r.stderr.splitlines() if "reaper_bwfloor.c:" in l and ("error" in l or "warning" in l)]
if r.returncode or own:
    die("reaper_bwfloor.c:\n" + (r.stderr if r.returncode else "\n".join(own)))
src = open(floor, encoding="utf-8").read()
if "pend[u] = 1;" not in src or "note=picker-pending" not in src:
    die("reaper_bwfloor.c lacks the deferred re-arm restart (pend[] / note=picker-pending)")
print("PASS: reaper_bwfloor.c compiles; deferred re-arm restart present")
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0)
