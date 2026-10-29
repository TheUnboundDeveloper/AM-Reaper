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
ASUS = "52.250.42.40"
LE = ["172.65.32.248", "2606:4700:60:0:f53d:5624:85c7:3a2c"]

a = rw.find("static int rw_seed_has(const char *list, const char *ip)")
b = rw.find("static void rw_seed_allow(void)")
if a < 0 or b < 0:
    print("FAIL seed helpers not found in rwarden.c"); sys.exit(1)
b = rw.find("\n}\n", b) + 3
helpers = rw[a:b]
defs = re.findall(r"^#define (?:RW_GEO_HOST_IP|RW_SEED_MARK|RW_ABUSECH_IPS|RW_SEED_MARK_ABUSECH|RW_ASUSDDNS_IP|RW_SEED_MARK_ASUSDDNS|RW_LE_IPS|RW_SEED_MARK_LE|RW_DDNS_WARNED|RW_DNSALLOW_SEED|RW_SEED_MARK_DNSALLOW)\b(?:.*\\\n)*.*$", rw, re.M)

# ---- static
check("the four Fastly addresses for the abuse.ch hosts are the seed",
      '#define RW_ABUSECH_IPS  "%s"' % " ".join(ABUSE) in rw)
check("the abuse.ch seed has its own marker (boxes that took the ipdeny seed still get it)",
      '#define RW_SEED_MARK_ABUSECH REAPER_RW_DIR "/.seed_abusech"' in rw and len(defs) == 11, defs)
DNSSEED = ["abuse.ch", "ipdeny.com", "pool.ntp.org", "asuscomm.com", "asus.com", "github.com", "githubusercontent.com",
           "spamhaus.org", "malware-filter.gitlab.io", "v.firebog.net", "blocklistproject.github.io", "hole.cert.pl", "threatview.io"]
dx = rw[rw.find('"rw_dexempt() {\\n"'):]
dx = dx[:dx.find('"}\\n"')]
check("2026-10-22: Dreadwatch's fixed never-block names are a one-time seed of the page's never-block list, not hard-coded",
      ('#define RW_SEED_MARK_DNSALLOW REAPER_RW_DIR "/.seed_dnsallow"' in rw
       and "printf '%s\\\\n' local arpa lan\\n" in dx and not any(n in dx for n in DNSSEED)), dx[:300])
check("2026-10-22: the ASUS DDNS server and the Let's Encrypt API (v4 + v6) are seeds with their own markers",
      '#define RW_ASUSDDNS_IP  "%s"' % ASUS in rw and '#define RW_LE_IPS       "%s"' % " ".join(LE) in rw
      and '#define RW_SEED_MARK_ASUSDDNS REAPER_RW_DIR "/.seed_asusddns"' in rw and '#define RW_SEED_MARK_LE REAPER_RW_DIR "/.seed_letsencrypt"' in rw)
sv = open(os.path.join(os.path.dirname(RW), "services.c"), encoding="utf-8", errors="surrogateescape").read()
sd = sv[sv.find("start_ddns(char *caller, int isAidisk)"):]
check("start_ddns seeds them before any update, after the DDNS-off return (not on the AiDisk register path)",
      0 < sd.find('if (!nvram_get_int("ddns_enable_x")) {') < sd.find("rwarden_ddns_seed();") < sd.find("else { // AiDisk register DDNS"))
