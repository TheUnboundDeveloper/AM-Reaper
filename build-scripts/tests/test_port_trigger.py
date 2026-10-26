#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Port Trigger has its iptables target, and rc writes the port forms each option expects.

WHY THIS EXISTS (2026-10-23, found during the LAN/WAN page conversion). Commit 0b8cea213a deleted
iptables-1.4.x/extensions/libipt_TRIGGER.c because it "won't compile" (it included the kernel-internal
<net/netfilter/nf_nat.h>, absent from the toolchain headers HND builds use) - it had already been
missing from the build clone, so EVERY image shipped without the userspace TRIGGER target while rc
still wrote `-j TRIGGER` rules. With Port Trigger on, iptables-restore refuses the whole nat table:
after a reboot, no NAT at all. The kernel side (CONFIG_IP_NF_TARGET_TRIGGER) was always built.
Second defect in the same path: the trigger port feeds both --dport (iptables wants a:b) and
--trigger-match (the extension's parse_ports wants a-b, and reads a:b as the single port a).

WHAT IT CHECKS: the extension source is present, without the kernel-internal include and with the
one constant it took from it; its header sits in iptables' include tree and matches the kernel's;
rc/firewall.c writes --dport in a:b form and --trigger-match in a-b form; the extension compiles
(-fsyntax-only) with the host compiler against iptables' own headers when gcc is available.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
EXT = os.path.join(SRC, "iptables-1.4.x", "extensions", "libipt_TRIGGER.c")
if not SRC or not os.path.isdir(os.path.join(SRC, "iptables-1.4.x")):
    print("SKIP: no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

check("the userspace TRIGGER target source is present", os.path.isfile(EXT))
ext = open(EXT, encoding="utf-8", errors="replace").read() if os.path.isfile(EXT) else ""
check("it no longer includes the kernel-internal nf_nat.h", "#include <net/netfilter/nf_nat.h>" not in ext)
check("it defines the --trigger-relate option bit it took from that header (value 2)",
      re.search(r"#define IP_NAT_RANGE_PROTO_SPECIFIED 2\b", ext) is not None)
hdr = os.path.join(SRC, "iptables-1.4.x", "include", "linux", "netfilter_ipv4", "ipt_TRIGGER.h")
check("ipt_TRIGGER.h sits in iptables' include tree", os.path.isfile(hdr))
kdirs = [os.path.join(SRC, "..", "..", d, "kernel", "linux-4.19", "include", "linux", "netfilter_ipv4", "ipt_TRIGGER.h")
         for d in ("src-rt-5.04behnd.4916",)]
kh = next((k for k in kdirs if os.path.isfile(k)), None)
if kh and os.path.isfile(hdr):
    check("it is the kernel's struct layout (byte-identical copy)", open(kh, "rb").read() == open(hdr, "rb").read())

fw = open(os.path.join(SRC, "rc", "firewall.c"), encoding="utf-8", errors="replace").read()
a = fw.find('"-j TRIGGER --trigger-type out --trigger-proto %s --trigger-match %s --trigger-relate %s\\n"')
blk = fw[max(0, a - 900):a + 300]
check("rc writes --dport in a:b form", "if ((p = strchr(dport, '-')) != NULL)" in blk and "*p = ':';" in blk and "dport," in blk)
check("rc writes --trigger-match in a-b form", "if ((p = strchr(tmatch, ':')) != NULL)" in blk and "tmatch, in_port);" in blk)
check("the nat-side TRIGGER rule is still written (the target now exists)",
      'fprintf(fp, "-A VSERVER -j TRIGGER --trigger-type dnat\\n");' in fw)

# The same commit also deleted libipt_webstr.c (it compiles as it is - its own struct, no kernel header);
# the URL filter writes `-m webstr` into the IPv4 filter restore, so every URL rule was refused (and past
# 8 refused lines the whole filter table). Gate the whole class: every `-m <match>` that rc writes into
# an iptables rule line has a userspace extension in the iptables tree.
import glob
xdir = os.path.join(SRC, "iptables-1.4.x", "extensions")
have = set()
for pfx in ("libxt_", "libipt_", "libip6t_"):
    have |= {os.path.basename(p)[len(pfx):-2].lower() for p in glob.glob(os.path.join(xdir, pfx + "*.c"))}
missing = {}
for f in glob.glob(os.path.join(SRC, "rc", "*.c")):
    t = open(f, encoding="latin-1").read()
    for m in re.finditer(r'"[^"\n]*?(?:-[AIN] |--append |--insert )[^"\n]*?-m ([A-Za-z][A-Za-z0-9_]*)[^"\n]*"', t):
        if m.group(1).lower() not in have:
            missing.setdefault(m.group(1), set()).add(os.path.basename(f))
check("every -m match rc writes into a rule has its userspace extension (webstr included)",
      not missing, {k: sorted(v) for k, v in missing.items()})
check("libipt_webstr.c (IPv4 URL filter) is present beside libip6t_webstr.c",
      os.path.isfile(os.path.join(xdir, "libipt_webstr.c")))

CC = shutil.which("gcc") or shutil.which("cc")
if CC and ext:
    inc = os.path.join(SRC, "iptables-1.4.x", "include")
    r = subprocess.run([CC, "-fsyntax-only", "-Wall", "-D_INIT=libipt_TRIGGER_init", "-I" + inc,
                        "-I" + os.path.join(SRC, "iptables-1.4.x"), EXT], capture_output=True, text=True)
    check("the extension compiles against iptables' own headers (host gcc, syntax only)", r.returncode == 0, r.stderr)
else:
    print("note: no host compiler - compile check skipped")

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_port_trigger")
