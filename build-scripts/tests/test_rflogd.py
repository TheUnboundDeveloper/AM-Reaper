#!/usr/bin/env python3
"""rflogd, the firewall log collector (NFLOG plan, 2026-11-08): the real rflogd.c host-compiled with -DRFLOGD_HOST
and driven on synthetic netlink messages.

  - the CONFIG message, byte for byte: BIND, copy mode PACKET with the copy length, 64 KB kernel buffer, 1 s flush,
    100-packet batches, sequence numbers on; never PF_BIND (it would swap the family's default logger);
  - lines in xt_LOG's text: IPv4 TCP with SEQ / OPT for the stock and blob prefixes and without for Warden's, IPv6 UDP,
    ICMP / ICMPv6 echo, MARK, a truncated header, a malformed attribute (refused), a prefix with control bytes;
  - lost lines from the sequence numbers (gaps, a backwards jump, the 32-bit wrap);
  - suppressed lines from iptables-save -c counters, across a rule reload;
  - fwlog.conf parsing (bad values ignored, the remote target checked), the ISO timestamp.
Addresses are documentation ranges (RFC 5737 / RFC 3849). Exit 0 pass, 1 fail, 77 skipped.
"""
import json, os, shutil, struct, subprocess, sys, tempfile, datetime, socket

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rflogd", "rflogd.c")):
    print("SKIP: no router source tree with rflogd (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no host compiler"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:500] if detail else ""))

src = open(os.path.join(SRC, "rflogd", "rflogd.c"), encoding="utf-8").read()
check("rflogd.c credits netfilter / nfnetlink_log and copies no upstream code",
      "https://www.netfilter.org/" in src and "net/netfilter/nfnetlink_log.c" in src and "no upstream code is copied" in src)
check("rflogd reads no nvram and links no libshared",
      "nvram" not in src.split("*/", 1)[1].replace("reads no nvram", "") and "-lshared" not in open(os.path.join(SRC, "rflogd", "Makefile")).read())
check("privileges: every capability but NET_ADMIN / NET_RAW dropped, no new privileges, not dumpable",
      "PR_CAPBSET_DROP" in src and "PR_SET_NO_NEW_PRIVS" in src and "PR_SET_DUMPABLE, 0" in src
      and src.index("rfl_drop_caps();") < src.index("while (!g_term)"))
check("timers on the monotonic clock; the clock counts as set only past the binary's build time - the router boots at 2023-12-31 (_r3/_r4 metal)",
      "clock_gettime(CLOCK_MONOTONIC, &t);" in src and "if (!clock_set(since) && clock_set(now))" in src
      and "if (!clock_set(now)) {" in src and 'stat("/proc/self/exe", &bst) == 0 && bst.st_mtime > clock_floor' in src
      and "1600000000)" not in src.replace("static time_t clock_floor = 1600000000;", "")
      and "hour_at = mono_start + 3600;" in src and "if (m >= hour_at) {" in src and "now - stats_at" not in src
      and "now >= hour_at" not in src)
mk = open(os.path.join(SRC, "Makefile"), encoding="utf-8", errors="replace").read()
check("top Makefile builds and installs rflogd beside rdnsmapd",
      "obj-y += rflogd\n" in mk and "rflogd-install:\n\t$(MAKE) -C rflogd INSTALLDIR=$(INSTALLDIR)/rflogd install" in mk)
rmk = open(os.path.join(SRC, "rflogd", "Makefile"), encoding="utf-8").read()
check("rflogd/Makefile: PIE, RELRO/now, FORTIFY, stack protector, installs to /bin",
      "-fPIE" in rmk and "-z,relro,-z,now" in rmk and "_FORTIFY_SOURCE=2" in rmk and "-fstack-protector-strong" in rmk
      and "$(INSTALLDIR)/bin/rflogd" in rmk)

DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
struct rfl_conf { int groups[8], ngroups; long ram_kb, keep_days, keep_mb; unsigned cpu; int copy; char fwd_host[64]; int fwd_port; char host[64]; };
struct rfl_pkt { int family; char prefix[64]; uint32_t mark, indev, outdev, physin, physout, seq; int has_seq;
	const unsigned char *payload, *hw; size_t plen, hwlen; long long ts_sec, ts_usec; int has_ts; };
