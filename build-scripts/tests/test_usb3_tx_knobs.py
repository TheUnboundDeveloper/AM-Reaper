#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USB 3 write-speed levers on the BCM4912 / BCM6813 family (RT-BE96U field report, 2026-11-01).

WHY THIS EXISTS. USB 3 writes on this family run at about half of reads (SNBForums thread 98134: RT-BE96U and
GT-AX6000 ~170-190 MB/s writes vs ~350-380 MB/s reads; RT-BE92U / RT-AX88U balanced). The host controller is a
DWC_usb31 behind the UBUS fabric, and the firmware programs neither its global registers nor the USB master's
fabric credits - every value is a silicon default (USB->BIU route credits 4, against 7-12 for PCIe; TX packet
threshold off; SS park mode on; read attributes 0). The glue now takes five module parameters for those
levers, which rc passes from nvram only when a key is set, so each can be A/B tested with a reboot and the
hardware stays at its defaults on every box that sets nothing.

WHAT IT CHECKS. (1) The glue: the parameters exist, the tuning runs inside the xhci-gbl block BEFORE the xhci
platform device is added (no traffic), only on a DWC_usb31 id, and only when a parameter is set. (2) The register
math, by compiling the glue's plain-C block on the host: GTXTHRCFG packet-count mode sets bit 26, count in
25:21, burst in 20:16 and keeps the periodic fields; count 1..8 (the SS bulk FIFO holds 8 packets), count <=
burst <= 16; GSBUSCFG0 read attributes land in 31:24 only; the DWC_usb31 id test. (3) rc: the nvram->insmod
helper accepts digits only (an nvram value becomes an insmod argument), each key is passed only when set, the
DCM switch writes the live sysfs parameter. (4) Markers for the staged image are present.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "usb.c")):
    print("SKIP: no router source tree"); sys.exit(77)
PLAT = os.environ.get("REAPER_PLATFORM_SRC") or os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916"))  # release/src/router -> release/src-rt-...
GLUE = os.path.join(PLAT, "bcmdrivers", "opensource", "bus", "usb", "impl1", "bcm_bca_usb_xhci.c")
if not os.path.isfile(GLUE):
    print("SKIP: no platform tree (%s)" % GLUE); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

g = open(GLUE, encoding="utf-8").read()
rc = open(os.path.join(SRC, "rc", "usb.c"), encoding="utf-8").read()

# ---------- (1) glue structure ----------
for p in ("ubus_credits", "txthr_cnt", "txthr_burst", "parkmode_off", "rd_attr"):
    check("glue: module parameter %s" % p, re.search(r"module_param\(%s, " % p, g) is not None)
check("glue: rd_attr defaults to -1 (0 is a real value) and the others to 0",
      "static int rd_attr = -1;" in g and "static int ubus_credits = 0;" in g and "static int txthr_cnt = 0;" in g)
call = g.find("reaper_usb3_tune(pdev, xhci_gbl);")
add = g.find("platform_device_add(bca_pdata->xhci)")
gbl_map = g.find('platform_get_resource_byname(pdev, IORESOURCE_MEM, "xhci-gbl")')
check("glue: tuning runs after the xhci-gbl map and BEFORE the xhci platform device is added",
      -1 < gbl_map < call < add, (gbl_map, call, add))
body = g[g.find("static void reaper_usb3_tune("):g.find("static struct of_device_id const bcm_bca_usb_xhci_of_match")]
check("glue: returns at once when no parameter is set (hardware defaults untouched)",
      re.search(r"if \(!ubus_credits && !txthr_cnt && !txthr_burst && !parkmode_off && rd_attr < 0\)\s*return;", body) is not None)
