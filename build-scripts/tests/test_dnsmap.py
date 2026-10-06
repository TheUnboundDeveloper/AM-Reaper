#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The passive DNS name map (rdnsmapd) - parser, table, backfill and kernel filter, run on the host.

WHY THIS EXISTS. Flow Explorer destination names (v3.3.4) come from a daemon that parses
every DNS reply crossing the router CPU and writes ip -> name into a 128 KB table that httpd
mmaps in place (shared/reaper_dnsmap.h). Nothing else in the tree exercises a DNS wire parser,
and the kernel filter that keeps the daemon's cost at zero is a hand-transcribed classic BPF
array: a wrong jump offset silently kills the feature with a green build.

WHAT IT DOES. Compiles rdnsmapd/rdnsmapd.c on the host (RDM_TEST drops its main) behind a
30-line test main that feeds captured-looking frames into a calloc'd table and prints the
entries, then asserts:
  - an A reply with a CNAME chain maps the ADDRESS to the QNAME the client asked for (never
    the CNAME target), with the TTL floor applied;
  - a second QNAME for the same address updates the name and counts a change (ndist);
  - AAAA-only, truncated (TC), NXDOMAIN, two-question and over-long-label replies add nothing;
    a mixed-case QNAME is stored lower-case; a name longer than the slot keeps its tail;
    a QNAME carrying a double quote is refused (the CGI prints names raw inside JSON);
  - an IPv6-carried reply is parsed; nine addresses sharing one probe window evict the
    earliest-expiring entry and nothing else;
  - the one-shot backfill (Names off -> on): the PTR query encodes the address with the target
    index as its id, an answer lands as a REVERSE name (ndist 0), the first forward reply takes
    over, a learned name is never downgraded, and the conntrack scan takes original-tuple remote
    ends only, deduplicated, skipping IPv6, LAN, CGNAT and already-named addresses;
  - the sock_filter array, extracted from the source, accepts the sample replies and rejects a
    TCP segment, a UDP datagram from another port, a later IP fragment and an ARP frame;
  - the wiring: web.c, services.c, rc.h, defaults.c, the root Makefile, the page, the markers,
    and every RCON_ token the page uses in all 25 dictionaries.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's
