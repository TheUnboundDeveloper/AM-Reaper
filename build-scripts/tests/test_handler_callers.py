#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every request address and every page hook httpd registers has a caller - or a written reason.

WHY THIS EXISTS. Review 2026-11-17 (B-28, B-29) found 79 rows of mime_handlers[] and about 100 names of
ej_handlers[] that no shipped page calls: parsers of admin input that no page test ever exercises. v3.8.4 removed
the worst of them (REAPER-UNUSED-V384, REAPER-UNUSED-V384B). This test stops the list growing back: a new row or
hook must be called by something that ships, or be entered in the allow-list beside this file with its reason.

WHAT COUNTS AS A CALLER.
  a request address (a mime_handlers[] row, e.g. "apply.cgi*")
    - its name in a shipped web file (the whole name: "get_x.cgi", not just "get_x"), or
    - its name as a link target in open C / shell code ("/page_default.cgi?url=..." in httpd.c), or
    - for a row that serves files (do_file / do_ej / an image handler, or a wildcard pattern): a shipped file the
      pattern matches, or the pattern's fixed tail (".CFG") in a shipped web file.
  a page hook (an ej_handlers[] name, e.g. "nvram_get")
    - <% name( ... ) %> in a shipped web file, or
    - the name in an appGet.cgi?hook= string, or as the start of a string literal (httpApi.hookGet("name")).
    A JavaScript function or variable of the same name is NOT a caller.
  Table entries are not callers: the AiMesh node whitelist, the exception list, the "file need not exist" list in
  httpd.c and comments name addresses without requesting them.

WHAT "SHIPPED" MEANS. Everything under www/ outside www/sysdep/, plus the sysdep folders the Makefile copies in for
the Reaper models (OVERLAYS), minus what an unconditional "rm -f / rm -rf $(INSTALLDIR)/www/..." line of www/Makefile
removes, minus the paths listed in handler_callers.unshipped (source files no Reaper image installs: the conditional
removals and the overlays of other brands, taken from the release images; a file missing from that list only makes
this test more lenient). Symbolic links are resolved.

THE ALLOW-LIST. handler_callers.allow: name <TAB> reason, one per line. A line whose name has a caller is stale and
fails (unless its reason carries "[not on every line]": the 3006.102.8 line ships pages the 102.10 line does not).
A line naming a row or hook this tree does not have is ignored (the three trees share one list).
Rows inside "#if 0" are never built and are skipped.

Exit 0 pass, 1 fail, 77 skipped (no router source tree).
Options: --list prints every name with its verdict (CALLED / ALLOWED / UNUSED) for a review;
         --model prints the shipped-file model (one path per line), to compare with an image's www.
