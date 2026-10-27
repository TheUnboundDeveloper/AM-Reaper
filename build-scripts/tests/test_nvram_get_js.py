#!/usr/bin/env python3
"""Settings reach page scripts as safe JS literals (BACKLOG "settings written into page scripts without escaping",
reviewed and remediated 2026-10-26).

WHY. httpd's <% nvram_get("k"); %> escapes " & < > (as &#NN) but writes ' and \\ as they are. Reaper pages wrote it
inside script strings - 349 reads of 229 settings in 44 files, plus two stock scripts a Reaper page loads - so a
stored value holding ' ended the string and the rest ran as code in the admin's browser (a crafted backup file, an
AiMesh node or the ASUS app can store one). Measured in a real browser on the mock with every one of those settings
hostile: 29 of 57 pages broken, injected code running on 25 (the shell and the dashboard among them).

WHAT IT DOES. Lifts httpd's reaper_js_literal() out of httpd/web.c, compiles it on the host and evaluates its output
under node for: quotes of all three kinds, backslash, ${}, </script>, controls, UTF-8 of 2/3/4 bytes, and invalid
UTF-8 (lone continuation, truncated, overlong, surrogate -> U+FFFD) - every result must be one string literal equal
to the input (or the U+FFFD form) with no raw ' " ` \\ < > $. Then source checks: nvram_get and nvram_get_js share one
lookup (ej_nvram_value: alias, band names, AiMesh CAP-private config, decrypted lists), the hook is registered, and no
script in a Reaper page / kit script (nor the two stock scripts) reads <% nvram_get( any more.
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:500] if detail else ""))
web = open(os.path.join(SRC, "httpd", "web.c"), encoding="utf-8", errors="replace").read()

a = web.index("char *reaper_js_literal(const char *s)")
fn = web[a:web.index("\n}\n", a) + 3]
gcc, node = shutil.which("gcc") or shutil.which("cc"), shutil.which("node")
if gcc and node:
    d = tempfile.mkdtemp()
    vectors = [b"", b"plain text 1.2.3", b"it's", b'say "hi"', b"back`tick ${alert(1)}", b"trail\\", b"a\\'b",
               b"</script><script>alert(1)</script>", b"tab\tnl\ncr\r", "Прошивка".encode(),
               "設定".encode(), "\U0001F600 ok".encode(), b"\x80lone", b"\xc3", b"\xe2\x82", b"\xc0\xaf",
               b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"&#60;b&#62;"]
    cvec = ",\n".join('{%s, %d}' % ('"' + "".join("\\x%02x" % c for c in v) + '"', len(v)) for v in vectors)
    harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
''' + fn + r'''
struct v { const char *s; int n; } V[] = {
''' + cvec + r'''
};
int main(void){ unsigned i; for (i = 0; i < sizeof(V)/sizeof(V[0]); i++) { char *o = reaper_js_literal(V[i].s); puts(o ? o : "NULL"); free(o); } return 0; }
'''
    c = os.path.join(d, "t.c"); open(c, "w").write(harness)
    exe = os.path.join(d, "t")
    r = subprocess.run([gcc, "-Wall", "-o", exe, c], capture_output=True, text=True)
    check("reaper_js_literal compiles on the host", r.returncode == 0, r.stderr[-400:])
    if r.returncode == 0:
        lits = subprocess.run([exe], capture_output=True, text=True).stdout.rstrip("\n").split("\n")
        check("one literal per input", len(lits) == len(vectors), len(lits))
        raw_ok = all(l.startswith('"') and l.endswith('"') and not re.search(r"['`<>$]|\\(?![xu])", l[1:-1]) and '"' not in l[1:-1] for l in lits)
        check("every literal is one double-quoted string with no raw ' \" ` \\ < > $ inside", raw_ok, [l for l in lits][:6])
        js = os.path.join(d, "e.js")
        open(js, "w").write("const L=[" + ",".join(lits) + "];console.log(JSON.stringify(L));")
        r2 = subprocess.run([node, js], capture_output=True, text=True)
        check("node evaluates all of them", r2.returncode == 0, r2.stderr[-300:])
        if r2.returncode == 0:
            got = json.loads(r2.stdout)
            exp = [v.decode("utf-8", "replace") for v in vectors]
            # Python's "replace" folds a whole bad sequence into one U+FFFD; the C side emits one per bad byte -
            # compare after collapsing runs of U+FFFD
            norm = lambda s: re.sub("�+", "�", s)
            bad = [(v, g) for v, g, e in zip(vectors, got, exp) if norm(g) != norm(e)]
            check("each evaluates back to the input (invalid UTF-8 as U+FFFD)", not bad, bad[:4])
    shutil.rmtree(d, ignore_errors=True)
else:
    print("note: no host C compiler or node - literal vectors skipped")

check("nvram_get and nvram_get_js share one lookup (ej_nvram_value)",
      web.count("ej_nvram_value(name, name_tmp, sizeof(name_tmp), config_buf, sizeof(config_buf), dec_passwd, sizeof(dec_passwd))") == 2
      and "is_cap_private_cfg(name_tmp)" in web[web.index("ej_nvram_value(char *name"):web.index("ej_nvram_get(int eid")])
check("the hook is registered", '{ "nvram_get_js", ej_nvram_get_js},' in web)

www = os.path.join(SRC, "www")
files = [os.path.join(www, f) for f in os.listdir(www) if (f.startswith("Reaper_") or f in ("Main_ReaperDash.asp", "reaper_shell.asp", "reaper_util.js")) and f.endswith((".asp", ".js"))]
files += [os.path.join(www, "reaper", f) for f in os.listdir(os.path.join(www, "reaper")) if f.endswith(".js")]
files += [os.path.join(www, "js", "https_redirect", "https_redirect.js"), os.path.join(www, "js", "httpApi.js")]
left, n_js = [], 0
for p in files:
    t = open(p, encoding="utf-8", errors="replace").read()
    n_js += t.count("nvram_get_js(")
    ranges = [(0, len(t))] if p.endswith(".js") else [(m.end(), (t.find("</script", m.end()) + 1 or len(t) + 1) - 1) for m in re.finditer(r"<script\b[^>]*>", t, re.I)]
    for m in re.finditer(r"<%\s*nvram_get\(", t):
        if any(x <= m.start() < y for x, y in ranges):
            left.append("%s:%d" % (os.path.relpath(p, www), t.count("\n", 0, m.start()) + 1))
check("no script in a Reaper page or kit script (or the two stock scripts) reads <% nvram_get( - nvram_get_js only",
      not left and n_js >= 330, (left[:10], n_js))
print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