release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import glob, os, re, shutil, struct, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rdnsmapd", "rdnsmapd.c")):
    skip("no router source tree with rdnsmapd (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

# ---------------------------------------------------------------- frame builders
def dns_name(s):
    out = b""
    for lab in s.split("."):
        out += bytes([len(lab)]) + lab.encode("latin-1")
    return out + b"\x00"

def rr(owner, rtype, ttl, rdata):
    return owner + struct.pack(">HHIH", rtype, 1, ttl, len(rdata)) + rdata

def dns_reply(qname, answers, flags=0x8180, qd=1, qtype=1, ident=0x1234):
    """answers: list of (owner bytes, type, ttl, rdata)"""
    hdr = struct.pack(">HHHHHH", ident, flags, qd, len(answers), 0, 0)
    q = dns_name(qname) + struct.pack(">HH", qtype, 1)
    body = b"".join(rr(*a) for a in answers)
    return hdr + q + body

PTR_Q = b"\xc0\x0c"                        # pointer to the question name

def eth(payload, ethertype):
    return bytes.fromhex("001122334455") + bytes.fromhex("66778899aabb") + struct.pack(">H", ethertype) + payload

def udp(payload, sport=53, dport=40000):
    return struct.pack(">HHHH", sport, dport, 8 + len(payload), 0) + payload

def ipv4(payload, proto=17, frag=0):
    tot = 20 + len(payload)
    hdr = struct.pack(">BBHHHBBH4s4s", 0x45, 0, tot, 0x4242, frag, 64, proto, 0,
                      bytes([10, 1, 1, 1]), bytes([10, 1, 1, 50]))
    return hdr + payload

def ipv6(payload, nh=17):
    hdr = struct.pack(">IHBB", 0x60000000, len(payload), nh, 64) + bytes(16) + bytes(16)
    return hdr + payload

def frame4(dns, sport=53):
    return eth(ipv4(udp(dns, sport)), 0x0800)

def frame6(dns):
    return eth(ipv6(udp(dns)), 0x86dd)

A1 = bytes([93, 184, 216, 34])
replies = {
    "chain":   frame4(dns_reply("example.com", [(PTR_Q, 5, 60, dns_name("edge.cdn.net")), (dns_name("edge.cdn.net"), 1, 20, A1)])),
    "rename":  frame4(dns_reply("other.example", [(PTR_Q, 1, 300, A1)])),
    "aaaa":    frame4(dns_reply("v6only.example", [(PTR_Q, 28, 60, bytes(16))], qtype=28)),
    "tc":      frame4(dns_reply("trunc.example", [(PTR_Q, 1, 60, bytes([1, 2, 3, 4]))], flags=0x8380)),
    "nxdomain": frame4(dns_reply("nx.example", [(PTR_Q, 1, 60, bytes([1, 2, 3, 5]))], flags=0x8183)),
    "twoq":    frame4(dns_reply("twoq.example", [(PTR_Q, 1, 60, bytes([1, 2, 3, 6]))], qd=2)),
    "mixed":   frame4(dns_reply("ExAmPlE.OrG", [(PTR_Q, 1, 7200, bytes([198, 51, 100, 7]))])),
    "long":    frame4(dns_reply("a" * 35 + "." + "b" * 36 + ".example.com", [(PTR_Q, 1, 60, bytes([198, 51, 100, 8]))])),
    "quote":   frame4(dns_reply('bad"name.example', [(PTR_Q, 1, 60, bytes([198, 51, 100, 9]))])),
    "v6outer": frame6(dns_reply("six.example", [(PTR_Q, 1, 60, bytes([198, 51, 100, 10]))])),
}

# backfill: PTR answers are raw DNS payloads whose id indexes the target list (id 0 here)
PTRS = {
    "ptr":   dns_reply("34.216.184.93.in-addr.arpa", [(PTR_Q, 12, 3600, dns_name("ptr.example.net"))], qtype=12, ident=0),
    "ptr2":  dns_reply("34.216.184.93.in-addr.arpa", [(PTR_Q, 12, 3600, dns_name("example.com"))], qtype=12, ident=0),
}
CT_FIXTURE = "\n".join([
    "ipv4     2 tcp      6 431999 ESTABLISHED src=10.1.1.50 dst=93.184.216.34 sport=50000 dport=443 packets=10 bytes=1000 src=93.184.216.34 dst=203.0.113.9 sport=443 dport=50000 packets=9 bytes=900 [ASSURED] mark=0 use=1",
    "ipv4     2 udp      17 29 src=10.1.1.51 dst=93.184.216.34 sport=5000 dport=443 packets=1 bytes=100 src=93.184.216.34 dst=203.0.113.9 sport=443 dport=5000 packets=1 bytes=100 mark=0 use=1",
    "ipv4     2 tcp      6 100 ESTABLISHED src=10.1.1.52 dst=198.51.100.7 sport=1 dport=80 packets=1 bytes=1 src=198.51.100.7 dst=203.0.113.9 sport=80 dport=1 packets=1 bytes=1 mark=0 use=1",
    "ipv4     2 tcp      6 100 ESTABLISHED src=10.1.1.52 dst=192.168.50.9 sport=2 dport=80 packets=1 bytes=1 src=192.168.50.9 dst=10.1.1.52 sport=80 dport=2 packets=1 bytes=1 mark=0 use=1",
    "ipv6     10 tcp      6 100 ESTABLISHED src=2001:db8::1 dst=2001:db8::2 sport=3 dport=443 packets=1 bytes=1 src=2001:db8::2 dst=2001:db8::1 sport=443 dport=3 packets=1 bytes=1 mark=0 use=1",
    "ipv4     2 udp      17 20 src=100.64.0.5 dst=10.1.1.1 sport=4 dport=53 packets=1 bytes=1 src=10.1.1.1 dst=100.64.0.5 sport=53 dport=4 packets=1 bytes=1 mark=0 use=1",
    ""])

# nine addresses that share one probe window (same 11-bit hash), with distinct expiries
def rdm_hash(ip):
    return ((ip * 0x9E3779B1) & 0xffffffff) >> 21
buckets = {}
collide = None
for ip in range(0x0b000001, 0x0b000001 + 400000, 7):
    nip = struct.unpack("<I", struct.pack(">I", ip))[0]      # the table hashes the network-order u32 as stored
    buckets.setdefault(rdm_hash(nip), []).append(ip)
    if len(buckets[rdm_hash(nip)]) >= 9:
        collide = buckets[rdm_hash(nip)]
        break
if not collide:
    die("could not find nine colliding addresses")
evict = []
for k, ip in enumerate(collide):
    evict.append(frame4(dns_reply("host%d.example" % k, [(PTR_Q, 1, 3600 + 600 * k, struct.pack(">I", ip))])))

# ---------------------------------------------------------------- host compile
td = tempfile.mkdtemp(prefix="dnsmap-")
try:
    MAIN = r'''
#include <stdio.h>
int main(int argc, char **argv)
{
	void *map = calloc(1, RDM_SIZE);
	struct rdm_hdr *h = map;
	struct rdm_ent *t = rdm_table(map);
	uint32_t now = 1000000, i, tg[RDM_BF_MAX];
	FILE *f; static uint8_t fb[4096]; int n, a, ntg;

	h->magic = RDM_MAGIC; h->slots = RDM_SLOTS; h->esize = sizeof(struct rdm_ent);
	printf("bpf %u\n", (unsigned)(sizeof(rdm_bpf) / sizeof(rdm_bpf[0])));
	for (a = 1; a < argc; a++) {
		if (!strcmp(argv[a], "--targets")) {
			ntg = rdm_targets(tg, RDM_BF_MAX, t, now);
			printf("targets %d\n", ntg);
			for (i = 0; i < (uint32_t)ntg; i++)
				printf("target %u.%u.%u.%u\n", tg[i] & 255, (tg[i] >> 8) & 255, (tg[i] >> 16) & 255, tg[i] >> 24);
			continue;
		}
		if (!strcmp(argv[a], "--ptrq") && a + 1 < argc) {
			struct in_addr ia; char nm[256]; uint8_t qb[64];
			if (!inet_aton(argv[a + 1], &ia)) return 3;
			n = rdm_ptr_query(qb, sizeof(qb), 7, ia.s_addr);
			if (n > 12 && rdm_readname(qb, n, 12, nm) > 0) printf("ptrq %s %d %u\n", nm, n, (qb[0] << 8) | qb[1]);
			a += 1;
			continue;
		}
		if (!strcmp(argv[a], "--ptr") && a + 2 < argc) {
			struct in_addr ia;
			if (!inet_aton(argv[a + 1], &ia)) return 3;
			tg[0] = ia.s_addr;
			if (!(f = fopen(argv[a + 2], "rb"))) return 2;
			n = (int)fread(fb, 1, sizeof(fb), f); fclose(f);
			rdm_parse_ptr(fb, n, map, now, tg, 1);
			a += 2;
			continue;
		}
		if (!(f = fopen(argv[a], "rb"))) return 2;
		n = (int)fread(fb, 1, sizeof(fb), f); fclose(f);
		rdm_parse(fb, n, map, now);
	}
	printf("seen %u upd %u\n", h->seen, h->upd);
	for (i = 0; i < RDM_SLOTS; i++)
		if (t[i].ip)
			printf("%u.%u.%u.%u %s %u %u\n", t[i].ip & 255, (t[i].ip >> 8) & 255, (t[i].ip >> 16) & 255, t[i].ip >> 24,
			       t[i].name, t[i].exp - now, t[i].ndist);
	return 0;
}
'''
    csrc = os.path.join(td, "t.c")
    with open(csrc, "w") as f:
        f.write('#define RDM_TEST 1\n#include "rdnsmapd.c"\n' + MAIN)
    ctf = os.path.join(td, "nf_conntrack")
    with open(ctf, "w") as f:
        f.write(CT_FIXTURE)
    exe = os.path.join(td, "t")
    p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wno-unused-parameter", '-DRDM_CT="%s"' % ctf, "-I", os.path.join(SRC, "shared"),
                        "-I", os.path.join(SRC, "rdnsmapd"), "-o", exe, csrc], capture_output=True, text=True)
    if p.returncode != 0:
        die("host compile failed:\n" + p.stderr)
    if "warning" in p.stderr:
        die("host compile warnings:\n" + p.stderr)
    check("rdnsmapd.c + reaper_dnsmap.h compile clean with -Wall -Wextra", True)

    extra = {}
    def run(items):
        """items: a replies[] key or raw frame bytes (a captured frame), ("--ptr", ip, payload) (a PTR
        answer for that target), "--targets" (list conntrack targets now), "--ptrq:<ip>" (encode a query)"""
        args = []
        for i, it in enumerate(items):
            fp = os.path.join(td, "f%02d.bin" % i)
            if isinstance(it, tuple):
                with open(fp, "wb") as f: f.write(it[2])
                args += [it[0], it[1], fp]
            elif isinstance(it, str) and it.startswith("--ptrq:"):
                args += ["--ptrq", it[7:]]
            elif isinstance(it, str) and it.startswith("--"):
                args.append(it)
            else:
                with open(fp, "wb") as f: f.write(replies[it] if isinstance(it, str) else it)
                args.append(fp)
        r = subprocess.run([exe] + args, capture_output=True, text=True)
        if r.returncode != 0:
            die("test binary failed: %s %s" % (r.stdout, r.stderr))
        ents = {}
        seen = upd = None
        extra.clear(); extra["targets"] = []
        for ln in r.stdout.splitlines():
            w = ln.split()
            if w[0] == "seen": seen, upd = int(w[1]), int(w[3])
            elif w[0] == "target": extra["targets"].append(w[1])
            elif w[0] == "targets": extra["ntargets"] = int(w[1])
            elif w[0] == "ptrq": extra["ptrq"] = (w[1], int(w[2]), int(w[3]))
            elif w[0] != "bpf": ents[w[0]] = (w[1], int(w[2]), int(w[3]))
        return ents, seen, upd

    e, seen, upd = run(["chain"])
    check("CNAME chain: the address maps to the QNAME, not the CNAME target",
          e.get("93.184.216.34", ("",))[0] == "example.com", e)
    check("TTL floor: a 20 s record lives RDM_TTL_MIN", e.get("93.184.216.34", ("", 0))[1] == 3600, e)
    check("counters: one reply seen, one A record written", (seen, upd) == (1, 1), (seen, upd))

    e, seen, upd = run(["chain", "rename"])
    check("a new QNAME for the same address: name updated, ndist 2",
          e.get("93.184.216.34") == ("other.example", 3600, 2), e)

    e, seen, upd = run(["aaaa", "tc", "nxdomain", "twoq"])
    check("AAAA-only, truncated, NXDOMAIN and two-question replies add nothing", e == {}, e)
    check("only the AAAA reply counted as parsed (TC/RCODE/QDCOUNT fail the header test)", seen == 1 and upd == 0, (seen, upd))

    e, seen, upd = run(["mixed", "long", "quote", "v6outer"])
    check("QNAME is stored lower-case", e.get("198.51.100.7", ("",))[0] == "example.org", e)
    check("a name longer than the slot keeps its registrable tail",
          e.get("198.51.100.8", ("",))[0] == "b" * 36 + ".example.com", e)
    check("a QNAME with a double quote is refused", "198.51.100.9" not in e, e)
    check("an IPv6-carried reply is parsed", e.get("198.51.100.10", ("",))[0] == "six.example", e)

    e, seen, upd = run(evict)
    dotted = lambda ip: "%u.%u.%u.%u" % (ip >> 24, (ip >> 16) & 255, (ip >> 8) & 255, ip & 255)
    check("nine addresses in one probe window: the earliest-expiring entry is evicted, the other eight stay",
          dotted(collide[0]) not in e and all(dotted(ip) in e for ip in collide[1:]) and len(e) == 8, sorted(e))

    # ---------------------------------------------------------------- the one-shot reverse backfill
    e, seen, upd = run(["--ptrq:93.184.216.34"])
    check("PTR query encodes d.c.b.a.in-addr.arpa with the target index as its id",
          extra.get("ptrq", ("",))[0] == "34.216.184.93.in-addr.arpa" and extra["ptrq"][2] == 7, extra.get("ptrq"))
    e, seen, upd = run([("--ptr", "93.184.216.34", PTRS["ptr"])])
    check("a PTR answer stores a REVERSE name: ndist 0, one-hour life",
          e.get("93.184.216.34") == ("ptr.example.net", 3600, 0) and upd == 1, (e, upd))
    e, seen, upd = run([("--ptr", "93.184.216.34", PTRS["ptr"]), "chain"])
    check("the first forward reply replaces the reverse name and counts as a change (ndist 1)",
          e.get("93.184.216.34") == ("example.com", 3600, 1), e)
    e, seen, upd = run(["chain", ("--ptr", "93.184.216.34", PTRS["ptr"])])
    check("a learned name is never downgraded by a later PTR answer",
          e.get("93.184.216.34") == ("example.com", 3600, 1) and upd == 1, (e, upd))
    e, seen, upd = run([("--ptr", "93.184.216.34", PTRS["ptr2"]), "chain"])
    check("a forward reply that agrees with the reverse name confirms it (ndist 0 -> 1, no change counted)",
          e.get("93.184.216.34") == ("example.com", 3600, 1), e)
    e, seen, upd = run(["--targets"])
    check("targets: original tuples only, remote ends only, deduplicated, IPv6 and LAN/CGNAT rows skipped",
          extra["targets"] == ["93.184.216.34", "198.51.100.7"], extra["targets"])
    e, seen, upd = run(["chain", "--targets"])
    check("targets: an address the table already names is not asked about again",
          extra["targets"] == ["198.51.100.7"], extra["targets"])

    # ---------------------------------------------------------------- the kernel filter, interpreted
    src = read("rdnsmapd/rdnsmapd.c")
    m = re.search(r"static struct sock_filter rdm_bpf\[\] = \{(.*?)\n\};", src, re.S)
    if not m:
        die("rdm_bpf array not found")
    insns = [tuple(int(x, 0) for x in g) for g in re.findall(r"\{\s*(0x[0-9a-fA-F]+),\s*(\d+),\s*(\d+),\s*(0x[0-9a-fA-F]+)\s*\}", m.group(1))]
    check("filter has 16 instructions", len(insns) == 16, len(insns))

    def bpf(pkt):
        A = X = 0; pc = 0
        def ld(off, size):
            if off < 0 or off + size > len(pkt): return None
            return int.from_bytes(pkt[off:off + size], "big")
        while pc < len(insns):
            code, jt, jf, k = insns[pc]; pc += 1
            if code == 0x28: A = ld(k, 2)
            elif code == 0x30: A = ld(k, 1)
            elif code == 0x48: A = ld(X + k, 2)
            elif code == 0xb1:
                b = ld(k, 1); X = None if b is None else 4 * (b & 0xf)
            elif code == 0x15: pc += jt if A == k else jf
            elif code == 0x45: pc += jt if (A & k) else jf
            elif code == 0x06: return k
            else: die("unexpected BPF opcode 0x%x" % code)
            if A is None or X is None: return 0
        return 0

    check("filter accepts the IPv4 and IPv6 replies", bpf(replies["chain"]) > 0 and bpf(replies["v6outer"]) > 0)
    tcp = eth(ipv4(b"\x00\x35\x9c\x40" + bytes(16), proto=6), 0x0800)
    other = frame4(dns_reply("x.example", [(PTR_Q, 1, 60, A1)]), sport=5353)
    frag = eth(ipv4(udp(dns_reply("x.example", [(PTR_Q, 1, 60, A1)])), frag=0x0001), 0x0800)
    arp = eth(bytes(28), 0x0806)
    check("filter rejects TCP, another source port, a later fragment and ARP",
          bpf(tcp) == 0 and bpf(other) == 0 and bpf(frag) == 0 and bpf(arp) == 0)

    # ---------------------------------------------------------------- wiring
    web = read("httpd/web.c")
    for want in ('#include "reaper_dnsmap.h"', 'rconn_names_table(', 'rdm_find(rdm, ra.s_addr, rdm_now)', 'rdm_touch(e, rdm_now)',
                 '\\"srvn\\":\\"%s\\",\\"srvx\\":%u', 'get_cgi("names")', 'notify_rc("restart_rdnsmap")', '\\"rtr\\":[',
                 'f_write_string(RDM_BACKFILL, "1\\n", 0, 0)'):
        if want not in web:
            die("web.c lacks %s" % want)
    check("web.c maps the table, names the remote end per row, lists the router addresses, toggles the switch", True)
    # r9 attempt 1 (2026-10-05): reaper_audit() is a static defined ~800 lines BELOW the conn CGI; a call
    # without a prior prototype made gcc see an implicit non-static declaration first and the build
    # died at "static declaration follows non-static declaration". The host test cannot compile web.c,
    # so pin the ordering instead.
    proto = "static void reaper_audit(const char *feat, const char *act, const char *detail);"
    check("web.c declares reaper_audit before the Names toggle calls it",
          proto in web and web.index(proto) < web.index('get_cgi("names")'), "")
    svc = read("rc/services.c")
    for want in ('void\nstart_rdnsmap(void)', 'xstart("rdnsmapd")', 'strcmp(script, "rdnsmap")', 'unlink("/tmp/reaper/dnsmap")'):
        if want not in svc:
            die("services.c lacks %s" % want)
    check("services.c starts, stops, restarts the daemon and removes the table on opt-out", True)
    if "start_rdnsmap" not in read("rc/rc.h"): die("rc.h lacks start_rdnsmap")
    if '"rconn_names", "1"' not in read("shared/defaults.c"): die("defaults.c lacks rconn_names=1")
    if "obj-y += rdnsmapd" not in read("Makefile"): die("root Makefile lacks obj-y += rdnsmapd")
    check("rc.h, defaults.c (default on) and the root Makefile carry the daemon", True)

    page = open(os.path.join(SRC, "www", "Reaper_Conn.asp"), "rb").read()
    if any(b > 0x7f for b in page): die("Reaper_Conn.asp is not pure ASCII")
    page = page.decode("ascii")
    for want in ('destCell(c)', 'function destName(c)', 'c.srvn', 'names[c.srv]', 'delete names[k]', 'id="namesbtn"',
                 '<#RCON_44#>', '<#RCON_45#>', '<#RCON_46#>', '<#RSYS_02#>', '"?names="', 'c.srvx===0', '.qn.rev',
                 # the detail panel follows the reader: stretched cell, placement from the shell's visible slice
                 'class="dside"', '.dside{align-self:stretch}', 'function placeDetail()', '"--rv-top"', '"--rv-h"',
                 'new MutationObserver(placeDetail)', 'addEventListener("scroll",placeDetail', '    placeDetail();\n  }'):
        if want not in page:
            die("Reaper_Conn.asp lacks %s" % want)
    # rule 29: a token inside a single-quoted JS string never reaches the dictionary pass. The
    # page's own style puts tokens in template literals BETWEEN single-quoted fragments
    # ('...'+`<#X#>`+'...'), so blank the literals first or every such line reads as a hit.
    if re.search(r"'[^'\n]*<#[A-Za-z_0-9]+#>[^'\n]*'", re.sub(r"`[^`\n]*`", "``", page)):
        die("a dict token sits inside a single-quoted JS string (rule 29)")
    check("page renders name over address, keeps a name while the address is listed, drops it after, toggles", True)
    check("the detail panel is no longer position:sticky (it cannot engage inside the shell frame)",
          "position:sticky" not in re.search(r"^\.detail\{[^\n]*$", page, re.M).group(0), "")
    toks = sorted(set(re.findall(r"<#(RCON_\d+)#>", page)))
    dicts = [d for d in glob.glob(os.path.join(SRC, "www", "*.dict")) if not d.endswith("temp.dict")]
    if len(dicts) != 25: die("expected 25 dictionaries, found %d" % len(dicts))
    for d in dicts:
        keys = set(re.findall(r"^(RCON_\d+)=", open(d, encoding="utf-8", errors="surrogateescape").read(), re.M))
        missing = [t for t in toks if t not in keys]
        if missing: die("%s lacks %s" % (os.path.basename(d), ", ".join(missing)))
    check("every RCON token the page uses exists in all 25 dictionaries (%d tokens)" % len(toks), True)
    mk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verify_markers.txt"), encoding="utf-8").read()
    check("markers pin the daemon, the httpd path, the page field and the rc start",
          all(w in mk for w in ("bin/rdnsmapd|RDM1|1", "usr/sbin/httpd|/tmp/reaper/dnsmap|1", "www/Reaper_Conn.asp|srvn|1", "sbin/rc|rdnsmapd|1",
                                "bin/rdnsmapd|in-addr|1", "usr/sbin/httpd|dnsmap.backfill|1", "www/Reaper_Conn.asp|dside|1")))

    if fails:
        print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
    print("all checks passed: the DNS map names addresses by what the client asked for, stays bounded, the kernel filter matches only DNS replies, and the feature is wired end to end")
finally:
    shutil.rmtree(td, ignore_errors=True)
