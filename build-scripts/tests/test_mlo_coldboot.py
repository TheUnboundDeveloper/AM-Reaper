#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MLO on + a restart without a power-off: warn (rc/reaper_mloboot.c REAPER-MLOBOOT, 2026-11-20).

WHY THIS EXISTS. On the RT-BE96U with MLO on, a soft restart sometimes leaves Wi-Fi accepting no devices until the
router is unplugged (2026-07, 2026-10: 1 of 6 soft restarts). On a good boot the kernel log carries the Wi-Fi
driver's "dhdpcie_bus_bridge_init" lines; on the bad one they are missing. No software path gives the radios a
power-on reset, and the owner chose WARN ONLY (2026-11-20): one syslog line, an uncommitted nvram flag, a dashboard
banner, and a power-cycle note on the MLO switch's confirm.

WHAT IT DOES.
  1. Compiles the pure decision (the REAPER-MLOBOOT-PURE block, extracted from rc/reaper_mloboot.c) on the host
     (-Wall -Wextra -Werror) and feeds it fixtures in the router's own formats (owner's RT-BE96U, 2026-11-20:
     /proc/bootstate/reset_status prints plain hex "20000000"; dmesg "RESET STATUS SW reset 0x20000000",
     "BOOT REASON ACTIVATE 0x100", "bcm-pcie: Core [N] Using epuperstb"): cold boot, warm good, warm bad, MLO off,
     a rotated log, unknown / malformed status, hardware and PCIe resets, power-on with other bits.
     2026-11-23 (REAPER-MLOBOOT-SEEN): every case runs with seen = 1 (this router has printed the bridge line on an
     earlier start); with seen = 0 nothing warns, because the line comes from the closed dongle driver and was read on
     one board only - a radio revision that words it differently must not get the banner on every restart.
  2. Pins the wiring: once per boot after wlready in start_wl, the seen file (/jffs/reaper/mlo_bridge_seen), the kernel log read with klogctl READ_ALL (nothing
     consumed), the flag written every boot (0 or 1) and never committed, one syslog line, Makefile / rc.h, the
     default, the dashboard banner (server-rendered, both keys), the MLO confirm note.

Exit 0 pass, 1 fail, 77 skipped (no gcc, not Linux, or no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

FAILS = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + (("" if cond or not detail else ": " + str(detail)[:600])))
    if not cond:
        FAILS.append(name)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "rc")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
if not sys.platform.startswith("linux"):
    skip("not Linux")
GCC = shutil.which("gcc") or shutil.which("cc")
if not GCC:
    skip("no host gcc")

