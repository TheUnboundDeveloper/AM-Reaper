#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gatekeeper waiting page: approved devices are looked up in the list store, not in nvram (field report, 2026-11-11).

WHY THIS EXISTS. v2.6.3 moved the Gatekeeper device list from nvram gk_rl to /jffs/gatekeeper/rl (shared/gk_rl.c,
gk_rl_get/gk_rl_set), and start_gk's gk_rl_migrate() clears the nvram copy. rc, gkd and web.c moved to the store;
httpd.c's gk_mac_known() - the check behind the "awaiting approval" page - kept reading nvram gk_rl. On a migrated
router that read is empty, so every device counted as unapproved: with Gatekeeper and its waiting-room page on, every
plain-HTTP request got "Awaiting approval", the login page included, while the same devices had full LAN and internet
access (the firewall reads the store). A v3.7.5 user could not log in from any device; HTTPS was unaffected.

WHAT IT DOES. Pins gk_mac_known() to gk_rl_get(); refuses any nvram read of gk_rl outside shared/gk_rl.c in the
programs that use the list (httpd, rc, gkd, shared); compiles the real gk_mac_known() with the real gk_rl_get() on
the host and runs it on a list file (the file wins over a stale nvram value, nvram only before migration, case,
prefix and empty-MAC cases); pins the captive check's escape hatches and its call to gk_mac_known().

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
HC = os.path.join(SRC, "httpd", "httpd.c") if SRC else ""
ST = os.path.join(SRC, "shared", "gk_rl.c") if SRC else ""
if not HC or not os.path.isfile(HC) or not os.path.isfile(ST):
    skip("no router source tree with httpd/httpd.c and shared/gk_rl.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def rd(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read()

hc, st = rd(HC), rd(ST)

km = re.search(r"^static int\ngk_mac_known\(const char \*mac\)\n\{.*?^\}\n", hc, re.S | re.M)
check("httpd: gk_mac_known() is a block the test can cut out", km is not None)
kb = km.group(0) if km else ""
check("httpd: gk_mac_known() reads the list through gk_rl_get()", "gk_rl_get()" in kb)
check("httpd: gk_mac_known() does not read nvram", "nvram" not in kb, kb[:200])
check("httpd: an empty MAC is refused before the search", re.search(r"if \(!n\)\s*return 0;", kb) is not None)

gm = re.search(r"^static char \*gk_rl_buf;.*?\n.*?^char \*gk_rl_get\(void\)\n\{.*?^\}\n", st, re.S | re.M)
check("shared: gk_rl_get() and its buffer are a block the test can cut out", gm is not None)

# the regression class: a reader of the old nvram copy anywhere but the store itself
NVREAD = re.compile(r'nvram_(?:safe_)?get(?:_int)?\(\s*"gk_rl"\s*\)|nvram_match\(\s*"gk_rl"|nvram get gk_rl\b|_nv gk_rl\b')
bad = []
for sub in ("httpd", "rc", "gkd", "shared"):
    base = os.path.join(SRC, sub)
    if not os.path.isdir(base):
        continue
    for dp, dn, fn in os.walk(base):
        for f in fn:
            if not f.endswith((".c", ".h", ".sh")):
                continue
            p = os.path.join(dp, f)
            if os.path.normpath(p) == os.path.normpath(ST):
                continue
            try:
                t = rd(p)
            except OSError:
                continue
            for m in NVREAD.finditer(t):
                bad.append("%s:%d" % (os.path.relpath(p, SRC), t.count("\n", 0, m.start()) + 1))
check("no nvram read of gk_rl outside shared/gk_rl.c (httpd, rc, gkd, shared)", not bad, ", ".join(bad))

cm = re.search(r"^int\nreaper_gk_captive_check\(const char \*client_ip\)\n\{.*?^\}\n", hc, re.S | re.M)
cb = cm.group(0) if cm else ""
check("httpd: the captive check is a block the test can read", cm is not None)
i_ssl, i_mac = cb.find("if (do_ssl)"), cb.find("return gk_mac_known(mac) ? 0 : 1;")
check("httpd: the HTTPS escape hatch comes before the list lookup", 0 < i_ssl < i_mac, (i_ssl, i_mac))
check("httpd: the HTTP-only and alert-only exits are still there",
      'nvram_get_int("http_enable") == 0' in cb and 'nvram_match("gk_captive", "0") || nvram_match("gk_default", "1")' in cb)

cc = shutil.which("gcc") or shutil.which("cc")
if km and gm and cc:
    with tempfile.TemporaryDirectory() as td:
        rl = os.path.join(td, "rl")
        prog = ("#define _GNU_SOURCE\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n"
                "#include <sys/stat.h>\n#define GK_RL_FILE \"%s\"\n#define GK_RL_MAX (256 * 1024)\n"
                "static const char *nv_gk_rl = \"\";\n"
                "static char *nvram_safe_get(const char *k) { return (char *)(strcmp(k, \"gk_rl\") ? \"\" : nv_gk_rl); }\n"
                % rl) + gm.group(0) + "\n" + kb + r"""
int main(int argc, char **argv) {
  int i;
  nv_gk_rl = argv[1];
  for (i = 2; i < argc; i++) putchar(gk_mac_known(argv[i]) ? '1' : '0');
  return 0;
}
"""
        c_, x = os.path.join(td, "t.c"), os.path.join(td, "t")
        open(c_, "w").write(prog)
        r = subprocess.run([cc, "-Wall", "-Werror", "-o", x, c_], capture_output=True, text=True)
        check("host: gk_mac_known() + gk_rl_get() compile clean (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            A, B, C = "AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02", "AA:BB:CC:DD:EE:03"
            macs = [A, B, A.lower(), C, A[:-1], ""]
            def run(file_text, nv):
                if file_text is None:
                    if os.path.exists(rl): os.remove(rl)
                else:
                    open(rl, "w").write(file_text)
                try:	# the pre-fix lookup spun for ever on an empty MAC; a hang is a failure, not a stuck suite
                    return subprocess.run([x, nv] + macs, capture_output=True, text=True, timeout=10).stdout
                except subprocess.TimeoutExpired:
                    return "TIMEOUT (the lookup never returned)"
            lst = "<%s>1>0<%s>2>0\n" % (A, B)
            got = run(lst, "")
            check("migrated router (file, empty nvram): both listed devices are known, any case; others and a prefix are not",
                  got == "111000", got)
            got = run(lst, "<%s>1>0" % C)
            check("the file wins over a stale nvram value", got == "111000", got)
            got = run("", "<%s>1>0" % A)
            check("an empty file means an empty list, whatever nvram holds", got == "000000", got)
            got = run(None, "<%s>1>0" % C)
            check("before migration (no file) the nvram copy is read", got == "000100", got)
elif km and gm:
    print("note no C compiler on the host - the lookup is not compiled")

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("\nall checks passed")
