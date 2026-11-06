#!/usr/bin/env python3
"""Kernel round 2026-11-06 (Audit Findings: the deferred kernel stable-fix round + the port-trigger item).

  CVE-2024-26921  inet_defrag: a fragment's socket is no longer released while the TX path still uses it.
                  4.19 hand port of upstream 18685451fc4e: the reassembly offset moves from
                  skb->ip_defrag_offset (a union with skb->sk) into the fragment control block; the union
                  in skbuff.h is left as it is, so struct sk_buff stays byte-identical for the closed
                  Broadcom modules; skb_orphan() moves from ip_defrag()/nf_ct_frag6_gather() to the
                  queued case; inet_frag_reasm_prepare()/finish() hand the socket to the reassembled
                  head and fix its wmem accounting (is_skb_wmem() is a local helper - 4.19 lacks it).
  CVE-2023-4207   cls_fw: tcf_result is no longer copied on update (upstream 76e42ae83199).
  CVE-2023-4623   sch_hfsc: an inner class must have an fsc curve (upstream b3d26c5702c7).
  E-6 follow-up   ipt_TRIGGER: checkentry() no longer empties the whole trigger list. Every "out" rule key
                  holds a reference (checkentry takes it, the new destroy() drops it); a key that reaches
                  zero flushes only its own entries. The reference code is compiled from the tree and run
                  against the x_tables order (new table checked before the old one is destroyed).
Not taken, with the reason in the private notes: CVE-2023-42756 (4.19 call_ad() never drops the nfnl lock,
so the ADD/SWAP window does not exist), CVE-2023-4921 (sch_qfq not built), CVE-2023-4206 / CVE-2023-4208 /
CVE-2023-42753 / CVE-2024-53141 (already in the tree).
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] / REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "init.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
K = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "kernel", "linux-4.19"))
if not os.path.isfile(os.path.join(K, "net", "ipv4", "inet_fragment.c")):
    print("SKIP: no kernel tree next to the router source"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")

def rd(rel):
    p = os.path.join(K, rel)
    return open(p, encoding="latin-1").read() if os.path.isfile(p) else ""
def nocomment(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("//"))
def func(t, head):
    m = re.search(r"\n" + re.escape(head) + r".*?\n\}\n", t, re.S)
    return m.group(0) if m else ""

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

# ---- CVE-2024-26921
fr = nocomment(rd("net/ipv4/inet_fragment.c"))
cb = re.search(r"struct ipfrag_skb_cb \{.*?\n\};", fr, re.S)
check("26921: the reassembly offset lives in the fragment control block",
      bool(cb) and re.search(r"\bint\s+ip_defrag_offset;", cb.group(0)) is not None)
check("26921: no raw skb->ip_defrag_offset use is left in inet_fragment.c",
      not re.search(r"(?<!FRAG_CB\()\b\w+\)?->ip_defrag_offset", re.sub(r"FRAG_CB\(\w+\)->ip_defrag_offset", "", fr)))
check("26921: the control block is checked against skb->cb at build time",
      "BUILD_BUG_ON(sizeof(struct ipfrag_skb_cb) > sizeof(((struct sk_buff *)0)->cb));" in fr)
wm = func(fr, "static inline bool reaper_is_skb_wmem")
check("26921: is_skb_wmem() helper covers sock_wfree, __sock_wfree and tcp_wfree",
      all(x in wm for x in ("sock_wfree ||", "__sock_wfree", "tcp_wfree")))
prep = func(fr, "void *inet_frag_reasm_prepare")
check("26921: prepare() keeps skb_morph from releasing the socket",
      re.search(r"skb->sk = NULL;\s*skb->destructor = NULL;\s*\}\s*skb_morph\(skb, head\);", prep) is not None)
check("26921: prepare() failures restore the socket (no bare return NULL left)",
      "return NULL;" not in prep and prep.count("goto out_restore_sk;") == 3 and "out_restore_sk:" in prep)
check("26921: prepare() hands the socket to the head and charges the truesize delta",
      re.search(r"head->sk = sk;\s*head->destructor = destructor;\s*refcount_add\(ts_delta, &sk->sk_wmem_alloc\);", prep) is not None)
fin = func(fr, "void inet_frag_reasm_finish")
check("26921: finish() charges the socket for what the head grew by",
      "const unsigned int head_truesize = head->truesize;" in fin
      and "refcount_add(head->truesize - head_truesize, &sk->sk_wmem_alloc);" in fin)

ipf = nocomment(rd("net/ipv4/ip_fragment.c"))
check("26921: ip_defrag() no longer orphans the skb", "skb_orphan" not in func(ipf, "int ip_defrag("))
check("26921: ip_frag_queue() orphans only the queued skb",
      re.search(r"skb_dst_drop\(skb\);\s*skb_orphan\(skb\);\s*return -EINPROGRESS;", func(ipf, "static int ip_frag_queue")) is not None)
nf6 = nocomment(rd("net/ipv6/netfilter/nf_conntrack_reasm.c"))
check("26921: nf_ct_frag6_gather() no longer orphans the skb", "skb_orphan" not in func(nf6, "int nf_ct_frag6_gather("))
check("26921: nf_ct_frag6_queue() orphans only the queued skb",
      re.search(r"skb_dst_drop\(skb\);\s*skb_orphan\(skb\);\s*return -EINPROGRESS;", func(nf6, "static int nf_ct_frag6_queue")) is not None)
skbh = rd("include/linux/skbuff.h")
check("26921: struct sk_buff is unchanged (sk / ip_defrag_offset union kept - closed modules)",
      re.search(r"union \{\s*struct sock\s+\*sk;\s*int\s+ip_defrag_offset;\s*\};", skbh) is not None)

# ---- CVE-2023-4207 / CVE-2023-4623
fw = nocomment(rd("net/sched/cls_fw.c"))
check("4207: cls_fw update does not copy tcf_result", "fnew->res = f->res;" not in fw and "fnew->id = f->id;" in fw)
hf = rd("net/sched/sch_hfsc.c")
check("4623: hfsc refuses a parent class without an fsc curve",
      "if (!(parent->cl_flags & HFSC_FSC) && parent != &q->root) {" in hf)

# ---- E-6: ipt_TRIGGER per-rule references
tr = rd("net/ipv4/netfilter/ipt_TRIGGER.c"); trc = nocomment(tr)
ce = func(trc, "static int checkentry")
check("E-6: checkentry() no longer flushes the whole trigger list", "trigger_flush()" not in ce and "trig_rule_get(info)" in ce)
check("E-6: the target has a destroy() that drops the rule's reference",
      ".destroy = destroy," in trc and "trig_rule_put(info);" in func(trc, "static void destroy"))
fl = func(trc, "static void trigger_flush_rule")
check("E-6: a rule's flush frees only that rule's entries, timers cancelled first",
      "trig_key_eq(trig->rproto, &trig->ports, ports, proto) && del_timer(&trig->timeout)" in fl)

if CC:
    m = re.search(r"(struct trig_rule \{.*?\n\};\n.*?static LIST_HEAD\(trig_rules\);\nstatic DEFINE_MUTEX\(trig_rules_mutex\);\n)", tr, re.S)
    pieces = [m.group(1) if m else ""] + [func(tr, h) for h in (
        "static int trig_key_eq", "static int trig_rule_get", "static void trig_rule_put")]
    if all(pieces):
        stub = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned short u_int16_t;
struct list_head { struct list_head *next, *prev; };
#define LIST_HEAD(n) struct list_head n = { &(n), &(n) }
#define container_of(p, t, m) ((t *)((char *)(p) - __builtin_offsetof(t, m)))
#define list_entry(p, t, m) container_of(p, t, m)
#define list_for_each_entry(pos, head, m) for (pos = list_entry((head)->next, __typeof__(*pos), m); &pos->m != (head); pos = list_entry(pos->m.next, __typeof__(*pos), m))
static void list_add(struct list_head *n, struct list_head *h) { n->next = h->next; n->prev = h; h->next->prev = n; h->next = n; }
static void list_del(struct list_head *e) { e->prev->next = e->next; e->next->prev = e->prev; }
#define DEFINE_MUTEX(n) int n
#define mutex_lock(x) ((void)(x))
#define mutex_unlock(x) ((void)(x))
#define GFP_KERNEL 0
#define ENOMEM 12
#define kzalloc(s, f) calloc(1, (s))
#define kfree free
struct ipt_trigger_ports { u_int16_t mport[2]; u_int16_t rport[2]; };
struct ipt_trigger_info { int type; u_int16_t proto; struct ipt_trigger_ports ports; };
static int flushed[8], nflush;
static void trigger_flush_rule(u_int16_t proto, const struct ipt_trigger_ports *p) { flushed[nflush++] = p->mport[0]; (void)proto; }
'''
        harness = r'''
static struct ipt_trigger_info R(int m) { struct ipt_trigger_info i = { 1, 6, { { m, m }, { m + 1000, m + 1010 } } }; return i; }
int main(void)
{
	struct ipt_trigger_info a = R(10), b = R(20), b2 = R(20);
	int bad = 0;
	/* boot: table with rules a, b */
	trig_rule_get(&a); trig_rule_get(&b);
	/* an unrelated change (Warden etc.) replaces the table: new checked, then old destroyed */
	trig_rule_get(&a); trig_rule_get(&b); trig_rule_put(&a); trig_rule_put(&b);
	if (nflush != 0) { printf("FAIL replace with the same rules flushed %d\n", nflush); bad = 1; }
	/* rule a removed: new table has b only */
	trig_rule_get(&b); trig_rule_put(&a); trig_rule_put(&b);
	if (nflush != 1 || flushed[0] != 10) { printf("FAIL removed rule: nflush=%d first=%d\n", nflush, flushed[0]); bad = 1; }
	/* a second rule with the same key (tcp and udp match) - flushed only when both are gone */
	trig_rule_get(&b2);
	trig_rule_put(&b);
	if (nflush != 1) { printf("FAIL shared key flushed while still referenced\n"); bad = 1; }
	/* port trigger switched off: the last rule goes */
	trig_rule_put(&b2);
	if (nflush != 2 || flushed[1] != 20) { printf("FAIL last rule: nflush=%d\n", nflush); bad = 1; }
	/* a put for a key never taken is harmless */
	trig_rule_put(&a);
	if (nflush != 2) { printf("FAIL unknown put flushed\n"); bad = 1; }
	return bad;
}
'''
        d = tempfile.mkdtemp()
        try:
            c = os.path.join(d, "t.c"); x = os.path.join(d, "t")
            open(c, "w").write(stub + "\n".join(pieces) + harness)
            r = subprocess.run([CC, "-Wall", "-Werror", "-o", x, c], capture_output=True, text=True)
            check("E-6: the reference code compiles on the host", r.returncode == 0, r.stderr)
            if r.returncode == 0:
                r = subprocess.run([x], capture_output=True, text=True)
                check("E-6: table replace keeps sessions; a removed rule (and only it) is flushed",
                      r.returncode == 0, r.stdout)
        finally:
            shutil.rmtree(d, ignore_errors=True)
    else:
        check("E-6: the reference code was found in ipt_TRIGGER.c", False, [bool(p) for p in pieces])
else:
    print("note: no host compiler - the E-6 behaviour test was not run")

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
