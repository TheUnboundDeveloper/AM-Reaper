#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CVE-2026-43198: a v6-mapped TCP child is finished before it is hashed (kernel 4.19.294).

WHY THIS EXISTS. tcp_v6_syn_recv_sock() handles an IPv4 connection accepted on a dual-stack
IPv6 listener by calling tcp_v4_syn_recv_sock(), which inserts the child into the established
hash, and only then pointing the child's pinet6 at its own ipv6_pinfo and setting its ops. In
that window another CPU can use the child with pinet6 still aimed at the LISTENER's ipv6_pinfo
(syzbot). 4.19 is EOL, so the fix (upstream 858d2a4f67ff, 5.10.y aef4a9ae) is carried here.

THE PORT. Same mechanism as upstream - a hook, tcp_v6_mapped_child_init(), that
__tcp_v4_syn_recv_sock() runs before the child is synced and hashed - but without changing the
exported tcp_v4_syn_recv_sock() or the af_ops syn_recv_sock signature (closed Broadcom modules
link against this kernel; none references either today, and this keeps it that way). The
Broadcom MPTCP variant (CONFIG_BCM_MPTCP, enabled on no Reaper model) is left as shipped.

WHAT IT PINS (source order, comments stripped).
- __tcp_v4_syn_recv_sock() takes the hook and runs it after sk_setup_caps() and BEFORE
  tcp_sync_mss() and inet_ehash_nolisten() (the publish).
- tcp_v4_syn_recv_sock() is still exported with six arguments and passes NULL.
- tcp_v6_mapped_child_init() sets pinet6 to the child's own ipv6_pinfo, the mapped ops and
  backlog handler, and clears the list pointers; mcast fields come from newinet.
- the non-MPTCP mapped branch of tcp_v6_syn_recv_sock() returns __tcp_v4_syn_recv_sock(...,
  tcp_v6_mapped_child_init) and no longer touches the child after the call.
- the model's kernel config: CONFIG_BCM_MPTCP and CONFIG_MPTCP off (so the fixed path is built).

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or
REAPER_ROUTER_SRC; the kernel is found at ../../src-rt-5.04behnd.4916/kernel/linux-4.19).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
K = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "kernel", "linux-4.19")) if SRC else ""
V4, V6, H = (os.path.join(K, p) for p in ("net/ipv4/tcp_ipv4.c", "net/ipv6/tcp_ipv6.c", "include/net/tcp.h"))
if not K or not all(os.path.isfile(p) for p in (V4, V6, H)):
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

v4 = nocomment(open(V4, encoding="latin-1").read())
v6 = nocomment(open(V6, encoding="latin-1").read())
h = nocomment(open(H, encoding="latin-1").read())

check("tcp.h declares __tcp_v4_syn_recv_sock() with the opt_child_init hook",
      re.search(r"struct sock \*__tcp_v4_syn_recv_sock\([^;]*bool \*own_req,\s*void \(\*opt_child_init\)", h, re.S) is not None)
check("tcp.h keeps the six-argument tcp_v4_syn_recv_sock()",
      re.search(r"struct sock \*tcp_v4_syn_recv_sock\([^;]*bool \*own_req\);", h, re.S) is not None)

inner = extract(v4, "struct sock *__tcp_v4_syn_recv_sock(")
check("tcp_ipv4.c defines __tcp_v4_syn_recv_sock()", inner is not None)
if inner:
    hook = inner.find("opt_child_init(newsk, sk);")
    caps = inner.find("sk_setup_caps(newsk, dst);")
    sync = inner.find("tcp_sync_mss(newsk")
    pub = inner.find("inet_ehash_nolisten(")
    check("the hook runs after sk_setup_caps()", 0 <= caps < hook, (caps, hook))
    check("the hook runs before tcp_sync_mss() (sync sees the mapped ops)", 0 <= hook < sync, (hook, sync))
    check("the hook runs before inet_ehash_nolisten() (the publish)", 0 <= hook < pub, (hook, pub))
    check("the hook call is guarded by a NULL test", "if (opt_child_init)" in inner)
outer = extract(v4, "struct sock *tcp_v4_syn_recv_sock(")
check("tcp_v4_syn_recv_sock() is a wrapper passing NULL",
      outer is not None and re.search(r"return __tcp_v4_syn_recv_sock\([^;]*own_req,\s*NULL\);", outer, re.S) is not None)
check("both symbols are exported",
      "EXPORT_SYMBOL(__tcp_v4_syn_recv_sock);" in v4 and "EXPORT_SYMBOL(tcp_v4_syn_recv_sock);" in v4)

init = extract(v6, "static void tcp_v6_mapped_child_init(struct sock *newsk, const struct sock *sk)")
check("tcp_ipv6.c defines tcp_v6_mapped_child_init()", init is not None)
if init:
    for frag, what in (("newinet->pinet6 = newnp = &newtcp6sk->inet6;", "pinet6 points at the child's own ipv6_pinfo"),
                       ("inet_csk(newsk)->icsk_af_ops = &ipv6_mapped;", "mapped ops"),
                       ("newsk->sk_backlog_rcv = tcp_v4_do_rcv;", "IPv4 backlog handler"),
                       ("newnp->ipv6_mc_list = NULL;", "multicast list cleared"),
                       ("newnp->ipv6_fl_list = NULL;", "flow-label list cleared"),
                       ("newnp->opt", "options cleared"),
                       ("newnp->mcast_oif   = newinet->mc_index;", "mcast_oif from newinet (no skb here)"),
                       ("newnp->mcast_hops  = newinet->mc_ttl;", "mcast_hops from newinet")):
        check("child init: " + what, frag in init)

rs = extract(v6, "static struct sock *tcp_v6_syn_recv_sock(")
check("tcp_v6_syn_recv_sock() (non-MPTCP definition) found", rs is not None)
if rs:
    m = rs.find("if (skb->protocol == htons(ETH_P_IP)) {")
    e = rs.find("#else", m)
    branch = rs[m:e] if 0 <= m < e else ""
    check("the mapped branch returns __tcp_v4_syn_recv_sock(..., tcp_v6_mapped_child_init)",
          re.search(r"return __tcp_v4_syn_recv_sock\([^;]*tcp_v6_mapped_child_init\);", branch, re.S) is not None, branch[:200])
    check("the mapped branch writes nothing to the child after the call", "newnp->" not in branch and "pinet6" not in branch)

cfg = os.path.join(K, ".config")
if os.path.isfile(cfg):
    c = open(cfg, encoding="latin-1").read()
    check("model kernel config: CONFIG_BCM_MPTCP off (the fixed path is the one built)", "CONFIG_BCM_MPTCP=y" not in c)
    check("model kernel config: CONFIG_MPTCP off", "\nCONFIG_MPTCP=y" not in c)
else:
    print("note: no generated kernel .config (cold tree) - config pins skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: a v6-mapped child gets its own IPv6 state before it is hashed (CVE-2026-43198)")
