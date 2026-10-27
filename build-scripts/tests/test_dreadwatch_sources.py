#!/usr/bin/env python3
"""Dreadwatch sources: removable built-in rows, your own sources, API sources (owner, 2026-10-27).

WHY. The owner asked for Wallguard's customisation (2026-10-26) on Dreadwatch too: every list removable, the ones the
router sets up included, and your own lists imported as a text list at a web address or through a supplier's API.
/jffs/rwarden/dnssrc holds "hidden <row>" (basics = urlhaus phish c2 threatfox), "off <slot>" and "custom <slot>
<https-url> [options]" (Wallguard's grammar); the API keys are write-only in /jffs/rwarden/dnskeys. update.sh fetches
your sources through wallguard.sh's own fetch (one code path for both tools), so the key reaches curl only in a
root-only -K config file.

WHAT IT DOES.
  - update.sh: the threat-domain block lifted from rc/rwarden.c, run under sh and busybox ash with the REAL
    wallguard.sh (fetch action) and a fake curl: removed rows are never fetched and leave the list; your sources'
    names carry their own ids (custom<n>) in the table, after the built-in lists; a text list's hosts / adblock /
    dnsmasq / bare lines; a JSON answer's field; the key only in the -K config (never in an argument or the log);
    an unticked source is not fetched; bad lines are skipped and logged; a missing key is state "key" (the last
    download kept), an answer without the field is "failed"; a source deleted loses its download; a source's own
    host is never blocked; the boot rebuild knows the source ids.
  - wallguard.sh fetch action: refuses a bad id or argument count; the key file passed is the one read.
  - httpd: rdw_chk_src, src_keys_ok and src_keys_save compiled on the host (good / bad lines, key prune).
  - page / packs: the form and the save carry dnssrc / dnskeys; RDWT_65 in all 25 packs.
"""
import gzip, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwarden.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
SH = "/bin/sh" if os.path.exists("/bin/sh") else shutil.which("sh")
BB = shutil.which("busybox")
CC = shutil.which("gcc") or shutil.which("cc")
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
rw, web, wgsh, page = rd("rc/rwarden.c"), rd("httpd/web.c"), rd("wallguard/wallguard.sh"), rd("www/Reaper_Dreadwatch.asp")
WGSH = os.path.join(SRC, "wallguard", "wallguard.sh")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))

# ---- the C-literal lifter (test_warden_dns.py's)
def macros_of(src):
    m = {}
    for line in src.splitlines():
        mm = re.match(r'\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$', line)
        if not mm: continue
        name, rest = mm.group(1), re.sub(r"/\*.*?\*/", "", mm.group(2))
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"|([A-Za-z_][A-Za-z0-9_]*)', rest)
        if not parts or not any(s for s, _ in parts): continue
        val, okay = "", True
        for s, ident in parts:
            if ident:
                if ident in m: val += m[ident]
                else: okay = False; break
            else: val += s
        if okay: m[name] = val
    return m
def c_unescape(s):
    out, i = [], 0
    table = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "'": "'", "?": "?", "a": "\a", "r": "\r"}
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append(table.get(s[i + 1], "\\" + s[i + 1])); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)
def lift_body(body, macros):
    text = ""
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|(/\*.*?\*/)|([A-Za-z_][A-Za-z0-9_]*)', body, re.S):
        if m.group(1) is not None: text += c_unescape(m.group(1))
        elif m.group(3) is not None: text += c_unescape(macros.get(m.group(3), ""))
    return text
macros = macros_of(rw)
at = rw.find("# ---- threat domains")
block = lift_body(rw[rw.rfind("fputs(", 0, at) + 6:rw.find(", f);", at)], macros)
SPLIT = 'if [ "$(_nv rwarden_dns)" = 1 ]; then\n'
check("the threat-domain block lifts whole", block.startswith("# ---- threat domains") and SPLIT in block)
head_part, tail_part = block.split(SPLIT, 1); tail_part = SPLIT + tail_part
check("rwarden.c: the source ids, the sources file and the key file are defines",
      macros.get("RW_DCUST_STR") == "custom1 custom2 custom3 custom4 custom5 custom6 custom7 custom8"
      and macros.get("RW_DNS_SRC") == "/jffs/rwarden/dnssrc" and macros.get("RW_DNS_KEYS") == "/jffs/rwarden/dnskeys")
