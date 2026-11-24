#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Policy Routing selects on fetched lists: ASN and country objects (REAPER-FW-LISTS, 2026-11-22).

WHY. Policy Routing dropped any rule that named a country object ("Warden owns the country sets") and knew no ASN
object at all. Both are now fetched lists: the object layer builds rwfw_<name> for one while a Policy Routing rule
names it, and asks rc/reaper_pbr.c reaper_pbr_uses_object() whether one does. A wrong answer there is silent either
way - "no" leaves a rule matching an empty set, "yes" for an unused list downloads and loads a list nobody asked for.

This test compiles the real ppbr_resolve_object() and reaper_pbr_uses_object() and checks:
  1. an ASN object and a country object resolve to their own name; a MAC object and an unknown one still drop the
     rule with a reason; a group expands to its usable members, ASN and country included;
  2. uses_object: an enabled rule that selects on the object, directly or through a group, in the staged list or
     in the confirmed one; never a disabled rule, never a source / MAC selector that happens to carry the name.
Exit 0 pass, 1 fail, 77 skipped (no compiler or no router source: pass release/src/router or set REAPER_ROUTER_SRC).
"""
import os, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_pbr.c")):
    print("SKIP: no router source tree"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no host C compiler"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def extract(src, signature):
    i = src.index(signature); j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    raise ValueError("unbalanced braces after " + signature)

pbr = open(os.path.join(SRC, "rc", "reaper_pbr.c"), encoding="utf-8", errors="surrogateescape").read()
if "reaper_pbr_uses_object" not in pbr:
    print("SKIP: this tree has no fetched lists"); sys.exit(77)

STUB = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
static void logmessage(const char *t, const char *fmt, ...) { va_list ap; fprintf(stderr, "LOG %s: ", t); va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap); fputc('\n', stderr); }
static char *envs(const char *k) { char *v = getenv(k); return v ? v : ""; }
static char *reaper_fw_list_get(const char *key) { return envs(!strcmp(key, "obj") ? "T_OBJ" : "T_GRP"); }
static char *reaper_pbr_rl_get(void) { return envs("T_DRAFT"); }
#define REAPER_PBR_RL "confirmed"
static char *rjf_get(const char *path, int *exists) { char *v = getenv("T_GOOD"); (void)path; *exists = v ? 1 : 0; return v ? v : ""; }
static int t_vstrsep(char *buf, const char *sep, ...) { va_list ap; char **p; int n = 0; va_start(ap, sep);
	while ((p = va_arg(ap, char **)) != NULL) { *p = buf ? strsep(&buf, sep) : NULL; if (*p) n++; } va_end(ap); return n; }
#define vstrsep(buf, sep, ...) t_vstrsep(buf, sep, __VA_ARGS__, NULL)
'''
MAIN = r'''
int main(int argc, char **argv) { char out[1024]; int n;
	if (!strcmp(argv[1], "uses")) { printf("%d\n", reaper_pbr_uses_object(argv[2])); return 0; }
	n = ppbr_resolve_object(argv[2], out, sizeof(out)); printf("%d|%s\n", n, out); return 0; }
'''
td = tempfile.mkdtemp(prefix="pbrfetch-")
try:
    parts = [STUB]
    for sig in ("static int ppbr_obj_routable(", "static int ppbr_obj_type(", "static int ppbr_resolve_object(",
                "static int ppbr_list_names(", "int reaper_pbr_uses_object("):
        parts.append(extract(pbr, sig))
    parts.append(MAIN)
    c = os.path.join(td, "p.c"); x = os.path.join(td, "p")
    with open(c, "w") as fh: fh.write("\n".join(parts))
    r = subprocess.run([CC, "-std=gnu99", "-w", "-o", x, c], capture_output=True, text=True)
    check("the real functions compile on the host", r.returncode == 0, r.stderr[:1500])
    if r.returncode != 0:
        raise SystemExit
    OBJ = "h1>host>192.0.2.1<n1>cidr>198.51.100.0/24<d1>fqdn>example.com<a1>asn>AS2906<g1>geo>NL<m1>mac>AA:BB:CC:DD:EE:FF<a2>asn>13335"
    GRP = "mix>a1,g1,m1,n1,gone>c<onlymac>m1>c<two>a2>c"
    def run(mode, name, draft="", good=None):
        env = dict(os.environ, T_OBJ=OBJ, T_GRP=GRP, T_DRAFT=draft)
        if good is not None: env["T_GOOD"] = good
        else: env.pop("T_GOOD", None)
        p = subprocess.run([x, mode, name], capture_output=True, text=True, env=env)
        return p.stdout.strip(), p.stderr

    # ---- 1. resolve ----
    check("an ASN object resolves to its own name (one mark rule on rwfw_<name>)", run("res", "a1")[0] == "1|a1")
    check("a country object resolves to its own name - no longer dropped", run("res", "g1")[0] == "1|g1")
    check("host, cidr and domain objects as before", [run("res", n)[0] for n in ("h1", "n1", "d1")] == ["1|h1", "1|n1", "1|d1"])
    o, e = run("res", "m1")
    check("a MAC object still drops the rule, with the reason", o == "-1|object m1 is a mac object, which has no destination set to select on", o)
    o, e = run("res", "mix")
    check("a group expands to its usable members, ASN and country included; the MAC and the missing member are skipped and named",
          o == "3|a1,g1,n1" and "member m1 skipped (not an address, domain, ASN or country object)" in e and "member gone skipped" in e, o + e)
    check("a group with nothing usable drops the rule", run("res", "onlymac")[0] == "-1|group onlymac has no member Policy Routing can select on")
    check("an unknown name drops the rule", run("res", "nope")[0] == "-1|object nope does not exist")
    check("the old refusal text is gone from the source", "Warden owns the country sets and Policy Routing cannot select on them" not in pbr)

    # ---- 2. uses_object ----
    R = lambda en, st, sv, tg="WGC1": "%s>d>%s>%s>>>%s" % (en, st, sv, tg)
    check("an enabled rule selecting on the object: used", run("uses", "a1", draft=R(1, "ipset", "a1"))[0] == "1")
    check("the page's domain selector form counts the same", run("uses", "d1", draft=R(1, "domain", "d1"))[0] == "1")
    check("a disabled rule does not count", run("uses", "a1", draft=R(0, "ipset", "a1"))[0] == "0")
    check("a source or MAC selector that carries the same text does not count",
          run("uses", "a1", draft=R(1, "src", "a1") + "<" + R(1, "mac", "a1"))[0] == "0")
    check("another object's rule does not count", run("uses", "a1", draft=R(1, "ipset", "a2"))[0] == "0")
    check("through a group that holds it: used", run("uses", "g1", draft=R(1, "ipset", "mix"))[0] == "1")
    check("a group that does not hold it: not used", run("uses", "a1", draft=R(1, "ipset", "two"))[0] == "0")
    check("named only in the confirmed list (the staged one differs): still used",
          run("uses", "a1", draft=R(1, "ipset", "n1"), good=R(1, "ipset", "h1") + "<" + R(1, "ipset", "a1"))[0] == "1")
    check("named in neither list: not used", run("uses", "a1", draft=R(1, "ipset", "n1"), good=R(1, "ipset", "h1"))[0] == "0")
    check("no confirmed list on the box yet: the staged one decides", run("uses", "a1", draft="")[0] == "0" and run("uses", "a1", draft=R(1, "ipset", "a1"))[0] == "1")
    check("a broken record (wrong field count) is skipped, the next one still counts",
          run("uses", "a1", draft="1>d>ipset>a1<" + R(1, "ipset", "a1"))[0] == "1" and run("uses", "a1", draft="1>d>ipset>a1")[0] == "0")
    check("an empty name is never used", run("uses", "", draft=R(1, "ipset", ""))[0] == "0")
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
