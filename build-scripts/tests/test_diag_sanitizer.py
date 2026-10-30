#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The diag sanitizer redacts what its ledger promises - run, not read.

WHY THIS EXISTS. On 2026-10-12 a report the diag had marked CLEAN carried the owner's
IPv6 tunnel allocation three times: "2001:db8:8cd0::/48" in the Warden and ip6tables
lines passed the IPv6 pass (the compressed-form match demanded a hex digit after the
"::"), dnsmasq's reverse-zone names spelled the same prefix backwards as nibbles (and
the IPv4 pass carved "8.0.7.4" out of their middle), and the lease file's DHCPv6 DUID
kept the router MAC's last four bytes (the six-byte MAC match took the front). The
tripwire counted none of it because it only knew IPv4, MAC and e-mail shapes. v1.3.35
closes all three and adds IPv6 residue to the tripwire. Later the same day the _r5
report printed a client's own DHCP domain raw ("Ignoring domain <employer network> for
DHCP host name ..."): neither a value the sanitizer was given nor a fixed shape. v1.3.36
splits the sanitizer into targeted stages (SAN_STAGES: literals, client-supplied names,
e-mail, MAC, IPv6, IPv4) and adds the client-names stage, which reads the DHCP and
gatekeeper log templates and masks what clients wrote there everywhere it appears.
A regex is the kind of thing that reads right and runs wrong, so this suite EXECUTES
the stage programs and the tripwire cut out of others/reaper_diag - in the script's own
SAN_STAGES order, under busybox awk (the router's), gawk and mawk, whichever the host
has - over the exact lines that leaked, plus the lines that must stay readable.

WHAT IT DOES.
  - addresses: the "::" prefix, a full compressed address, a link-local address with an
    EUI-64 tail, a reverse zone, a DUID and a plain MAC are all tokenized; the same value
    always gets the same token; fe80::/10, fc00::/7, ff02::1, ::1 and ::/0, a private
    reverse zone, a timestamp and RFC1918 addresses are untouched;
  - client names: a DHCP domain, the name beside it, a DHCPACK/DHCPREPLY name (short ones
    too), "not giving name", a gatekeeper "host (...)" - masked at their position and
    everywhere else in the report; generic domains (lan, local) and pool.ntp.org stay
    readable; a value the literal list already holds keeps its [HOST-n] token;
  - the stages run in SAN_STAGES order, ip4 last (it strips the sentinels), a failing
    stage writes no report, and the ledger lines come out in stage order;
  - tripwire: the sanitized body counts 0 0 0 0 0; the raw body counts IPv6, MAC and
    client-name residue;
  - the lease section skips the duid line; the boot-skeleton FINDING no longer claims a
    refused line when there is none; the marker and the script agree on the version
    (test_diag_version covers the page).
Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as
argv[1] or REAPER_ROUTER_SRC - or no awk on the host).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
DIAG = os.path.join(SRC, "others", "reaper_diag")
if not SRC or not os.path.isfile(DIAG):
    skip("no router source tree with others/reaper_diag (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

HERE = os.path.dirname(os.path.abspath(__file__))
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(DIAG, encoding="utf-8", errors="surrogateescape").read()

# ------------------------------------------------------------------ cut the stages out
mst = re.search(r'^SAN_STAGES="([a-z0-9 ]+)"$', src, re.M)
check("the script names its sanitizer stages in SAN_STAGES", mst is not None)
STAGES = mst.group(1).split() if mst else []
PROG = {}
for st in STAGES:
    m = re.search(r"cat > \"\$AWKP\.%s\" <<'AWKEOF'\n(.*?)\nAWKEOF\n" % re.escape(st), src, re.S)
    check("stage %s is a heredoc the test can cut out" % st, m is not None)
    PROG[st] = m.group(1) if m else ""
check("stages: lit first, ctx before mac, ip4 last", STAGES[:1] == ["lit"] and STAGES[-1:] == ["ip4"]
      and "ctx" in STAGES and STAGES.index("ctx") < STAGES.index("mac"), STAGES)
check("only the last stage strips the sentinels", 'gsub("\\001", "", line)' in PROG.get("ip4", "")
      and all('gsub("\\001"' not in PROG[x] for x in STAGES[:-1]))
m2 = re.search(r"RESID=\"\$\(awk -v FWVER=\"\$\(nvram get firmver 2>/dev/null\)\" '\n(.*?)' \"\$BODY\"\)\"", src, re.S)
check("the tripwire awk program is a quoted literal the test can cut out", m2 is not None)
TRIP = m2.group(1) if m2 else ""

awks = []
if shutil.which("busybox"):
    r = subprocess.run(["busybox", "awk", "BEGIN{print 1}"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip() == "1":
        awks.append(["busybox", "awk"])
for a in ("gawk", "mawk"):
    if shutil.which(a):
        awks.append([a])
if not awks:
    skip("no awk on the host (busybox, gawk or mawk)")
print("awks: " + ", ".join(" ".join(a) for a in awks))

RAW = "\n".join([
    "RETURN     all      *      *       2001:db8:8cd0::/48   ::/0",
    "RETURN     all      *      *       ::/0                 2001:db8:8cd0::/48",
    "RETURN     all      *      *       fe80::/10            ::/0",
    "RETURN     all      *      *       fc00::/7             ::/0",
    "RETURN     all      *      *       ::/0                 2001:db8:8cd0:1:a::b/128",
    "inet6 addr: fe80::211:22ff:fe33:4455/64 Scope:Link",
    "mdns ff02::fb all-nodes ff02::1",
    "tcp        0      0 ::1:53                  :::*                    LISTEN",
    "Dec 31 19:10:23 dnsmasq[4046]: using nameserver 192.168.50.1#53 for domain 0.0.0.0.0.d.c.8.0.7.4.0.1.0.0.2.ip6.arpa",
    "Dec 31 19:10:23 dnsmasq[4042]: using nameserver 10.20.0.1#53 for domain 0.0.1.0.0.d.c.8.0.7.4.0.1.0.0.2.ip6.arpa",
    "Dec 31 19:10:23 dnsmasq[4042]: using nameserver 10.20.0.1#53 for domain 0.20.10.in-addr.arpa",
    "duid 00:01:00:01:2f:3a:4b:5c:6e:d8:39:8c",
    "86400 aa:bb:cc:dd:ee:ff 192.168.50.97 host",
    "br0\t\t8000.aabbccddeeff\tno\t\teth1",
    "Oct 12 19:10:01 rwatch: tick 12:34:56",
    "resolver: other-external 203.0.113.9",
    # 16-26: v1.3.36 client-supplied names
    "Dec 31 19:01:43 dnsmasq-dhcp[4041]: Ignoring domain v08.med.example.gov for DHCP host name WORKPC-17",
    "Dec 31 19:01:43 dnsmasq-dhcp[4041]: DHCPACK(br0) 192.168.50.223 11:22:33:44:55:66 WORKPC-17",
    "Oct 11 09:00:01 dnsmasq-dhcp[4041]: DHCPACK(br0) 192.168.50.40 11:22:33:44:55:77 tv",
    "Oct 11 09:00:02 dnsmasq-dhcp[4041]: DHCPACK(br0) 192.168.50.41 11:22:33:44:55:88",
    "Oct 11 09:00:03 dnsmasq-dhcp[4041]: not giving name kitchen-ipad to the DHCP lease of 192.168.50.42 because the name exists in /etc/hosts",
    "Oct 11 09:00:04 gatekeeper: new device 11:22:33:44:55:99 host (Guest-Laptop) held at the gate",
    "Oct 11 09:00:05 an unrelated line mentions WORKPC-17 and v08.med.example.gov again",
    "Dec 31 19:01:44 dnsmasq-dhcp[4041]: Ignoring domain lan for DHCP host name laptop",
    "Oct 11 09:00:06 dnsmasq-dhcp[4041]: DHCPREPLY(br0) 2001:db8:8cd0::5 00:01:00:01:2f:3a:4b:5c:6e:d8:39:8d phone6",
    "Oct 11 09:00:07 ntpd: server pool.ntp.org ok on wlan0, lan_ifnames unchanged",
    "Oct 11 09:00:08 dnsmasq-dhcp[4041]: DHCPACK(br0) 192.168.50.50 11:22:33:44:55:aa MyNAS-01",
    # 27-29: v1.3.37 a generic device/OS word as a name is masked in its template line only
    "Oct 11 09:00:09 dnsmasq-dhcp[4041]: DHCPACK(br0) 192.168.50.61 11:22:33:44:55:bb Linux",
    "  uname: Linux GT-BE98 4.19.294 #1 SMP PREEMPT aarch64 | 5523 admin S sw_devled",
    "Oct 11 09:00:10 dnsmasq-dhcp[4041]: DHCPACK(br0) 192.168.50.62 11:22:33:44:55:cc admin",
])
SLIST = "HOST\tMyNAS-01\n"

def pipeline(text):
    """Run SAN_STAGES in order, exactly as the script does (ctx gets the file twice)."""
    res = []
    for a in awks:
        with tempfile.TemporaryDirectory() as td:
            sl = os.path.join(td, "s.list"); open(sl, "w").write(SLIST)
            cur = os.path.join(td, "in.0"); open(cur, "w").write(text + "\n")
            ledger, ok, errs = "", True, ""
            for n, st in enumerate(STAGES, 1):
                pf = os.path.join(td, st + ".awk"); open(pf, "w").write(PROG[st])
                nxt = os.path.join(td, "in.%d" % n)
                files = [cur, cur] if st == "ctx" else [cur]
                r = subprocess.run(a + ["-v", "SFILE=" + sl, "-v", "FWVER=3.0.0.6", "-f", pf] + files,
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    ok, errs = False, errs + "%s: %s\n" % (st, r.stderr)
                    break
                open(nxt, "w").write(r.stdout)
                ledger += r.stderr
                cur = nxt
            res.append((" ".join(a), ok, open(cur).read(), ledger, errs))
    return res

def trip(text, a):
    with tempfile.TemporaryDirectory() as td:
        pf = os.path.join(td, "t.awk"); i = os.path.join(td, "b.txt")
        open(pf, "w").write(TRIP); open(i, "w").write(text)
        r = subprocess.run(a + ["-v", "FWVER=3.0.0.6", "-f", pf, i], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

# ------------------------------------------------------------------ the pipeline, executed
for (name, ok, out, err, errs), a in zip(pipeline(RAW), awks):
    tag = "[%s] " % name
    check(tag + "every stage runs", ok, errs)
    L = out.split("\n")
    if len(L) < 30:
        check(tag + "the pipeline kept every line", False, len(L))
        continue
    check(tag + "a prefix ending in :: is tokenized", "[IP6-" in L[0] and "8cd0" not in L[0] and "2001" not in L[0], L[0])
    tok = re.search(r"\[IP6-\d+\]", L[0]).group(0) if re.search(r"\[IP6-\d+\]", L[0]) else ""
    check(tag + "the same prefix gets the same token on the next line", tok and tok + "/48" in L[1], L[1])
    check(tag + "::/0 and ::1 stay as they are", "::/0" in L[0] and "::/0" in L[1] and "::1:53" in L[7], (L[0], L[7]))
    check(tag + "fe80::/10 and fc00::/7 stay readable", "fe80::/10" in L[2] and "fc00::/7" in L[3], (L[2], L[3]))
    check(tag + "a full compressed address is tokenized", "[IP6-" in L[4] and "8cd0" not in L[4], L[4])
    check(tag + "a link-local address with an EUI-64 tail is tokenized", "[IP6-" in L[5] and "fe33" not in L[5], L[5])
    check(tag + "ff02::fb and ff02::1 stay readable", "ff02::fb" in L[6] and "ff02::1" in L[6], L[6])
    check(tag + "a reverse zone is tokenized whole, nothing carved out as an IPv4",
          "[IP6-ARPA-1]" in L[8] and "8.0.7.4" not in L[8] and "d.c" not in L[8] and "[EXT-IP-" not in L[8] and "192.168.50.1" in L[8], L[8])
    check(tag + "a second reverse zone gets its own token", "[IP6-ARPA-2]" in L[9] and "[EXT-IP-" not in L[9], L[9])
    check(tag + "a private in-addr.arpa zone is untouched", "0.20.10.in-addr.arpa" in L[10], L[10])
    check(tag + "a DUID is one pseudonym, no tail left", "MAC-" in L[11] and not re.search(r"[0-9a-f]{2}:[0-9a-f]{2}", L[11]), L[11])
    check(tag + "a MAC in a lease line is a pseudonym", "MAC-" in L[12] and "aa:bb" not in L[12] and "192.168.50.97" in L[12], L[12])
    check(tag + "a colonless bridge id is still a pseudonym", "MAC-" in L[13] and "aabbcc" not in L[13], L[13])
    check(tag + "a timestamp is untouched", "12:34:56" in L[14], L[14])
    check(tag + "a public IPv4 is still tokenized", "[EXT-IP-" in L[15] and "203.0.113.9" not in L[15], L[15])
    # v1.3.36 client-supplied names
    check(tag + "a client's DHCP domain is masked, and the name beside it",
          "example.gov" not in L[16] and "[CLIENT-DOMAIN-1]" in L[16] and "WORKPC-17" not in L[16] and "[CLIENT-NAME-" in L[16], L[16])
    nt = re.search(r"\[CLIENT-NAME-\d+\]", L[16])
    nt = nt.group(0) if nt else "?"
    check(tag + "the same name on its DHCPACK line gets the same token", L[17].endswith(nt) and "WORKPC" not in L[17], L[17])
    check(tag + "a short DHCPACK name is masked at its position",
          re.search(r"\[CLIENT-NAME-\d+\]$", L[18]) is not None and not L[18].endswith(" tv"), L[18])
    check(tag + "a DHCPACK without a name keeps its MAC pseudonym last",
          re.search(r"MAC-\d+$", L[19]) is not None and "CLIENT" not in L[19], L[19])
    check(tag + "a 'not giving name' name is masked", "kitchen-ipad" not in L[20] and "[CLIENT-NAME-" in L[20], L[20])
    check(tag + "a gatekeeper host name is masked", "Guest-Laptop" not in L[21] and "host ([CLIENT-NAME-" in L[21], L[21])
    check(tag + "a collected name and domain are masked on any other line too",
          "WORKPC-17" not in L[22] and "example.gov" not in L[22] and nt in L[22] and "[CLIENT-DOMAIN-1]" in L[22], L[22])
    check(tag + "a generic domain stays readable, its name does not",
          "Ignoring domain lan for" in L[23] and "laptop" not in L[23], L[23])
    check(tag + "a DHCPv6 reply name is masked, the address and DUID too",
          "phone6" not in L[24] and "8cd0" not in L[24] and "MAC-" in L[24], L[24])
    check(tag + "ordinary names and words stay readable",
          "pool.ntp.org" in L[25] and "wlan0" in L[25] and "lan_ifnames" in L[25], L[25])
    check(tag + "a name the literal list holds keeps its literal token",
          L[26].endswith("[HOST-1]") and "CLIENT" not in L[26], L[26])
    check(tag + "a generic word used as a name is still masked at its DHCPACK position",
          re.search(r"\[CLIENT-NAME-\d+\]$", L[27]) is not None and re.search(r"\[CLIENT-NAME-\d+\]$", L[29]) is not None, (L[27], L[29]))
    check(tag + "but not across the rest of the report (uname and ps lines keep Linux and admin)",
          "uname: Linux GT-BE98" in L[28] and "5523 admin S sw_devled" in L[28], L[28])
    ordered = all(k in err for k in ("hostnames", "client names", "MAC addresses", "IPv6 addresses", "public IPv4"))
    check(tag + "the ledger carries every stage's lines, in stage order",
          ordered
          and re.search(r"hostnames redacted\s+: 1\b", err) is not None
          and re.search(r"client names from log lines: [5-9]", err) is not None
          and re.search(r"client domains redacted\s+: 1\b", err) is not None
          and re.search(r"IPv6 reverse zones redacted: 2\b", err) is not None
          and err.index("hostnames") < err.index("client names") < err.index("MAC addresses")
          < err.index("IPv6 addresses") < err.index("public IPv4"), err)
    rc, tout, terr = trip(out, a)
    check(tag + "tripwire runs on the sanitized body", rc == 0, terr)
    check(tag + "tripwire: the sanitized body has no residue (IPv4 IPv6 MAC e-mail client-names)",
          tout.strip() == "0 0 0 0 0", tout)
    rc, tout, terr = trip(RAW + "\n", a)
    v = tout.split()
    check(tag + "tripwire: the raw lines count IPv6, MAC and client-name residue",
          len(v) == 5 and int(v[3]) >= 4 and int(v[1]) >= 2 and int(v[4]) >= 5, tout)

# ------------------------------------------------------------------ the rest, read
check("a failing stage writes no report", "sanitizer stage '$_st' failed - no report written" in src
      and 'rm -f "$BODY".* "$BODY"' in src)
check("the scratch cleanup covers the stage files", "$AWKP.* $BODY $BODY.*" in src)
check("the lease section skips the duid line", "awk '$1 == \"duid\" { next } {" in src)
check("the ledger prints the residual lines and the verdict names client names",
      'echo "  residual IPv6 shapes        : $R6"' in src and 'echo "  residual client names       : $RC"' in src
      and "MAC, e-mail or client-supplied name survived the sanitizer" in src)
check("the boot-skeleton finding no longer claims a refused line in every case",
      "(one line was refused;" not in src and "no refused line was recorded" in src
      and "_nerr=$(ls /tmp/err_rules/*.err" in src)
check("VER is v1.3.48", 'VER="REAPER-DIAG v1.3.52"' in src)
mkr = open(os.path.join(HERE, "..", "verify_markers.txt"), encoding="utf-8").read()
check("build markers pin the version and the new tokens",
      "usr/sbin/reaper_diag|REAPER-DIAG v1.3.52|1" in mkr and "usr/sbin/reaper_diag|4c. DNS DIRECTOR|1" in mkr
      and "usr/sbin/reaper_diag|[IP6-ARPA-|1" in mkr
      and "usr/sbin/reaper_diag|residual IPv6 shapes|1" in mkr and "usr/sbin/reaper_diag|[CLIENT-DOMAIN-|1" in mkr
      and "usr/sbin/reaper_diag|residual client names|1" in mkr
      and "usr/sbin/reaper_diag|reaper_tx_sg_max|1" in mkr and "usr/sbin/reaper_diag|dot upstreams|1" in mkr)

# ------------------------------------------------------------------ v1.3.38 Runner 4-frag cap
check("15 reads the kernel cap, its counter and TCP's max_skb_frags",
      "/proc/sys/net/core/reaper_tx_sg_max" in src and "/proc/sys/net/core/reaper_tx_sg_linearized" in src
      and "/proc/sys/net/core/max_skb_frags" in src)
check("15 counts the refused-packet lines in dmesg and syslog and reads tx_dropped",
      "dmesg 2>/dev/null | grep -c 'exceed max_sg_array'" in src and "statistics/tx_dropped" in src and "/proc/net/vlan/config" in src)
check("15's syslog count takes only the kernel's own line (an echoed command is not a refused packet)",
      "grep -c 'exceed max_sg_array' \"$F\"" not in src)
m = re.search(r"SGS \+ \$\(grep -c '([^']+)' \"\$F\"", src)
check("15: the syslog pattern can be cut out", m is not None)
if m and shutil.which("busybox"):
    sample = "\n".join([
        "Oct 14 11:05:41 kernel: bdmf_sysb_data_to_sgdesc: ERROR: skb->nr_frags 5 exceed max_sg_array 4",
        "Oct  4 09:01:02 kernel: bdmf_sysb_data_to_sgdesc: ERROR: skb->nr_frags 10 exceed max_sg_array 4",
        "Oct 14 07:16:02 rmcpd-lab: rmcpd-lab: exec: dmesg | grep -c 'exceed max_sg_array'",
        "Oct 14 07:20:00 rmcpd-lab: exec: grep -c '" + m.group(1) + "' f",
    ]) + "\n"
    r = subprocess.run(["busybox", "grep", "-c", m.group(1)], input=sample, capture_output=True, text=True)
    check("15: the syslog pattern counts the two kernel lines and neither echoed command (busybox grep)",
          r.stdout.strip() == "2", r.stdout + r.stderr)
check("a FINDING fires on any refused-packet line",
      'if [ "${SGN:-0}" -gt 0 ] 2>/dev/null; then' in src and "with more than 4 fragments" in src)
check("5 counts DoT upstreams by family and never prints the list",
      "dot upstreams     : ipv4=$DOT4 ipv6=$DOT6" in src and 'echo "$(nvram get dnspriv_rulelist' not in src)
# v1.3.38: a dead dongle is named in 7 and a trap counted in 19b (owner RT-BE96U 2026-10-14)
check("7: a radio on in nvram whose driver has no adapter is a FINDING",
      'if [ "$(nvram get wl${u}_radio 2>/dev/null)" = 1 ] && [ -z "$(wl -i $IFN isup 2>/dev/null)" ]; then' in src
      and "is enabled but its driver has no adapter" in src and "dongle: NOT ANSWERING" in src)
check("19b: dongle traps are counted on the kernel's own line and the crash dumps listed by name only",
      "kernel: TRAP type 0x' \"$SNAP\"" in src and 'debug-*_DHD.tgz' in src and "dongle traps      :" in src
      and "dongle trap(s) in the log" in src)
m = re.search(r"grep -iE 'error\|fail\|warn\|oops\|BUG\|timeout\|leak\|denied' \| awk '(.*?)' \| sort", src)
check("19b: the dmesg summary masks through an awk program the test can cut out", m is not None)
if m:
    SUMIN = "\n".join([
        "bdmf_sysb_data_to_sgdesc: ERROR: skb->nr_frags 5 exceed max_sg_array 4",
        "SBF: hdr [0xffffff801a207000] bfwtbl [0xffffff801a207010] error",
        "CFG80211-ERROR) wl_cfg80211_add_virtual_iface :",
        "failed to set WLC_E_CAC_STATE_CHANGE bit",
    ]) + "\n"
    for a in awks:
        tag = "[%s] " % " ".join(a)
        r = subprocess.run(a + [m.group(1)], input=SUMIN, capture_output=True, text=True)
        L = r.stdout.split("\n")
        check(tag + "19b: the summary program runs", r.returncode == 0 and len(L) >= 4, r.stderr)
        if len(L) < 4: continue
        check(tag + "19b: 'exceed' and the frag counts stay readable",
              L[0] == "bdmf_sysb_data_to_sgdesc: ERROR: skb->nr_frags 5 exceed max_sg_array 4", L[0])
        check(tag + "19b: kernel addresses collapse to N", L[1] == "SBF: hdr [N] bfwtbl [N] error", L[1])
        check(tag + "19b: driver names with short digit runs stay as they are",
              L[2] == "CFG80211-ERROR) wl_cfg80211_add_virtual_iface :" and L[3].startswith("failed to set WLC_E_CAC"), (L[2], L[3]))

# ------------------------------------------------------------------ v1.3.39 DNS Director, QoS port, gateway
# GT-BE98 2026-10-14: the report could not say what DNS Director was told per network, read
# tmctl against a VLAN device (rc=108) and claimed a QoS cap on a jack hardware QoS refuses,
# and printed "default gateway: NONE" on a dual-WAN multipath route.
check("4c exists and reads the nat chain with counters, never a MAC or an address",
      'sec "4c. DNS DIRECTOR' in src and "iptables -t nat -nvxL DNSFILTER 2>/dev/null | tail -n +3 > \"$DFS\"" in src
      and "$DFS" in src.split("trap 'rm -f")[1].split("\n")[0]
      and 'echo "$(nvram get dnsfilter_rulelist' not in src and 'echo "$(nvram get dnsfilter_custom' not in src)
check("4c: a network at No Redirection under a global mode is a FINDING, a choice without a rule is a WARN",
      "does not reach them - a device there may use any port-53 server" in src
      and "have a DNS Director choice but no rule in the nat chain" in src)
check("4c: the DoT block and the IPv6 filter chain are read per family",
      "DNSFILTER_DOT" in src and "ip6tables -nvxL DNSFILTERF" in src)
check("5: resolvers are named by kind through dnskind()", "dnskind() {" in src and 'echo "  resolver: $(dnskind "$d")"' in src
      and "Cloudflare family ($d)" not in src)
check("10: the shaped port is resolved like hwqos_tm_ifname() and a LAN-trunk parent refuses",
      "/proc/net/vlan/config" in src.split('sec "10. QOS')[1].split('sec "10b.')[0]
      and '/sys/class/net/$QPAR/brport' in src and "is enabled but NOT applied" in src
      and "tmctl getqcfg --devtype 0 --if $QPORT --qid $q" in src and "tmctl getqcfg --devtype 0 --if $WANIF" not in src)
check("16: the gateway comes from every 'via' of the default route, point-to-point is named",
      'DRT="$(ip route show default 2>/dev/null)"' in src and "sed -n 's/.*via \\([0-9][0-9.]*\\).*/\\1/p'" in src
      and "point-to-point on" in src and "awk '/^default/{print $3; exit}'" not in src)
# the SDN parser is executed: sdn_rl field 9 is dnsf_idx, subnet_rl field 2 the bridge, main LAN and
# disabled networks are skipped, cp_idx (field 12) rides along
msd = re.search(r"^sdn_dnsf\(\) \{\n(.*?)\n\}\n", src, re.S | re.M)
check("4c: sdn_dnsf() can be cut out", msd is not None)
shs = []
if shutil.which("busybox"):
    shs.append(["busybox", "sh"])
if shutil.which("sh"):
    shs.append(["sh"])
if msd and shs:
    SDN = ("<0>DEFAULT>1>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
           "<1>CCTV>1>1>1>1>0>0>0>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
           "<2>IoT>1>2>2>2>0>0>11>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
           "<3>Guest>1>3>3>3>0>0>8>0>0>1>0>0>0>0>0>0>0>WEB>0>0>0"
           "<4>Off>0>4>4>4>0>0>11>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0"
           "<5>NoSubnet>1>5>0>5>0>0>13>0>0>0>0>0>0>0>0>0>0>WEB>0>0>0")
    SUB = ("<1>br55>10.1.50.1>255.255.255.128>1>10.1.50.2>10.1.50.126>86400>>>>>>0"
           "<2>br56>10.1.65.1>255.255.255.240>1>10.1.65.2>10.1.65.14>86400>>>>>>0"
           "<3>br57>10.1.60.1>255.255.255.240>1>10.1.60.2>10.1.60.14>86400>>>>>>0"
           "<4>br58>10.1.70.1>255.255.255.240>1>10.1.70.2>10.1.70.14>86400>>>>>>0")
    prog = "sdn_dnsf() {\n" + msd.group(1) + "\n}\nsdn_dnsf \"$1\" \"$2\"\n"
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
        fh.write(prog); tp = fh.name
    try:
        for s in shs:
            tag = "[%s] " % " ".join(s)
            r = subprocess.run(s + [tp, SDN, SUB], capture_output=True, text=True)
            check(tag + "4c: sdn_dnsf prints bridge, sdn index, dnsf_idx and cp_idx for the enabled networks with a subnet only",
                  r.returncode == 0 and r.stdout.split("\n")[:-1] == ["br55 1 0 0", "br56 2 11 0", "br57 3 8 1"], r.stdout + r.stderr)
    finally:
        os.unlink(tp)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