check("rw_seed_allow (every Warden start) runs the DDNS seeds too", "\trwarden_ddns_seed();\t/* 2026-10-22" in helpers)
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
static int reaper_write_atomic(const char *p, const char *b, size_t n, int mode) { (void)n; (void)mode; return put(p, b); }
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

    def run(allow=None, committed=True, marks=(), fail_set=False, nv=None, warned=False, dnsallow=None):
        d = tempfile.mkdtemp(dir=td); rwd = os.path.join(d, "rw"); os.mkdir(rwd); os.mkdir(os.path.join(d, "tmp"))
        # the Dreadwatch seed has its own cases below; elsewhere it is already taken
        if dnsallow is None: open(os.path.join(rwd, ".seed_dnsallow"), "w").write("1")
        else: open(os.path.join(rwd, "dnsallow"), "w").write(dnsallow)
        if warned: open(os.path.join(d, "tmp", "rwarden.ddns_warned"), "w").write("1")
        if committed: open(os.path.join(rwd, ".committed"), "w").write("1")
        for m in marks: open(os.path.join(rwd, m), "w").write("1")
        if allow is not None: open(os.path.join(rwd, "allow"), "w").write(allow)
        env = dict(os.environ)
        if fail_set: env["FAIL_SET"] = "1"
        for k, v in (nv or {}).items(): env["NV_" + k] = v
        p = subprocess.run([exe], cwd=d, capture_output=True, text=True, env=env)
        al = os.path.join(rwd, "allow")
        return {"allow": open(al).read() if os.path.exists(al) else None,
                "geo": os.path.exists(os.path.join(rwd, ".seed_geohost")),
                "abuse": os.path.exists(os.path.join(rwd, ".seed_abusech")),
                "asus": os.path.exists(os.path.join(rwd, ".seed_asusddns")),
                "le": os.path.exists(os.path.join(rwd, ".seed_letsencrypt")),
                "eval": [l for l in p.stdout.splitlines() if l.startswith("EVAL ")],
                "warned": os.path.exists(os.path.join(d, "tmp", "rwarden.ddns_warned")),
                "dnsallow": open(os.path.join(rwd, "dnsallow")).read() if os.path.exists(os.path.join(rwd, "dnsallow")) else None,
                "dmark": os.path.exists(os.path.join(rwd, ".seed_dnsallow")),
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

    # ---- 2026-10-22: Dreadwatch's never-block names land in the page's list, once
    x = run(allow="1.2.3.4", marks=(".seed_geohost", ".seed_abusech"), dnsallow="")
    check("empty never-block list: the 13 names are added once, logged naming the Dreadwatch page, marker set",
          x["dnsallow"] == " ".join(DNSSEED) and x["dmark"] and len(x["log"]) == 1
          and "never-block list: added" in x["log"][0] and "Dreadwatch page" in x["log"][0], x)
    x = run(allow="1.2.3.4", marks=(".seed_geohost", ".seed_abusech"), dnsallow="mine.example asuscomm.com")
    check("the operator's own entries are kept, names already there are not added twice",
          x["dnsallow"] == "mine.example asuscomm.com " + " ".join(n for n in DNSSEED if n != "asuscomm.com"), x["dnsallow"])
    x = run(allow="1.2.3.4", marks=(".seed_geohost", ".seed_abusech", ".seed_dnsallow"), dnsallow="mine.example")
    check("marker present: a name the operator removed stays removed", x["dnsallow"] == "mine.example" and not x["log"], x)
    x = run(allow="1.2.3.4", marks=(".seed_geohost", ".seed_abusech"), dnsallow="a.example\nb.example")
    check("a newline-separated list is matched too (no duplicates of existing names)",
          x["dnsallow"].startswith("a.example\nb.example ") and x["dnsallow"].count("asus.com") == 1, x["dnsallow"])

    # ---- 2026-10-22: ASUS DDNS / Let's Encrypt
    M2 = (".seed_geohost", ".seed_abusech")
    ASUSNV = {"ddns_enable_x": "1", "ddns_server_x": "WWW.ASUS.COM"}
    x = run(allow="1.2.3.4", marks=M2)
    check("DDNS off, no certificate: neither seed, no marker", x["allow"] == "1.2.3.4" and not x["asus"] and not x["le"] and not x["log"], x)
    x = run(allow="1.2.3.4", marks=M2, nv={"ddns_enable_x": "1", "ddns_server_x": "WWW.NO-IP.COM"})
    check("another DDNS provider: the ASUS server is not seeded", x["allow"] == "1.2.3.4" and not x["asus"], x)
    x = run(allow="1.2.3.4", marks=M2, nv=dict(ASUSNV, rwarden_enable="1"))
    check("ASUS DDNS on: its server is added once, logged, marker set; the certificate seed waits",
          x["allow"] == "1.2.3.4 " + ASUS and x["asus"] and not x["le"] and len(x["log"]) == 1 and "ns1.asuscomm.com (%s)" % ASUS in x["log"][0], x)
    check("... and goes straight into the running whitelist set while Warden is on", x["eval"] == ["EVAL ipset add rw_allow %s -exist" % ASUS], x["eval"])
    x = run(allow="1.2.3.4", marks=M2, nv=dict(ASUSNV, le_enable="1", rwarden_enable="1"))
    check("ASUS DDNS + Let's Encrypt: both seeds, the v6 address into the v6 set",
          x["allow"] == "1.2.3.4 %s %s" % (ASUS, " ".join(LE)) and x["asus"] and x["le"]
          and x["eval"] == ["EVAL ipset add rw_allow %s -exist" % ASUS, "EVAL ipset add rw_allow %s -exist" % LE[0],
                            "EVAL ipset add rw_allow6 %s -exist" % LE[1]], x)
    x = run(allow="1.2.3.4", marks=M2, nv=dict(ASUSNV, le_enable="1"))
    check("Warden off: the list gets the entries, the live sets are not touched", x["asus"] and x["le"] and not x["eval"], x)
    x = run(allow="1.2.3.4 %s/128" % LE[1], marks=M2, nv={"le_enable": "1"})
    check("an address already present as /128 is not added again", x["allow"] == "1.2.3.4 %s/128 %s" % (LE[1], LE[0]), x["allow"])
    x = run(allow="1.2.3.4", marks=M2 + (".seed_asusddns",), nv=dict(ASUSNV, rwarden_enable="1", rwarden_self="1"))
    check("seeded then removed, router-traffic filter on: stays removed, ONE warning naming the address",
          x["allow"] == "1.2.3.4" and len(x["log"]) == 1 and "router-traffic filter is ON" in x["log"][0] and ASUS in x["log"][0] and x["warned"], x)
    x = run(allow="1.2.3.4", marks=M2 + (".seed_asusddns",), nv=dict(ASUSNV, rwarden_enable="1", rwarden_self="1"), warned=True)
    check("... and not again in the same boot (start_ddns runs on every retry)", not x["log"], x["log"])
    x = run(allow="1.2.3.4", marks=M2 + (".seed_asusddns",), nv=dict(ASUSNV, rwarden_enable="1"))
    check("seeded then removed, router-traffic filter off: no warning (country blocks never touch the router's own traffic)",
          not x["log"] and not x["warned"], x)
    x = run(allow="1.2.3.4 " + ASUS, marks=M2 + (".seed_asusddns",), nv=dict(ASUSNV, rwarden_enable="1", rwarden_self="1"))
    check("entry still there: no warning", not x["log"], x["log"])
    x = run(allow="1.2.3.4", marks=M2, nv=dict(ASUSNV, rwarden_enable="1"), fail_set=True)
    check("a failed list write: no marker, no live add (the next DDNS start retries)", not x["asus"] and not x["eval"], x)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
