#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The hosts Policy Routing's fetched lists come from, in the operator's "do not block" lists (2026-11-22).

WHY. Warden can block the router's own downloads: with the router-traffic filter on, a blocked country or a feed
that covers a list host stops the fetch (RIPEstat is hosted in the Netherlands), and a threat list that carried a
source's name would stop its lookup. Owner 2026-11-22: put the sources into the "do not block" lists by default
and let the user decide to keep them. That is a seed like the others in rc/rwarden.c - an owner-directed exception
to "an update never rewrites a user setting" - so it must only ADD, add each entry once, show on the page, never
come back after the user deletes it, never be lost to a failed write, and here also: fire only when an ASN or a
country list is actually in use, so a router that never uses one gets nothing added.

WHAT IT DOES. Lifts the seed helpers and rwarden_listsrc_seed() out of rc/rwarden.c, compiles them with
file-backed stubs and runs the seed against prepared states; and checks the source of rc/reaper_fw.c for where
it is called. Exit 0 pass, 1 fail, 77 skipped (no gcc, no router source tree, or a tree without the seed).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RW = os.path.join(SRC, "rc", "rwarden.c")
if not SRC or not os.path.isfile(RW):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")
rw = open(RW, encoding="utf-8", errors="surrogateescape").read()
if "void rwarden_listsrc_seed(void)" not in rw:
    skip("this tree has no list-source seed")