check("glue: DWC_usb31 id gate before any write", body.find("rp_dwc31_is(id)") < body.find("ubus_master_set_token_credits"))
check("glue: credits go to the USB master toward BIU", "ubus_master_set_token_credits(UBUS_PORT_ID_USB, UBUS_PORT_ID_BIU, ubus_credits)" in body)
check("glue: every applied change is logged with old and new value", body.count("dev_info(") >= 5 and "0x%08x -> 0x%08x" in body)
check("glue: register offsets inside xhci-gbl (0xc100): GSBUSCFG0 0, GTXTHRCFG 8, GUCTL1 0x1c, GSNPSID 0x20",
      all(s in g for s in ("#define RP_GBL_GSBUSCFG0 0x00", "#define RP_GBL_GTXTHRCFG 0x08", "#define RP_GBL_GUCTL1    0x1c", "#define RP_GBL_GSNPSID   0x20")))
check("glue: includes bcm_ubus4.h for the credit call", "#include <bcm_ubus4.h>" in g)

# ---------- (2) register math on the host ----------
m = re.search(r"/\* REAPER_USB3_PURE_BEGIN.*?\*/\n(.*?)/\* REAPER_USB3_PURE_END \*/", g, re.S)
check("glue: plain-C block present for the host compile", m is not None)
CC = shutil.which("gcc") or shutil.which("cc")
if m and CC:
    work = tempfile.mkdtemp(prefix="usb3k_")
    try:
        src = m.group(1) + r'''
#include <stdio.h>
int main(void)
{
    unsigned int r = 0;
    r |= (rp_dwc31_is(0x33313130u) == 1) ? 0 : 1u << 0;        /* the RT-BE96U core */
    r |= (rp_dwc31_is(0x5533300au) == 0) ? 0 : 1u << 1;        /* a DWC_usb3 is not */
    r |= (rp_txthr_value(0x00F00000u, 3, 16) == 0x04700000u) ? 0 : 1u << 2;
    r |= (rp_txthr_value(0x00F00000u, 4, 8) == 0x04880000u) ? 0 : 1u << 3;
    r |= (rp_txthr_value(0x00F0F3FFu, 8, 16) == 0x0510F3FFu) ? 0 : 1u << 4;  /* periodic fields kept */
    r |= (rp_txthr_valid(3, 16) && rp_txthr_valid(1, 1) && rp_txthr_valid(8, 16)) ? 0 : 1u << 5;
    r |= (!rp_txthr_valid(0, 16) && !rp_txthr_valid(9, 16) && !rp_txthr_valid(5, 4) && !rp_txthr_valid(1, 17) && !rp_txthr_valid(3, 0)) ? 0 : 1u << 6;
    r |= (rp_rdattr_value(0x00000001u, 2) == 0x22000001u) ? 0 : 1u << 7;
    r |= (rp_rdattr_value(0x22000001u, 0) == 0x00000001u) ? 0 : 1u << 8;
    r |= (rp_rdattr_value(0x00FF0001u, 15) == 0xFFFF0001u) ? 0 : 1u << 9;  /* write attrs untouched */
    printf("%u\n", r);
    return 0;
}
'''
        p = os.path.join(work, "k.c"); open(p, "w").write(src)
        b = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-o", os.path.join(work, "k"), p],
                           capture_output=True, text=True)
        check("register math compiles on the host (-Wall -Wextra -Werror)", b.returncode == 0, b.stderr[-600:])
        if b.returncode == 0:
            out = subprocess.run([os.path.join(work, "k")], capture_output=True, text=True).stdout.strip()
            check("register math: every case right (bitmask of failures = 0)", out == "0", "failures bitmask " + out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
elif m:
    print("note: no host compiler - math checks skipped")

# ---------- (3) rc ----------
hm = re.search(r"/\* REAPER_USB3_PARAM_BEGIN.*?\*/\n(.*?)/\* REAPER_USB3_PARAM_END \*/", rc, re.S)
check("rc: nvram->insmod helper present", hm is not None)
if hm and CC:
    work = tempfile.mkdtemp(prefix="usb3p_")
    try:
        src = r'''
#include <stdio.h>
#include <string.h>
#include <stddef.h>
static const char *NV;
static char *nvram_get(const char *n) { (void)n; return (char *)NV; }
''' + hm.group(1) + r'''
int main(void)
{
    char b[32]; unsigned int r = 0;
    NV = "8";          r |= (reaper_usb3_param(b, sizeof b, "ubus_credits", "k") == 1 && !strcmp(b, "ubus_credits=8")) ? 0 : 1u << 0;
    NV = "";           r |= (reaper_usb3_param(b, sizeof b, "x", "k") == 0) ? 0 : 1u << 1;
    NV = NULL;         r |= (reaper_usb3_param(b, sizeof b, "x", "k") == 0) ? 0 : 1u << 2;
    NV = "4 foo=1";    r |= (reaper_usb3_param(b, sizeof b, "x", "k") == 0) ? 0 : 1u << 3;   /* no second argument */
    NV = "-1";         r |= (reaper_usb3_param(b, sizeof b, "x", "k") == 0) ? 0 : 1u << 4;
    NV = "123456";     r |= (reaper_usb3_param(b, sizeof b, "x", "k") == 0) ? 0 : 1u << 5;   /* over 5 digits */
    NV = "0";          r |= (reaper_usb3_param(b, sizeof b, "parkmode_off", "k") == 1 && !strcmp(b, "parkmode_off=0")) ? 0 : 1u << 6;
    printf("%u\n", r);
    return 0;
}
'''
        p = os.path.join(work, "p.c"); open(p, "w").write(src)
        b = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", os.path.join(work, "p"), p], capture_output=True, text=True)
        check("rc helper compiles on the host", b.returncode == 0, b.stderr[-600:])
        if b.returncode == 0:
            out = subprocess.run([os.path.join(work, "p")], capture_output=True, text=True).stdout.strip()
            check("rc helper: digits only, nothing else becomes an insmod argument (bitmask = 0)", out == "0", "failures bitmask " + out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
blk = rc[rc.find('argv[n++] = "insmod";'):rc.find("_eval(argv, NULL, 0, NULL);")] if 'argv[n++] = "insmod";' in rc else ""
for param, key in (("ubus_credits", "reaper_usb3_credits"), ("txthr_cnt", "reaper_usb3_txthr_cnt"), ("txthr_burst", "reaper_usb3_txthr_burst"),
                   ("parkmode_off", "reaper_usb3_parkoff"), ("rd_attr", "reaper_usb3_rdattr")):
    check("rc: %s passed from nvram %s, only when set" % (param, key), ('"%s", "%s"' % (param, key)) in blk)
check("rc: usb3_enable still comes first, unchanged", 'argv[n++] = (nvram_get_int("usb_usb3") == 1) ? "usb3_enable=1" : "usb3_enable=0";' in blk)
check("rc: the levers are compiled for BCM4912 / BCM6813 only", "#if defined(BCM4912) || defined(BCM6813)" in blk)
check("rc: DCM switch writes the live sysfs parameter only on an explicit \"0\"",
      'nvram_match("reaper_usb3_dcm", "0")' in blk and '"/sys/module/ubus4_dcm/parameters/enable", "0"' in blk)
check("rc: argv is NULL-terminated and within its size (10 slots, max 8 used)", "argv[n] = NULL;" in rc and "char *argv[10]" in rc)
check("rc: the helper is defined BEFORE add_usb_host_modules(), which calls it (a later static definition after an implicit use fails the compile)",
      -1 < rc.find("REAPER_USB3_PARAM_BEGIN") < rc.find("add_usb_host_modules("))

# ---------- (4) markers ----------
mk = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "verify_markers.txt")
mkt = open(mk, encoding="utf-8", errors="replace").read() if os.path.isfile(mk) else ""
check("markers: module parameters and the rc keys are checked in the staged image",
      "lib/modules/4.19.294/extra/bcm_bca_usb.ko|ubus_credits|1" in mkt and "sbin/rc|reaper_usb3_credits|1" in mkt)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
