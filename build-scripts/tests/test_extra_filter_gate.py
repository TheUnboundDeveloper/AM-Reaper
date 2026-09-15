#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The closed blob's anti-botnet blocklist may never take the whole filter table down.

WHY THIS EXISTS. Field data (RT-BE88U on v3.1.6, 2026-09-14): write_extra_filter() in the
closed rc/prebuild/<model>/private.o appends ASUS's OUTPUT_DNS / OUTPUT_IP blocklist -
`-m u32` and `-m string --algo bm` rules - to /tmp/filter_rules right before COMMIT, on every
model, with no switch. The tester's kernel refused those rules, and because iptables-restore
is atomic the WHOLE table stayed the boot skeleton: no port forwards, no VPN server chains,
no DoS guard, for as long as the box ran. The blob cannot be changed; what it writes can.
rc/firewall.c reaper_write_extra_filter() runs the blob into a scratch file and copies only
the rules this kernel takes into the table (registry first, then a probe of each distinct
rule shape alone in a scratch chain), logging once per boot what it left out. Both emitters
(filter_setting, filter_setting2) must call the wrapper, not the blob.

WHAT IT DOES. Extracts reaper_write_extra_filter() and the reaper_nf_* helpers from the real
firewall.c (brace-matched), compiles them with a stub write_extra_filter() that emits the
tester's block, a fake registry and a fake `iptables-restore` for the probe, and asserts:
  - registry lacks string/u32: no `-m string` / `-m u32` line reaches the table; the chain
    declarations, `-A OUTPUT -j OUTPUT_IP` and the `-d <ip>` lines do; ONE log line names the
    match and the count, and a second call in the same boot logs nothing more;
  - registry has both but the probe refuses them (the reporter's kernel): same result;
  - registry has both and the probe takes them: the block passes through byte for byte and
    nothing is logged;
  - on the real source, both `write_extra_filter(fp)` call sites are gone and both
    `reaper_write_extra_filter(fp)` calls are present.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

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

# the call sites, on the real source (whole-line comments stripped so a comment quoting
# the old call cannot satisfy or fail the check)
code = "\n".join(l for l in source.splitlines() if not l.strip().startswith(("*", "/*", "//")))
# the wrapper's own fallback call (fopen failed -> the blob writes straight through) is the
# one bare call allowed; judge the rest of the file without it
code = code.replace(extract(code, "static void reaper_write_extra_filter("), "")
if len(re.findall(r"^\s*write_extra_filter\(fp\);", code, re.M)) != 0:
    die("a bare write_extra_filter(fp) call is back in firewall.c - the blob's block must go through reaper_write_extra_filter()")
if len(re.findall(r"^\s*reaper_write_extra_filter\(fp\);", code, re.M)) != 2:
    die("expected exactly 2 reaper_write_extra_filter(fp) call sites (filter_setting, filter_setting2)")
print("  ok  both filter emitters call reaper_write_extra_filter(fp); the bare blob call is gone")

parts = [
    "#define REAPER_NF_MATCHES4 NF_M4\n#define REAPER_NF_TARGETS4 NF_T4\n"
    "#define REAPER_NF_MATCHES6 NF_M4\n#define REAPER_NF_TARGETS6 NF_T4\n"
    "#define REAPER_NF_PROBE_CHAIN \"REAPER_PROBE\"\n#define REAPER_NF_PROBE_FILE NF_PROBE\n"
    "#define REAPER_NF_MAXNAMES 64\n#define REAPER_NF_MAXSIGS 48\n"
    "#define REAPER_EXTRA_TMP EXTRA_TMP\n#define REAPER_EXTRA_WARNED EXTRA_WARNED\n",
    extract(source, "static int reaper_nf_listed("),
    extract(source, "static int reaper_nf_supported("),
    extract(source, "static void reaper_nf_declared("),
    extract(source, "static int reaper_nf_rule_names("),
    extract(source, "static int reaper_nf_probe_form("),
    extract(source, "static int reaper_nf_probe("),
    extract(source, "static int reaper_nf_forward_refs("),
    extract(source, "static int reaper_nf_copy_supported("),
    extract(source, "static void reaper_write_extra_filter("),
]

BLOB_C = r'''
/* the RT-BE88U shape (2026-09-14): OUTPUT_DNS and logdrop_ip are declared AFTER the
 * first rule that jumps to them - which iptables-restore cannot resolve */
static const char *BLOB =
":logdrop_dns - [0:0]\n"
"-A logdrop_dns -j LOG --log-prefix \"DROP_DNS \" --log-tcp-sequence --log-tcp-options --log-ip-options\n"
"-A logdrop_dns -j DROP\n"
"-A OUTPUT -p udp --dport 53 -m u32 --u32 0>>22&0x3c@8>>15&1=0 -j OUTPUT_DNS\n"
"-A OUTPUT -p tcp --dport 53 -m u32 --u32 0>>22&0x3c@12>>26&0x3c@8>>15&1=0 -j OUTPUT_DNS\n"
":OUTPUT_DNS - [0:0]\n"
"-A OUTPUT_DNS -m string --icase --hex-string \"|08|hackucdt|03|com|00|\" --algo bm -j logdrop_dns\n"
"-A OUTPUT_DNS -m string --icase --hex-string \"|07|uctkone|03|com|00|\" --algo bm -j logdrop_dns\n"
":OUTPUT_IP - [0:0]\n"
"-A OUTPUT -j OUTPUT_IP\n"
"-A OUTPUT_IP -d 51.15.120.245 -j logdrop_ip\n"
"-A OUTPUT_IP -d 45.33.73.134 -j logdrop_ip\n"
":logdrop_ip - [0:0]\n"
"-A logdrop_ip -j LOG --log-prefix \"DROP_IP \" --log-tcp-sequence --log-tcp-options --log-ip-options\n"
"-A logdrop_ip -j DROP\n";
void write_extra_filter(FILE *fp) { fputs(BLOB, fp); }
'''
STUBS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
static const char *NF_M4, *NF_T4, *EXTRA_TMP, *EXTRA_WARNED;
static char *NF_PROBE;
static FILE *LOG;
#define eval(...) ((void)0)
void logmessage(const char *tag, const char *fmt, ...) { va_list ap; va_start(ap, fmt); fprintf(LOG, "%s: ", tag); vfprintf(LOG, fmt, ap); fputc('\n', LOG); va_end(ap); fflush(LOG); }
int f_exists(const char *p) { struct stat st; return stat(p, &st) == 0; }
int f_write_string(const char *p, const char *s, unsigned fl, unsigned mode) { FILE *f = fopen(p, "w"); if (!f) return -1; fputs(s, f); fclose(f); return 0; }
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
	LOG = fopen(argv[1], "a"); NF_M4 = argv[2]; NF_T4 = argv[3]; NF_PROBE = argv[4]; EXTRA_TMP = argv[5]; EXTRA_WARNED = argv[6];
	FILE *out = fopen(argv[7], "w");
	reaper_write_extra_filter(out); fclose(out);
	return 0;
}
'''
# the fake iptables-restore: refuses a --noflush probe carrying -m string / -m u32 when
# $FAKE_MODE says `refuse`; takes everything otherwise
FAKE = r'''#!/bin/sh
mode=""; [ -f "$FAKE_MODE" ] && mode="$(cat "$FAKE_MODE")"
[ "$1" = "--noflush" ] && shift
echo "probe $1" >> "$FAKE_TRACE"
if [ "$mode" = refuse ] && grep -qE -- '-m (string|u32)( |$)' "$1"; then
  echo "iptables-restore: line 4 failed" >&2; exit 1
