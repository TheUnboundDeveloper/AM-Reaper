#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASUS drop intake, batch p11 (2026-11-18) - the newline guard RUN, the RT-BE96U 6717a0 firmware, the BQ16 Pro guards.

WHY. ASUS GPL 102_39448 changed nvram_safe_get() in Broadcom's bcmnvram.h (a static inline compiled into every open
program): a value that holds a newline or carriage return comes back "" (logged "nvram_safe_get: blocked newline in
key %s") unless its key is one of ten multi-line keys. Reaper took it verbatim (REAPER-NVRAM-NEWLINE). Its stock-only
radio firmware intake replaced the RT-BE96U early-unit firmware 6717a0 (Merlin's 2025-10 file, microcode 1892.42713)
with stock 39435's (1892.42726). On the alpha line the BQ16 Pro moved to GPL 102_39442 closed objects, so three
guards that existed for its 102_39256 objects now cover the BQ16 only: the late init_switch_pre() timing and the LAN
power-cycle exclusion (39442 source calls init_switch_pre() in init_switch()), the CVE-2026-19386 config-upload route
(39442's handler equals the fixed 40585 one) and the legacy licence set (39442 ships 1119 / 1212 / 1296).
WHAT IT CHECKS.
  1. bcmnvram.h: marker, ASUS's exact allow-list, and the REAL function extracted and compiled on the host with a stub
     nvram: a multi-line value under a key off the list -> "" and one log call (\\n and \\r), every listed key passes
     through, a near-miss key (vpn_client6_custom) is blocked, plain values / missing keys unchanged.
  2. Dev and alpha trees: RT-BE96U 6717a0 = stock 39435 (sha256 24fc4e7e0ef7eede..., microcode 1892.42726).
  3. Alpha tree (it carries the compatibility layer): the three guards and the licence set name the BQ16 only.
Exit 0 pass, 1 fail, 77 skipped (no router source tree or no host compiler).
"""
import os, re, shutil, subprocess, sys, tempfile, hashlib

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
REL = os.path.dirname(os.path.dirname(os.path.abspath(SRC))) if SRC else ""
H = os.path.join(REL, "src-rt-5.04behnd.4916/bcmdrivers/broadcom/net/wl/impl103/main/src/include/bcmnvram.h")
if not SRC or not os.path.isfile(H):
    print("SKIP: no router source tree"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no host C compiler"); sys.exit(77)
TREE = os.path.dirname(REL)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))
def read(p): return open(p, encoding="utf-8", errors="surrogateescape").read()

ALLOW = ["vpn_server_custom", "vpn_server1_custom", "vpn_client_custom", "vpn_client1_custom", "vpn_client2_custom",
         "vpn_client3_custom", "vpn_client4_custom", "vpn_client5_custom", "sshd_authkeys", "fb_comment"]
h = read(H)
check("bcmnvram.h carries the guard marker REAPER-NVRAM-NEWLINE", "REAPER-NVRAM-NEWLINE" in h)
m = re.search(r"newline_allowed\[\] = \{(.*?)NULL", h, re.S)
lst = re.findall(r'"([^"]+)"', m.group(1)) if m else []
check("allow-list is exactly ASUS 102_39448's ten keys", lst == ALLOW, lst)
check("<syslog.h> is included outside the kernel", "#ifndef __KERNEL__\n#include <syslog.h>\n#endif" in h)
i = h.find("static INLINE char *\nnvram_safe_get(const char *name)")
j = h.find("\n}\n", i)
fn = h[i:j + 3] if i >= 0 and j > i else ""
check("nvram_safe_get() found in bcmnvram.h", bool(fn))
if fn:
    fn = fn.replace("static INLINE", "static inline").replace("syslog(LOG_WARNING,", "test_log(LOG_WARNING,")
    prog = r'''
#include <stdio.h>
#include <string.h>
#include <syslog.h>
static int logged; static char lastkey[64];
static void test_log(int pri, const char *fmt, const char *k) { (void)pri; (void)fmt; logged++; snprintf(lastkey, sizeof lastkey, "%s", k); }
static const char *K[16], *V[16]; static int NV;
static char *nvram_get(const char *name) { for (int i = 0; i < NV; i++) if (!strcmp(K[i], name)) return (char *)V[i]; return NULL; }
''' + fn + r'''
static void set(const char *k, const char *v) { K[NV] = k; V[NV] = v; NV++; }
int main(void) {
  set("lan_ipaddr", "192.0.2.1"); set("inject", "1;\nreboot"); set("inject_cr", "a\rb");
  set("vpn_client6_custom", "x\ny"); set("empty", "");
  const char *allow[] = {"vpn_server_custom","vpn_server1_custom","vpn_client_custom","vpn_client1_custom","vpn_client2_custom",
                         "vpn_client3_custom","vpn_client4_custom","vpn_client5_custom","sshd_authkeys","fb_comment"};
  for (int i = 0; i < 10; i++) set(allow[i], "line1\nline2");
  printf("plain=%s\n", nvram_safe_get("lan_ipaddr"));
  printf("missing=[%s]\n", nvram_safe_get("nokey"));
  printf("empty=[%s]\n", nvram_safe_get("empty"));
  /* call first, then read the counter: argument evaluation order is unspecified */
  int l0 = logged; const char *r = nvram_safe_get("inject"); printf("inject=[%s] logged=%d key=%s\n", r, logged - l0, lastkey);
  l0 = logged; r = nvram_safe_get("inject_cr"); printf("inject_cr=[%s] logged=%d\n", r, logged - l0);
  l0 = logged; r = nvram_safe_get("vpn_client6_custom"); printf("nearmiss=[%s] logged=%d\n", r, logged - l0);
  int pass = 0; l0 = logged;
  for (int i = 0; i < 10; i++) if (!strcmp(nvram_safe_get(allow[i]), "line1\nline2")) pass++;
  printf("allowed_pass=%d logged=%d\n", pass, logged - l0);
  return 0;
}
'''
    td = tempfile.mkdtemp(prefix="p11nv_")
    c = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(c, "w").write(prog)
    r = subprocess.run([CC, "-O1", "-Wall", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("the extracted guard compiles cleanly (-Wall -Werror)", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        out = subprocess.run([exe], capture_output=True, text=True).stdout
        check("a plain value comes back unchanged", "plain=192.0.2.1" in out, out)
        check("a missing key and an empty value come back empty", "missing=[]" in out and "empty=[]" in out, out)
        check("a value with a newline under an unlisted key -> empty, logged once with its key", "inject=[] logged=1 key=inject" in out, out)
        check("a carriage return is blocked the same way", "inject_cr=[] logged=1" in out, out)
        check("a near-miss key (vpn_client6_custom) is blocked - the list is exact", "nearmiss=[] logged=1" in out, out)
        check("all ten listed keys pass a multi-line value through, nothing logged", "allowed_pass=10 logged=0" in out, out)
    shutil.rmtree(td, ignore_errors=True)

# ---- 2. RT-BE96U 6717a0 on the Dev and alpha trees
br = subprocess.run(["git", "-C", TREE, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
F17 = os.path.join(REL, "src-rt-5.04behnd.4916/bcmdrivers/broadcom/net/wl/impl103/sys/src/dongle/sysdeps/RT-BE96U/6717a0/rtecdc.bin")
if br in ("be96u-only", "be96u-unify") and os.path.isfile(F17):
    b = open(F17, "rb").read(); s = hashlib.sha256(b).hexdigest()
    check("RT-BE96U 6717a0 = stock 39435's file (24fc4e7e0ef7eede...)", s.startswith("24fc4e7e0ef7eede"), s[:16])
    check("RT-BE96U 6717a0 microcode 1892.42726 (was Merlin's 1892.42713)", b"1892.42726" in b)
else:
    print(f"note: tree on '{br}' - the RT-BE96U 6717a0 refresh is a Dev / alpha change, not checked here")

# ---- 3. alpha tree: BQ16 Pro guards
R = os.path.abspath(SRC)
if os.path.isfile(os.path.join(R, "rc/reaper_legacy_blobs_shim.c")):
    ib = read(os.path.join(R, "rc/sysdeps/init-broadcom.c")); ini = read(os.path.join(R, "rc/init.c")); web = read(os.path.join(R, "httpd/web.c"))
    bfs = read(os.path.join(REL, "src-rt-5.04behnd.4916/targets/buildFS"))
    check("LAN power-cycle exclusion: BQ16 only", "#if defined(BCM6813) && !(defined(RTCONFIG_REAPER_LEGACY_BLOBS) && defined(BQ16))" in ib
          and "(defined(BQ16) || defined(BQ16_PRO))" not in ib)
    check("late init_switch_pre(): BQ16 only (init.c)", "#if defined(RTCONFIG_REAPER_LEGACY_BLOBS) && defined(BQ16)\n" in ini
          and "(defined(BQ16) || defined(BQ16_PRO))" not in ini)
    check("CVE-2026-19386 config-upload route served for the BQ16 Pro",
          "#if !defined(RTCONFIG_REAPER_LEGACY_BLOBS) || defined(BQ16_PRO)" in web)
    check("legacy licence set (1077 / 1079 / 1080): BQ16 only", 'if [ "$BUILD_NAME" = "BQ16" ]; then' in bfs
          and '[ "$BUILD_NAME" = "BQ16_PRO" ]' not in bfs)
else:
    print("note: no compatibility layer in this tree - the alpha-line BQ16 Pro guards are not checked here")

# ---- 4. batch p13: infosvr (all lines), the 102.8 line's 40585 hardening and Wi-Fi scripts
inf = read(os.path.join(R, "infosvr/common.c"))
m = inf.find("case NET_CMD_ID_GETINFO_MANU:")
# the case runs to its break (a commented-out "// case NET_CMD_ID_GETINFO:" sits right under the label)
man = inf[m:inf.find("break;", m)] if m >= 0 else ""
check("infosvr GETINFO_MANU: PrinterInfo written with snprintf(sizeof), no sprintf / strcpy left in that case",
      # >= 2: the case falls through into GETINFO, which has its own two bounded writes
      man.count("snprintf(ginfo->PrinterInfo, sizeof(ginfo->PrinterInfo)") >= 2
      and "sprintf(ginfo->PrinterInfo, \"" not in man.replace("snprintf", "")
      and "strcpy(ginfo->" not in man, man[:400])
WL = os.path.join(REL, "src-rt-5.04behnd.4916/router-sysdep.rt-be96u/wlan/scripts/wlinc.sh")
if os.path.isfile(WL):
    wl = read(WL)   # code lines only: the fixed file's comment explains the bug and quotes "=~"
    code = "\n".join(x for x in wl.splitlines() if not x.lstrip().startswith("#"))
    check("wlinc.sh: no [[ =~ ]] (busybox ash has none) - the decimal CPU mask is converted with a POSIX case",
          "=~" not in code and "''|*[!0-9]*) ;;" in code)
if br == "be96u-102.8":
    web = read(os.path.join(R, "httpd/web.c")); svc = read(os.path.join(R, "rc/services.c"))
    check("102.8 web.c: no websWrite(stream, json..., ret) format-string call left", "websWrite(stream, json_object_to_json_string(retObj), ret);" not in web)
    check("102.8 web.c: the CA upload file name is checked at all three places", web.count("is_valid_cert_filename(token)") == 3)
    check("102.8 web.c: iperf3 server and client accept only their start / stop services",
          'strcmp(rc_service, "start_iperf3_server") != 0' in web and 'strcmp(rc_service, "start_iperf3_client") != 0' in web)
    check("102.8 web.c: the four diag handlers bound duration / point and compute the start time in 64 bits",
          web.count("long long query_start_time_64") == 4 and "query_start_time = query_end_time - query_point*query_duration;" not in web)
    check("102.8 services.c: start_dnsmasq copies the DHCP range with strlcpy", 'strlcpy(dhcp_start, nvram_safe_get("dhcp_start"), sizeof(dhcp_start));' in svc
          and 'strcpy(dhcp_start, nvram_safe_get("dhcp_start"));' not in svc)
    bfs8 = read(os.path.join(REL, "src-rt-5.04behnd.4916/targets/buildFS"))
    check("102.8 licences: 1296 in pakl, removed again for the BQ16 / BQ16 Pro only",
          os.path.isfile(os.path.join(REL, "src-rt-5.04behnd.4916/targets/pakl/Broadcom-PAK_License-1296.Asus_BQ16_BQ16_PRO.bin"))
          and 'if [ "$BUILD_NAME" = "BQ16" ] || [ "$BUILD_NAME" = "BQ16_PRO" ]; then\n\t\trm -f $TARGETS_DIR/$ROOTFS/rom/etc/licenses/*1296*.bin' in bfs8)

if fails:
    print("\n%d check(s) failed" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
