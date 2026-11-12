#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DNS-over-HTTPS for devices: the router side around rednsd (owner, 2026-11-10).

WHY THIS EXISTS. The Encrypted DNS server answered DNS-over-TLS only, so Windows 11 and web browsers, which set
up encrypted DNS as DNS-over-HTTPS, had to be left on plain DNS to be filtered. rednsd now also answers
DNS-over-HTTPS on TCP 443 of the LAN and guest addresses (its own test is test_rednsd.py). This file covers what
is built around it:
  rc      which listener lines are written, and that DNS-over-HTTPS stays down - with a reason - while the web
          interface or an OpenVPN server already owns TCP 443 on the router;
  httpd   the list of devices that still ask in the clear (connection table, the router's own networks only,
          never the router itself) and the lease names for the listed addresses;
  page    two switches, the two-leg status with its red warnings, the Save that offers to switch on the
          upstream leg, and the strings in all 25 language packs.

WHAT IT DOES. Compiles the real rc and httpd functions on the host with stand-ins for nvram, the interface list
and the files they read, runs them on sample data, and pins the page and pack text.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import glob, json, os, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
ENC = os.path.join(SRC, "rc", "encdns.c") if SRC else ""
if not ENC or not os.path.isfile(ENC):
    skip("no router source tree with rc/encdns.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
def cut(text, start, end):
    a = text.find(start); b = text.find(end, a + 1) if a >= 0 else -1
    return text[a:b] if 0 <= a < b else ""

tmp = tempfile.mkdtemp(prefix="dohsrv-")
def build(name, code, libs=()):
    c = os.path.join(tmp, name + ".c"); x = os.path.join(tmp, name)
    open(c, "w", encoding="utf-8", errors="surrogateescape").write(code)
    r = subprocess.run([CC, "-O1", "-Wall", "-Werror", "-Wno-unused-function", "-Wno-deprecated-declarations", "-o", x, c] + list(libs),
                       capture_output=True, text=True)
    return (x if r.returncode == 0 else None), r.stderr

# ------------------------------------------------------------------ rc: listener lines and the busy port
enc = rd(ENC)
rcfn = cut(enc, "static int red_dot_on(void)", "static void red_static(struct rb *r)")
check("rc: the three functions are found", "red_doh_busy" in rcfn and "red_listen" in rcfn)
check("rc: DNS-over-HTTPS port is 443 and DNS-over-TLS stays 853", "#define RED_DOH_PORT 443" in enc.replace("\t", " ") or "#define RED_DOH_PORT\t443" in enc)
RC_H = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define RED_PORT 853
#define RED_DOH_PORT 443
struct rb { char b[1024]; };
static void rb_add(struct rb *r, const char *fmt, ...) { va_list ap; size_t l = strlen(r->b); va_start(ap, fmt); vsnprintf(r->b + l, sizeof(r->b) - l, fmt, ap); va_end(ap); }
static int NA; static char **NV;
static const char *nvram_safe_get(const char *k) { int i; size_t l = strlen(k); for (i = 1; i < NA; i++) if (!strncmp(NV[i], k, l) && NV[i][l] == '=') return NV[i] + l + 1; return ""; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int ipv6_enabled(void) { return nvram_get_int("t_ipv6"); }	/* review 2026-11-11 (C-6) */
''' + rcfn + r'''
int main(int argc, char **argv) { struct rb r; const char *b; NA = argc; NV = argv; r.b[0] = 0;
  red_listen(&r, "192.168.50.1"); b = red_doh_busy(); printf("busy=%s\n%s", b ? b : "-", r.b); return 0; }
'''
x, err = build("rc", RC_H)
check("rc: the real functions compile on the host", x is not None, err)
def rc(*kv):
    return subprocess.run([x] + list(kv), capture_output=True, text=True).stdout if x else ""
BOTH = ["reaper_dot_srv=1", "reaper_doh_srv=1", "http_enable=2", "https_lanport=8443"]
L853, L443 = "listen 192.168.50.1 853\n", "listen 192.168.50.1 443 doh\n"
check("rc: both switches on, port free: an 853 line and a 443 doh line", rc(*BOTH) == "busy=-\n" + L853 + L443, rc(*BOTH))
check("rc: DNS-over-HTTPS only", rc("reaper_doh_srv=1", "https_lanport=8443", "http_enable=2") == "busy=-\n" + L443)
check("rc: DNS-over-TLS only (the state before this change)", rc("reaper_dot_srv=1", "https_lanport=8443", "http_enable=2") == "busy=-\n" + L853)
check("rc: neither switch writes no listener", rc("https_lanport=8443") == "busy=-\n")
o = rc("reaper_dot_srv=1", "reaper_doh_srv=1", "http_enable=2", "https_lanport=443")
check("rc: web interface on 443: no 443 line, DNS-over-TLS unaffected, reason 'https'", o == "busy=https\n" + L853, o)
check("rc: web interface HTTPS-only on 443 is busy too", rc("reaper_doh_srv=1", "http_enable=1", "https_lanport=443").startswith("busy=https\n"))
check("rc: plain-HTTP-only web interface leaves 443 free even if the port setting says 443",
      rc("reaper_doh_srv=1", "http_enable=0", "https_lanport=443") == "busy=-\n" + L443)
# review 2026-11-11 (C-6): Web Access from WAN over IPv6 has its own listener on the WAN HTTPS port
o = rc(*BOTH, "misc_http_x=1", "misc_httpsport_x=443", "t_ipv6=1")
check("rc: IPv6 web access from WAN on 443: reason 'https', no 443 line", o == "busy=https\n" + L853, o)
check("rc: the same with IPv6 off, on another port, or with web access off leaves 443 free",
      rc(*BOTH, "misc_http_x=1", "misc_httpsport_x=443") == "busy=-\n" + L853 + L443
      and rc(*BOTH, "misc_http_x=1", "misc_httpsport_x=8443", "t_ipv6=1") == "busy=-\n" + L853 + L443
      and rc(*BOTH, "misc_http_x=0", "misc_httpsport_x=443", "t_ipv6=1") == "busy=-\n" + L853 + L443)
o = rc(*BOTH, "vpn_server1_port=443", "vpn_server1_proto=tcp-server", "vpn_serverx_start=1,")
check("rc: an enabled OpenVPN server on tcp/443: reason 'ovpn', no 443 line", o == "busy=ovpn\n" + L853, o)
check("rc: the second OpenVPN server counts as well",
      rc(*BOTH, "vpn_server2_port=443", "vpn_server2_proto=tcp-server", "vpn_serverx_start=2,").startswith("busy=ovpn\n"))
check("rc: an OpenVPN server on udp/443 is no conflict",
      rc(*BOTH, "vpn_server1_port=443", "vpn_server1_proto=udp", "vpn_serverx_start=1,") == "busy=-\n" + L853 + L443)
check("rc: a tcp/443 OpenVPN server that is not started is no conflict",
      rc(*BOTH, "vpn_server1_port=443", "vpn_server1_proto=tcp-server", "vpn_serverx_start=") == "busy=-\n" + L853 + L443)
st = cut(enc, "static void red_static(struct rb *r)", "static void red_policy(struct rb *r)")
check("rc: every LAN-side address goes through red_listen", st.count("red_listen(r, ") >= 3, st.count("red_listen(r, "))
check("rc: the WAN-address listener stays DNS-over-TLS only (no 443 on the WAN address)",
      "wan" in st and " doh" not in st.replace("red_doh", ""), "")
check("rc: the server runs when either switch is on", "red_dot_on() || red_doh_on()" in cut(enc, "static int red_enabled(void)", "static void red_status_note"))
wd = cut(enc, "void rednsd_wan_drop(FILE *fp)", "\n}\n")
check("rc: the internet-side 443 drop exists only while DNS-over-HTTPS listens", "RED_DOH_PORT" in wd and "red_doh_on()" in wd and "red_doh_busy()" in wd, wd[:300])
check("rc: that drop spares the bridges and loopback", "! -i br+" in wd and "-i lo" in wd)
defs = rd(os.path.join(SRC, "shared", "defaults.c"))
check("defaults: reaper_doh_srv exists and is OFF", '{ "reaper_doh_srv", "0"' in defs)
web = rd(os.path.join(SRC, "httpd", "web.c"))
check("backup: reaper_doh_srv is in the settings table", '{ "encdns", "reaper_doh_srv", 2 }' in " ".join(web.split()))
rw = rd(os.path.join(SRC, "rc", "rwatch.c"))
check("watchdog: rednsd is restarted and recorded under either switch", rw.count("$(_nv reaper_doh_srv)") >= 2, rw.count("$(_nv reaper_doh_srv)"))
check("httpd and rc agree on what makes the port busy",
      'nvram_get_int("https_lanport") == 443' in cut(web, "static const char *renc_doh_busy(void)", "\n}\n").replace("RED_DOH_PORT", "443")
      or "https_lanport" in cut(web, "static const char *renc_doh_busy(void)", "\n}\n"))

# ------------------------------------------------------------------ httpd: who still asks in the clear
dev = cut(web, "#define RENC_PLAIN_MAX", "static int renc_private_v4(const char *s)")
check("httpd: the device code is found", "renc_plain_scan" in dev and "renc_devices" in dev)
ct = os.path.join(tmp, "conntrack"); ld = os.path.join(tmp, "misc"); os.mkdir(ld)
dev_t = dev.replace('"/proc/net/nf_conntrack"', json.dumps(ct)).replace('"/var/lib/misc/%s"', json.dumps(ld + "/%s")).replace('"/var/lib/misc"', json.dumps(ld))
check("httpd: the three paths were redirected for the test", ct in dev_t and dev_t.count(ld) == 2 and "/var/lib/misc" not in dev_t and "/proc/net" not in dev_t)
HT = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <dirent.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
struct ifaddrs { struct ifaddrs *ifa_next; char *ifa_name; struct sockaddr *ifa_addr, *ifa_netmask; };
static struct ifaddrs IF[8]; static struct sockaddr_storage SA[8], SM[8]; static int NIF;
static void addif(const char *name, int fam, const char *a, const char *m) {
  struct ifaddrs *i = &IF[NIF];
  memset(&SA[NIF], 0, sizeof(SA[0])); memset(&SM[NIF], 0, sizeof(SM[0]));
  if (fam == AF_INET) { struct sockaddr_in *x = (void *)&SA[NIF], *y = (void *)&SM[NIF]; x->sin_family = y->sin_family = AF_INET; inet_pton(AF_INET, a, &x->sin_addr); inet_pton(AF_INET, m, &y->sin_addr); }
  else { struct sockaddr_in6 *x = (void *)&SA[NIF], *y = (void *)&SM[NIF]; x->sin6_family = y->sin6_family = AF_INET6; inet_pton(AF_INET6, a, &x->sin6_addr); inet_pton(AF_INET6, m, &y->sin6_addr); }
  i->ifa_name = (char *)name; i->ifa_addr = (void *)&SA[NIF]; i->ifa_netmask = (void *)&SM[NIF]; i->ifa_next = NULL;
  if (NIF) IF[NIF - 1].ifa_next = i;
  NIF++;
}
static int getifaddrs(struct ifaddrs **p) { *p = &IF[0]; return 0; }
static void freeifaddrs(struct ifaddrs *p) { (void)p; }
static long UP; static long uptime(void) { return UP; }
static size_t t_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
#define strlcpy t_strlcpy
#define websWrite(s, ...) fprintf(s, __VA_ARGS__)
''' + dev_t + r'''
int main(int argc, char **argv) {
  addif("lo", AF_INET, "127.0.0.1", "255.0.0.0");
  addif("eth0", AF_INET, "203.0.113.45", "255.255.255.0");
  addif("br0", AF_INET, "192.168.50.1", "255.255.255.0");
  addif("br0", AF_INET6, "fd5a:1b2c:3d4e::1", "ffff:ffff:ffff:ffff::");
  addif("br0", AF_INET6, "fe80::1", "ffff:ffff:ffff:ffff::");
  addif("br52", AF_INET, "10.20.0.1", "255.255.255.0");
  addif("eth0", AF_INET6, "fe80::99", "ffff:ffff:ffff:ffff::");
  UP = atol(argv[1]); renc_devices(stdout, argv[2]); printf("\n");
  if (argc > 4) { FILE *f = fopen(argv[3], "w"); fputs(argv[4], f); fclose(f); UP = atol(argv[5]); renc_devices(stdout, argv[2]); printf("\n"); UP = atol(argv[6]); renc_devices(stdout, argv[2]); printf("\n"); }
  return 0; }
'''
x2, err = build("httpd", HT)
check("httpd: the real functions compile on the host", x2 is not None, err)
def row(fam, proto, src, dst, sport, dport):
    return "%s     2 %s      17 25 src=%s dst=%s sport=%d dport=%d src=%s dst=%s sport=%d dport=%d mark=0 use=1\n" % (fam, proto, src, dst, sport, dport, dst, src, dport, sport)
rows = [
    row("ipv4", "udp", "192.168.50.23", "192.168.50.1", 40000, 53),                      # a LAN device asking the router
    row("ipv4", "tcp", "192.168.50.31", "192.168.50.1", 40001, 443),                     # DNS-over-HTTPS: not plain
    row("ipv4", "udp", "192.168.50.1", "9.9.9.9", 40002, 53),                            # the router's LAN address
    row("ipv4", "udp", "203.0.113.45", "9.9.9.9", 40003, 53),                            # the router's WAN address
    row("ipv4", "udp", "198.51.100.7", "203.0.113.45", 40004, 53),                       # from outside
    row("ipv6", "udp", "fd5a:1b2c:3d4e:0000:0000:0000:0000:0042", "fd5a:1b2c:3d4e:0000:0000:0000:0000:0001", 40005, 53),
    row("ipv4", "udp", "192.168.50.23", "192.168.50.1", 40006, 53),                      # the same device again
    row("ipv4", "tcp", "10.20.0.9", "8.8.8.8", 40007, 53),                               # a guest device, DNS to an outside server
    row("ipv4", "udp", "192.168.50.40", "224.0.0.251", 5353, 5353),                      # mDNS
    row("ipv4", "udp", "192.168.50.60", "1.1.1.1", 53, 40008),                           # dport=53 only in the reply half
    "ipv4     2 udp      17 25 src=192.168.50.99\"<x> dst=192.168.50.1 sport=1 dport=53 src=1.1.1.1\n",   # not an address
    row("ipv4", "udp", "127.0.0.1", "127.0.1.1", 40009, 53),                             # dnsmasq to the forwarder
    row("ipv4", "udp", "192.168.50.61", "192.168.50.1", 40010, 530),                     # port 530
    row("ipv6", "udp", "fe80:0000:0000:0000:0000:0000:0000:0099", "ff02:0000:0000:0000:0000:0000:0000:0002", 40011, 53),   # the router's own WAN link-local
    row("ipv6", "udp", "fe80:0000:0000:0000:0000:0000:0000:0abc", "fe80:0000:0000:0000:0000:0000:0000:0001", 40012, 53),   # a device's link-local
]
open(ct, "w").write("".join(rows))
open(os.path.join(ld, "dnsmasq.leases"), "w").write(
    "1731300000 aa:bb:cc:dd:ee:01 192.168.50.23 Nathans-iPhone 01:aa:bb:cc:dd:ee:01\n"
    "1731300000 aa:bb:cc:dd:ee:02 192.168.50.31 DESKTOP-WIN11 *\n"
    "1731300000 aa:bb:cc:dd:ee:03 192.168.50.50 not-listed *\n"
    "1731300000 aa:bb:cc:dd:ee:04 192.168.50.40 * *\n"
    "duid 00:01:00:01:2a:2b:2c:2d:aa:bb:cc:dd:ee:ff\n"
    "1731300000 1234567 fd5a:1b2c:3d4e::42 ipad6 00:01:00:01\n")
open(os.path.join(ld, "dnsmasq-52.leases"), "w").write("1731300000 aa:bb:cc:dd:ee:05 10.20.0.9 <b>x</b> *\n")
open(os.path.join(ld, "dnsmasq.conf"), "w").write("1731300000 aa:bb:cc:dd:ee:06 192.168.50.23 WRONG-FILE *\n")
ST = '{"clients":[{"a":"192.168.50.31","proto":"doh","q":1,"last":1}]}'
out = subprocess.run([x2, "100", ST, ct, row("ipv4", "udp", "192.168.50.77", "192.168.50.1", 1, 53), "105", "111"],
                     capture_output=True, text=True).stdout.split("\n") if x2 else ["", "", ""]
def parse(s):
    try: return json.loads("{" + s.lstrip(",") + "}")
    except Exception as e: return {"err": str(e), "raw": s}
j1, j2, j3 = parse(out[0]), parse(out[1]), parse(out[2])
check("httpd: the output is valid JSON members", "err" not in j1, j1)
check("httpd: plain = the LAN device, the IPv6 device in short form, the guest device, the link-local device - each once, nothing else",
      j1.get("plain") == ["192.168.50.23", "fd5a:1b2c:3d4e::42", "10.20.0.9", "fe80::abc"], j1.get("plain"))
check("httpd: names for a plain device, an encrypted peer and the IPv6 device; none for an unlisted lease",
      j1.get("names") == {"192.168.50.23": "Nathans-iPhone", "192.168.50.31": "DESKTOP-WIN11", "fd5a:1b2c:3d4e::42": "ipad6"}, j1.get("names"))
check("httpd: a lease name with markup characters is dropped, not printed", "<" not in out[0] and "10.20.0.9" not in (j1.get("names") or {}))
check("httpd: within 10 seconds the connection table is not read again", j2.get("plain") == j1.get("plain"), j2.get("plain"))
check("httpd: after 10 seconds it is", j3.get("plain") == ["192.168.50.77"], j3.get("plain"))
h = cut(web, "do_reaper_encdns_cgi(char *url, FILE *stream)", "\n}\n")
check("httpd: the handler prints the device data after rednsd's own text", 0 < h.find('"{\\"st\\":%s') < h.find("renc_devices(stream, st);"))

# ------------------------------------------------------------------ page and language packs
pg = rd(os.path.join(SRC, "www", "Reaper_EncryptedDNS.asp"))
check("page: ASCII only", all(ord(c) < 128 for c in pg))
for needle, what in [
    ('id="tgdoh"', "the DNS-over-HTTPS switch"),
    ('<input type="hidden" name="reaper_doh_srv" value="">', "its form field"),
    ('<input type="hidden" name="dnspriv_enable" value="1" disabled>', "the upstream switch is posted only when enabled for one Save"),
    ('id="leg_dev"', "the device-to-router line"), ('id="leg_up"', "the router-to-upstream line"),
    (".leg.bad{color:var(--crimson)", "a failing leg is red"),
    ('id="dv_list"', "the device list"), ('id="d_doh_url"', "the address to paste"), ('id="appledl2"', "the Apple HTTPS profile"),
    ("(doh ? 'HTTPS' : 'TLS')", "the profile's protocol"), ("'/dns-query</string>'", "the profile's ServerURL"),
    ("UP && !UP.on && UP.servers > 0 && confirm(", "the upstream leg is offered only when a server is set, and asked"),
    ("sv.push('restart_stubby'); sv.push('restart_wan_dns 0');", "the services of the upstream leg"),
    ("if(srvChg || f.reaper_doh_block.value", "the firewall follows the server switches"),
]:
    check("page: " + what, needle in pg, needle)
sv = cut(pg, "function encSave(){", "\n}\n")
check("page: the upstream field is disabled again at the start of every Save", sv.find("f.dnspriv_enable.disabled = true;") < sv.find("f.dnspriv_enable.disabled = false;") and "f.dnspriv_enable.disabled = true;" in sv)
legs = cut(pg, "function encLegs(j, st, running){", "\n}\n"); devs = cut(pg, "function encDevs(j, st){", "\n}\n")
check("page: status and device text is set as text, never as markup", "innerHTML" not in legs and "innerHTML" not in devs and "innerHTML" not in sv)
check("page: every upstream failure has its own red text",
      all(("<#RENC_%d#>" % n) in legs for n in (84, 85, 86, 87, 88, 89)) and legs.count("'bad'") + legs.count("leg bad") >= 9, legs.count("bad"))
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if os.path.basename(p) != "temp.dict")
check("packs: 25 language packs", len(packs) == 25, len(packs))
used = sorted(set(int(m) for m in __import__("re").findall(r"<#RENC_(\d+)#>", pg)))
check("page: uses the new strings 70..102", all(n in used for n in range(70, 103)), [n for n in range(70, 103) if n not in used])
bad = []
for p in packs:
    b = open(p, "rb").read()
    keys = set(int(m) for m in __import__("re").findall(rb"(?m)^RENC_(\d+)=.", b))
    miss = [n for n in used if n not in keys]
    if miss or b"`" in b"".join(l for l in b.split(b"\n") if l.startswith(b"RENC_")) or b"${" in b"".join(l for l in b.split(b"\n") if l.startswith(b"RENC_")):
        bad.append((os.path.basename(p), miss[:5]))
check("packs: every string the page uses exists in every pack, none with a backtick or ${ (they sit in template literals)", not bad, bad)
en = open(os.path.join(SRC, "www", "EN.dict"), "rb").read()
check("packs: the page no longer says the router does not offer DNS-over-HTTPS", b"which this router does not offer" not in en)
for n in (74, 81, 84, 96, 99):
    line = [l for l in en.split(b"\n") if l.startswith(b"RENC_%d=" % n)]
    check("packs: RENC_%d keeps its %%1 placeholder" % n, len(line) == 1 and b"%1" in line[0], line)

# ------------------------------------------------------------------ automatic setup: DHCP option 162 (RFC 9463)
# WHY: a device that supports the option switches to the router's encrypted DNS by itself. It authenticates the
# NAME in the option, so the option is published only with a publicly trusted certificate, and only on networks
# whose DNS server is the router. A malformed option line would stop dnsmasq - and with it DHCP and DNS.
dnr = cut(enc, "#define RED_DNR", "void stop_rednsd(void)")
check("dnr: the code is found", "rednsd_dnr_option" in dnr and "red_dnr_sync" in dnr)
OSSL = shutil.which("openssl")
have_ssl = subprocess.run([CC, "-x", "c", "-", "-o", os.path.join(tmp, "probe"), "-lcrypto"], input="#include <openssl/x509v3.h>\nint main(void){return 0;}\n",
                          capture_output=True, text=True).returncode == 0
if not OSSL or not have_ssl:
    print("skip dnr run: no openssl command or no OpenSSL headers on this host")
else:
    pk = os.path.join(tmp, "pki"); os.mkdir(pk)
    def ossl(*a):
        return subprocess.run([OSSL] + list(a), capture_output=True, text=True, cwd=pk)
    def ca(n):
        # the stock openssl.cnf already makes a req -x509 certificate a CA (a second basicConstraints would break it)
        ossl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", n + ".key", "-out", n + ".pem", "-days", "30", "-subj", "/CN=Test CA " + n)
    def usable(n):
        return ossl("verify", "-CAfile", "good.pem", n + ".pem").returncode == 0
    def leaf(n, signer, san, days="30"):
        open(os.path.join(pk, n + ".ext"), "w").write("subjectAltName=" + san + "\n")
        ossl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", n + ".key", "-out", n + ".csr", "-subj", "/CN=leaf")
        return ossl("x509", "-req", "-in", n + ".csr", "-CA", signer + ".pem", "-CAkey", signer + ".key", "-CAcreateserial", "-out", n + ".pem",
                    "-days", days, "-extfile", n + ".ext")
    ca("good"); ca("other")
    leaf("ok", "good", "DNS:*.wild.example.net,DNS:router.example.org,DNS:myhome.asuscomm.com")
    leaf("stranger", "other", "DNS:myhome.asuscomm.com")
    leaf("wildonly", "good", "DNS:*.example.net")
    ossl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "self.key", "-out", "self.pem", "-days", "30", "-subj", "/CN=self",
         "-addext", "subjectAltName=DNS:myhome.asuscomm.com")
    leaf("old", "good", "DNS:myhome.asuscomm.com", days="-1")
    expired = ossl("x509", "-in", "old.pem", "-noout", "-checkend", "0").returncode != 0
    check("dnr: the test's own certificate chain is sound (openssl verify)", usable("ok") and not usable("stranger") and not usable("self"))
    P = lambda n: os.path.join(pk, n).replace("\\", "/")
    DH = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <sys/stat.h>
