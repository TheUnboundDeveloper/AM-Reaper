#!/usr/bin/env python3
"""Wallguard's never-blocked names are seeded entries of the operator's allow list - compiled on the host.

WHY (owner, 2026-10-22). The names Wallguard never blocks were a fixed list in rc/wallguard.c that the operator
could not take out. A hard-coded exemption outlives a service that is later compromised, or a lapsed domain
someone else buys. They are now added ONCE to the allow list on the Wallguard page (/jffs/wallguard/allow), with a
marker so a removed entry stays removed; the never-block set rc writes (safe) keeps only the names that come
from the operator's own settings and custom lists.

WHAT IT DOES. Lifts the preset catalog, sh_name_ok / sh_url_host / sh_add and the seed section out of
rc/wallguard.c, compiles them with file-backed stubs (-Wall -Wextra -Werror) and runs sh_seed_allow() against
prepared states. Static checks: sh_write_safe no longer carries a fixed list and calls the seed first.
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
SC = os.path.join(SRC, "rc", "wallguard.c")
CC = shutil.which("gcc") or shutil.which("cc")
if not os.path.exists(SC) or not CC:
    print("SKIP: rc/wallguard.c or a C compiler not found"); sys.exit(0)
sc = open(SC, encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def cut(start, end_marker="\n}\n"):
    a = sc.find(start)
    if a < 0:
        print("FAIL not found: " + start); sys.exit(1)
    b = sc.find(end_marker, a)
    return sc[a:b + len(end_marker)]

FIXED = ["asus.com", "asusrouter.com", "asuscomm.com", "abuse.ch", "spamhaus.org", "www.ipdeny.com", "iplists.firehol.org",
         "forcesafesearch.google.com", "strict.bing.com", "safe.duckduckgo.com", "restrict.youtube.com", "restrictmoderate.youtube.com",
         "github.com", "raw.githubusercontent.com", "objects.githubusercontent.com", "pool.ntp.org", "time.google.com", "time.cloudflare.com"]
PRESET_HOSTS = ["small.oisd.nl", "big.oisd.nl", "adguardteam.github.io"]   # the presets' hosts not already in FIXED
ALL = FIXED + PRESET_HOSTS

# ---- static
safe = cut("static void sh_write_safe(void)")
check("sh_write_safe carries no fixed name list any more and seeds the allow list first",
      "fixed[]" not in safe and safe.find("sh_seed_allow();") < safe.find("sh_add(") and not any('"%s"' % n in safe for n in FIXED))
check("the seed has its own marker in /jffs/wallguard", '#define SH_SEED_MARK SH_JFFS "/.seed_allow"' in sc)

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdarg.h>
#include <unistd.h>
#define SH_JFFS "sj"
static int f_exists(const char *p) { return access(p, F_OK) == 0; }
static char rbuf[65536];
static char *rjf_get(const char *p, int *ex)
{
	FILE *f = fopen(p, "r"); size_t n;
	if (!f) { *ex = 0; rbuf[0] = 0; return rbuf; }
	n = fread(rbuf, 1, sizeof(rbuf) - 1, f); rbuf[n] = 0; fclose(f); *ex = 1; return rbuf;
}
static int rjf_set(const char *p, const char *v, const char *tag)
{
	FILE *f; (void)tag;
	if (getenv("FAIL_SET") && strcmp(p, SH_JFFS "/.seed_allow")) return -1;
	if (!(f = fopen(p, "w"))) return -1;
	fputs(v, f); return fclose(f);
}
static void logmessage(const char *tag, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
static void logmessage(const char *tag, const char *fmt, ...)
{
	va_list ap; va_start(ap, fmt); printf("LOG %s: ", tag); vprintf(fmt, ap); printf("\n"); va_end(ap);
}
''' + cut("static const struct { int bit; const char *id, *url; } presets[] = {", "};\n") \
    + "#define NPRESETS (int)(sizeof(presets) / sizeof(presets[0]))\n" \
    + cut("static int sh_name_ok(const char *s)") + cut("static void sh_url_host(const char *u, char *h, size_t n)") \
    + cut("static void sh_add(char **b, size_t *len, size_t *cap, const char *fmt, ...)") \
    + sc[sc.find("#define SH_SEED_MARK"):sc.find("\n}\n", sc.find("static void sh_seed_allow(void)")) + 3] + r'''
int main(void) { sh_seed_allow(); return 0; }
'''

with tempfile.TemporaryDirectory() as td:
    c = os.path.join(td, "seed.c"); exe = os.path.join(td, "seed")
    open(c, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("the seed compiles cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n".join(fails)); sys.exit(1)

    def run(allow=None, mark=False, fail_set=False):
        d = tempfile.mkdtemp(dir=td); j = os.path.join(d, "sj"); os.mkdir(j)
        if allow is not None: open(os.path.join(j, "allow"), "w").write(allow)
        if mark: open(os.path.join(j, ".seed_allow"), "w").write("1")
        env = dict(os.environ)
        if fail_set: env["FAIL_SET"] = "1"
        p = subprocess.run([exe], cwd=d, capture_output=True, text=True, env=env)
        al = os.path.join(j, "allow")
        return {"allow": open(al).read() if os.path.exists(al) else None, "mark": os.path.exists(os.path.join(j, ".seed_allow")),
                "log": [l for l in p.stdout.splitlines() if l.startswith("LOG ")], "rc": p.returncode, "dir": d}

    x = run()
    check("no allow list yet: every fixed name and preset host added once, one per line, logged, marker set",
          x["allow"] == "".join(n + "\n" for n in ALL) and x["mark"] and len(x["log"]) == 1 and "Wallguard page" in x["log"][0], x)
    x = run(allow="mine.example\nasus.com")
    check("the operator's entries stay first; a name already there is not added again; a missing final newline is fixed",
          x["allow"] == "mine.example\nasus.com\n" + "".join(n + "\n" for n in ALL if n != "asus.com"), x["allow"])
    x = run(allow="mine.example\n", mark=True)
    check("marker present: removed entries stay removed, nothing logged", x["allow"] == "mine.example\n" and not x["log"], x)
    x = run(allow="".join(n + "\n" for n in ALL))
    check("all present: list untouched, marker set, no log line", x["allow"] == "".join(n + "\n" for n in ALL) and x["mark"] and not x["log"], x)
    x = run(allow="sub.asus.com\n")
    check("a longer name sharing the text is not a match (whole-line comparison)", "\nasus.com\n" in x["allow"], x["allow"])
    x = run(allow="mine.example\n", fail_set=True)
    check("a failed write leaves the marker unset (the next start retries)", x["allow"] == "mine.example\n" and not x["mark"] and not x["log"], x)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
