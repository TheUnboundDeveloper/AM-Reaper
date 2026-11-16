#!/usr/bin/env python3
"""Warden custom IP feeds: "$APIkey" in a feed's address (field request, 2026-11-15).

WHY. Wallguard's and Dreadwatch's sources take "$APIkey" where a supplier wants a key in the address; Warden's custom
IP feeds refused any "$". Now a feed's URL / IPv6 URL may carry the literal "$APIkey" after the host. The key is
write-only in /jffs/rwarden/cfkeys ("<place> <key>", place = the feed's place in rwarden_cfeeds), and update.sh
fetches such a feed through wallguard.sh's own fetch (one code path for the three tools), so the key reaches curl
only in a root-only -K config file. A feed without "$APIkey" is fetched exactly as before.

A feed has no slot number of its own, so httpd files the keys again with every save of the list: a feed keeps its
key when its name is unchanged and its addresses still point at a host the key was already sent to.

WHAT IT DOES.
  - rc: rw_valid_feedurl / rw_cfeed_fetch and the generator's custom-feed block compiled on the host; the generated
    text run under sh and busybox ash with the REAL wallguard.sh and a fake curl.
  - httpd: rw_cfkeys_save compiled on the host (set, clear, reorder, rename, host change, duplicate names, prune).
  - page: the address check run under node against the same table as rc's; the save posts cfkeys.
  - packs: RWDN_124 in all 25.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import glob, json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwarden.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
SH = "/bin/sh" if os.path.exists("/bin/sh") else shutil.which("sh")
BB = shutil.which("busybox")
CC = shutil.which("gcc") or shutil.which("cc")
NODE = shutil.which("node")
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
rw, web, page = rd("rc/rwarden.c"), rd("httpd/web.c"), rd("www/Reaper_Warden.asp")
WGSH = os.path.join(SRC, "wallguard", "wallguard.sh")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:700] if detail != "" else ""))

def cfun(src, name):
    m = re.search(r"\nstatic [a-z_ ]+\*?%s\([^)]*\)\n\{.*?\n\}\n" % name, src, re.S)
    return m.group(0) if m else ""

# the address table: rc and the page must agree on every row
LONG_OK = "https://a.example/" + "x" * (200 - 18)
LONG_KEY_OK = "https://a.example/" + "x" * (200 - 18 - 7) + "$APIkey"
URLS = [
    ("https://lists.example/ips.txt", 1), ("https://lists.example/ips?token=$APIkey", 1),
    ("https://lists.example/$APIkey/ips.txt", 1), ("https://lists.example/a?k=$APIkey&x=$APIkey", 1),
    ("https://lists.example/ips?token=$APIkey&fmt=cidr", 1), (LONG_OK, 1), (LONG_KEY_OK, 1),
    ("https://$APIkey.example/ips", 0), ("https://lists.example$APIkey/ips", 0), ("https://$APIkey/ips", 0),
    ("https://lists.example/ips?token=$APIke", 0), ("https://lists.example/ips?token=$apikey", 0),
    ("https://lists.example/ips?token=$", 0), ("https://lists.example/$(reboot)", 0), ("https://lists.example/${IFS}", 0),
    ("https://lists.example/a'b", 0), ("https://lists.example/a b", 0), ("https://lists.example/a;b", 0),
    ("https://user@lists.example/ips", 0), ("http://lists.example/ips?token=$APIkey", 0), ("https://", 0),
    (LONG_OK + "x", 0), (LONG_KEY_OK + "x", 0), ("https://a.example/" + "x" * (200 - 18 - 3) + "$APIkey", 0),
]

# ================================================================ rc
macros = dict(re.findall(r'#define\s+(RW_CFEED_\w+)\s+(\d+)', rw))
check("rc: the limits are unchanged (8 feeds, name 24, address 200)",
      macros == {"RW_CFEED_MAX": "8", "RW_CFEED_NAME_MAX": "24", "RW_CFEED_URL_MAX": "200"}, macros)
check("rc: the key file is a define beside Dreadwatch's", '#define RW_CF_KEYS   RW_CACHE "/cfkeys"' in rw and '#define RW_CACHE  "/jffs/rwarden"' in rw)
names = ("rw_field", "rw_valid_feedname", "rw_valid_feedurl", "rw_cfeed_fetch")
fns = [cfun(rw, n) for n in names]
a = rw.find('list = rw_list_get("cfeeds");'); b = rw.find("/* rebuild rw_threat / rw_threat6 atomically", a)
block = rw[a:rw.rfind("\n", a, b)] if 0 < a < b else ""
check("rc: the functions and the generator's custom-feed block are found", all(fns) and "rw_cfeed_fetch(fx, sizeof(fx), u4, nrec);" in block,
      [n for n, f in zip(names, fns) if not f])
check("rc: a keyed feed goes through wallguard.sh's fetch with the feed's place; a plain one through curl as before",
      "${RW_WGSH:-/usr/sbin/wallguard.sh} fetch $TMP '%s' '' \" RW_CF_KEYS \" custom%d </dev/null >/dev/null 2>&1" in fns[3]
      and "snprintf(out, sz, \"$CURLC '%s' -o $TMP 2>/dev/null\", url);" in fns[3])
gen = None
if CC and all(fns) and block:
    w = tempfile.mkdtemp(prefix="cfk_rc_")
    try:
        c = os.path.join(w, "t.c")
        open(c, "w").write(r'''#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <stdarg.h>
#define RW_CACHE "/jffs/rwarden"
#define RW_CF_KEYS RW_CACHE "/cfkeys"
#define RW_CFEED_MAX 8
#define RW_CFEED_NAME_MAX 24
#define RW_CFEED_URL_MAX 200
static const char *g_list;
static char *rw_list_get(const char *n) { (void)n; return g_list ? strdup(g_list) : NULL; }
static void logmessage(const char *t, const char *fmt, ...) { va_list ap; va_start(ap, fmt); fprintf(stderr, "%s: ", t); vfprintf(stderr, fmt, ap); fputc('\n', stderr); va_end(ap); }
''' + "".join(fns) + r'''
int main(int argc, char **argv) { char *list, *tok, *save = NULL; FILE *f = stdout; int i;
  if (!strcmp(argv[1], "url")) { for (i = 2; i < argc; i++) printf("%d", rw_valid_feedurl(argv[i])); printf("\n"); return 0; }
  g_list = argv[2];
  ''' + block + r'''
  return 0; }
''')
        exe = os.path.join(w, "t")
        r = subprocess.run([CC, "-Wall", "-Wextra", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
        check("rc: they compile on their own, no warning", r.returncode == 0 and not r.stderr.strip(), r.stderr[-900:])
        if r.returncode == 0:
            r = subprocess.run([exe, "url"] + [u for u, _ in URLS], capture_output=True, text=True)
            want = "".join(str(v) for _, v in URLS)
            check("rc: the address check - $APIkey only, whole, after the host, inside the 200 limit",
                  r.stdout.strip() == want, [u for (u, v), g in zip(URLS, r.stdout.strip()) if str(v) != g])
            LIST = ("<Plain>https://plain.example/ips.txt>"
                    "<bad name!>https://skipped.example/x>"
                    "<Keyed>https://keyed.example/v1/ips?token=$APIkey>https://keyed.example/v1/ips6?token=$APIkey"
                    "<NoKey>https://nokey.example/ips?k=$APIkey>"
                    "<Down>https://down.example/$APIkey/ips>"
                    "<BadUrl>https://$APIkey.example/ips>")
            r = subprocess.run([exe, "gen", LIST], capture_output=True, text=True)
            gen = r.stdout
            check("rc: the plain feed's text is what it was before this change, byte for byte",
                  gen.startswith("if $CURLC 'https://plain.example/ips.txt' -o $TMP 2>/dev/null; then\n"
                                 "  grep -oE '([0-9]{1,3}\\.){3}[0-9]{1,3}(/[0-9]{1,2})?' $TMP | rw_f4 >> $NEW\n"
                                 "  OK=1\nelse\n  logger -t rwarden \"custom feed fetch FAILED: Plain\"\nfi\n"), gen[:400])
            check("rc: a feed's place counts every record (the skipped one too): Keyed is 3, NoKey 4, Down 5",
                  "fetch $TMP 'https://keyed.example/v1/ips?token=$APIkey' '' /jffs/rwarden/cfkeys custom3 " in gen
                  and "fetch $TMP 'https://keyed.example/v1/ips6?token=$APIkey' '' /jffs/rwarden/cfkeys custom3 " in gen
                  and "/jffs/rwarden/cfkeys custom4 " in gen and "/jffs/rwarden/cfkeys custom5 " in gen, gen)
            check("rc: an address with $APIkey in the host is skipped and logged", "$APIkey.example" not in gen and "BadUrl" in r.stderr, r.stderr)
            check("rc: the placeholder only ever sits inside single quotes", all(l.count("'") >= 2 for l in gen.splitlines() if "$APIkey" in l))
    finally:
        shutil.rmtree(w, ignore_errors=True)
elif not CC:
    print("note: no host C compiler - the rc and httpd functions were not run")

FAKECURL = r'''#!/bin/sh
echo "ARGS $*" >> "$WORK/curl.args"
out=; url=
while [ $# -gt 0 ]; do
  case "$1" in
    --version) exit 0 ;;
    -K) cat "$2" >> "$WORK/curl.cfg"; ls -l "$2" | cut -c1-10 >> "$WORK/curl.mode"
        cu=$(sed -n 's/^url = "\(.*\)"$/\1/p' "$2"); [ -n "$cu" ] && url=$cu; shift 2; continue ;;
    -o) out=$2; shift 2; continue ;;
    https://*) url=$1 ;;
  esac
  shift
done
echo "URL $url" >> "$WORK/curl.urls"
case "$url" in
  https://plain.example/*) printf '198.51.100.1\n198.51.100.0/24\n' > "$out" ;;
  https://keyed.example/v1/ips6*) printf '2001:db8:6::/48\n' > "$out" ;;
  https://keyed.example/*) printf '203.0.113.7\n' > "$out" ;;
  *) exit 6 ;;
esac
'''
if gen and os.path.isfile(WGSH):
    shells = [("sh", [SH])] + ([("ash", [BB, "ash"])] if BB else [])
    for tag, shell in shells:
        work = tempfile.mkdtemp(prefix="cfk_run_")
        try:
            binp, kt = os.path.join(work, "bin"), os.path.join(work, "kt")
            os.makedirs(binp); os.makedirs(kt)
            open(os.path.join(binp, "curl"), "w").write(FAKECURL); os.chmod(os.path.join(binp, "curl"), 0o755)
            keyf = os.path.join(work, "cfkeys")
            open(keyf, "w").write("3 S3cret/K+y=42\n"); os.chmod(keyf, 0o600)
            open(os.path.join(work, "wgwrap.sh"), "w").write('echo "$*" >> "$WORK/wgsh.args"\nexec %s %s "$@"\n' % (" ".join(shell), WGSH))
            body = gen.replace("/jffs/rwarden/cfkeys", keyf)
            sp = os.path.join(work, "run.sh")
            open(sp, "w").write('CURLC="curl -fsSL"\nTMP=%s/feed\nNEW=%s/new4; : > $NEW\nNEW6=%s/new6; : > $NEW6\nOK=0\n'
                                'rw_f4() { cat; }\nrw_f6() { cat; }\nlogger() { echo "$*" >> %s/log; }\n'
                                'RW_WGSH="%s %s/wgwrap.sh"\n' % (work, work, work, work, " ".join(shell), work) + body + 'echo "OK=$OK"\n')
            for nm, sh in (("sh -n", [SH, "-n"]),) + ((("ash -n", [BB, "ash", "-n"]),) if BB else ()):
                pn = subprocess.run(sh + [sp], capture_output=True, text=True)
                check("[%s] the generated text parses (%s)" % (tag, nm), pn.returncode == 0, pn.stderr)
            env = dict(os.environ, WORK=work, LC_ALL="C", PATH=binp + ":" + os.environ["PATH"], WALLGUARD_DIR=os.path.join(work, "wg"),
                       WALLGUARD_KEYTMP=kt, WALLGUARD_JFFS=os.path.join(work, "wgj"))
            p = subprocess.run(shell + [sp], capture_output=True, text=True, env=env, cwd=work, timeout=90)
            rf = lambda n: open(os.path.join(work, n)).read() if os.path.exists(os.path.join(work, n)) else ""
            args, cfg, urls, log, wg = rf("curl.args"), rf("curl.cfg"), rf("curl.urls"), rf("log"), rf("wgsh.args")
            check("[%s] the block runs" % tag, p.returncode == 0 and "OK=1" in p.stdout, p.stderr[-600:])
            check("[%s] the plain feed is fetched by curl with its address as an argument" % tag,
                  "https://plain.example/ips.txt -o" in args and "198.51.100.0/24" in rf("new4"), args)
            check("[%s] the keyed feed: the saved key goes into the address, %%-encoded, in the -K config" % tag,
                  'url = "https://keyed.example/v1/ips?token=S3cret%2FK%2By%3D42"' in cfg
                  and "URL https://keyed.example/v1/ips?token=S3cret%2FK%2By%3D42" in urls and "203.0.113.7" in rf("new4"), cfg)
            check("[%s] its IPv6 address gets the same key" % tag,
                  'url = "https://keyed.example/v1/ips6?token=S3cret%2FK%2By%3D42"' in cfg and "2001:db8:6::/48" in rf("new6"), cfg)
            check("[%s] the key is never in a command line or the log" % tag, "S3cret" not in args and "S3cret" not in log and "S3cret" not in wg, args)
            check("[%s] the config that carries it is the owner's alone and is removed" % tag,
                  set(rf("curl.mode").split()) == {"-rw-------"} and os.listdir(kt) == [], (rf("curl.mode"), os.listdir(kt)))
            check("[%s] wallguard.sh gets the address with the placeholder, the key file and the feed's place" % tag,
                  ("fetch %s/feed https://keyed.example/v1/ips?token=$APIkey  %s custom3" % (work, keyf)) in wg, wg)
            check("[%s] a feed with no key saved is not fetched and says so" % tag,
                  "nokey.example" not in urls and "custom feed has no API key saved, not fetched: NoKey" in log, log)
            check("[%s] a keyed feed with no key is told apart from a failed download" % tag,
                  "custom feed has no API key saved, not fetched: Down" in log and "FAILED: NoKey" not in log, log)
            open(keyf, "a").write("5 other-key\n")
            for n in ("curl.args", "curl.cfg", "curl.urls", "log", "wgsh.args", "curl.mode"):
                if os.path.exists(os.path.join(work, n)): os.unlink(os.path.join(work, n))
            p = subprocess.run(shell + [sp], capture_output=True, text=True, env=env, cwd=work, timeout=90)
            check("[%s] a download that fails is logged as failed, under the feed's own key" % tag,
                  "custom feed fetch FAILED: Down" in rf("log") and "URL https://down.example/other-key/ips" in rf("curl.urls"), rf("log") + rf("curl.urls"))
        finally:
            shutil.rmtree(work, ignore_errors=True)

# ================================================================ httpd
hn = ("sh_whole", "sh_key_ok", "src_key_line", "src_keys_ok", "rw_cf_host", "rw_cf_parse", "rw_cf_known_host", "rw_cfkeys_save")
hf = [cfun(web, n) for n in hn]
st = re.search(r"struct rw_cfrec \{[^}]*\};", web)
check("httpd: the key store's functions are there", all(hf) and st, [n for n, f in zip(hn, hf) if not f])
check("httpd: the key file is a define beside Dreadwatch's", '#define RW_CFKEYS   REAPER_RW_DIR "/cfkeys"' in web)
if CC and all(hf) and st:
    w = tempfile.mkdtemp(prefix="cfk_httpd_")
    try:
        c = os.path.join(w, "t.c")
        open(c, "w").write(r'''#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <unistd.h>
static char g_kf[512];
#define RW_CFKEYS g_kf
static char rjbuf[65536];
static char *rjf_get(const char *p, int *ex) { FILE *f = fopen(p, "r"); size_t n = 0; rjbuf[0] = 0; *ex = f != NULL;
  if (f) { n = fread(rjbuf, 1, sizeof(rjbuf) - 1, f); rjbuf[n] = 0; fclose(f); } return rjbuf; }
static int rjf_set(const char *p, const char *v, const char *tag) { FILE *f = fopen(p, "w"); (void)tag; if (!f) return -1; fputs(v, f); fclose(f); return 0; }
''' + st.group(0) + "\n" + "".join(hf) + r'''
int main(int argc, char **argv) { snprintf(g_kf, sizeof(g_kf), "%s", argv[1]);
  printf("%d\n", rw_cfkeys_save(argv[2], argv[3], argc > 4 ? argv[4] : NULL)); return 0; }
''')
        exe = os.path.join(w, "t")
        r = subprocess.run([CC, "-Wall", "-Wextra", "-o", exe, c], capture_output=True, text=True)
        check("httpd: they compile on their own, no warning", r.returncode == 0 and not r.stderr.strip(), r.stderr[-900:])
        if r.returncode == 0:
            kf = os.path.join(w, "cfkeys")
            A = "Alpha>https://a.example/l?k=$APIkey>"
            B = "Beta>https://b.example/ips.txt>"
            C = "Gamma>https://c.example/$APIkey/v4>https://c.example/$APIkey/v6"
            def save(old, new, upd=None, start=None):
                if start is None:
                    if os.path.exists(kf): os.unlink(kf)
                else:
                    open(kf, "w").write(start)
                r = subprocess.run([exe, kf, old, new] + ([upd] if upd is not None else []), capture_output=True, text=True)
                return r.stdout.strip(), (open(kf).read() if os.path.exists(kf) else "")
            L = "<" + A + "<" + B + "<" + C
            check("httpd: a typed key is filed under the feed's place", save(L, L, "1 KEY-A\n3 KEY-C") == ("0", "1 KEY-A\n3 KEY-C\n"))
            check("httpd: a save with nothing typed keeps the keys", save(L, L, None, "1 KEY-A\n3 KEY-C\n") == ("0", "1 KEY-A\n3 KEY-C\n"))
            check("httpd: feeds reordered - each key follows its feed",
                  save(L, "<" + C + "<" + B + "<" + A, None, "1 KEY-A\n3 KEY-C\n") == ("0", "1 KEY-C\n3 KEY-A\n"))
            check("httpd: a feed deleted - its key goes, the feed behind it keeps its own",
                  save(L, "<" + B + "<" + C, None, "1 KEY-A\n3 KEY-C\n") == ("0", "2 KEY-C\n"))
            check("httpd: a renamed feed loses its key",
                  save(L, "<" + A.replace("Alpha", "Alpha2") + "<" + B + "<" + C, None, "1 KEY-A\n3 KEY-C\n") == ("0", "3 KEY-C\n"))
            check("httpd: a feed pointed at another host loses its key (a key is never sent where it was not typed for)",
                  save(L, "<" + A.replace("a.example", "evil.example") + "<" + B + "<" + C, None, "1 KEY-A\n3 KEY-C\n") == ("0", "3 KEY-C\n"))
            check("httpd: another path on the same host keeps it; the host compares without case",
                  save(L, "<" + A.replace("a.example/l", "A.Example/v2/list") + "<" + B + "<" + C, None, "1 KEY-A\n3 KEY-C\n") == ("0", "1 KEY-A\n3 KEY-C\n"))
            check("httpd: an IPv6 address added on the same host keeps it, on another host loses it",
                  save("<" + A, "<Alpha>https://a.example/l?k=$APIkey>https://a.example/l6?k=$APIkey", None, "1 KEY-A\n") == ("0", "1 KEY-A\n")
                  and save("<" + A, "<Alpha>https://a.example/l?k=$APIkey>https://other.example/l6?k=$APIkey", None, "1 KEY-A\n") == ("0", ""))
            check("httpd: the placeholder taken out of the address - the key goes",
                  save(L, "<Alpha>https://a.example/l><" + B + "<" + C, None, "1 KEY-A\n3 KEY-C\n") == ("0", "3 KEY-C\n"))
            check("httpd: two feeds of one name - a key is not guessed between them",
                  save("<" + A + "<" + B, "<" + A + "<" + A, None, "1 KEY-A\n") == ("0", "")
                  and save("<" + A + "<" + A, "<" + A + "<" + B, None, "1 KEY-A\n") == ("0", ""))
            check("httpd: '-' clears one key; a typed key replaces the old one, wherever the feed went",
                  save(L, L, "1 -", "1 KEY-A\n3 KEY-C\n") == ("0", "3 KEY-C\n")
                  and save(L, "<" + C + "<" + A, "2 NEW-A", "1 KEY-A\n3 KEY-C\n") == ("0", "1 KEY-C\n2 NEW-A\n"))
            check("httpd: a key typed for a feed that sends none, or for no feed, is not kept",
                  save(L, L, "2 KEY-B\n7 KEY-X") == ("0", ""))
            check("httpd: a line that is not valid stops the save - nothing is written",
                  save(L, L, "1 has space", "1 KEY-A\n") == ("-1", "1 KEY-A\n") and save(L, L, '1 q"uote', "1 KEY-A\n") == ("-1", "1 KEY-A\n")
                  and save(L, L, "9 KEY", "1 KEY-A\n") == ("-1", "1 KEY-A\n") and save(L, L, "1 a$b", "1 KEY-A\n") == ("-1", "1 KEY-A\n"))
            check("httpd: a record rc skips still counts for the place (the numbering is rc's)",
                  save("", "<bad name!>https://x.example/l<" + A, "2 KEY-A") == ("0", "2 KEY-A\n"))
            check("httpd: the list emptied - the key file is removed", save(L, "", None, "1 KEY-A\n3 KEY-C\n") == ("0", "") and not os.path.exists(kf))
    finally:
        shutil.rmtree(w, ignore_errors=True)

h = web[web.find('if (!strcmp(action, "save_lists")) {'):]
h = h[:h.find('if (!strcmp(action, "dns_status")) {')]
check("httpd save: the keys are checked before anything is written",
      0 < h.find("if (!src_keys_ok(cfk)) {") < h.find('rw_list_set("dnssrc", clean)') and h.find("if (!src_keys_ok(cfk)) {") < h.find("rw_list_set(names[i], v)"))
check("httpd save: the keys are filed again at once after the feed list is stored, against the list as it was",
      re.search(r'cf_old = is_cf \? rw_list_get\("cfeeds"\) : NULL;\n\t+if \(rw_list_set\(names\[i\], v\) != 0\) \{.*?\n\t+\}\n\t+if \(is_cf\) \{\n\t+int kr = rw_cfkeys_refile\(cf_old \? cf_old : "", cfk\);', h, re.S) is not None)
check("httpd: the page learns only which places have a key",
      'if (!strcmp(name, "dnskeys") || !strcmp(name, "cfkeys")) {' in web and 'rjf_get(!strcmp(name, "cfkeys") ? RW_CFKEYS : RDW_KEYS, &ex)' in web)
ia, ib = web.find('{ "warden", "rwarden_cfeeds",'), web.find('{ "warden", "rwarden_cfkeys",')
check("settings file: the keys travel with the feeds, after them; a file with feeds and no keys clears this router's",
      0 < ia < ib and 'else if (!strcmp(nv, "rwarden_cfkeys")) f = RW_CFKEYS;' in web
      and "if (cf_src && !cf_keys) unlink(RW_CFKEYS);" in web
      and re.search(r'if \(!strcmp\(nv, "rwarden_cfkeys"\)\) \{.*?if \(!src_keys_ok\(v\)\)\n\t+return -1;\n\t+unlink\(RW_CFKEYS\);\n\t+return rw_cfkeys_refile\(NULL, v\) == 0 \? 0 : -1;', web, re.S) is not None)

# ================================================================ page
check("page: a key box per feed (write-only), the saved places from the router, the keys posted with the list",
      'class="cf-key" maxlength="200" autocomplete="new-password"' in page and "cfkeys: '<% rwarden_list(\"cfkeys\"); %>'," in page
      and "if(cfeeds.keys) lf.append('cfkeys', cfeeds.keys);" in page and "<#RWDN_124#>" in page)
pf = []
for n in ("rwCfeedUsesKey", "rwCfeedHost", "rwCfeedValidUrl", "rwCfeedValidKey", "rwCfeedKeeps"):
    m = re.search(r"\nfunction %s\(.*?\n(?=function |/\*)" % n, page, re.S)
    pf.append(m.group(0) if m else "")
cm = re.search(r"var CFEED_MAX = 8, CFEED_NAME_MAX = 24, CFEED_URL_MAX = 200;\nvar CFEED_URL_RE = [^\n]+\n", page)
check("page: the address functions are found", all(pf) and cm, [i for i, f in enumerate(pf) if not f])
if NODE and all(pf) and cm:
    js = cm.group(0) + "".join(pf) + r'''
var U = %s;
var o = {haskey: true, name: "Alpha", url: "https://a.example/l?k=$APIkey", url6: ""};
console.log(JSON.stringify({
  urls: U.map(function(u){ return rwCfeedValidUrl(u) ? 1 : 0; }),
  keys: ["KEY-A", "S3cret/K+y=42", "", "has space", 'q"uote', "a'b", "a`b", "a$b", "a" + String.fromCharCode(92) + "b", new Array(202).join("k")].map(function(k){ return rwCfeedValidKey(k) ? 1 : 0; }),
  keeps: [rwCfeedKeeps({rwOrig: o}, "Alpha", "https://A.example/v2?k=$APIkey", ""), rwCfeedKeeps({rwOrig: o}, "Alpha2", o.url, ""),
          rwCfeedKeeps({rwOrig: o}, "Alpha", "https://evil.example/l?k=$APIkey", ""), rwCfeedKeeps({rwOrig: o}, "Alpha", o.url, "https://a.example/6?k=$APIkey"),
          rwCfeedKeeps({rwOrig: o}, "Alpha", o.url, "https://b.example/6?k=$APIkey"), rwCfeedKeeps({rwOrig: null}, "Alpha", o.url, ""),
          rwCfeedKeeps({rwOrig: {haskey: false, name: "Alpha", url: o.url, url6: ""}}, "Alpha", o.url, "")]
}));
''' % json.dumps([u for u, _ in URLS])
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "p.js"); open(f, "w").write(js)
        r = subprocess.run([NODE, f], capture_output=True, text=True)
        try: o = json.loads(r.stdout)
        except Exception: o = None
        check("page: the functions run under node", o is not None, r.stderr or r.stdout)
        if o:
            check("page: its address check agrees with rc's on every row of the table",
                  o["urls"] == [v for _, v in URLS], [u for (u, v), g in zip(URLS, o["urls"]) if v != g])
            check("page: a key is 1-200 printable characters without space, quotes, backslash, backtick or $",
                  o["keys"] == [1, 1, 0, 0, 0, 0, 0, 0, 0, 0], o["keys"])
            check("page: 'key saved' is shown by the rule the router keeps a key by (same name, a known host)",
                  o["keeps"] == [True, False, False, True, False, False, False], o["keeps"])
elif not NODE:
    print("note: node not found - the page functions were not run")
check("page: no key typed and none kept (or two feeds of one name) -> the row is refused with the existing message; the place is the row's place in the saved list",
      "if(k ? !rwCfeedValidKey(k) : (seen[n] > 1 || !rwCfeedKeeps(r, n, u, u6))){ bad.push(n + ': ' + `<#RSHD_158#>`); continue; }" in page
      and "if(k && out.length < CFEED_MAX) keys.push((out.length + 1) + ' ' + k);" in page)

# ================================================================ packs
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if os.path.basename(p) != "temp.dict")
missing, same = [], []
en = ""
for p in packs:
    t = open(p, encoding="utf-8", errors="surrogateescape").read()
    m = re.search(r"^RWDN_124=(.*)$", t, re.M)
    if not m or m.group(1).count("$APIkey") != 2 or "https://example.com/list?key=$APIkey" not in m.group(1):
        missing.append(os.path.basename(p)); continue
    if os.path.basename(p) == "EN.dict": en = m.group(1)
for p in packs:
    t = open(p, encoding="utf-8", errors="surrogateescape").read()
    m = re.search(r"^RWDN_124=(.*)$", t, re.M)
    if m and os.path.basename(p) != "EN.dict" and m.group(1) == en: same.append(os.path.basename(p))
check("packs: RWDN_124 in all 25, with the placeholder and the example kept as typed", len(packs) == 25 and not missing, missing)
check("packs: each pack has its own text (none is the English line)", not same, same)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for x in fails: print("  " + x)
    sys.exit(1)
print("\nall checks passed")
