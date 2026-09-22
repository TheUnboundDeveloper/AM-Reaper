#!/usr/bin/env python3
"""tier 3 - the walker's PATH and DECIDING RULE against a REAL kernel walk.

WHY THIS EXISTS. Tiers 1 and 2 (test_fwsim.py) check the walker's VERDICTS:
given a table and a witness, is the answer green/red/depends/na. Nothing checked
the other half of its output - the chain it says the packet took and the rule it
says decided the matter. That is the walker's most useful column and it was its
least verified, which matters most for repair-on-red: repair acts on the
walker's reading, so a wrong deciding rule would drive an automated fix.

HOW. Replay a ruleset into a throwaway network namespace, send a real packet
through it, and ask the kernel itself which rule decided. Then compare.

WHAT THIS IS NOT. This validates the walker's LOGIC, not the platform. The host
kernel is not the router's 4.19, and a ruleset emitted by iptables 1.4.x does not
always restore under the host's newer iptables. A witness whose rules will not
load is reported `unvalidatable` - never as a pass and never as a failure.

ENVIRONMENT NOTES, both learned the hard way on 2026-09-15:
  * The ROUTER KERNEL CANNOT DO THIS AT ALL. `-j TRACE` is not compiled in:
    release/src-rt-5.04behnd.4916/kernel/linux-4.19/.config carries
    `# CONFIG_NETFILTER_XT_TARGET_TRACE is not set`. An earlier plan to arm TRACE
    on a lab router was impossible, not merely awkward.
  * Netfilter LOG/TRACE output from a NON-INITIAL network namespace never reaches
    the kernel ring buffer on the WSL2 kernel - proven with rule counters showing
    the packet traversed while /dev/kmsg stayed empty. So this tier does NOT use
    the classic `-j TRACE` -> dmesg route. It restores through the nft backend and
    reads `nft monitor trace`, whose events are delivered over netlink and so
    cross the namespace boundary.

Needs root, ip, nft, iptables-nft-restore and ipset. Exits 77 (skip) otherwise,
which is the normal result in the ordinary `reaper`-user test run: this tier is
meant to be run deliberately, as root.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

NS = "fwsimt"          # the router under test
NSC = "fwsimtc"        # the client, so packets actually arrive on an interface

failures = []
unvalidatable = []


def skip(msg):
    print("SKIP: " + msg)
    sys.exit(77)


def die(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        print("FAIL " + name + (("\n     " + str(detail)) if detail else ""))
        failures.append(name)


def sh(cmd, check_rc=True, inp=None):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, input=inp)
    if check_rc and p.returncode != 0:
        raise RuntimeError("%s -> rc=%d %s%s" % (cmd, p.returncode, p.stdout[-400:], p.stderr[-400:]))
    return p


src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
walker = os.path.join(src_root, "reaper_fwsim", "reaper_fwsim.c") if src_root else ""
if not walker or not os.path.exists(walker):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
if os.geteuid() != 0:
    skip("needs root to create a network namespace - run this tier deliberately, as root")
for tool in ("ip", "nft", "iptables-nft-restore", "ipset"):
    if not shutil.which(tool):
        skip("missing %s" % tool)

td = tempfile.mkdtemp(prefix="fwsimtrace.")
exe = os.path.join(td, "reaper_fwsim")
CC = os.environ.get("CC", "cc")
p = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wno-unused-parameter", "-Wno-sign-compare",
                    "-DFWSIM_HOST", "-o", exe, walker], capture_output=True, text=True)
if p.returncode != 0:
    die("could not build the walker: " + p.stderr[-800:])

# ---------------------------------------------------------------- the fixture
# Deliberately its own, not tier 1's: the two tiers answer different questions
# (verdict vs path) and sharing a fixture would tie one to the other's shape.
# Kept small so every rule here is one a witness below actually reaches.
SAVE4 = """*raw
:PREROUTING ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
COMMIT
*nat
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
:POSTROUTING ACCEPT [0:0]
:VSERVER - [0:0]
-A PREROUTING -d 203.0.113.5/32 -j VSERVER
-A VSERVER -p tcp -m tcp --dport 443 -j DNAT --to-destination 192.168.50.10:8443
COMMIT
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
:INPUT_ICMP - [0:0]
:SECURITY - [0:0]
:RW_DROP - [0:0]
:WARDEN - [0:0]
-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT
-A INPUT ! -i lo -p tcp -m tcp --dport 5152 -j DROP
-A INPUT -i br0 -m state --state NEW -j ACCEPT
-A INPUT -j DROP
-A FORWARD -j WARDEN
-A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
-A FORWARD -i eth0 -j SECURITY
-A FORWARD -m conntrack --ctstate DNAT -j ACCEPT
-A FORWARD -i br0 -o eth0 -p tcp -m multiport --dports 25,465 -j REJECT --reject-with icmp-port-unreachable
-A FORWARD -i br0 -o eth0 -j ACCEPT
-A SECURITY -j RETURN
-A WARDEN -m set --match-set rw_allow src -j RETURN
-A WARDEN -m set --match-set rw_ban src -j RW_DROP
-A RW_DROP -j DROP
COMMIT
"""

ADDR = ("1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever\n"
        "2: eth0    inet 203.0.113.5/24 brd 203.0.113.255 scope global eth0\\       valid_lft forever\n"
        "3: br0    inet 192.168.50.1/24 brd 192.168.50.255 scope global br0\\       valid_lft forever\n")
NV = "sw_mode=1\nlan_ifname=br0\nwan0_ifname=eth0\nwan0_proto=dhcp\nlan_ipaddr=192.168.50.1\n"
SETS = "rw_ban 198.51.100.66\nrw_allow 198.51.100.77\n"

CLIENT = "192.168.50.123"

# id | in | src | dst | proto | port | ct | expect   -- the walker's witness form
CASES = [
    ("T-fwd-accept", "br0", CLIENT, "203.0.113.9", "tcp", "443", "NEW", "ACCEPT",
     "a plain LAN to WAN forward"),
    ("T-fwd-reject", "br0", CLIENT, "203.0.113.9", "tcp", "25", "NEW", "DROP",
     "the multiport REJECT, three rules above the ACCEPT - a different index in the same chain"),
    ("T-in-accept", "br0", CLIENT, "192.168.50.1", "tcp", "8443", "NEW", "ACCEPT",
     "INPUT rather than FORWARD"),
    ("T-in-drop", "br0", CLIENT, "192.168.50.1", "tcp", "5152", "NEW", "DROP",
     "the Advisor-port DROP, which sits ABOVE the br0 accept"),
]


def w(name, text):
    p = os.path.join(td, name)
    with open(p, "w") as f:
        f.write(text)
    return p


def walker_says(case):
    """the walker's own reading: (table/chain, index, rule text)"""
    cid, inif, src, dst, proto, port, ct, expect, _ = case
    wit = "%s|trace case|4|%s|%s|%s|%s|%s|%s|%s|||\n" % (cid, inif, src, dst, proto, port, ct, expect)
    jf = os.path.join(td, cid + ".json")
    args = [exe, "--save4", w(cid + ".v4", SAVE4), "--addr", w(cid + ".addr", ADDR),
            "--members", w(cid + ".mem", SETS), "--nv", w(cid + ".nv", NV),
            "--witness", w(cid + ".wit", wit), "--wan", "eth0", "--lan", "br0", "--json", jf]
    p = subprocess.run(args, capture_output=True, text=True)
    if not os.path.exists(jf):
        die("no JSON from the walker for %s: %s" % (cid, p.stderr[-400:]))
    with open(jf) as f:
        j = json.load(f)
    for x in j["witnesses"]:
        if x["id"] == cid:
            return x
    die("walker emitted no row for " + cid)


