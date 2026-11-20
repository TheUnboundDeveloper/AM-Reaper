#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal: one portal start per request (2026-11-12).

WHY THIS EXISTS. On the owner's router a Guest Portal create ran the portal for 17 s, stopped it and took another
17 s to bring it back - inside one request. restart_wireless() (rc/lan.c) starts the portal itself, and the Network
page's list ("restart_wireless;restart_sdn 4;...;restart_chilli;restart_uam_srv;") then restarts it. A phone that
joined as soon as the network appeared got an address, lost the sign-in service and waited.

WHAT IT DOES. Compiles the real list matcher (rc/services.c REAPER-RCREST block) on the host and runs it, then
pins the hand-over: the "wireless" service gives restart_wireless() what is left of the list being processed and
clears it afterwards, and restart_wireless() leaves the start to a portal service still to come.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router).
Without a host C compiler only the pins run."""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "lan.c")):
    print("SKIP: no router tree with rc/lan.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="latin-1").read()

svc, lan, rch = read("rc/services.c"), read("rc/lan.c"), read("rc/rc.h")

# ---- pins
check("rc.h declares the matcher and the hand-over",
      "extern int reaper_rc_rest_has(const char *rest, const char *svc);" in rch
      and "extern const char *reaper_wl_rest;" in rch)
check("the wireless service hands restart_wireless() the rest of the list and clears it after",
      re.search(r"reaper_wl_rest = nvptr;[^\n]*\n#endif\n\t\t\trestart_wireless\(\);\n#ifdef RTCONFIG_MULTILAN_CFG\n"
                r"\t\t\treaper_wl_rest = NULL;\n", svc) is not None)
check("nothing else sets the hand-over", svc.count("reaper_wl_rest = ") == 3 and "reaper_wl_rest =" not in lan,
      svc.count("reaper_wl_rest = "))
m = re.search(r"\nvoid restart_wireless\(void\)\n\{.*?\n\}\n", lan, re.S)
body = m.group(0) if m else ""
check("restart_wireless() found", bool(body))
check("restart_wireless() leaves the start to a portal service still to come",
      'if (reaper_rc_rest_has(reaper_wl_rest, "restart_chilli"))\n\t\tlogmessage(' in body
      and "\telse\n\t\tstart_chilli();\n" in body
      and 'if (!reaper_rc_rest_has(reaper_wl_rest, "restart_CP"))\n\t\tstart_CP();\n' in body)
check("restart_wireless() still stops the portal before the radios go down",
      body.find("stop_chilli();") >= 0 and body.find("stop_chilli();") < body.find("reaper_rc_rest_has("))
check("the portal's own service still stops and starts it",
      'strcmp(script, "chilli") == 0)\n\t{\n\t\tif(action&RC_SERVICE_STOP) stop_chilli();\n'
      '\t\tif(action&RC_SERVICE_START) start_chilli();' in svc)

# ---- the matcher, compiled and run
blk = re.search(r"/\* REAPER-RCREST-BEGIN \*/(.*?)/\* REAPER-RCREST-END \*/", svc, re.S)
check("REAPER-RCREST block present", bool(blk))
CC = shutil.which("gcc") or shutil.which("cc")
if blk and not CC:
    print("SKIP (part): no host C compiler - the matcher was not run")
elif blk:
    CASES = [
        ("restart_sdn 4;restart_qos;restart_firewall;restart_chilli;restart_uam_srv;", "restart_chilli", 1),
        ("restart_sdn 4;restart_qos;restart_firewall;restart_chilli;restart_uam_srv;", "restart_CP", 0),
        ("restart_qos;restart_firewall;", "restart_chilli", 0),
        ("restart_chilli", "restart_chilli", 1),
        ("restart_chilli 2;restart_qos", "restart_chilli", 1),
        ("restart_chillispot;restart_qos", "restart_chilli", 0),
        ("xrestart_chilli;", "restart_chilli", 0),
        ("stop_chilli;start_chilli;", "restart_chilli", 0),
        ("restart_CP;restart_uam_srv;", "restart_CP", 1),
        ("restart_sdn restart_chilli;", "restart_chilli", 0),
        ("", "restart_chilli", 0),
        (";;restart_chilli;;", "restart_chilli", 1),
        ("restart_chilli", "", 0),
    ]
    rows = ",\n".join('  { "%s", "%s", %d }' % c for c in CASES)
    prog = ("#include <stdio.h>\n#include <string.h>\n" + blk.group(1) +
            "\nstatic const struct { const char *l, *s; int want; } T[] = {\n" + rows + "\n};\n"
            "int main(void)\n{\n  unsigned i; int bad = 0;\n"
            "  for (i = 0; i < sizeof(T) / sizeof(T[0]); i++)\n"
            "    if (reaper_rc_rest_has(T[i].l, T[i].s) != T[i].want) { printf(\"case %u [%s] [%s]\\n\", i, T[i].l, T[i].s); bad++; }\n"
            "  if (reaper_rc_rest_has(NULL, \"restart_chilli\") || reaper_rc_rest_has(\"restart_chilli\", NULL)) { puts(\"NULL\"); bad++; }\n"
            "  return bad ? 1 : 0;\n}\n")
    tmp = tempfile.mkdtemp()
    try:
        c, exe = os.path.join(tmp, "t.c"), os.path.join(tmp, "t")
        open(c, "w", encoding="latin-1").write(prog)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("the matcher compiles clean (-Wall -Werror)", r.returncode == 0, r.stderr[-400:])
        if r.returncode == 0:
            r = subprocess.run([exe], capture_output=True, text=True, timeout=30)
            check("the matcher: %d list cases and NULL arguments" % len(CASES), r.returncode == 0, r.stdout[-400:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
