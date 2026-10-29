#!/usr/bin/env python3
"""test_wallguard_rc.py - Wallguard phase 2 (2026-10-21): rc's schedules and service bits, the
blocked-services catalog, and the CGI's checks for the three new settings.

WHY. Phase 2 adds per-profile blocked services (one list bit per profile, from the bits presets
and custom lists never use), schedules that switch a profile's service block on and off (rc
evaluates them in local time when it writes the policy), and per-profile safe-search flags. The
schedule logic decides when a child's games are blocked, so it is compiled out of rc/wallguard.c
and run through its edges; the catalog is data the page and rc both parse.

WHAT IT DOES. Compiles sh_sched_active() from rc/wallguard.c with a small driver (cross-midnight,
day edges, start == end, several windows, no window); parses wallguard/services.txt (ids unique and
well-formed, every domain valid, categories known); pins the service-bit table, the policy's
keep / flags output, the cron edge wiring, the CGI validators and the Makefile install line.

Exit 0 pass, 1 fail, 77 skipped (no router source tree; the compiled half also needs gcc).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "wallguard.c")):
    skip("no router source tree with rc/wallguard.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
def read(p): return open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or detail == "" else " - " + str(detail)))
    if not cond: fails.append(name)

rc, web, mk = read("rc/wallguard.c"), read("httpd/web.c"), read("wallguard/Makefile")

# ---------------------------------------------------------------- the catalog
cat = read("wallguard/services.txt")
NAME = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
rows = [l.split("|") for l in cat.splitlines() if l.strip() and not l.startswith("#")]
ids = [r[0] for r in rows]
badrow = [r for r in rows if len(r) != 4 or not re.match(r"^[a-z0-9_]{1,24}$", r[0]) or not r[1].strip()
          or r[2] not in ("social", "video", "gaming", "messaging", "shopping", "dating", "ai")
          or any(c in r[1] for c in '"\\<>|') or not r[3].split()]
baddom = [(r[0], d) for r in rows if len(r) == 4 for d in r[3].split() if not NAME.match(d)]
check("catalog: %d services, every row id|label|category|domains with a known category" % len(rows), len(rows) >= 30 and not badrow, badrow[:3])
check("catalog: ids unique", len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1][:3])
check("catalog: every domain is a valid host name (subtree entries)", not baddom, baddom[:5])
check("catalog: the plain services parents ask for are there",
      all(i in ids for i in ("tiktok", "youtube", "instagram", "snapchat", "roblox", "epicgames", "minecraft", "discord")))
check("Makefile installs the catalog where rc and httpd read it",
      "install -D -m 0644 services.txt $(INSTALLDIR)/usr/share/wallguard/services" in mk
      and '#define SH_CATALOG\t"/usr/share/wallguard/services"' in rc and '#define SH_CATALOG\t"/usr/share/wallguard/services"' in web)

# ---------------------------------------------------------------- rc wiring
check("rc: 13 service bits, none a preset (1-9) or custom (20-27) bit",
      "static const int sh_svc_bit[SH_SVC_MAX] = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 28, 29, 30 };" in rc)
check("rc: the default profile's mask never takes a profile's service bit (kind s skipped)",
      "kind != 's'" in rc and '"%d svc_%s - s\\n"' in rc)
check("rc: the policy carries keep (the service bits) and a flags field on default / mac / net lines",
      '"keep %x\\n"' in rc and '"default %x %x\\n"' in rc and '"mac %s %x %x\\n"' in rc and '"net %s/%u %x %x\\n"' in rc)
check("rc: window edges become cron entries that rewrite the policy, cleared on stop",
      "service start_wallguard_policy >/dev/null 2>&1" in rc and rc.count('unlink(SH_DIR "/cron");') == 1
      and '"wallguard_e%02d%02d %d %d\\n"' in rc)
check("rc: Bypass carries no services and no safe search", '!strcmp(pid, "bypass")' in rc and "return 0;\t\t\t/* Bypass changes nothing, safe search included */" in rc)
check("rc: an unset clock keeps services blocked (tm NULL = active)", "tmv.tm_year + 1900 >= 2024" in rc and "(!tm || sh_sched_active(" in rc)

# ---------------------------------------------------------------- CGI
check("CGI: services / sched / safe saved through their own checks",
      '{ "services", SH_JFFS "/services", sh_chk_services }' in web and '{ "sched", SH_JFFS "/sched", sh_chk_sched }' in web
      and '{ "safe", SH_JFFS "/safe", sh_chk_safe }' in web)
check("CGI: config returns the catalog, which bit is whose and the safe-search state",
      '"],\\"svcbits\\":{"' in web and '",\\"catalog\\":["' in web and '"},\\"ss\\":{"' in web)

# ---------------------------------------------------------------- the schedule, compiled
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("note: no C compiler - the compiled half is skipped")
else:
    a = rc.index("struct sh_win {")
    b = rc.index("\n}\n", rc.index("static int sh_sched_active(")) + 3
    td = tempfile.mkdtemp(prefix="wallguardrc-")
    try:
        c = os.path.join(td, "t.c")
        open(c, "w").write("#include <stdio.h>\n#include <stdlib.h>\n#include <time.h>\n" + rc[a:b] + r'''
/* argv: windows as "days,from,to" (minutes) then "wday,hh,mm" to test; prints 1 / 0 */
int main(int c, char **v)
{
	struct sh_win w[8];
	struct tm tm = { 0 };
	int n = 0, i;
	for (i = 1; i < c - 1 && n < 8; i++, n++)
		if (sscanf(v[i], "%d,%d,%d", &w[n].days, &w[n].from, &w[n].to) != 3)
			return 2;
	if (sscanf(v[c - 1], "%d,%d,%d", &tm.tm_wday, &tm.tm_hour, &tm.tm_min) != 3)
		return 2;
	printf("%d\n", sh_sched_active(w, n, &tm));
	return 0;
}
''')
        exe = os.path.join(td, "t")
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("sh_sched_active compiles on the host (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            def act(wins, when):
                return subprocess.run([exe] + wins + [when], capture_output=True, text=True).stdout.strip() == "1"
            MON_FRI = 0b0111110       # bit 0 Sunday .. bit 6 Saturday
            bed = ["%d,%d,%d" % (MON_FRI, 21 * 60, 7 * 60)]      # school nights 21:00 -> 07:00
            check("no window = always on", act([], "3,12,0"))
            check("a school-night window is on Monday 22:00 and off Monday 20:59",
                  act(bed, "1,22,0") and not act(bed, "1,20,59"))
            check("...past midnight it stays on (Tuesday 06:59) and ends at 07:00",
                  act(bed, "2,6,59") and not act(bed, "2,7,0"))
            check("...Friday night carries into Saturday morning, but Saturday night is off",
                  act(bed, "6,3,0") and not act(bed, "6,22,0"))
            check("...Sunday night is off (Sunday not in the days), Monday 06:00 is off (Sunday did not start it)",
                  not act(bed, "0,22,0") and not act(bed, "1,6,0"))
            day = ["%d,%d,%d" % (0b1000001, 9 * 60, 17 * 60)]    # weekends 09:00-17:00
            check("a same-day window: on inside, off at its end minute and on other days",
                  act(day, "6,9,0") and act(day, "0,16,59") and not act(day, "0,17,0") and not act(day, "3,12,0"))
            whole = ["%d,%d,%d" % (0b0001000, 0, 0)]             # Wednesday, start == end
            check("start == end = the whole day", act(whole, "3,0,0") and act(whole, "3,23,59") and not act(whole, "4,0,0"))
            check("several windows: any one on is on", act(day + bed, "1,23,0") and act(day + bed, "6,10,0") and not act(day + bed, "3,12,0"))
    finally:
        shutil.rmtree(td, ignore_errors=True)

# ---- review 2026-10-21 (agent findings, each verified in the tree before the fix)
web = read("httpd/web.c")
m = re.search(r"static int sh_mac\(const char \*s\)\n\{.*?\n\}\n", web, re.S)
# review 2026-10-24 (Q-B-9): sh_mac returns the Gatekeeper's gk_valid_mac (one copy of the rule) - lift that too
g = re.search(r"static int\ngk_valid_mac\(const char \*m\)\n\{.*?\n\}\n", web, re.S)
check("CGI: sh_mac() is found", bool(m) and bool(g))
if m and g and CC:
    td = tempfile.mkdtemp(prefix="shmac_")
    try:
        open(os.path.join(td, "m.c"), "w").write("#include <ctype.h>\n#include <string.h>\n#include <stdio.h>\n" + g.group(0) + m.group(0) +
            'int main(int c, char **v) { (void)c; printf("%d", sh_mac(v[1])); return 0; }\n')
        b = subprocess.run([CC, "-Wall", "-Werror", "-o", os.path.join(td, "m"), os.path.join(td, "m.c")], capture_output=True, text=True)
        def mac_ok(s): return subprocess.run([os.path.join(td, "m"), s], capture_output=True, text=True).stdout == "1"
        check("CGI: sh_mac() takes exactly xx:xx:xx:xx:xx:xx (MED: '0:0:0:0:0:0;halt;' passed ether_atoe and reached popen)",
              b.returncode == 0 and mac_ok("00:00:5e:00:53:Af") and not mac_ok("0:0:0:0:0:0;halt;") and not mac_ok("0:0:0:0:0:0`id`")
              and not mac_ok("aa-bb-cc-dd-ee-ff") and not mac_ok("aa:bb:cc:dd:ee:f") and not mac_ok("aa:bb:cc:dd:ee:fg"), b.stderr[-200:])
    finally:
        shutil.rmtree(td, ignore_errors=True)
shc = read("rc/wallguard.c"); enc = read("rc/encdns.c")
check("rc: Wallguard's policy writes the normalised MAC, never the parsed text",
      shc.count("ether_atoe(a, ea) && ether_etoa(ea, a)") == 2)
check("rc: rednsd's conf and the REAPER_EDNS rule write the normalised MAC",
      enc.count("ether_etoa(ea, macbuf)") == 2 and "--mac-source %s -j RETURN\\n\", mac)" not in enc)
fwd = read("dnsmasq/src/forward.c"); eng = read("dnsmasq/src/wallguard.c")
check("dnsmasq: a duplicate query joins one in flight only when Wallguard judges both askers alike (LOW: shared CNAME verdict)",
      "(wallguard_merge_ok(&forward->frec_src.wallguard_client, reaper_client(udpaddr), now) || (forward = NULL, 0))" in fwd
      and "int wallguard_merge_ok(union mysockaddr *a, union mysockaddr *b, time_t now)" in eng)
check("httpd: rednsd's status file is opened O_NONBLOCK (LOW: a FIFO hung httpd)",
      "RENC_NOTE : RENC_STATUS, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)" in web)
ssh = read("wallguard/wallguard.sh"); scc = read("wallguard/wallguardc.c")
check("wallguard.sh: builds are serialised; wallguardc's temp files are per process (LOW: two builds shared db.tmp)",
      'exec 8>"$D/build.lock"' in ssh and "lock_wait 8 300" in ssh and "flock -w" not in ssh and scc.count('"%s.%d.tmp"') == 2)

# ---------------------------------------------------------------- 2026-10-25: the rename's one-time carry-over
# A box that ran a test image under the earlier name keeps its two nvram switches and its /jffs folder; the function is
# lifted out of rc/wallguard.c and run against a stub nvram and a temporary /jffs.
j2, ub, rch = read("rc/jffs2.c"), read("rc/ubifs.c"), read("rc/rc.h")
check("carry-over: called right after the /jffs permission sweep on both flash file systems; declared in rc.h",
      'reaper_jffs_perm_sweep("/jffs");\n\t/* 2026-10-25: Wallguard settings saved under its earlier test name move once (rc/wallguard.c) */\n\twallguard_migrate_legacy("/jffs");' in j2
      and "reaper_jffs_perm_sweep(UBIFS_MNT_DIR);\n\t/* 2026-10-25: Wallguard settings saved under its earlier test name move once (rc/wallguard.c) */\n\twallguard_migrate_legacy(UBIFS_MNT_DIR);" in ub
      and "extern void wallguard_migrate_legacy(const char *jffs);" in rch)
m = re.search(r'#define SH_LEGACY\t"shr" "oud"\nvoid wallguard_migrate_legacy\(const char \*jffs\)\n\{.*?\n\}\n', rc, re.S)
gcc = shutil.which("gcc")
check("carry-over: the function is found (the old name in two parts, so no rename sweep can rewrite it)", bool(m))
if m and gcc:
    LEG = "shr" "oud"
    drv = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
static char K[8][32], V[8][32]; static int nk, commits;
static char *nvram_get(const char *k){ int i; for (i = 0; i < nk; i++) if (K[i][0] && !strcmp(K[i], k)) return V[i]; return NULL; }
static int nvram_set(const char *k, const char *v){ int i; for (i = 0; i < nk; i++) if (K[i][0] && !strcmp(K[i], k)) { snprintf(V[i], 32, "%s", v); return 0; }
  snprintf(K[nk], 32, "%s", k); snprintf(V[nk], 32, "%s", v); nk++; return 0; }
static int nvram_unset(const char *k){ int i; for (i = 0; i < nk; i++) if (!strcmp(K[i], k)) K[i][0] = 0; return 0; }
static int nvram_commit(void){ commits++; return 0; }
static void logmessage(const char *t, const char *f, ...){ (void)t; (void)f; }
''' + m.group(0) + r'''
int main(int argc, char **argv){
  int i; (void)argc;
  for (i = 2; i + 1 < argc; i += 2) nvram_set(argv[i], argv[i + 1]);
  wallguard_migrate_legacy(argv[1]);
  for (i = 0; i < nk; i++) if (K[i][0]) printf("%s=%s\n", K[i], V[i]);
  printf("commits=%d\n", commits); return 0;
}
'''
    td = tempfile.mkdtemp(prefix="synmig_")
    try:
        open(os.path.join(td, "m.c"), "w").write(drv)
        b = subprocess.run([gcc, "-Wall", "-Werror", "-Wno-unused-function", "-o", os.path.join(td, "m"), os.path.join(td, "m.c")], capture_output=True, text=True)
        check("carry-over: compiles cleanly on the host (-Wall -Werror)", b.returncode == 0, b.stderr[-300:])
        if b.returncode == 0:
            def run(jffs, *kv): return subprocess.run([os.path.join(td, "m"), jffs] + list(kv), capture_output=True, text=True).stdout.split()
            j = os.path.join(td, "j1"); os.makedirs(os.path.join(j, LEG)); open(os.path.join(j, LEG, "sched"), "w").write("p1 7f 22:00 07:00\n")
            o = run(j, LEG + "_enable", "1", LEG + "_mode", "nx", "wallguard_enable", "0", "wallguard_mode", "null")
            check("carry-over: an old switch wins over the new key's factory default, the old keys go, one commit",
                  sorted(o) == sorted(["wallguard_enable=1", "wallguard_mode=nx", "commits=1"]), o)
            check("carry-over: the /jffs folder moves with its files",
                  not os.path.exists(os.path.join(j, LEG)) and open(os.path.join(j, "wallguard", "sched")).read().startswith("p1 7f"))
            o = run(j, "wallguard_enable", "1")
            check("carry-over: a second boot changes nothing and commits nothing", o == ["wallguard_enable=1", "commits=0"], o)
            j = os.path.join(td, "j2"); os.makedirs(os.path.join(j, LEG)); os.makedirs(os.path.join(j, "wallguard"))
            run(j)
            check("carry-over: an existing new folder is never overwritten (the old one is left in place)",
                  os.path.isdir(os.path.join(j, LEG)) and os.path.isdir(os.path.join(j, "wallguard")))
            j = os.path.join(td, "j3"); os.makedirs(j); os.makedirs(os.path.join(td, "elsewhere")); os.symlink(os.path.join(td, "elsewhere"), os.path.join(j, LEG))
            run(j)
            check("carry-over: a link planted under the old name is not followed or moved",
                  os.path.islink(os.path.join(j, LEG)) and not os.path.exists(os.path.join(j, "wallguard")))
    finally:
        shutil.rmtree(td, ignore_errors=True)

# release review 2026-10-25 (W-1): a table holding My rules alone because every list download failed (wallguard.sh's
# pending mark) is fetched again at WAN up - not within two minutes of the last attempt - and by rwatch every 10 min;
# switching Wallguard off removes the mark. Rename leftovers: the prefixes compare their whole length.
rcw = read("rc/wallguard.c")
fw = rcw[rcw.find("void wallguard_on_firewall(void)"):rcw.find("void wallguard_store_attached(void)")]
check("W-1: start_firewall fetches again while the pending mark stands, at most every 2 min",
      'else if (f_exists(SH_DIR "/pending") &&' in fw and "time(NULL) - st.st_mtime >= 120" in fw
      and fw.count('sh_run_bg("update");') == 2)
check("W-1: stop_wallguard removes the pending mark", 'SH_DIR "/db", SH_DIR "/pending", SH_DIR "/policy"' in rcw)
check("rename leftovers: wallguard_ (10) and wallguard-dir= (14) compared over their whole length",
      rcw.count('!strncmp(name, "wallguard_", 10)') == 2 and '!strncmp(l, "wallguard-dir=", 14)' in rcw
      and '"wallguard_", 7)' not in rcw and '"wallguard-dir=", 11)' not in rcw)
rw = read("rc/rwatch.c")
check("W-1: rwatch fetches while the table is missing OR the pending mark stands, every 10 min with the WAN up",
      "{ [ ! -s /tmp/wallguard/db ] || [ -f /tmp/wallguard/pending ]; }; then\\n" in rw
      and "[ -s /tmp/wallguard/db ] || sh /usr/sbin/wallguard.sh restore" in rw and "+%s) )) -ge 600 ]; }; then\\n" in rw)
sh = read("wallguard/wallguard.sh")
check("X-1: stats reads the store's place without touching the volume; fold queues history for one detached writer that drops the locks",
      "HB=$(store_peek shh)" in sh and "b=$(store_peek shl)" in sh and 'hist "$REC.add"' not in sh
      and '( exec 6>&- 7>&- 8>&- 9>&-; hist "$D/hist.work"; rm -f "$D/hist.work" ) </dev/null >/dev/null 2>&1 &' in sh
      and 'exec 6>"$D/fold.lock"' in sh)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
