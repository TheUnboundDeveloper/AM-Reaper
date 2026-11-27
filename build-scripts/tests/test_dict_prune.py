#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dictionary prune (REAPER-CUT8-DICT, native-UI cutover stage 5, 2026-11-27).

WHY THIS EXISTS. Stage 5 stopped shipping the stock pages; 181 dictionary keys were named only by them. The www
install now drops those keys from the STAGED language packs (router/tools/reaper_dict_prune.py, list
reaper_dict_prune.txt beside it); the source packs keep them. Two staged forms exist and the difference is the whole
risk: 102.10 packs keep KEY=text lines and httpd finds a key by name, but the 102.8 packs are renumbered and httpd
reads a string by its LINE POSITION (httpd.c search_desc: atoi(name) indexes the line array) - deleting a line there
would shift every later string onto the wrong label. So the tool deletes lines only in the named form and empties
them in place in the numbered form, and refuses while any staged file still names a listed key.
This test pins: the tool, the list and the Makefile hook in the tree (last step of the install, failure not ignored);
that no source file the install keeps names a listed key; the tool's behaviour on both forms (byte-exact, BOM kept,
lockstep, refusals, idempotent); and reaper_verify's dict-tokens gate (reaper_dictcheck.py) on both forms.
Exit 0 pass, 1 fail, 77 skipped.
"""
import fnmatch, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree"); sys.exit(77)
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(SRC, "tools", "reaper_dict_prune.py")
LIST = os.path.join(SRC, "tools", "reaper_dict_prune.txt")
CHK = os.path.join(HERE, "..", "reaper_dictcheck.py")
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))
def rd(*p):
    try: return open(os.path.join(*p), encoding="utf-8", errors="replace").read()
    except OSError: return ""

# ---- 1. the tree wiring -------------------------------------------------------------------------------------------
www = os.path.join(SRC, "www")
mk = rd(www, "Makefile")
check("tools/reaper_dict_prune.py and its list are in the tree", os.path.isfile(TOOL) and os.path.isfile(LIST))
hook = "\tpython3 $(TOP)/tools/reaper_dict_prune.py $(INSTALLDIR)/www $(TOP)/tools/reaper_dict_prune.txt $(SRCBASE)/image/dictenum.txt\n"
check("www/Makefile runs the prune once, failure NOT ignored (no leading '-', no '|| true')",
      mk.count(hook) == 1 and mk.count("reaper_dict_prune.py") == 1)
i_stock = mk.find("# End REAPER-CUT8-STOCK"); i_hook = mk.find(hook)
check("...after the stage 5 removal block (the guard needs the removed pages gone) and as the last step of the file",
      0 <= i_stock < i_hook and mk.rstrip().endswith("# End REAPER-CUT8-DICT")
      and not re.search(r"^\t", mk[i_hook + len(hook):], re.M), (i_stock, i_hook))
keys = [l.strip() for l in rd(LIST).split("\n") if l.strip() and not l.startswith("#")]
check("the list holds keys, one per line, no duplicates", len(keys) > 100 and len(set(keys)) == len(keys)
      and all(re.match(r"^[A-Za-z0-9_]+$", k) for k in keys), len(keys))
check("...and never a language-header or BOM key (the language menu reads LANG_*)",
      not [k for k in keys if k == "BOM" or k.startswith("LANG_")])
src_keys = set()
for line in open(os.path.join(www, "EN.dict"), "rb"):
    line = line.lstrip(b"\xef\xbb\xbf")
    if b"=" in line: src_keys.add(line.split(b"=", 1)[0].decode("utf-8", "replace"))
check("every listed key is in the source EN pack (a list that belongs to this tree)",
      not [k for k in keys if k not in src_keys], [k for k in keys if k not in src_keys][:10])

# ---- 2. no file the install keeps names a listed key ---------------------------------------------------------------
# "Removed" means an UNCONDITIONAL rm of www/Makefile (or handler_callers.unshipped). A file removed only under a model
# flag ships on some model: RT-BE88U builds with RTCONFIG_REVERTFW=y, so get_release_note_revertfw.asp ships there and
# its keys must stay (the first list had two such keys; the BE88U install would have refused).
def unconditional_rms(text):
    out, depth = [], 0
    for line in text.split("\n"):
        if re.match(r"^(ifeq|ifneq|ifdef|ifndef)\b", line): depth += 1; continue
        if re.match(r"^endif\b", line): depth -= 1; continue
        if depth == 0:
            m = re.match(r"^\trm\s+-\w+\s+(.*)$", line)
            if m:
                for arg in m.group(1).split():
                    am = re.match(r"^\$\(INSTALLDIR\)/www/(\S+)$", arg)
                    if am: out.append(am.group(1))
    return out
gone = unconditional_rms(mk)
uns = [l.strip() for l in rd(HERE, "handler_callers.unshipped").split("\n") if l.strip() and not l.startswith("#")]
def removed(rel):
    for pat in gone + uns:
        if fnmatch.fnmatch(rel, pat) or rel.startswith(pat.rstrip("/") + "/"): return True
    return False
TOK = re.compile(rb"<#([A-Za-z0-9_]+)#>")
kset = set(keys); named_by = {}
roots = [("", www)]
sd = os.path.join(www, "sysdep")
if os.path.isdir(os.path.join(sd, "FUNCTION", "QIS_V3")): roots.append(("", os.path.join(sd, "FUNCTION", "QIS_V3")))
for d in (os.listdir(sd) if os.path.isdir(sd) else []):
    if re.match(r"^(RT-BE|GT-BE|BQ16)", d) and os.path.isdir(os.path.join(sd, d, "www")): roots.append(("", os.path.join(sd, d, "www")))
for _, base in roots:
    for root, dirs, files in os.walk(base):
        if base == www and os.path.relpath(root, www).split(os.sep)[0] == "sysdep": dirs[:] = []; continue
        for f in files:
            p = os.path.join(root, f); rel = os.path.relpath(p, base).replace(os.sep, "/")
            if f.endswith(".dict") or f == "Makefile" or removed(rel): continue
            try: data = open(p, "rb").read()
            except OSError: continue
            for m in set(TOK.findall(data)):
                m = m.decode()
                if m in kset: named_by.setdefault(m, []).append(rel)
check("no source file the install keeps names a listed key", not named_by, sorted(named_by.items())[:6])

# ---- 3. the tool on synthetic packs ---------------------------------------------------------------------------------
BOM = b"\xef\xbb\xbf"
def run(*args):
    p = subprocess.run([sys.executable] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")
def mkwww(packs, pages):
    d = tempfile.mkdtemp(prefix="dictprune_")
    for n, b in packs.items(): open(os.path.join(d, n), "wb").write(b)
    for n, b in pages.items():
        os.makedirs(os.path.dirname(os.path.join(d, n)), exist_ok=True)
        open(os.path.join(d, n), "wb").write(b)
    return d
def rb(d, n): return open(os.path.join(d, n), "rb").read()
tmp = []
lst = tempfile.mktemp(suffix=".txt"); open(lst, "w").write("# comment\nKB\nKC\n\n"); tmp.append(lst)
named = BOM + b"BOM=BOM\nKA=alpha\nKB=beta \xc3\xa9\nKC=gamma\nKD=delta"            # no final newline on purpose
named_tw = BOM + b"BOM=BOM\nKA=a-tw\nKB=b-tw\nKC=c-tw\nKD=d-tw"
d = mkwww({"EN.dict": named, "TW.dict": named_tw, "temp.dict": b"x\n"}, {"p.asp": b"<#KA#> <#KD#>"}); tmp.append(d)
rc, out = run(TOOL, d, lst)
check("named form: listed lines deleted, the rest byte-exact (BOM, UTF-8, no final newline kept)",
      rc == 0 and rb(d, "EN.dict") == BOM + b"BOM=BOM\nKA=alpha\nKD=delta" and rb(d, "TW.dict") == BOM + b"BOM=BOM\nKA=a-tw\nKD=d-tw"
      and rb(d, "temp.dict") == b"x\n", out)
rc, out = run(TOOL, d, lst)
check("named form: a second run is a no-op that does not fail the install", rc == 0 and "nothing to drop" in out
      and rb(d, "EN.dict") == BOM + b"BOM=BOM\nKA=alpha\nKD=delta", out)
lst0 = tempfile.mktemp(suffix=".txt"); open(lst0, "w").write("KX\n"); tmp.append(lst0)
d = mkwww({"EN.dict": BOM + b"KX=first\nKA=alpha\n", "TW.dict": BOM + b"KX=f-tw\nKA=a-tw\n"}, {"p.asp": b"<#KA#>"}); tmp.append(d)
rc, out = run(TOOL, d, lst0)
check("named form: deleting the first line carries the BOM to the next one", rc == 0 and rb(d, "EN.dict") == BOM + b"KA=alpha\n", out)
d = mkwww({"EN.dict": named, "TW.dict": named_tw}, {"p.asp": b"<#KA#>", "js/x.js": b"`<#KC#>`"}); tmp.append(d)
rc, out = run(TOOL, d, lst)
check("named form: REFUSED while a staged file names a listed key, packs untouched",
      rc == 1 and "js/x.js <#KC#>" in out and rb(d, "EN.dict") == named, out)
d = mkwww({"EN.dict": named, "TW.dict": BOM + b"BOM=BOM\nKA=a\nKB=b\nKC=c"}, {"p.asp": b"<#KA#>"}); tmp.append(d)
rc, out = run(TOOL, d, lst)
check("named form: REFUSED when the packs would stop being lockstep", rc == 1 and "lockstep" in out and rb(d, "EN.dict") == named, out)
num = BOM + b"English\nalpha\nbeta\ngamma\ndelta\n"
num_tw = BOM + b"Chinese\na-tw\nb-tw\nc-tw\nd-tw\n"
enum = tempfile.mktemp(suffix=".txt"); open(enum, "wb").write(b"0=LANG_EN\n1=KA\n2=KB\n3=KC\n4=KD\n"); tmp.append(enum)
d = mkwww({"EN.dict": num, "TW.dict": num_tw}, {"p.asp": b"<#1#><#4#>"}); tmp.append(d)
rc, out = run(TOOL, d, lst, enum)
check("numbered form: listed lines emptied IN PLACE, line count unchanged (httpd indexes by line)",
      rc == 0 and rb(d, "EN.dict") == BOM + b"English\nalpha\n\n\ndelta\n" and rb(d, "TW.dict") == BOM + b"Chinese\na-tw\n\n\nd-tw\n", out)
rc, out = run(TOOL, d, lst, enum)
check("numbered form: a second run changes nothing", rc == 0 and rb(d, "EN.dict") == BOM + b"English\nalpha\n\n\ndelta\n", out)
d = mkwww({"EN.dict": num, "TW.dict": num_tw}, {"p.asp": b"<#1#><#3#>"}); tmp.append(d)
rc, out = run(TOOL, d, lst, enum)
check("numbered form: REFUSED while a staged page names a listed key by number", rc == 1 and "<#3#>" in out and rb(d, "EN.dict") == num, out)
rc, out = run(TOOL, d, lst)
check("numbered form: REFUSED without dictenum.txt", rc == 1 and "dictenum" in out and rb(d, "EN.dict") == num, out)

# ---- 4. reaper_verify's dict-tokens gate -----------------------------------------------------------------------------
check("reaper_dictcheck.py is beside reaper_verify.sh and reaper_verify runs it",
      os.path.isfile(CHK) and 'pass "dict-tokens"' in rd(HERE, "..", "reaper_verify.sh"))
d = mkwww({"EN.dict": BOM + b"BOM=BOM\nKA=alpha\nKD=delta\n", "TW.dict": BOM + b"BOM=BOM\nKA=a\nKD=d\n"},
          {"p.asp": b"<#KA#>", "js/asus_policy.js": b"<#ASUS_Aiboard_EULA_Law_2#>"}); tmp.append(d)
rc, out = run(CHK, d)
check("gate, named form: passes when every token resolves (the known stock EULA gap allowed)", rc == 0 and "0 unresolved (1 known" in out, out)
open(os.path.join(d, "q.asp"), "wb").write(b"<#KB#>")
rc, out = run(CHK, d)
check("gate, named form: FAILS on a token no pack carries", rc == 1 and "q.asp <#KB#>" in out, out)
d = mkwww({"EN.dict": BOM + b"English\nalpha\n\ndelta\n", "TW.dict": BOM + b"Chinese\na\n\nd\n"}, {"p.asp": b"<#1#><#3#>"}); tmp.append(d)
rc, out = run(CHK, d)
check("gate, numbered form: passes when every number is a non-empty line", rc == 0, out)
open(os.path.join(d, "q.asp"), "wb").write(b"<#2#>")
rc, out = run(CHK, d)
check("gate, numbered form: FAILS on a token whose line was emptied", rc == 1 and "q.asp <#2#>" in out, out)
open(os.path.join(d, "TW.dict"), "wb").write(BOM + b"Chinese\na\nd\n"); os.remove(os.path.join(d, "q.asp"))
rc, out = run(CHK, d)
check("gate: FAILS when the packs are not lockstep", rc == 1 and "lockstep" in out, out)

for t in tmp:
    shutil.rmtree(t, ignore_errors=True) if os.path.isdir(t) else (os.path.exists(t) and os.remove(t))
print("%d checks failed" % len(fails) if fails else "all checks passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