def ns_up():
    ns_down()
    sh("ip netns add %s" % NS)
    sh("ip netns add %s" % NSC)
    sh("ip link add vlanA netns %s type veth peer name vcli netns %s" % (NS, NSC))
    sh("ip netns exec %s ip link set vlanA name br0" % NS)
    sh("ip netns exec %s ip addr add 192.168.50.1/24 dev br0" % NS)
    sh("ip netns exec %s ip link set br0 up" % NS)
    sh("ip netns exec %s ip link set lo up" % NS)
    sh("ip netns exec %s sysctl -qw net.ipv4.ip_forward=1" % NS)
    sh("ip netns exec %s ip link add eth0 type dummy" % NS)
    sh("ip netns exec %s ip addr add 203.0.113.5/24 dev eth0" % NS)
    sh("ip netns exec %s ip link set eth0 up" % NS)
    # a route for the WAN-side destination so FORWARD is actually reached
    sh("ip netns exec %s ip route add 203.0.113.0/24 dev eth0" % NS, check_rc=False)
    sh("ip netns exec %s ip addr add %s/24 dev vcli" % (NSC, CLIENT))
    sh("ip netns exec %s ip link set vcli up" % NSC)
    sh("ip netns exec %s ip link set lo up" % NSC)
    sh("ip netns exec %s ip route add default via 192.168.50.1" % NSC)
    # the sets the fixture's WARDEN chain matches on; without them the restore
    # fails outright and every case would read as unvalidatable
    for s in ("rw_ban", "rw_allow"):
        sh("ip netns exec %s ipset create %s hash:net" % (NS, s), check_rc=False)
    sh("ip netns exec %s ipset add rw_ban 198.51.100.66" % NS, check_rc=False)
    sh("ip netns exec %s ipset add rw_allow 198.51.100.77" % NS, check_rc=False)


def ns_down():
    for n in (NS, NSC):
        subprocess.run("ip netns del %s" % n, shell=True, capture_output=True)