fw = open(os.path.join(SRC, "rc", "reaper_fw.c"), encoding="utf-8", errors="surrogateescape").read()
rch = open(os.path.join(SRC, "rc", "rc.h"), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

IPS = ["185.199.108.133", "185.199.109.133", "185.199.110.133", "185.199.111.133",
       "2606:50c0:8000::154", "2606:50c0:8001::154", "2606:50c0:8002::154", "2606:50c0:8003::154",
       "193.0.6.150", "2001:67c:2e8:22::c100:696", "45.33.65.164"]
NAMES = ["ripe.net", "hackertarget.com"]

a = rw.find("static int rw_seed_has(const char *list, const char *ip)")
b = rw.find("static void rw_seed_live(const char *ips)")
b = rw.find("\n}\n", b) + 3
helpers = rw[a:b]                                     # rw_seed_has, rw_seed_one, rw_seed_live
i = rw.find("/* REAPER-FW-LISTS-SEED BEGIN"); j = rw.find("/* REAPER-FW-LISTS-SEED END */")
block = rw[i:j]
if a < 0 or i < 0 or j < 0:
    print("FAIL seed code not found in rwarden.c"); sys.exit(1)

# ---- static
m = re.search(r'#define RW_LISTSRC_IPS\s+((?:"[^"]*"\s*\\?\s*)+)', block)
got = " ".join(re.findall(r'"([^"]*)"', m.group(1))).split() if m else []
check("the addresses are exactly the eleven resolved for the three hosts (GitHub raw v4 + v6, RIPEstat v4 + v6, HackerTarget)", got == IPS, got)
check("the names are the two not already in the Dreadwatch seed", '#define RW_LISTSRC_NAMES "%s"' % " ".join(NAMES) in block
      and "githubusercontent.com" in rw[rw.find("#define RW_DNSALLOW_SEED"):rw.find("#define RW_SEED_MARK_DNSALLOW")]
      and "ipdeny.com" in rw[rw.find("#define RW_DNSALLOW_SEED"):rw.find("#define RW_SEED_MARK_DNSALLOW")])
check("each list has its own marker, apart from every other seed's",
      '#define RW_SEED_MARK_LISTSRC REAPER_RW_DIR "/.seed_listsrc"' in block and '#define RW_SEED_MARK_LISTSRC_DNS REAPER_RW_DIR "/.seed_listsrc_dns"' in block)
check("it is NOT part of the every-start seeds (rw_seed_allow): only a list in use fires it",
      "rwarden_listsrc_seed" not in rw[rw.find("static void rw_seed_allow(void)"):rw.find("\n}\n", rw.find("static void rw_seed_allow(void)"))]
      and rw.find("static void rw_seed_allow(void)") < i)
gl = fw[fw.find("static void rfw_gen_lists("):]
gl = gl[:gl.find("/* REAPER-FW-LISTS F-END */")]
check("the object layer calls it only when a fetched list is in use, before the first download is tried",
      gl.count("rwarden_listsrc_seed();") == 1
      and gl.find("\tif (any) {") < gl.find("rwarden_listsrc_seed();") < gl.find('system("sh " RFW_LISTS " fill') < gl.find('" missing >/dev/null') < gl.rfind("\n\t} else {\n"), gl[-900:])
check("the prototype is in rc.h", "extern void rwarden_listsrc_seed(void);" in rch)

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdarg.h>
#define REAPER_RW_DIR "rw"
#define REAPER_TMPDIR "tmp"
static int nvram_match(const char *k, const char *v) { char e[64]; const char *g; snprintf(e, sizeof(e), "NV_%s", k); g = getenv(e); return g && !strcmp(g, v); }
static int stub_eval(const char **a) { int i; printf("EVAL"); for (i = 0; a[i]; i++) printf(" %s", a[i]); printf("\n"); return 0; }
#define eval(...) stub_eval((const char *[]){ __VA_ARGS__, NULL })
static int f_exists(const char *p) { return access(p, F_OK) == 0; }
static char *slurp(const char *p)
{
	FILE *f = fopen(p, "r"); char *b; long n;
	if (!f) return NULL;
	fseek(f, 0, SEEK_END); n = ftell(f); rewind(f);
	b = calloc(1, n + 1); if (fread(b, 1, n, f) != (size_t)n) n = 0; b[n] = 0; fclose(f); return b;
}
static int put(const char *p, const char *v) { FILE *f = fopen(p, "w"); if (!f) return -1; fputs(v, f); return fclose(f); }
static char *rw_list_get(const char *name) { char p[64], *v; snprintf(p, sizeof(p), REAPER_RW_DIR "/%s", name); v = slurp(p); return v ? v : strdup(""); }
static int rw_list_set(const char *name, const char *v)
{
	char p[64]; const char *f = getenv("FAIL_SET");
	if (f && (!strcmp(f, "all") || !strcmp(f, name))) return -1;
	snprintf(p, sizeof(p), REAPER_RW_DIR "/%s", name);
	return put(p, v);
}
static int rjf_set(const char *p, const char *v, const char *tag) { (void)tag; return put(p, v); }
static void logmessage(const char *tag, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
static void logmessage(const char *tag, const char *fmt, ...) { va_list ap; va_start(ap, fmt); printf("LOG %s: ", tag); vprintf(fmt, ap); printf("\n"); va_end(ap); }
''' + helpers + "\n" + block + r'''
int main(void) { rwarden_listsrc_seed(); return 0; }
'''

with tempfile.TemporaryDirectory() as td:
    c = os.path.join(td, "seed.c"); exe = os.path.join(td, "seed")
    open(c, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("the seed compiles cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n".join(fails)); sys.exit(1)

    def run(allow="", dnsallow="", committed=True, marks=(), fail=None, warden=False, again=None):
        d = again or tempfile.mkdtemp(dir=td); rwd = os.path.join(d, "rw")
        if not again:
            os.mkdir(rwd)
            if committed: open(os.path.join(rwd, ".committed"), "w").write("1")
            for mk in marks: open(os.path.join(rwd, mk), "w").write("1")
            open(os.path.join(rwd, "allow"), "w").write(allow); open(os.path.join(rwd, "dnsallow"), "w").write(dnsallow)
        env = dict(os.environ); env.pop("FAIL_SET", None)
        if fail: env["FAIL_SET"] = fail
        if warden: env["NV_rwarden_enable"] = "1"
        p = subprocess.run([exe], cwd=d, capture_output=True, text=True, env=env)
        rd = lambda n: open(os.path.join(rwd, n)).read() if os.path.exists(os.path.join(rwd, n)) else None
        return {"allow": rd("allow"), "dns": rd("dnsallow"), "m": os.path.exists(os.path.join(rwd, ".seed_listsrc")),
                "md": os.path.exists(os.path.join(rwd, ".seed_listsrc_dns")),
                "eval": [l for l in p.stdout.splitlines() if l.startswith("EVAL ")],
                "log": [l for l in p.stdout.splitlines() if l.startswith("LOG ")], "dir": d}

    x = run(committed=False)
    check("before the list migration has committed: nothing written, no marker", x["allow"] == "" and x["dns"] == "" and not x["m"] and not x["md"] and not x["log"], x)
    x = run()
    check("first use, empty lists: the eleven addresses go into the whitelist, the two names into the never-block names",
          x["allow"] == " ".join(IPS) and x["dns"] == " ".join(NAMES), x)
    check("first use: both markers written, one log line per list saying what was added and where to remove it",
          x["m"] and x["md"] and len(x["log"]) == 2 and "whitelist: added" in x["log"][0] and "remove it on the Warden page" in x["log"][0]
          and "193.0.6.150" in x["log"][0] and "never-block list: added" in x["log"][1] and "remove it on the Dreadwatch page" in x["log"][1]
          and "ripe.net hackertarget.com" in x["log"][1], x["log"])
    check("Warden off: the running sets are not touched", not x["eval"], x["eval"])
    y = run(again=x["dir"])
    check("second run: nothing changes, nothing is logged", y["allow"] == x["allow"] and y["dns"] == x["dns"] and not y["log"] and not y["eval"], y)
    x = run(warden=True)
    check("Warden on: each address also goes straight into the running whitelist set of its family",
          x["eval"] == ["EVAL ipset add %s %s -exist" % ("rw_allow6" if ":" in ip else "rw_allow", ip) for ip in IPS], x["eval"])
    x = run(allow="10.1.2.3 193.0.6.150/32 mine", dnsallow="corp.example hackertarget.com")
    check("the operator's own entries are kept in place and in order; an entry already there is not added twice",
          x["allow"] == "10.1.2.3 193.0.6.150/32 mine " + " ".join(ip for ip in IPS if ip != "193.0.6.150")
          and x["dns"] == "corp.example hackertarget.com ripe.net", x)
    x = run(allow="10.1.2.3", dnsallow="corp.example", marks=(".seed_listsrc", ".seed_listsrc_dns"))
    check("an entry the operator removed after the seed stays removed (markers present: the lists are never touched)",
          x["allow"] == "10.1.2.3" and x["dns"] == "corp.example" and not x["log"] and not x["eval"], x)
    x = run(allow="10.1.2.3", marks=(".seed_listsrc",))
    check("the two seeds are independent: one taken, the other still fires once", x["allow"] == "10.1.2.3" and x["dns"] == " ".join(NAMES) and x["md"], x)
    x = run(allow="10.1.2.3", fail="allow", warden=True)
    check("a failed whitelist write: no marker, no entry in the running sets, the names still seeded",
          x["allow"] == "10.1.2.3" and not x["m"] and not x["eval"] and x["dns"] == " ".join(NAMES) and x["md"], x)
    y = run(again=x["dir"], warden=True)
    check("... and the next run retries the whitelist and adds it", y["allow"] == "10.1.2.3 " + " ".join(IPS) and y["m"] and len(y["eval"]) == len(IPS), y)
    x = run(allow=" ".join(IPS), dnsallow=" ".join(NAMES))
    check("everything already present: lists untouched, markers set, no log line",
          x["allow"] == " ".join(IPS) and x["dns"] == " ".join(NAMES) and x["m"] and x["md"] and not x["log"], x)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
