#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every IPv4 nat/probe/bind site the 2026-10-07 IPv6 review named keeps its IPv6 twin.

WHY THIS EXISTS. The review (audits/IPV6-COVERAGE-2026-10-07.md) found the enforcement
layers dual-stack but the NAT-based features and the probes IPv4-only: Gatekeeper's
captive redirect (A4), the rules engine's intercepts (A5), rwatch's WAN probes (A7),
the SNMP agent address (A9) and the DHCPv6 hostname path (A10). Each fix is a twin
line beside an existing IPv4 line in generated shell, so a later edit to the v4 line
is exactly where the twin gets lost. This test pins the pairs.

WHAT IT DOES. Reads the sources and asserts, per site, that the ip6tables / ping6 /
udp6 / DNSMASQ_MAC twin is present and, where the v4 form is counted, that the two
counts agree. Source-level only; the generated scripts themselves are exercised by
the build's reaper_verify markers and on metal.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as
argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "gatekeeper.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="replace").read()

def pair(text, v4, v6, label):
    a, b = text.count(v4), text.count(v6)
    if a == 0:
        die("%s: the IPv4 form is gone (%r) - update this test with the code" % (label, v4))
    if b != a:
        die("%s: %d IPv4 line(s) but %d IPv6 twin(s)\n  v4: %r\n  v6: %r" % (label, a, b, v4, v6))
    ok("%s: %d pair(s)" % (label, a))

def has(text, needle, label):
    if needle not in text:
        die("%s: missing %r" % (label, needle))
    ok(label)

# ---- A4 Gatekeeper captive redirect ----
g = read("rc/gatekeeper.c")
pair(g, "while iptables -t nat -D PREROUTING -i $I -j REAPER_GKN", "while ip6tables -t nat -D PREROUTING -i $I -j REAPER_GKN", "gatekeeper: nat PREROUTING jump teardown (apply.sh + C)")
pair(g, "iptables -t nat -F REAPER_GKN", "ip6tables -t nat -F REAPER_GKN", "gatekeeper: REAPER_GKN flush/delete")
pair(g, '"iptables -t nat -N REAPER_GKN', '"ip6tables -t nat -N REAPER_GKN', "gatekeeper: REAPER_GKN creation")
pair(g, "iptables -t nat -I PREROUTING 1 -i $I -j REAPER_GKN", "ip6tables -t nat -I PREROUTING 1 -i $I -j REAPER_GKN", "gatekeeper: per-bridge nat hook")
has(g, "ip6tables -t nat -A REAPER_GKN -p tcp --dport 80 -j REDIRECT --to-ports 80", "gatekeeper: IPv6 captive REDIRECT present")
if g.count("$T -t nat -A REAPER_GKN -m mac --mac-source %s -j RETURN; done") < 2:
    die("gatekeeper: the known-MAC RETURN into REAPER_GKN is not emitted for both tables at both sites")
ok("gatekeeper: known-MAC nat RETURN loops over iptables and ip6tables (device rules + AiMesh relist)")
if "iptables -t nat -A REAPER_GKN -m mac --mac-source %s -j RETURN\\n\"" in g and "for T in iptables ip6tables; do $T -t nat -A REAPER_GKN" not in g:
    die("gatekeeper: a bare v4-only known-MAC RETURN into REAPER_GKN remains")
has(read("gkd/gkd.c"), "ip6tables -t nat -nL REAPER_GKN", "gkd: chains_armed() asserts the IPv6 nat chain too")
h = read("httpd/httpd.c")
has(h, "reaper_nd_mac_of_str", "httpd: the captive check resolves an IPv6 peer through the shared neighbour cache")
if re.search(r"v6 peer: ARP can't resolve - let it through", h):
    die("httpd: the old 'let an IPv6 peer through' early return is still present")
ok("httpd: no IPv6 peer bypass of the captive check")

# ---- A7 rwatch ----
r = read("rc/rwatch.c")
for needle, label in (("ping6 -c1 -W3 \\\"$GW6\\\"", "rwatch: IPv6 first-hop probe"),
                      ("ping6 -c1 -W3 2606:4700:4700::1111", "rwatch: IPv6 internet probe (Cloudflare)"),
                      ("ping6 -c1 -W3 2001:4860:4860::8888", "rwatch: IPv6 internet probe (Google)"),
                      ("FAIL=\\\"$FAIL wan6-gw\\\"", "rwatch: wan6-gw token"),
                      ("FAIL=\\\"$FAIL wan6-internet\\\"", "rwatch: wan6-internet token"),
                      ("[ \\\"$V6S\\\" != disabled ] && [ -n \\\"$V6R\\\" ]", "rwatch: the probe is gated on ipv6_service + ipv6_rtr_addr"),
                      ("{ ip -6 addr; ip -6 neigh; }", "rwatch: incident dump carries the IPv6 address and neighbour tables")):
    has(r, needle, label)
