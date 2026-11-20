#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal: a signed-in device's connection to the pre-sign-in stand-in address is refused at once (2026-11-13).

WHY THIS EXISTS. Before sign-in the portal answers every A lookup with a stand-in address (198.18.0.1) so the
phone's sign-in sheet opens. A phone keeps using that answer for a while after sign-in. Its connections to the
stand-in were forwarded and dropped further on without a word, so each waited out its own timeout: about 30 s
between "Successful!" and a working connection, and 40 to 60 blocked-connection log lines per sign-in. The portal
now stops those packets itself and answers a TCP segment with a reset, so the device looks the name up again.

WHAT IT DOES. Compiles the REAPER-STANDIN block of coovachilli/src/dhcp.c on the host and runs it on real packet
bytes: a first SYN (reset + acknowledgement of the SYN - a bare reset is ignored by a connecting stack), a SYN
carrying data, a segment that acknowledges something (reset with that sequence number), an IP header with options,
and the cases that must send nothing (an incoming reset, UDP, a fragment, a short or over-declared packet). Then
it pins the wiring in dhcp_receive_ip(): signed-in devices only, before the packet is passed on, the reply's
checksums are computed, the packet is not forwarded, and the address is the one the pre-sign-in answer hands out.
Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, struct, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
DHCP = os.path.join(SRC, "coovachilli", "src", "dhcp.c") if SRC else ""
if not DHCP or not os.path.isfile(DHCP):
    skip("no router tree with coovachilli/src/dhcp.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def done():
    print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
    if fails:
        print("\n".join(fails))
    sys.exit(1 if fails else 0)

src = open(DHCP, encoding="utf-8", errors="surrogateescape").read()
m = re.search(r"/\* REAPER-STANDIN-BEGIN.*?\*/(.*?)/\* REAPER-STANDIN-END \*/", src, re.S)
check("dhcp.c carries the REAPER-STANDIN block", m is not None)
if not m:
    done()

MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
%s
static unsigned char hex(char c) { return (unsigned char)(c <= '9' ? c - '0' : c - 'a' + 10); }
int main(int argc, char **argv)
{
	unsigned char in[256], out[64]; size_t n = 0, r, i; const char *h;
	if (argc != 2) return 2;
	for (h = argv[1]; h[0] && h[1] && n < sizeof(in); h += 2) in[n++] = (unsigned char)(hex(h[0]) << 4 | hex(h[1]));
	memset(out, 0xee, sizeof(out));
	r = reaper_tcp_refuse(out, 40, in, n);
	printf("%%u ", (unsigned)r);
	for (i = 0; i < r; i++) printf("%%02x", out[i]);
	printf(" %%02x %%08x\n", out[40], (unsigned)REAPER_STANDIN_ADDR);
	return 0;
}
'''

def ip(proto=6, src="192.0.2.10", dst="198.18.0.1", payload=b"", ihl=5, frag=0, tot=None):
    a = bytes(int(x) for x in src.split(".")); b = bytes(int(x) for x in dst.split("."))
    opts = b"\x01" * ((ihl - 5) * 4)
    total = ihl * 4 + len(payload) if tot is None else tot
    return struct.pack("!BBHHHBBH", 0x40 | ihl, 0, total, 0x1234, frag, 64, proto, 0) + a + b + opts + payload

def tcp(sport=50000, dport=80, seq=1000, ack=0, flags=0x02, data=b"", doff=5):
    return struct.pack("!HHIIBBHHH", sport, dport, seq, ack, doff << 4, flags, 65535, 0, 0) + b"\x01" * ((doff - 5) * 4) + data

tmp = tempfile.mkdtemp()
try:
    c = os.path.join(tmp, "s.c"); exe = os.path.join(tmp, "s")
    open(c, "w").write(MAIN % m.group(1))
    r = subprocess.run([CC, "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
    check("the block compiles with -Wall -Wextra -Werror", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        def run(pkt):
            o = subprocess.run([exe, pkt.hex()], capture_output=True, text=True).stdout.split()
            n = int(o[0]); body = bytes.fromhex(o[1]) if n else b""
            return n, body, o[-2], o[-1]
        def fields(b):
            v = struct.unpack("!BBHHHBBH4s4sHHIIBBHHH", b)
            return dict(ver=v[0], tot=v[2], frag=v[4], ttl=v[5], proto=v[6], ipck=v[7], src=".".join(map(str, v[8])),
                        dst=".".join(map(str, v[9])), sport=v[10], dport=v[11], seq=v[12], ack=v[13], doff=v[14], fl=v[15], win=v[16], tck=v[17])

        n, b, guard, addr = run(ip(payload=tcp(seq=1000)))
        check("the stand-in address is 198.18.0.1", addr == "c6120001", addr)
        check("a first SYN gets a 40-byte reply and nothing is written past it", n == 40 and guard == "ee", (n, guard))
        if n == 40:
            f = fields(b)
            check("the reply comes from the stand-in back to the device, ports swapped",
                  f["src"] == "198.18.0.1" and f["dst"] == "192.0.2.10" and f["sport"] == 80 and f["dport"] == 50000, f)
            check("to a SYN: reset + acknowledgement, sequence 0, acknowledging the SYN (seq + 1)",
                  f["fl"] == 0x14 and f["seq"] == 0 and f["ack"] == 1001, f)
            check("a plain IPv4 / TCP header: version 4, 20 + 20 bytes, do-not-fragment, a hop limit, no window",
                  f["ver"] == 0x45 and f["tot"] == 40 and f["frag"] == 0x4000 and f["ttl"] > 0 and f["proto"] == 6 and f["doff"] == 0x50 and f["win"] == 0, f)
            check("both checksums are left zero for the caller's routine", f["ipck"] == 0 and f["tck"] == 0, f)
        n, b, _, _ = run(ip(payload=tcp(seq=0xfffffff0, flags=0x02, data=b"x" * 20)))
        check("a SYN carrying data: the acknowledgement covers the data too (and wraps correctly)",
              n == 40 and fields(b)["ack"] == (0xfffffff0 + 20 + 1) & 0xffffffff and fields(b)["fl"] == 0x14, n and fields(b))
        n, b, _, _ = run(ip(payload=tcp(seq=7000, ack=424242, flags=0x18, data=b"GET / HTTP/1.1\r\n")))
        check("a segment that acknowledges something: a reset with that sequence number and no acknowledgement",
              n == 40 and fields(b)["fl"] == 0x04 and fields(b)["seq"] == 424242 and fields(b)["ack"] == 0, n and fields(b))
        n, b, _, _ = run(ip(payload=tcp(seq=5, ack=9, flags=0x11)))
        check("a FIN + ACK: the same", n == 40 and fields(b)["fl"] == 0x04 and fields(b)["seq"] == 9, n and fields(b))
        n, b, _, _ = run(ip(ihl=7, payload=tcp(seq=33, dport=5223)))
        check("an IP header with options is read at its real length",
              n == 40 and fields(b)["sport"] == 5223 and fields(b)["ack"] == 34 and fields(b)["src"] == "198.18.0.1", n and fields(b))
        n, b, _, _ = run(ip(payload=tcp(seq=1, doff=8)))
        check("TCP options on the SYN do not count as data", n == 40 and fields(b)["ack"] == 2, n and fields(b))
        check("an incoming reset is never answered", run(ip(payload=tcp(flags=0x04)))[0] == 0 and run(ip(payload=tcp(flags=0x14, ack=5)))[0] == 0)
        check("UDP is not answered", run(ip(proto=17, payload=b"\x00" * 28))[0] == 0)
        check("a fragment is not answered (more-fragments, or an offset)",
              run(ip(frag=0x2000, payload=tcp()))[0] == 0 and run(ip(frag=0x0010, payload=tcp()))[0] == 0)
        check("a do-not-fragment SYN is answered", run(ip(frag=0x4000, payload=tcp()))[0] == 40)
        check("a packet shorter than its headers is not answered", run(ip(payload=tcp())[:36])[0] == 0 and run(b"\x45\x00")[0] == 0)
        check("a total length beyond the bytes received is not answered", run(ip(payload=tcp(), tot=400))[0] == 0)
        check("a TCP header length beyond the packet is not answered", run(ip(payload=tcp(doff=15)[:20]))[0] == 0)
        check("IPv6 bytes are not answered", run(b"\x60" + b"\x00" * 59)[0] == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# wiring in dhcp_receive_ip()
f = re.search(r"\nint dhcp_receive_ip\(struct dhcp_ctx \*ctx, uint8_t \*pack, size_t len\) \{(.*?)\n\}\n", src, re.S)
check("dhcp_receive_ip() found", f is not None)
if f:
    body = f.group(1)
    a = body.find("case DHCP_AUTH_PASS:")
    b = body.find("if (pack_iph->daddr == htonl(REAPER_STANDIN_ADDR)) {")
    c2 = body.find("dhcp_postauthDNAT(conn, pack, len, 0, &do_checksum);")
    nxt = body.find("case DHCP_AUTH_UNAUTH_TOS:")
    check("the test sits in the signed-in branch, before the packet is passed on", 0 <= a < b < c2 < nxt, (a, b, c2, nxt))
    check("only one such test, and a device that has not signed in is untouched (its lookups and redirect are as before)",
          src.count("htonl(REAPER_STANDIN_ADDR)") == 1 and body.find("REAPER_STANDIN_ADDR") > a)
    blk = body[b:c2] if 0 <= b < c2 else ""
    check("the reset is built from the IP header, checksummed and sent back to the device",
          "reaper_tcp_refuse(reaper_rst + reaper_el, 40, (const uint8_t *)pack_iph, len - reaper_el)" in blk
          and "chksum(pkt_iphdr(reaper_rst));" in blk
          and "dhcp_send(this, dhcp_conn_idx(conn), conn->hismac, reaper_rst, reaper_el + 40);" in blk)
    check("the Ethernet header is the device's own, turned round (a VLAN tag is kept)",
          "memcpy(reaper_rst, pack, reaper_el);" in blk and "memcpy(pkt_ethhdr(reaper_rst)->dst, pack_ethh->src, PKT_ETH_ALEN);" in blk
          and "memcpy(pkt_ethhdr(reaper_rst)->src, pack_ethh->dst, PKT_ETH_ALEN);" in blk
          and "uint8_t reaper_rst[sizeof(struct pkt_ethhdr8021q_t) + 40];" in blk)
    check("the packet is never forwarded, whatever its protocol", re.search(r"OTHER_RECEIVED\(conn, pack_iph\);\s*return 0;\s*\}\s*$", blk.rstrip() + "\n", re.S) is not None or
          re.search(r"OTHER_RECEIVED\(conn, pack_iph\);\s*\n\s*return 0;\s*\n\s*\}", blk) is not None)
check("the pre-sign-in answer hands out the same address", "reaper_redir.s_addr = htonl(0xC6120001);" in src and "#define REAPER_STANDIN_ADDR 0xC6120001u" in src)
check("the old note that nothing sticks after sign-in is gone", "so nothing sticks after sign-in" not in src)

done()
