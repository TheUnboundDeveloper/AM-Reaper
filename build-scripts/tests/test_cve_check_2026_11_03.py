#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The four fixes taken from the 2026-11-03 CVE check (CVEs published 2026-08-05..2026-11-03), carried in v3.7.1.

WHY THIS EXISTS. The check (private record) ranked these four first; each is a few lines, three of them backports
that 4.19 / BusyBox upstream will never ship for us:
- CVE-2026-88833, BusyBox udhcpc (the WAN DHCP client, root, on by default): udhcp_recv_raw_packet() trusted the IP
  total length; one under the IP + UDP headers plus the fixed DHCP part wrapped `bytes` and the final memcpy ran with
  a negative size. A minimum-length test after the length is read.
- CVE-2026-99059, WireGuard (upstream d0305f8d9002): consume_response re-checked only the handshake state after an
  intermediate initiation; it now also compares the ephemeral key (crypto_memneq).
- CVE-2026-98276, socket timestamp (upstream 9ed55f3dbef4): SOCK_TIMESTAMP was set without the socket lock
  (sock_set_flag is not atomic). 4.19 has the helper in sock.c twice AND in compat.c twice - compat is the path the
  32-bit userspace takes on this arm64 kernel, so all four are locked. Every built caller holds no socket lock.
- CVE-2026-19386, 102.8 line only: the closed config-upload handler of the 102.8 blobs is the unfixed one; nothing on
  this firmware posts upload_config_sync.cgi, so its route is compiled out there (the 102.10 blobs carry ASUS's fix).

WHAT IT DOES. Pins each change in the source the build compiles. Exit 0 pass, 1 fail, 77 skipped.
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "busybox", "networking", "udhcp", "dhcpc.c")):
    print("SKIP: no router source tree"); sys.exit(77)
K = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "kernel", "linux-4.19"))
VC = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt", "version.conf"))
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
rd = lambda p: open(p, encoding="utf-8", errors="replace").read()

d = rd(os.path.join(SRC, "busybox", "networking", "udhcp", "dhcpc.c"))
f = d[d.find("static NOINLINE int udhcp_recv_raw_packet("):]
f = f[:f.find("\n}\n")]
i_len = f.find("bytes = ntohs(packet.ip.tot_len);")
i_min = f.find("if (bytes < (int)(sizeof(packet.ip) + sizeof(packet.udp) + offsetof(struct dhcp_packet, options))) {")
i_cpy = f.find("bytes -= sizeof(packet.ip) + sizeof(packet.udp);")
check("udhcpc: a minimum-length test right after the IP total length is read, before the subtraction and memcpy",
      0 <= i_len < i_min < i_cpy, (i_len, i_min, i_cpy))
check("udhcpc: the short packet is dropped (return -2)", re.search(r"packet is too short, ignoring\"\);\s*return -2;", f) is not None)

if os.path.isdir(K):
    n = rd(os.path.join(K, "net", "wireguard", "noise.c"))
    cr = n[n.find("wg_noise_handshake_consume_response("):]
    cr = cr[:cr.find("\n}\n")]
    check("WireGuard: consume_response re-checks state AND the ephemeral key under the write lock",
          re.search(r"if \(handshake->state != state \|\|\s*crypto_memneq\(handshake->ephemeral_private, ephemeral_private,\s*NOISE_PUBLIC_KEY_LEN\)\) \{", cr) is not None)
    check("WireGuard: noise.c includes crypto/algapi.h (crypto_memneq)", "#include <crypto/algapi.h>" in n)
    LOCK = r"if \(!sock_flag\(sk, SOCK_TIMESTAMP\)\) \{\s*lock_sock\(sk\);\s*sock_enable_timestamp\(sk, SOCK_TIMESTAMP\);\s*release_sock\(sk\);\s*\}"
    for fn, path in (("sock_get_timestamp", "net/core/sock.c"), ("sock_get_timestampns", "net/core/sock.c"),
                     ("compat_sock_get_timestamp", "net/compat.c"), ("compat_sock_get_timestampns", "net/compat.c")):
        s = rd(os.path.join(K, path))
        b = s[s.find("int %s(struct sock *sk" % fn):]
        b = b[:b.find("\n}\n")]
        check("socket timestamp: %s sets SOCK_TIMESTAMP under the socket lock" % fn,
              re.search(LOCK, b) is not None and not re.search(r"\n\tsock_enable_timestamp\(sk, SOCK_TIMESTAMP\);", b), path)
else:
    print("skip the kernel checks (no kernel tree next to the router source)")

line = "102.8" if os.path.isfile(VC) and "SERIALNO=102.8\n" in rd(VC) else "102.10"
w = rd(os.path.join(SRC, "httpd", "web.c"))
row = re.search(r'(?m)^(#if 0[^\n]*\n(?:\t \*[^\n]*\n)*)?\t\{ "upload_config_sync\.cgi\*"', w)
if line == "102.8":
    check("102.8: the upload_config_sync.cgi route is compiled out (#if 0 around the row)",
          row is not None and row.group(1) is not None and "CVE-2026-19386" in row.group(1))
else:
    check("102.10: the upload_config_sync.cgi route stays (the 40585 blobs carry ASUS's fix)", row is not None)

if fails:
    print("\n".join("FAILED: " + f for f in fails)); sys.exit(1)
print("all checks passed (%s line)" % line)
