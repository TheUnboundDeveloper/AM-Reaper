#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A refused filter-table restore must be loud and must not leave the boot skeleton.

WHY THIS EXISTS. Field data (2026-09-13, review R15): an RT-BE88U ran for two weeks on
start_default_filter()'s boot skeleton - no port forwards, no VPN server chains - because
one line of /tmp/filter_rules was refused by the kernel and iptables-restore is atomic.
The saved copies pass `iptables-restore --test`, and the firmware's own _eval() sends the
restore's stderr to /dev/null, so nothing on the box could say WHICH line. The fix
(rc/firewall.c reaper_restore_rules) keeps the restore's words, names the refused line in
syslog, and applies the table without it, up to eight times.

WHAT IT DOES. Extracts reaper_restore_rules() and its two helpers from the real
firewall.c (brace-matched, not copied), compiles them on the host with stubs for _eval
(runs a fake iptables-restore), logmessage (captured), rule_apply_checking and
check_if_dir_exist, and drives them with a fake `iptables-restore` that refuses any rule
containing the token REFUSE with the real binary's wording ("iptables-restore: line N
failed"). Asserts:
  - a clean file applies first time and leaves no .err file behind;
  - one refused rule: the table is applied without it, the rule text is in the log, the
    retry file lacks exactly that line, and the success line counts 1 skipped;
  - two refused rules: both skipped, in order, 2 counted;
  - a refusal on a chain-declaration line is NOT stripped: the table stays unapplied and
    the log says so;
  - a refusal that names no line (a crash) is logged with the restore's output and left;
  - the cap: nine refused rules stop after eight and report NOT applied.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, stat, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
fw = os.path.join(src_root, "rc", "firewall.c") if src_root else ""
if not fw or not os.path.isfile(fw):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
if not shutil.which("gcc") and not shutil.which("cc"):
    skip("no host C compiler")
CC = shutil.which("gcc") or shutil.which("cc")

def extract(src, signature):
    i = src.find(signature)
    if i < 0: die("signature not found in firewall.c: %r" % signature)
    j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        c = src[k]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    die("unbalanced braces after %r" % signature)

with open(fw, encoding="utf-8", errors="replace") as f:
    source = f.read()

parts = [
    "#define REAPER_RESTORE_MAX_SKIP 8\n#define REAPER_ERR_RULES ERR_DIR\n",
    extract(source, "static void reaper_restore_read_err("),
    extract(source, "static int reaper_restore_drop_line("),
    extract(source, "static int reaper_restore_rules("),
]

STUBS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <libgen.h>
#include <sys/stat.h>
#include <sys/types.h>
static const char *ERR_DIR;
static FILE *LOG;
void logmessage(const char *tag, const char *fmt, ...) { va_list ap; va_start(ap, fmt); fprintf(LOG, "%s: ", tag); vfprintf(LOG, fmt, ap); fputc('\n', LOG); va_end(ap); fflush(LOG); }
int check_if_dir_exist(const char *p) { struct stat st; return stat(p, &st) == 0 && S_ISDIR(st.st_mode); }
void rule_apply_checking(char *caller, int line, char *rule_path, int ret) { logmessage(caller, "apply rules error(%d)", line); }
/* the real _eval forks, redirects stdout+stderr to path (">file"), execvp's argv */
int _eval(char *const argv[], const char *path, int timeout, int *ppid) {
	char cmd[1024]; int n = 0, i;
	for (i = 0; argv[i]; i++) n += snprintf(cmd + n, sizeof(cmd) - n, "%s%s", i ? " " : "", argv[i]);
	if (path && *path == '>') n += snprintf(cmd + n, sizeof(cmd) - n, " >%s 2>&1", path + 1);
	int st = system(cmd);
	return st == -1 ? 127 : (WIFEXITED(st) ? WEXITSTATUS(st) : 128);
}
'''
MAIN = r'''
int main(int argc, char **argv) {
	ERR_DIR = argv[1]; LOG = fopen(argv[2], "a");
	int r = reaper_restore_rules("iptables-restore", argv[3], 4242);
	printf("rc=%d\n", r); return r ? 1 : 0;
}
'''

# the fake iptables-restore: refuses the first rule containing REFUSE, in the real binary's words
FAKE = r'''#!/bin/sh
# usage: iptables-restore <file>   (mode file next to the target: <file>.mode)
f="$1"
mode=""; [ -f "$FAKE_MODE" ] && mode="$(cat "$FAKE_MODE")"
case "$mode" in
  crash) echo "Segmentation fault" >&2; exit 139 ;;
  decl)  echo "iptables-restore: line 2 failed" >&2; exit 1 ;;