i6, i2 = r.find("# 1b) IPv6 first hop"), r.find("# 2) loopback DNS through dnsmasq")
if not (0 < i6 < i2):
    die("rwatch: the IPv6 block must sit between section 1 and section 2")
ok("rwatch: IPv6 block ordered after the IPv4 first-hop check and before the DNS check")

# ---- A9 SNMP ----
s = read("rc/snmpd.c")
has(s, "agentAddress udp:%s:161,udp6:[%s]:161", "snmpd: dual agentAddress when the LAN has a global IPv6 address")
has(s, 'ipv6_nvname("ipv6_rtr_addr")', "snmpd: the v6 address comes from the WAN-unit-aware nvram name")
has(s, 'fprintf(fp, "agentAddress udp:%s:161\\n", lan_ip);', "snmpd: the IPv4-only form is kept for a box without IPv6")
fw = read("rc/firewall.c")
pair(fw, '-A INPUT -i %s -p udp --dport 161 -j %s\\n", wan_if', '-A INPUT -i %s -p udp --dport 161 -j %s\\n", wan6face', "firewall: snmpd_wan INPUT allow")

# ---- A10 DHCPv6 hostnames ----
sv = read("rc/services.c")
has(sv, 'getenv("DNSMASQ_MAC")', "services: DHCPv6 lease events file the name under DNSMASQ_MAC")
has(sv, "is6 ? NULL : getenv(\"DNSMASQ_VENDOR_CLASS\")", "services: no vendor class is recorded for a DHCPv6 event")

# ---- A5 rules engine ----
f = read("rc/reaper_fw.c")
pair(f, "iptables -t nat -N \" RFW_CHAIN_NAT", "ip6tables -t nat -N \" RFW_CHAIN_NAT", "reaper_fw: REAPER_FWN creation")
pair(f, "iptables -t nat -N \" RFW_CHAIN_MASQ", "ip6tables -t nat -N \" RFW_CHAIN_MASQ", "reaper_fw: REAPER_FWM creation")
pair(f, "iptables -t nat -N \" RFW_CHAIN_HC", "ip6tables -t nat -N \" RFW_CHAIN_HC", "reaper_fw: REAPER_FWHC creation")
pair(f, "iptables -t nat -I PREROUTING -j \" RFW_CHAIN_NAT", "ip6tables -t nat -I PREROUTING -j \" RFW_CHAIN_NAT", "reaper_fw: PREROUTING hook")
pair(f, "iptables -t nat -A POSTROUTING -j \" RFW_CHAIN_MASQ", "ip6tables -t nat -A POSTROUTING -j \" RFW_CHAIN_MASQ", "reaper_fw: POSTROUTING hook")
pair(f, "while iptables -t nat -D PREROUTING -j \" RFW_CHAIN_NAT", "while ip6tables -t nat -D PREROUTING -j \" RFW_CHAIN_NAT", "reaper_fw: PREROUTING teardown")
pair(f, "while iptables -t nat -D POSTROUTING -j \" RFW_CHAIN_MASQ", "while ip6tables -t nat -D POSTROUTING -j \" RFW_CHAIN_MASQ", "reaper_fw: POSTROUTING teardown")
pair(f, "iptables -t nat -F \" RFW_CHAIN_NAT", "ip6tables -t nat -F \" RFW_CHAIN_NAT", "reaper_fw: REAPER_FWN flush")
pair(f, "iptables -t nat -X \" RFW_CHAIN_NAT", "ip6tables -t nat -X \" RFW_CHAIN_NAT", "reaper_fw: REAPER_FWN delete")
has(f, "RFWR ip6tables -t nat -A \" RFW_CHAIN_NAT \" -i %s -p %s --dport %s%s%s%s", "reaper_fw: IPv6 redirect twin")
has(f, "-j DNAT --to-destination [%s]:%s", "reaper_fw: IPv6 intercept DNAT with a bracketed target")
has(f, "rfw_hc_target6", "reaper_fw: the resolver-health gate knows the watched resolver's IPv6 address")
has(f, "for T in iptables ip6tables; do\\n\"", "reaper_fw: hcgate.sh walks both families")
has(f, "case $T in iptables) F=ipv4; M=\" RFW_HC_DOWN4 \";; *) F=ipv6; M=\" RFW_HC_DOWN6 \";; esac", "reaper_fw: hcgate.sh closes the IPv6 chain on its own marker (2026-10-08)")
has(f, "rfw_field(tok, 12, iip6", "reaper_fw: field 12 (iip6) is parsed")
print("PASS test_ipv6_twins")
