#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batched rule and set loads (review 2026-11-17: C-E1, C-E2, C-E3, C-6) and the 2026-11-18 QoS field fix.

WHY. The rules engine, Policy Routing and guest isolation loaded one rule per iptables process and one set member per
ipset process; guest isolation emptied its chains and refilled them rule by rule with the jumps in place, and cut
every guest connection on every firewall restart; the domain-list resolver wrote a temp file to /jffs every ten
minutes; the saved set contents were replayed on every apply. Each of these now has one load per table (or one
restore per object batch) with the old rule-by-rule path kept as the fallback. This test GENERATES the scripts with
the real code and RUNS them under stand-in tools:

  1. rules engine (rc/reaper_fw.c RFWR / RFWH / RFLR + the commit): queued lines are the same rules, in the same
     order, with the same arguments, as the rule-by-rule run; a refused commit, one bad rule and an argument the
     restore format cannot carry all end in the rule-by-rule run with its failure count.
  2. object sets (rfw_emit_sets): one `ipset restore` for the literal objects, the type test, the entry-by-entry
     fallback with the rejected entry named; the saved contents of a domain list are replayed only into an EMPTY set.
  3. the resolver (rfw_gen_resolve): an unchanged list touches nothing under /jffs.
  4. guest isolation (rc/reaper_guest.c): both chains of a family are replaced in one commit; the flow purge runs
     only when the rules or the live chains differ from the last complete load; the nat lines still run alone.
  5. the settings read (_nvc, printf form) and the QoS lines (flow-cache flush after the rules, first-packet restore).
