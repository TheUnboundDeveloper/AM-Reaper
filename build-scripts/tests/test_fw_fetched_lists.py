#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Policy Routing by ASN and by country: the fetched lists (REAPER-FW-LISTS, 2026-11-22).

WHY. An ASN list (object type asn) or a country list (type geo) that a Policy Routing rule names gets its own
rwfw_<name> / rwfw6_<name> set. The set script only CREATES that set; /tmp/reaper_fw/lists.sh fills it, always by
building a temporary set and swapping it in, from prefix lists it downloads (ASN: ipverse, then RIPEstat, then
HackerTarget; country: Warden's loaded set, then ipdeny, then ipverse) and saves under /jffs/reaper_fw/lists.
A downloaded list decides where traffic goes, so what reaches a set is filtered and capped, and a failed or
refused update leaves the live set and the saved list as they were.

This test compiles the real functions from rc/reaper_fw.c, GENERATES the set script and lists.sh with them and
RUNS lists.sh under stand-in ipset / curl / logger / nvram / df:
  1. the AS number validator and the saved-list names of an object;
  2. the set script: a fetched list in use is created and kept, never flushed, destroyed or filled there; one no
     rule names gets no set; the literal objects are untouched;
  3. lists.sh as generated: the table, the daily job, the caps on lists in use, the self-monitor's job table;
  4. lists.sh running: source order and fallback, the temporary-set swap, the filter, the cap, the memory guard,
     last-good on failure, refill from flash without the network, a save only on a change, cleanup.
Mutation checks: with the filter, the swap or the cap taken out of the script the matching check must fail.
Exit 0 pass, 1 fail, 77 skipped (no compiler or no router source: pass release/src/router or set REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_fw.c")):
    print("SKIP: no router source tree"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
SH = shutil.which("sh")
if not CC or not SH or not shutil.which("flock"):
    print("SKIP: no host C compiler, no sh or no flock"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:1200] if detail else ""))

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

def rd(p):
    try:
        with open(p) as fh: return fh.read()
    except OSError:
        return ""

fw = read("rc/reaper_fw.c"); rwatch = read("rc/rwatch.c")
if "REAPER-FW-LISTS" not in fw:
    print("SKIP: this tree has no fetched lists"); sys.exit(77)
td = tempfile.mkdtemp(prefix="fwlists-")
try:
    rfw = os.path.join(td, "rfw"); os.mkdir(rfw)
    jffs = os.path.join(td, "jffs"); cache = os.path.join(jffs, "reaper_fw", "lists")
    defs = []
    for m in re.finditer(r"^#define[ \t]+(RFW_[A-Z0-9_]+)[ \t]+(.*)$", fw, re.M):
        name, val = m.group(1), m.group(2).rstrip()
        if val.endswith("\\"): continue
        if name == "RFW_DIR": val = '"%s"' % rfw
        elif name == "RFW_CACHE": val = '"%s/reaper_fw"' % jffs
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
static void logmessage(const char *t, const char *fmt, ...) { va_list ap; fprintf(stderr, "LOG %s: ", t); va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap); fputc('\n', stderr); }
static int reaper_script_ok(const char *p) { (void)p; return 0; }
static void reaper_secure_dir(const char *p, int m) { (void)p; (void)m; }
static int t_eval(const char *a, ...) { va_list ap; const char *s; fprintf(stderr, "EVAL %s", a); va_start(ap, a); while ((s = va_arg(ap, const char *)) != NULL) fprintf(stderr, " %s", s); va_end(ap); fputc('\n', stderr); return 0; }
#define eval(...) t_eval(__VA_ARGS__, NULL)
static int nvram_match(const char *k, const char *v) { char e[64]; const char *x; snprintf(e, sizeof(e), "NV_%s", k); x = getenv(e); return x && !strcmp(x, v); }
static int reaper_pbr_uses_object(const char *name) { char w[64]; const char *u = getenv("USES"); snprintf(w, sizeof(w), " %s ", name); return u && strstr(u, w) != NULL; }
static void rwarden_listsrc_seed(void) { fprintf(stderr, "SEED listsrc\n"); }
'''
    parts = [STUB, "\n".join(defs), mt.group(0) if mt else ""]
    SIGS = ("static int rfw_valid_name(", "static int rfw_valid_cidr(", "static int rfw_valid_cidr6(", "static int rfw_valid_ip(",
            "static int rfw_valid_range(", "static int rfw_valid_mac(", "static int rfw_valid_fqdn(", "static int rfw_valid_cc(",
            "static int rfw_field(", "static unsigned long rfw_asn_num(", "static int rfw_fetched_type(", "static int rfw_word_in(",
            "static int rfw_fetched_keys(", "static int rfw_fetched_wanted(", "static void rfw_emit_one_set(",
            "static void rfw_emit_fetched_set(", "static void rfw_emit_sets(", "static int rfw_list_saved(", "static void rfw_gen_lists(")
    try:
        for sig in SIGS: parts.append(extract(fw, sig))
        missing = ""
    except ValueError as e:
        missing = str(e)
    parts.append(r'''
int main(int argc, char **argv) { rfw_cfg_t c; static char keep[8192]; char keys[512]; memset(&c, 0, sizeof(c));
	if (!strcmp(argv[1], "asn")) { printf("%lu\n", rfw_asn_num(argv[2])); return 0; }
	if (!strcmp(argv[1], "keys")) { int n = rfw_fetched_keys(argv[2], argv[3], keys, sizeof(keys)); printf("%d|%s\n", n, keys); return 0; }
	c.obj = argv[2];
	if (!strcmp(argv[1], "sets")) { keep[0] = 0; rfw_emit_sets(stdout, &c, keep, sizeof(keep)); printf("#KEEP=%s \n", keep); }
	else rfw_gen_lists(&c);
	return 0; }