reb_at = rw.find("static const char rw_nx_rebuild_sh[] =")
rebuild_src = lift_body(rw[reb_at + len("static const char rw_nx_rebuild_sh[] ="):rw.find(";\n", reb_at)], macros)
check("boot rebuild: the table ids include your sources' slots (a name of theirs is never dropped at boot)",
      '--kids "urlhaus phish c2 crypto ransom certpl threatview threatfox other legacy custom1 custom2 custom3 custom4 custom5 custom6 custom7 custom8"' in rebuild_src)

MYLIST = ("# my own list\n0.0.0.0 hosts1.example\n||adblock1.example^\naddress=/dnsm.example/0.0.0.0\n"
          "server=/srv.example/1.1.1.1\nlocal=/loc.example/\nbare1.example\nmylist.example\n")
API = r'''{"query_status":"ok","data":[{"ioc":"Bad-Domain.example","ioc_type":"domain"},
 {"ioc":"https:\/\/evil.example.net\/x.exe","ioc_type":"url"},{"ioc":"203.0.113.9:443","ioc_type":"ip:port"}]}'''
FAKECURL = r'''#!/bin/sh
# fake curl for wallguard.sh: record the arguments and the -K config, answer by host from $FIX
echo "ARGS $*" >> "$WORK/wgcurl.log"
out=; url=
while [ $# -gt 0 ]; do
  case "$1" in
    --version) exit 0 ;;
    -K) cat "$2" >> "$WORK/wgcurl.cfg"; ls -l "$2" | cut -c1-10 >> "$WORK/wgcurl.mode"; shift 2; continue ;;
    -o) out=$2; shift 2; continue ;;
    https://*) url=$1 ;;
  esac
  shift
done
case "$url" in
  *mylist.example*) f=mylist.txt ;;
  *api.example*) f=${API_FILE:-api.json} ;;
  *) exit 6 ;;
esac
cp "$FIX/$f" "$out"
'''
HEAD = r'''
_nv() { cat "$NVDIR/$1" 2>/dev/null; }
logger() { printf "%s\n" "$*" >> "$LOGF"; }
curl() {
  o=""; u=""; p=""
  for a in "$@"; do [ "$p" = -o ] && o="$a"; case "$a" in https://*) u="$a";; esac; p="$a"; done
  case "$u" in *urlhaus*) id=urlhaus;; *phishing-filter*) id=phish;; *C2IntelFeeds*) id=c2;; *Prigent-Crypto*) id=crypto;; *blocklistproject*) id=ransom;; *) id=none;; esac
  echo "$u" >> "$WORK/fetched"
  cp "$FIX/$id.txt" "$o" 2>/dev/null || { printf 404; return 22; }; printf 200
}
CURL=curl
TMP=$WORK/feed.1
wallguardc() {
  echo "$*" >> "$WORK/wallguardc.calls"
  case "$1" in
    build) o=""; p=""; kf=""; kids=""; : > "$WORK/sc.tbl"
      for a in "$@"; do [ "$p" = --out ] && o="$a"; [ "$p" = --kfile ] && kf="$a"; [ "$p" = --kids ] && kids="$a"; p="$a"; done
      [ -n "$kf" ] && awk -v K="$kids" '{ L[NR] = $0 } END { n = split(K, ids, " "); for (i = 1; i <= n; i++) for (r = 1; r <= NR; r++) { split(L[r], x, " "); f = (x[1] == "-") ? "other" : x[1]; m = split(f, a, ","); for (j = 1; j <= m; j++) if (a[j] == ids[i]) print ids[i], x[2] } }' "$kf" >> "$WORK/sc.tbl"
      cp "$WORK/sc.tbl" "$o";;
  esac
  return 0
}
'''
NV = {"rwarden_dns": "1", "rwarden_dns_feeds": "urlhaus phish c2 threatfox crypto ransom", "lan_domain": "home.lan",
      "ddns_hostname_x": "", "ntp_server0": "pool.ntp.org", "ntp_server1": "", "dnspriv_rulelist": ""}