def rd(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

mb = rd("rc/reaper_mloboot.c")
m = re.search(r"/\* REAPER-MLOBOOT-PURE-BEGIN \*/\n(.*?)/\* REAPER-MLOBOOT-PURE-END \*/", mb, re.S)
check("rc/reaper_mloboot.c: one pure decision block", m is not None and mb.count("REAPER-MLOBOOT-PURE-BEGIN") == 1)

COLD = ("[    0.000000] Booting Linux on physical CPU 0x0000000000 [0x420f1000]\n"
        "[    0.000000] Linux version 4.19.294 (reaper@build) (gcc version 10.3.0) #1 SMP PREEMPT\n"
        "[    0.000000] RESET STATUS POR reset 0x80000000\n[    0.000000] BOOT REASON REBOOT 0x0\n"
        "[    2.110000] bcm-pcie: Core [1] Using epuperstb\n[    2.120000] bcm-pcie: Core [2] Using epuperstb\n"
        "[    2.130000] bcm-pcie: Core [3] Using epuperstb\n"
        "[   14.200000] dhdpcie_bus_bridge_init: ipc_mlo bridge set up\n[   14.300000] bcm-pcie: Core [1] BAR3/BAR4\n")
WARM_OK = COLD.replace("RESET STATUS POR reset 0x80000000", "RESET STATUS SW reset 0x20000000") \
              .replace("BOOT REASON REBOOT 0x0", "BOOT REASON ACTIVATE 0x100")
WARM_BAD = "\n".join(l for l in WARM_OK.split("\n") if "dhdpcie_bus_bridge_init" not in l and "BAR3" not in l)
ROTATED = "\n".join(l for l in WARM_BAD.split("\n") if "Linux version" not in l and "Booting Linux" not in l)
CASES = [
    # name, mld_enable, reset_status file text, klog, expected
    ("cold boot, MLO on (power-on, bridge line)", "1", "80000000\n", COLD, 0),
    ("cold boot without the bridge line (power-on: never warn)", "1", "80000000\n", WARM_BAD.replace("20000000", "80000000"), 0),
    ("warm good: soft restart, bridge line present", "1", "20000000\n", WARM_OK, 0),
    ("warm BAD: soft restart, no bridge line -> warn", "1", "20000000\n", WARM_BAD, 1),
    ("warm bad, status read without newline", "1", "20000000", WARM_BAD, 1),
    ("warm bad, status with 0x and capitals", "1", "0x2000000A\n", WARM_BAD, 1),
    ("hardware reset, no bridge line -> warn", "1", "40000000\n", WARM_BAD, 1),
    ("PCIe reset, no bridge line -> warn", "1", "10000000\n", WARM_BAD, 1),
    ("power-on bit with others set: power-on wins", "1", "a0000000\n", WARM_BAD, 0),
    ("MLO off (today's router: no bridge line expected)", "0", "20000000\n", WARM_BAD, 0),
    ("MLO unset", "", "20000000\n", WARM_BAD, 0),
    ("the log no longer holds the boot start (rotated): decide nothing", "1", "20000000\n", ROTATED, 0),
    ("no kernel log", "1", "20000000\n", "", 0),
    ("no reset status file", "1", "", WARM_BAD, 0),
    ("status 0 (no reset bit known)", "1", "0\n", WARM_BAD, 0),
    ("SMC-style status (low bits only): unknown here", "1", "1\n", WARM_BAD, 0),
    ("malformed status", "1", "20000000 junk\n", WARM_BAD, 0),
    ("over-long status", "1", "120000000\n", WARM_BAD, 0),
]

def cstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'

if m:
    # every case above on a router that has printed the bridge line before (seen = 1, REAPER-MLOBOOT-SEEN 2026-11-23)
    calls = "".join('\tprintf("%%d\\n", rmb_owed(%s, %s, %s, %d, 1));\n' % (cstr(mld), cstr(st), cstr(kl), len(kl.encode()))
                    for _, mld, st, kl, _e in CASES)
    # a log buffer that is not NUL-terminated and ends right after the needle
    calls += '\t{ static const char b[] = "Linux version x\\ndhdpcie_bus_bridge_init"; char *k = malloc(sizeof(b) - 1); memcpy(k, b, sizeof(b) - 1);\n' \
             '\t  printf("%d\\n", rmb_owed("1", "20000000", k, sizeof(b) - 1, 1)); printf("%d\\n", rmb_owed("1", "20000000", k, sizeof(b) - 2, 1)); free(k); }\n'
    calls += '\tprintf("%d\\n", rmb_owed(NULL, "20000000", "Linux version", 13, 1)); printf("%d\\n", rmb_owed("1", NULL, "Linux version", 13, 1));\n'
    # a router whose radios have never printed the line (another radio revision may word it differently): never warn
    calls += "".join('\tprintf("%%d\\n", rmb_owed("1", %s, %s, %d, 0));\n' % (cstr(st), cstr(kl), len(kl.encode()))
                     for st, kl in (("20000000\n", WARM_BAD), ("40000000\n", WARM_BAD), ("10000000\n", WARM_BAD), ("20000000\n", WARM_OK)))
    DRV = "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n" + m.group(1) + "\nint main(void)\n{\n" + calls + "\treturn 0;\n}\n"
    work = tempfile.mkdtemp(prefix="rmb_")
    try:
        c = os.path.join(work, "d.c"); open(c, "w").write(DRV)
        exe = os.path.join(work, "d")
        cc = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-fsanitize=address,undefined",
                             "-o", exe, c], capture_output=True, text=True)
        if cc.returncode != 0:
            cc = subprocess.run([GCC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", exe, c],
                                capture_output=True, text=True)
        check("the decision (extracted from rc/reaper_mloboot.c) compiles on the host (-Wall -Wextra -Werror)", cc.returncode == 0, cc.stderr[-1200:])
        if cc.returncode == 0:
            r = subprocess.run(["setarch", "x86_64", "-R", exe] if shutil.which("setarch") else [exe], capture_output=True, text=True, timeout=60)
            check("it runs clean (no sanitizer report)", r.returncode == 0 and "ERROR" not in r.stderr, r.stderr[-600:])
            got = r.stdout.split()
            for i, (name, _m, _s, _k, exp) in enumerate(CASES):
                check(name + " -> %s" % ("warn" if exp else "no warning"), i < len(got) and got[i] == str(exp), got[i] if i < len(got) else None)
            tail = got[len(CASES):]
            check("an unterminated log buffer is searched by length: the needle at the very end counts, one byte short does not",
                  tail[:2] == ["0", "1"], tail)
            check("NULL mld_enable or NULL status: no warning", tail[2:4] == ["0", "0"], tail)
            check("the bridge line never seen on this router: a soft, hardware or PCIe restart without it does not warn",
                  tail[4:8] == ["0", "0", "0", "0"], tail)
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ------------------------------------------------------------ wiring
fn = re.search(r"void reaper_mlo_coldboot_check\(void\)\n\{(.*?)\n\}\n", mb, re.S)
body = fn.group(1) if fn else ""
check("once per boot (static guard), the log read only with MLO on, READ_ALL (3) of the ring size (10), nothing consumed",
      "static int done;" in body and "if (done)\n\t\treturn;\n\tdone = 1;" in body and 'if (nvram_match("mld_enable", "1")) {' in body
      and "klogctl(10, NULL, 0)" in body and "klogctl(3, klog, sz)" in body and "klogctl(4" not in body and "klogctl(5" not in body)
check("the flag is written every boot (0 or 1), never committed; one syslog line only when owed",
      'nvram_set("reaper_mlo_coldboot_owed", owed ? "1" : "0");' in body and "nvram_commit" not in mb
      and body.count("logmessage(") == 1 and "if (owed)\n\t\tlogmessage(" in body)
check("seen (2026-11-23): read before the decision and passed to it; written once, only when this boot's log has the line",
      "seen = rmb_seen();" in body and 'owed = rmb_owed(nvram_safe_get("mld_enable"), rs, klog, (size_t)n, seen);' in body
      and 'if (!seen && n > 0 && rmb_has(klog, (size_t)n, "dhdpcie_bus_bridge_init"))\n\t\trmb_mark_seen();' in body
      and body.find("seen = rmb_seen();") < body.find("owed = rmb_owed(") < body.find("rmb_mark_seen();") < body.find("free(klog);"))
fs = re.search(r"static int rmb_seen\(void\)\n\{(.*?)\n\}\n", mb, re.S); fm = re.search(r"static void rmb_mark_seen\(void\)\n\{(.*?)\n\}\n", mb, re.S)
check("seen: an empty regular file on /jffs, never followed through a link, created only if absent (never rewritten)",
      '#define RMB_SEEN_DIR\t"/jffs/reaper"' in mb and '#define RMB_SEEN\tRMB_SEEN_DIR "/mlo_bridge_seen"' in mb
      and fs is not None and "lstat(RMB_SEEN, &st) == 0 && S_ISREG(st.st_mode)" in fs.group(1)
      and fm is not None and "open(RMB_SEEN, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600)" in fm.group(1)
      and "write(" not in fm.group(1) and "O_TRUNC" not in mb)
check("no reboot, no notify_rc, no radio action (warn only, owner 2026-11-20)",
      not re.search(r"\breboot\s*\(|notify_rc|eval\(|system\(|kill\(", mb))
lan = rd("rc/lan.c")
check("rc/lan.c start_wl: the check right after wlready=1 (the radios are up), outside the QCA block",
      '\tnvram_set_int("wlready", 1);\n\ttimecheck();\n#endif\n\treaper_mlo_coldboot_check();' in lan and lan.count("reaper_mlo_coldboot_check();") == 1)
check("Makefile builds it, rc.h declares it",
      "OBJS += reaper_mloboot.o" in rd("rc/Makefile") and "extern void reaper_mlo_coldboot_check(void);" in rd("rc/rc.h"))
check("defaults.c: reaper_mlo_coldboot_owed = 0 (state)",
      '{ "reaper_mlo_coldboot_owed", "0", CKN_STR1, CKN_TYPE_DEFAULT, CKN_ACC_LEVEL_DEFAULT, CKN_ENC_DEFAULT, 0 },' in rd("shared/defaults.c"))
check("not carried by the settings file (state of this boot)", '"reaper_mlo_coldboot_owed"' not in rd("httpd/web.c"))
dash = rd("www/Main_ReaperDash.asp")
check("dashboard: a hidden banner shown only for owed=1 with MLO on, server-rendered with nvram_get_js, in a closure",
      'id="mlo_coldboot_badge" style="display:none' in dash and "<#RDSH_124#>" in dash and "<#RDSH_125#>" in dash
      and "if (<% nvram_get_js(\"reaper_mlo_coldboot_owed\"); %> === '1' && <% nvram_get_js(\"mld_enable\"); %> === '1'){" in dash)
mlo = rd("www/Reaper_MLO.asp")
check("MLO switch: the power-cycle note in both confirms (on and off)", mlo.count("<#RDSH_126#>") == 2
      and "lines.push(`<#AiMesh_System_Reboot_Hint#>`, `<#RDSH_126#>`, `<#AiMesh_Are_U_Sure_Proceed#>`);" in mlo
      and "`<#AiMesh_System_Reboot_Hint#>` + '\\n' + `<#RDSH_126#>`)) return false;" in mlo)
for f, t in (("rc/reaper_mloboot.c", mb), ("www/Main_ReaperDash.asp", dash), ("www/Reaper_MLO.asp", mlo)):
    check(f + ": ASCII only", not re.search(r"[^\x00-\x7f]", t))
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if re.match(r"^[A-Z]{2}\.dict$", f))
miss = []
for f in packs:
    t = open(os.path.join(www, f), encoding="utf-8").read()
    for k in ("RDSH_124", "RDSH_125", "RDSH_126"):
        mm = re.search(r"^%s=(.+)$" % k, t, re.M)
        if not mm or any(x in mm.group(1) for x in ('"', "`", "\\", "${", "</")):
            miss.append(f + ":" + k)
if os.environ.get("REAPER_SKIP_DICT"):
    print("note: dict check skipped (REAPER_SKIP_DICT)")
else:
    check("RDSH_124-126 in every language pack, quote-safe", packs and not miss, miss[:8])

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