''')
    csrc = os.path.join(td, "l.c"); gen = os.path.join(td, "l")
    with open(csrc, "w") as fh: fh.write("\n".join(parts))
    r = subprocess.run([CC, "-std=gnu99", "-w", "-o", gen, csrc], capture_output=True, text=True)
    check("the fetched-list functions compile on the host", r.returncode == 0 and mt is not None and not missing, missing + r.stderr[:1500])
    if r.returncode != 0:
        raise SystemExit

    def g(*a, uses="", pbr="1"):
        env = dict(os.environ, USES=" " + uses + " ", NV_reaper_pbr_enable=pbr)
        p = subprocess.run([gen] + list(a), capture_output=True, text=True, env=env)
        return p.stdout, p.stderr

    # ================= 1. the validator, the saved-list names =================
    ok = {"AS2906": 2906, "as2906": 2906, "2906": 2906, "1": 1, "23455": 23455, "64495": 64495, "131072": 131072, "4199999999": 4199999999}
    bad = ["0", "AS0", "23456", "64496", "64512", "65535", "65536", "131071", "4200000000", "4294967295", "4294967296", "99999999999",
           "", "AS", "A2906", "2906x", "29 06", "-1", "2906;id", "AS2906/", "$(id)", "2906\n"]
    got = {k: g("asn", k)[0].strip() for k in list(ok) + bad}
    check("AS number: AS2906 / as2906 / 2906 and the edges of the public ranges are taken",
          all(got[k] == str(v) for k, v in ok.items()), repr({k: got[k] for k in ok}))
    check("AS number: 0, AS_TRANS, the reserved and private blocks, anything not digits - all refused (0)",
          all(got[k] == "0" for k in bad), repr({k: got[k] for k in bad if got[k] != "0"}))
    check("saved-list names: each number once, comma or space, bad ones dropped",
          g("keys", "asn", "AS2906, 40027 as2906,65535,junk AS13335")[0].strip() == "3|as2906 as40027 as13335")
    many = ",".join(str(n) for n in range(1000, 1040))
    n16 = g("keys", "asn", many)[0].strip()
    check("saved-list names: 16 AS numbers at most in one list", n16.startswith("16|as1000 ") and n16.endswith(" as1015"), n16)
    check("saved-list names: a country list is cc_<code>, lower case; not a country = none",
          g("keys", "geo", "NL")[0].strip() == "1|cc_nl" and g("keys", "geo", "NLD")[0].strip() == "0|" and g("keys", "asn", "nope")[0].strip() == "0|")

    # ================= 2. the set script =================
    OBJ = ("n1>cidr>198.51.100.0/24<a1>asn>AS2906,AS40027<a2>asn>13335<g1>geo>NL<g2>geo>US<x1>asn>junk<d1>fqdn>example.com")
    out, err = g("sets", OBJ, uses="a1 g1 x1")
    check("set script: an ASN list a rule names is created in both families with its size, -exist",
          "ipset create rwfw_a1 hash:net maxelem 65536 -exist" in out and "ipset create rwfw6_a1 hash:net family inet6 maxelem 65536 -exist" in out, out)
    check("set script: a country list a rule names gets its own set, with the country size",
          "ipset create rwfw_g1 hash:net maxelem 262144 -exist" in out and "ipset create rwfw6_g1 hash:net family inet6 maxelem 262144 -exist" in out, out)
    lines_f = [l for l in out.splitlines() if re.search(r"rwfw6?_(a1|g1)\b", l) and not l.startswith("#KEEP")]
    check("set script: a fetched list is never flushed, destroyed or filled here (only the two create lines each)",
          len(lines_f) == 4 and all(l.startswith("ipset create ") for l in lines_f), "\n".join(lines_f))
    keep = out[out.index("#KEEP="):]
    check("set script: both of its sets are on the keep list (the sweep leaves them)",
          all(" %s " % s in keep for s in ("rwfw_a1", "rwfw6_a1", "rwfw_g1", "rwfw6_g1")), keep)
    check("set script: a list no rule names gets no set and is not kept (it is swept)",
          not re.search(r"rwfw6?_(a2|g2)\b", out), out)
    check("set script: an ASN list with no valid number gets no set", not re.search(r"rwfw6?_x1\b", out), out)
    check("set script: the literal and the domain objects are as before",
          "RFWS create rwfw_n1 hash:net" in out and "RFWS add rwfw_n1 198.51.100.0/24" in out and "ipset create rwfw_d1 hash:net timeout 3600 -exist" in out
          and "unknown type" not in err, out + err)
    out0, err0 = g("sets", OBJ, uses="a1 g1", pbr="0")
    check("set script: with Policy Routing off no fetched list gets a set", not re.search(r"rwfw6?_(a1|g1)\b", out0), out0)

    # ================= 3. lists.sh as generated =================
    LS = os.path.join(rfw, "lists.sh")
    out, err = g("lists", OBJ, uses="a1 g1 x1")
    sc = rd(LS)
    tab = sc[sc.index("OBJS='\n") + 7:sc.index("\n'\n")] if "OBJS='\n" in sc else ""
    check("lists.sh: the table names each list in use with its kind, set size and saved-list names",
          tab.splitlines() == ["a1 asn 65536 as2906 as40027", "g1 geo 262144 cc_nl"], tab)
    check("lists.sh: the daily job is installed with the script's update mode",
          ("EVAL cru a reaper_fw_lists 17 5 * * * sh %s update" % LS) in err, err)
    if "rwarden_listsrc_seed();" in fw:               # 2026-11-22: the sources go into the "do not block" lists on first use
        check("a list in use asks Warden to add the list sources to the do-not-block lists (once; test_warden_listsrc_seed.py)",
              err.count("SEED listsrc") == 1, err)
        check("building the sets alone does not add them (only the list updater does)", "SEED listsrc" not in g("sets", OBJ, uses="a1")[1])
    check("lists.sh: parses (sh -n)", subprocess.run([SH, "-n", LS], capture_output=True).returncode == 0)
    if shutil.which("busybox"):
        check("lists.sh: parses (busybox ash -n)", subprocess.run(["busybox", "ash", "-n", LS], capture_output=True).returncode == 0)
    check("lists.sh: no apostrophe inside the table quoting, and the mode is private",
          "'" not in tab and (os.stat(LS).st_mode & 0o777) == 0o700)
    check("self-monitor: the job table carries the same command, so the Security Review does not report it",
          "reaper_fw_lists) echo 'sh /tmp/reaper_fw/lists.sh update';;" in rwatch
          and '"17 5 * * * sh " RFW_LISTS " update"' in fw and '#define RFW_LISTS       RFW_DIR "/lists.sh"' in fw)
    big = "<".join("o%d>asn>%s" % (i, ",".join(str(1000 + i * 16 + j) for j in range(16))) for i in range(3))
    out, err = g("lists", big, uses="o0 o1 o2")
    sc3 = rd(LS)
    check("lists.sh: 32 different AS numbers in use at most - the list that would pass it is left out and named in the log",
          "\no0 asn " in sc3 and "\no1 asn " in sc3 and "\no2 asn " not in sc3 and "ASN list o2 NOT loaded" in err, err)
    cc9 = "<".join("c%d>geo>%s" % (i, c) for i, c in enumerate(["NL", "US", "DE", "FR", "GB", "JP", "BR", "IN", "CA"]))
    out, err = g("lists", cc9 + "<c9>geo>nl", uses=" ".join("c%d" % i for i in range(10)))
    sc9 = rd(LS)
    check("lists.sh: 8 different countries in use at most; a second list of a country already in use still loads",
          "\nc7 geo " in sc9 and "\nc8 geo " not in sc9 and "\nc9 geo 262144 cc_nl" in sc9 and "country list c8 NOT loaded" in err, err)
    out, err = g("lists", OBJ, uses="")
    check("lists.sh: nothing in use - the script is removed and the daily job deleted",
          not os.path.exists(LS) and "EVAL cru d reaper_fw_lists" in err, err)
    if "REAPER-FW-LISTS-RETRY" in fw:                 # 2026-11-23: the retry job of a list that has never arrived
        check("nothing in use: the retry job is deleted too", "EVAL cru d reaper_fw_lists_retry" in err, err)
        check("self-monitor: the retry job's command is in the job table (the Security Review does not report it)",
              "reaper_fw_lists_retry) echo 'sh /tmp/reaper_fw/lists.sh missing';;" in rwatch
              and r'cru a reaper_fw_lists_retry \"*/15 * * * * sh " RFW_LISTS " missing\"' in fw)
    if "REAPER-FW-LISTS-WANUP" in fw:                 # 2026-11-23: WAN up asks for a list that has never arrived
        wu = extract(fw, "void reaper_fw_lists_wanup(void)")
        check("WAN up: reaper_fw_lists_wanup() runs the script's wan mode in the background, only when the script exists",
              "access(RFW_LISTS, F_OK) != 0) return;" in wu and 'system("sh " RFW_LISTS " wan >/dev/null 2>&1 &")' in wu
              and "reaper_script_ok(RFW_LISTS)" in wu, wu)
        wan = read("rc/wan.c")
        check("WAN up: wan_up() calls it after the policy-routing reassert and the kill switch, once; rc.h declares it",
              wan.count("reaper_fw_lists_wanup();") == 1 and wan.find("reaper_pbr_reassert();") < wan.find("amvpn_set_kilswitch_rules_all();\n#endif\n\treaper_fw_lists_wanup();")
              and "extern void reaper_fw_lists_wanup(void);" in read("rc/rc.h"))
    check("nothing in use: the list sources are NOT added to the do-not-block lists", "SEED listsrc" not in err, err)

    # ================= 4. lists.sh running =================
    b = os.path.join(td, "bin"); os.mkdir(b)
    sets = os.path.join(td, "sets"); web = os.path.join(td, "web"); os.mkdir(web)
    OUT = os.path.join(td, "out")
    IPSET = r'''#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]; d = os.environ["FAKE_SETS"]; os.makedirs(d, exist_ok=True)