fi
exit 0
'''

td = tempfile.mkdtemp(prefix="extrafilter-")
try:
    csrc = os.path.join(td, "t.c")
    with open(csrc, "w") as f:
        f.write(STUBS + BLOB_C + "\n".join(parts) + MAIN)
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
    m4 = os.path.join(td, "m4"); t4 = os.path.join(td, "t4")
    with open(t4, "w") as f: f.write("LOG\n")

    def run(matches, mode, warned_exists=False):
        with open(m4, "w") as f: f.write("".join(n + "\n" for n in matches))
        log = os.path.join(td, "log"); out = os.path.join(td, "out")
        warned = os.path.join(td, "warned"); trace = os.path.join(td, "trace")
        if os.path.exists(warned) and not warned_exists: os.unlink(warned)
        with open(log, "w"): pass
        with open(trace, "w"): pass
        modef = os.path.join(td, "mode")
        with open(modef, "w") as f: f.write(mode)
        env["FAKE_MODE"] = modef; env["FAKE_TRACE"] = trace
        p = subprocess.run([exe, log, m4, t4, os.path.join(td, "probe.rules"), os.path.join(td, "extra.tmp"), warned, out],
                           capture_output=True, text=True, env=env)
        if p.returncode != 0: die("run failed: %s %s" % (p.stdout, p.stderr))
        with open(log) as f: L = f.read()
        with open(out) as f: O = f.read()
        with open(trace) as f: T = f.read()
        return L, O, T

    BASE = ["state", "tcp", "udp", "conntrack"]
    fails = []
    def check(name, cond, detail=""):
        print(("ok   " if cond else "FAIL ") + name)
        if not cond: fails.append(name + (" - " + detail if detail else ""))

    def decls_first(O):
        lines = O.splitlines()
        rules = [i for i, l in enumerate(lines) if l.startswith("-")]
        decls = [i for i, l in enumerate(lines) if l.startswith(":")]
        return bool(decls) and bool(rules) and max(decls) < min(rules)

    # 1. the registry lacks string and u32
    L, O, T = run(BASE, "")
    check("registry: no string/u32 rule reaches the table", "-m string" not in O and "-m u32" not in O, O)
    check("registry: declarations and the address rules stay", ":OUTPUT_DNS - [0:0]" in O and "-A OUTPUT -j OUTPUT_IP" in O and "-A OUTPUT_IP -d 51.15.120.245 -j logdrop_ip" in O and "-A logdrop_dns -j LOG" in O, O)
    check("registry: every declaration precedes the first rule", decls_first(O), O)
    check("registry: two log lines - the reorder and the drop, with the match and the count", L.count("\n") == 2 and "declares 2 chain(s) (OUTPUT_DNS,logdrop_ip) after the first rule" in L and "will not take 'u32'" in L and "4 rule(s) of the ASUS anti-botnet blocklist" in L, L)
    L2, O2, T2 = run(BASE, "", warned_exists=True)
    check("registry: a second call in the same boot logs nothing more", L2 == "" and O2 == O, L2)

    # 2. registered but refused (the reporter's kernel) -> the probe decides
    L, O, T = run(BASE + ["string", "u32"], "refuse")
    check("probe: no string/u32 rule reaches the table", "-m string" not in O and "-m u32" not in O, O)
    check("probe: the rest stays, declarations first", ":OUTPUT_DNS - [0:0]" in O and "-A OUTPUT_IP -d 45.33.73.134 -j logdrop_ip" in O and decls_first(O), O)
    check("probe: two log lines, probe wording", L.count("\n") == 2 and "will not take 'u32'" in L and "4 rule(s)" in L, L)
    check("probe: one probe per distinct rule shape", 2 <= T.count("probe ") <= 6, T)

    # 3. registered and taken (the RT-BE88U, by its own test) -> every line kept, only the
    #    declarations moved ahead of the rules, one log line saying so
    L, O, T = run(BASE + ["string", "u32"], "")
    check("passthrough: every line of the block, declarations first", O.count("-m string") == 2 and O.count("-m u32") == 2 and O.count("\n") == 15 and decls_first(O), O)
    check("passthrough: one log line, the reorder only", L.count("\n") == 1 and "declares 2 chain(s) (OUTPUT_DNS,logdrop_ip)" in L and "will not take" not in L, L)

    if fails:
        print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
    print("all checks passed: reaper_write_extra_filter() keeps the blocklist where the kernel takes it and never lets it sink the table")
finally:
    shutil.rmtree(td, ignore_errors=True)