Policy Routing's batch is checked in test_pbr_apply_script.py (it has the generator harness).
Exit 0 pass, 1 fail, 77 skipped (no compiler or no router source: pass release/src/router or set REAPER_ROUTER_SRC).
"""
import os, re, shlex, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_fw.c")):
    print("SKIP: no router source tree"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
SH = shutil.which("sh")
if not CC or not SH:
    print("SKIP: no host C compiler or no sh"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

def extract(src, signature):
    i = src.index(signature); j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    raise ValueError("unbalanced braces after " + signature)

def fakes(d, table):
    os.makedirs(d, exist_ok=True)
    for name, body in table.items():
        p = os.path.join(d, name)
        with open(p, "w", newline="\n") as fh: fh.write("#!/bin/sh\n" + body)
        os.chmod(p, 0o755)

def rd(p):
    try:
        with open(p) as fh: return fh.read()
    except OSError:
        return ""

fw = read("rc/reaper_fw.c"); guest = read("rc/reaper_guest.c"); qos = read("rc/qos.c"); nvh = read("rc/reaper_nv.h")
td = tempfile.mkdtemp(prefix="p7batch-")
try:
    # ================= 1. the rules engine's queue =================
    b1 = fw[fw.index('\tfprintf(f,\n\t  "RFW_FAIL=0\\n"'):fw.index('fi; }\\n\\n");') + len('fi; }\\n\\n");')]
    s2 = fw.index('\tfprintf(f,\n\t  "if [ \\"$RFWB\\" != 0 ]; then\\n"')
    b2 = fw[s2:fw.index('"fi\\n\\n");', s2) + len('"fi\\n\\n");')]
    rfw = os.path.join(td, "rfw"); os.mkdir(rfw); fl = os.path.join(td, "fwlog"); os.mkdir(fl)
    c1 = os.path.join(td, "q.c")
    with open(c1, "w") as fh:
        fh.write('#include <stdio.h>\n#define RFL_DIR "%s"\n#define RFW_DIR "%s"\n#include "reaper_fwlog.h"\n'
                 'int main(void) { FILE *f = stdout;\n%s\nfprintf(f, "@@BODY@@\\n");\n%s\nreturn 0; }\n' % (fl, rfw, b1, b2))
    g1 = os.path.join(td, "q")
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wno-unused-function", "-o", g1, c1, "-I", os.path.join(SRC, "shared")],
                       capture_output=True, text=True)
    check("rules engine: the queue helpers and the commit compile on the host", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        tmpl = subprocess.run([g1], capture_output=True, text=True).stdout
        BODY = ("RFWR iptables -A REAPER_FWF -s 192.0.2.4 -j DROP\n"
                "RFLR 43 'REAPER-FW:5 ' '-m limit --limit 6/min --limit-burst 12 ' iptables -A REAPER_FWF -s 192.0.2.4\n"
                "RFWR iptables -A REAPER_FWF ! -s 192.0.2.9 -m comment --comment 'two words' -j RETURN\n"
                "RFWR ip6tables -A REAPER_FWF -s 2001:db8::1 -j DROP\n"
                "RFWH iptables -t nat -F REAPER_FWN\n"
                "RFWR iptables -t nat -A REAPER_FWN -p udp --dport 53 -j DNAT --to-destination 192.0.2.1\n"
                "RFWH iptables -t nat -I PREROUTING -j REAPER_FWN\n"
                "RFWR ip6tables -t nat -I REAPER_FWHC 1 -j RETURN\n")
        TAIL = 'echo "FAIL=$RFW_FAIL HARD=$RFW_HARD NOBATCH=$RFW_NOBATCH" >> "$OUT.res"\n'
        b = os.path.join(td, "bin1")
        XT = ('T=${0##*/}; printf "%s|" "$T" "$@" >> "$OUT"; echo >> "$OUT"\ncase " $* " in *FAILME*) exit 1;; esac\nexit 0\n')
        RS = ('T=${0##*/}; T=${T%-restore}; echo "RESTORE $T $*" >> "$OUT"; bad=0\n'
              'while IFS= read -r l; do echo "$l" >> "$OUT.pay.$T"; case "$l" in *FAILME*) bad=1;; esac; done\n'
              '[ -n "$FAKE_RESTORE_FAIL" ] && { echo "refused by the test" >&2; exit 1; }\n'
              '[ "$bad" = 1 ] && { echo "line refused" >&2; exit 1; }\nexit 0\n')
        fakes(b, {"iptables": XT, "ip6tables": XT, "iptables-restore": RS, "ip6tables-restore": RS,
                  "logger": 'echo "logger $*" >> "$OUT.log"\n'})
        def run1(extra="", **envx):
            sc = os.path.join(rfw, "apply.sh"); out = os.path.join(td, "o1")
            for n in os.listdir(td):
                if n.startswith("o1"): os.unlink(os.path.join(td, n))
            with open(sc, "w", newline="\n") as fh: fh.write("#!/bin/sh\n" + tmpl.replace("@@BODY@@\n", BODY + extra) + TAIL)
            env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=out, **envx)
            p = subprocess.run([SH, sc], capture_output=True, text=True, env=env, cwd=td)
            return (rd(out), {t: rd(out + ".pay." + t) for t in ("iptables", "ip6tables")}, rd(out + ".log"), rd(out + ".res"), p)
        def split(out):
            # per (tool, table): the rule argument lists, in order, from the single calls
            d = {}
            for l in out.splitlines():
                a = l.split("|")[:-1]
                if not a or a[0] not in ("iptables", "ip6tables"): continue
                tb = "filter"; rest = a[1:]
                if rest[:1] == ["-t"]: tb = rest[1]; rest = rest[2:]
                if rest[0] in ("-A", "-I"): d.setdefault((a[0], tb), []).append(rest)
            return d
        def split_pay(pay):
            d = {}
            for tool, txt in pay.items():
                tb = None
                for l in txt.splitlines():
                    if l.startswith("*"): tb = l[1:]
                    elif l == "COMMIT" or not l: continue
                    else: d.setdefault((tool, tb), []).append(shlex.split(l))
            return d
        out, pay, log, res, p = run1()
        check("queued: only the flush runs at once; no append or insert reaches the tools one by one",
              [l for l in out.splitlines() if not l.startswith("RESTORE")] == ["iptables|-t|nat|-F|REAPER_FWN|"], out)
        check("queued: one --noflush commit per tool and table (4), each a complete payload",
              out.count("RESTORE iptables --noflush") == 2 and out.count("RESTORE ip6tables --noflush") == 2
              and pay["iptables"].count("COMMIT") == 2 and pay["ip6tables"].count("COMMIT") == 2
              and pay["iptables"].startswith("*filter\n-A REAPER_FWF -s 192.0.2.4 -j DROP\n"), out + pay["iptables"])
        check("queued: an argument with a space travels as ONE quoted argument (log prefix, comment)",
              '--log-prefix "REAPER-FW:5 " --log-level 5' in pay["iptables"] and '--comment "two words" -j RETURN' in pay["iptables"]
              and "-A REAPER_FWF ! -s 192.0.2.9 " in pay["iptables"], pay["iptables"])
        check("queued: the structural insert rides in the nat payload after the chain's own rule",
              "*nat\n-A REAPER_FWN -p udp --dport 53 -j DNAT --to-destination 192.0.2.1\n-I PREROUTING -j REAPER_FWN\nCOMMIT\n" in pay["iptables"]
              and "*nat\n-I REAPER_FWHC 1 -j RETURN\nCOMMIT\n" in pay["ip6tables"], pay["iptables"] + pay["ip6tables"])
        check("queued: nothing failed, nothing is left in the queue folder",
              res == "FAIL=0 HARD=0 NOBATCH=\n" and not [n for n in os.listdir(rfw) if n.startswith("batch.")], res + repr(os.listdir(rfw)))
        q = split_pay(pay)
        out2, pay2, log2, res2, p2 = run1(RFW_NOBATCH="1")
        check("rule by rule (RFW_NOBATCH=1): no restore is used", "RESTORE" not in out2 and res2 == "FAIL=0 HARD=0 NOBATCH=1\n", out2 + res2)
        check("the queued rules are the rule-by-rule rules: same tools, tables, order and arguments", q == split(out2) and len(q) == 4,
              repr(q) + "\n" + repr(split(out2)))
        out3, pay3, log3, res3, p3 = run1(FAKE_RESTORE_FAIL="1")
        check("commit refused: logged with the tool's words, the script runs itself again and loads rule by rule",
              "batched rule load refused (refused by the test) - loading rule by rule" in log3 and res3 == "FAIL=0 HARD=0 NOBATCH=1\n"
              and split(out3) == split(out2), log3 + res3)
        out4, pay4, log4, res4, p4 = run1("RFWR iptables -A REAPER_FWF -s FAILME -j DROP\n")
        check("one rule the kernel refuses: every other rule still loads and that one is counted and named",
              res4 == "FAIL=1 HARD=0 NOBATCH=1\n" and "rule failed: iptables -A REAPER_FWF -s FAILME -j DROP" in log4
              and "iptables|-A|REAPER_FWF|-s|192.0.2.4|-j|DROP|" in out4 and "iptables|-t|nat|-I|PREROUTING|-j|REAPER_FWN|" in out4, res4 + log4)
        out5, pay5, log5, res5, p5 = run1("RFWR iptables -A REAPER_FWF -m comment --comment 'a\"b' -j RETURN\n")
        check("an argument holding a double quote is never put in a payload: no commit is tried, rule by rule instead",
              "RESTORE" not in out5 and res5 == "FAIL=0 HARD=0 NOBATCH=1\n" and 'iptables|-A|REAPER_FWF|-m|comment|--comment|a"b|-j|RETURN|' in out5
              and "an argument the restore format cannot carry" in log5, out5 + log5)
        sc = os.path.join(rfw, "apply.sh")
        check("the script parses (sh -n)", subprocess.run([SH, "-n", sc], capture_output=True).returncode == 0)
        if shutil.which("busybox"):
            check("the script parses (busybox ash -n)", subprocess.run(["busybox", "ash", "-n", sc], capture_output=True).returncode == 0)
    check("rules engine: the commit sits after the last chain is filled and before the set sweep and hook.sh",
          fw.index("RFWH iptables -t nat -A POSTROUTING -j") < fw.index('"if [ \\"$RFWB\\" != 0 ]; then\\n"') < fw.index('"RFW_KEEP=\\"%s\\"\\n"')
          < fw.index("fprintf(f, REAPER_HOOK_RUN);"))

    # ================= 2. object sets, 3. the resolver =================
    defs = []
    for m in re.finditer(r"^#define[ \t]+(RFW_[A-Z0-9_]+)[ \t]+(.*)$", fw, re.M):
        name, val = m.group(1), m.group(2).rstrip()
        if val.endswith("\\"): continue
        if name == "RFW_DIR": val = '"%s"' % rfw
        elif name == "RFW_CACHE": val = '"%s/jffs/reaper_fw"' % td
        defs.append("#define %s %s" % (name, val))
    mt = re.search(r"typedef struct \{[^}]*\} rfw_cfg_t;", fw)
    STUB = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <ctype.h>
#include <time.h>
#include <sys/stat.h>
#include <arpa/inet.h>
static size_t t_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
static size_t t_strlcat(char *d, const char *s, size_t n) { size_t l = strlen(d); if (l < n) t_strlcpy(d + l, s, n - l); return l + strlen(s); }
#define strlcpy t_strlcpy
#define strlcat t_strlcat
static void logmessage(const char *t, const char *fmt, ...) { (void)t; (void)fmt; }
static int reaper_script_ok(const char *p) { (void)p; return 0; }
static int t_eval(int x, ...) { return x; }
#define eval(...) t_eval(0, __VA_ARGS__)
'''
    parts = [STUB, "\n".join(defs), mt.group(0) if mt else ""]
    for sig in ("static int rfw_valid_name(", "static int rfw_valid_cidr(", "static int rfw_valid_cidr6(", "static int rfw_valid_ip(", "static int rfw_valid_range(",
                "static int rfw_valid_mac(", "static int rfw_valid_fqdn(", "static int rfw_field(", "static void rfw_emit_one_set(",
                "static void rfw_emit_sets(", "static void rfw_gen_resolve("):
        parts.append(extract(fw, sig))
    parts.append(r'''
int main(int argc, char **argv) { rfw_cfg_t c; static char keep[8192]; memset(&c, 0, sizeof(c)); c.obj = argv[2];
	if (!strcmp(argv[1], "sets")) { keep[0] = 0; rfw_emit_sets(stdout, &c, keep, sizeof(keep)); printf("echo \"KEEP=%s\" >> \"$OUT\"\n", keep); }
	else rfw_gen_resolve(&c);
	return 0; }
''')
    c2 = os.path.join(td, "s.c"); g2 = os.path.join(td, "s")
    with open(c2, "w") as fh: fh.write("\n".join(parts))
    r = subprocess.run([CC, "-std=gnu99", "-w", "-o", g2, c2], capture_output=True, text=True)
    check("object sets: rfw_emit_sets and rfw_gen_resolve compile on the host", r.returncode == 0 and mt is not None, r.stderr[:1500])
    if r.returncode == 0:
        OBJ = ("h1>host>192.0.2.1,2001:db8::1<n1>cidr>198.51.100.0/24<r1>range>192.0.2.10-192.0.2.20"
               "<m1>mac>AA:BB:CC:DD:EE:FF<d1>fqdn>example.com")
        frag = subprocess.run([g2, "sets", OBJ], capture_output=True, text=True).stdout
        types = dict(re.findall(r"^RFWS create (rwfw6?_\w+) (\S+)", frag, re.M))
        b = os.path.join(td, "bin2"); sets = os.path.join(td, "sets"); os.mkdir(sets)
        cache = os.path.join(td, "jffs", "reaper_fw", "sets"); os.makedirs(cache)
        IPS = ('echo "ipset $*" >> "$OUT"\ncase "$1" in\n'
               '  list) [ -f "$FAKE_SETS/$3" ] || exit 1; cat "$FAKE_SETS/$3"; exit 0;;\n'
               '  restore) bad=0; while IFS= read -r l; do echo "  < $l" >> "$OUT"; [ -n "$FAKE_BAD" ] && case "$l" in *" $FAKE_BAD") bad=1;; esac; done\n'
               '    [ -n "$FAKE_IPSET_RESTORE_FAIL" ] && exit 1; exit $bad;;\n'
               '  add) [ -n "$FAKE_BAD" ] && [ "$3" = "$FAKE_BAD" ] && exit 1;;\n'
               '  -t) echo "Number of entries: ${FAKE_N:-2}";;\n'
               '  save) echo "create $2 hash:net timeout 3600"; cat "$FAKE_SAVE";;\n'
               'esac\nexit 0\n')
        fakes(b, {"ipset": IPS, "logger": 'echo "logger $*" >> "$OUT"\n',
                  "nslookup": 'echo "Server:    127.0.0.1"; echo "Address 1: 127.0.0.1 localhost"; echo; echo "Name:      $1"; echo "Address 1: 203.0.113.7"\n'})
        def run2(script, **envx):
            sc = os.path.join(rfw, "sets.sh"); out = os.path.join(td, "o2"); open(out, "w").close()
            with open(sc, "w", newline="\n") as fh: fh.write("#!/bin/sh\n" + script)
            env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=out, FAKE_SETS=sets, **envx)
            p = subprocess.run([SH, sc], capture_output=True, text=True, env=env, cwd=td)
            return rd(out), p
        o, p = run2(frag)
        pay = [l[4:] for l in o.splitlines() if l.startswith("  < ")]
        check("sets, new box: the literal objects load through ONE `ipset restore -exist`; no `ipset add` process at all",
              o.count("ipset restore -exist") == 1 and "ipset add " not in o and p.returncode == 0, o + p.stderr)
        want = ["create rwfw_h1 " + types.get("rwfw_h1", "?"), "flush rwfw_h1",
                "create rwfw6_h1 " + types.get("rwfw_h1", "?") + " family inet6", "flush rwfw6_h1",
                "add rwfw_h1 192.0.2.1", "add rwfw6_h1 2001:db8::1",
                "create rwfw_n1 " + types.get("rwfw_n1", "?"), "flush rwfw_n1",
                "create rwfw6_n1 " + types.get("rwfw_n1", "?") + " family inet6", "flush rwfw6_n1", "add rwfw_n1 198.51.100.0/24",
                "create rwfw_r1 hash:ip", "flush rwfw_r1", "create rwfw6_r1 hash:ip family inet6", "flush rwfw6_r1",
                "add rwfw_r1 192.0.2.10-192.0.2.20",
                "create rwfw_m1 hash:mac", "flush rwfw_m1", "add rwfw_m1 AA:BB:CC:DD:EE:FF"]
        check("sets, new box: create, flush and members per object, each family in its own set, a MAC object in one set", pay == want,
              "\n".join(pay))
        check("sets: a domain list's sets are created with their expiry, never flushed, and kept by the sweep list",
              "ipset create rwfw_d1 " in o and " timeout 3600 -exist" in o and "flush rwfw_d1" not in o and "flush rwfw6_d1" not in o
              and re.search(r"KEEP=.* rwfw_d1 rwfw6_d1", o) is not None, o)
        check("sets: the queue file is removed", not [n for n in os.listdir(rfw) if n.startswith("sets.batch")], repr(os.listdir(rfw)))
        # the type test: an exact Type line stays, another type or a longer name of the same start goes
        def hdr(name, typ, extra=""):
            with open(os.path.join(sets, name), "w") as fh:
                fh.write("Name: %s\nType: %s\nRevision: 6\nHeader: family inet hashsize 1024 maxelem 65536%s\nSize in memory: 440\nReferences: 0\n" % (name, typ, extra))
        hdr("rwfw_r1", "hash:ip"); hdr("rwfw_n1", "hash:ip"); hdr("rwfw_h1", types.get("rwfw_h1", "hash:net") + ",port")
        o, p = run2(frag)
        check("sets: a set of the right type is kept; another type, or a type that only STARTS the same, is destroyed first",
              "ipset destroy rwfw_r1" not in o and "ipset destroy rwfw_n1" in o and "ipset destroy rwfw_h1" in o
              and "ipset destroy rwfw6_h1" not in o, o)
        for n in os.listdir(sets): os.unlink(os.path.join(sets, n))
        o, p = run2(frag, FAKE_IPSET_RESTORE_FAIL="1")
        adds = [l for l in o.splitlines() if l.startswith("ipset add ")]
        check("sets, restore refused: logged, then every create / flush / add runs one by one with -exist",
              "batched object load refused - loading entry by entry" in o and "ipset create rwfw_h1 %s -exist" % types.get("rwfw_h1", "?") in o
              and "ipset create rwfw6_n1 %s family inet6 -exist" % types.get("rwfw_n1", "?") in o and "ipset flush rwfw_m1" in o
              and adds == ["ipset add rwfw_h1 192.0.2.1 -exist", "ipset add rwfw6_h1 2001:db8::1 -exist", "ipset add rwfw_n1 198.51.100.0/24 -exist",
                           "ipset add rwfw_r1 192.0.2.10-192.0.2.20 -exist", "ipset add rwfw_m1 AA:BB:CC:DD:EE:FF -exist"], o)
        o, p = run2(frag, FAKE_BAD="2001:db8::1")
        check("sets, one entry the kernel rejects: the rest still load and the entry is named with its OBJECT's name",
              "logger -t reaper_fw object h1: entry rejected by ipset: 2001:db8::1" in o and "ipset add rwfw_n1 198.51.100.0/24 -exist" in o
              and "ipset add rwfw_m1 AA:BB:CC:DD:EE:FF -exist" in o and o.count("entry rejected by ipset") == 1, o)
        # the saved contents of a domain list: replayed only into an empty set
        with open(os.path.join(cache, "rwfw_d1"), "w") as fh: fh.write("add rwfw_d1 203.0.113.5\n")
        def replay(header):
            for n in os.listdir(sets): os.unlink(os.path.join(sets, n))
            if header is not None:
                with open(os.path.join(sets, "rwfw_d1"), "w") as fh: fh.write(header)
            o, p = run2(frag)
            return ("  < add rwfw_d1 203.0.113.5" in o, "ipset destroy rwfw_d1" in o)
        H = "Name: rwfw_d1\nType: hash:net\nRevision: 6\nHeader: family inet hashsize 1024 maxelem 65536%s\nSize in memory: 500\nReferences: 1\n%s"
        check("saved list: a set that holds addresses is left to its own timers - NO replay, not destroyed",
              replay(H % (" timeout 3600", "Number of entries: 5\n")) == (False, False))
        check("saved list: an EMPTY set gets its saved addresses back", replay(H % (" timeout 3600", "Number of entries: 0\n")) == (True, False))
        check("saved list: a set that does not exist yet (after a reboot) gets them back", replay(None) == (True, False))
        check("saved list: a header without a count (older ipset) reads as empty - replayed, as before", replay(H % (" timeout 3600", "")) == (True, False))
        check("saved list: a set built without an expiry is destroyed, made again and filled", replay(H % ("", "Number of entries: 5\n")) == (True, True))
        check("saved list: the replay line is guarded on the count (source)", "REAPER-FW-REPLAY-EMPTY" in fw
              and '[ \\"${_n:-0}\\" = 0 ] && [ -f " RFW_SETCACHE "/%s%s ] && grep \'^add \' " RFW_SETCACHE' in fw)
        for n in os.listdir(sets): os.unlink(os.path.join(sets, n))
        os.unlink(os.path.join(cache, "rwfw_d1"))

        # ---- 3. the resolver: an unchanged list writes nothing under /jffs ----
        subprocess.run([g2, "resolve", OBJ], capture_output=True, text=True)
        rs = rd(os.path.join(rfw, "resolve.sh"))
        check("resolver: the script is generated and tests /jffs for writing", "[ -w /jffs ]" in rs, rs[:300])
        rs = rs.replace("[ -w /jffs ]", '[ -w "%s/jffs" ]' % td)
        save = os.path.join(td, "save.txt")
        with open(save, "w") as fh: fh.write("add rwfw_d1 203.0.113.7 timeout 3500\n")
        def run3():
            sc = os.path.join(rfw, "resolve.sh"); out = os.path.join(td, "o3"); open(out, "w").close()
            with open(sc, "w", newline="\n") as fh: fh.write(rs)
            env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=out, FAKE_SETS=sets, FAKE_SAVE=save)
            p = subprocess.run([SH, sc], capture_output=True, text=True, env=env, cwd=td)
            return rd(out), p
        o, p = run3()
        cf = os.path.join(cache, "rwfw_d1")
        check("resolver: the answer goes into the set and the saved copy holds the members without their timers",
              "ipset add rwfw_d1 203.0.113.7 -exist" in o and "127.0.0.1" not in "".join(l for l in o.splitlines(True) if l.startswith("ipset add"))
              and rd(cf) == "add rwfw_d1 203.0.113.7\n", o + rd(cf))
        st_f = os.stat(cf); st_d = os.stat(cache); time.sleep(0.06)
        o, p = run3()
        st_f2 = os.stat(cf); st_d2 = os.stat(cache)
        check("resolver, nothing changed: the saved file is the same file, untouched",
              (st_f.st_ino, st_f.st_mtime_ns) == (st_f2.st_ino, st_f2.st_mtime_ns))
        check("resolver, nothing changed: NOTHING was created or removed in the /jffs folder (its own time stamp did not move)",
              st_d.st_mtime_ns == st_d2.st_mtime_ns and sorted(os.listdir(cache)) == ["rwfw6_d1", "rwfw_d1"], repr(os.listdir(cache)))
        with open(save, "w") as fh: fh.write("add rwfw_d1 203.0.113.7 timeout 3500\nadd rwfw_d1 203.0.113.8 timeout 3600\n")
        o, p = run3()
        check("resolver, the list changed: the saved copy is replaced, and no temp file is left on /jffs or in RAM",
              rd(cf) == "add rwfw_d1 203.0.113.7\nadd rwfw_d1 203.0.113.8\n" and sorted(os.listdir(cache)) == ["rwfw6_d1", "rwfw_d1"]
              and not [n for n in os.listdir(rfw) if n.startswith("setsave")], repr(os.listdir(cache)) + repr(os.listdir(rfw)))
        check("resolver: the comparison copy is built in RAM (source)", "REAPER-FW-SAVE-RAM" in fw
              and '> " RFW_SETCACHE "/$s.tmp\\n' not in fw and '> " RFW_DIR "/setsave.$$\\n' in fw)

    # ================= 4. guest isolation =================
    mg = re.search(r"/\* REAPER-GUEST-PURE-BEGIN.*?\*/(.*?)/\* REAPER-GUEST-PURE-END \*/", guest, re.S)
    check("guest isolation: reaper_guest.c carries the pure block", mg is not None)
    if mg:
        c3 = os.path.join(td, "g.c"); g3 = os.path.join(td, "g")
        with open(c3, "w") as fh:
            fh.write('#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <net/if.h>\n'
                     '#define REAPER_AIMESH_SET "reaper_aimesh"\n#define REAPER_HOOK_IN "REAPER_HOOK"\n#define REAPER_HOOK_FWD "REAPER_HOOK_F"\n'
                     + mg.group(1) + r'''
int main(int argc, char **argv) { struct rg_net g[2]; char wan4[2][IFNAMSIZ] = { "eth0", "ppp0" }; int s = atoi(argv[1]);
	memset(g, 0, sizeof(g));
	if (s == 2) { g[0].sdn_idx = 4; strcpy(g[0].ifname, "tun22"); strcpy(g[0].brname, "br55"); strcpy(g[0].subnet, "192.168.52.0/24"); g[0].portal = 1; }
	else { g[0].sdn_idx = 5; strcpy(g[0].ifname, "br56"); strcpy(g[0].brname, "br56"); strcpy(g[0].subnet, "192.168.53.0/24");
	       if (s == 3) { strcpy(g[0].vpnif, "wgc5"); g[0].killsw = 1; } }
	rg_write(stdout, g, 1, wan4, 1, "eth0", "HOOK_RUN\n"); return 0; }
''')
        r = subprocess.run([CC, "-Wall", "-Wno-unused-function", "-o", g3, c3], capture_output=True, text=True)
        check("guest isolation: the pure block compiles on the host", r.returncode == 0, r.stderr[:1200])
        if r.returncode == 0:
            b = os.path.join(td, "bin3"); state = os.path.join(td, "state"); os.mkdir(state)
            gdir = os.path.join(td, "rguest"); os.mkdir(gdir)
            XT = ('T=${0##*/}; echo "$T $*" >> "$OUT"\ntb=filter; [ "$1" = -t ] && { tb=$2; shift 2; }\n[ "$tb" = filter ] || exit 0\n'
                  'case "$1" in\n'
                  '  -S) [ -f "$STATE/$T.$2" ] || exit 1; echo "-N $2"; cat "$STATE/$T.$2";;\n'
                  '  -C) [ -f "$STATE/$T.hook.$4" ] || exit 1;;\n'
                  '  -N) [ -f "$STATE/$T.$2" ] && exit 1; : > "$STATE/$T.$2";;\n'
                  '  -F) [ -f "$STATE/$T.$2" ] || exit 1; : > "$STATE/$T.$2";;\n'
                  '  -A) c=$2; shift; echo "-A $*" >> "$STATE/$T.$c";;\n'
                  '  -D|-X) exit 1;;\nesac\nexit 0\n')
            RS = ('T=${0##*/}; T=${T%-restore}; echo "$T-restore $*" >> "$OUT"\n'
                  '[ -n "$FAKE_RESTORE_FAIL" ] && { cat > /dev/null; exit 1; }\n'
                  'while IFS= read -r l; do echo "  < $l" >> "$OUT"\n'
                  '  case "$l" in ":"*) c=${l#:}; c=${c%% *}; : > "$STATE/$T.$c";; "-A "*) c=${l#-A }; c=${c%% *}; echo "$l" >> "$STATE/$T.$c";; esac\n'
                  'done\nexit 0\n')
            fakes(b, {"iptables": XT, "ip6tables": XT, "iptables-restore": RS, "ip6tables-restore": RS,
                      "ipset": "exit 0\n", "logger": 'echo "logger $*" >> "$OUT"\n', "conntrack": 'echo "conntrack $*" >> "$OUT"\n',
                      "fc": 'echo "fc $*" >> "$OUT"\n',
                      "HOOK_RUN": 'echo HOOK_RUN >> "$OUT"\nfor T in iptables ip6tables; do : > "$STATE/$T.hook.REAPER_GUI"; : > "$STATE/$T.hook.REAPER_GUF"; done\n'})
            def gen(s):
                return subprocess.run([g3, str(s)], capture_output=True, text=True).stdout
            def run4(text, how="path", **envx):
                sc = os.path.join(gdir, "apply.sh"); out = os.path.join(td, "o4"); open(out, "w").close()
                with open(sc, "w", newline="\n") as fh: fh.write(text)
                env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=out, STATE=state, **envx)
                if how == "path": p = subprocess.run([SH, sc], capture_output=True, text=True, env=env, cwd=td)
                else: p = subprocess.run([SH, "apply.sh"], capture_output=True, text=True, env=env, cwd=gdir)
                return rd(out), p
            def wipe():
                for n in os.listdir(state): os.unlink(os.path.join(state, n))
            t1 = gen(1); t2 = gen(2); t3 = gen(3)
            f4 = [l[len("R iptables "):] for l in t1.splitlines() if l.startswith("R iptables -A ")]
            f6 = [l[len("R ip6tables "):] for l in t1.splitlines() if l.startswith("R ip6tables -A ")]
            def payload(o, tool):
                L = o.splitlines(); i = L.index(tool + "-restore --noflush"); pl = []
                for l in L[i + 1:]:
                    if not l.startswith("  < "): break
                    pl.append(l[4:])
                return pl
            o, p = run4(t1)
            check("guest, first load: each family's two chains arrive in ONE --noflush commit that names both chains",
                  o.count("iptables-restore --noflush") == 1 and o.count("ip6tables-restore --noflush") == 1
                  and payload(o, "iptables") == ["*filter", ":REAPER_GUI - [0:0]", ":REAPER_GUF - [0:0]"] + f4 + ["COMMIT"]
                  and payload(o, "ip6tables") == ["*filter", ":REAPER_GUI - [0:0]", ":REAPER_GUF - [0:0]"] + f6 + ["COMMIT"] and len(f4) > 8,
                  o[:1500])
            live = [l for l in o.splitlines() if l.startswith(("iptables ", "ip6tables "))]
            check("guest, first load: the chains are never emptied or filled by single calls (no -F, -N or -A on them)",
                  not [l for l in live if re.search(r" -(F|N|A) REAPER_GU[IF]\b", l)], "\n".join(live))
            check("guest, first load: the commit comes before hook.sh, and the flows are purged (rules are new)",
                  o.index("ip6tables-restore --noflush") < o.index("HOOK_RUN") < o.index("conntrack -D -s 192.168.53.0/24")
                  and "conntrack -D -d 192.168.53.0/24" in o and os.path.isfile(os.path.join(gdir, "apply.sh.sig")), o[-600:])
            o, p = run4(t1)
            check("guest, same rules and the chains untouched since: the chains are still replaced in one commit each",
                  o.count("-restore --noflush") == 2 and payload(o, "iptables")[3:-1] == f4, o[:400])
            check("guest, same rules and the chains untouched since: NO flow is purged (no conntrack -D, no fc flush)",
                  not [l for l in o.splitlines() if l.startswith(("conntrack ", "fc "))], o[-400:])
            wipe()
            o, p = run4(t1)
            check("guest, the filter table was replaced meanwhile (chains and jumps gone): the flows ARE purged",
                  "conntrack -D -s 192.168.53.0/24" in o, o[-400:])
            run4(t1)
            os.unlink(os.path.join(state, "iptables.hook.REAPER_GUF"))
            o, p = run4(t1)
            check("guest, one jump was missing: the flows ARE purged", "conntrack -D -s 192.168.53.0/24" in o, o[-400:])
            run4(t1)
            with open(os.path.join(state, "ip6tables.REAPER_GUF"), "a") as fh: fh.write("-A REAPER_GUF -i br56 -j RETURN\n")
            o, p = run4(t1)
            check("guest, a live chain differs from what the last load left: the flows ARE purged", "conntrack -D -s 192.168.53.0/24" in o, o[-400:])
            run4(t1)
            o, p = run4(t3)
            check("guest, the rules changed (kill switch on): the flows ARE purged", "conntrack -D -s 192.168.53.0/24" in o and t3 != t1, o[-400:])
            wipe(); run4(t1)
            o, p = run4(t1, FAKE_RESTORE_FAIL="1")
            L = o.splitlines()
            check("guest, commit refused: logged, the script runs itself again, empties the chains and loads rule by rule",
                  "logger -t reaper guest isolation: batched rule load refused - loading rule by rule" in o
                  and "iptables -F REAPER_GUI" in L and "ip6tables -F REAPER_GUF" in L
                  and [l[len("iptables "):] for l in L if l.startswith("iptables -A ")] == f4
                  and [l[len("ip6tables "):] for l in L if l.startswith("ip6tables -A ")] == f6, o[:900])
            check("guest, commit refused: the flows are purged and no signature is left to trust",
                  "conntrack -D -s 192.168.53.0/24" in o and not os.path.exists(os.path.join(gdir, "apply.sh.sig")), o[-300:])
            wipe()
            o, p = run4(t1, how="relative")
            check("guest, not started by its full path: rule by rule (there is no safe place for the queue)",
                  "-restore" not in o and "iptables -A REAPER_GUI -i br56 -j DROP" in o and "conntrack -D -s 192.168.53.0/24" in o
                  and not [n for n in os.listdir(gdir) if "batch" in n], o[:500])
            wipe()
            o, p = run4(t2)
            check("guest portal: the nat lines (DNS to the guest resolver) still run at once, in their own table",
                  "iptables -t nat -A REAPER_GUN -i tun22 -p udp --dport 53 -j REDIRECT --to-ports 53" in o
                  and "iptables -t nat -I PREROUTING 1 -j REAPER_GUN" in o and "REAPER_GUN" not in "".join(l for l in o.splitlines() if l.startswith("  < ")), o[:700])
            # reaper_guest_nat_reassert() runs the REAPER_GUN lines of the file alone: they must still be whole commands
            open(os.path.join(td, "o4"), "w").close()
            env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=os.path.join(td, "o4"), STATE=state)
            p = subprocess.run([SH, "-c", 'R() { "$@" 2>/dev/null; }; eval "$(grep REAPER_GUN %s | grep -v \'^#\')"' % os.path.join(gdir, "apply.sh")],
                               capture_output=True, text=True, env=env)
            o = rd(os.path.join(td, "o4"))
            check("guest portal: the nat-only re-run (after the nat table is replaced) runs exactly the nat lines, without an error",
                  p.returncode == 0 and p.stderr == "" and o.count("iptables -t nat ") == len(o.splitlines()) and len(o.splitlines()) >= 5, o + p.stderr)
            check("guest: the reassert in rc still reads the file that way", "grep REAPER_GUN \" RG_APPLY \" | grep -v '^#'" in guest)
            for nm, t in (("plain", t1), ("portal", t2), ("kill switch", t3)):
                sc = os.path.join(td, "syn.sh"); open(sc, "w").write(t)
                ok = subprocess.run([SH, "-n", sc], capture_output=True).returncode == 0
                if shutil.which("busybox"): ok = ok and subprocess.run(["busybox", "ash", "-n", sc], capture_output=True).returncode == 0
                check("guest (%s): the script parses" % nm, ok)

    # ================= 5. settings read; QoS =================
    c4 = os.path.join(td, "n.c"); g4 = os.path.join(td, "n")
    with open(c4, "w") as fh:
        fh.write('#include <stdio.h>\n#include "reaper_nv.h"\nint main(void) { printf(REAPER_NV_HELPER REAPER_NVS_HELPER '
                 'REAPER_NVC_HELPER_FMT("lan_ipaddr sshd_port odd_one")); return 0; }\n')
    r = subprocess.run([CC, "-Wall", "-Wno-format-security", "-o", g4, c4, "-I", os.path.join(SRC, "rc")], capture_output=True, text=True)
    check("settings: the printf form of the batch helper compiles", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        pre = subprocess.run([g4], capture_output=True, text=True).stdout
        b = os.path.join(td, "bin5")
        fakes(b, {"nvram": 'echo "nvram $*" >> "$OUT"\ncase "$1" in show) [ -n "$FAKE_SHOW_FAIL" ] && exit 1\n'
                           '  printf "%s\\n" "lan_ipaddr=192.168.50.1" "sshd_port=2222" "odd_one=\\$(touch $PWN) \\`touch $PWN\\`; x" "other=1";;\n'
                           '  get) case "$2" in live_one) echo live;; sshd_port) echo 2222;; lan_ipaddr) echo 192.168.50.1;; esac;; esac\nexit 0\n',
                  "usleep": "sleep 0.02\n", "logger": "exit 0\n"})
        def run5(**envx):
            out = os.path.join(td, "o5"); open(out, "w").close(); pwn = os.path.join(td, "pwned")
            if os.path.exists(pwn): os.unlink(pwn)
            env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=out, PWN=pwn, **envx)
            p = subprocess.run([SH, "-c", pre + 'echo "[$(_nvc lan_ipaddr)] [$(_nvc sshd_port)] [$(_nvc odd_one)] [$(_nvc live_one)]"'],
                               capture_output=True, text=True, env=env, cwd=td)
            return p.stdout.strip(), rd(out), os.path.exists(pwn)
        v, o, pw = run5()
        check("settings: the listed names come from ONE `nvram show`; a name outside the list is read live",
              v == "[192.168.50.1] [2222] [$(touch %s) `touch %s`; x] [live]" % ((os.path.join(td, "pwned"),) * 2)
              and o.count("nvram show") == 1 and o.count("nvram get") == 1 and "nvram get live_one" in o, v + "\n" + o)
        check("settings: a value full of shell syntax is carried as text and never run", not pw)
        v, o, pw = run5(FAKE_SHOW_FAIL="1")
        check("settings: when the batch read gives nothing, every name falls back to its own guarded read",
              v.startswith("[192.168.50.1] [2222] ") and "nvram get lan_ipaddr" in o and "nvram get sshd_port" in o, v + "\n" + o)
    hdr_i = fw.index("# generated by reaper_fw - do not edit; idempotent (teardown then rebuild)")
    check("rules engine: its ten settings go through the batch (no `_nv` read is left in reaper_fw.c)",
          "$(_nv " not in fw and fw.count("$(_nvc ") == 10
          and 'REAPER_NVC_HELPER_FMT("lan_ifname lan_ipaddr lan_netmask wan0_ifname wan_ifname https_lanport http_enable http_lanport sshd_enable sshd_port")' in fw
          and fw.index("REAPER_NVS_HELPER", hdr_i) < fw.index("REAPER_NVC_HELPER_FMT(", hdr_i) < fw.index('"LANIF=\\"$(_nvc lan_ifname)\\"\\n"'))

    # ---- C-D2: the confirm window and the deadline watcher have one copy (rc/reaper_cc.h) ----
    c6 = os.path.join(td, "cc.c"); g6 = os.path.join(td, "cc")
    with open(c6, "w") as fh:
        fh.write('#include <stdio.h>\n#include <stdlib.h>\nstatic int nvram_get_int(const char *k) { const char *v = getenv("NVCONF"); (void)k; return v ? atoi(v) : 0; }\n'
                 '#include "reaper_cc.h"\nint main(int argc, char **argv) { reaper_cc_gen(argv[1], "/tmp/x/armed", "/tmp/x/deadline", "/tmp/x/rollback.sh");\n'
                 'printf("%d\\n", reaper_cc_secs()); return 0; }\n')
    r = subprocess.run([CC, "-Wall", "-Werror", "-o", g6, c6, "-I", os.path.join(SRC, "rc")], capture_output=True, text=True)
    check("commit-confirm: rc/reaper_cc.h compiles on its own with -Wall -Werror", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        wf = os.path.join(td, "cc_check.sh")
        secs = {v: subprocess.run([g6, wf], capture_output=True, text=True, env=dict(os.environ, NVCONF=v)).stdout.strip()
                for v in ("", "0", "-5", "1", "14", "15", "60", "600", "3600", "9999")}
        check("commit-confirm: the window is 60 s by default, never under 15 s, never over 3600 s",
              secs == {"": "60", "0": "60", "-5": "60", "1": "15", "14": "15", "15": "15", "60": "60", "600": "600", "3600": "3600", "9999": "3600"}, secs)
        w = rd(wf)
        tail = ('[ -d /tmp/x/armed ] || exit 0\nD="$(cat /tmp/x/deadline 2>/dev/null)"\ncase "$D" in \'\'|*[!0-9]*) exit 0;; esac\n'
                'N="$(date +%s)"\n[ "$N" -lt "$D" ] && exit 0\nsh /tmp/x/rollback.sh\n')
        check("commit-confirm: the watcher script is the one both engines wrote before (not armed / no deadline / not due -> exit; else revert)",
              w.startswith("#!/bin/sh\n# _nv: nvram get with a 5 s ceiling") and w.endswith(tail) and (os.stat(wf).st_mode & 0o777) == 0o700, w[-400:])
        # run it: not armed, armed but not due, armed and due
        xb = os.path.join(td, "x"); os.makedirs(xb, exist_ok=True)
        ws = w.replace("/tmp/x/", xb + "/")
        with open(wf, "w", newline="\n") as fh: fh.write(ws)
        with open(os.path.join(xb, "rollback.sh"), "w") as fh: fh.write('echo reverted >> "%s/ran"\n' % xb)
        def due(armed, deadline):
            if os.path.exists(os.path.join(xb, "ran")): os.unlink(os.path.join(xb, "ran"))
            if armed: os.makedirs(os.path.join(xb, "armed"), exist_ok=True)
            elif os.path.isdir(os.path.join(xb, "armed")): os.rmdir(os.path.join(xb, "armed"))
            with open(os.path.join(xb, "deadline"), "w") as fh: fh.write(deadline)
            subprocess.run([SH, wf], capture_output=True, text=True)
            return os.path.exists(os.path.join(xb, "ran"))
        now = int(time.time())
        check("commit-confirm: the watcher reverts only when armed AND past a readable deadline",
              (due(False, str(now - 5)), due(True, str(now + 600)), due(True, "junk"), due(True, ""), due(True, str(now - 5)))
              == (False, False, False, False, True))
    check("commit-confirm: both engines call the shared copy and keep no copy of their own",
          all(s.count('"N=\\"$(date +%%s)\\"\\n"') == 0 for s in (fw, read("rc/reaper_pbr.c")))
          and "reaper_cc_gen(RFW_CC, RFW_ARMED, RFW_DEADLINE, RFW_ROLLBACK);" in fw and "return reaper_cc_secs();" in fw
          and "reaper_cc_gen(PPBR_CC, PPBR_ARMED, PPBR_DEADLINE, PPBR_ROLLBACK);" in read("rc/reaper_pbr.c")
          and "return reaper_cc_secs();" in read("rc/reaper_pbr.c"))

    a = qos[qos.index("int add_iQosRules(char *pcWANIF)"):qos.index("int start_iQos(void)")]
    check("QoS: after the class rules are back, the flow cache is flushed (classful hardware QoS only, behind the PBR reassert)",
          re.search(r"reaper_pbr_reassert\(\);\s*\n\s*#ifdef HND_ROUTER\s*\n(?:\s*/\*.*?\*/\s*\n)?\s*if \(IS_HWQOS_CLASSFUL\(\)\)\s*\n\s*eval\(\"fc\", \"flush\"\);\s*\n#endif\s*\n\s*return status;",
                    a, re.S) is not None, a[-900:])
    h = qos[qos.index("int start_hwqos_classful(void)"):]
    h = h[:h.index("\n}\n")]
    check("QoS: and once more after the class queues are rebuilt",
          h.index('eval((char *)qosfn, "start")') < h.rindex('eval("fc", "flush");') < h.rindex("return 0;"), h[-500:])
    check("QoS: the first packet of a connection gets its class - a packet-mark restore after the QOSO jump, both families",
          '"-A POSTROUTING -o %s -j QOSO\\n"\n\t\t\t"-A POSTROUTING -o %s -j CONNMARK --restore-mark --mask 0x%x\\n",\n\t\t\t\taction, class_num|class_gum, class_mask|class_gum,\n\t\t\t\tpcWANIF,\n\t\t\t\tpcWANIF, class_mask' in qos
          and "\t\t\t\twan6face,\n\t\t\t\twan6face, class_mask" in qos)
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