open(os.environ["OUT"], "a").write("ipset " + " ".join(a) + "\n")
def p(n): return os.path.join(d, n)
def load(n):
    l = open(p(n)).read().split("\n"); return l[0], [x for x in l[1:] if x]
def store(n, h, e): open(p(n), "w").write(h + "\n" + "".join(x + "\n" for x in e))
bad = os.environ.get("FAKE_BAD", "")
c = a[0] if a else ""
if c == "list":
    n = a[-1]
    if not os.path.exists(p(n)): sys.exit(1)
    h, e = load(n); print("Name: %s\nType: hash:net\nHeader: %s\nNumber of entries: %d" % (n, h, len(e))); sys.exit(0)
if c == "create":
    n = a[1]; h = " ".join(x for x in a[2:] if x != "-exist")
    if os.path.exists(p(n)): sys.exit(0 if "-exist" in a else 1)
    store(n, h, []); sys.exit(0)
if c == "destroy":
    n = a[1]
    if not os.path.exists(p(n)) or os.path.exists(p(n) + ".inuse"): sys.exit(1)
    os.unlink(p(n)); sys.exit(0)
if c == "flush":
    n = a[1]
    if not os.path.exists(p(n)): sys.exit(1)
    store(n, load(n)[0], []); sys.exit(0)
if c == "restore":
    for l in sys.stdin.read().split("\n"):
        w = l.split()
        if len(w) != 3 or w[0] != "add": continue
        if w[2] == bad or not os.path.exists(p(w[1])): sys.exit(1)
        h, e = load(w[1])
        if w[2] not in e: e.append(w[2])
        store(w[1], h, e)
    sys.exit(0)
if c == "add":
    n, v = a[1], a[2]
    if v == bad or not os.path.exists(p(n)): sys.exit(1)
    h, e = load(n)
    if v not in e: e.append(v)
    store(n, h, e); sys.exit(0)
if c == "swap":
    x, y = a[1], a[2]
    if os.environ.get("FAKE_SWAP_FAIL") or not os.path.exists(p(x)) or not os.path.exists(p(y)): sys.exit(1)
    hx, ex = load(x); hy, ey = load(y); store(x, hy, ey); store(y, hx, ex); sys.exit(0)
if c == "rename":
    if not os.path.exists(p(a[1])) or os.path.exists(p(a[2])): sys.exit(1)
    os.rename(p(a[1]), p(a[2])); sys.exit(0)
if c == "save":
    n = a[1]
    if not os.path.exists(p(n)): sys.exit(1)
    h, e = load(n); print("create %s %s" % (n, h))
    for x in e: print("add %s %s" % (n, x))
    sys.exit(0)
sys.exit(0)
'''
    CURL = r'''#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]
if "--version" in a: sys.exit(0)
url = [x for x in a if x.startswith("http")][-1]; o = a[a.index("-o") + 1]
open(os.environ["OUT"], "a").write("curl " + " ".join(a) + "\n")
m = {}
for l in open(os.path.join(os.environ["FAKE_WEB"], "map")).read().split("\n"):
    if "\t" in l:
        u, f, rc = l.split("\t"); m[u] = (f, int(rc))
# -w '%{http_code}' (2026-11-24, REAPER-FW-LISTS-FAMILY): 200 when it arrived, 404 for a file the source does not have
# (curl -f exits 22), 000 when nothing answered
def hc(rc):
    if "-w" in a: sys.stdout.write("200" if rc == 0 else "404" if rc == 22 else "000")