def norm(rule_text):
    """nft prints the same rule slightly differently in `list` and in `trace`;
    drop the counters and collapse spacing so the two can be matched."""
    t = re.sub(r"counter packets \d+ bytes \d+", "", rule_text)
    t = re.sub(r"#\s*handle \d+", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def rule_index_map():
    """normalized rule text -> (table, chain, 1-based index), as the walker counts."""
    out = {}
    p = sh("ip netns exec %s nft -a list ruleset" % NS)
    table = chain = None
    idx = 0
    for line in p.stdout.splitlines():
        s = line.strip()
        m = re.match(r"table (\w+) (\S+) \{", s)
        if m:
            table = m.group(2)
            continue
        m = re.match(r"chain (\S+) \{", s)
        if m:
            chain = m.group(1)
            idx = 0
            continue
        if s.startswith("type ") or s in ("}", "") or s.startswith("table ") or s.startswith("chain "):
            continue
        if table and chain:
            idx += 1
            k = norm(s)
            # an identical rule twice in one chain cannot be told apart from the
            # trace text alone; record the ambiguity rather than guessing
            out[(table, k)] = None if (table, k) in out else (table, chain, idx)
    return out


def send(case):
    cid, inif, src, dst, proto, port, ct, expect, _ = case
    code = ("import socket\n"
            "s=socket.socket(socket.AF_INET, socket.SOCK_%s)\n"
            "s.settimeout(1)\n"
            "try:\n"
            "    s.%s(('%s', %s))\n"
            "except Exception:\n"
            "    pass\n") % ("STREAM" if proto == "tcp" else "DGRAM",
                             "connect" if proto == "tcp" else "connect",
                             dst, port)
    if proto != "tcp":
        code += "try:\n    s.send(b'x')\nexcept Exception:\n    pass\n"
    subprocess.run("ip netns exec %s timeout 3 python3 -c \"%s\"" % (NSC, code.replace('"', '\\"')),
                   shell=True, capture_output=True)


def kernel_says(case):
    """(table, chain, index, verdict) the KERNEL reports for the deciding rule."""
    cid, inif, src, dst, proto, port, ct, expect, _ = case
    imap = rule_index_map()
    sh("ip netns exec %s iptables-nft -t raw -F PREROUTING" % NS, check_rc=False)
    sh("ip netns exec %s iptables-nft -t raw -I PREROUTING -p %s -s %s -d %s --dport %s -j TRACE"
       % (NS, proto, src, dst, port))
    tf = os.path.join(td, cid + ".trace")
    mon = subprocess.Popen("ip netns exec %s timeout 5 nft monitor trace > %s 2>&1" % (NS, tf), shell=True)
    import time
    time.sleep(1)
    send(case)
    time.sleep(2)
    mon.wait()
    decided = None
    with open(tf) as f:
        for line in f:
            m = re.search(r"trace id \w+ (\w+) (\S+) (\S+) rule (.*?) \(verdict (\w+)\)", line.strip())
            if not m:
                continue
            fam, tbl, chn, rule, verdict = m.groups()
            if verdict in ("accept", "drop", "reject"):
                hit = imap.get((tbl, norm(rule)))
                decided = (tbl, chn, hit[2] if hit else None, verdict, rule)
    return decided


# ------------------------------------------------------------------- the run
print("tier 3: walker path vs real kernel traversal (nft trace in a netns)")
try:
    ns_up()
    restore = sh("ip netns exec %s iptables-nft-restore" % NS, check_rc=False, inp=SAVE4)
    if restore.returncode != 0:
        ns_down()
        skip("the fixture will not restore under this host's iptables: " + restore.stderr[-300:])

    for case in CASES:
        cid = case[0]
        note = case[8]
        w_row = walker_says(case)
        k = kernel_says(case)
        if k is None:
            unvalidatable.append(cid)
            print("----  %s: no trace event - UNVALIDATABLE (not a pass, not a failure)" % cid)
            continue
        ktbl, kchn, kidx, kverdict, krule = k
        # the walker writes its deciding rule as `table/CHAIN#index <text>`
        m = re.match(r"(\w+)/(\S+?)#(\d+)", w_row.get("rule", ""))
        if not m:
            check("%s: the walker names a deciding rule at all" % cid, False, w_row.get("rule"))
            continue
        wtbl, wchn, widx = m.group(1), m.group(2), int(m.group(3))
        check("%s: same table and chain as the kernel (%s)" % (cid, note),
              (wtbl, wchn) == (ktbl, kchn), "walker %s/%s vs kernel %s/%s" % (wtbl, wchn, ktbl, kchn))
        if kidx is None:
            print("----  %s: that rule appears twice in its chain - index not comparable" % cid)
        else:
            check("%s: same rule INDEX as the kernel" % cid, widx == kidx,
                  "walker #%d vs kernel #%d (%s)" % (widx, kidx, krule))
finally:
    ns_down()

if unvalidatable:
    print("unvalidatable: " + ", ".join(unvalidatable))
if failures:
    print("\n%d check(s) FAILED - the walker's deciding rule disagrees with the kernel" % len(failures))
    sys.exit(1)
print("\nall checks passed: the walker's path and deciding rule match what the kernel actually did")
