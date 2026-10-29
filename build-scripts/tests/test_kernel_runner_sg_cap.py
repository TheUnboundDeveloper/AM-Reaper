#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Runner 4-fragment transmit cap (kernel 4.19.294, BCM6813 / XRDP).

WHY THIS EXISTS. The Runner's CPU-TX path takes at most RUNNER_MAX_SG_FRAGS (4) page fragments
per non-GSO skb (rdp/projects/BCM6813/target/bdmf/system/linux/ce/bdmf_system.h). The check is
in the closed bdmf.o; the prebuilt enet caller treats a refusal as "already freed" and counts
tx_dropped, and the kernel logs "skb->nr_frags N exceed max_sg_array 4". enet advertises
NETIF_F_SG and has no ndo_features_check, so stock never linearizes for it. TCP adds one frag
per write it cannot merge (tcp_sendmsg_locked), and stubby - one thread, small TLS records,
several upstream sockets, Nagle on - builds 5-10 frag skbs whenever the upstream RTT is long
enough (field, GT-BE98, 2026-10-14: IPv6 DoT servers reached through a 6in4 tunnel; line count
matched eth1 tx_dropped 1:1). Every such packet was dropped and its retransmit, a clone with the
same frags, was dropped again.

THE FIX. netif_skb_features() clears NETIF_F_SG for a non-GSO skb with more frags than
net.core.reaper_tx_sg_max (default 4, 0 = stock), so validate_xmit_skb() linearizes exactly
those skbs (at most one MSS). net.core.reaper_tx_sg_linearized counts how often the cap fired.

