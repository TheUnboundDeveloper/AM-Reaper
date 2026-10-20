#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Warden whitelist seeds: the list hosts the router must always reach - compiled on the host.

WHY THIS EXISTS. Warden can block the router's own list downloads. 2026-10-19: www.ipdeny.com sits in
France, so FR + the router-traffic filter dropped every country-list fetch; its address was seeded ONCE
into the user's whitelist. 2026-10-20 (owner): the abuse.ch feed hosts (urlhaus / threatfox for
Dreadwatch, feodotracker for the feodo IP feed) are Fastly anycast addresses inside the USA country
list, so the same seed now covers their four addresses. A seed is an owner-directed exception to "an
update never rewrites a user setting", so it must only ADD, add each address once, never come back
after the user deletes it, and never be lost to a failed write.

WHAT IT DOES. Lifts rw_seed_has .. rw_seed_allow and the seed #defines out of rc/rwarden.c, compiles
them with file-backed stubs (rw_list_get/rw_list_set/rjf_set on a temp dir, logmessage prints), runs
rw_seed_allow() against prepared states and asserts:
  - nothing happens before the nvram -> /jffs list migration has committed;
  - an empty whitelist gets the ipdeny host and the four abuse.ch addresses, both markers, two log lines;
  - a box that already took the ipdeny seed (older firmware) gets only the abuse.ch addresses;
  - with both markers present the list is never touched, even if the user deleted the entries;
  - an address already present (bare or /32) is not added twice; a longer address sharing the prefix
    (151.101.2.490) does not count as present;
  - the user's list is kept verbatim and in order, the new entries appended with one space;
  - a failed list write leaves the marker unset, so the next start retries;
and statically: the four addresses, the separate marker, and the call order in start_rwarden.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree).
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
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

ABUSE = ["151.101.2.49", "151.101.66.49", "151.101.130.49", "151.101.194.49"]
GEO = "51.15.12.186"

a = rw.find("static int rw_seed_has(const char *list, const char *ip)")
b = rw.find("static void rw_seed_allow(void)")
if a < 0 or b < 0:
    print("FAIL seed helpers not found in rwarden.c"); sys.exit(1)
b = rw.find("\n}\n", b) + 3
helpers = rw[a:b]
defs = re.findall(r"^#define (?:RW_GEO_HOST_IP|RW_SEED_MARK|RW_ABUSECH_IPS|RW_SEED_MARK_ABUSECH)\b.*$", rw, re.M)

# ---- static
check("the four Fastly addresses for the abuse.ch hosts are the seed",
      '#define RW_ABUSECH_IPS  "%s"' % " ".join(ABUSE) in rw)
check("the abuse.ch seed has its own marker (boxes that took the ipdeny seed still get it)",
      '#define RW_SEED_MARK_ABUSECH REAPER_RW_DIR "/.seed_abusech"' in rw and len(defs) == 4, defs)