SRCFILE = "\n".join([
    "hidden basics", "hidden crypto",
    "custom 1 https://mylist.example/hosts.txt name=My%20list",
    "custom 2 https://api.example/v1/ name=TFox fmt=json:ioc method=post body=%7B%22q%22%3A1%7D hdr=Auth-Key",
    "custom 3 https://mylist.example/off.txt",
    "off 3",
    "custom 4 https://mylist.example/x name=a;reboot",
    'custom 5 https://mylist.example/"x',
    "custom 6 http://mylist.example/plain",
    "custom 1 https://dup.example/second", ""])

shells = [("sh", [SH])] + ([("ash", [BB, "ash"])] if BB else [])
for tag, shell in shells:
    work = tempfile.mkdtemp(prefix="dwsrc_")
    try:
        fix, nvd, binp = os.path.join(work, "fix"), os.path.join(work, "nv"), os.path.join(work, "bin")
        wtmp, wjffs, kt, wgd = (os.path.join(work, d) for d in ("tmp", "jffs", "kt", "wg"))
        for d in (fix, nvd, binp, wtmp, wjffs, kt, wgd): os.makedirs(d)
        open(os.path.join(fix, "ransom.txt"), "w").write("ransom1.example\n")
        open(os.path.join(fix, "urlhaus.txt"), "w").write("0.0.0.0 uh1.example\n")
        open(os.path.join(fix, "mylist.txt"), "w").write(MYLIST)
        open(os.path.join(fix, "api.json"), "w").write(API)
        open(os.path.join(fix, "nofield.json"), "w").write('{"data":[{"other":"x.example"}]}')
        open(os.path.join(binp, "curl"), "w").write(FAKECURL); os.chmod(os.path.join(binp, "curl"), 0o755)
        # a wrapper that records how update.sh calls wallguard.sh, then runs the real one under the shell on test
        open(os.path.join(work, "wgwrap.sh"), "w").write('echo "$*" >> "$WORK/wgsh.args"\nexec %s %s "$@"\n' % (" ".join(shell), WGSH))
        for k, v in NV.items(): open(os.path.join(nvd, k), "w").write(v)
        open(os.path.join(wjffs, "dnsallow"), "w").write("")
        srcp, keyp = os.path.join(wjffs, "dnssrc"), os.path.join(wjffs, "dnskeys")
        open(srcp, "w").write(SRCFILE)
        open(keyp, "w").write("2 S3cretKEY-42\n"); os.chmod(keyp, 0o600)
        logf = os.path.join(work, "logger.out")
        over = ('RW_DNSC=%s/dns.conf\nRW_DNSK=%s/dns.nx\nRW_DNSL=%s/dns.cache\nRW_DNSU=%s/dns.upd\nRW_DNSF=%s/dns.feeds\n'
                'RW_DNSH=/tmp/dreadwatch/dns.hits\nRW_DNSA=%s/dnsallow\nRW_DNS_CAP=200000\nRW_NXDIR=%s/nx\nRW_NXDB=%s/nx/threat.db\n'
                'RW_DNSKG=%s/dns.k.gz\nRW_DNSKS=%s/dns.k.sum\nRW_DNSN=%s/dns.count\nRW_DNS1=%s/dns.first\nRW_WALLGUARDC=wallguardc\n'
                'RW_DNSS=%s\nRW_DNSKEY=%s\nRW_WGSH="%s %s/wgwrap.sh"\n'
                % (wtmp, wjffs, wjffs, wtmp, wjffs, wjffs, wtmp, wtmp, wjffs, wjffs, wtmp, wtmp, srcp, keyp, shell[-1] if tag == "sh" else "busybox ash", work))
        env = dict(os.environ, NVDIR=nvd, LOGF=logf, FIX=fix, WORK=work, LC_ALL="C", PATH=binp + ":" + os.environ["PATH"],
                   WALLGUARD_DIR=wgd, WALLGUARD_KEYTMP=kt, WALLGUARD_JFFS=os.path.join(work, "wgj"))
        rf = lambda p: open(p).read() if os.path.exists(p) else ""
        def run(extra=None):
            for f in ("fetched", "wgcurl.log", "wgcurl.cfg", "wgcurl.mode", "wgsh.args", "wallguardc.calls"):
                p = os.path.join(work, f)
                if os.path.exists(p): os.unlink(p)
            if os.path.exists(logf): os.unlink(logf)
            sp = os.path.join(work, "run.sh")
            open(sp, "w").write(HEAD + head_part + over + tail_part + '\necho "DNS_CHANGED=$DNS_CHANGED"\n')
            p = subprocess.run(shell + [sp], capture_output=True, text=True, env=dict(env, **(extra or {})), cwd=work, timeout=90)
            kg = os.path.join(wjffs, "dns.k.gz")
            kl = gzip.open(kg, "rt").read().splitlines() if os.path.exists(kg) else []
            fm = {l.split()[0]: l.split() for l in rf(os.path.join(wjffs, "dns.feeds")).splitlines() if l.split()}
            return p, kl, fm, rf(logf)

        p, kl, fm, log = run()
        check("[%s] the block runs (rc %d)" % (tag, p.returncode), p.returncode == 0 and "DNS_CHANGED=1" in p.stdout, p.stderr[-600:])
        fetched = rf(os.path.join(work, "fetched"))
        check("[%s] removed built-in rows are never fetched (Reaper's Basics and Crypto), a kept one is" % tag,
              "urlhaus" not in fetched and "phishing" not in fetched and "C2Intel" not in fetched and "Prigent" not in fetched
              and "blocklistproject" in fetched, fetched)
        want = ["ransom ransom1.example", "custom1 hosts1.example", "custom1 adblock1.example", "custom1 dnsm.example",
                "custom1 srv.example", "custom1 loc.example", "custom1 bare1.example", "custom2 bad-domain.example", "custom2 evil.example.net"]
        check("[%s] your sources' names carry their own ids, after the built-in lists: hosts, adblock, dnsmasq and bare lines; "
              "the API's JSON field (a URL cut to its host, an address dropped); the source's own host never listed" % tag, kl == want, kl)
        calls = rf(os.path.join(work, "wallguardc.calls"))
        check("[%s] the table ids carry the eight source slots" % tag,
              "--kids urlhaus phish c2 crypto ransom certpl threatview threatfox other custom1 custom2 custom3 custom4 custom5 custom6 custom7 custom8" in calls, calls[-300:])
        cfg, cargs, wargs = rf(os.path.join(work, "wgcurl.cfg")), rf(os.path.join(work, "wgcurl.log")), rf(os.path.join(work, "wgsh.args"))
        check("[%s] the API key reaches curl only in its -K config (0600), never an argument of curl or wallguard.sh, never the log" % tag,
              'header = "Auth-Key: S3cretKEY-42"' in cfg and "S3cretKEY" not in cargs and "S3cretKEY" not in wargs and "S3cretKEY" not in log
              and rf(os.path.join(work, "wgcurl.mode")).startswith("-rw-------") and os.listdir(kt) == [], (cfg, cargs, wargs))
        check("[%s] the POST body went from a file, decoded, with a JSON content type" % tag,
              'data-binary = "@' in cfg and 'header = "Content-Type: application/json"' in cfg, cfg)
        check("[%s] wallguard.sh was called with the key FILE and the slot id" % tag,
              ("fetch %s/feed.1 https://api.example/v1/ name=TFox fmt=json:ioc method=post body=%%7B%%22q%%22%%3A1%%7D hdr=Auth-Key %s custom2" % (work, keyp)) in wargs, wargs)
        check("[%s] an unticked source is not fetched; a duplicate slot and bad lines are not either" % tag,
              "off.txt" not in cargs and "dup.example" not in cargs and "/x " not in cargs and "plain" not in cargs, cargs)
        check("[%s] bad lines are skipped and say why" % tag,
              "your source 4 has options that are not valid - skipped" in log and "your source 5 has characters that are not allowed - skipped" in log
              and "your source 6 has no https:// address - skipped" in log, log)
        check("[%s] per-list state: sources ok / off, removed rows off, no row for a skipped line" % tag,
              fm.get("custom1", [])[1:2] == ["1"] and fm.get("custom1", [])[6:7] == ["ok"] and fm.get("custom2", [])[6:7] == ["ok"]
              and fm.get("custom3", [])[1:2] == ["0"] and fm.get("custom3", [])[6:7] == ["off"]
              and fm.get("urlhaus", [])[6:7] == ["off"] and fm.get("crypto", [])[6:7] == ["off"] and fm.get("ransom", [])[6:7] == ["ok"]
              and "custom4" not in fm and "custom5" not in fm and "custom6" not in fm, fm)

        # the key is removed: state "key", no curl call, the last download kept
        os.unlink(keyp)
        p, kl2, fm, log = run()
        check("[%s] no key saved: the API is not called, state 'key', the log says why, the last download stays" % tag,
              p.returncode == 0 and "api.example" not in rf(os.path.join(work, "wgcurl.log")) and fm.get("custom2", [])[6:7] == ["key"]
              and "none is saved for it" in log and "custom2 bad-domain.example" in kl2, (fm.get("custom2"), log[-400:]))
        # the answer holds no such field
        open(keyp, "w").write("2 S3cretKEY-42\n"); os.chmod(keyp, 0o600)
        p, kl3, fm, log = run({"API_FILE": "nofield.json"})
        check("[%s] an answer without the field: state 'failed', the reason logged" % tag,
              fm.get("custom2", [])[6:7] == ["failed"] and "no names in the JSON field" in log, (fm.get("custom2"), log[-400:]))
        # a source deleted and the rows restored
        open(srcp, "w").write("custom 2 https://api.example/v1/ name=TFox fmt=json:ioc method=post body=%7B%22q%22%3A1%7D hdr=Auth-Key\n")
        p, kl4, fm, log = run()
        check("[%s] a deleted source loses its download and its names; restored rows are fetched again" % tag,
              not any(l.startswith("custom1 ") for l in kl4) and "custom1" not in fm and not os.path.exists(os.path.join(wtmp, "dns.conf.custom1.last"))
              and "urlhaus" in rf(os.path.join(work, "fetched")) and "urlhaus uh1.example" in kl4, (kl4, sorted(fm)))
        # no sources file at all: the old behaviour
        os.unlink(srcp)
        p, kl5, fm, log = run()
        check("[%s] no sources file: the built-in lists as before, no source rows" % tag,
              p.returncode == 0 and not any(k.startswith("custom") for k in fm) and "urlhaus uh1.example" in kl5, sorted(fm))

        # the fetch action itself
        r = subprocess.run(shell + [WGSH, "fetch", os.path.join(work, "o"), "https://api.example/v1/", "", keyp, "nope"], capture_output=True, text=True, env=env)
        r2 = subprocess.run(shell + [WGSH, "fetch", os.path.join(work, "o"), "https://api.example/v1/"], capture_output=True, text=True, env=env)
        check("[%s] wallguard.sh fetch refuses an id that is not custom1-8, and a short argument list" % tag, r.returncode == 2 and r2.returncode == 2)
        open(os.path.join(work, "otherkeys"), "w").write("7 OtherFileKey\n")
        open(os.path.join(work, "wgcurl.cfg"), "w").write("")
        r = subprocess.run(shell + [WGSH, "fetch", os.path.join(work, "o"), "https://api.example/v1/", "hdr=Auth-Key fmt=json:ioc", os.path.join(work, "otherkeys"), "custom7"],
                           capture_output=True, text=True, env=env)
        check("[%s] wallguard.sh fetch reads the key file it is handed (not Wallguard's own)" % tag,
              r.returncode == 0 and 'header = "Auth-Key: OtherFileKey"' in rf(os.path.join(work, "wgcurl.cfg")), (r.returncode, rf(os.path.join(work, "wgcurl.cfg"))))
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ---- httpd: the validators and the shared key store, compiled on the host
def cfun(name):
    m = re.search(r"\nstatic [a-z ]+\*?%s\([^)]*\)\n\{.*?\n\}\n" % name, web, re.S)
    return m.group(0) if m else ""
