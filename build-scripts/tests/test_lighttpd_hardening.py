#!/usr/bin/env python3
"""lighttpd hardening (audit F-4): full RELRO (2026-11-05), PIE + FORTIFY (2026-11-06).

The first PIE cut assigned CFLAGS_REAPER_HARDEN AFTER the `export CFLAGS=` that expands it: configure got
neither -fPIE nor -O2/-D_FORTIFY_SOURCE, while the post-configure sed still put -pie on the program's link
line - the image's lighttpd came out PIE with a TEXTREL and no FORTIFY. This pins the order, evaluates the
CFLAGS the script exports, and checks that -pie reaches the program only (never the -shared modules).
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] / REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
P = os.path.join(SRC, "lighttpd-1.4.39", "preconfigure-script-hnd") if SRC else ""
if not P or not os.path.isfile(P):
    print("SKIP: no router source tree with lighttpd-1.4.39 (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
t = open(P, encoding="latin-1").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

i_set, i_exp = t.find('\nCFLAGS_REAPER_HARDEN="'), t.find('\nexport CFLAGS="')
check("the hardening flags are set before the CFLAGS that expands them", 0 <= i_set < i_exp, (i_set, i_exp))
check("CFLAGS carries them", re.search(r'^export CFLAGS="[^\n]*\$CFLAGS_REAPER_HARDEN"', t, re.M) is not None)
check("-O2, FORTIFY and -fPIE", '"-O2 -D_FORTIFY_SOURCE=2 -fPIE"' in t)
check("full RELRO kept on LDFLAGS", re.search(r'^export LDFLAGS="-Wl,-z,relro,-z,now ', t, re.M) is not None)
check("-pie goes on lighttpd_LDFLAGS only, after configure, and its absence fails configure",
      "s/^lighttpd_LDFLAGS = -export-dynamic$/lighttpd_LDFLAGS = -export-dynamic -pie/" in t
      and "-pie not set in src/Makefile" in t and "exit $_rc" in t and not re.search(r'LDFLAGS="[^"\n]*-pie', t))
sh = shutil.which("sh")
if sh:
    seg = "\n".join(l for l in t.splitlines() if l.startswith(("CFLAGS_REAPER_HARDEN=", "export CFLAGS=")))
    r = subprocess.run([sh, "-c", seg + '\nprintf "%s" "$CFLAGS"'], capture_output=True, text=True)
    check("the exported CFLAGS really contain the flags", "-O2 -D_FORTIFY_SOURCE=2 -fPIE" in r.stdout, r.stdout[-120:])
print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
