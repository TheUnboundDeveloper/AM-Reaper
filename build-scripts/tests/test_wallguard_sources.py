#!/usr/bin/env python3
"""Wallguard sources: removable built-in lists, your own sources, API sources (owner, 2026-10-26).

WHY. Some list suppliers (abuse.ch) now serve their data only through an API: a POST with a body, a per-user key
in a header (Auth-Key) and a JSON answer. A custom source can now say so - method=post, body=, hdr=<header>,
fmt=json:<field> - and the key itself lives in /jffs/wallguard/keys (root 0600), never in the lists line, the page
or a command line: wallguard.sh hands it to curl in a root-only config file (-K) that is removed after the fetch.
A built-in list can be removed from the table ("hidden <id>") and restored.

WHAT IT DOES.
  - wallguard.sh: lifts pdec / json_names / fetch and runs them under sh and busybox ash with a fake curl that
    records its arguments and the config it was handed: the key reaches curl only through -K, the body goes as
    data-binary from a file, JSON bodies get a JSON content type, both temp files are gone afterwards and were
    0600; a JSON answer becomes names (a URL cut to its host, an address dropped, duplicates once); a source
    that needs a key with none saved returns 99 without calling curl; an answer with no such field returns 98;
    a plain source is fetched exactly as before; feed_ok refuses options on a preset and odd characters.
  - httpd: sh_chk_opts / sh_chk_list / sh_key_ok compiled on the host: every option form, hidden <preset>.
  - rc: a custom line's options reach the feeds file as a fifth field; a bad one is skipped and logged.
"""
import os, re, shutil, stat, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "wallguard", "wallguard.sh")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
sh, web, rc = rd("wallguard/wallguard.sh"), rd("httpd/web.c"), rd("rc/wallguard.c")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:500] if detail else ""))

def lift(fn):
    m = re.search(r"^%s\(\) \{\n.*?^\}\n" % fn, sh, re.S | re.M)
    return m.group(0) if m else ""
FN = lift("pdec") + lift("json_names") + lift("fetch") + lift("feed_ok")
check("pdec, json_names, fetch and feed_ok are in wallguard.sh", all(lift(f) for f in ("pdec", "json_names", "fetch", "feed_ok")))
check("update() fetches through fetch() and names the two new reasons",
      'fetch "$L/$id.new" "$url" "$c" "$opt" "$id"; fr=$?' in sh and "none is saved for it" in sh and "held no names" in sh)
check("every feeds reader takes the options field", sh.count("while read -r bit id url kind opt; do") == 4
      and "while read -r bit id url kind; do" not in sh)

FAKE = r'''#!/bin/sh
# fake curl: record the arguments and the -K config, answer from $F_ANSWER
echo "ARGS $*" >> "$W/curl.log"
while [ $# -gt 0 ]; do
  case "$1" in
    -K) cp "$2" "$W/last.cfg"; ls -l "$2" | cut -c1-10 > "$W/last.cfg.mode"
        b=$(sed -n 's/^data-binary = "@\(.*\)"$/\1/p' "$2"); [ -n "$b" ] && { cp "$b" "$W/last.body"; ls -l "$b" | cut -c1-10 > "$W/last.body.mode"; }
        shift 2; continue ;;
    -o) out=$2; shift 2; continue ;;
  esac
  shift
done
[ -n "$F_ANSWER" ] && cp "$F_ANSWER" "$out"
exit ${F_RC:-0}
'''
JSON = r'''{"query_status":"ok","data":[
 {"id":"1","ioc":"Bad-Domain.example","ioc_type":"domain"},
 {"id":"2","ioc":"https:\/\/evil.example.net\/path\/x.exe","ioc_type":"url"},
 {"id":"3","ioc":"203.0.113.9:443","ioc_type":"ip:port"},
 {"id":"4","ioc":"bad-domain.example","ioc_type":"domain"},
 {"id":"5", "ioc" : "user@mail.example.org:8080/a"}]}'''