"""
import fnmatch, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
LIST = "--list" in sys.argv
MODEL = "--model" in sys.argv
SRC = ARGS[0] if ARGS else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")) or not os.path.isdir(os.path.join(SRC, "www")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
HERE = os.path.dirname(os.path.abspath(__file__))
ALLOW = os.environ.get("REAPER_HANDLER_ALLOW", os.path.join(HERE, "handler_callers.allow"))
UNSHIPPED = os.environ.get("REAPER_HANDLER_UNSHIPPED", os.path.join(HERE, "handler_callers.unshipped"))

FAILS = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or not detail else ": " + str(detail)[:1500]))
    if not cond:
        FAILS.append(name)

def rd(*rel):
    with open(os.path.join(SRC, *rel), encoding="utf-8", errors="replace") as f:
        return f.read()

# ------------------------------------------------------------------------------------------------ the two tables
def strip_c_comments(s):
    """comments of one line out, string literals untouched (the pattern "js/*" is not a comment start)"""
    return re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//.*$', lambda m: m.group(0) if m.group(0).startswith('"') else "", s)

def parse_table(text, head_re):
    """rows of a { "name", ... }, table with the enclosing #if chain; rows under #if 0 are dropped"""
    lines = text.split("\n")
    start = [i for i, l in enumerate(lines) if re.search(head_re, l)]
    if len(start) != 1:
        return None
    out, stack = [], []
    i = start[0] + 1
    while i < len(lines) and not lines[i].startswith("};"):
        s = lines[i].strip()
        if s.startswith("#"):
            d = re.sub(r"\s+", " ", re.sub(r"\s*/[/*].*$", "", s)).strip()   # the directive without its comment
            if re.match(r"# ?if", d):
                stack.append(d)
            elif re.match(r"# ?(else|elif)", d):
                if stack:
                    stack[-1] = "NOT " + stack[-1] if not stack[-1].startswith("NOT ") else stack[-1][4:]
            elif re.match(r"# ?endif", d):
                if stack:
                    stack.pop()
        else:
            m = re.match(r'\{\s*"([^"]*)"\s*,(.*)\}\s*,?\s*$', strip_c_comments(lines[i]).strip())
            if m and not any(re.fullmatch(r"# ?if 0", c) for c in stack):
                fields = [f.strip() for f in re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", m.group(2))]
                out.append({"name": m.group(1), "fields": fields, "line": i + 1, "cond": list(stack)})
        i += 1
    return out

web = rd("httpd", "web.c")
rows = parse_table(web, r"^struct mime_handler mime_handlers\[\]\s*=")
hooks = parse_table(web, r"^struct ej_handler ej_handlers\[\]\s*=")
check("web.c: mime_handlers[] and ej_handlers[] are found", bool(rows) and bool(hooks) and len(rows) > 200 and len(hooks) > 200,
      (rows and len(rows), hooks and len(hooks)))
if not rows or not hooks:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
FILE_OUT = ("do_file", "do_ej", "do_CoBrand_img")

# ------------------------------------------------------------------------------------------------ shipped www
REAPER_MODELS = ("RT-BE96U", "RT-BE86U", "RT-BE88U", "GT-BE98_PRO", "GT-BE98", "GT-BE19000", "BQ16", "BQ16_PRO")
# (folder under www/sysdep/FUNCTION, where its content lands under www/) - the overlays a Reaper build can take
OVERLAYS = (("QIS_V3/QIS_wizard.htm", "QIS_wizard.htm"), ("QIS_V3/images", "images"), ("QIS_V3/mobile", "mobile"),
            ("SITE_SURVEY", ""), ("RWD_UI", "RWD_UI"), ("SDN/SDN", "SDN"), ("SDN/SDN.asp", "SDN.asp"),
            ("SDN/ajax/freewifi_tos.json", "ajax/freewifi_tos.json"), ("LIGHT_EFFECT/AURA", "light_effect"),
            ("LIGHT_EFFECT/LEDG", "light_effect"), ("MULTISERVICE_WAN/Advanced_WAN_Content.asp", "Advanced_WAN_Content.asp"))
# NOT overlays of a Reaper build (compared file by file with the release images, 2026-11-21): ROG_UI, TUF_UI, UI4,
# GS_UI, YEAR20, BUSINESS_UI, QIS_V2, VPNC_V2 / VPNS_V2 - a caller found only there does not ship.
BIN_EXT = {".png", ".gif", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".gz", ".bmp", ".cur",
           ".mp4", ".webp", ".swf", ".cab", ".zip", ".bin", ".mp3", ".wav", ".pdf", ".dict"}
www = os.path.join(SRC, "www")
mk = rd("www", "Makefile")

def makefile_unconditional_rms(mk_text):
    out, depth = [], 0
    for ln in mk_text.replace("\\\n", " ").split("\n"):
        s = ln.strip()
        if re.match(r"(ifeq|ifneq|ifdef|ifndef)\b", s):
            depth += 1
        elif re.match(r"endif\b", s):
            depth = max(0, depth - 1)
        elif depth == 0 and ln.startswith("\t"):
            for cmd in re.split(r"\s*(?:;|&&)\s*", s):
                m = re.match(r"-?@?rm\s+((?:-[rRf]+\s+)+)(.*)$", cmd)
                if m:
                    for arg in m.group(2).split():
                        am = re.match(r"\$\(INSTALLDIR\)/www/(\S+)$", arg)
                        if am:
                            out.append(am.group(1).rstrip("/"))
    return out

shipped = {}        # install path -> set of real source files (a path can come from www/ and from an overlay)
def add(dst, real):
    shipped.setdefault(dst.replace(os.sep, "/"), set()).add(real)
def add_tree(srcdir, dst):
    if os.path.isfile(srcdir):
        add(dst, os.path.realpath(srcdir)); return
    for root, dirs, fs in os.walk(srcdir, followlinks=True):
        for f in fs:
            p = os.path.join(root, f)
            r = os.path.relpath(p, srcdir)
            add(os.path.join(dst, r) if dst else r, os.path.realpath(p))
for root, dirs, fs in os.walk(www, followlinks=True):
    rel = os.path.relpath(root, www)
    if rel == "sysdep" or rel.startswith("sysdep" + os.sep):
        dirs[:] = []
        continue
    for f in fs:
        add(os.path.normpath(os.path.join(rel, f)), os.path.realpath(os.path.join(root, f)))
for sub, dst in OVERLAYS:
    p = os.path.join(www, "sysdep", "FUNCTION", *sub.split("/"))
    if os.path.exists(p):
        add_tree(p, dst)
for model in REAPER_MODELS:
    p = os.path.join(www, "sysdep", model, "www")
    if os.path.isdir(p):
        add_tree(p, "")
n_all = len(shipped)
rms = makefile_unconditional_rms(mk)
check("www/Makefile: the unconditional removals are read (the stock backup page among them)",
      len(rms) > 50 and "Advanced_SettingBackup_Content.asp" in rms, len(rms))
unshipped = []
if os.path.isfile(UNSHIPPED):
    unshipped = [l.strip() for l in open(UNSHIPPED, encoding="utf-8") if l.strip() and not l.startswith("#")]
check("handler_callers.unshipped is beside the test", len(unshipped) > 20, UNSHIPPED)
def drop(pat):
    if any(ch in pat for ch in "*?["):
        ks = [k for k in shipped if fnmatch.fnmatch(k, pat) or fnmatch.fnmatch(k, pat + "/*")]
    else:
        ks = [k for k in shipped if k == pat or k.startswith(pat + "/")]
    for k in ks:
        del shipped[k]
for pat in rms + unshipped + ["Makefile", "gendict.pl", ".gitignore"]:
    drop(pat)
for k in [k for k in shipped if k.endswith(".bak")]:
    del shipped[k]

if MODEL:
    for k in sorted(shipped):       # install path <TAB> the source file(s) it comes from
        print("MODEL\t%s\t%s" % (k, "|".join(sorted(shipped[k]))))

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
def plain_name(pat):
    p = pat.rstrip("*")
    return None if ("*" in p or not p) else p
stems, multi = {}, []
for r in rows:
    p = plain_name(r["name"])
    if not p:
        continue
    stem = re.match(r"^(.*?)(\.[A-Za-z0-9]+)?$", p).group(1)
    if IDENT.fullmatch(stem):
        stems.setdefault(stem, set()).add(p)
    else:
        multi.append(p)
hookset = set(h["name"] for h in hooks)

row_hit, hook_hit, texts = {}, {}, {}
def scan_www(data, where):
    for m in IDENT.finditer(data):
        w = m.group(0)
        if w in stems:
            tail = data[m.end():m.end() + 48]
            for full in stems[w]:
                rest = full[len(w):]
                if tail.startswith(rest) and not re.match(r"[A-Za-z0-9_]", tail[len(rest):len(rest) + 1] or " "):
                    row_hit.setdefault(full, where)
        if w in hookset and w not in hook_hit:
            before = data[max(0, m.start() - 300):m.start()]
            linebefore = before[before.rfind("\n") + 1:]
            to, tc = before.rfind("<%"), before.rfind("%>")
            if to > tc and re.match(r"\s*$", before[to + 2:]) and re.match(r"\s*\(", data[m.end():m.end() + 8]):
                hook_hit[w] = ("EJ", where)
            elif "hook=" in linebefore:
                hook_hit[w] = ("HOOK", where)
            elif before[-1:] in ("\"", "'", "`"):
                hook_hit[w] = ("QUOTED", where)
    for full in multi:
        if full not in row_hit and full in data:
            row_hit[full] = where
n_text = 0
for dst in sorted(shipped):
    if os.path.splitext(dst)[1].lower() in BIN_EXT:
        continue
    for real in sorted(shipped[dst]):
        try:
            raw = open(real, "rb").read()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        data = raw.decode("utf-8", errors="replace")
        n_text += 1
        texts[dst] = texts.get(dst, "") + data
        scan_www(data, dst)
check("the shipped-www model has files to read", n_text > 300, n_text)

# ------------------------------------------------------------------------------------------------ open code
def strip_code(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"(?m)//[^\n]*$", " ", text)
code = {}
for d in ("httpd", "rc", "shared", "others"):
    base = os.path.join(SRC, d)
    if not os.path.isdir(base):
        continue
    for root, dirs, fs in os.walk(base):
        dirs[:] = [x for x in dirs if x not in ("prebuild", ".git")]
        for f in fs:
            p = os.path.join(root, f)
            try:
                raw = open(p, "rb").read()
            except OSError:
                continue
            if b"\0" in raw[:4096] or len(raw) > 6000000:
                continue
            t = raw.decode("utf-8", errors="replace")
            code[os.path.relpath(p, SRC)] = strip_code(t) if f.endswith((".c", ".h")) else t
def code_link(name):
    """the name as a link target in code: /name with nothing path-like before the slash ('/x.cgi', "%s/x.cgi")"""
    rx = re.compile(r"(?:(?<![A-Za-z0-9_.\-])|(?<=%s)|(?<=%d))/" + re.escape(name) + r"(?![A-Za-z0-9_])")
    for rel, t in code.items():
        if name in t and rx.search(t):
            return rel
    return None

# ------------------------------------------------------------------------------------------------ verdicts
def pat_regex(pat):
    """httpd's match(): ** = anything, * = anything but '/', ? = one character"""
    out = ""
    i = 0
    while i < len(pat):
        if pat.startswith("**", i):
            out += ".*"; i += 2
        elif pat[i] == "*":
            out += "[^/]*"; i += 1
        elif pat[i] == "?":
            out += "."; i += 1
        else:
            out += re.escape(pat[i]); i += 1
    return re.compile("^" + out + "$")

verdict = {}     # key -> (kind, state, why)
for r in rows:
    name = r["name"]
    out = (r["fields"] + [""] * 5)[3] if len(r["fields"]) >= 4 else ""
    p = plain_name(name)
    why = None
    if p:
        if p in row_hit:
            why = "named in " + row_hit[p]
        elif out in FILE_OUT and (p in shipped or p.lstrip("/") in shipped):
            why = "serves the shipped file " + p
        else:
            c = code_link(p)
            if c:
                why = "link in " + c
    else:
        rx = pat_regex(name)
        f = next((k for k in shipped if rx.match(k)), None)
        if f:
            why = "matches the shipped file " + f
        else:
            tail = name.rstrip("*").rsplit("*", 1)[-1]
            src = next((k for k, t in texts.items() if len(tail) >= 4 and tail in t), None)
            if src:
                why = "its fixed tail %s is in %s" % (tail, src)
    verdict.setdefault(name, ("row", "CALLED" if why else "UNUSED", why or "no caller"))
    if why and verdict[name][1] == "UNUSED":
        verdict[name] = ("row", "CALLED", why)
for h in hooks:
    name = h["name"]
    if name in verdict and verdict[name][0] == "row":
        continue
    if name in hook_hit:
        verdict[name] = ("hook", "CALLED", "%s in %s" % hook_hit[name])
    else:
        verdict[name] = ("hook", "UNUSED", "no caller")

allow, bad_lines = {}, []
if os.path.isfile(ALLOW):
    for n, ln in enumerate(open(ALLOW, encoding="utf-8").read().split("\n"), 1):
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = ln.split("\t")
        if len(parts) != 2 or not parts[0].strip() or len(parts[1].strip()) < 12 or parts[0] in allow:
            bad_lines.append("line %d: %s" % (n, ln[:60]))
            continue
        allow[parts[0]] = parts[1].strip()
check("handler_callers.allow is beside the test: name <TAB> reason, one line per name, a real reason each",
      os.path.isfile(ALLOW) and not bad_lines, bad_lines[:5] or ALLOW)

unused = sorted(k for k, v in verdict.items() if v[1] == "UNUSED" and k not in allow)
stale = sorted(k for k, v in verdict.items() if v[1] == "CALLED" and k in allow and "[not on every line]" not in allow[k])
absent = sorted(k for k in allow if k not in verdict)
n_rows = sum(1 for v in verdict.values() if v[0] == "row")
n_hooks = sum(1 for v in verdict.values() if v[0] == "hook")
print("     %d rows and %d hooks read; %d called, %d allowed with a reason; %d allow-list lines name nothing in this tree"
      % (n_rows, n_hooks, sum(1 for v in verdict.values() if v[1] == "CALLED"),
         sum(1 for k, v in verdict.items() if v[1] == "UNUSED" and k in allow), len(absent)))
check("every mime_handlers[] row has a caller or an allow-list line",
      not [k for k in unused if verdict[k][0] == "row"],
      "NO CALLER: " + ", ".join(k for k in unused if verdict[k][0] == "row"))
check("every ej_handlers[] hook has a caller or an allow-list line",
      not [k for k in unused if verdict[k][0] == "hook"],
      "NO CALLER: " + ", ".join(k for k in unused if verdict[k][0] == "hook"))
check("no allow-list line is stale (its name has a caller now: take the line out)", not stale,
      ", ".join("%s (%s)" % (k, verdict[k][2]) for k in stale))
if LIST:
    for k in sorted(verdict, key=lambda x: (verdict[x][0], x)):
        kind, state, why = verdict[k]
        if state == "UNUSED" and k in allow:
            state, why = "ALLOWED", allow[k]
        print("LIST\t%s\t%s\t%s\t%s" % (kind, k, state, why))

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