#include <arpa/inet.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#define RED_PORT 853
#define RED_DOH_PORT 443
#define RED_DIR "%(dir)s"
#define RED_CABUNDLE "%(ca)s"
static const char *RED_CERT, *RED_KEY;
static int NA; static char **NV;
static const char *nvram_safe_get(const char *k) { int i; size_t l = strlen(k); for (i = 1; i < NA; i++) if (!strncmp(NV[i], k, l) && NV[i][l] == '=') return NV[i] + l + 1; return ""; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int ipv6_enabled(void) { return nvram_get_int("t_ipv6"); }	/* review 2026-11-11 (C-6) */
static int f_exists(const char *p) { struct stat sb; return stat(p, &sb) == 0; }
static int f_read_string(const char *p, char *b, int max) { FILE *f = fopen(p, "r"); size_t n; if (!f) return -1; n = fread(b, 1, max - 1, f); b[n] = 0; fclose(f); return (int)n; }
static int reaper_secure_dir(const char *p, mode_t m) { (void)p; (void)m; return 0; }
static int reaper_write_atomic(const char *p, const void *d, size_t l, mode_t m) { FILE *f = fopen(p, "w"); (void)m; if (!f) return -1; fwrite(d, 1, l, f); fclose(f); return 0; }
static int pids(const char *n) { (void)n; return nvram_get_int("t_dnsmasq"); }
static int RESTARTS;
static void stop_dnsmasq(void) { }
static void start_dnsmasq(void) { RESTARTS++; }
#define logmessage(tag, ...) (printf("log: " __VA_ARGS__), printf("\n"))
static int red_enabled(void) { return nvram_get_int("t_enabled"); }
static long UP = 1000;	/* review 2026-11-11 (C-8): red_public_name tries an unverified chain again after a minute */
static long uptime(void) { return UP; }
struct rb { char b[8]; };
static void rb_add(struct rb *r, const char *fmt, ...) { (void)r; (void)fmt; }
''' % {"dir": tmp.replace("\\", "/"), "ca": P("good.pem")} + rcfn + dnr + r'''
int main(int argc, char **argv) {
  NA = argc; NV = argv; RED_CERT = nvram_safe_get("t_cert"); RED_KEY = nvram_safe_get("t_key");
  if (!strcmp(argv[1], "m=opt")) { rednsd_dnr_option(stdout, nvram_safe_get("t_tag"), nvram_safe_get("t_addr")); rednsd_dnr_option(stdout, "br52", "10.20.0.1"); }
  if (!strcmp(argv[1], "m=sync")) { red_dnr_sync(); printf("restarts=%%d\n", RESTARTS); red_dnr_sync(); printf("restarts=%%d\n", RESTARTS); }
  if (!strcmp(argv[1], "m=mark")) rednsd_dnr_mark();
  if (!strcmp(argv[1], "m=retry")) {	/* the CA bundle is away for the first look, back for the second and third */
    char away[512], nm[256]; int a, b, c;
    snprintf(away, sizeof(away), "%s.away", RED_CABUNDLE);
    if (rename(RED_CABUNDLE, away) != 0) { printf("retry setup failed\n"); return 1; }
    a = red_public_name(nm, sizeof(nm));
    rename(away, RED_CABUNDLE);
    b = red_public_name(nm, sizeof(nm));
    UP += 61; c = red_public_name(nm, sizeof(nm));
    printf("retry %%d %%d %%d %%s\n", a, b, c, nm);
  }
  return 0; }
'''.replace("%%", "%")
    x3, err = build("dnrtest", DH, ["-lcrypto"])   # not "dnr": that is the state file's name in this folder
    check("dnr: the real functions compile against OpenSSL on the host", x3 is not None, err)
    def run(mode, cert, *kv):
        base = ["m=" + mode, "t_cert=" + P(cert + ".pem"), "t_key=" + P(cert + ".key"), "t_enabled=1", "t_tag=lan", "t_addr=192.168.50.1",
                "reaper_dot_srv=1", "reaper_doh_srv=1", "http_enable=2", "https_lanport=8443"]
        keys = set(k.split("=")[0] for k in kv)
        argv = [x3, base[0]] + list(kv) + [b for b in base[1:] if b.split("=")[0] not in keys]   # a value given by the case wins
        return subprocess.run(argv, capture_output=True, text=True).stdout if x3 else ""
    def decode(line):
        """one dhcp-option line -> (tag, [instances]) by RFC 9463 section 5.1"""
        head, _, hx = line.rpartition(",")
        if not hx.strip(): return head, [], 0
        b = bytes(int(h, 16) for h in hx.split(":")); out = []; i = 0
        while i < len(b):
            ln = int.from_bytes(b[i:i + 2], "big"); inst = b[i + 2:i + 2 + ln]; i += 2 + ln
            prio = int.from_bytes(inst[0:2], "big"); al = inst[2]; adn = inst[3:3 + al]; k = 3 + al
            labels = []; q = 0
            while adn[q]: labels.append(adn[q + 1:q + 1 + adn[q]].decode()); q += 1 + adn[q]
            ok_adn = (q == len(adn) - 1)
            addrl = inst[k]; addrs = inst[k + 1:k + 1 + addrl]; k += 1 + addrl
            sv = {}; order = []
            while k < len(inst):
                key = int.from_bytes(inst[k:k + 2], "big"); vl = int.from_bytes(inst[k + 2:k + 4], "big"); sv[key] = inst[k + 4:k + 4 + vl]; order.append(key); k += 4 + vl
            out.append({"prio": prio, "name": ".".join(labels), "adn_ok": ok_adn, "addr": ".".join(str(c) for c in addrs), "svc": sv, "order": order, "exact": k == len(inst)})
        return head, out, len(b)
    o = run("opt", "ok", "ddns_hostname_x=MyHome.ASUSCOMM.com").strip().split("\n")
    check("dnr: one option line per network, in dnsmasq's hex form", len(o) == 2 and o[0].startswith("dhcp-option=lan,162,") and o[1].startswith("dhcp-option=br52,162,")
          and all(c in "0123456789abcdef:" for c in o[0].split(",")[2]), o)
    head, ins, total = decode(o[0]) if len(o) == 2 else ("", [], 0)
    check("dnr: two instances that end exactly where their length says, option within 255 bytes", len(ins) == 2 and all(i["exact"] and i["adn_ok"] for i in ins) and total <= 255, (ins, total))
    if len(ins) == 2:
        check("dnr: the name is the DDNS name the certificate covers, lower case", ins[0]["name"] == ins[1]["name"] == "myhome.asuscomm.com", ins[0]["name"])
        check("dnr: the address is the router's address on that network", ins[0]["addr"] == ins[1]["addr"] == "192.168.50.1" and decode(o[1])[1][0]["addr"] == "10.20.0.1")
        check("dnr: DNS-over-HTTPS first (priority 1): alpn h2 and the path, keys ascending, no address hints",
              ins[0]["prio"] == 1 and ins[0]["svc"] == {1: b"\x02h2", 7: b"/dns-query{?dns}"} and ins[0]["order"] == [1, 7], ins[0])
        check("dnr: DNS-over-TLS second (priority 2): alpn dot, default port", ins[1]["prio"] == 2 and ins[1]["svc"] == {1: b"\x03dot"}, ins[1])
    o2 = run("opt", "ok", "ddns_hostname_x=elsewhere.example.com").strip().split("\n")
    check("dnr: a DDNS name the certificate does not cover: its first plain name, never the wildcard",
          len(o2) == 2 and decode(o2[0])[1][0]["name"] == "router.example.org", o2)
    check("dnr: DNS-over-HTTPS port busy: only the DNS-over-TLS instance", [i["prio"] for i in decode(run("opt", "ok", "https_lanport=443").split("\n")[0])[1]] == [2])
    check("dnr: DNS-over-TLS off: only the DNS-over-HTTPS instance", [i["prio"] for i in decode(run("opt", "ok", "reaper_dot_srv=0").split("\n")[0])[1]] == [1])
    check("dnr: nothing while the server is off", run("opt", "ok", "t_enabled=0") == "")
    check("dnr: nothing for a self-signed certificate", run("opt", "self") == "")
    check("dnr: nothing for a certificate from a CA the router does not trust", run("opt", "stranger") == "")
    check("dnr: nothing when the certificate has only a wildcard name and the DDNS name is not under it", run("opt", "wildonly", "ddns_hostname_x=a.b.example.net") == "")
    check("dnr: a wildcard certificate that covers the DDNS name publishes the DDNS name",
          decode(run("opt", "wildonly", "ddns_hostname_x=home.example.net").split("\n")[0])[1][0]["name"] == "home.example.net")
    check("dnr: nothing without the key file", run("opt", "ok", "t_key=/nonexistent") == "")
    # review 2026-11-11 (C-8): a chain that could not be verified (the CA bundle unreadable at that moment) is not
    # remembered for good: not asked again within the minute, verified on the first look after it
    rr = run("retry", "ok", "ddns_hostname_x=myhome.asuscomm.com")
    check("dnr: an unverified chain is tried again after a minute, not before", rr.startswith("retry 0 0 1 "), rr)
    check("dnr: an address that is not IPv4 writes nothing for that network only", run("opt", "ok", "t_addr=fe80::1").strip().startswith("dhcp-option=br52,162,"))
    if expired:
        check("dnr: a certificate that has run out is not published once the clock is set", run("opt", "old", "ntp_ready=1") == "")
        check("dnr: before the clock is set the chain alone decides (as rednsd judges it)", run("opt", "old", "ntp_ready=0").startswith("dhcp-option=lan,162,"))
    else:
        print("skip dnr expiry: this openssl could not make an expired test certificate")
    st = os.path.join(tmp, "dnr")
    if os.path.exists(st): os.remove(st)
    r = run("sync", "ok", "t_dnsmasq=1", "ddns_hostname_x=myhome.asuscomm.com")
    check("dnr: a change restarts dnsmasq once, then nothing more", "restarts=1\nrestarts=1\n" in r and "is offered" in r, r)
    check("dnr: the record holds the name and the two protocols", open(st).read() == "myhome.asuscomm.com 1 1")
    r = run("sync", "ok", "t_dnsmasq=1", "ddns_hostname_x=myhome.asuscomm.com", "reaper_doh_srv=0")
    check("dnr: switching one protocol off is a change", "restarts=1" in r and open(st).read() == "myhome.asuscomm.com 1 0", r)
    r = run("sync", "self", "t_dnsmasq=0")
    check("dnr: with dnsmasq not running nothing is restarted (its next start writes the record)", "restarts=0\nrestarts=0\n" in r, r)
    r = run("sync", "self", "t_dnsmasq=1")
    check("dnr: losing the trusted certificate withdraws the option", "is withdrawn" in r and "restarts=1\nrestarts=1" in r and open(st).read() == "", r)
    run("mark", "ok", "ddns_hostname_x=myhome.asuscomm.com")
    check("dnr: the end of a dnsmasq start records what it published", open(st).read() == "myhome.asuscomm.com 1 1")
    # the option line through a real dnsmasq parser, when this host has one
    dm = shutil.which("dnsmasq")
    if dm and len(o) == 2:
        cf = os.path.join(tmp, "dm.conf"); open(cf, "w").write("port=0\ndhcp-range=lan,192.168.50.2,192.168.50.254,255.255.255.0,86400s\n" + o[0] + "\n")
        t = subprocess.run([dm, "--test", "-C", cf], capture_output=True, text=True)
        check("dnr: dnsmasq accepts the option line", t.returncode == 0, t.stderr)
    else:
        print("skip dnr parser run: no dnsmasq on this host")
srv = rd(os.path.join(SRC, "rc", "services.c")); sdn = rd(os.path.join(SRC, "rc", "sdn.c"))
a = srv.find('"dhcp-option=lan,6%s%s%s%s%s\\n"'); b = srv.find('rednsd_dnr_option(fp, "lan", lan_ipaddr);')
check("dnr: the LAN gets it only in the else of 'custom DNS servers for clients'", 0 < a < b and b - a < 700 and "else" in srv[a:b] and srv[a:b].count(";") == 1, (a, b))
a = sdn.find('fprintf(fp, "dhcp-option=%s,6,%s\\n", pmtl->nw_t.ifname, pmtl->nw_t.dns[1]);', sdn.find("else if(pmtl->nw_t.dns[1][0] != '\\0')"))
b = sdn.find("rednsd_dnr_option(fp, pmtl->nw_t.ifname, pmtl->nw_t.addr);")
check("dnr: a guest network gets it only when it has no DNS server of its own", 0 < a < b and b - a < 300 and "else" in sdn[a:b], (a, b))
check("dnr: start_dnsmasq records the published state before the refresh", 0 < srv.find("rednsd_dnr_mark();") < srv.find("rednsd_refresh();", srv.find("rednsd_dnr_mark();")))
check("dnr: the restart uses calls that exist on every platform (restart_dnsmasq() is not linked on this one)", "restart_dnsmasq(0)" not in dnr and "stop_dnsmasq(ALL_SDN);" in dnr and "start_dnsmasq(ALL_SDN);" in dnr)
check("dnr: both entry points of the server end with the check", "void start_rednsd(void)\n{\n\tred_start();\n\tred_dnr_sync();\n}" in enc and "void rednsd_refresh(void)\n{\n\tred_refresh();\n\tred_dnr_sync();\n}" in enc)
check("dnr: the resolver.arpa record is not published (its verified mode cannot pass on a LAN address)", "dns-rr" not in enc)
check("dnr: httpd reports the offered name from rc's file, letters digits dot dash only", '"/tmp/rednsd/dnr"' in h and "\\\"dnr\\\":\\\"%s\\\"" in h and "isalnum" in h[h.find('"/tmp/rednsd/dnr"'):h.find('"/tmp/rednsd/dnr"') + 400])
check("dnr: the page shows it", 'id="leg_auto"' in pg and "j.dnr" in pg and "<#RENC_104#>" in pg and "<#RENC_105#>" in pg)

shutil.rmtree(tmp, ignore_errors=True)
print("\n%d failed" % len(fails) if fails else "\nall passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
