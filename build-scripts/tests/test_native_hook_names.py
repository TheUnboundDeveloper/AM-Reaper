#!/usr/bin/env python3
"""Every appGet hook a Reaper page asks for is named exactly as httpd registers it.

WHY THIS EXISTS. httpd answers an appGet request hook by hook (httpd/web.c app_call): it cuts each hook at "(", looks the
name up in ej_handlers[] by EXACT match, and answers under "<name>-<first argument>" (get_clientlist* and the nvram
readers excepted). A name it does not have gets no answer at all - no error, no key. The stock pages hide this behind
httpApi.hookGet("name-arg"), which turns "name-arg" into the request "name(arg)". A native page that copied the stock
spelling straight into its request - "get_customized_attribute-<id>()" - was never answered: the Network page's guest
portal editor never read the stored sign-in page look, showed the built-in one, and every Apply on that network uploaded
the built-in look over the owner's (field report, v3.8.5 alpha, 2026-11-27). The page's test rig took the hook name as
"everything before (", so it accepted the wrong spelling.

WHAT IT DOES. For every Reaper-native page (www/Reaper_*.asp, the dashboard, the shell) and the kit scripts, it collects
the hook names each request is built from and checks each against the ej_handlers[] table of THIS tree's web.c (the
names under any build option count):
  - text written straight after "appGet.cgi?hook=" (split at %3B / ;),
  - a literal passed to encodeURIComponent() right after "hook=' +",
  - every string element of a call to a page helper that sends its list as the hook parameter (a function whose body
    holds "appGet.cgi?hook=" and does not build hooks out of its list - hooks([...]) ...), and of arrays joined into
    that parameter,
  - the literal a .map(function(k){ return '<name>(' ...}) builds hooks from on a hook-building line.
A literal is the text up to its closing quote; its name is what comes before "(" (a literal with no "(" that runs into
a concatenation - 'name-' + id + '()' - is a name with a dash, which httpd never has). Names built entirely at run time
are not seen; the page rigs cover those.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree with httpd/web.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:900] if detail else ""))
def rd(*p): return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

web = rd("httpd", "web.c")
a = web.find("struct ej_handler ej_handlers[] = {"); b = web.find("\n};", a)
REG = set(re.findall(r'\{\s*"([A-Za-z0-9_]+)"\s*,', web[a:b])) if a >= 0 else set()
check("web.c: the ej_handlers[] table is found and holds the hooks pages use (%d names)" % len(REG),
      len(REG) > 100 and {"nvram_get", "nvram_char_to_ascii", "get_clientlist", "get_customized_attribute"} <= REG)
# the app_call rule this test leans on: exact name match, answer key name-arg0
check("web.c app_call: a hook is found by its exact name and answered under name-arg0",
      "if (strcmp(handler->pattern, func) == 0){" in web and 'websWrite(stream,"\\"%s-%s\\":", func, argv[0]);' in web)

W = os.path.join(SRC, "www")
pages = sorted(f for f in os.listdir(W) if (f.startswith("Reaper_") and f.endswith(".asp")) or f in ("Main_ReaperDash.asp", "reaper_shell.asp"))
scripts = [os.path.join("reaper", f) for f in sorted(os.listdir(os.path.join(W, "reaper"))) if f.endswith(".js")] + ["reaper_util.js"]
LIT = r"""'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`"""

def name_of(lit):
    t = lit.replace("%28", "(").replace("%29", ")").strip()
    return t.split("(", 1)[0].strip()

def bracket(text, i):
    """the text of the [...] or (...) that opens at text[i]"""
    o = text[i]; c = {"[": "]", "(": ")", "{": "}"}[o]; d = 0; j = i
    while j < len(text):
        ch = text[j]
        if ch in "'\"`":
            q = ch; j += 1
            while j < len(text) and text[j] != q:
                j += 2 if text[j] == "\\" else 1
        elif ch == o: d += 1
        elif ch == c:
            d -= 1
            if d == 0: return text[i + 1:j]
        j += 1
    return ""

def elements(arr):
    """the string literal that starts each element of an array literal's text"""
    out = []
    for m in re.finditer(r"(?:^|,)\s*(?:" + LIT + ")", arr):
        out.append(next(g for g in m.groups() if g is not None))
    return out