st = rw[rw.find("void start_rwarden(void)"):]
st = st[:st.find("\n}\n")]
check("start_rwarden seeds right after the list migration, before the apply reads the list",
      0 <= st.find("rw_list_migrate();") < st.find("rw_seed_allow();") < st.find("rw_gen_") if "rw_gen_" in st else
      0 <= st.find("rw_list_migrate();") < st.find("rw_seed_allow();"))

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#define REAPER_RW_DIR "rw"
static int f_exists(const char *p) { return access(p, F_OK) == 0; }
static char *slurp(const char *p)
{
	FILE *f = fopen(p, "r"); char *b; long n;
	if (!f) return NULL;
	fseek(f, 0, SEEK_END); n = ftell(f); rewind(f);
	b = calloc(1, n + 1); if (fread(b, 1, n, f) != (size_t)n) n = 0; b[n] = 0; fclose(f); return b;
}
static int put(const char *p, const char *v)
{
	FILE *f = fopen(p, "w");
	if (!f) return -1;
	fputs(v, f); return fclose(f);
}
static char *rw_list_get(const char *name)
{
	char p[64], *v;
	snprintf(p, sizeof(p), REAPER_RW_DIR "/%s", name);
	v = slurp(p);
	return v ? v : strdup("");
}
static int rw_list_set(const char *name, const char *v)
{
	char p[64];
	if (getenv("FAIL_SET")) return -1;
	snprintf(p, sizeof(p), REAPER_RW_DIR "/%s", name);
	return put(p, v);
}
static int rjf_set(const char *p, const char *v, const char *tag) { (void)tag; return put(p, v); }
static void logmessage(const char *tag, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
#include <stdarg.h>
static void logmessage(const char *tag, const char *fmt, ...)
{
	va_list ap; va_start(ap, fmt); printf("LOG %s: ", tag); vprintf(fmt, ap); printf("\n"); va_end(ap);
}
''' + "\n".join(defs) + "\n" + helpers + r'''
int main(void) { rw_seed_allow(); return 0; }
'''

with tempfile.TemporaryDirectory() as td:
    c = os.path.join(td, "seed.c"); exe = os.path.join(td, "seed")
    open(c, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("the seed helpers compile cleanly on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n".join(fails)); sys.exit(1)

    def run(allow=None, committed=True, marks=(), fail_set=False):
        d = tempfile.mkdtemp(dir=td); rwd = os.path.join(d, "rw"); os.mkdir(rwd)
        if committed: open(os.path.join(rwd, ".committed"), "w").write("1")
        for m in marks: open(os.path.join(rwd, m), "w").write("1")
        if allow is not None: open(os.path.join(rwd, "allow"), "w").write(allow)
        env = dict(os.environ)
        if fail_set: env["FAIL_SET"] = "1"
        p = subprocess.run([exe], cwd=d, capture_output=True, text=True, env=env)
        al = os.path.join(rwd, "allow")
        return {"allow": open(al).read() if os.path.exists(al) else None,
                "geo": os.path.exists(os.path.join(rwd, ".seed_geohost")),
                "abuse": os.path.exists(os.path.join(rwd, ".seed_abusech")),
                "log": [l for l in p.stdout.splitlines() if l.startswith("LOG ")], "rc": p.returncode, "dir": d}

    x = run(allow="", committed=False)
    check("before the list migration commits: nothing written, no marker", x["allow"] == "" and not x["geo"] and not x["abuse"] and not x["log"], x)

    x = run(allow="")
    check("empty whitelist: the ipdeny host then the four abuse.ch addresses",
          x["allow"] == " ".join([GEO] + ABUSE), x["allow"])
    check("empty whitelist: both markers written", x["geo"] and x["abuse"], x)
    check("empty whitelist: one log line per seed, naming what was added",
          len(x["log"]) == 2 and "www.ipdeny.com (%s)" % GEO in x["log"][0]
          and "abuse.ch feed hosts (URLhaus, ThreatFox, Feodo Tracker) (%s)" % " ".join(ABUSE) in x["log"][1], x["log"])

    x = run(allow="10.0.0.0/8 " + GEO, marks=(".seed_geohost",))
    check("a box that took the ipdeny seed gets only the abuse.ch addresses, appended",
          x["allow"] == "10.0.0.0/8 %s %s" % (GEO, " ".join(ABUSE)) and x["abuse"] and len(x["log"]) == 1, x)

    x = run(allow="1.2.3.4", marks=(".seed_geohost", ".seed_abusech"))
    check("both markers present: a user who deleted the entries keeps them deleted",
          x["allow"] == "1.2.3.4" and not x["log"], x)

    x = run(allow="192.0.2.7,151.101.66.49/32<151.101.2.490 ", marks=(".seed_geohost",))
    check("present addresses (bare or /32) are not added again; a longer address sharing the prefix is not a match",
          x["allow"] == "192.0.2.7,151.101.66.49/32<151.101.2.490 151.101.2.49 151.101.130.49 151.101.194.49", x["allow"])
    check("the log names only what was added", len(x["log"]) == 1 and "(151.101.2.49 151.101.130.49 151.101.194.49)" in x["log"][0], x["log"])

    x = run(allow=" ".join(ABUSE), marks=(".seed_geohost",))
    check("all four already present: list untouched, marker set, no log line", x["allow"] == " ".join(ABUSE) and x["abuse"] and not x["log"], x)

    x = run(allow="198.51.100.0/24", marks=(".seed_geohost",), fail_set=True)
    check("a failed list write leaves the marker unset (the next start retries)", x["allow"] == "198.51.100.0/24" and not x["abuse"] and not x["log"], x)
    env = dict(os.environ); env.pop("FAIL_SET", None)
    subprocess.run([exe], cwd=x["dir"], capture_output=True, text=True, env=env)
    check("... and the retry adds them", open(os.path.join(x["dir"], "rw", "allow")).read() == "198.51.100.0/24 " + " ".join(ABUSE)
          and os.path.exists(os.path.join(x["dir"], "rw", ".seed_abusech")))

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