shells = [["sh"]] + ([["busybox", "ash"]] if shutil.which("busybox") else [])
for shell in shells:
    tag = "ash" if shell[0] == "busybox" else "sh"
    W = tempfile.mkdtemp(prefix="wgsrc_")
    try:
        J, KT, BIN = os.path.join(W, "jffs"), os.path.join(W, "kt"), os.path.join(W, "bin")
        for d in (J, KT, BIN): os.makedirs(d)
        open(os.path.join(BIN, "curl"), "w").write(FAKE); os.chmod(os.path.join(BIN, "curl"), 0o755)
        open(os.path.join(W, "answer.json"), "w").write(JSON)
        open(os.path.join(W, "answer.txt"), "w").write("example.org\n")
        open(os.path.join(W, "nofield.json"), "w").write('{"data":[{"other":"x.example"}]}')
        def run(body, **env):
            sp = os.path.join(W, "run.sh")
            # busybox ash runs applets before PATH; curl is not an applet, but keep the fake first anyway
            open(sp, "w").write('J="%s"; KT="%s"\n%s\n%s' % (J, KT, FN, body))
            e = dict(os.environ, PATH=BIN + ":" + os.environ["PATH"], W=W, LC_ALL="C", **env)
            return subprocess.run(shell + [sp], capture_output=True, text=True, env=e, timeout=30)
        def reset():
            for f in ("curl.log", "last.cfg", "last.body", "last.cfg.mode", "last.body.mode", "out"):
                p = os.path.join(W, f)
                if os.path.exists(p): os.remove(p)
        rf = lambda f: open(os.path.join(W, f)).read() if os.path.exists(os.path.join(W, f)) else ""

        # an API source: POST + JSON body + Auth-Key + json:ioc
        open(os.path.join(J, "keys"), "w").write("2 S3cretKEY-42\n"); os.chmod(os.path.join(J, "keys"), 0o600)
        body_enc = "%7B%22query%22%3A%22get_iocs%22%2C%22days%22%3A7%7D"
        opts = "name=ThreatFox fmt=json:ioc method=post body=%s hdr=Auth-Key" % body_enc
        reset()
        r = run('fetch "$W/out" "https://api.example/v1/" "curl -fsSL" "%s" custom2; echo "rc=$?"' % opts, F_ANSWER=os.path.join(W, "answer.json"))
        cfg, args = rf("last.cfg"), rf("curl.log")
        check(tag + ": the API call succeeds", "rc=0" in r.stdout, r.stdout + r.stderr)
        check(tag + ": the key reaches curl only in its -K config, never in the arguments",
              'header = "Auth-Key: S3cretKEY-42"' in cfg and "S3cretKEY" not in args and " -K " in args, (cfg, args))
        check(tag + ": the body goes from a file, decoded, with a JSON content type",
              rf("last.body") == '{"query":"get_iocs","days":7}' and 'data-binary = "@' in cfg
              and 'header = "Content-Type: application/json"' in cfg, (rf("last.body"), cfg))
        check(tag + ": both temp files were 0600 and are gone", rf("last.cfg.mode").startswith("-rw-------")
              and rf("last.body.mode").startswith("-rw-------") and os.listdir(KT) == [], (rf("last.cfg.mode"), os.listdir(KT)))
        names = rf("out").split()
        check(tag + ": the JSON answer becomes names: domains, a URL's host, no address, once each",
              names == ["bad-domain.example", "evil.example.net", "mail.example.org"], names)

        # a key-needing source with no key saved: no curl call
        os.remove(os.path.join(J, "keys")); reset()
        r = run('fetch "$W/out" "https://api.example/v1/" "curl -fsSL" "%s" custom2; echo "rc=$?"' % opts, F_ANSWER=os.path.join(W, "answer.json"))
        check(tag + ": no saved key -> 99, curl never called", "rc=99" in r.stdout and rf("curl.log") == "", r.stdout + rf("curl.log"))
        # a key for another slot does not count
        open(os.path.join(J, "keys"), "w").write("3 OtherKey\n"); reset()
        r = run('fetch "$W/out" "https://api.example/v1/" "curl -fsSL" "%s" custom2; echo "rc=$?"' % opts, F_ANSWER=os.path.join(W, "answer.json"))
        check(tag + ": another slot's key is not used", "rc=99" in r.stdout, r.stdout)

        # an answer with no such field
        reset()
        r = run('fetch "$W/out" "https://api.example/v1/" "curl -fsSL" "fmt=json:ioc" custom4; echo "rc=$?"', F_ANSWER=os.path.join(W, "nofield.json"))
        check(tag + ": no names in the field -> 98", "rc=98" in r.stdout, r.stdout)
        # a GET API source with a key: no body, no data-binary
        open(os.path.join(J, "keys"), "w").write("5 abc123\n"); reset()
        r = run('fetch "$W/out" "https://api.example/hosts.txt" "curl -fsSL" "hdr=Auth-Key" custom5; echo "rc=$?"', F_ANSWER=os.path.join(W, "answer.txt"))
        check(tag + ": a GET source sends only the header", "rc=0" in r.stdout and 'header = "Auth-Key: abc123"' in rf("last.cfg")
              and "data-binary" not in rf("last.cfg") and rf("out") == "example.org\n", (r.stdout, rf("last.cfg")))
        # a plain source: exactly the old call
        reset()
        r = run('fetch "$W/out" "https://lists.example/hosts" "curl -fsSL --max-time 25" "" custom1; echo "rc=$?"', F_ANSWER=os.path.join(W, "answer.txt"))
        check(tag + ": a plain source is fetched as before (no -K)", "rc=0" in r.stdout and " -K " not in rf("curl.log")
              and "-o %s/out https://lists.example/hosts" % W in rf("curl.log"), rf("curl.log"))
        # curl failing passes its status through, and cleans up
        reset()
        r = run('fetch "$W/out" "https://api.example/v1/" "curl -fsSL" "method=post body=x hdr=Auth-Key" custom5; echo "rc=$?"', F_RC="22")
        check(tag + ": curl's failure status comes back, temp files removed", "rc=22" in r.stdout and os.listdir(KT) == [], (r.stdout, os.listdir(KT)))
        # feed_ok
        r = run('feed_ok 20 custom1 https://x.example/l c "name=A fmt=list"; echo "a=$?"\n'
                'feed_ok 1 hagezi_light https://x.example/l p "name=A"; echo "b=$?"\n'
                'feed_ok 20 custom1 https://x.example/l c "name=A;rm"; echo "c=$?"\n'
                'feed_ok 20 custom1 https://x.example/l c ""; echo "d=$?"')
        check(tag + ": feed_ok: options on a custom line ok, on a preset or with odd characters refused",
              "a=0" in r.stdout and "b=1" in r.stdout and "c=1" in r.stdout and "d=0" in r.stdout, r.stdout)
    finally:
        shutil.rmtree(W, ignore_errors=True)

