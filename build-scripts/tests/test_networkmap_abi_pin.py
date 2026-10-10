#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""networkmap shared-memory ABI pin: httpd's CLIENT_DETAIL_INFO_TABLE must match the prebuilt
networkmap's layout whatever the model's feature flags say (field, ZenWiFi BQ16, 2026-10-10).

WHY THIS EXISTS. networkmap is a closed prebuilt; the same ASUS binary ships on every BCM4916
model and writes the client table into shared memory key 1001. httpd (built from source) reads
it through networkmap.h, whose struct has members gated on RTCONFIG_* flags. The BQ16 and BQ16 Pro
are the only roster models built without RTCONFIG_CAPTIVE_PORTAL, so their httpd lacked
`subunit[MAX_NR_CLIENT_LIST]` and read the entry counts (which sit after it) 255 bytes early:
zero clients on the dashboard, the stock client list and every AiMesh node count, from the first
boot. The bwdpi block already carried the same pin for the same reason.

WHAT IT DOES. Extracts the struct (and the MLO typedefs it needs) from networkmap.h, compiles its
sizeof on the host under the BQ16 flag set and under the RT-BE96U flag set, and requires both to be
equal - and equal again with the bwdpi/captive flags toggled. Then pins the text: no #if above
`subunit`, the bwdpi members unconditional, the counters after both.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
H = os.path.join(SRC, "networkmap", "networkmap.h")
if not SRC or not os.path.isfile(H):
    skip("no router source tree with networkmap/networkmap.h (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

src = open(H, encoding="latin-1").read()
lines = src.split("\n")
end = next(i for i, l in enumerate(lines) if "} CLIENT_DETAIL_INFO_TABLE" in l)
start = max(i for i, l in enumerate(lines[:end]) if l.startswith("typedef struct"))
struct = lines[start:end + 1]
body = "\n".join(struct)

# ---------------------------------------------------------------- text pins
i_sub = next((i for i, l in enumerate(struct) if re.search(r"\bsubunit\[MAX_NR_CLIENT_LIST\]", l)), None)
check("the struct carries subunit[MAX_NR_CLIENT_LIST]", i_sub is not None)
if i_sub is not None:
    above = [l.strip() for l in struct[max(0, i_sub - 12):i_sub]]
    gated = any(l.startswith("#if") for l in above) and not any(l.startswith("#endif") for l in above[-(len(above)):] if False)
    # a gate is an #if/#ifdef between the previous #endif and the member
    depth = 0
    for l in struct[:i_sub]:
        s = l.strip()
        if s.startswith("#if"): depth += 1
        elif s.startswith("#endif"): depth -= 1
    check("subunit is NOT inside any #if block (unconditional, like the bwdpi pin)", depth == 0, "depth=%d" % depth)
i_bw = next((i for i, l in enumerate(struct) if "bwdpi_host[" in l), None)
i_cnt = next((i for i, l in enumerate(struct) if re.search(r"\bint\s+ip_mac_num;", l)), None)
check("bwdpi_host and the counters are present", i_bw is not None and i_cnt is not None)
if i_sub is not None and i_bw is not None and i_cnt is not None:
    check("order: subunit, then the bwdpi block, then ip_mac_num (the counters sit after both)", i_sub < i_bw < i_cnt)
    depth = 0
    for l in struct[:i_bw]:
        s = l.strip()
        if s.startswith("#if"): depth += 1
        elif s.startswith("#endif"): depth -= 1
    check("the bwdpi block is unconditional too", depth == 0, "depth=%d" % depth)

# ---------------------------------------------------------------- sizeof under both flag sets
# the MLO typedefs the struct references (mlo_band_t, mlo_link_info_t)
m = re.search(r"#ifdef RTCONFIG_MLO\s*\ntypedef enum \{.*?\} mlo_link_info_t;\s*\n#endif", src, re.S)
mlo_block = m.group(0) if m else ""
check("the MLO typedefs were found for the harness", bool(mlo_block))
def find_define(name):
    for root in (os.path.join(SRC, "shared"), os.path.join(SRC, "networkmap"), os.path.join(SRC, "httpd")):
        for dp, _, fs in os.walk(root):
            for f in fs:
                if not f.endswith(".h"): continue
                try: t = open(os.path.join(dp, f), encoding="latin-1").read()
                except OSError: continue
                mm = re.search(r"#define\s+%s\s+\(?(\d+)\)?" % re.escape(name), t)
                if mm: return int(mm.group(1))
    return None
mlo_all = find_define("MLO_ALL_MAC_LEN")
check("MLO_ALL_MAC_LEN resolved from the tree", mlo_all is not None, "fell back to 128")
if mlo_all is None: mlo_all = 128

HARNESS = r'''
#include <stdio.h>
#include <stdint.h>
#include <time.h>
#define MAX_NR_CLIENT_LIST 255
#define MLO_ALL_MAC_LEN @@MLOALL@@
@@MLO@@
@@STRUCT@@
int main(void) { printf("%zu\n", sizeof(CLIENT_DETAIL_INFO_TABLE)); return 0; }
'''
td = tempfile.mkdtemp(prefix="nmp-abi.")
sizes = {}
try:
    c = os.path.join(td, "t.c")
    with open(c, "w") as f:
        f.write(HARNESS.replace("@@MLOALL@@", str(mlo_all)).replace("@@MLO@@", mlo_block).replace("@@STRUCT@@", body))
    base = ["-DRTCONFIG_IPV6", "-DRTCONFIG_MULTILAN_CFG", "-DRTCONFIG_MLO"]
    sets = {
        "RT-BE96U/GT-BE98/BE86U/BE88U (captive portal on)": base + ["-DRTCONFIG_CAPTIVE_PORTAL"],
        "BQ16/BQ16 Pro (captive portal off)": base,
        "captive portal on + FBWIFI": base + ["-DRTCONFIG_CAPTIVE_PORTAL", "-DRTCONFIG_FBWIFI"],
        "bwdpi flag on (the older pin)": base + ["-DRTCONFIG_CAPTIVE_PORTAL", "-DRTCONFIG_BWDPI"],
    }
    for name, flags in sets.items():
        exe = os.path.join(td, "t")
        p = subprocess.run([CC, "-std=gnu99", "-w"] + flags + ["-o", exe, c], capture_output=True, text=True)
        if p.returncode != 0:
            check("harness compiles for: " + name, False, p.stderr[-400:]); continue
        sizes[name] = int(subprocess.run([exe], capture_output=True, text=True).stdout.strip() or 0)
        print("     sizeof(CLIENT_DETAIL_INFO_TABLE) %-50s = %d" % (name, sizes[name]))
finally:
    shutil.rmtree(td, ignore_errors=True)
check("one layout for every flag set (the prebuilt networkmap writes exactly one)",
      len(sizes) == 4 and len(set(sizes.values())) == 1, sizes)

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: httpd's client table matches the prebuilt networkmap on every model's flag set")
