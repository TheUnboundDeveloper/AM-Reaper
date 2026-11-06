#!/usr/bin/env python3
"""Conntrack helpers by explicit rule only (audit E-13, owner 2026-11-05: "FTP/PPTP helper off by default").

WHY. Stock wrote nf_conntrack_helper=1: every loaded helper attached itself to every connection on its port, so any
LAN client's FTP session got the ALG and a hostile FTP server's PASV/PORT reply opened RELATED pinholes towards that
client (PPTP likewise). rc now writes 0 and rc/reaper_cthelper.c attaches each helper with a raw-table CT rule only
where it is wanted.

WHAT IT CHECKS. Compiles rc/reaper_cthelper.c on the host against stub rc.h/shared.h that record every argv, and runs
it for each switch combination: traffic to the router itself (own FTP server, a port-forwarded FTP port, the PPTP
server) always gets its helper; LAN clients going out get FTP only with nf_ftp=1 and PPTP only while PPTP passthrough
is on; RTSP / H.323 / SIP follow their switches; the router's own outgoing PPTP keeps it; IPv6 FTP/SIP; chains are
flushed and hooked once. Pins the wiring (sysctl 0, the three call sites, the default, the Makefile).
Exit 0 pass, 1 fail, 77 skipped.
"""
import os, shutil, subprocess, sys, tempfile
SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
F = os.path.join(SRC, "rc", "reaper_cthelper.c")
if not SRC or not os.path.isfile(F):
    print("SKIP: no router source tree with rc/reaper_cthelper.c"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no host compiler"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="replace").read()

STUB = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int nv_n; static char nv_k[32][32], nv_v[32][32];
static const char *nvram_safe_get(const char *k) { int i; for (i = 0; i < nv_n; i++) if (!strcmp(nv_k[i], k)) return nv_v[i]; return ""; }
static int nvram_match(const char *k, const char *v) { return !strcmp(nvram_safe_get(k), v); }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int ipv6_enabled(void) { return nvram_match("ipv6", "1"); }
static int _eval(char *const argv[], const char *path, int t, int *pid) { int i; (void)path; (void)t; (void)pid;
  for (i = 0; argv[i]; i++)
    printf("%s%s", i ? " " : "", argv[i]);
  printf("\n");
  /* -C (is the hook there?) fails the first time only */
  return (argv[3] && !strcmp(argv[3], "-C")) ? 1 : 0; }
'''
MAIN = r'''
int main(int argc, char **argv) { int i; for (i = 1; i < argc && nv_n < 32; i++) { char *e = strchr(argv[i], '='); if (!e) continue;
  *e = 0; snprintf(nv_k[nv_n], 32, "%s", argv[i]); snprintf(nv_v[nv_n++], 32, "%s", e + 1); }
  reaper_ct_helpers(); return 0; }
'''
w = tempfile.mkdtemp(prefix="cth_")
try:
    os.makedirs(os.path.join(w, "inc"))
    open(os.path.join(w, "inc", "rc.h"), "w").write(STUB)
    open(os.path.join(w, "inc", "shared.h"), "w").write("")
    c = os.path.join(w, "t.c"); open(c, "w").write(open(F).read() + MAIN)
    exe = os.path.join(w, "t")
    b = subprocess.run([CC, "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-I", os.path.join(w, "inc"), "-o", exe, c], capture_output=True, text=True)
    check("rc/reaper_cthelper.c compiles on the host with -Wall -Wextra -Werror", b.returncode == 0, b.stderr[-800:])
    if b.returncode == 0:
        run = lambda *nv: subprocess.run([exe] + list(nv), capture_output=True, text=True).stdout.splitlines()
        base = run()
        adds = [l for l in base if " -A " in l]
        check("defaults: the router's own FTP (21) and PPTP (1723) get their helper; nothing for LAN clients except PPTP passthrough",
              "iptables -t raw -A REAPER_CTH -p tcp -m addrtype --dst-type LOCAL --dport 21 -j CT --helper ftp" in adds
              and "iptables -t raw -A REAPER_CTH -p tcp -m addrtype --dst-type LOCAL --dport 1723 -j CT --helper pptp" in adds
              and "iptables -t raw -A REAPER_CTH -p tcp -m addrtype ! --dst-type LOCAL --dport 1723 -j CT --helper pptp" in adds
              and not any("! --dst-type LOCAL --dport 21 " in l for l in adds), adds)
        check("defaults: the router's own outgoing PPTP keeps the helper (OUTPUT)",
              "iptables -t raw -A REAPER_CTHO -p tcp --dport 1723 -j CT --helper pptp" in adds, adds)
        check("each chain is created, flushed and hooked once (the hook only when -C says it is missing)",
              "iptables -t raw -F REAPER_CTH" in base and "iptables -t raw -I PREROUTING 1 -j REAPER_CTH" in base
              and "iptables -t raw -I OUTPUT 1 -j REAPER_CTHO" in base)
        a = [l for l in run("nf_ftp=1") if " -A " in l]
        check("FTP passthrough on: LAN clients' FTP gets the ALG", "iptables -t raw -A REAPER_CTH -p tcp -m addrtype ! --dst-type LOCAL --dport 21 -j CT --helper ftp" in a, a)
        a = [l for l in run("fw_pt_pptp=0") if " -A " in l]
        check("PPTP passthrough off: no helper for LAN clients' PPTP, the router's own kept",
              not any("! --dst-type LOCAL --dport 1723" in l for l in a) and any("--dst-type LOCAL --dport 1723" in l for l in a), a)
        a = [l for l in run("nf_pptp=0") if " -A " in l]
        check("nf_pptp=0 (module unloaded): no PPTP rule at all (a CT rule would load it again)", not any("pptp" in l for l in a), a)
        a = [l for l in run("ftp_enable=1", "ftp_port=2121", "vts_ftpport=2121") if " -A " in l]
        check("own FTP server on 2121 + a port-forward on the same port: one rule, 21,2121, through multiport",
              "iptables -t raw -A REAPER_CTH -p tcp -m addrtype --dst-type LOCAL -m multiport --dports 21,2121 -j CT --helper ftp" in a, a)
        a = [l for l in run("vts_ftpport=990") if " -A " in l]
        check("a port-forwarded FTP server keeps its ALG (raw PREROUTING is before DNAT: the router's own address)",
              "iptables -t raw -A REAPER_CTH -p tcp -m addrtype --dst-type LOCAL -m multiport --dports 21,990 -j CT --helper ftp" in a, a)
        a = [l for l in run("fw_pt_rtsp=1", "fw_pt_h323=1", "fw_pt_sip=1") if " -A " in l]
        check("RTSP / H.323 / SIP passthrough on: their helpers by port, both directions",
              "iptables -t raw -A REAPER_CTH -p tcp -m multiport --dports 554,8554 -j CT --helper rtsp" in a
              and "iptables -t raw -A REAPER_CTH -p tcp --dport 1720 -j CT --helper Q.931" in a
              and "iptables -t raw -A REAPER_CTH -p udp --dport 1719 -j CT --helper RAS" in a
              and "iptables -t raw -A REAPER_CTH -p udp --dport 5060 -j CT --helper sip" in a, a)
        check("RTSP / H.323 / SIP off by default", not any(h in " ".join(adds) for h in ("rtsp", "Q.931", "RAS", "sip")))
        a = [l for l in run("ipv6=1", "nf_ftp=1", "fw_pt_sip=1") if l.startswith("ip6tables") and " -A " in l]
        check("IPv6: FTP (own + passthrough) and SIP, no PPTP",
              "ip6tables -t raw -A REAPER_CTH -p tcp -m addrtype --dst-type LOCAL --dport 21 -j CT --helper ftp" in a
              and "ip6tables -t raw -A REAPER_CTH -p tcp -m addrtype ! --dst-type LOCAL --dport 21 -j CT --helper ftp" in a
              and any("helper sip" in l for l in a) and not any("pptp" in l for l in a), a)
        check("IPv6 untouched while IPv6 is off", not any(l.startswith("ip6tables") for l in base))
finally:
    shutil.rmtree(w, ignore_errors=True)

common, mk, rch, dfl = rd("rc/common.c"), rd("rc/Makefile"), rd("rc/rc.h"), rd("shared/defaults.c")
check("rc: automatic helper assignment off", 'nf_conntrack_helper", "0", 0, 0);' in common and 'nf_conntrack_helper", "1"' not in common)
check("rc: the rules are rebuilt at every module change and every firewall start (3 call sites)", common.count("reaper_ct_helpers();") == 3)
check("rc: built and declared", "OBJS += reaper_cthelper.o" in mk and "extern void reaper_ct_helpers(void);" in rch)
check("defaults: the FTP ALG for LAN clients is off (nf_ftp 0)", '{ "nf_ftp", "0",' in dfl)
nat = rd("www/Reaper_NAT.asp")
check("NAT page: the FTP Passthrough switch reads and writes nf_ftp like the other ALG switches (an optional OFF has a GUI switch)",
      'id="t_ftp"' in nat and "['t_ftp', 'nf_ftp']" in nat and "nvram_char_to_ascii(\"\",\"nf_ftp\")" in nat
      and "vts_ftpport: 'alg', nf_ftp: 'alg'}" in nat and "fw_pt_pppoerelay: 1, nf_ftp: 1};" in nat and "<#RNAT_49#>" in nat and "<#RNAT_50#>" in nat)
import re as _re
_w = os.path.join(SRC, "www"); _packs = [f for f in os.listdir(_w) if _re.fullmatch(r"[A-Z]{2}\.dict", f)]
check("RNAT_49/50 in all 25 packs", len(_packs) == 25 and all("\nRNAT_49=" in open(os.path.join(_w, p), encoding="utf-8").read()
      and "\nRNAT_50=" in open(os.path.join(_w, p), encoding="utf-8").read() for p in _packs))
print("%d failure(s)" % len(fails))
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