if url not in m: hc(22); sys.exit(22)
f, rc = m[url]
if f: open(o, "w").write(open(os.path.join(os.environ["FAKE_WEB"], f)).read())
hc(rc)
sys.exit(rc)
'''
    for name, body in (("ipset", IPSET), ("curl", CURL),
                       ("logger", '#!/bin/sh\necho "logger $*" >> "$OUT"\n'),
                       ("cru", '#!/bin/sh\necho "cru $*" >> "$OUT"\n'),
                       ("nvram", '#!/bin/sh\n[ "$2" = rwarden_self ] && echo "${FAKE_SELF:-0}"\nexit 0\n'),
                       ("df", '#!/bin/sh\nif [ -n "$FAKE_DF" ]; then echo "Filesystem 1K-blocks Used Available Use% Mounted on"; echo "x 100 100 $FAKE_DF 50% /jffs"; else exec /bin/df "$@"; fi\n')):
        pth = os.path.join(b, name)
        with open(pth, "w", newline="\n") as fh: fh.write(body)
        os.chmod(pth, 0o755)
    # 2026-11-23: lists.sh runs under busybox awk when the host has one, as on the router. gawk / mawk accept things
    # busybox awk refuses: `a (x ? y : z)` is a call to a function a there (the Warden copy stopped at the first bare
    # address), and `^` needs CONFIG_FEATURE_AWK_LIBM.
    BBAWK = bool(shutil.which("busybox")) and subprocess.run(["busybox", "awk", "BEGIN { exit 0 }"], capture_output=True).returncode == 0
    if BBAWK:
        with open(os.path.join(b, "awk"), "w", newline="\n") as fh: fh.write('#!/bin/sh\nexec busybox awk "$@"\n')
        os.chmod(os.path.join(b, "awk"), 0o755)
    print("note: lists.sh runs under %s" % ("busybox awk (as on the router)" if BBAWK else "the host awk (no busybox here)"))

    V4 = "https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/%s/ipv4-aggregated.txt"
    V6 = "https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/%s/ipv6-aggregated.txt"
    RIPE = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS%s"
    HT = "https://api.hackertarget.com/aslookup/?q=AS%s"
    DENY4 = "https://www.ipdeny.com/ipblocks/data/aggregated/%s-aggregated.zone"
    DENY4B = "https://www.ipdeny.com/ipblocks/data/countries/%s.zone"
    DENY6 = "https://www.ipdeny.com/ipv6/ipaddresses/aggregated/%s-aggregated.zone"
    CV4 = "https://raw.githubusercontent.com/ipverse/country-ip-blocks/master/country/%s/ipv4-aggregated.txt"
    CV6 = "https://raw.githubusercontent.com/ipverse/country-ip-blocks/master/country/%s/ipv6-aggregated.txt"
    def webfile(name, text):
        with open(os.path.join(web, name), "w") as fh: fh.write(text)
        return name
    def webmap(table):
        with open(os.path.join(web, "map"), "w") as fh:
            for u, v in table.items():
                f, rc = v if isinstance(v, tuple) else (v, 0)
                fh.write("%s\t%s\t%d\n" % (u, f, rc))
    webfile("as2906.4", "# AS2906 (AS-SSI)\n# Netflix Streaming Services Inc.\n#\n23.246.0.0/18\n37.77.184.0/21\n45.57.0.0/17\n")
    webfile("as2906.6", "# AS2906 (AS-SSI)\n#\n2620:10c:7000::/44\n2A00:86C0::/32\n")
    webfile("ripe.json", '{"messages":[],"see_also":[],"version":"1.3","data_call_name":"announced-prefixes","cached":false,"data":{"prefixes":['
            '{"prefix":"23.246.0.0/18","timelines":[{"starttime":"2026-11-08T00:00:00","endtime":"2026-11-22T00:00:00"}]},'
            '{"prefix":"2a00:86c0::/32","timelines":[{"starttime":"2026-11-08T00:00:00","endtime":"2026-11-22T00:00:00"}]}],'
            '"query_starttime":"2026-11-08T00:00:00","resource":"2906","latest_time":"2026-11-22T00:00:00"},"query_id":"20261122-ab12",'
            '"process_time":120,"server_id":"app111","build_version":"main-2026.11.20","status":"ok","status_code":200,"time":"2026-11-22T23:10:00.123456"}')
    webfile("ht.txt", '"2906","AS-SSI, US"\n9.187.0.0/16\n2a00:86c0:2050::/48\n64.120.240.0/20\n')
    webfile("ht.limit", "API count exceeded - Increase Quota with Membership\n")
    webfile("evil.txt", "192.168.0.0/16\n10.0.0.0/8\n172.16.0.0/12\n100.64.0.0/10\n127.0.0.0/8\n169.254.0.0/16\n224.0.0.0/4\n0.0.0.0/0\n1.0.0.0/7\n"
            "300.1.1.0/24\n8.8.8.0/33\n8.8.8.8\n1.2.3.0/24;reboot\n$(id)/24\n203.0.113.0/24\nfe80::/10\nfc00::/7\nff00::/8\n::/0\n2000::/3\n"
            "::ffff:10.0.0.0/104\n12:34/56\n2001:db8:1::/48\n"
            # 2026-11-23: supernets that START outside a reserved range but hold one (192.0.0.0/8 holds 192.168.0.0/16,
            # 100.0.0.0/8 the carrier-NAT range); one with host bits set; and a real prefix right below multicast
            "192.0.0.0/8\n172.0.0.0/8\n100.0.0.0/8\n169.0.0.0/8\n172.31.0.0/8\n223.255.255.0/24\n")
    webfile("part.txt", "198.18.0.0/15\n")
    OCT = [i for i in range(1, 224) if i not in (10, 100, 127, 169, 172, 192)]
    webfile("wide.txt", "".join("%d.0.0.0/8\n" % i for i in OCT))           # 217 x /8: the whole public IPv4 space
    webfile("plaus.txt", "".join("%d.0.0.0/8\n" % i for i in OCT[:90]))     # 90 x /8 = 1.5 billion, about one big country

    def mk(obj, uses):
        g("lists", obj, uses=uses)
        return rd(LS)
    def run(mode, script=None, **envx):
        if script is not None:
            with open(LS, "w", newline="\n") as fh: fh.write(script)
        open(OUT, "w").close()
        env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), OUT=OUT, FAKE_SETS=sets, FAKE_WEB=web,
                   RFL_D=rfw, RFL_JFFS=jffs, RFL_MEMINFO=os.path.join(td, "meminfo"), **envx)
        p = subprocess.run([SH, LS, mode], capture_output=True, text=True, env=env, cwd=td)
        return rd(OUT), p
    def members(n):
        t = rd(os.path.join(sets, n)); return sorted(x for x in t.split("\n")[1:] if x)
    def mkset(n, entries=(), v6=False):
        os.makedirs(sets, exist_ok=True)
        with open(os.path.join(sets, n), "w") as fh:
            fh.write("hash:net %smaxelem 65536\n" % ("family inet6 " if v6 else "") + "".join(e + "\n" for e in entries))
    def fresh(names=("a1",)):
        shutil.rmtree(sets, ignore_errors=True); shutil.rmtree(jffs, ignore_errors=True)
        shutil.rmtree(os.path.join(rfw, "lists.w"), ignore_errors=True)
        for f in ("lists.status",):
            try: os.unlink(os.path.join(rfw, f))
            except OSError: pass
        os.makedirs(jffs)
        for n in names: mkset("rwfw_" + n); mkset("rwfw6_" + n, v6=True)
    def status():
        return rd(os.path.join(rfw, "lists.status")).splitlines()
    with open(os.path.join(td, "meminfo"), "w") as fh: fh.write("MemTotal: 2000000 kB\nMemAvailable: 1500000 kB\n")
    A1 = "a1>asn>AS2906"
    S_A1 = mk(A1, "a1")

    # --- a. the first source answers ---
    fresh(); webmap({V4 % 2906: "as2906.4", V6 % 2906: "as2906.6"})
    o, p = run("update")
    check("update: the list comes from ipverse, both families; no other source is asked",
          members("rwfw_a1") == ["23.246.0.0/18", "37.77.184.0/21", "45.57.0.0/17"] and members("rwfw6_a1") == ["2620:10c:7000::/44", "2a00:86c0::/32"]
          and "stat.ripe.net" not in o and "hackertarget" not in o, o + p.stderr)
    seq = [l for l in o.splitlines() if l.startswith("ipset ") and ("rwfx4" in l or "rwfw_a1" in l) and " list " not in l]
    check("update: the set is replaced whole - temporary set created, loaded, swapped in, removed; the live set is never flushed or destroyed",
          seq[-4:] == ["ipset create rwfx4 hash:net maxelem 65536", "ipset restore -exist", "ipset swap rwfx4 rwfw_a1", "ipset destroy rwfx4"][-4:]
          or [s for s in seq if "restore" not in s][-3:] == ["ipset create rwfx4 hash:net maxelem 65536", "ipset swap rwfx4 rwfw_a1", "ipset destroy rwfx4"], "\n".join(seq))
    check("update: no flush or destroy of the live sets", "ipset flush rwfw_a1" not in o and "ipset destroy rwfw_a1" not in o
          and "ipset flush rwfw6_a1" not in o and "ipset destroy rwfw6_a1" not in o, o)
    check("update: every download is https-pinned, size-capped and time-capped",
          all(("--proto =https --proto-redir =https" in l and "--max-filesize 4194304" in l and "--max-time 20" in l and " -f" in l.replace("-fsSL", " -f"))
              for l in o.splitlines() if l.startswith("curl ")), o)
    check("update: the list is saved per AS number and family, with its source",
          rd(os.path.join(cache, "as2906.4")) == "23.246.0.0/18\n37.77.184.0/21\n45.57.0.0/17\n"
          and rd(os.path.join(cache, "as2906.6")) == "2620:10c:7000::/44\n2a00:86c0::/32\n"
          and rd(os.path.join(cache, "as2906.meta")).split()[0] == "ipverse" and rd(os.path.join(cache, "as2906.meta")).split()[2:] == ["3", "2"])
    st = status()
    check("update: the status names the source, the counts and the loaded sets",
          any(re.match(r"K\|as2906\|ipverse\|\d+\|3\|2\|\d+\|ok\|ok\|-\|-$", l) for l in st) and "O|a1|asn|ok|3|ok|2" in st, "\n".join(st))
    ino = os.stat(os.path.join(cache, "as2906.4")).st_ino; mino = os.stat(os.path.join(cache, "as2906.meta")).st_ino
    o, p = run("update")
    check("update again, nothing changed: nothing is written under /jffs and the set is not rebuilt",
          os.stat(os.path.join(cache, "as2906.4")).st_ino == ino and os.stat(os.path.join(cache, "as2906.meta")).st_ino == mino
          and "ipset swap" not in o, o)

    # --- b. fallback order ---
    fresh(); webmap({RIPE % 2906: "ripe.json", HT % 2906: "ht.txt"})
    o, p = run("update")
    urls = [l.split()[-1] for l in o.splitlines() if l.startswith("curl ")]
    check("fallback: ipverse has nothing (404) - RIPEstat is asked next and its JSON is read; HackerTarget is not asked",
          urls == [V4 % 2906, V6 % 2906, RIPE % 2906] and members("rwfw_a1") == ["23.246.0.0/18"] and members("rwfw6_a1") == ["2a00:86c0::/32"]
          and any(re.match(r"K\|as2906\|ripestat\|.*\|ok\|http\|ok\|-$", l) for l in status()), o + "\n".join(status()))
    fresh(); webmap({RIPE % 2906: ("", 28), HT % 2906: "ht.txt"})
    o, p = run("update")
    urls = [l.split()[-1] for l in o.splitlines() if l.startswith("curl ")]
    check("fallback: RIPEstat cannot be reached - HackerTarget is the last resort, its header line is not taken for a prefix",
          urls == [V4 % 2906, V6 % 2906, RIPE % 2906, HT % 2906] and members("rwfw_a1") == ["64.120.240.0/20", "9.187.0.0/16"]
          and members("rwfw6_a1") == ["2a00:86c0:2050::/48"]
          and any(re.match(r"K\|as2906\|hackertarget\|.*\|ok\|http\|conn\|ok$", l) for l in status()), o + "\n".join(status()))

    # --- c. every source fails: last good stays ---
    before4 = members("rwfw_a1"); c4 = rd(os.path.join(cache, "as2906.4"))
    webmap({RIPE % 2906: ("", 7), HT % 2906: "ht.limit"})
    o, p = run("update", FAKE_SELF="1")
    check("all sources fail: the live set and the saved list stay as they were, and the log says which source said what",
          members("rwfw_a1") == before4 and rd(os.path.join(cache, "as2906.4")) == c4 and "ipset swap" not in o
          and "as2906: no source answered (http / conn / empty) - keeping the list already saved" in o, o)
    check("all sources fail, one unreachable, router-traffic filter on: the log names Warden's filter as a possible cause",
          "router-traffic filter is on" in o, o)
    check("all sources fail: the status keeps the saved list's source and shows the failed check",
          any(re.match(r"K\|as2906\|hackertarget\|.*\|fail\|http\|conn\|empty$", l) for l in status()), "\n".join(status()))
    o, p = run("update", FAKE_SELF="0")
    check("all sources fail, filter off: no Warden hint", "router-traffic filter" not in o, o)
    fresh(); webmap({})
    o, p = run("update")
    check("never fetched and nothing answers: the set stays empty, the log says nothing is loaded yet",
          members("rwfw_a1") == [] and "nothing loaded yet" in o and not os.path.exists(os.path.join(cache, "as2906.4")), o)

    # --- d. the filter ---
    fresh(); webmap({V4 % 2906: "evil.txt"})
    o, p = run("update")
    check("filter: private, reserved, over-wide and malformed entries never reach a set - only the real prefixes do (the text after one is cut off, never passed on)",
          members("rwfw_a1") == ["1.2.3.0/24", "203.0.113.0/24", "223.255.255.0/24"] and members("rwfw6_a1") == ["2001:db8:1::/48"], repr(members("rwfw_a1")) + repr(members("rwfw6_a1")) + o)
    check("filter: nothing but address/length tokens is ever passed to ipset", not re.search(r"reboot|\$\(|;", "\n".join(l for l in o.splitlines() if l.startswith("ipset"))), o)
    # (the width check goes too: unfiltered, this reply holds 0.0.0.0/0 and would be refused whole for that alone)
    mut = S_A1.replace("| flt4 |", "|").replace("&& $5 >= 8 &&", "&&").replace("if wide; then", "if false; then")
    fresh(); o, p = run("update", script=mut)
    check("MUTATION: with the IPv4 filter and the /8 floor taken out, private and over-wide prefixes load (so the check above is real)",
          mut != S_A1 and "192.168.0.0/16" in members("rwfw_a1") and "1.0.0.0/7" in members("rwfw_a1"), repr(members("rwfw_a1")))
    m_old = re.sub(r"flt4\(\) \{ awk .*?print \}'; \}", lambda _m: r"flt4() { grep -vE '^(0\.|10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.|22[4-9]\.|2[34][0-9]\.|25[0-5]\.)'; }", S_A1, flags=re.S)
    fresh(); o, p = run("update", script=m_old)
    check("MUTATION: with the old leading-octet filter, 192.0.0.0/8 and 100.0.0.0/8 load (so the overlap check above is real)",
          m_old != S_A1 and "192.0.0.0/8" in members("rwfw_a1") and "100.0.0.0/8" in members("rwfw_a1"), repr(members("rwfw_a1")))
    fresh(); webmap({V4 % 2906: "wide.txt", RIPE % 2906: "ripe.json"}); o, p = run("update", script=S_A1)
    check("too wide: a reply that adds up to the whole Internet is not used at all, the next source is asked, the status says why",
          members("rwfw_a1") == ["23.246.0.0/18"] and "as2906: a reply covers more than half of the Internet - not used" in o
          and any(re.match(r"K\|as2906\|ripestat\|.*\|ok\|wide\|ok\|-$", l) for l in status()), o + "\n".join(status()))
    mw = S_A1.replace("if wide; then", "if false; then")
    fresh(); o, p = run("update", script=mw)
    check("MUTATION: with the width check taken out the whole-Internet list loads", mw != S_A1 and len(members("rwfw_a1")) == len(OCT), len(members("rwfw_a1")))
    fresh(); webmap({V4 % 2906: "plaus.txt"}); o, p = run("update", script=S_A1)
    check("too wide: a large but plausible list (1.5 billion addresses, a big country) still loads", len(members("rwfw_a1")) == 90, o)

    # --- e. the cap, f. the memory guard ---
    fresh(); mkset("rwfw_a1", ["198.51.100.0/24"]); webmap({V4 % 2906: "as2906.4"})
    small = S_A1.replace("a1 asn 65536 as2906", "a1 asn 2 as2906")
    o, p = run("update", script=small)
    check("cap: a list larger than its set is refused whole - the set keeps what it had, the log and the status say too large",
          members("rwfw_a1") == ["198.51.100.0/24"] and "3 prefixes is over the limit of 2" in o and "ipset swap" not in o
          and any(l.startswith("O|a1|asn|big|") for l in status()), o + "\n".join(status()))
    mutc = small.replace('if [ "$_n" -gt "$_mx" ]; then', 'if false; then')
    fresh(); mkset("rwfw_a1", ["198.51.100.0/24"]); o, p = run("update", script=mutc)
    check("MUTATION: with the cap taken out the oversize list loads", mutc != small and len(members("rwfw_a1")) == 3, repr(members("rwfw_a1")))
    with open(os.path.join(td, "meminfo"), "w") as fh: fh.write("MemAvailable: 2 kB\n")
    fresh(); mkset("rwfw_a1", ["198.51.100.0/24"]); webmap({V4 % 2906: "as2906.4", V6 % 2906: "as2906.6"})
    big4 = "".join("11.%d.%d.0/24\n" % (i // 256, i % 256) for i in range(40)); webfile("big.4", big4); webmap({V4 % 2906: "big.4"})
    o, p = run("update", script=S_A1)
    check("memory guard: a list that would take more than a quarter of the free memory is not loaded; the set stays",
          members("rwfw_a1") == ["198.51.100.0/24"] and "not enough free memory" in o and any(l.startswith("O|a1|asn|mem|") for l in status()), o)
    with open(os.path.join(td, "meminfo"), "w") as fh: fh.write("MemTotal: 2000000 kB\nMemAvailable: 1500000 kB\n")
    o, p = run("fill")
    check("memory guard: a plain refill does not retry a refused list, the daily update does",
          "ipset create rwfx4" not in o, o)
    o, p = run("update")
    check("memory guard: with memory free again the daily update loads it", len(members("rwfw_a1")) == 40, o)

    # --- g. refill from flash, h. no needless rebuild ---
    fresh(); webmap({V4 % 2906: "as2906.4", V6 % 2906: "as2906.6"}); run("update")
    shutil.rmtree(sets); shutil.rmtree(os.path.join(rfw, "lists.w")); mkset("rwfw_a1"); mkset("rwfw6_a1", v6=True)
    o, p = run("fill")
    check("after a restart: the sets are refilled from the saved lists with no download at all",
          members("rwfw_a1") == ["23.246.0.0/18", "37.77.184.0/21", "45.57.0.0/17"] and len(members("rwfw6_a1")) == 2 and "curl" not in o, o)
    o, p = run("fill")
    check("refill again: a set that is loaded and unchanged is left alone (no temporary set, no swap)",
          "rwfx" not in o and "ipset swap" not in o and "curl" not in o, o)
    with open(os.path.join(cache, "as2906.4"), "a") as fh: fh.write("192.168.1.0/24\n10.1.0.0/16\n")
    mkset("rwfw_a1")
    o, p = run("fill")
    check("refill: a saved list is filtered again on the way in - an entry planted in the file does not reach the set",
          members("rwfw_a1") == ["23.246.0.0/18", "37.77.184.0/21", "45.57.0.0/17"], repr(members("rwfw_a1")))
    muts = S_A1.replace('ipset swap "$_t" "$_s" 2>/dev/null', "false")
    fresh(); mkset("rwfw_a1", ["198.51.100.0/24"]); os.unlink(os.path.join(sets, "rwfw_a1")); mkset("rwfw_a1", ["198.51.100.0/24"])
    open(os.path.join(sets, "rwfw_a1.inuse"), "w").close()
    o, p = run("update", script=muts)
    check("MUTATION: with the swap taken out a set a rule holds cannot be replaced at all (so the swap is what loads it)",
          muts != S_A1 and members("rwfw_a1") == ["198.51.100.0/24"] and "could not be replaced" in o, o)
    os.unlink(os.path.join(sets, "rwfw_a1.inuse"))
    fresh(); mkset("rwfw_a1", ["198.51.100.0/24"]); open(os.path.join(sets, "rwfw_a1.inuse"), "w").close()
    o, p = run("update", script=S_A1)
    check("a set a rule holds is replaced by the swap, in place", members("rwfw_a1") == ["23.246.0.0/18", "37.77.184.0/21", "45.57.0.0/17"], o)
    os.unlink(os.path.join(sets, "rwfw_a1.inuse"))

    # --- i. a family that goes away ---
    webmap({V4 % 2906: "as2906.4"})
    o, p = run("update")
    check("the AS stops announcing IPv6: its saved IPv6 list goes and the IPv6 set is emptied",
          not os.path.exists(os.path.join(cache, "as2906.6")) and members("rwfw6_a1") == [] and len(members("rwfw_a1")) == 3
          and any(re.match(r"K\|as2906\|ipverse\|\d+\|3\|0\|", l) for l in status()), o + "\n".join(status()))

    # --- j. two AS numbers in one list, one fails ---
    S_A2 = mk("a1>asn>AS2906,AS13335", "a1")
    webfile("as13335.4", "104.16.0.0/13\n23.246.0.0/18\n"); webmap({V4 % 2906: "as2906.4", V4 % 13335: "as13335.4"})
    fresh(); o, p = run("update")
    check("two AS numbers in one list: the set is their union, a prefix both carry once",
          members("rwfw_a1") == ["104.16.0.0/13", "23.246.0.0/18", "37.77.184.0/21", "45.57.0.0/17"], repr(members("rwfw_a1")))
    webmap({V4 % 2906: "as2906.4"})
    o, p = run("update")
    check("one of them fails later: its saved list still feeds the set (nothing is lost)",
          members("rwfw_a1") == ["104.16.0.0/13", "23.246.0.0/18", "37.77.184.0/21", "45.57.0.0/17"] and "as13335: no source answered" in o, o)

    # --- k. cleanup ---
    S_B = mk("b1>asn>AS13335", "b1")
    mkset("rwfw_b1"); mkset("rwfw6_b1", v6=True); webmap({V4 % 13335: "as13335.4"})
    o, p = run("update")
    check("a list that is no longer used: its saved files go, and the sets this script filled for it are freed",
          not os.path.exists(os.path.join(cache, "as2906.4")) and not os.path.exists(os.path.join(cache, "as2906.meta"))
          and os.path.exists(os.path.join(cache, "as13335.4")) and not os.path.exists(os.path.join(sets, "rwfw_a1"))
          and members("rwfw_b1") == ["104.16.0.0/13", "23.246.0.0/18"], o + repr(os.listdir(cache)))
    g("lists", "b1>asn>AS13335", uses="b1")           # regenerate, then the empty script (rc removes it after one run)
    empty = rd(LS)[:rd(LS).index("OBJS='\n")] + "OBJS='\n'\n" + rd(LS)[rd(LS).index("\n'\n") + 3:]
    o, p = run("fill", script=empty)
    check("nothing in use any more: saved lists, working files and status go, the set is freed",
          not os.path.exists(cache) and not os.path.exists(os.path.join(rfw, "lists.w")) and not os.path.exists(os.path.join(rfw, "lists.status"))
          and not os.path.exists(os.path.join(sets, "rwfw_b1")), o + p.stderr)

    # --- l. no room on /jffs ---
    fresh(); webmap({V4 % 2906: "as2906.4", V6 % 2906: "as2906.6"})
    o, p = run("update", script=S_A1, FAKE_DF="10")
    check("no room on /jffs: the list is kept in memory, the set is still loaded, the log says so once",
          len(members("rwfw_a1")) == 3 and not os.path.exists(os.path.join(cache, "as2906.4"))
          and os.path.exists(os.path.join(rfw, "lists.w", "c", "as2906.4")) and o.count("cannot be saved on /jffs") == 1, o)
    o, p = run("update")
    check("room again: the list moves to /jffs and the memory copy goes",
          os.path.exists(os.path.join(cache, "as2906.4")) and not os.path.exists(os.path.join(rfw, "lists.w", "c", "as2906.4")), o)

    # --- m. an oversize or broken download ---
    fresh(); webmap({V4 % 2906: ("part.txt", 63), RIPE % 2906: "ripe.json"})
    o, p = run("update")
    check("a download cut off by the size cap is thrown away whole (its part is not used); the next source is asked",
          "198.18.0.0/15" not in members("rwfw_a1") and members("rwfw_a1") == ["23.246.0.0/18"]
          and any(re.match(r"K\|as2906\|ripestat\|.*\|ok\|big\|ok\|-$", l) for l in status()), o + "\n".join(status()))

    # --- n. missing mode ---
    fresh(); webmap({V4 % 2906: "as2906.4"}); run("update")
    o, p = run("missing")
    check("missing mode: a list that has been fetched is not fetched again", "curl" not in o, o)
    fresh(); webmap({V4 % 2906: ("", 7), V6 % 2906: ("", 7), RIPE % 2906: ("", 28), HT % 2906: ("", 7)})
    o1, p = run("missing"); o2, p = run("missing")
    check("missing mode: a list nothing answers for is tried, then left alone for 10 minutes",
          o1.count("curl ") == 4 and "curl" not in o2, o1 + "----" + o2)
    check("missing mode: a list that has not arrived installs the 15-minute retry job",
          ("cru a reaper_fw_lists_retry */15 * * * * sh %s missing" % LS) in o1, o1)
    webmap({V4 % 2906: "as2906.4"})
    o3, p = run("wan")
    check("wan mode (the WAN came up): the list is asked for at once, without the 10-minute wait, and loads; the retry job goes",
          o3.count("curl ") == 2 and members("rwfw_a1") == ["23.246.0.0/18", "37.77.184.0/21", "45.57.0.0/17"]
          and "cru d reaper_fw_lists_retry" in o3 and "cru a reaper_fw_lists_retry" not in o3, o3)
    o4, p = run("wan")
    check("wan mode: a list already saved is not fetched again", "curl" not in o4, o4)

    # --- o. one update at a time ---
    fresh(); webmap({V4 % 2906: "as2906.4"})
    lk = os.path.join(rfw, "lists.lock")
    hold = subprocess.Popen(["flock", lk, "sleep", "2"])
    import time
    time.sleep(0.5)
    o, p = run("update")
    hold.wait()                                       # not kill: the sleep it started would keep the lock
    check("a second update while one runs does nothing", "curl" not in o and members("rwfw_a1") == [], o)

    # --- p. country lists ---
    S_G = mk("g1>geo>NL", "g1")
    fresh(names=("g1",)); mkset("rw_g_nl", ["31.3.96.0/21", "5.2.3.4"]); mkset("rw_g6_nl", ["2a02:a400::/25"], v6=True); webmap({})
    o, p = run("update", script=S_G)
    check("country list: Warden holds the country - its loaded set is copied, nothing is downloaded, a single address keeps its length",
          members("rwfw_g1") == ["31.3.96.0/21", "5.2.3.4/32"] and members("rwfw6_g1") == ["2a02:a400::/25"] and "curl" not in o
          and any(re.match(r"K\|cc_nl\|warden\|", l) for l in status()), o + "\n".join(status()))
    check("country list: Warden's own sets are only read", not re.search(r"ipset (flush|destroy|swap|add|create|restore).*rw_g6?_nl", o), o)
    webfile("nl.zone", "31.3.96.0/21\n37.0.0.0/15\n"); webfile("nl6.zone", "2a02:a400::/25\n"); webfile("nlv.txt", "# nl\n45.80.0.0/14\n")
    fresh(names=("g1",)); webmap({DENY4 % "nl": "nl.zone", DENY6 % "nl": "nl6.zone", CV4 % "nl": "nlv.txt"})
    o, p = run("update")
    urls = [l.split()[-1] for l in o.splitlines() if l.startswith("curl ")]
    check("country list: Warden does not hold it - ipdeny is asked, ipverse is not",
          urls == [DENY4 % "nl", DENY6 % "nl"] and members("rwfw_g1") == ["31.3.96.0/21", "37.0.0.0/15"]
          and any(re.match(r"K\|cc_nl\|ipdeny\|.*\|ok\|-\|ok\|-$", l) for l in status()), o + "\n".join(status()))
    fresh(names=("g1",)); webmap({DENY4B % "nl": "nl.zone"})
    o, p = run("update")
    check("country list: ipdeny's aggregated file is missing - its plain zone file is used", members("rwfw_g1") == ["31.3.96.0/21", "37.0.0.0/15"], o)
    fresh(names=("g1",)); webmap({CV4 % "nl": "nlv.txt"})
    o, p = run("update")
    check("country list: ipdeny has nothing - ipverse country blocks are the last resort",
          members("rwfw_g1") == ["45.80.0.0/14"] and any(re.match(r"K\|cc_nl\|ipverse\|.*\|ok\|-\|http\|ok$", l) for l in status()), o + "\n".join(status()))
    check("country list: the set is built with the country size", "ipset create rwfx4 hash:net maxelem 262144" in o, o)

    if "REAPER-FW-LISTS-FAMILY" in S_A1:              # 2026-11-24 (cut-readiness review)
        # --- q. one family's request fails: that family keeps its saved list ---
        fresh(); webmap({V4 % 2906: "as2906.4", V6 % 2906: "as2906.6"}); run("update", script=S_A1)
        c6 = rd(os.path.join(cache, "as2906.6"))
        webmap({V4 % 2906: "as2906.4", V6 % 2906: ("", 28)})
        o, p = run("update")
        check("IPv4 arrives, the IPv6 request times out: the saved IPv6 list and the IPv6 set stay as they were, the log says so",
              rd(os.path.join(cache, "as2906.6")) == c6 and len(members("rwfw6_a1")) == 2 and "ipset flush rwfw6_a1" not in o
              and "as2906: the IPv6 request did not answer - keeping the IPv6 list already saved" in o and len(members("rwfw_a1")) == 3, o)
        check("... and the saved list's counts still name both families", rd(os.path.join(cache, "as2906.meta")).split()[2:] == ["3", "2"],
              rd(os.path.join(cache, "as2906.meta")))
        mf = S_A1.replace('elif [ -n "$_kn" ]; then', "elif true; then")
        webmap({V4 % 2906: "as2906.4", V6 % 2906: "as2906.6"}); run("update", script=S_A1)
        webmap({V4 % 2906: "as2906.4", V6 % 2906: ("", 28)})
        o, p = run("update", script=mf)
        check("MUTATION: when a failed family counts as 'none', the saved IPv6 list goes and the IPv6 set is emptied (so the check above is real)",
              mf != S_A1 and not os.path.exists(os.path.join(cache, "as2906.6")) and members("rwfw6_a1") == [], o)
        # --- r. Warden holds the country's IPv4 but its IPv6 set is empty: download instead of copying half ---
        fresh(names=("g1",)); mkset("rw_g_nl", ["31.3.96.0/21"]); mkset("rw_g6_nl", [], v6=True)
        webmap({DENY4 % "nl": "nl.zone", DENY6 % "nl": "nl6.zone"})
        o, p = run("update", script=S_G)
        check("country list: Warden's IPv6 set is empty (perhaps its own fetch failed) - the list is downloaded, both families arrive",
              "curl" in o and members("rwfw6_g1") == ["2a02:a400::/25"] and any(re.match(r"K\|cc_nl\|ipdeny\|", l) for l in status()),
              o + "\n".join(status()))
        mg = S_G.replace(' && [ "$(cnt "rw_g6_$_n")" -gt 0 ] 2>/dev/null', "")
        fresh(names=("g1",)); mkset("rw_g_nl", ["31.3.96.0/21"]); mkset("rw_g6_nl", [], v6=True)
        o, p = run("update", script=mg)
        check("MUTATION: copying Warden's IPv4 alone leaves the list without IPv6 (so the check above is real)",
              mg != S_G and members("rwfw6_g1") == [] and "curl" not in o, o)
        # --- s. an AS every source answers with nothing: no endless retry ---
        webfile("ripe0.json", '{"data":{"prefixes":[]},"status":"ok"}')
        fresh(); webmap({RIPE % 2906: "ripe0.json", HT % 2906: "ht.limit"})
        o, p = run("missing", script=S_A1)
        wd = os.path.join(rfw, "lists.w")
        check("every source answers with no prefix: nothing is loaded and the 15-minute retry job is NOT installed",
              "nothing loaded yet" in o and "cru a reaper_fw_lists_retry" not in o and os.path.exists(os.path.join(wd, "e.as2906")), o)
        with open(os.path.join(wd, "r.as2906"), "w") as fh: fh.write("0 fail http empty empty\n")   # past the 10-minute wait
        o, p = run("missing")
        check("... the retry (missing mode) does not ask for it again", "curl" not in o, o)
        o, p = run("wan")
        check("... the WAN coming up still asks", o.count("curl ") == 4, o)
        webmap({V4 % 2906: ("", 7), V6 % 2906: ("", 7), RIPE % 2906: ("", 28), HT % 2906: ("", 7)})
        o, p = run("update")
        check("... a source that cannot be reached is not 'nothing': the marker goes and the retry job comes back",
              not os.path.exists(os.path.join(wd, "e.as2906")) and "cru a reaper_fw_lists_retry" in o, o)
        me = S_A1.replace(' || [ -f "$W/e.$_key" ] || _miss=1', " || _miss=1")
        fresh(); webmap({RIPE % 2906: "ripe0.json", HT % 2906: "ht.limit"})
        o, p = run("missing", script=me)
        check("MUTATION: without the marker the retry job is installed for it (so the check above is real)",
              me != S_A1 and "cru a reaper_fw_lists_retry" in o, o)
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
