#!/usr/bin/env python3
"""Review 2026-10-28 (both lines after the GPL split) - the fixes the owner asked for.

  R-1  shared/misc.c isValidMacAddress(): a separator out of place makes it no MAC. Stock broke out of the loop
       and returned i == 12 && s == 0, so 12 hex digits + a separator + anything passed unread - and on the
       102.10 line the AiMesh applyapp actions print that value into cfg_server's JSON. The function is
       compiled from the real source and run on good and bad strings; the stock `break` must fail them.
  D-1  httpd/web.c: the Surfshark sign-in handlers (new with GPL 102_40585, closed web_hook.o, third-party
       cloud) are not in the compiled handler table. On the 102.8 line web.c has none - that passes too.
  (R-2, a header API key never follows a redirect, is checked in test_wallguard_sources.py.)
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - argv[1] / REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "shared", "misc.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no C compiler"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

misc = rd("shared/misc.c")
m = re.search(r"\nint isValidMacAddress\(const char\* mac\) \{\n.*?\n\}\n", misc, re.S)
check("R-1: isValidMacAddress() is in shared/misc.c", bool(m))
GOOD = ["AA:BB:CC:DD:EE:FF", "aa-bb-cc-dd-ee-ff", "AABBCCDDEEFF", "00:11:22:33:44:55"]
BAD = ['AABBCCDDEEFF:"},{"x":1', "AABBCCDDEEFF-;reboot;", 'A":A:BB:CC:DD:EE:FF', "AA:BB:CC:DD:EE:F",
       "AA:BB:CC:DD:EE:FF:", "AA:BB:CC:DD:EE:FF:00", ":AA:BB:CC:DD:EE:FF", "AA::BB:CC:DD:EE:FF", "", "AABBCCDDEEFF "]

def run(fn, tmp, tag):
    c = os.path.join(tmp, tag + ".c"); x = os.path.join(tmp, tag)
    open(c, "w").write("#include <stdio.h>\n#include <ctype.h>\n" + fn +
                       'int main(int c, char **v) { for (int i = 1; i < c; i++) printf("%d", isValidMacAddress(v[i])); return 0; }\n')
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-o", x, c], capture_output=True, text=True)
    if r.returncode:
        return None, r.stderr
    g = subprocess.run([x] + GOOD, capture_output=True, text=True).stdout
    b = subprocess.run([x] + BAD, capture_output=True, text=True).stdout
    return (g, b), ""

if m:
    tmp = tempfile.mkdtemp(prefix="rev1028_")
    try:
        res, err = run(m.group(0), tmp, "real")
        check("R-1: the real function compiles", res is not None, err)
        if res:
            check("R-1: well-formed MACs pass", res[0] == "1" * len(GOOD), list(zip(GOOD, res[0])))
            check("R-1: a separator out of place, trailing text, quotes or a short MAC are refused",
                  res[1] == "0" * len(BAD), list(zip(BAD, res[1])))
        mut = m.group(0).replace("if (i == 0 || i / 2 - 1 != s)\n\t\t\t\treturn 0;", "if (i == 0 || i / 2 - 1 != s)\n\t\t\t\tbreak;")
        check("R-1: the mutant (stock `break`) differs from the real text", mut != m.group(0))
        if mut != m.group(0):
            mres, _ = run(mut, tmp, "mut")
            check("R-1: the stock `break` mutant fails the bad strings (the check has teeth)",
                  mres is not None and mres[1] != "0" * len(BAD), mres)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

web = rd("httpd/web.c")
rows = [mo.start() for mo in re.finditer(r'\n\t\{ "surfshark_(login|2fa)\.cgi"', web)]
def compiled_off(pos):
    # the nearest preprocessor line above the row opens the block it sits in
    head = web[:pos].split("\n")
    for l in reversed(head):
        if l.startswith("#if") or l.startswith("#ifdef") or l.startswith("#endif") or l.startswith("#else"):
            return l.startswith("#if 0")
    return False
check("D-1: no Surfshark handler row is compiled (each sits in an #if 0 block; none at all on the 102.8 line)",
      all(compiled_off(p) for p in rows), len(rows))

print("%d failure(s)" % len(fails))
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
