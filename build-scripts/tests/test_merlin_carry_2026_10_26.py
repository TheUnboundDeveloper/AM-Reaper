#!/usr/bin/env python3
"""Upstream carries from Asuswrt-Merlin, 2026-10-26 (owner picked 1-5 and 7 of the review list).

WHY. Merlin (Eric Sauvageau) took these after 3006.102.10 alpha 2; each was checked against our tree first, so none
duplicates an earlier fix of ours:
  1. miniupnpd "MX: 0" is invalid (CVE-2026-107159; Thomas Bernard, Merlin da326375b16) - both trees, BE96U ships
     the IGDv2 one. Our code treated 0 as a valid wait time. NOT reachable in our build today: both config.h
     files leave UPNP_STRICT and DELAY_MSEARCH_RESPONSE off, which compiles the whole MX path out; carried so
     the code matches upstream and stays safe if either is ever switched on.
  2. urlfilterd bounds the captured payload and searches a NUL-terminated copy (ASUS GPL 102_40585, in Merlin's
     RT-BE96U merge d7c6a53e440). Our earlier "urlfilter" hardening (bcc18b85e41) fixed the keyword quoting in the
     firewall rules, not the daemon's packet parsing.
  3. CA bundle: Mozilla data of 2026-10-21 (Merlin ea5483e5207) - Entrust Root CA, ePKI, Atos TrustedRoot 2011 and
     SecureSign Root CA12 out; SECOM 2024 and Telia v3 in. Ours was 2026-05-24.
  4. wanduck's listening sockets are close-on-exec (Jacopo Labardi, Merlin ba476c59af1).
  5. SDN networks may reach the router's DNS over TCP (dave14305, Merlin e26fc8f4d78). Our own firewall engine
     allowed TCP 53 from the main LAN only.
  7. OpenSSL 3.5 configure: the deprecated no-ssl2 option is gone (Merlin 9e53d766f86).
Item 6 (the Wi-Fi start-up scripts) is deliberately NOT carried: the owner is investigating it first.

WHAT IT DOES. Source checks for each item, plus: every certificate in the bundle parses (when openssl is present).
"""
import os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "wanduck.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

for t in ("miniupnpd-igdv2", "miniupnpd"):
    s = rd(t + "/minissdp.c")
    check("1 %s: MX 0 or negative is refused (strict) / treated as 1 (delayed)" % t,
          "} else if(mx_value <= 0) {" in s and 'ignoring SSDP packet with invalid value for MX: header' in s
          and re.search(r"#elif defined\(DELAY_MSEARCH_RESPONSE\)\s*\n\s*if\(mx_value <= 0\) \{", s))
    check("1 %s: a missing MX is still told apart from an invalid one" % t, "if(mx_value == -1) {" in s)

uf_path = os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "router-sysdep.rt-be96u", "urlfilterd", "filter.c")
if os.path.isfile(uf_path):
    u = open(uf_path, encoding="utf-8", errors="surrogateescape").read()
    check("2 urlfilterd: a capture shorter than an IP header is accepted untouched",
          "if (data_len < (int)sizeof(struct iphdr))" in u)
    check("2 urlfilterd: an offset past the captured data is accepted untouched",
          "if (payload_offset < 0 || payload_offset >= data_len)" in u)
    check("2 urlfilterd: the search runs on a bounded, NUL-terminated copy",
          "memcpy(match_buf, data + payload_offset, match_len);" in u and "match_buf[match_len] = '\\0';" in u
          and "match = match_buf;" in u and "match = (char *)(data + payload_offset);" not in u)
else:
    print("skip urlfilterd (no router-sysdep.rt-be96u next to the router tree)")

ca = rd("rom/certs/ca-bundle.crt")
check("3 CA bundle is Mozilla's 2026-10-21 data or newer",
      re.search(r"Certificate data from Mozilla as of: \w+ (\w+) (\d+) [\d:]+ (\d{4})", ca) is not None and
      (lambda m: (int(m.group(3)), ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(m.group(1)), int(m.group(2))) >= (2026, 9, 21))(
          re.search(r"Certificate data from Mozilla as of: \w+ (\w+) (\d+) [\d:]+ (\d{4})", ca)))
for n in ("Entrust Root Certification Authority", "ePKI Root Certification Authority", "Atos TrustedRoot 2011", "SecureSign Root CA12"):
    check("3 CA bundle: '%s' is out" % n, re.search(r"^%s$" % re.escape(n), ca, re.M) is None)
for n in ("SECOM TLS RSA Root CA 2024", "Telia RSA TLS Root CA v3"):
    check("3 CA bundle: '%s' is in" % n, re.search(r"^%s$" % re.escape(n), ca, re.M) is not None)
if shutil.which("openssl"):
    p7 = subprocess.run(["openssl", "crl2pkcs7", "-nocrl", "-certfile", os.path.join(SRC, "rom/certs/ca-bundle.crt")], capture_output=True)
    pr = subprocess.run(["openssl", "pkcs7", "-print_certs", "-noout"], input=p7.stdout, capture_output=True)
    nparsed = len(re.findall(rb"^subject", pr.stdout, re.M))
    check("3 CA bundle: every certificate parses", nparsed == ca.count("BEGIN CERTIFICATE") and nparsed > 100, (nparsed, ca.count("BEGIN CERTIFICATE")))

w = rd("rc/wanduck.c")
check("4 wanduck: passivesock() sockets are close-on-exec", "s = socket(PF_INET, type | SOCK_CLOEXEC, protocol_num);" in w)

f = rd("rc/firewall_sdn.c")
TCP53 = 'fprintf(fp, "-A %s -i %s -p tcp --dport 53 -j %s\\n", SDN_FILTER_INPUT_CHAIN, pmtl->nw_t.ifname, logaccept);'
check("5 SDN: DNS over TCP to the router is accepted on each SDN interface (IPv4 and the IPv6 twin)", f.count(TCP53) == 2, f.count(TCP53))
# each TCP rule must come before that family's host-service drop, as the UDP rule does
v4, v6 = f.find('nvram_safe_get("lan_ipaddr"), logdrop'), f.find("pmtl->nw_t.ifname, addr6, logdrop")
t4, t6 = f.find(TCP53), f.find(TCP53, f.find(TCP53) + 1)
check("5 SDN: each TCP 53 accept sits before its family's host-service drop", 0 < t4 < v4 < t6 < v6, (t4, v4, t6, v6))

mk = rd("Makefile")
check("7 OpenSSL 3.5: no-ssl2 is no longer passed", re.search(r"^OPENSSL_CIPHERS := no-gost no-heartbeats no-err no-unit-test$", mk, re.M) is not None)

print("%d failure(s)" % len(fails))
for x in fails: print("  " + x)
sys.exit(1 if fails else 0)
