#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SSH over IPv6 from the internet: the per-/64 rate limiter (rc/firewall.c, 2026-10-19).

WHY THIS EXISTS. The stock brute-force guard for SSH and Telnet is IPv4-only: its chains are
written for the IPv4 table, and the IPv6 rule for the WAN SSH port was a plain accept - written
twice, in filter_setting() and filter_setting2(). A guess-the-password run over IPv6 met nothing.
The guard is two `-m recent` rules ahead of that accept (xt_recent is built into this kernel,
so no module order matters): the sixth NEW connection from one /64 inside 60 s is dropped, and a
continuing flood keeps the entry fresh. WAN only - the rule exists only where the WAN accept does.

WHAT IT DOES. Pins that one helper emits both rules, that BOTH sites call it directly before
the accept under the same conditions, that the netmask is a /64, that the match is one the
kernel provides, and - when ip6tables-restore and root are available - that a sample table
holding the two lines loads under `--test`. Exit 0 pass, 1 fail, 77 skipped (no tree).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

passed = 0
def ok(cond, what):
    global passed
    if not cond: die(what)
    passed += 1
    print("ok   " + what)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "firewall.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
with open(os.path.join(SRC, "rc", "firewall.c"), encoding="utf-8", errors="replace") as f:
    fw = f.read()

i = fw.find("static void reaper_ssh6_guard(FILE *fp6, int port, const char *logdrop)")
ok(i >= 0, "firewall.c: the helper exists")
helper = fw[i:fw.find("\n}\n", i)]
DROP = '"-A INPUT -p tcp -m tcp --dport %d -m conntrack --ctstate NEW -m recent --name rw_ssh6 --mask ffff:ffff:ffff:ffff:: --update --seconds 60 --hitcount 5 -j %s\\n"'
SET = '"-A INPUT -p tcp -m tcp --dport %d -m conntrack --ctstate NEW -m recent --name rw_ssh6 --mask ffff:ffff:ffff:ffff:: --set\\n"'
ok(DROP in helper and SET in helper and helper.index(DROP) < helper.index(SET), "helper: the drop (update + hitcount 5 in 60 s) precedes the set, both on NEW only")
ok("--mask ffff:ffff:ffff:ffff::" in helper, "helper: the list is keyed per /64")
ok(i < fw.find("\nfilter_setting(int wan_unit"), "helper: defined before filter_setting()")

CALL = ('if (ipv6_enabled() && nvram_match("ipv6_fw_enable", "1")) {\n'
        '\t\t\t\treaper_ssh6_guard(fp_ipv6, nvram_get_int("sshd_port") ? : 22, logdrop);')
ACCEPT = 'fprintf(fp_ipv6, "-A INPUT -p tcp -m tcp --dport %d -j %s\\n",\n\t\t\t\t\tnvram_get_int("sshd_port") ? : 22, logaccept);'
ok(fw.count(CALL) == 2, "both WAN-SSH sites (filter_setting, filter_setting2) call the helper under the v6 accept's own condition (%d)" % fw.count(CALL))
ok(fw.count(ACCEPT) == 2, "the v6 accept itself is still written at both sites")
for site in (m.start() for m in re.finditer(re.escape(CALL), fw)):
    ok(0 < fw.find(ACCEPT, site) - site < 400, "the guard sits directly ahead of the accept at offset %d" % site)
ok('if (nvram_get_int("sshd_enable") == 1) {' in fw[fw.find(CALL) - 400:fw.find(CALL)], "the guard exists only where SSH is open to the WAN (sshd_enable == 1)")

# the kernel must provide the matches (nf-parity's own rule, pinned here for these two)
cfg = None
for cand in (os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "kernel", "linux-4.19", ".config"),):
    if os.path.isfile(cand): cfg = open(cand, errors="replace").read()
if cfg is not None:
    ok("CONFIG_NETFILTER_XT_MATCH_RECENT=y" in cfg, "kernel: xt_recent is built in (no modprobe before the restore)")
    ok(re.search(r"CONFIG_NETFILTER_XT_MATCH_CONNTRACK=[ym]", cfg) is not None, "kernel: the conntrack match is available")
else:
    print("skip kernel .config not found beside the tree")

# the lines load as a filter table when the host can test them (root + ip6tables-restore)
r6 = shutil.which("ip6tables-restore")
if r6 and os.geteuid() == 0:
    d = tempfile.mkdtemp(prefix="ssh6_")
    try:
        p = os.path.join(d, "t.rules")
        open(p, "w").write("*filter\n:INPUT ACCEPT [0:0]\n:logdrop - [0:0]\n"
                           + DROP.strip('"').replace("\\n", "\n").replace("%d", "22").replace("%s", "logdrop")
                           + SET.strip('"').replace("\\n", "\n").replace("%d", "22")
                           + "-A INPUT -p tcp -m tcp --dport 22 -j ACCEPT\nCOMMIT\n")
        r = subprocess.run([r6, "--test", p], capture_output=True, text=True)
        ok(r.returncode == 0, "ip6tables-restore --test accepts the two rules (%s)" % r.stderr.strip()[:200])
    finally:
        shutil.rmtree(d, ignore_errors=True)
else:
    print("skip ip6tables-restore --test (needs root and ip6tables)")

print("PASS: %d checks" % passed)