# ---- httpd validators
CC = shutil.which("gcc") or shutil.which("cc")
def cfun(name):
    m = re.search(r"\nstatic int %s\([^)]*\)\n\{.*?\n\}\n" % name, web, re.S)
    return m.group(0) if m else ""
fns = [cfun(n) for n in ("sh_whole", "sh_url", "sh_hex", "sh_pct", "sh_chk_opts", "sh_chk_list", "sh_key_ok")]
check("httpd: the validators are there", all(fns), [bool(f) for f in fns])
if CC and all(fns):
    w = tempfile.mkdtemp(prefix="wgchk_")
    try:
        c = os.path.join(w, "t.c")
        open(c, "w").write('#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n#include <ctype.h>\n'
                           'static const char *sh_presets[] = { "hagezi_light", "oisd_small", NULL };\n' + "".join(fns) + r'''
int main(int argc, char **argv) { char b[4096]; int i;
  for (i = 2; i < argc; i++) { snprintf(b, sizeof(b), "%s", argv[i]);
    printf("%d", !strcmp(argv[1], "key") ? sh_key_ok(b) : sh_chk_list(b)); }
  printf("\n"); return 0; }
''')
        exe = os.path.join(w, "t")
        r = subprocess.run([CC, "-Wall", "-o", exe, c], capture_output=True, text=True)
        check("httpd: the validators compile on their own", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            good = ["oisd_small", "hidden oisd_small", "custom 1 https://a.example/l",
                    "custom 2 https://api.example/v1/ name=Threat%20Fox fmt=json:ioc method=post body=%7B%22q%22%3A1%7D hdr=Auth-Key",
                    "custom 8 https://a.example/l fmt=list", "custom 3 https://a.example/l method=get"]
            bad = ["hidden nope", "custom 9 https://a.example/l", "custom 1 http://a.example/l",
                   "custom 1 https://a.example/l name=", "custom 1 https://a.example/l name=%3Cb%3E",
                   "custom 1 https://a.example/l fmt=json:", "custom 1 https://a.example/l fmt=json:a.b",
                   "custom 1 https://a.example/l method=put", "custom 1 https://a.example/l hdr=Auth:Key",
                   "custom 1 https://a.example/l body=%0A", "custom 1 https://a.example/l body=%zz",
                   "custom 1 https://a.example/l name=A name=B", "custom 1 https://a.example/l junk",
                   "custom 1 https://a.example/l body=" + "x" * 1025]
            r = subprocess.run([exe, "list"] + good, capture_output=True, text=True)
            check("httpd: every good line passes", r.stdout.strip() == "1" * len(good), r.stdout)
            r = subprocess.run([exe, "list"] + bad, capture_output=True, text=True)
            check("httpd: every bad line is refused", r.stdout.strip() == "0" * len(bad), list(zip(bad, r.stdout.strip())))
            r = subprocess.run([exe, "key", "abc123", "S3cret-Key_99", "has space", 'q"uote', "back\\slash", "dol$lar", "x" * 201, ""], capture_output=True, text=True)
            check("httpd: API keys - plain tokens pass; spaces, quotes, backslash, $ and over-long are refused",
                  r.stdout.strip() == "11000000", r.stdout)
    finally:
        shutil.rmtree(w, ignore_errors=True)
check("httpd: keys are write-only (config lists slots, never values) and follow the lists on save",
      '",\\"keys\\":["' in web and "sh_keys_save(get_cgi(\"keys\"))" in web and "live = src_custom_slots(listf);" in web)  # 2026-10-27: shared with Dreadwatch
check("rc: a custom line's options reach the feeds file; a bad one is skipped and logged",
      '"%d custom%d %s c%s%s\\n"' in rc and "its options are not valid - skipped" in rc)
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