found = {}      # name -> [file:what]
def note(f, lit, what):
    n = name_of(lit)
    if not n or n.startswith("<%") or re.match(r"^[\s+]", lit): return
    found.setdefault(n, []).append("%s: %s %r" % (f, what, lit[:60]))

for f in pages + scripts:
    p = os.path.join(W, f)
    if not os.path.isfile(p): continue
    t = open(p, encoding="utf-8", errors="surrogateescape").read()
    # 1. text written straight after hook=
    for m in re.finditer(r"appGet\.cgi\?hook=([^'\"`&\s]*)", t):
        for h in re.split(r"%3[Bb]|;", m.group(1)):
            if h and "(" in h.replace("%28", "("): note(f, h, "hook=")
    # 2. encodeURIComponent('...') right after hook=' +
    for m in re.finditer(r"hook=['\"`]\s*\+\s*encodeURIComponent\(\s*(?:" + LIT + ")", t):
        note(f, next(g for g in m.groups() if g is not None), "encodeURIComponent")
    # 3. helpers that send their list as the hook parameter, and every call of them with an array literal
    helpers = set()
    for m in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{", t):
        body = bracket(t, t.index("{", m.end() - 1))
        # a helper that builds hooks from its list (appGetAscii: setting names -> 'nvram_char_to_ascii(' + k + ...) takes
        # setting names, not hook names
        if "appGet.cgi?hook=" in body and ".map(" not in body and not re.search(r"['\"`][A-Za-z_]\w*\(['\"`]\s*\+", body):
            helpers.add(m.group(1))
    for h in helpers:
        for m in re.finditer(r"(?<![\w$.])" + re.escape(h) + r"\(\s*\[", t):
            for lit in elements(bracket(t, t.index("[", m.start()))): note(f, lit, h + "([...])")
    # arrays joined into the hook parameter: hook=' + X.join(  /  hook=' + encodeURIComponent(X.join(
    for m in re.finditer(r"hook=['\"`]?\s*\+\s*(?:encodeURIComponent\()?([A-Za-z_$][\w$]*)\.join\(", t):
        v = m.group(1)
        for am in re.finditer(r"(?<![\w$.])" + re.escape(v) + r"\s*=\s*\[", t):
            for lit in elements(bracket(t, t.index("[", am.start()))): note(f, lit, v + " = [...]")
        for pm in re.finditer(r"(?<![\w$.])" + re.escape(v) + r"\.push\(\s*(?:" + LIT + ")", t):
            note(f, next(g for g in pm.groups() if g is not None), v + ".push")
    # 4. hooks built by a map on a hook-building line
    for line in t.split("\n"):
        if not re.search(r"hook|appGet", line, re.I): continue
        for m in re.finditer(r"\.map\(function\s*\(\s*\w+\s*\)\s*\{\s*return\s+(?:" + LIT + ")", line):
            lit = next(g for g in m.groups() if g is not None)
            if not lit.startswith("<"): note(f, lit, "map")

bad = sorted("%s  <- %s" % (n, "; ".join(w[:3])) for n, w in found.items() if n not in REG)
dash = sorted(n for n in found if "-" in n)
check("every hook name a native page asks for is registered in this tree's web.c (%d names in %d pages/scripts)" % (len(found), len(pages) + len(scripts)),
      not bad, bad[:12])
check("no hook is asked for in the stock hookGet spelling name-arg (httpd has no name with a dash)", not dash, dash)
check("the scan is not vacuous: the Network page's own requests were seen",
      {"get_cfg_clientlist", "reaper_sdn_defer", "reaper_devnames", "get_customized_attribute"} <= set(found), sorted(found)[:40])
# the Network page reads the stored sign-in page look by the registered name and the answer key httpd writes
net = rd("www", "Reaper_Network.asp")
check("Network page: the stored look is asked for as get_customized_attribute(<id>), read under get_customized_attribute-<id>",
      "hooks(['get_customized_attribute(' + c.id + ')']" in net and "key = 'get_customized_attribute-' + c.id;" in net
      and "get_customized_attribute-' + c.id + '()'" not in net)
check("Network page: only a numeric id is asked for, and a look that could not be read is not uploaded",
      "if (!/^\\d{1,13}$/.test(String(c.id))){ FM.look[t] = 'failed'; return; }" in net and "if (r.upload && look) uploadLook(r.upload, send); else send();" in net)

print("\n%d failing" % len(fails))
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
