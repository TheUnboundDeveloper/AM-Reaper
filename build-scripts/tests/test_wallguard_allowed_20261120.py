#!/usr/bin/env python3
"""Wallguard: the Allowed tab - view and edit the allow / block lists, 24 h allows included (item 7, 2026-11-20).

WHY. The owner's test loop: a site breaks -> Fix a device -> Allow a few names for 24 h -> still broken -> allow more ->
once it works, take names off one at a time to find the one that matters and keep only that one. A 24 h allow could
not be removed or extended (only by waiting, or by hand on the router), and one that had run out stayed in the table
until the next build (the 05:15 update or a rule change) - up to ~35 h. Owner decision 2026-11-20: a sixth tab
"Allowed"; the Rules tab's text boxes stay.

WHAT IT DOES.
  - httpd (web.c): the helpers behind action=allow24 (op del / extend / keep) and action=myrules (list allow / block,
    op del / move) lifted and compiled on the host with stub nvram / files / notify: names checked with sh_name (bad
    name, empty, too many, duplicates, upper case), extend replaces in place (latest expiry + 24 h, at most 7 days,
    duplicates folded, a run-out entry renewed from now), keep = Never block first then off the 24 h list, move = the
    other list first then off this one, one rebuild per request and none when nothing changed, an audit line per name,
    POST only, an unreadable file never rewritten. The dispatch sits inside do_reaper_wallguard_cgi after reaper_gate.
  - rc: the 15-minute cron runs "fold expire" (wallguard.sh rebuilds once a 24 h allow has run out; the runtime test is
    in test_wallguard_sh.py).
  - page: the panel, the requests, the dirty-box refusal, the light config path; the list readers and the merge of a
    router-side change into the boxes run under node.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import json, os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")) or not os.path.isfile(os.path.join(SRC, "www", "Reaper_Wallguard.asp")):
    print("SKIP: no router tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
web, pg, rcw = rd("httpd/web.c"), rd("www/Reaper_Wallguard.asp"), rd("rc/wallguard.c")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:700] if detail != "" else ""))

def cfun(name):
    m = re.search(r"\nstatic (?:int|void) %s\([^)]*\)\n\{.*?\n\}\n" % name, web, re.S)
    return m.group(0) if m else ""

# ============================================================ httpd: pins
cg = re.search(r"\nstatic void\ndo_reaper_wallguard_cgi\(char \*url, FILE \*stream\)\n\{.*?\n\}\n", web, re.S)
cgb = cg.group(0) if cg else ""
check("CGI: allow24 / myrules dispatched inside do_reaper_wallguard_cgi, after reaper_gate",
      'if (!strcmp(action, "allow24") || !strcmp(action, "myrules")) {\n\t\tsh_edit_cgi(stream, action);' in cgb
      and cgb.find("reaper_gate()") < cgb.find("sh_edit_cgi(stream, action)"))
check("CGI: at most 100 names a request, +24 h, capped at 7 days",
      "#define SH_EDIT_MAX\t100" in web and "#define SH_A24_ADD\t86400" in web and "#define SH_A24_CAP\t(7 * 86400)" in web)
check("rc: the 15-minute cron fold asks for the expiry check",
      '"*/15 * * * * sh " SH_SCRIPT " fold expire"' in rcw and '"*/15 * * * * sh " SH_SCRIPT " fold");' not in rcw)

# ============================================================ httpd: the helpers on the host
CC = shutil.which("gcc") or shutil.which("cc")
NAMES = ("sh_name", "sh_names_split", "sh_names_find", "sh_names_edit", "sh_a24_edit", "sh_same", "sh_file_edit", "sh_edit_cgi")
fns = [cfun(n) for n in NAMES]
check("httpd: the helpers lift", all(fns), [n for n, f in zip(NAMES, fns) if not f])
if CC and all(fns):
    w = tempfile.mkdtemp(prefix="wgallow_")
    try:
        STUB = r'''#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include <stdarg.h>
#include <ctype.h>
#include <time.h>
#define SH_JFFS "./wg"
#define SH_LIST_MAX 16384
#define SH_EDIT_MAX 100
#define SH_A24_ADD 86400
#define SH_A24_CAP (7 * 86400)
static int reaper_req_post = 1;
static char CK[16][32], CV[16][20000]; static int cn;
static char *get_cgi(const char *k) { int i; for (i = 0; i < cn; i++) if (!strcmp(CK[i], k)) return CV[i]; return NULL; }
static char rjbuf[65536];
static char *rjf_get(const char *p, int *ex) { FILE *f; size_t n = 0; rjbuf[0] = 0;
  if (getenv("UNREADABLE") && strstr(p, getenv("UNREADABLE"))) { *ex = -1; return rjbuf; }
  f = fopen(p, "r"); *ex = f != NULL;
  if (f) { n = fread(rjbuf, 1, sizeof(rjbuf) - 1, f); rjbuf[n] = 0; fclose(f); while (n && rjbuf[n-1] == '\n') rjbuf[--n] = 0; } return rjbuf; }
static int rjf_set(const char *p, const char *v, const char *tag) { FILE *f = fopen(p, "w"); (void)tag; if (!f) return -1; fputs(v, f); fclose(f); printf("SET %s\n", p); return 0; }
static void notify_rc(const char *s) { printf("NOTIFY %s\n", s); }
static void reaper_audit(const char *a, const char *b, const char *c) { printf("AUDIT %s|%s|%s\n", a, b, c); }
static int websWrite(FILE *s, const char *fmt, ...) { va_list ap; int r; (void)s; va_start(ap, fmt); printf("JSON "); r = vprintf(fmt, ap); printf("\n"); va_end(ap); return r; }
'''
        MAIN = r'''
int main(int argc, char **argv) { int i;
  if (getenv("GET")) reaper_req_post = 0;
  if (!strcmp(argv[1], "unit")) {
    char v[20000], *nm[SH_EDIT_MAX], o[16384]; int n, h;
    snprintf(v, sizeof(v), "%s", argv[2]); n = sh_names_split(v, nm, SH_EDIT_MAX);
    printf("N %d\n", n); for (i = 0; i < n; i++) printf("NAME %s\n", nm[i]);
    if (n > 0 && argc > 4) {
      if (!strcmp(argv[3], "names")) { sh_names_edit(argv[4], nm, 1, nm + 1, n - 1, o, sizeof(o)); printf("OUT[%s]\n", o); }
      else { int r = sh_a24_edit(argv[4], nm, n, argv[3][0], atoll(argv[5]), o, sizeof(o), &h); printf("R %d HIT %d OUT[%s] SAME %d\n", r, h, o, sh_same(argv[4], o)); }
    }
    return 0;
  }
  for (i = 2; i < argc && cn < 16; i++) { char *e = strchr(argv[i], '='); if (!e) continue; *e = 0; snprintf(CK[cn], 32, "%s", argv[i]); snprintf(CV[cn++], 20000, "%s", e + 1); }
  sh_edit_cgi(stdout, argv[1]);
  return 0;
}
'''
        c = os.path.join(w, "t.c")
        open(c, "w").write(STUB + "".join(fns) + MAIN)
        exe = os.path.join(w, "t")
        r = subprocess.run([CC, "-Wall", "-Wextra", "-Wno-unused-parameter", "-o", exe, c], capture_output=True, text=True)
        check("httpd: the helpers compile on their own with -Wall -Wextra", r.returncode == 0 and "warning" not in r.stderr, r.stderr[-1500:])
        if r.returncode == 0:
            def unit(*a):
                return subprocess.run([exe, "unit"] + list(a), capture_output=True, text=True).stdout
            o = unit("Ads.Example.com,b.example,ads.example.com")
            check("names: lower case, each once", "N 2\nNAME ads.example.com\nNAME b.example\n" == o, o)
            bad = ["", ",", "a.example,bad name.example", "x", "a.example,-lead.example", "a.example\r\nX-Hdr: 1",
                   "a.example;reboot", "a.example/b", "a@b.example", 'a"b.example', "a.example,.lead.example",
                   ",".join("n%d.example" % i for i in range(101))]
            got = [unit(b).split("\n")[0] for b in bad]
            check("names: empty, bad characters, CR/LF, ; / @ quotes, a leading dot or dash, 101 names - refused",
                  all(g == "N -1" for g in got), list(zip(bad, got)))
            check("names: 100 distinct names pass", unit(",".join("n%d.example" % i for i in range(100))).startswith("N 100\n"))
            now = 1_000_000
            cur = "%d foo.example\n%d x.example\n%d foo.example\njunk line\n%d bar.example" % (now + 100, now + 200, now + 5000, now - 50)
            o = unit("foo.example,bar.example,none.example", "e", cur, str(now))
            check("a24 extend: one line per name where its first line was (latest expiry + 24 h; a run-out one from now), others kept, hit counts",
                  "R 0 HIT 2 OUT[%d foo.example\n%d x.example\njunk line\n%d bar.example\n] SAME 0" % (now + 5000 + 86400, now + 200, now + 86400) in o, o)
            o = unit("foo.example", "e", "%d foo.example" % (now + 7 * 86400 - 10), str(now))
            check("a24 extend: never past 7 days from now", "OUT[%d foo.example\n]" % (now + 7 * 86400) in o, o)
            o = unit("foo.example,none.example", "d", cur, str(now))
            check("a24 del: every line of the name goes, the rest (junk, other names, run-out ones) kept",
                  "R 0 HIT 1 OUT[%d x.example\njunk line\n%d bar.example\n]" % (now + 200, now - 50) in o, o)
            o = unit("none.example", "d", cur, str(now))
            check("a24 del of a name not there: the text is unchanged (sh_same)", "HIT 0" in o and o.strip().endswith("SAME 1"), o)
            o = unit("foo.example", "e", "%d FOO.example" % (now + 10), str(now))
            check("a24: names match whatever their case in the file", "HIT 1" in o, o)
            o = unit("gone.example,new.example,a.example", "names", "a.example\ngone.example # note\n\nb.example\nGONE.example")
            check("lists: the named lines go (first word, any case), empty lines go, new names appended once, present ones not twice",
                  "OUT[a.example\nb.example\nnew.example\n]" in o, o)

            def cgi(action, *kv, env=None, files=None):
                d = os.path.join(w, "run"); shutil.rmtree(d, ignore_errors=True); os.makedirs(os.path.join(d, "wg"))
                for k, v in (files or {}).items(): open(os.path.join(d, "wg", k), "w").write(v)
                rr = subprocess.run([exe, action] + list(kv), capture_output=True, text=True, cwd=d, env=dict(os.environ, **(env or {})))
                fs = {k: open(os.path.join(d, "wg", k)).read() for k in os.listdir(os.path.join(d, "wg"))}
                js = [l[5:] for l in rr.stdout.split("\n") if l.startswith("JSON ")]
                return (json.loads(js[0]) if js else None), rr.stdout, fs
            t = int(time.time())
            F = {"allow24": "%d keep.example\n%d other.example\n%d keep.example\n" % (t + 100, t + 200, t + 300), "allow": "mine.example\n", "block": "ads.example\n"}
            j, out, fs = cgi("allow24", "op=keep", "name=Keep.Example", files=F)
            check("allow24 keep: on Never block, off the 24 h list, one rebuild, one audit line, Never block written first",
                  j == {"ok": 1, "n": 1, "changed": 1} and fs["allow"] == "mine.example\nkeep.example\n" and fs["allow24"] == "%d other.example\n" % (t + 200)
                  and out.count("NOTIFY start_wallguard_rebuild") == 1 and "AUDIT wallguard|allow 24h made permanent|keep.example" in out
                  and out.find("SET ./wg/allow\n") < out.find("SET ./wg/allow24\n"), (j, out, fs))
            j, out, fs = cgi("allow24", "op=extend", "name=keep.example,other.example", files=F)
            lines = fs["allow24"].split("\n")
            check("allow24 extend: duplicates folded into one line in place, both extended, one rebuild, two audit lines",
                  j and j["ok"] == 1 and lines[0].endswith(" keep.example") and int(lines[0].split()[0]) == t + 300 + 86400
                  and lines[1].endswith(" other.example") and len([l for l in lines if l]) == 2 and out.count("NOTIFY") == 1 and out.count("AUDIT") == 2, (out, fs))
            j, out, fs = cgi("allow24", "op=del", "name=nobody.example", files=F)
            check("allow24 del of a name not there: ok, nothing written, no rebuild, no audit", j == {"ok": 1, "n": 1, "changed": 0}
                  and "SET" not in out and "NOTIFY" not in out and "AUDIT" not in out, out)
            j, out, fs = cgi("myrules", "list=allow", "op=move", "name=mine.example", files=F)
            check("myrules move: onto Always block first, then off Never block, one rebuild",
                  j and j["ok"] == 1 and fs["block"] == "ads.example\nmine.example\n" and fs["allow"] == ""
                  and out.find("SET ./wg/block\n") < out.find("SET ./wg/allow\n") and out.count("NOTIFY") == 1
                  and "AUDIT wallguard|never block moved to always block|mine.example" in out, (out, fs))
            j, out, fs = cgi("myrules", "list=block", "op=del", "name=ads.example", files=F)
            check("myrules del: off Always block, Never block untouched", j and j["ok"] == 1 and fs["block"] == "" and fs["allow"] == "mine.example\n"
                  and "always block removed" in out, (out, fs))
            refused = [cgi("allow24", "op=nuke", "name=keep.example", files=F), cgi("allow24", "op=del", files=F),
                       cgi("allow24", "op=del", "name=bad name", files=F), cgi("myrules", "list=adv", "op=del", "name=a.example", files=F),
                       cgi("myrules", "op=del", "name=a.example", files=F), cgi("myrules", "list=allow", "op=extend", "name=a.example", files=F),
                       cgi("allow24", "op=del", "name=keep.example", env={"GET": "1"}, files=F)]
            check("refused (RSHD_E2), nothing written: unknown op, no name, a bad name, an unknown list, no list, extend on My rules, a GET",
                  all(x[0] == {"ok": 0, "ek": "RSHD_E2"} and "SET" not in x[1] and "NOTIFY" not in x[1] for x in refused), [x[1] for x in refused])
            j, out, fs = cgi("allow24", "op=del", "name=keep.example", env={"UNREADABLE": "allow24"}, files=F)
            check("a list that exists but cannot be read is never rewritten (RSHD_E1)", j == {"ok": 0, "ek": "RSHD_E1"} and "SET" not in out
                  and fs["allow24"] == F["allow24"], out)
    finally:
        shutil.rmtree(w, ignore_errors=True)

# ============================================================ page
P = pg[pg.find('<div class="tab" id="tab_allowed"'):pg.find("<!-- ============================= DEVICES")]
scripts = "\n".join(re.findall(r"<script>(.*?)</script>", pg, re.S))
check("page: the Allowed panel - the 24 h table with select-all, filter, Remove selected / +24 h / Remove all, the two list tables",
      all(x in P for x in ('id="a24all"', 'id="a24body"', 'id="alfilter"', 'data-act="a24delsel"', 'data-act="a24extsel"', 'data-act="a24delall"',
                           'id="nbbody"', 'id="abbody"', "<#RSHD_42#>", "<#RSHD_221#>", "<#RSHD_222#>", "<#RSHD_217#>")))
check("page: the requests - action=allow24 op del / extend / keep, action=myrules list + op, names joined by commas in turns of 100",
      "shListOp({action: 'allow24', op: op}, names);" in pg and "shListOp({action: 'myrules', list: list, op: op}, [name]);" in pg
      and "p.name = left.splice(0, 100).join(',');" in pg and "shPost(p, function(j){" in pg)
check("page: a My rules box with unsaved edits blocks the changes that a later Save would undo (keep, Remove, Move)",
      "if(op === 'keep' && shRuleDirty('allow')){ alert(`<#RSHD_224#>`); shTab('rules'); return; }" in pg
      and "if(shRuleDirty('allow') || shRuleDirty('block')){ alert(`<#RSHD_224#>`); shTab('rules'); return; }" in pg)
check("page: allow24 / allow / block join the light config path (no unsaved edit elsewhere is lost) and the snapshot compares the boxes to the router",
      "var SH_LIGHT = {pause: 1, ss: 1, allow24: 1, allow: 1, block: 1};" in pg and "shLiveLists(j); shPaintPauses(); shPaintDevs();" in pg
      and "o.block = shRuleDirty('block') ? p.block : ''; o.allow = shRuleDirty('allow') ? p.allow : '';" in pg)
check("page: the Rules tab line keeps showing the running allows; the time left refreshes with the 15 s poll on the tab",
      "function shPaintA24Line(){" in pg and "shPaintA24Line(); shPaintAllowed();" in pg and "if(shCur === 'allowed') shPaintAllowed();" in pg)
newk = ["RSHD_%d" % k for k in (208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225)]
check("page: every new key used; inside the script only in template literals; ASCII only",
      all(("<#%s#>" % k) in pg for k in newk) and all(scripts.count("<#%s#>" % k) == scripts.count("`<#%s#>`" % k) for k in newk)
      and all(ord(ch) < 128 for ch in pg), [k for k in newk if ("<#%s#>" % k) not in pg])

def jsfun(name):
    i = pg.find("function %s(" % name)
    if i < 0: return ""
    j = pg.find("{", i); depth = 0
    for k in range(j, len(pg)):
        if pg[k] == "{": depth += 1
        elif pg[k] == "}":
            depth -= 1
            if depth == 0: return pg[i:k + 1]
    return ""
NODE = shutil.which("node")
js = [jsfun(n) for n in ("shA24", "shNames", "shLeft", "shRuleDirty", "shLiveLists")]
check("page: the list readers lift", all(js))
if NODE and all(js):
    now = int(time.time())
    prog = r'''
var EL = {allow: {value: ''}, block: {value: ''}}, painted = 0;
function $(id){ return EL[id]; }
function shPaintA24Line(){ painted++; } function shPaintAllowed(){ painted++; }
var cfg = {allow24: '', allow: '', block: ''};
''' + "\n".join(js).replace("`<#RSHD_223#>`", "'%1 h %2 min'") + r'''
var NOW = %d, out = {};
cfg.allow24 = (NOW + 600) + ' b.example\n' + (NOW - 5) + ' gone.example\n' + (NOW + 300) + ' a.example\njunk\n' + (NOW + 900) + ' b.example\n';
out.a24 = shA24();
out.names = shNames('X.example\n\n  y.example # c\nx.example\n');
out.left = shLeft(NOW + 3 * 3600 + 25 * 60 + 30);
cfg.allow = 'one.example\n'; cfg.block = 'ads.example\n';
EL.allow.value = 'one.example\n'; EL.block.value = 'ads.example\nmine.example\n';
out.dirty = [shRuleDirty('allow'), shRuleDirty('block')];
shLiveLists({allow: 'one.example\nunbreak.example\n', block: 'ads.example\nrouter.example\n', allow24: ''});
out.after = [EL.allow.value, EL.block.value, cfg.allow, cfg.block, painted, shRuleDirty('allow'), shRuleDirty('block')];
console.log(JSON.stringify(out));
''' % now
    r = subprocess.run([NODE, "-e", prog], capture_output=True, text=True)
    try:
        o = json.loads(r.stdout)
    except Exception:
        o = {}
    check("node: shA24 - running allows only, one per name (its latest expiry), soonest first, junk ignored",
          o.get("a24") == [{"n": "a.example", "t": now + 300}, {"n": "b.example", "t": now + 900}], (r.stderr[-500:], o.get("a24")))
    check("node: shNames - first word, lower case, once; shLeft - hours and minutes", o.get("names") == ["x.example", "y.example"]
          and o.get("left") == "3 h 25 min", o)
    check("node: shLiveLists - a clean box takes the router's list; a box with unsaved edits keeps them and gains the names the router added",
          o.get("dirty") == [False, True] and o.get("after") == ["one.example\nunbreak.example\n", "ads.example\nmine.example\nrouter.example\n",
                                                              "one.example\nunbreak.example\n", "ads.example\nrouter.example\n", 2, False, True], o)
elif not NODE:
    print("SKIP (node part): no node")

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