WHAT IT PINS (source, comments stripped): the guarded hunk inside netif_skb_features() after
the features-check branch and before harmonize_features(); the knob and counter definitions
and their externs; both sysctl entries with their modes and bounds; the bdmf cap still 4 (an
SDK merge that changes it must revisit the default); with a generated .config, CONFIG_BCM_XRDP=y
(the hunk is compiled into the image). Source pins prove the text; the behaviour is proven on
metal with net.core.reaper_tx_sg_max 0 vs 4.

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or
REAPER_ROUTER_SRC; the kernel is found at ../../src-rt-5.04behnd.4916/kernel/linux-4.19).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
PLAT = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916")) if SRC else ""
K = os.path.join(PLAT, "kernel", "linux-4.19") if PLAT else ""
FILES = {
    "dev": "net/core/dev.c",
    "sysctl": "net/core/sysctl_net_core.c",
    "netdevice_h": "include/linux/netdevice.h",
}
BDMF = os.path.join(PLAT, "rdp", "projects", "BCM6813", "target", "bdmf", "system", "linux", "ce", "bdmf_system.h") if PLAT else ""
if not K or not all(os.path.isfile(os.path.join(K, p)) for p in FILES.values()):
    skip("no kernel tree next to the router source (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def nocomment(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("//"))

def extract(src, sig):
    i = src.find(sig)
    if i < 0: return None
    j = src.find("{", i); d = 0
    for k in range(j, len(src)):
        if src[k] == "{": d += 1
        elif src[k] == "}":
            d -= 1
            if d == 0: return src[i:k + 1]
    return None

def norm(s): return re.sub(r"\s+", " ", s)

S = {k: nocomment(open(os.path.join(K, p), encoding="latin-1").read()) for k, p in FILES.items()}
GUARD = "#if defined(CONFIG_BCM_XRDP)"

# the knob and the counter
d = norm(S["dev"])
m = re.search(re.escape(GUARD) + r" int sysctl_reaper_tx_sg_max __read_mostly = (\d+); atomic_long_t reaper_tx_sg_linearized; #endif", d)
check("dev.c: knob + counter defined together under CONFIG_BCM_XRDP", m is not None)
check("dev.c: the default cap is 4 (the bdmf limit)", m is not None and m.group(1) == "4")
check("dev.c: knob and counter defined once each",
      d.count("int sysctl_reaper_tx_sg_max ") == 1 and d.count("atomic_long_t reaper_tx_sg_linearized") == 1)

# the hunk
fn = extract(S["dev"], "netdev_features_t netif_skb_features(struct sk_buff *skb)")
check("dev.c: netif_skb_features() found", fn is not None)
if fn:
    n = norm(fn)
    hunk = (GUARD + " { int cap = READ_ONCE(sysctl_reaper_tx_sg_max); "
            "if (unlikely(cap && !skb_is_gso(skb) && skb_shinfo(skb)->nr_frags > cap && (features & NETIF_F_SG))) { "
            "features &= ~NETIF_F_SG; atomic_long_inc(&reaper_tx_sg_linearized); } } #endif")
    check("cap: the guarded hunk is present verbatim", hunk in n, n[-700:])
    i_hunk = n.find(hunk)
    i_chk = n.find("features &= dflt_features_check(skb, dev, features);")
    i_ret = n.find("return harmonize_features(skb, features);")
    check("cap: it runs after the ndo/dflt features check (covers devices with their own check)",
          i_hunk > i_chk >= 0)
    check("cap: it runs before harmonize_features()", 0 <= i_hunk < i_ret)
    check("cap: GSO skbs are never touched (bdmf_sg_gso packs those)", "!skb_is_gso(skb)" in n)
    check("cap: only NETIF_F_SG is cleared", n.count("features &= ~NETIF_F_SG;") == 1 and "NETIF_F_CSUM" not in n.split(GUARD)[-1].split("#endif")[0])

# validate_xmit_skb() still linearizes on a missing SG (the mechanism the hunk relies on)
fn = extract(S["dev"], "static struct sk_buff *validate_xmit_skb(struct sk_buff *skb, struct net_device *dev, bool *again)")
check("dev.c: validate_xmit_skb() linearizes when SG is cleared",
      fn is not None and "features = netif_skb_features(skb);" in norm(fn)
      and "if (skb_needs_linearize(skb, features) && __skb_linearize(skb)) goto out_kfree_skb;" in norm(fn))

# externs
h = norm(S["netdevice_h"])
check("netdevice.h: externs under CONFIG_BCM_XRDP",
      (GUARD + " extern int sysctl_reaper_tx_sg_max; extern atomic_long_t reaper_tx_sg_linearized; #endif") in h)

# sysctls
s = norm(S["sysctl"])
check("sysctl: reaper_tx_sg_max is 0644 int, 0..MAX_SKB_FRAGS",
      ("{ .procname = \"reaper_tx_sg_max\", .data = &sysctl_reaper_tx_sg_max, .maxlen = sizeof(int), "
       ".mode = 0644, .proc_handler = proc_dointvec_minmax, .extra1 = &zero, .extra2 = &max_skb_frags, }") in s)
check("sysctl: reaper_tx_sg_linearized is read-only through its own handler",
      ("{ .procname = \"reaper_tx_sg_linearized\", .maxlen = sizeof(unsigned long), .mode = 0444, "
       ".proc_handler = proc_reaper_tx_sg_linearized, }") in s)
fn = extract(S["sysctl"], "static int proc_reaper_tx_sg_linearized(struct ctl_table *table, int write,")
check("sysctl: the counter handler reads the atomic into a temporary table",
      fn is not None and "atomic_long_read(&reaper_tx_sg_linearized)" in norm(fn)
      and "proc_doulongvec_minmax(&tmp, write, buffer, lenp, ppos)" in norm(fn))
check("sysctl: entries and handler sit under CONFIG_BCM_XRDP",
      s.count(GUARD) >= 2 and s.find(GUARD) < s.find("proc_reaper_tx_sg_linearized"))

# the hardware cap this default mirrors
if os.path.isfile(BDMF):
    b = open(BDMF, encoding="latin-1").read()
    check("bdmf_system.h: RUNNER_MAX_SG_FRAGS is still 4 (revisit the default if an SDK changes it)",
          re.search(r"#define\s+RUNNER_MAX_SG_FRAGS\s+4\b", b) is not None)
else:
    print("note: bdmf_system.h not present - the hardware-cap pin is skipped")

cfg = os.path.join(K, ".config")
if os.path.isfile(cfg):
    c = open(cfg, encoding="latin-1").read()
    check("model kernel config: CONFIG_BCM_XRDP=y (the cap is compiled in)", "\nCONFIG_BCM_XRDP=y" in c)
else:
    print("note: no generated kernel .config (cold tree) - config pin skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: the Runner 4-fragment transmit cap is in the tree")
