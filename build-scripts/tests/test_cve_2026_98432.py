#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CVE-2026-98432: IPv4 TCP handshake use-after-free of the SYN's IP options (backport, 2026-11-03).

WHY THIS EXISTS. tcp_v4_syn_recv_sock() hands ireq->ireq_opt to the child socket without a copy; another cpu
building a SYNACK for a retransmitted SYN reads the same options under rcu_read_lock() only, and the child's
inet_sock_destruct() (or the request socket's destructor) freed them with a plain kfree(). Upstream e3f33b0a1d89
("ipv4: free inet_opt and ireq_opt after an RCU grace period") switches both frees to kfree_rcu(). 4.19 is EOL
upstream, so the fix is carried here. TRAP: 4.19's kfree_rcu() has no NULL check (it hands &ptr->rcu straight to
kfree_call_rcu), and almost every socket has no IP options - the literal upstream line would oops on every
socket close. The backport tests the pointer first, as cipso_ipv4.c does.

WHAT IT DOES. Checks both sites free through kfree_rcu(opt, rcu) behind an `if (opt)`, that no plain kfree() of
inet_opt / ireq_opt is left in af_inet.c / tcp_ipv4.c, that this kernel's kfree_rcu() really lacks the NULL test
(so the guard stays needed - if a future rebase brings the NULL-safe macro, the guard is harmless), and that
struct ip_options_rcu has the rcu member the macro names. Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
K = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "kernel", "linux-4.19")) if SRC else ""
if not K or not os.path.isfile(os.path.join(K, "net", "ipv4", "tcp_ipv4.c")):
    print("SKIP: no kernel tree next to the router source"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda *p: open(os.path.join(K, *p), encoding="utf-8", errors="replace").read()

af = rd("net", "ipv4", "af_inet.c")
tc = rd("net", "ipv4", "tcp_ipv4.c")
isd = af[af.find("void inet_sock_destruct(struct sock *sk)"):]
isd = isd[:isd.find("\n}\n")]
rqd = tc[tc.find("tcp_v4_reqsk_destructor(struct request_sock *req)\n#endif\n{"):]
rqd = rqd[:rqd.find("\n}\n")]
GUARD = r"struct ip_options_rcu \*opt = rcu_dereference_protected\(%s, 1\);\s*if \(opt\)\s*kfree_rcu\(opt, rcu\);"
check("inet_sock_destruct: inet_opt freed with kfree_rcu behind a NULL test",
      re.search(GUARD % r"inet->inet_opt", isd) is not None, isd[-400:])
check("tcp_v4_reqsk_destructor: ireq_opt freed with kfree_rcu behind a NULL test",
      re.search(GUARD % r"inet_rsk\(req\)->ireq_opt", rqd) is not None, rqd[-300:])
plain = re.compile(r"\bkfree\(rcu_dereference_protected\([^)]*(inet_opt|ireq_opt)")
check("no plain kfree() of inet_opt / ireq_opt left in af_inet.c or tcp_ipv4.c",
      not plain.search(af) and not plain.search(tc))
rcu = rd("include", "linux", "rcupdate.h")
m = re.search(r"#define kfree_rcu\(ptr, rcu_head\)[^\n]*\n([^\n]*)", rcu)
check("this kernel's kfree_rcu() has no NULL test (the guard is required)",
      m is not None and "__kfree_rcu(&((ptr)->rcu_head)" in m.group(1), m.group(0) if m else "no macro")
ins = rd("include", "net", "inet_sock.h")
check("struct ip_options_rcu carries the rcu member kfree_rcu() names",
      re.search(r"struct ip_options_rcu \{\s*struct rcu_head rcu;", ins) is not None)

if fails:
    print("\n".join("FAILED: " + f for f in fails)); sys.exit(1)
print("all checks passed")
