#!/usr/bin/env python3
"""Wallguard engine fixes (owner-approved, 2026-11-15): the device's MAC on every record, an allow that reaches a
CNAME block, and CNAME blocks shown under the name the device asked.

WHY. On the owner's router the policy had no per-device lines, so dnsmasq/src/wallguard.c never looked a MAC up
(the lookup sat behind `sh.nmac`) and every hit / recent record carried "-": the page's Unbreak, which filters by the
device's MAC, always found nothing (D4). A reply whose CNAME chain reached a listed name was answered NXDOMAIN without
asking whether the name the device asked for was allowed, so allowing a site (Paramount+) did nothing - only
allowing its hidden CNAME target helped (D2). The 'c' hit was filed under the chain's list entry and the live view got
no record at all, so the live view showed the asked name as passed (D1).

WHAT IT DOES.
  - Compiles the tree's dnsmasq/src/wallguard.c on the host with stubs for the rest of dnsmasq, writes a block table
    in wallguard_db.h's format (Python), and drives wallguard_answer() / wallguard_cname_listed() /
    wallguard_cname_verdict():
      D4  records carry the MAC with no per-device policy lines; an unknown device "-"; a passed query never looks
          a MAC up; a per-device policy line still decides by MAC exactly as before.
      D2  the asked name allowed exactly, or by a parent's allow-with-subdomains, is not blocked by its chain; an
          exact-only allow of a parent does not cover a child; an unlisted target never reaches a verdict.
      D1  the c record: hits "time ip bits c mac asked chain" (7 fields), live "time ip qtype c asked chain"
          (6 fields); every other record keeps its field count (hits 6, live 5).
  - Source pins: the policy MAC lookup still gated on sh.nmac, the record lookup after the rate limit, the verdict's
    allow check, the forward.c call, the prototype, the not-cached rule in rfc1035.c, both wallguard_db.h copies.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, shutil, struct, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "dnsmasq", "src", "wallguard.c")):
    print("SKIP: no router tree with dnsmasq/src/wallguard.c (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail != "" else ""))

eng, fw, rf, hd = rd("dnsmasq/src/wallguard.c"), rd("dnsmasq/src/forward.c"), rd("dnsmasq/src/rfc1035.c"), rd("dnsmasq/src/dnsmasq.h")

# ============================================================ source pins
check("D4: the policy still matches per-device lines only when it has some (semantics unchanged)",
      "if (client && sh.nmac && find_mac(client, mac, 1, now) == 6)" in eng)
hit = eng[eng.index("static void wallguard_hit("):eng.index("static void wallguard_live(")]
check("D4: a record looks the MAC up itself when the policy did not - after the rate limit, lazily (ARP cache)",
      "if (!have_mac && client && find_mac(client, lmac, 1, dnow) == 6)" in hit
      and hit.index("used >= WALLGUARD_HIT_RATE") < hit.index("find_mac(client, lmac"))
ver = eng[eng.index("int wallguard_cname_verdict("):]
check("D2: the verdict lets the asked name's table allow (exact or allow-with-subdomains walk) win over the chain",
      "wallguard_lookup(&sh.t.v, q, &abits) == WALLGUARD_ALLOWED" in ver
      and "extract_name(header, n, &p, q, EXTR_NAME_EXTRACT, 4)" in ver)
check("D1: a c block is recorded in hits and the live view under the asked name, the chain entry as the extra field",
      "wallguard_hit(client, sh.cname_bits & mask, 'c', asked ? q : sh.cname_name, sh.cname_name, mac, have_mac, now);" in ver
      and "wallguard_live(client, qtype, asked ? q : sh.cname_name, 'c', sh.cname_name);" in ver)
check("record formats: hits 6 fields + chain for c only; live 5 fields + chain for c only",
      '"%ld %s %x %c %s %s %s\\n"' in hit and '"%ld %s %x %c %s %s\\n"' in hit
      and '"%ld %s %u %c %s %s\\n"' in eng and '"%ld %s %u %c %s\\n"' in eng)
check("forward.c hands the reply to the verdict; dnsmasq.h prototype matches",
      "rc = wallguard_cname_verdict(header, n, wallguard_client, now) ? 4 : 0;" in fw
      and "int wallguard_cname_verdict(struct dns_header *header, size_t n, union mysockaddr *client, time_t now);" in hd)
check("rfc1035.c: a listed chain is still checked to the end and never cached (rebind, ipsets, not-cached rule)",
      "if (wallguard_listed)\n    return 3;" in rf and "wallguard_cname_listed(name)" in rf)
if os.path.isfile(os.path.join(SRC, "wallguard", "wallguard_db.h")):
    check("both copies of wallguard_db.h are identical", rd("wallguard/wallguard_db.h") == rd("dnsmasq/src/wallguard_db.h"))
check("edited engine files are ASCII only",
      all(all(ord(c) < 128 for c in t) for t in (eng, rd("dnsmasq/src/wallguard_db.h"))))

# ============================================================ host harness
FNV0, FNVP, M64 = 0xcbf29ce484222325, 0x100000001b3, (1 << 64) - 1
def fnv(s):
    h = FNV0
    for c in s.lower().encode():
        h = ((h ^ c) * FNVP) & M64
    return h
SUB = 0x80000000
def table(block, allow):
    """wallguard_db.h layout: hdr (784 B), block hashes, masks, pad 8, allow hashes, flags - host byte order"""
    b = sorted((fnv(n), m) for n, m in block.items()); a = sorted((fnv(n), f) for n, f in allow.items())
    hdr = struct.pack("=4sIIIIIQ", b"SHRD", 1, len(b), len(a), 0, 0, int(time.time())) + b"\0" * (31 * 24) + b"\0" * 8
    assert len(hdr) == 784
    out = hdr + b"".join(struct.pack("=Q", h) for h, _ in b) + b"".join(struct.pack("=I", m) for _, m in b)
    out += b"\0" * (-len(out) % 8)
    return out + b"".join(struct.pack("=Q", h) for h, _ in a) + b"".join(struct.pack("=I", f) for _, f in a)

HARNESS = r'''
#include "dnsmasq.h"
#undef free
struct daemon *dnsmasq_daemon;
static int mac_calls;
void free_real(const char *f, unsigned int l, void *p) { (void)f; (void)l; free(p); }
time_t dnsmasq_time(void) { return 1000; }
void my_syslog(int pri, const char *fmt, ...) { (void)pri; (void)fmt; }
void setup_reply(struct dns_header *h, unsigned int f, int e) { (void)h; (void)f; (void)e; }
unsigned char *skip_questions(struct dns_header *h, size_t n)
{ unsigned char *p = (unsigned char *)(h + 1); (void)n; while (*p) p += *p + 1; return p + 5; }
int add_resource_record(struct dns_header *h, char *limit, int *t, int no, unsigned char **pp, unsigned long ttl,
			int *off, unsigned short type, unsigned short cl, char *fmt, ...)
{ (void)h; (void)limit; (void)t; (void)no; (void)pp; (void)ttl; (void)off; (void)type; (void)cl; (void)fmt; return 0; }
struct crec *cache_find_by_name(struct crec *c, char *name, time_t now, unsigned int prot)
{ (void)c; (void)name; (void)now; (void)prot; return NULL; }
int lookup_domain(char *q, int fl, int *lo, int *hi) { (void)q; (void)fl; (void)lo; (void)hi; return 0; }
int reaper_nx_listed(const char *n) { (void)n; return 0; }
int find_mac(union mysockaddr *a, unsigned char *mac, int lazy, time_t now)
{
  (void)lazy; (void)now;
  mac_calls++;
  if (a->sa.sa_family == AF_INET && a->in.sin_addr.s_addr == inet_addr("192.168.50.10"))
    { memcpy(mac, "\xaa\xbb\xcc\xdd\xee\x01", 6); return 6; }
  return 0;
}
/* the question only: uncompressed labels, parm bytes must follow */
int extract_name(struct dns_header *h, size_t plen, unsigned char **pp, char *name, int func, unsigned int parm)
{
  unsigned char *p = *pp, *end = (unsigned char *)h + plen;
  char *o = name;
  (void)func;
  while (p < end && *p)
    {
      unsigned int l = *p++;
      if (l > 63 || p + l > end) return 0;
      if (o != name) *o++ = '.';
      memcpy(o, p, l); o += l; p += l;
    }
  if (p >= end) return 0;
  p++; *o = 0;
  if (p + parm > end) return 0;
  *pp = p;
  return 1;
}
static size_t mkq(unsigned char *buf, const char *name)
{
  unsigned char *p = buf + sizeof(struct dns_header);
  const char *s = name;
  memset(buf, 0, 512);
  ((struct dns_header *)buf)->qdcount = htons(1);
  while (*s)
    {
      const char *d = strchr(s, '.');
      size_t l = d ? (size_t)(d - s) : strlen(s);
      *p++ = (unsigned char)l; memcpy(p, s, l); p += l; s += l;
      if (*s == '.') s++;
    }
  *p++ = 0; *p++ = 0; *p++ = 1; *p++ = 0; *p++ = 1;	/* A, IN */
  return (size_t)(p - buf);
}
static union mysockaddr cl(const char *ip)
{ union mysockaddr a; memset(&a, 0, sizeof(a)); a.in.sin_family = AF_INET; a.in.sin_addr.s_addr = inet_addr(ip); return a; }
static int ask(const char *name, const char *ip)
{
  unsigned char buf[512]; size_t n = mkq(buf, name); union mysockaddr a = cl(ip); int ede;
  strcpy(daemon->namebuff, name);
  return wallguard_answer((struct dns_header *)buf, (char *)buf + 512, n, &a, T_A, dnsmasq_time(), &ede) > 0;
}
static int cname(const char *asked, const char *target, const char *ip)
{
  unsigned char buf[512]; size_t n = mkq(buf, asked); union mysockaddr a = cl(ip);
  if (!wallguard_cname_listed(target)) return -1;
  return wallguard_cname_verdict((struct dns_header *)buf, n, &a, dnsmasq_time());
}
int main(int argc, char **argv)
{
  static struct daemon d;
  int c0;
  if (argc < 3) return 2;
  dnsmasq_daemon = &d; d.wallguard_dir = argv[1]; d.namebuff = malloc(MAXDNAMESTR + 1); d.pipe_to_parent = -1;
  if (!strcmp(argv[2], "main"))
    {
      printf("block_known=%d\n", ask("x.ads.test", "192.168.50.10"));
      printf("block_unknown=%d\n", ask("y.ads.test", "10.0.0.9"));
      c0 = mac_calls; ask("news.test", "192.168.50.10"); ask("allowed.paramount.test", "192.168.50.10");
      printf("pass_mac_calls=%d\n", mac_calls - c0);
      c0 = mac_calls; ask("z.ads.test", "192.168.50.10");
      printf("block_mac_calls=%d\n", mac_calls - c0);
      printf("cname_block=%d\n", cname("www.paramount.test", "edge.tracker-cdn.test", "192.168.50.10"));
      printf("cname_allowed_exact=%d\n", cname("allowed.paramount.test", "edge.tracker-cdn.test", "192.168.50.10"));
      printf("cname_allowed_sub=%d\n", cname("www.okzone.test", "edge.tracker-cdn.test", "192.168.50.10"));
      printf("cname_allowed_apex=%d\n", cname("okzone.test", "edge.tracker-cdn.test", "192.168.50.10"));
      printf("cname_exact_not_sub=%d\n", cname("sub.exact.test", "edge.tracker-cdn.test", "192.168.50.10"));
      printf("cname_unknown_dev=%d\n", cname("img.paramount.test", "edge.tracker-cdn.test", "10.0.0.9"));
      printf("cname_unlisted_target=%d\n", cname("www.paramount.test", "cdn.clean.test", "192.168.50.10"));
    }
  else
    {
      printf("mac_bypass=%d\n", ask("x.ads.test", "192.168.50.10"));
      printf("other_blocked=%d\n", ask("x.ads.test", "10.0.0.9"));
      printf("cname_mac_bypass=%d\n", cname("www.paramount.test", "edge.tracker-cdn.test", "192.168.50.10"));
      printf("cname_other=%d\n", cname("www.paramount.test", "edge.tracker-cdn.test", "10.0.0.9"));
    }
  return 0;
}
'''

if not CC:
    print("SKIP (harness): no host compiler - source pins only")
else:
    w = tempfile.mkdtemp(prefix="wgeng_")
    try:
        inc = os.path.join(SRC, "dnsmasq", "src")
        hc, exe = os.path.join(w, "h.c"), os.path.join(w, "h")
        open(hc, "w").write(HARNESS)
        flags = ["-std=gnu99", "-Wall", "-DHAVE_BROKEN_RTC", "-DNO_ID", "-DNO_AUTH", "-DNO_INOTIFY", "-DNO_DUMPFILE",
                 "-DNO_GMP", "-DNO_DBUS", '-DVERSION="host"', "-I", inc]
        b = subprocess.run([CC] + flags + ["-o", exe, os.path.join(inc, "wallguard.c"), hc], capture_output=True, text=True)
        warn = [l for l in b.stderr.splitlines() if "wallguard.c" in l and "warning" in l]
        check("the engine builds on the host with the harness, no warnings from wallguard.c", b.returncode == 0 and not warn,
              (b.stderr[-800:]))
        if b.returncode == 0:
            db = table({"ads.test": 0x2 | SUB, "tracker-cdn.test": 0x40 | SUB},
                       {"allowed.paramount.test": 0, "okzone.test": SUB, "exact.test": 0})
            def setup(name, policy):
                sd = os.path.join(w, name); os.makedirs(os.path.join(sd, "run"))
                open(os.path.join(sd, "db"), "wb").write(db)
                open(os.path.join(sd, "policy"), "w").write(policy)
                open(os.path.join(sd, "live.on"), "w").close()
                return sd
            def go(sd, mode):
                r = subprocess.run([exe, sd, mode], capture_output=True, text=True, timeout=30)
                kv = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
                rec = lambda leaf: [l.split() for l in open(os.path.join(sd, "run", leaf)).read().splitlines()
                                    if not l.startswith("#")] if os.path.exists(os.path.join(sd, "run", leaf)) else []
                return kv, rec("hits"), rec("live")
            sd = setup("main", "default 7fffffff\n")
            kv, hits, live = go(sd, "main")
            MAC = "aa:bb:cc:dd:ee:01"
            q = [x for x in hits if x[3] == "q"]; c = [x for x in hits if x[3] == "c"]
            check("blocking works with no per-device policy lines", kv.get("block_known") == "1" and kv.get("block_unknown") == "1", kv)
            check("D4: a q record carries the device MAC although the policy has no per-device lines",
                  any(x[1] == "192.168.50.10" and x[4] == MAC and x[5] == "ads.test" for x in q), q)
            check("D4: an unknown device's record carries '-'", any(x[1] == "10.0.0.9" and x[4] == "-" for x in q), q)
            check("D4 cost: a passed (or allowed) query never looks a MAC up; a recorded block looks it up once",
                  kv.get("pass_mac_calls") == "0" and kv.get("block_mac_calls") == "1", kv)
            check("D2: the chain into a listed name still blocks a name that is not allowed", kv.get("cname_block") == "1", kv)
            check("D2: the asked name allowed exactly - the chain no longer blocks it", kv.get("cname_allowed_exact") == "0", kv)
            check("D2: the asked name under an allow-with-subdomains entry (and that entry's own name) - not blocked",
                  kv.get("cname_allowed_sub") == "0" and kv.get("cname_allowed_apex") == "0", kv)
            check("D2: an exact-only allow of a parent does not cover a child (same semantics as the table)",
                  kv.get("cname_exact_not_sub") == "1", kv)
            check("an unlisted CNAME target never reaches a verdict", kv.get("cname_unlisted_target") == "-1", kv)
            check("D1: a c hit is 7 fields - time ip bits c mac asked chain - under the asked name, with the MAC",
                  any(x[1:] == ["192.168.50.10", "40", "c", MAC, "www.paramount.test", "tracker-cdn.test"] for x in c), c)
            check("D1: ...for an unknown device too, MAC '-'",
                  any(x[1:] == ["10.0.0.9", "40", "c", "-", "img.paramount.test", "tracker-cdn.test"] for x in c), c)
            check("D2: allowed names left no c record", not any(x[5] in ("allowed.paramount.test", "www.okzone.test", "okzone.test")
                                                              for x in c), c)
            check("every other hit keeps 6 fields; every c hit has 7", all(len(x) == 6 for x in q) and c and all(len(x) == 7 for x in c), hits)
            lc = [x for x in live if x[3] == "c"]
            check("D1: the live view gets the c block - time ip qtype c asked chain",
                  any(x[1:] == ["192.168.50.10", "1", "c", "www.paramount.test", "tracker-cdn.test"] for x in lc), live)
            check("live: other verdicts keep 5 fields (b, -, a)", all(len(x) == 5 for x in live if x[3] != "c")
                  and any(x[3] == "b" for x in live) and any(x[3] == "-" for x in live) and any(x[3] == "a" for x in live), live)
            check("records are stamped with the date", hits and abs(int(hits[0][0]) - time.time()) < 120, hits[:1])

            sd2 = setup("macpol", "default 7fffffff\nmac %s 0\n" % MAC)
            kv2, hits2, _ = go(sd2, "macpol")
            check("policy unchanged: a per-device line (Bypass by MAC) still decides for that device only",
                  kv2.get("mac_bypass") == "0" and kv2.get("other_blocked") == "1", kv2)
            check("...and the CNAME verdict follows it", kv2.get("cname_mac_bypass") == "0" and kv2.get("cname_other") == "1", kv2)
    finally:
        shutil.rmtree(w, ignore_errors=True)

print("\n%d failure(s)" % len(fails) if fails else "\nall checks passed")
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