size_t rfl_cfg_msg(unsigned char *, size_t, uint16_t, uint8_t, int, int, uint32_t);
int rfl_parse(const unsigned char *, size_t, struct rfl_pkt *);
size_t rfl_format(const struct rfl_pkt *, char *, size_t, time_t);
size_t rfl_stamp(char *, size_t, long long, long);
void rfl_counters_parse(const char *, const char *);
unsigned long long rfl_suppressed(int);
uint32_t rfl_seq_gap(uint32_t *, int *, uint32_t);
void rfl_conf_default(struct rfl_conf *);
void rfl_conf_parse(struct rfl_conf *, const char *);
static size_t slurp(const char *p, unsigned char *b, size_t cap) { FILE *f = fopen(p, "rb"); size_t n; if (!f) return 0; n = fread(b, 1, cap, f); fclose(f); return n; }
int main(int argc, char **argv)
{
	static unsigned char b[65536];
	if (!strcmp(argv[1], "cfg")) {
		size_t n = rfl_cfg_msg(b, sizeof(b), 40, 1, 1, 128, 7), i;
		for (i = 0; i < n; i++) printf("%02x", b[i]);
		printf("\n");
	} else if (!strcmp(argv[1], "pkt")) {
		struct rfl_pkt pk; char line[1024];
		size_t n = slurp(argv[2], b, sizeof(b));
		if (rfl_parse(b, n, &pk) != 0) { printf("REFUSED\n"); return 0; }
		rfl_format(&pk, line, sizeof(line), time(NULL));
		printf("%s\n", line);
	} else if (!strcmp(argv[1], "ctr")) {
		int i;
		for (i = 2; i < argc; i++) { size_t n = slurp(argv[i], b, sizeof(b) - 1); b[n] = 0; rfl_counters_parse("v4", (char *)b); }
		printf("%llu %llu %llu %llu\n", rfl_suppressed(0), rfl_suppressed(40), rfl_suppressed(41), rfl_suppressed(42));
	} else if (!strcmp(argv[1], "seq")) {
		uint32_t next = 0; int seen = 0, i;
		for (i = 2; i < argc; i++) printf("%u ", rfl_seq_gap(&next, &seen, (uint32_t)strtoul(argv[i], NULL, 0)));
		printf("\n");
	} else if (!strcmp(argv[1], "conf")) {
		struct rfl_conf c; size_t n = slurp(argv[2], b, sizeof(b) - 1); int i;
		b[n] = 0; rfl_conf_default(&c); rfl_conf_parse(&c, (char *)b);
		printf("{\"groups\":[");
		for (i = 0; i < c.ngroups; i++) printf("%s%d", i ? "," : "", c.groups[i]);
		printf("],\"ram_kb\":%ld,\"keep_days\":%ld,\"keep_mb\":%ld,\"cpu\":%u,\"copy\":%d,\"fwd\":\"%s\",\"port\":%d,\"host\":\"%s\"}\n",
		       c.ram_kb, c.keep_days, c.keep_mb, c.cpu, c.copy, c.fwd_host, c.fwd_port, c.host);
	} else if (!strcmp(argv[1], "stamp")) {
		char t[64];
		rfl_stamp(t, sizeof(t), atoll(argv[2]), atol(argv[3]));
		printf("%s\n", t);
	}
	return 0;
}
'''

# ---------------------------------------------------------------- netlink message builders (host = little-endian)
def attr(t, data):
    l = 4 + len(data)
    return struct.pack("<HH", l, t) + data + b"\0" * ((4 - l % 4) % 4)

def msg(family, attrs, group=40):
    body = struct.pack("!BBH", family, 0, group) + b"".join(attrs)
    return struct.pack("<IHHII", 16 + len(body), (4 << 8) | 0, 0, 0, 0) + body

def be32(v): return struct.pack("!I", v)
def csum0(b): return b
def ip4(proto, l4, tot=None, ident=7238, flags=0x4000, ttl=64, src="192.0.2.50", dst="198.51.100.7"):
    tot = tot or 20 + len(l4)
    return struct.pack("!BBHHHBBH4s4s", 0x45, 0, tot, ident, flags, ttl, proto, 0,
                       socket.inet_aton(src), socket.inet_aton(dst)) + l4
OPTS = bytes.fromhex("020405b40402080a000000010000000001030307")
SYN = struct.pack("!HHIIBBHHH", 51234, 443, 287454020, 0, 0xa0, 0x02, 64240, 0, 0) + OPTS
HW = bytes.fromhex("02005e10000102005e1000020800")

NFULA_PACKET_HDR, NFULA_MARK, NFULA_INDEV, NFULA_OUTDEV, NFULA_HWHEADER, NFULA_PAYLOAD, NFULA_PREFIX, NFULA_SEQ = 1, 2, 4, 5, 16, 9, 10, 12
HDR = attr(NFULA_PACKET_HDR, struct.pack("!HBB", 0x0800, 1, 0))
lo = socket.if_nametoindex("lo") if hasattr(socket, "if_nametoindex") else 1

td = tempfile.mkdtemp(prefix="rflogd-")
try:
    shutil.copy(os.path.join(SRC, "rflogd", "rflogd.c"), td)
    shutil.copy(os.path.join(SRC, "shared", "reaper_fwlog.h"), td)
    with open(os.path.join(td, "drv.c"), "w") as fh: fh.write(DRIVER)
    exe = os.path.join(td, "drv")
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wno-unused-parameter", "-Werror", "-DRFLOGD_HOST",
                        '-DRFL_DIR="%s"' % td, "-I", td, "-o", exe, os.path.join(td, "rflogd.c"), os.path.join(td, "drv.c")],
                       capture_output=True, text=True)
    check("host: rflogd.c (test build) compiles with -Wall -Wextra -Werror", r.returncode == 0, r.stderr)
    if r.returncode:
        raise SystemExit
    def drv(*a, env=None):
        return subprocess.run([exe] + list(a), capture_output=True, text=True, env=env).stdout.strip()
    def pkt(m):
        p = os.path.join(td, "m.bin"); open(p, "wb").write(m); return drv("pkt", p)

    # ---- the CONFIG message
    h = bytes.fromhex(drv("cfg"))
    ln, typ, flags, seq, pid = struct.unpack("<IHHII", h[:16])
    fam, ver, res = struct.unpack("!BBH", h[16:20])
    attrs, at = [], 20
    while at + 4 <= len(h):
        al, at_t = struct.unpack("<HH", h[at:at + 4]); attrs.append((at_t, h[at + 4:at + al])); at += (al + 3) & ~3
    check("CONFIG: one message, type ULOG|CONFIG, REQUEST|ACK, AF_UNSPEC, group 40",
          ln == len(h) and typ == 0x0401 and flags == 0x0005 and fam == 0 and ver == 0 and res == 40, (ln, typ, flags, fam, res))
    want = [(1, b"\x01"), (2, struct.pack("!IBB", 128, 2, 0)[:len(attrs[1][1]) if len(attrs) > 1 else 6]),
            (3, be32(65536)), (4, be32(100)), (5, be32(100)), (6, struct.pack("!H", 1))]
    check("CONFIG: BIND, copy PACKET 128 bytes, nlbufsiz 64 KB, timeout 1 s, qthresh 100, flags SEQ - in that order",
          [a[0] for a in attrs] == [1, 2, 3, 4, 5, 6] and attrs[0][1] == b"\x01" and attrs[1][1][:5] == struct.pack("!IB", 128, 2)
          and attrs[2][1] == be32(65536) and attrs[3][1] == be32(100) and attrs[4][1] == be32(100) and attrs[5][1] == struct.pack("!H", 1),
          attrs)
    check("CONFIG: never PF_BIND (3) or PF_UNBIND (4)", not any(a[0] == 1 and a[1][:1] in (b"\x03", b"\x04") for a in attrs))

    # ---- lines
    base = [HDR, attr(NFULA_INDEV, be32(lo)), attr(NFULA_HWHEADER, HW), attr(NFULA_SEQ, be32(1))]
    MAC = "MAC=02:00:5e:10:00:01:02:00:5e:10:00:02:08:00"
    out = pkt(msg(2, base + [attr(NFULA_PREFIX, b"ACCEPT \0"), attr(NFULA_PAYLOAD, ip4(6, SYN))]))
    check("IPv4 TCP SYN, stock prefix: xt_LOG text with SEQ / ACK and the TCP options",
          out == "ACCEPT IN=lo OUT= " + MAC + " SRC=192.0.2.50 DST=198.51.100.7 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=7238 DF "
                 "PROTO=TCP SPT=51234 DPT=443 SEQ=287454020 ACK=0 WINDOW=64240 RES=0x00 SYN URGP=0 "
                 "OPT (020405B40402080A000000010000000001030307)", out)
    out = pkt(msg(2, base + [attr(NFULA_PREFIX, b"REAPER-WARDEN \0"), attr(NFULA_PAYLOAD, ip4(6, SYN))], 41))
    check("IPv4 TCP SYN, Warden prefix: no SEQ / OPT (its LOG rules never asked for them)",
          out == "REAPER-WARDEN IN=lo OUT= " + MAC + " SRC=192.0.2.50 DST=198.51.100.7 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=7238 DF "
                 "PROTO=TCP SPT=51234 DPT=443 WINDOW=64240 RES=0x00 SYN URGP=0", out)
    icmp = struct.pack("!BBHHH", 8, 0, 0, 4660, 1)
    out = pkt(msg(2, base + [attr(NFULA_PREFIX, b"DROP \0"), attr(NFULA_MARK, be32(0x10)), attr(NFULA_PAYLOAD, ip4(1, icmp, flags=0))]))
    check("IPv4 ICMP echo with a mark: TYPE/CODE/ID/SEQ, MARK at the end",
          out.endswith("TTL=64 ID=7238 PROTO=ICMP TYPE=8 CODE=0 ID=4660 SEQ=1 MARK=0x10") and " DF " not in out, out)
    v6 = struct.pack("!IHBB16s16s", (6 << 28) | (0 << 20) | 0x12345, 30, 17, 64,
                     socket.inet_pton(socket.AF_INET6, "2001:db8::5"), socket.inet_pton(socket.AF_INET6, "2001:db8:1::53"))
    out = pkt(msg(10, [HDR, attr(NFULA_OUTDEV, be32(lo)), attr(NFULA_PREFIX, b"DROP \0"),
                       attr(NFULA_PAYLOAD, v6 + struct.pack("!HHHH", 53000, 53, 30, 0))]))
    check("IPv6 UDP leaving the router: no MAC, xt_LOG's IPv6 header fields",
          out == "DROP IN= OUT=lo SRC=2001:db8::5 DST=2001:db8:1::53 LEN=70 TC=0 HOPLIMIT=64 FLOWLBL=74565 PROTO=UDP SPT=53000 DPT=53 LEN=30", out)
    v6i = struct.pack("!IHBB16s16s", 6 << 28, 8, 58, 255, socket.inet_pton(socket.AF_INET6, "2001:db8::5"),
                      socket.inet_pton(socket.AF_INET6, "2001:db8::1"))
    out = pkt(msg(10, [HDR, attr(NFULA_PREFIX, b"REAPER-WARDEN-SELF \0"), attr(NFULA_PAYLOAD, v6i + struct.pack("!BBHHH", 128, 0, 0, 7, 9))], 41))
    check("ICMPv6 echo request", out.endswith("PROTO=ICMPv6 TYPE=128 CODE=0 ID=7 SEQ=9"), out)
    out = pkt(msg(2, base + [attr(NFULA_PREFIX, b"DROP \0"), attr(NFULA_PAYLOAD, ip4(6, SYN[:10], tot=60))]))
    check("a TCP header cut short: INCOMPLETE with the bytes there were", out.endswith("PROTO=TCP INCOMPLETE [10 bytes]"), out)
    bad = msg(2, base + [attr(NFULA_PREFIX, b"DROP \0")])
    bad = bad + struct.pack("<HH", 4000, NFULA_PAYLOAD) + b"\0" * 8
    bad = struct.pack("<I", len(bad)) + bad[4:]
    check("an attribute longer than the message is refused, nothing read past it", pkt(bad) == "REFUSED", pkt(bad))
    check("a message without a payload is refused", pkt(msg(2, base + [attr(NFULA_PREFIX, b"DROP \0")])) == "REFUSED")
    out = pkt(msg(2, base + [attr(NFULA_PREFIX, b"BAD\x07\x1b[31m \0"), attr(NFULA_PAYLOAD, ip4(6, SYN))]))
    check("control bytes in a prefix become '?' (no terminal escapes in the log)", out.startswith("BAD??[31m IN=") and "\x1b" not in out, repr(out))

    # ---- sequence gaps
    check("lost lines: gaps counted, a backwards jump restarts, the 32-bit wrap is one line",
          drv("seq", "5", "6", "9", "3", "4", "0xffffffff", "1") == "0 0 2 0 0 0 1", drv("seq", "5", "6", "9", "3", "4", "0xffffffff", "1"))

    # ---- suppressed lines
    d1 = ("*filter\n[100:6000] -A logaccept -m state --state NEW -m limit --limit 10000/s --limit-burst 20000 -j NFLOG --nflog-group 40 --nflog-prefix \"ACCEPT \"\n"
          "[130:7800] -A logaccept -m state --state NEW\n[500:30000] -A logaccept -j ACCEPT\n"
          "[5:300] -A RW_DROP -m limit --limit 10000/s --limit-burst 20000 -j NFLOG --nflog-group 41 --nflog-prefix \"REAPER-WARDEN \"\n"
          "[9:540] -A RW_DROP -j DROP\n[7:420] -A logdrop_dns -j NFLOG --nflog-group 42 --nflog-prefix \"DROP_DNS \"\n"
          "[7:420] -A logdrop_dns -j DROP\n[0:0] -A FORWARD -j logaccept\n[3:180] -A RW_SELF -j RW_SDROP\nCOMMIT\n")
    d2 = ("*filter\n[10:600] -A logaccept -m state --state NEW -m limit --limit 10/s --limit-burst 50 -j LOG --log-prefix \"ACCEPT \" --log-level 5\n"
          "[12:720] -A logaccept -m state --state NEW\n[40:2400] -A logaccept -j ACCEPT\n"
          "[1:60] -A RW_DROP -j NFLOG --nflog-group 41 --nflog-prefix \"REAPER-WARDEN \"\n[2:120] -A RW_DROP -j DROP\nCOMMIT\n")
    p1, p2 = os.path.join(td, "c1"), os.path.join(td, "c2")
    open(p1, "w").write(d1); open(p2, "w").write(d2)
    check("suppressed: log rule vs the rule after it, per group (30 stock, 4 Warden, 0 blob)", drv("ctr", p1) == "34 30 4 0", drv("ctr", p1))
    check("suppressed: a rule reload (counters restart) keeps the earlier total (30+2, 4+1)", drv("ctr", p1, p2) == "37 32 5 0", drv("ctr", p1, p2))

    # ---- fwlog.conf
    c = os.path.join(td, "conf")
    open(c, "w").write("groups=40,41\nram_kb=4096\nkeep_days=0\nkeep_mb=100\ncpu=4\ncopy=9999\nfwd=[2001:db8::9]:5514\nhost=RT-BE96U\n")
    j = json.loads(drv("conf", c))
    check("conf: groups / sizes taken, out-of-range values ignored, an IPv6 target in brackets",
          j == {"groups": [40, 41], "ram_kb": 4096, "keep_days": 30, "keep_mb": 100, "cpu": 4, "copy": 128,
                "fwd": "2001:db8::9", "port": 5514, "host": "RT-BE96U"}, j)
    open(c, "w").write("fwd=192.0.2.9:514\n")
    check("conf: an IPv4 target", json.loads(drv("conf", c))["fwd"] == "192.0.2.9")
    open(c, "w").write("fwd=192.0.2.9;reboot:514\nhost=a b\n")
    j = json.loads(drv("conf", c))
    check("conf: a target or host name with other characters is refused (no forward, default host)",
          j["fwd"] == "" and j["host"] == "router", j)

    # ---- timestamp
    t = 1794200000
    u = drv("stamp", str(t), "123456", env=dict(os.environ, TZ="UTC0"))
    exp = datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%S") + ".123+00:00"
    check("timestamp: ISO 8601 with milliseconds and the offset", u == exp, (u, exp))
    e = drv("stamp", str(t), "5000", env=dict(os.environ, TZ="EST5"))
    check("timestamp: a western offset", e.endswith(".005-05:00"), e)
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