esac
n=$(grep -n 'REFUSE' "$f" | head -1 | cut -d: -f1)
if [ -n "$n" ]; then echo "iptables-restore: line $n failed" >&2; exit 1; fi
exit 0
'''

td = tempfile.mkdtemp(prefix="fwrestore-")
try:
    csrc = os.path.join(td, "t.c")
    with open(csrc, "w") as f:
        f.write(STUBS + "\n".join(parts) + MAIN)
    exe = os.path.join(td, "t")
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wno-unused-result", "-o", exe, csrc], capture_output=True, text=True)
    if p.returncode != 0:
        die("host compile failed:\n" + p.stderr)
    if "warning" in p.stderr:
        die("host compile warnings:\n" + p.stderr)
    binp = os.path.join(td, "bin"); os.mkdir(binp)
    fake = os.path.join(binp, "iptables-restore")
    with open(fake, "w") as f: f.write(FAKE)
    os.chmod(fake, 0o755)
    env = dict(os.environ, PATH=binp + os.pathsep + os.environ.get("PATH", ""))

    def run(rules, mode=""):
        errd = os.path.join(td, "err"); shutil.rmtree(errd, ignore_errors=True)
        rules_path = os.path.join(td, "filter_rules"); log = os.path.join(td, "log")
        with open(rules_path, "w") as f: f.write(rules)
        with open(log, "w"): pass
        modef = os.path.join(td, "mode")
        with open(modef, "w") as f: f.write(mode)
        env["FAKE_MODE"] = modef
        p = subprocess.run([exe, errd, log, rules_path], capture_output=True, text=True, env=env)
        with open(log) as f: L = f.read()
        retry = os.path.join(errd, "filter_rules.retry")
        R = open(retry).read() if os.path.isfile(retry) else None
        return p.returncode, L, R, os.path.isfile(os.path.join(errd, "filter_rules.err"))

    HEAD = "*filter\n:INPUT DROP [0:0]\n:FORWARD DROP [0:0]\n:SECURITY - [0:0]\n"
    ok = "-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT\n"
    bad1 = "-A FORWARD -m policy --dir in --pol ipsec -j REFUSE1\n"
    bad2 = "-A INPUT -p udp --dport 500 -j REFUSE2\n"
    fails = []
    def check(name, cond, detail=""):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond: fails.append(name + (" - " + detail if detail else ""))

    # 1. clean file
    rc, L, R, err = run(HEAD + ok + "COMMIT\n")
    check("clean file applies", rc == 0 and L == "", L)
    check("clean file leaves no .err", not err)

    # 2. one refused rule (line 6)
    rc, L, R, err = run(HEAD + ok + bad1 + ok + "COMMIT\n")
    check("one refused: table applied", rc == 0, L)
    check("one refused: names line 6 with the rule text", "kernel refused rule 6 of filter_rules - applying the table without it: -A FORWARD -m policy --dir in --pol ipsec -j REFUSE1" in L, L)
    check("one refused: keeps the restore's own words", "iptables-restore /" in L and "failed (rc 1): iptables-restore: line 6 failed" in L, L)
    check("one refused: retry file lacks exactly that line", R is not None and "REFUSE1" not in R and R.count("\n") == HEAD.count("\n") + 3, repr(R))
    check("one refused: success line counts 1", "applied with 1 rule(s) skipped" in L, L)
    check("one refused: rule_apply_checking still ran (copy kept)", "apply rules error(4242)" in L, L)

    # 3. two refused rules, in order
    rc, L, R, err = run(HEAD + bad1 + ok + bad2 + "COMMIT\n")
    check("two refused: applied", rc == 0, L)
    i1, i2 = L.find("REFUSE1"), L.find("REFUSE2")
    check("two refused: both named, in order", 0 <= i1 < i2, L)
    check("two refused: counts 2", "applied with 2 rule(s) skipped" in L, L)
    check("two refused: retry file clean", R is not None and "REFUSE" not in R and ok in R, repr(R))

    # 4. refusal on a chain declaration (line 2) is not stripped
    rc, L, R, err = run(HEAD + ok + "COMMIT\n", mode="decl")
    check("declaration refused: NOT applied", rc != 0 and "NOT applied" in L, L)
    check("declaration refused: nothing stripped", "kernel refused rule" not in L, L)

    # 5. a crash names no line
    rc, L, R, err = run(HEAD + ok + "COMMIT\n", mode="crash")
    check("crash: NOT applied, output kept", rc != 0 and "Segmentation fault" in L and "NOT applied" in L, L)
    check("crash: nothing stripped", "kernel refused rule" not in L, L)

    # 6. the cap: nine refused rules -> stop after eight
    nine = "".join("-A FORWARD -p tcp --dport %d -j REFUSE%d\n" % (1000 + i, i) for i in range(9))
    rc, L, R, err = run(HEAD + nine + ok + "COMMIT\n")
    check("cap: NOT applied after eight", rc != 0 and L.count("kernel refused rule") == 8 and "NOT applied" in L, L)

    if fails:
        print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
    print("all checks passed: reaper_restore_rules() skips a refused rule, names it, and stops where it must")
finally:
    shutil.rmtree(td, ignore_errors=True)
