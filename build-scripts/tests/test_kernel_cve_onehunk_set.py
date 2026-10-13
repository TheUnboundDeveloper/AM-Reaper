#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The five one-hunk kernel CVE backports from the 2026-08-30 check (kernel 4.19.294).

WHY THIS EXISTS. The 2026-08-30 CVE pass left five small upstream fixes unapplied, each rated LOW
on this firmware and three of them reboot-class (the kernel panics on any oops). 4.19 is EOL, so
each is carried here as the 4.19.y stable hunk:
  CVE-2023-52881  tcp_ack(): an ACK below snd_una is only tolerated within min(max_window,
                  bytes_acked), so an ACK for bytes never sent draws a challenge ACK
                  (upstream 3d501dd326fb, 4.19.302)
  CVE-2024-47684  tcp_rto_delta_us(): a NULL rtx-queue head is warned about and returns 0
                  instead of being dereferenced (upstream c8770db2d544, 4.19.323)
  CVE-2024-50154  reqsk_queue_unlink(): del_timer_sync() without timer_pending(), since that
                  reads false while the handler is running - EXCEPT when called from
                  reqsk_timer_handler() itself (from_timer): del_timer_sync() on the running
                  timer never returns, a CPU spins in softirq and the soft-lockup panic
                  reboots the box (v3.4.0 field, 2026-10-11) (upstream e8c526f2bdf1, 4.19.324)
  CVE-2023-6932   igmp_start_timer(): the reference is taken with refcount_inc_not_zero()
                  before the timer is armed (upstream e2b706c69190, 4.19.302)
  CVE-2024-50299  sctp_sf_ootb(): the chunk walk stops while a whole chunk header fits
                  (upstream 0ead60804b64, 4.19.324)

WHAT IT PINS (source, comments stripped): each hunk's fixed form is present and its vulnerable
form is absent, in the function that carries it. With a generated .config: SCTP and IPv4
multicast are built (the fixed paths are in the image).

Exit 0 pass, 1 fail, 77 skipped (no tree: pass release/src/router as argv[1] or
REAPER_ROUTER_SRC; the kernel is found at ../../src-rt-5.04behnd.4916/kernel/linux-4.19).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
K = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "kernel", "linux-4.19")) if SRC else ""
FILES = {
    "tcp_input": "net/ipv4/tcp_input.c",
    "tcp_h": "include/net/tcp.h",
    "icsk": "net/ipv4/inet_connection_sock.c",
    "igmp": "net/ipv4/igmp.c",
    "sctp": "net/sctp/sm_statefuns.c",
}
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

# CVE-2023-52881
fn = extract(S["tcp_input"], "static int tcp_ack(struct sock *sk, const struct sk_buff *skb, int flag)")
check("tcp_input.c: tcp_ack() found", fn is not None)
if fn:
    n = norm(fn)
    check("52881: the tolerated window is min_t(u64, tp->max_window, tp->bytes_acked)",
          "max_window = min_t(u64, tp->max_window, tp->bytes_acked);" in n)
    check("52881: the RFC 5961 test uses that window", "if (before(ack, prior_snd_una - max_window))" in n)
    check("52881: the raw tp->max_window test is gone", "before(ack, prior_snd_una - tp->max_window)" not in n)
    check("52881: the challenge ACK is still sent on the old-ACK path",
          re.search(r"before\(ack, prior_snd_una - max_window\)\) \{ if \(!\(flag & FLAG_NO_CHALLENGE_ACK\)\) tcp_send_challenge_ack\(sk, skb\); return -1; \}", n) is not None)

# CVE-2024-47684
fn = extract(S["tcp_h"], "static inline s64 tcp_rto_delta_us(const struct sock *sk)")
check("tcp.h: tcp_rto_delta_us() found", fn is not None)
if fn:
    n = norm(fn)
    check("47684: the rtx-queue head is tested before use", "if (likely(skb)) {" in n)
    check("47684: the timestamp is read only inside that test",
          re.search(r"if \(likely\(skb\)\) \{ u64 rto_time_stamp_us = skb->skb_mstamp \+ jiffies_to_usecs\(rto\);", n) is not None)
    check("47684: an empty queue warns once and returns 0", "WARN_ONCE(1," in n and re.search(r"\); return 0; \}", n) is not None)
    check("47684: the only skb dereference sits inside the NULL test",
          n.count("skb->skb_mstamp") == 1 and n.find("if (likely(skb)) {") < n.find("skb->skb_mstamp"))