names = ("sh_whole", "sh_url", "sh_hex", "sh_pct", "sh_chk_opts", "sh_key_ok", "src_custom_slots", "src_key_line",
         "src_keys_ok", "src_keys_save", "rdw_chk_src")
fns = [cfun(n) for n in names]
rows = re.search(r"static const char \*rdw_rows\[\] = \{[^}]*\};", web)
check("httpd: the validators and the key store are there", all(fns) and rows, [n for n, f in zip(names, fns) if not f])
if CC and all(fns) and rows:
    w = tempfile.mkdtemp(prefix="dwchk_")
    try:
        c = os.path.join(w, "t.c")
        open(c, "w").write(r'''#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <unistd.h>
static char rjbuf[65536];
static char *rjf_get(const char *p, int *ex) { FILE *f = fopen(p, "r"); size_t n = 0; rjbuf[0] = 0; *ex = f != NULL;
  if (f) { n = fread(rjbuf, 1, sizeof(rjbuf) - 1, f); rjbuf[n] = 0; fclose(f); } return rjbuf; }
static int rjf_set(const char *p, const char *v, const char *tag) { FILE *f = fopen(p, "w"); (void)tag; if (!f) return -1; fputs(v, f); fclose(f); return 0; }
''' + rows.group(0) + "\n" + "".join(fns) + r'''
int main(int argc, char **argv) { char b[4096]; int i;
  if (!strcmp(argv[1], "save")) { printf("%d\n", src_keys_save(argv[2], argv[3], "t", argc > 4 ? argv[4] : NULL)); return 0; }
  for (i = 2; i < argc; i++) { snprintf(b, sizeof(b), "%s", argv[i]);
    printf("%d", !strcmp(argv[1], "keys") ? src_keys_ok(b) : rdw_chk_src(b)); }
  printf("\n"); return 0; }
''')
        exe = os.path.join(w, "t")
        r = subprocess.run([CC, "-Wall", "-o", exe, c], capture_output=True, text=True)
        check("httpd: they compile on their own", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            good = ["hidden basics", "hidden crypto", "hidden ransom", "hidden certpl", "hidden threatview", "off 1", "off 8",
                    "custom 1 https://lists.example/hosts.txt", "custom 8 https://lists.example/l name=My%20list fmt=list",
                    "custom 2 https://threatfox-api.abuse.ch/api/v1/ name=abuse.ch%20ThreatFox fmt=json:ioc method=post body=%7B%22query%22%3A%22get_iocs%22%2C%22days%22%3A7%7D hdr=Auth-Key"]
            bad = ["hidden urlhaus", "hidden hagezi_light", "hidden", "off 9", "off 0", "off 3x", "off 03", "custom 9 https://a.example/l",
                   "custom 01 https://a.example/l", "custom 1 http://a.example/l", "custom 1 https://a.example/l junk",
                   "custom 1 https://a.example/l name=%3Cb%3E", "custom 1 https://a.example/l name=A name=B", "custom 1 https://a.ex\"ample/l",
                   "custom1 https://a.example/l", "basics", "urlhaus"]
            r = subprocess.run([exe, "src"] + good, capture_output=True, text=True)
            check("httpd: every good sources line passes", r.stdout.strip() == "1" * len(good), list(zip(good, r.stdout.strip())))
            r = subprocess.run([exe, "src"] + bad, capture_output=True, text=True)
            check("httpd: every bad sources line is refused", r.stdout.strip() == "0" * len(bad), list(zip(bad, r.stdout.strip())))
            r = subprocess.run([exe, "keys", "", "3 abc123", "3 -", "3 abc\n4 def", "9 abc", "3 has space", "3", "x abc", '3 q"uote'], capture_output=True, text=True)
            check("httpd: key updates - well-formed lines pass, a bad slot, a space, a quote or a missing key are refused", r.stdout.strip() == "11110" + "0000", r.stdout)
            lf, kf = os.path.join(w, "dnssrc"), os.path.join(w, "dnskeys")
            open(lf, "w").write("hidden basics\ncustom 1 https://a.example/l\ncustom 3 https://b.example/l hdr=Auth-Key\n")
            open(kf, "w").write("1 OLDKEY\n5 GONEKEY\n")
            r = subprocess.run([exe, "save", kf, lf, "3 NEWKEY"], capture_output=True, text=True)
            check("httpd: a saved key is kept, a new one added, the key of a slot that is gone dropped", r.stdout.strip() == "0" and open(kf).read() == "1 OLDKEY\n3 NEWKEY\n", (r.stdout, open(kf).read()))
            r = subprocess.run([exe, "save", kf, lf, "1 -"], capture_output=True, text=True)
            check("httpd: '<slot> -' clears one key", r.stdout.strip() == "0" and open(kf).read() == "3 NEWKEY\n", open(kf).read())
            r = subprocess.run([exe, "save", kf, lf, "3 bad key"], capture_output=True, text=True)
            check("httpd: a bad update writes nothing", r.stdout.strip() == "-1" and open(kf).read() == "3 NEWKEY\n", (r.stdout, open(kf).read()))
            open(lf, "w").write("hidden crypto\n")
            r = subprocess.run([exe, "save", kf, lf], capture_output=True, text=True)
            check("httpd: no sources left - the key file is removed", r.stdout.strip() == "0" and not os.path.exists(kf), r.stdout)
    finally:
        shutil.rmtree(w, ignore_errors=True)
sv = web[web.find('if (!strcmp(action, "save_lists")) {'):]
sv = sv[:sv.find("websWrite(stream, \"{\\\"ok\\\":1,\\\"saved\\\":%d}\", saved);")]
check("httpd: the save checks the sources and the keys before it writes either, sources first, keys after",
      0 < sv.find("sh_lines(src, clean, RDW_SRC_MAX, rdw_chk_src)") < sv.find("!src_keys_ok(keys)") < sv.find('rw_list_set("dnssrc", clean)')
      < sv.find("src_keys_save(RDW_KEYS, RDW_SRC, \"rwarden\", keys)"))
ej = web[web.find("ej_rwarden_list(int eid"):]
ej = ej[:ej.find("\n}\n")]
check("httpd: the page reads the sources; of the keys only the slot numbers",
      'strcmp(name, "dnssrc")) return 0;' in ej and 'if (!strcmp(name, "dnskeys")) {' in ej and 'websWrite(wp, "%d", slot);' in ej
      and ej.count("websWrite(") == 3)
check("httpd: Wallguard's key save is the shared one", "return src_keys_save(SH_JFFS \"/keys\", SH_JFFS \"/lists\", \"wallguard\", upd);" in web)

# ---- the page and the packs
check("page: removable rows, the sources form, Restore, the save carries dnssrc (+ dnskeys only when a key was typed)",
      all(s in page for s in ('id="fa_basics"', 'id="srcform"', "function dwSrcOk(){", "function dwPaintSrc(){", "`<#CTL_restore#>`",
                              "lf.append('dnssrc', src);", "if(keys) lf.append('dnskeys', keys);", "rwarden_list(\"dnssrc\")", "rwarden_list(\"dnskeys\")"))
      and "DNS_ROWS" not in page)
check("page: pure ASCII", all(ord(ch) < 0x7f for ch in page))
packs = "BR CN CZ DA DE EN ES FI FR HU IT JP KR MS NL NO PL RO RU SL SV TH TR TW UK".split()
miss = [pk for pk in packs if not re.search(r"^RDWT_65=.*/jffs/rwarden/dnskeys", rd("www/%s.dict" % pk), re.M)]
check("RDWT_65 (the key hint, Dreadwatch's key file) in all 25 packs", not miss, miss)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
