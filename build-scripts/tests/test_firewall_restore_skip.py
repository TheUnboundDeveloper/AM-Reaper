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

SECOND ROUND (2026-09-14, the same RT-BE88U on v3.1.6). The line the restore names is
COMMIT whenever the KERNEL refuses a rule - iptables 1.4.15 commits the whole table in one
setsockopt - and the line loop refuses to drop a COMMIT line, so the first fix could never
fire for a kernel refusal. The tester's box refused the closed blob's `-m string`/`-m u32`
anti-botnet rules, and its kernel REGISTERS both (read out of the CI image's IKCONFIG), so
a registry lookup alone would not have helped it either. reaper_restore_rules() now asks
the kernel two ways: the registry (/proc/net/ip_tables_matches|targets, after a modprobe
attempt) and a PROBE of each distinct rule shape alone in a scratch chain through
`iptables-restore --noflush`. Rules that fail either are left out, logged verbatim, and the
table is retried once.

THIRD ROUND (2026-09-15, the same box). The refused file committed cleanly BY HAND - same
bytes, same kernel, rc 0, empty dmesg. The cause is a RACE: this iptables 1.4.x has no xtables
lock, and the kernel refuses a replace at COMMIT with EAGAIN (pr_debug only) when another
process changed the table between the `*filter` snapshot and COMMIT. The writer is the
nat-start hook, which start_nat_rules() forks (not waited for) from nat_setting(), i.e.
BEFORE filter_setting() runs - the tester's Tailscale script inserts FORWARD rules right
inside the window. reaper_restore_run() now re-runs the identical file up to five times
with a doubling pause on a COMMIT-line failure, before anything is hoisted, probed or
dropped, and says so in one log line when the retry is what made it pass.

WHAT IT DOES. Extracts reaper_restore_rules() and its helpers from the real firewall.c
(brace-matched, not copied), compiles them on the host with stubs for _eval (runs a fake
iptables-restore), eval (no-op), logmessage (captured), rule_apply_checking and
check_if_dir_exist, and drives them with a fake `iptables-restore` that refuses:
  - any rule containing the token REFUSE with the real binary's wording, at that line
    (a parse-stage failure); or, in `kernel` mode,
  - at the COMMIT line whenever a `-m string` or `-m u32` rule is present, and, run with
    --noflush on a probe file, whenever that probe file carries one of those rules.
A fake registry directory stands in for /proc/net/ip_tables_*. Asserts:
  - a clean file applies first time and leaves no .err file behind;
  - one refused rule: the table is applied without it, the rule text is in the log, the
    retry file lacks exactly that line, and the success line counts 1 skipped;
  - two refused rules: both skipped, in order, 2 counted;
  - a refusal on a chain-declaration line is NOT stripped: the table stays unapplied and
    the log says so;
  - a refusal that names no line (a crash) is logged with the restore's output and left;
  - the cap: nine refused rules stop after eight and report NOT applied;
  - COMMIT refusal, registry lacks string/u32: exactly those rules are dropped, each named
    with its match, the chain declarations stay, the table applies, the count is right;
  - COMMIT refusal, registry HAS string/u32 (the reporter's kernel): the probe finds them,
    the same rules are dropped with the probe's wording, the table applies;
  - COMMIT refusal with nothing the kernel objects to: nothing is stripped on a guess and
    the table is reported NOT applied, after five identical tries;
  - the race: two COMMIT refusals then success -> applied in full on try 3, one log line
    naming the collision, nothing stripped, hoisted or probed, no error copy kept.
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
    "#define REAPER_RESTORE_MAX_SKIP 8\n#define REAPER_ERR_RULES ERR_DIR\n"
    "#define REAPER_NF_MATCHES4 NF_M4\n#define REAPER_NF_TARGETS4 NF_T4\n"
    "#define REAPER_NF_MATCHES6 NF_M6\n#define REAPER_NF_TARGETS6 NF_T6\n"
    "#define REAPER_NF_PROBE_CHAIN \"REAPER_PROBE\"\n#define REAPER_NF_PROBE_FILE NF_PROBE\n"
    "#define REAPER_NF_MAXNAMES 64\n#define REAPER_NF_MAXSIGS 48\n"
    "#define REAPER_RESTORE_RACE_TRIES 5\n#define REAPER_RESTORE_RACE_WAIT_US 1000u\n",
    extract(source, "static int reaper_nf_listed("),
    extract(source, "static int reaper_nf_supported("),
    extract(source, "static void reaper_nf_declared("),
    extract(source, "static int reaper_nf_rule_names("),
    extract(source, "static int reaper_nf_probe_form("),
    extract(source, "static int reaper_nf_probe("),
    extract(source, "static int reaper_nf_forward_refs("),
    extract(source, "static int reaper_nf_copy_supported("),
    extract(source, "static int reaper_restore_drop_unsupported("),
    extract(source, "static void reaper_restore_read_err("),
    extract(source, "static int reaper_restore_lineno("),
    extract(source, "static int reaper_restore_hoist("),
    extract(source, "static int reaper_restore_drop_line("),
    extract(source, "static int reaper_restore_is_commit("),
    extract(source, "static void reaper_restore_log_race("),
    extract(source, "static int reaper_restore_run("),
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
static const char *ERR_DIR, *NF_M4, *NF_T4, *NF_M6, *NF_T6;
static char *NF_PROBE;
static FILE *LOG;
#define eval(...) ((void)0)
void logmessage(const char *tag, const char *fmt, ...) { va_list ap; va_start(ap, fmt); fprintf(LOG, "%s: ", tag); vfprintf(LOG, fmt, ap); fputc('\n', LOG); va_end(ap); fflush(LOG); }
int check_if_dir_exist(const char *p) { struct stat st; return stat(p, &st) == 0 && S_ISDIR(st.st_mode); }
void rule_apply_checking(char *caller, int line, char *rule_path, int ret) { logmessage(caller, "apply rules error(%d)", line); }
/* the real _eval forks, redirects stdout+stderr to path (">file"), execvp's argv */
int _eval(char *const argv[], const char *path, int timeout, int *ppid) {
	char cmd[4096]; int n = 0, i;
	for (i = 0; argv[i]; i++) n += snprintf(cmd + n, sizeof(cmd) - n, "%s%s", i ? " " : "", argv[i]);
	if (path && *path == '>') n += snprintf(cmd + n, sizeof(cmd) - n, " >%s 2>&1", path + 1);
	int st = system(cmd);
	return st == -1 ? 127 : (WIFEXITED(st) ? WEXITSTATUS(st) : 128);
}
'''
MAIN = r'''
int main(int argc, char **argv) {
	ERR_DIR = argv[1]; LOG = fopen(argv[2], "a");
	NF_M4 = argv[4]; NF_T4 = argv[5]; NF_M6 = argv[6]; NF_T6 = argv[7]; NF_PROBE = argv[8];
	int r = reaper_restore_rules("iptables-restore", argv[3], 4242);
	printf("rc=%d\n", r); return r ? 1 : 0;
}
'''

# the fake iptables-restore. Modes (file $FAKE_MODE):
#   ""      refuse the first rule containing REFUSE, at its line
#   crash   segfault
#   decl    refuse line 2 (a chain declaration)
#   kernel  refuse at the COMMIT line whenever a -m string / -m u32 rule is present;
#           a --noflush probe file is judged the same way (the probe IS the rule)
#   commit  refuse at the COMMIT line whatever the file holds (a cause nobody can see)
#   race    refuse at the COMMIT line on the first two runs (another writer changed the
#           table under the restore - the kernel's EAGAIN), then take the file
FAKE = r'''#!/bin/sh
mode=""; [ -f "$FAKE_MODE" ] && mode="$(cat "$FAKE_MODE")"
noflush=0; [ "$1" = "--noflush" ] && { noflush=1; shift; }
f="$1"
echo "restore $noflush $f" >> "$FAKE_TRACE"
case "$mode" in
  crash) echo "Segmentation fault" >&2; exit 139 ;;
  decl)  [ "$noflush" = 1 ] && exit 0; echo "iptables-restore: line 2 failed" >&2; exit 1 ;;
  kernel)
    if grep -qE -- '-m (string|u32)( |$)' "$f"; then
      c=$(grep -n '^COMMIT' "$f" | head -1 | cut -d: -f1)
      echo "iptables-restore: line $c failed" >&2; exit 1
    fi
    exit 0 ;;
  commit)
    [ "$noflush" = 1 ] && exit 0
    c=$(grep -n '^COMMIT' "$f" | head -1 | cut -d: -f1)
    echo "iptables-restore: line $c failed" >&2; exit 1 ;;
  race)
    [ "$noflush" = 1 ] && exit 0
    k=$(cat "$FAKE_COUNT" 2>/dev/null || echo 0); k=$((k+1)); echo "$k" > "$FAKE_COUNT"
    if [ "$k" -le 2 ]; then
      c=$(grep -n '^COMMIT' "$f" | head -1 | cut -d: -f1)
      echo "iptables-restore: line $c failed" >&2; exit 1
    fi
    exit 0 ;;
  order)
    # the real 1.4.15 behaviour, measured on the RT-BE88U 2026-09-14: a -j to a chain declared
    # LATER is refused when the rule is READ, with the number on a later stderr line
    hit=$(awk '/^:/{decl[substr($1,2)]=1} /^-[AI] /{for(i=1;i<NF;i++) if($i=="-j"){t=$(i+1); if(t!="ACCEPT"&&t!="DROP"&&t!="RETURN"&&t!="LOG"&&!(t in decl)){print NR ":" t; exit}}}' "$f")
    if [ -n "$hit" ]; then
      printf "iptables-restore v1.4.15: Couldn't load target \`%s':No such file or directory\n\nError occurred at line: %s\nTry \`iptables-restore -h' or 'iptables-restore --help' for more information.\n" "${hit#*:}" "${hit%%:*}" >&2; exit 2
    fi
    exit 0 ;;
  parse)
    # a parse-stage refusal of a REFUSE rule, in the 1.4.15 wording (number on a later line)
    n=$(grep -n 'REFUSE' "$f" | head -1 | cut -d: -f1)
    if [ -n "$n" ]; then printf "iptables-restore v1.4.15: Couldn't load target \`REFUSE':No such file or directory\n\nError occurred at line: %s\n" "$n" >&2; exit 2; fi
    exit 0 ;;
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
    nfd = os.path.join(td, "nf"); os.mkdir(nfd)
    NF = {k: os.path.join(nfd, k) for k in ("m4", "t4", "m6", "t6")}
    probe = os.path.join(td, "probe.rules")

    def registry(matches, targets):
        for k, names in (("m4", matches), ("t4", targets), ("m6", matches), ("t6", targets)):
            with open(NF[k], "w") as f: f.write("".join(n + "\n" for n in names))

    def run(rules, mode=""):
        errd = os.path.join(td, "err"); shutil.rmtree(errd, ignore_errors=True)
        rules_path = os.path.join(td, "filter_rules"); log = os.path.join(td, "log")
        with open(rules_path, "w") as f: f.write(rules)
        with open(log, "w"): pass
        modef = os.path.join(td, "mode"); trace = os.path.join(td, "trace")
        count = os.path.join(td, "count")
        with open(modef, "w") as f: f.write(mode)
        with open(trace, "w"): pass
        if os.path.isfile(count): os.remove(count)
        env["FAKE_MODE"] = modef; env["FAKE_TRACE"] = trace; env["FAKE_COUNT"] = count
        p = subprocess.run([exe, errd, log, rules_path, NF["m4"], NF["t4"], NF["m6"], NF["t6"], probe],
                           capture_output=True, text=True, env=env)
        with open(log) as f: L = f.read()
        with open(trace) as f: T = f.read()
        retry = os.path.join(errd, "filter_rules.retry")
        R = open(retry).read() if os.path.isfile(retry) else None
        return p.returncode, L, R, os.path.isfile(os.path.join(errd, "filter_rules.err")), T

    HEAD = "*filter\n:INPUT DROP [0:0]\n:FORWARD DROP [0:0]\n:SECURITY - [0:0]\n"
    ok = "-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT\n"
    bad1 = "-A FORWARD -m policy --dir in --pol ipsec -j REFUSE1\n"
    bad2 = "-A INPUT -p udp --dport 500 -j REFUSE2\n"
    # the closed blob's block, as the RT-BE88U's refused copy carries it (2 of the 16 domains)
    BLOB = (":OUTPUT_DNS - [0:0]\n:logdrop_dns - [0:0]\n:OUTPUT_IP - [0:0]\n:logdrop_ip - [0:0]\n"
            "-A logdrop_dns -j LOG --log-prefix \"DROP_DNS \" --log-tcp-sequence --log-tcp-options --log-ip-options\n"
            "-A logdrop_dns -j DROP\n"
            "-A OUTPUT -p udp --dport 53 -m u32 --u32 0>>22&0x3c@8>>15&1=0 -j OUTPUT_DNS\n"
            "-A OUTPUT -p tcp --dport 53 -m u32 --u32 0>>22&0x3c@12>>26&0x3c@8>>15&1=0 -j OUTPUT_DNS\n"
            "-A OUTPUT_DNS -m string --icase --hex-string \"|08|hackucdt|03|com|00|\" --algo bm -j logdrop_dns\n"
            "-A OUTPUT_DNS -m string --icase --hex-string \"|07|uctkone|03|com|00|\" --algo bm -j logdrop_dns\n"
            "-A OUTPUT -j OUTPUT_IP\n"
            "-A OUTPUT_IP -d 51.15.120.245 -j logdrop_ip\n"
            "-A logdrop_ip -j DROP\n")
    BASE_REG = ["state", "policy", "conntrack", "mark", "set", "tcp", "udp"]
    BASE_TGT = ["LOG", "TCPMSS", "MARK"]
    fails = []
    def check(name, cond, detail=""):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond: fails.append(name + (" - " + detail if detail else ""))

    registry(BASE_REG + ["string", "u32"], BASE_TGT)

    # 1. clean file
    rc, L, R, err, T = run(HEAD + ok + "COMMIT\n")
    check("clean file applies", rc == 0 and L == "", L)
    check("clean file leaves no .err", not err)

    # 2. one refused rule (line 6)
    rc, L, R, err, T = run(HEAD + ok + bad1 + ok + "COMMIT\n")
    check("one refused: table applied", rc == 0, L)
    check("one refused: names line 6 with the rule text", "kernel refused rule 6 of filter_rules - applying the table without it: -A FORWARD -m policy --dir in --pol ipsec -j REFUSE1" in L, L)
    check("one refused: keeps the restore's own words", "iptables-restore /" in L and "failed (rc 1): iptables-restore: line 6 failed" in L, L)
    check("one refused: retry file lacks exactly that line", R is not None and "REFUSE1" not in R and R.count("\n") == HEAD.count("\n") + 3, repr(R))
    check("one refused: success line counts 1", "applied with 1 rule(s) skipped" in L, L)
    check("one refused: rule_apply_checking still ran (copy kept)", "apply rules error(4242)" in L, L)

    # 3. two refused rules, in order
    rc, L, R, err, T = run(HEAD + bad1 + ok + bad2 + "COMMIT\n")
    check("two refused: applied", rc == 0, L)
    i1, i2 = L.find("REFUSE1"), L.find("REFUSE2")
    check("two refused: both named, in order", 0 <= i1 < i2, L)
    check("two refused: counts 2", "applied with 2 rule(s) skipped" in L, L)
    check("two refused: retry file clean", R is not None and "REFUSE" not in R and ok in R, repr(R))

    # 4. refusal on a chain declaration (line 2) is not stripped, and - the registry and the
    #    probe both being satisfied - nothing is stripped on a guess either
    rc, L, R, err, T = run(HEAD + ok + "COMMIT\n", mode="decl")
    check("declaration refused: NOT applied", rc != 0 and "NOT applied" in L, L)
    check("declaration refused: nothing stripped", "kernel refused rule" not in L and "dropped:" not in L, L)
    check("declaration refused: the kernel is not asked (no probe)", "restore 1 " not in T, T)

    # 5. a crash names no line
    rc, L, R, err, T = run(HEAD + ok + "COMMIT\n", mode="crash")
    check("crash: NOT applied, output kept", rc != 0 and "Segmentation fault" in L and "NOT applied" in L, L)
    check("crash: nothing stripped", "kernel refused rule" not in L and "dropped:" not in L, L)

    # 6. the cap: nine refused rules -> stop after eight
    nine = "".join("-A FORWARD -p tcp --dport %d -j REFUSE%d\n" % (1000 + i, i) for i in range(9))
    rc, L, R, err, T = run(HEAD + nine + ok + "COMMIT\n")
    check("cap: NOT applied after eight", rc != 0 and L.count("kernel refused rule") == 8 and "NOT applied" in L, L)

    # 7. a KERNEL refusal (COMMIT line) with a registry that lacks string and u32
    registry(BASE_REG, BASE_TGT)
    rc, L, R, err, T = run(HEAD + ok + BLOB + ok + "COMMIT\n", mode="kernel")
    check("registry: table applied", rc == 0, L)
    check("registry: the four blocklist rules dropped, four counted", L.count(" - dropped: ") == 4 and "applied with 4 rule(s) skipped" in L, L)
    check("registry: each named with its match", L.count("kernel has no 'u32' match - dropped: -A OUTPUT -p") == 2 and L.count("kernel has no 'string' match - dropped: -A OUTPUT_DNS") == 2, L)
    check("registry: retry file keeps the declarations and the rest", R is not None and ":OUTPUT_DNS - [0:0]" in R and "-A OUTPUT_IP -d 51.15.120.245 -j logdrop_ip" in R and "-A OUTPUT -j OUTPUT_IP" in R and ok in R and "-m string" not in R and "-m u32" not in R, repr(R))
    check("registry: the line loop did not fire", "kernel refused rule" not in L, L)
    check("registry: the file five times (the race guard), then the retry once", T.count("restore 0 ") == 6, T)

    # 8. the reporter's kernel: string and u32 ARE registered and still refused -> the probe
    registry(BASE_REG + ["string", "u32"], BASE_TGT)
    rc, L, R, err, T = run(HEAD + ok + BLOB + ok + "COMMIT\n", mode="kernel")
    check("probe: table applied", rc == 0, L)
    check("probe: the four blocklist rules dropped with the probe's wording", L.count("kernel refuses a rule using 'u32' (probed alone in a scratch chain) - dropped: ") == 2 and L.count("kernel refuses a rule using 'string' (probed alone in a scratch chain) - dropped: ") == 2, L)
    check("probe: counted 4", "applied with 4 rule(s) skipped" in L, L)
    check("probe: one probe per distinct rule shape, not per rule", T.count("restore 1 ") <= 6 and T.count("restore 1 ") >= 2, T)
    check("probe: 'has no' never claimed on a registered name", "kernel has no" not in L, L)
    check("probe: retry file keeps the rest", R is not None and "-m string" not in R and "-m u32" not in R and ok in R and ":OUTPUT_DNS - [0:0]" in R, repr(R))

    # 9. a COMMIT refusal nobody can see: every name registered, every probe passes ->
    #    nothing stripped on a guess, NOT applied, the cause still on record
    rc, L, R, err, T = run(HEAD + ok + BLOB + ok + "COMMIT\n", mode="commit")
    check("opaque: NOT applied", rc != 0 and "NOT applied" in L, L)
    check("opaque: nothing stripped on a guess", "dropped:" not in L and "kernel refused rule" not in L, L)
    check("opaque: the identical file was tried five times first", T.count("restore 0 ") == 5, T)
    check("opaque: says it was a real refusal, not a collision", "refused at its COMMIT line on all 5 tries" in L, L)

    # 10. the RT-BE88U shape (2026-09-14, the tester's kernel takes every rule alone): the
    #     blob declares OUTPUT_DNS / logdrop_ip AFTER the rules that jump to them
    BLOB_LATE = ("-A logdrop_dns -j LOG --log-prefix \"DROP_DNS \" --log-tcp-sequence --log-tcp-options --log-ip-options\n"
                 "-A logdrop_dns -j DROP\n"
                 "-A OUTPUT -p udp --dport 53 -m u32 --u32 0>>22&0x3c@8>>15&1=0 -j OUTPUT_DNS\n"
                 ":OUTPUT_DNS - [0:0]\n:logdrop_dns - [0:0]\n"
                 "-A OUTPUT_DNS -m string --icase --hex-string \"|08|hackucdt|03|com|00|\" --algo bm -j logdrop_dns\n"
                 "-A OUTPUT -j OUTPUT_IP\n:OUTPUT_IP - [0:0]\n"
                 "-A OUTPUT_IP -d 51.15.120.245 -j logdrop_ip\n:logdrop_ip - [0:0]\n-A logdrop_ip -j DROP\n")
    rc, L, R, err, T = run(HEAD + ok + BLOB_LATE + ok + "COMMIT\n", mode="order")
    check("late decl: table applied in FULL", rc == 0 and "applied in full after moving 4 chain declaration(s)" in L, L)
    check("late decl: the parser's own words are kept, joined", "Couldn't load target `OUTPUT_DNS'" in L and " | Error occurred at line: 8" in L, L)
    m = re.search(r"4 chain\(s\) of filter_rules \(([^)]*)\) were declared after the first rule that jumps to them", L)
    check("late decl: names the four late chains (appended-to and jumped-to alike)", m is not None and sorted(m.group(1).split(",")) == ["OUTPUT_DNS", "OUTPUT_IP", "logdrop_dns", "logdrop_ip"], L)
    check("late decl: nothing dropped", "dropped:" not in L and "skipped" not in L and "kernel refused rule" not in L, L)
    first_rule = R.find("\n-A") if R else -1
    last_decl = R.rfind("\n:") if R else -1
    check("late decl: every declaration precedes the first rule in the retry file", R is not None and 0 < last_decl < first_rule and R.startswith("*filter\n"), repr(R))
    check("late decl: same lines, only reordered", R is not None and sorted(R.splitlines()) == sorted((HEAD + ok + BLOB_LATE + ok + "COMMIT\n").splitlines()), repr(R))
    check("late decl: tried exactly twice (file, hoisted file)", T.count("restore 0 ") == 2, T)

    # 11. a parse-stage refusal in the 1.4.15 wording (the number on a later line, after a
    #     blank one): the line loop must still find it and strip that rule
    rc, L, R, err, T = run(HEAD + ok + bad1 + ok + "COMMIT\n", mode="parse")
    check("parse wording: table applied with the rule skipped", rc == 0 and "applied with 1 rule(s) skipped" in L, L)
    check("parse wording: line 6 found through 'Error occurred at line: 6'", "kernel refused rule 6 of filter_rules" in L and "REFUSE1" in L, L)

    # 12. the RT-BE88U race (2026-09-15): the file is fine; another process changed the
    #     table under the restore twice running, and the third identical run commits
    rc, L, R, err, T = run(HEAD + ok + BLOB + ok + "COMMIT\n", mode="race")
    check("race: table applied in full", rc == 0, L)
    check("race: applied on try 3 of 5, and says why", "filter_rules applied on try 3 of 5 - another process changed the table while the restore was reading it" in L, L)
    check("race: nothing stripped, hoisted or probed", "dropped:" not in L and "kernel refused rule" not in L and "declared after" not in L and "restore 1 " not in T, L + T)
    check("race: the identical file was run exactly three times", T.count("restore 0 ") == 3 and T.count("filter_rules.retry") == 0, T)
    check("race: no error copy, no .err, no retry file", not err and R is None and "apply rules error" not in L, L)
    check("race: one line only", L.count("\n") == 1, L)

    if fails:
        print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
    print("all checks passed: reaper_restore_rules() rides out a collision with another writer, skips a refused rule, names it, asks the kernel about a COMMIT refusal, and stops where it must")
finally:
    shutil.rmtree(td, ignore_errors=True)