# CVE-2024-50154
fn = extract(S["icsk"], "static bool reqsk_queue_unlink(struct request_sock_queue *queue,")
check("inet_connection_sock.c: reqsk_queue_unlink() found", fn is not None)
if fn:
    n = norm(fn)
    check("50154: reqsk_queue_unlink() takes from_timer", "struct request_sock *req, bool from_timer)" in n)
    check("50154: del_timer_sync() is skipped only for the timer's own call",
          "if (!from_timer && del_timer_sync(&req->rsk_timer)) reqsk_put(req);" in n)
    check("50154: timer_pending() no longer gates it", "timer_pending(" not in n)
    check("50154: no unguarded del_timer_sync() left (it self-deadlocks from the handler)",
          n.count("del_timer_sync(") == 1)
fn = extract(S["icsk"], "static bool __inet_csk_reqsk_queue_drop(struct sock *sk,")
check("50154: __inet_csk_reqsk_queue_drop() carries from_timer to the unlink",
      fn is not None and "reqsk_queue_unlink(&inet_csk(sk)->icsk_accept_queue, req, from_timer);" in norm(fn))
fn = extract(S["icsk"], "bool inet_csk_reqsk_queue_drop(struct sock *sk, struct request_sock *req)")
check("50154: the exported drop is the non-timer form",
      fn is not None and "return __inet_csk_reqsk_queue_drop(sk, req, false);" in norm(fn))
fn = extract(S["icsk"], "static void reqsk_timer_handler(struct timer_list *t)")
check("inet_connection_sock.c: reqsk_timer_handler() found", fn is not None)
if fn:
    n = norm(fn)
    check("50154: the timer handler drops with from_timer and puts its own reference",
          "drop: __inet_csk_reqsk_queue_drop(sk_listener, req, true); reqsk_put(req); }" in n)
    check("50154: the timer handler never reaches a drop that waits on its own timer",
          "inet_csk_reqsk_queue_drop_and_put(" not in n and "inet_csk_reqsk_queue_drop(" not in n.replace("__inet_csk_reqsk_queue_drop(", ""))

# CVE-2023-6932
fn = extract(S["igmp"], "static void igmp_start_timer(struct ip_mc_list *im, int max_delay)")
check("igmp.c: igmp_start_timer() found", fn is not None)
if fn:
    n = norm(fn)
    check("6932: the reference is taken with refcount_inc_not_zero() first", "if (refcount_inc_not_zero(&im->refcnt)) {" in n)
    check("6932: a timer that was already armed gives the reference back",
          "if (mod_timer(&im->timer, jiffies + tv + 2)) ip_ma_put(im);" in n)
    check("6932: the old mod_timer-then-refcount_inc order is gone", "refcount_inc(&im->refcnt)" not in n)
    check("igmp.c: ip_ma_put() is defined before igmp_start_timer()",
          0 <= S["igmp"].find("static void ip_ma_put(struct ip_mc_list *im)") < S["igmp"].find("static void igmp_start_timer("))

# CVE-2024-50299
fn = extract(S["sctp"], "enum sctp_disposition sctp_sf_ootb(struct net *net,")
check("sm_statefuns.c: sctp_sf_ootb() found", fn is not None)
if fn:
    n = norm(fn)
    check("50299: the chunk walk requires a whole header to remain", "} while (ch_end + sizeof(*ch) < skb_tail_pointer(skb));" in n)
    check("50299: the bare tail test is gone", "} while (ch_end < skb_tail_pointer(skb));" not in n)
    check("50299: the per-chunk length and tail checks inside the loop are untouched",
          "if (ntohs(ch->length) < sizeof(*ch))" in n and "if (ch_end > skb_tail_pointer(skb))" in n)

cfg = os.path.join(K, ".config")
if os.path.isfile(cfg):
    c = open(cfg, encoding="latin-1").read()
    check("model kernel config: CONFIG_IP_SCTP=y (the OOTB path is in the image)", "\nCONFIG_IP_SCTP=y" in c)
    check("model kernel config: CONFIG_IP_MULTICAST=y (the IGMP timer path is in the image)", "\nCONFIG_IP_MULTICAST=y" in c)
    check("model kernel config: CONFIG_PANIC_ON_WARN off (the 47684 WARN_ONCE must not reboot the box)", "\nCONFIG_PANIC_ON_WARN=y" not in c)
else:
    print("note: no generated kernel .config (cold tree) - config pins skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed: the five one-hunk kernel CVE fixes from the 2026-08-30 check are in the tree")
