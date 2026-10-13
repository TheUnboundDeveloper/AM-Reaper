#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lldpd's VLAN tag stripping must move s-16 bytes, not s-12 (CVE-2026-46433).

WHY THIS EXISTS. lldpd_decode() strips an 802.1Q tag from a received frame by moving the bytes after
the tag four places left. The vendored lldpd (0.9.8, and the 1.0.11 tree other models select) passed
`s - 2*ETHER_ADDR_LEN` as the count: that is the length from offset 12 to the end of the frame, but the
move starts at offset 16, so it reads four bytes past the end. lldpd_recv() allocates and reads
exactly h_mtu bytes, so a VLAN-tagged frame of MTU size reads four bytes past a heap block - a crash
when the block ends a mapping, four bytes of heap in the decoded TLV tail otherwise. Any host on a
port lldpd binds can send that frame; on this firmware lldpd is the AiMesh wired-topology source.
Upstream fixed it in lldpd 1.0.22; Reaper carries the one-line fix in every lldpd tree it ships
(2026-10-13 code review, S1).

WHAT IT DOES. For every lldpd-*/src/daemon/lldpd.c under the router source, finds the VLAN
decapsulation block and pins the corrected count; a negative self-test shows the old form fails.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1] or
REAPER_ROUTER_SRC).
"""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
trees = sorted(glob.glob(os.path.join(src_root, "lldpd-*", "src", "daemon", "lldpd.c"))) if src_root else []
if not trees:
    skip("no lldpd tree under the router source (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

BLOCK = re.compile(r"if \(eheader\.ether_type == htons\(ETHERTYPE_VLAN\)\) \{(.*?)\n\t\}", re.S)
GOOD = "memmove(frame + 2*ETHER_ADDR_LEN, frame + 2*ETHER_ADDR_LEN + 4, s - 2*ETHER_ADDR_LEN - 4);"
BAD = "memmove(frame + 2*ETHER_ADDR_LEN, frame + 2*ETHER_ADDR_LEN + 4, s - 2*ETHER_ADDR_LEN);"

for path in trees:
    tree = path.split(os.sep)[-4]
    src = open(path, encoding="utf-8", errors="replace").read()
    m = BLOCK.search(src)
    check("%s: the VLAN decapsulation block is found" % tree, m is not None)
    blk = m.group(1) if m else ""
    check("%s: the move counts the four tag bytes out (s - 12 - 4)" % tree, GOOD in blk, blk.strip()[-160:])
    check("%s: the old over-reading count is gone" % tree, BAD not in blk)
    check("%s: s is reduced by the tag after the move" % tree, "s -= 4;" in blk)
    check("%s: the receive buffer is still exactly h_mtu (the size that makes the over-read reachable)" % tree,
          "malloc(hardware->h_mtu)" in src and "hardware->h_mtu)) == -1" in src)

# negative self-test: the shipped-before form must be caught
check("self-test: the pre-fix count fails the pin", GOOD not in BAD and (BAD in BAD))

if fails:
    print("\n%d FAIL:" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed: every lldpd tree strips a VLAN tag without reading past the frame")
