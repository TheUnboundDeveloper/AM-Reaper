#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DNS Health Check under DNS-over-TLS (owner, 2026-11-10: "when DoT is enabled it moves the health check to DoT if
possible").

WHY THIS EXISTS. The DNS Health Check (rc/rdnshc.c) asked its server a plain question on port 53 every few
seconds. With DNS-over-TLS on, those were the only plain DNS packets leaving the router, and the failover it drives
(moving the server's line in /tmp/resolv.dnsmasq) means nothing then: the router's DNS list holds the DNS-over-TLS
forwarder alone. Now, while DNS-over-TLS is on (the same test rc/wan.c uses for the router's own lookups), the check
asks the watched server over DNS-over-TLS when it is one of the DNS-over-TLS servers - TLS on the row's port, the
certificate checked against the row's name - and otherwise asks the DNS-over-TLS forwarder over loopback. It moves
nothing in that mode; state field 6 (p / t / s) tells the DNS Failover page and the diag.

WHAT IT DOES. Compiles the real hc_dot_mode(), dot_ask(), probe_dot() and their helpers against the host's OpenSSL,
decides the mode for a table of DNS-over-TLS settings, asks a local TLS DNS server (certificate from a test CA,
right name / wrong name / no name / silent / not listening) and a local forwarder; pins the main loop (no failover,
reload or gate under DNS-over-TLS); renders the page's status in node; runs the diag's lines in sh.

Exit 0 pass, 1 fail, 77 skipped (no router source tree, no compiler, no OpenSSL headers)."""
import json, os, re, shutil, socket, ssl, subprocess, sys, tempfile, threading, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
HC = os.path.join(SRC, "rc", "rdnshc.c") if SRC else ""
if not HC or not os.path.isfile(HC):
    skip("no router source tree with rc/rdnshc.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
OSSL = shutil.which("openssl")
if not CC or not OSSL:
    skip("no host C compiler or openssl command")
tmp = tempfile.mkdtemp(prefix="dnshcdot-")
if subprocess.run([CC, "-x", "c", "-", "-o", os.path.join(tmp, "p"), "-lssl", "-lcrypto"], input="#include <openssl/ssl.h>\nint main(void){return 0;}\n",
                  capture_output=True, text=True).returncode != 0:
    skip("no OpenSSL development headers on this host")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
def cut(text, start, end):
    a = text.find(start); b = text.find(end, a + 1) if a >= 0 else -1
    return text[a:b] if 0 <= a < b else ""

src = rd(HC)
dot = cut(src, "/* DNSHC-DOT-BEGIN", "/* DNSHC-DOT-END */")
cfg = cut(src, "struct hc_cfg {", "\n};\n") + "\n};\n"
dns = cut(src, "static int dns_build(unsigned char *pkt", "static int probe_addr(")
check("rdnshc: the DNS-over-TLS block, the config and the DNS helpers are found", bool(dot) and "int strict" in cfg and "static int dns_ask(" in dns)

# ------------------------------------------------------------------ a test CA, a server certificate for dot.test
pk = os.path.join(tmp, "pki"); os.mkdir(pk)
def ossl(*a): return subprocess.run([OSSL] + list(a), capture_output=True, text=True, cwd=pk)
ossl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.pem", "-days", "2", "-subj", "/CN=Test CA")
open(os.path.join(pk, "s.ext"), "w").write("subjectAltName=DNS:dot.test\n")
ossl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "s.key", "-out", "s.csr", "-subj", "/CN=dot.test")
ossl("x509", "-req", "-in", "s.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial", "-out", "s.pem", "-days", "2", "-extfile", "s.ext")
check("test: the test certificate chains to the test CA", ossl("verify", "-CAfile", "ca.pem", "s.pem").returncode == 0)

def free_port(kind=socket.SOCK_STREAM):
    s = socket.socket(socket.AF_INET, kind); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
FWD_PORT = free_port(socket.SOCK_DGRAM)

H = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <ctype.h>
#include <poll.h>
#include <time.h>
#include <unistd.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#define HC_FWD "127.0.0.1"
#define HC_FWD_PORT %(fport)d
#define HC_CABUNDLE "%(ca)s"
#define HC_DOT_MULT 3
static volatile int g_stop;
static int NA; static char **NV;
static const char *nvram_safe_get(const char *k) { int i; size_t l = strlen(k); for (i = 1; i < NA; i++) if (!strncmp(NV[i], k, l) && NV[i][l] == '=') return NV[i] + l + 1; return ""; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int is_routing_enabled(void) { return nvram_get_int("t_routing"); }
static int ipv6_enabled(void) { return nvram_get_int("t_ipv6"); }
static int hc_v6_usable(void) { return nvram_get_int("t_v6usable"); }
static int safe_atoi(const char *s) { return atoi(s); }
static long now_s(void) { return (long)time(NULL); }
static size_t t_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
#define strlcpy t_strlcpy
static int vstrsep(char *buf, const char *sep, ...) { va_list ap; char **p; int n = 0; va_start(ap, sep); while ((p = va_arg(ap, char **)) != NULL) { if (!buf) break; *p = strsep(&buf, sep); n++; } va_end(ap); return n; }
#define vstrsep(b, s, ...) vstrsep(b, s, __VA_ARGS__, NULL)
''' % {"fport": FWD_PORT, "ca": os.path.join(pk, "ca.pem")} + cfg + dns + dot + r'''
int main(int argc, char **argv) {
  struct hc_dot d; struct hc_cfg c; int m, an = 0, rc; struct timespec a, b;
  NA = argc; NV = argv;
  m = hc_dot_mode(nvram_safe_get("t_target"), nvram_safe_get("t_alt"), &d);
  printf("mode=%c addr=%s port=%d host=%s\n", m, d.addr, d.port, d.host);
  if (!strcmp(argv[1], "probe")) {
    memset(&c, 0, sizeof(c)); strcpy(c.name, "probe.test"); c.timeout_ms = nvram_get_int("t_timeout"); c.strict = nvram_get_int("t_strict");
    clock_gettime(CLOCK_MONOTONIC, &a);
    rc = (m == 't') ? dot_ask(&d, c.name, c.timeout_ms * HC_DOT_MULT, &an) : -2;
    printf("ask=%d an=%d probe=%d", rc, an, (m == 't' || m == 's') ? probe_dot(&c, m, &d) : -1);
    clock_gettime(CLOCK_MONOTONIC, &b);
    printf(" ms=%ld\n", (long)((b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000));
  }
  return 0; }
'''
cf = os.path.join(tmp, "h.c"); xf = os.path.join(tmp, "h")
open(cf, "w").write(H)
r = subprocess.run([CC, "-O1", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-Wno-unused-parameter", "-o", xf, cf, "-lssl", "-lcrypto"], capture_output=True, text=True)
check("rdnshc: the real DNS-over-TLS code compiles on the host with warnings as errors", r.returncode == 0, r.stderr)
if r.returncode != 0:
    shutil.rmtree(tmp, ignore_errors=True); print("\n%d failed" % len(fails))
    for f in fails: print("  " + f)
    sys.exit(1)

def run(mode, **kv):
    base = {"dnspriv_enable": "1", "t_routing": "1", "t_ipv6": "0", "t_v6usable": "0", "t_target": "1.1.1.3", "t_alt": "", "t_timeout": "500", "t_strict": "0"}
    base.update(kv)
    return subprocess.run([xf, mode] + ["%s=%s" % kv_ for kv_ in base.items()], capture_output=True, text=True, timeout=60).stdout
ROW_CF = "<1.1.1.3>853>family.cloudflare-dns.com><1.0.0.3>>family.cloudflare-dns.com>"
o = run("mode", dnspriv_rulelist=ROW_CF)
check("mode: DNS-over-TLS on and the watched server is a DoT server - asked over DNS-over-TLS on its port, with its name",
      "mode=t addr=1.1.1.3 port=853 host=family.cloudflare-dns.com" in o, o)
check("mode: the second row, with an empty port - port 853", "mode=t addr=1.0.0.3 port=853 host=family.cloudflare-dns.com" in run("mode", dnspriv_rulelist=ROW_CF, t_target="1.0.0.3"))
check("mode: a watched server that is not a DoT server - the forwarder", "mode=s addr= " in run("mode", dnspriv_rulelist=ROW_CF, t_target="192.168.50.98"))
check("mode: DNS-over-TLS switched off - port 53 as before", "mode=p" in run("mode", dnspriv_rulelist=ROW_CF, dnspriv_enable="0"))
check("mode: not in router mode - port 53 as before", "mode=p" in run("mode", dnspriv_rulelist=ROW_CF, t_routing="0"))
check("mode: switched on but no row with an address (the router's own lookups stay plain too) - port 53", "mode=p" in run("mode", dnspriv_rulelist="<>853>x.test>"))
check("mode: a row with a port of its own", "port=8853" in run("mode", dnspriv_rulelist="<1.1.1.3>8853>dot.test>"))
check("mode: a short row (fewer than 4 fields) is skipped, as rc/wan.c skips it", "mode=p" in run("mode", dnspriv_rulelist="<1.1.1.3>853>dot.test"))
check("mode: a name with a character outside a host name is not used (no name to check)", "mode=t addr=1.1.1.3 port=853 host=\n" in run("mode", dnspriv_rulelist="<1.1.1.3>853>bad name>"))
V6 = "<2606:4700:4700::1113>853>family.cloudflare-dns.com>"
check("mode: only an IPv6 row while IPv6 is off - DNS-over-TLS is not in use for the router, port 53", "mode=p" in run("mode", dnspriv_rulelist=V6, t_target="2606:4700:4700::1113"))
check("mode: IPv6 on but not usable now - DoT is on, the IPv6 server is not asked directly, the forwarder is",
      "mode=s" in run("mode", dnspriv_rulelist=V6, t_target="2606:4700:4700::1113", t_ipv6="1"))
check("mode: the IPv6 address (target6) matches a usable IPv6 row - asked over DNS-over-TLS, canonical spelling",
      "mode=t addr=2606:4700:4700::1113" in run("mode", dnspriv_rulelist=V6, t_alt="2606:4700:4700::1113", t_ipv6="1", t_v6usable="1"))
check("mode: the address spelling in the row does not matter (canonical compare)",
      "mode=t" in run("mode", dnspriv_rulelist="<2606:4700:4700:0:0:0:0:1113>853>x.test>", t_target="2606:4700:4700::1113", t_ipv6="1", t_v6usable="1"))

# ------------------------------------------------------------------ a TLS DNS server (RFC 7858) for the probe
def dns_answer(q, rcode=0, an=1, wrong_id=False):
    qid = q[0:2] if not wrong_id else bytes([q[0] ^ 0xff, q[1]])
    hdr = qid + bytes([0x81, 0x80 | rcode, 0, 1, 0, an, 0, 0, 0, 0])
    qd = q[12:]
    rr = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04\x7f\x00\x00\x01" if an else b""
    return hdr + qd + rr
class TLSDNS(threading.Thread):
    def __init__(self, cert, key, behave="ok"):
        super().__init__(daemon=True)
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); self.ctx.load_cert_chain(cert, key)
        self.ls = socket.socket(); self.ls.bind(("127.0.0.1", 0)); self.ls.listen(4); self.port = self.ls.getsockname()[1]
        self.behave = behave; self.n = 0; self.stop = False
    def run(self):
        self.ls.settimeout(0.2)
        while not self.stop:
            try: c, _ = self.ls.accept()
            except socket.timeout: continue
            except OSError: return
            try:
                c.settimeout(5); s = self.ctx.wrap_socket(c, server_side=True)
                ln = s.recv(2)
                q = b""
                while len(q) < (ln[0] << 8 | ln[1]): q += s.recv(4096)
                self.n += 1
                if self.behave == "silent": time.sleep(3); s.close(); continue
                a = dns_answer(q, wrong_id=(self.behave == "wrongid"), rcode=3 if self.behave == "nx" else 0, an=0 if self.behave == "nx" else 1)
                s.sendall(bytes([len(a) >> 8, len(a) & 0xff]) + a); s.close()
            except Exception:
                try: c.close()
                except Exception: pass
srv = TLSDNS(os.path.join(pk, "s.pem"), os.path.join(pk, "s.key")); srv.start()
def probe(host, port, **kv):
    return run("probe", dnspriv_rulelist="<127.0.0.1>%d>%s>" % (port, host), t_target="127.0.0.1", **kv)
o = probe("dot.test", srv.port)
check("probe: the server's certificate matches the row's name - an answer over DNS-over-TLS", "ask=0 an=1 probe=1" in o and srv.n >= 1, o)
o = probe("other.test", srv.port)
check("probe: the certificate does not carry the row's name - no answer counted (stubby would refuse it too)", "ask=-1 an=0 probe=0" in o, o)
o = probe("", srv.port)
check("probe: a row without a name - an encrypted answer is enough", "ask=0 an=1 probe=1" in o, o)
o = probe("dot.test", srv.port, t_strict="1")
check("probe: strict and a real answer (NOERROR + a record) - counted", "probe=1" in o, o)
nx = TLSDNS(os.path.join(pk, "s.pem"), os.path.join(pk, "s.key"), "nx"); nx.start()
o = probe("dot.test", nx.port, t_strict="1")
check("probe: strict and NXDOMAIN - not counted; not strict - counted", "ask=3 an=0 probe=0" in o and "probe=1" in probe("dot.test", nx.port), o)
wi = TLSDNS(os.path.join(pk, "s.pem"), os.path.join(pk, "s.key"), "wrongid"); wi.start()
check("probe: a reply with another id - not counted", "ask=-1" in probe("dot.test", wi.port))
si = TLSDNS(os.path.join(pk, "s.pem"), os.path.join(pk, "s.key"), "silent"); si.start()
o = probe("dot.test", si.port, t_timeout="300")
m = re.search(r"ms=(\d+)", o)
check("probe: a server that never answers - not counted, and the wait ends at three times the timeout (two probes here)",
      "ask=-1 an=0 probe=0" in o and m and int(m.group(1)) <= 2 * 3 * 300 + 400, o)
dead = free_port()
o = probe("dot.test", dead)
m = re.search(r"ms=(\d+)", o)
check("probe: nothing listening - not counted, at once", "ask=-1 an=0 probe=0" in o and m and int(m.group(1)) < 500, o)
# the forwarder: a UDP DNS stand-in on loopback
fw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); fw.bind(("127.0.0.1", FWD_PORT)); fw.settimeout(0.2)
got = []
def fwd_loop():
    end = time.time() + 15
    while time.time() < end:
        try: q, a = fw.recvfrom(2048)
        except socket.timeout: continue
        except OSError: return
        got.append(q); fw.sendto(dns_answer(q), a)
threading.Thread(target=fwd_loop, daemon=True).start()
o = run("probe", dnspriv_rulelist=ROW_CF, t_target="192.168.50.98")
check("probe: the watched server is not a DoT server - the DoT forwarder on loopback is asked, and answers",
      "mode=s" in o and "probe=1" in o and len(got) == 1 and b"\x05probe\x04test\x00" in got[0], (o, got))
for t in (srv, nx, wi, si): t.stop = True
fw.close()

# ------------------------------------------------------------------ the main loop
loop = cut(src, "int rdnshc_main(int argc, char *argv[])", "\nvoid stop_rdnshc(void)")
dbl = cut(loop, "\t\tif (dmode != 'p') {\n", "\t\t\tcontinue;\n\t\t}\n")
check("loop: the mode is decided every tick, from the watched address and its IPv6 twin", "dmode = enabled ? hc_dot_mode(c.target, c.alt, &dt) : 'p';" in loop)
check("loop: a demotion left from port-53 mode is undone when DNS-over-TLS comes on",
      "if ((down || fdown[0] || fdown[1]) && (!enabled || strcmp(watched, c.target) != 0 || dmode != 'p')) {" in loop)
check("loop: under DNS-over-TLS the tick probes over DNS-over-TLS and ends before anything is moved",
      "ok = probe_dot(&c, dmode, &dt);" in dbl and not any(x in dbl for x in ("assert_order(", "hc_reload(", "restore(&c", "face_marks(", "hc_gate(", "f_write_string(HC_STATE", "probe_addr("))
      and loop.find("if (dmode != 'p') {") < loop.find("if (v6_ready) ok6 = probe_addr(&c, a6, AF_INET6);"))
check("loop: before the clock is set nothing is counted (no certificate can be judged)", 'if (nvram_get_int("ntp_ready") == 1)' in dbl and "ok < 0 ||" in dbl)
check("loop: a mode change resets the counters and says so in the log", "if (dmode != last_dmode) {" in loop and "DNS-over-TLS is off - %s is asked on port 53 again" in loop)
check("state: a sixth field, the mode", '"%s %ld %d %c %c %c", what, since > 0 ? now_s() - since : 0, alive, g_f4, g_f6, g_dmode' in src)
check("probe: the forwarder is loopback, port 53 on the router", '#define HC_FWD\t\t"127.0.1.1"' in src and "#define HC_FWD_PORT\t53" in src)

# ------------------------------------------------------------------ 2026-11-20 REAPER-UPTLS: the upstream fallback
# WHY: with DNS-over-TLS on, dnsmasq's only upstream is the forwarder (stubby, 127.0.1.1); when it is dead or reaches
# none of its servers every LAN lookup failed and nothing said so. Owner 2026-11-10: the Opportunistic profile falls
# back to plain DNS by itself, comes back by itself, and the page says so in red; Strict never falls back (red only).
# This compiles the real uptls code (rc/rdnshc.c, between UT_EVERY and rdnshc_main) with the real row parser and the
# real servers-file writer (rc/wan.c update_resolvconf / update_resolvconf_plain), drives it with a fake clock and a
# fake forwarder, and checks what it writes, reloads, logs and publishes.
ut_src = cut(src, "#define UT_EVERY", "/* Called once per loop pass; does nothing until a check is due. */")
pure = cut(src, "/* UPTLS-PURE-BEGIN", "/* UPTLS-PURE-END */")
check("uptls: the fallback code and its pure state machine are found", bool(ut_src) and "static int ut_step(" in pure and "uptls_tick" in ut_src)
check("uptls: the pure block calls no firmware function", not any(x in pure for x in ("nvram_", "logmessage", "update_resolvconf", "notify_rc", "f_write", "pids(")))
lup = cut(src, "static int line_is_upstream(const char *line, const char *prefix)", "\n}\n") + "\n}\n"
wan_src = rd(os.path.join(SRC, "rc", "wan.c"))
wsec = cut(wan_src, "#ifdef RTCONFIG_DNSPRIVACY\n/* reaper 2026-11-10: does dnspriv_rulelist", "/* List of IP address blocks which are private")
check("uptls: the servers-file writer and its DNS-over-TLS test are found in rc/wan.c", "int update_resolvconf_plain(void)" in wsec and "static int dot_has_upstream(void)" in wsec)
sim_dir = os.path.join(tmp, "ut"); os.mkdir(sim_dir)
RESOLV = os.path.join(sim_dir, "resolv.conf"); SERVERS = os.path.join(sim_dir, "resolv.dnsmasq"); UTST = os.path.join(sim_dir, "uptls.state")
wsec_t = wsec.replace('"/tmp/resolv.conf"', json.dumps(RESOLV)).replace('"/tmp/resolv.dnsmasq"', json.dumps(SERVERS))
ut_t = ut_src.replace('"/tmp/reaper/uptls.state"', json.dumps(UTST))
dot_t = dot.replace("static int dot_ask(const struct hc_dot *d", "static int real_dot_ask(const struct hc_dot *d").replace(
    "static int hc_dot_row(", "static int dot_ask(const struct hc_dot *d, const char *name, int timeout_ms, int *ancount);\nstatic int hc_dot_row(", 1)
check("uptls: the test redirected the three files", RESOLV in wsec_t and SERVERS in wsec_t and UTST in ut_t and "/tmp/" not in ut_t.replace(UTST, ""))
SIM = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <ctype.h>
#include <poll.h>
#include <time.h>
#include <unistd.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#define RTCONFIG_DNSPRIVACY
#define RTCONFIG_IPV6
#define HC_FWD "127.0.1.1"
#define HC_FWD_PORT 53
#define HC_CABUNDLE "/nonexistent"
#define HC_DOT_MULT 3
#define HC_TAG "rdnshc"
#define HC_LINE 256
#define HC_DNSMASQ "%(servers)s"
#define SERVERS HC_DNSMASQ
#define RESOLV "%(resolv)s"
#define WAN_UNIT_FIRST 0
#define WAN_UNIT_MAX 2
enum { IPV6_DISABLED, IPV6_NATIVE_DHCP, IPV6_OTHER };
static volatile int g_stop;
static long T;			/* the fake clock */
static long now_s(void) { return T; }
/* nvram: a small table; argv sets it, events change it */
static char NK[64][48], NVv[64][256]; static int NN;
static const char *nvram_safe_get(const char *k) { int i; for (i = 0; i < NN; i++) if (!strcmp(NK[i], k)) return NVv[i]; return ""; }
static char *nvram_get_r(const char *k, char *b, size_t n) { snprintf(b, n, "%%s", nvram_safe_get(k)); return b; }
#define nvram_safe_get_r(name, buf, bufsize) (nvram_get_r(name, buf, bufsize) ? : "")
static int nvram_set(const char *k, const char *v) { int i; for (i = 0; i < NN; i++) if (!strcmp(NK[i], k)) break; if (i == NN) { if (NN == 64) return -1; NN++; } snprintf(NK[i], sizeof(NK[i]), "%%s", k); snprintf(NVv[i], sizeof(NVv[i]), "%%s", v); if (!strcmp(k, "reaper_uptls_state")) printf("T=%%ld STATE %%s\n", T, v); return 0; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int nvram_match(const char *k, const char *v) { return !strcmp(nvram_safe_get(k), v); }
static int is_routing_enabled(void) { return 1; }
static int ipv6_enabled(void) { return nvram_get_int("t_ipv6"); }
static int hc_v6_usable(void) { return nvram_get_int("t_ipv6"); }
static int get_ipv6_service(void) { return IPV6_NATIVE_DHCP; }
static char *ipv6_nvname(const char *n) { return (char *)n; }
static int wan_primary_ifunit(void) { return 0; }
static int safe_atoi(const char *s) { return atoi(s); }
static char *strcat_r(const char *a, const char *b, char *d) { strcpy(d, a); strcat(d, b); return d; }
static const char *find_word(const char *buf, const char *w) { return strstr(buf, w); }
static int file_lock(const char *n) { (void)n; return 7; }
static void file_unlock(int l) { (void)l; }
static int RELOADS;
static void reload_dnsmasq(void) { RELOADS++; printf("T=%%ld RELOAD\n", T); }
static size_t t_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
#define strlcpy t_strlcpy
static size_t t_strlcat(char *d, const char *s, size_t n) { size_t l = strlen(d); if (l < n) t_strlcpy(d + l, s, n - l); return l + strlen(s); }
#define strlcat t_strlcat
int update_resolvconf(void);
static int vstrsep(char *buf, const char *sep, ...) { va_list ap; char **p; int n = 0; va_start(ap, sep); while ((p = va_arg(ap, char **)) != NULL) { if (!buf) break; *p = strsep(&buf, sep); n++; } va_end(ap); return n; }
#define vstrsep(b, s, ...) vstrsep(b, s, __VA_ARGS__, NULL)
#define foreach(word, wordlist, next) \
		for (next = &wordlist[strspn(wordlist, " ")], strncpy(word, next, sizeof(word)), word[sizeof(word) - 1] = '\0', \
		     word[strcspn(word, " ")] = '\0', next = strchr(next, ' '); strlen(word); \
		     next = next ? &next[strspn(next, " ")] : "", strncpy(word, next, sizeof(word)), word[sizeof(word) - 1] = '\0', \
		     word[strcspn(word, " ")] = '\0', next = strchr(next, ' '))
/* the world the fallback probes */
static int W_STUBBY = 1, W_FWD_RC = 0, W_TLS = 1, TLS_ASKS, FWD_ASKS;
static int pids(char *n) { return !strcmp(n, "stubby") ? W_STUBBY : 0; }
static int dns_ask(const char *addr, int af, int port, const char *name, int timeout_ms, int *an)
{ (void)af; (void)timeout_ms; if (an) *an = 0; FWD_ASKS++; if (strcmp(addr, "127.0.1.1") || port != 53 || *name) return -9; return W_FWD_RC; }
static int landns_rcode_ok(int rcode) { return rcode == 0 || rcode == 3; }
static int landns_uplink_down(void) { return nvram_match("link_wan", "0"); }
static void logmessage(const char *tag, const char *fmt, ...) { va_list ap; printf("T=%%ld LOG %%s: ", T, tag); va_start(ap, fmt); vprintf(fmt, ap); va_end(ap); printf("\n"); }
static int notify_rc(const char *s) { printf("T=%%ld NOTIFY %%s\n", T, s); return 0; }
static int f_write_string(const char *p, const char *s, unsigned f, unsigned m) { FILE *fp = fopen(p, "w"); (void)f; (void)m; if (!fp) return 0; fputs(s, fp); fclose(fp); return 1; }
static int f_read_string(const char *p, char *b, int n) { FILE *fp = fopen(p, "r"); int r; if (!fp) return -1; r = (int)fread(b, 1, n - 1, fp); b[r < 0 ? 0 : r] = 0; fclose(fp); return r; }
''' % {"servers": SERVERS, "resolv": RESOLV} + wsec_t + cfg + cut(src, "static int dns_build(unsigned char *pkt", "/* One UDP query for <name> A IN") + dot_t + lup + r'''
static int dot_ask(const struct hc_dot *d, const char *name, int timeout_ms, int *an)
{ (void)timeout_ms; if (an) *an = 0; TLS_ASKS++; printf("T=%ld TLSASK %s#%d host=[%s] name=[%s]\n", T, d->addr, d->port, d->host, name); return W_TLS ? 0 : -1; }
''' + ut_t + r'''
static void nv_arg(const char *a) { char k[48]; const char *e = strchr(a, '='); if (!e || e - a >= 48) return; memcpy(k, a, e - a); k[e - a] = 0; nvram_set(k, e + 1); }
static void dump(const char *p, const char *tag) { char l[256]; FILE *fp = fopen(p, "r"); if (!fp) { printf("T=%ld %s (none)\n", T, tag); return; } while (fgets(l, sizeof(l), fp)) { l[strcspn(l, "\n")] = 0; printf("T=%ld %s %s\n", T, tag, l); } fclose(fp); }
int main(int argc, char **argv)
{
	int i;
	if (!strcmp(argv[1], "step")) {	/* step <strict> <r>...: the pure machine */
		struct ut_sm m; ut_reset(&m, UT_UNK);
		for (i = 3; i < argc; i++) { ut_step(&m, atoi(argv[i]), atoi(argv[2]), UT_FAIL_AFTER, UT_RECOVER_AFTER); printf("%s%s", ut_name(m.st), i + 1 < argc ? " " : "\n"); }
		return 0;
	}
	if (!strcmp(argv[1], "writer")) {	/* writer <nv>...: both writers, the files after each */
		for (i = 2; i < argc; i++) nv_arg(argv[i]);
		update_resolvconf(); dump(SERVERS, "DOT-SRV"); dump(RESOLV, "DOT-RES");
		update_resolvconf_plain(); dump(SERVERS, "FB-SRV"); dump(RESOLV, "FB-RES");
		printf("flag=%d\n", reaper_uptls_plain);
		return 0;
	}
	/* sim <seconds> <event>...  event = <t>:<what>; what = nv key=value | stubby=0/1 | fwd=<rcode> | tls=0/1 | rewrite | dump */
	{
		struct uptls u; long end = atol(argv[2]); int k;
		for (i = 3; i < argc && !isdigit((unsigned char)argv[i][0]); i++) nv_arg(argv[i]);
		k = i;
		update_resolvconf();	/* the boot state: DNS-over-TLS on */
		uptls_adopt(&u);
		for (T = 0; T <= end; T++) {
			for (i = k; i < argc; i++) {
				char *c = strchr(argv[i], ':'); const char *w = c + 1;
				if (!c || atol(argv[i]) != T) continue;
				if (!strncmp(w, "stubby=", 7)) W_STUBBY = atoi(w + 7);
				else if (!strncmp(w, "fwd=", 4)) W_FWD_RC = atoi(w + 4);
				else if (!strncmp(w, "tls=", 4)) W_TLS = atoi(w + 4);
				else if (!strcmp(w, "rewrite")) { printf("T=%ld REWRITE\n", T); update_resolvconf(); }
				else if (!strcmp(w, "dump")) dump(SERVERS, "SRV");
				else nv_arg(w);
			}
			uptls_tick(&u);
		}
		dump(SERVERS, "SRV");
		printf("END st=%s swapped=%d tls_asks=%d reloads=%d\n", ut_name(u.m.st), u.swapped, TLS_ASKS, RELOADS);
	}
	return 0;
}
'''
sim_c = os.path.join(sim_dir, "sim.c"); sim_x = os.path.join(sim_dir, "sim")
open(sim_c, "w", encoding="utf-8").write(SIM)
r = subprocess.run([CC, "-O1", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-Wno-unused-parameter", "-Wno-unused-but-set-variable",
                    "-Wno-format-truncation", "-Wno-stringop-truncation", "-o", sim_x, sim_c, "-lssl", "-lcrypto"], capture_output=True, text=True)
check("uptls: the real fallback code and the real servers-file writer compile on the host with warnings as errors", r.returncode == 0, r.stderr[:1500])
if r.returncode == 0:
    BASE_NV = ["dnspriv_enable=1", "dnspriv_profile=0", "dnspriv_rulelist=<1.1.1.1>853>cloudflare-dns.com><9.9.9.9>>dns.quad9.net>",
               "ntp_ready=1", "link_wan=1", "wan0_dns=203.0.113.1 203.0.113.2", "wan0_domain=isp.example", "t_ipv6=1",
               "ipv6_dnsenable=1", "ipv6_get_dns=2001:db8::53", "ipv6_get_domain="]
    def sim(seconds, *events, nv=()):
        if os.path.exists(UTST): os.unlink(UTST)
        o = subprocess.run([sim_x, "sim", str(seconds)] + BASE_NV + list(nv) + list(events), capture_output=True, text=True, timeout=60).stdout
        return o
    def lines(o, tag): return [l for l in o.splitlines() if (" %s " % tag) in l or l.startswith(tag)]
    def first_t(o, needle):
        for l in o.splitlines():
            if needle in l: return int(l.split()[0][2:])
        return -1
    # ---- the writer
    w = subprocess.run([sim_x, "writer"] + BASE_NV, capture_output=True, text=True, timeout=30).stdout
    srv_dot = [l.split(" ", 2)[2] for l in w.splitlines() if " DOT-SRV " in l]
    srv_fb = [l.split(" ", 2)[2] for l in w.splitlines() if " FB-SRV " in l]
    res_dot = [l.split(" ", 2)[2] for l in w.splitlines() if " DOT-RES " in l]
    res_fb = [l.split(" ", 2)[2] for l in w.splitlines() if " FB-RES " in l]
    check("writer: with DNS-over-TLS on, dnsmasq's servers are the forwarder (and the WAN domain routes) only",
          "server=127.0.1.1" in srv_dot and not any(l in srv_dot for l in ("server=203.0.113.1", "server=2001:db8::53")), srv_dot)
    check("writer: the fallback writes the WAN IPv4 and IPv6 servers in place of the forwarder",
          srv_fb[:2] == ["server=203.0.113.1", "server=203.0.113.2"] and "server=2001:db8::53" in srv_fb and "server=127.0.1.1" not in srv_fb, srv_fb)
    check("writer: the WAN domain routes are written the same either way", [l for l in srv_dot if l.startswith("server=/")] == [l for l in srv_fb if l.startswith("server=/")] and "server=/isp.example/203.0.113.1" in srv_fb, (srv_dot, srv_fb))
    check("writer: the router's own resolv.conf is the same as with DNS-over-TLS on (loopback first)", res_dot == res_fb and res_fb[:1] == ["nameserver 127.0.0.1"], (res_dot, res_fb))
    check("writer: one dnsmasq reload per write, and the switch is off again after the call", w.count("RELOAD") == 2 and "flag=0" in w, w[-300:])
    w2 = subprocess.run([sim_x, "writer"] + BASE_NV + ["dnspriv_profile=1"], capture_output=True, text=True, timeout=30).stdout
    check("writer: Strict - the router's own resolv.conf stays loopback only (the writer changes nothing there)",
          [l.split(" ", 2)[2] for l in w2.splitlines() if " DOT-RES " in l] == ["nameserver 127.0.0.1"] and [l.split(" ", 2)[2] for l in w2.splitlines() if " FB-RES " in l] == ["nameserver 127.0.0.1"], w2)
    # ---- the pure machine: r = 0 ok, 1 hold, 2 dead, 3 fwd, 4 tls
    st = lambda strict, *rs: subprocess.run([sim_x, "step", str(strict)] + [str(x) for x in rs], capture_output=True, text=True).stdout.split()
    check("step: three bad checks in a row before the fallback; two good ones before it ends",
          st(0, 0, 3, 3, 3, 0, 0) == ["ok", "ok", "ok", "fb", "fb", "ok"], st(0, 0, 3, 3, 3, 0, 0))
    check("step: a good check in between starts the count again", st(0, 3, 3, 0, 3, 3, 3) == ["unk", "unk", "ok", "ok", "ok", "fb"], st(0, 3, 3, 0, 3, 3, 3))
    check("step: Strict never asks for the fallback - the same checks give 'down'", st(1, 2, 2, 2, 0, 0) == ["unk", "unk", "down", "down", "ok"], st(1, 2, 2, 2, 0, 0))
    check("step: a hold moves no counter and never clears a failed state",
          st(0, 3, 3, 1, 1, 3, 1, 0, 1, 0) == ["unk", "unk", "held", "held", "fb", "fb", "fb", "fb", "ok"], st(0, 3, 3, 1, 1, 3, 1, 0, 1, 0))
    check("step: the forwarder answering in the clear is 'plain', not the fallback", st(0, 4, 4, 4) == ["unk", "unk", "plain"])
    check("step: plain -> fb needs three checks of a dead forwarder; fb -> plain two of an answering one",
          st(0, 4, 4, 4, 2, 2, 2, 4, 4) == ["unk", "unk", "plain", "plain", "plain", "fb", "fb", "plain"], st(0, 4, 4, 4, 2, 2, 2, 4, 4))
    # ---- the live loop: 30 s checks, the first 20 s after start, then 20 s again after the first gate pass
    o = sim(400, "100:fwd=2", "300:fwd=0")
    t_fb = first_t(o, "STATE fb"); t_ok = first_t(o, "LOG rdnshc: Encrypted DNS: the upstream DNS-over-TLS forwarder answers again")
    check("sim: the forwarder stops resolving (SERVFAIL) - the fallback after three checks (within ~2 minutes)", 100 < t_fb <= 100 + 3 * 30 + 30, t_fb)
    check("sim: the fallback says why in its state: the forwarder does not answer", "STATE fb %d fwd" % t_fb in o, lines(o, "STATE"))
    srv_mid = [l for l in o.splitlines() if " SRV " in l]
    check("sim: at the end the forwarder is back in dnsmasq's list", any("server=127.0.1.1" in l for l in srv_mid) and "END st=ok swapped=0" in o, o[-400:])
    check("sim: it comes back two checks after the forwarder answers", 300 < t_ok <= 300 + 2 * 30 + 30, t_ok)
    logs = [l for l in o.splitlines() if " LOG " in l]
    check("sim: exactly one syslog line into the fallback and one out of it", len(logs) == 2 and "Opportunistic profile: dnsmasq now asks the plain WAN DNS servers (3)" in logs[0], logs)
    o2 = sim(400, "100:fwd=2", "200:dump")
    d200 = [l.split(" ", 2)[2] for l in o2.splitlines() if l.startswith("T=200 SRV ")]
    check("sim: while the fallback lasts dnsmasq has the WAN servers and not the forwarder", "server=203.0.113.1" in d200 and "server=2001:db8::53" in d200 and "server=127.0.1.1" not in d200, d200)
    o3 = sim(260, "100:fwd=2", "220:rewrite", "221:dump")
    d221 = [l.split(" ", 2)[2] for l in o3.splitlines() if l.startswith("T=221 SRV ")]
    check("sim: a rewrite by wan_up / a VPN client during the fallback is undone within seconds, quietly",
          "server=127.0.1.1" not in d221 and "server=203.0.113.1" in d221 and len([l for l in o3.splitlines() if " LOG " in l]) == 1, (d221, o3[-600:]))
    o4 = sim(400, "100:stubby=0")
    check("sim: a forwarder that is not running - the fallback after three checks, reason 'dead' (the watchdog had that long to restart it)",
          "STATE fb" in o4 and " dead" in [l for l in o4.splitlines() if "STATE fb" in l][0] and "is not running (3 checks)" in o4, lines(o4, "STATE"))
    o5 = sim(400, "100:fwd=2", nv=["dnspriv_profile=1"])
    check("sim: Strict - never the fallback: state 'down', the servers-file keeps the forwarder, one log line saying nothing goes out in the clear",
          "STATE down" in o5 and "STATE fb" not in o5 and "server=203.0.113.1" not in o5.replace("wan0_dns", "") and o5.count(" RELOAD") == 1
          and "Strict profile: nothing is sent in the clear" in o5, o5[-800:])
    check("sim: Strict - the servers are never asked over DNS-over-TLS directly (the forwarder is TLS-only there)", "TLSASK" not in o5)
    o6 = sim(400, "100:fwd=2", "200:dnspriv_profile=1")
    t_end = first_t(o6, "the DNS-over-TLS profile changed")
    check("sim: switched to Strict during the fallback - the forwarder is back within a second, one line says why",
          0 < t_end <= 201 and "END st=" in o6 and "swapped=0" in o6 and [l for l in o6.splitlines() if l.startswith("T=%d RELOAD" % t_end)], o6[-800:])
    o7 = sim(400, "100:fwd=2", "200:dnspriv_enable=0")
    check("sim: DNS-over-TLS switched off during the fallback - it ends, state 'off'", "DNS-over-TLS is no longer in use for the router" in o7 and "END st=off swapped=0" in o7, o7[-500:])
    o8 = sim(400, "100:fwd=2", "110:ntp_ready=0", nv=[])
    check("sim: the clock is not set - held, never the fallback", "STATE fb" not in o8 and "STATE held" in o8 and " clock" in [l for l in o8.splitlines() if "STATE held" in l][0], lines(o8, "STATE"))
    o9 = sim(400, "100:fwd=2", "110:link_wan=0")
    check("sim: the uplink is down - held ('wan'), never the fallback", "STATE fb" not in o9 and "STATE held" in o9 and "wan" in [l for l in o9.splitlines() if "STATE held" in l][0], lines(o9, "STATE"))
    o10 = sim(600, "100:tls=0", "400:tls=1")
    check("sim: Opportunistic, the servers refuse DNS-over-TLS but the forwarder answers (in the clear) - 'plain', nothing moved",
          "STATE plain" in o10 and "STATE fb" not in o10 and o10.count(" RELOAD") == 1 and " tls" in [l for l in o10.splitlines() if "STATE plain" in l][0], lines(o10, "STATE"))
    check("sim: the servers are asked without a certificate name (as the forwarder in this profile) and with the root zone",
          "TLSASK 1.1.1.1#853 host=[] name=[]" in o10)
    check("sim: when DNS-over-TLS works again the forwarder is restarted (it backs off TLS for 15 minutes) - main LAN instance only",
          "NOTIFY restart_stubby 0" in o10 or "NOTIFY restart_stubby" in o10, o10[-600:])
    o12 = sim(600)
    tl = [int(l.split()[0][2:]) for l in o12.splitlines() if "TLSASK 1.1.1.1" in l]
    check("sim: while all is well the servers are asked directly every 120 s, and nothing is logged or moved", len(tl) >= 4 and " LOG " not in o12 and o12.count(" RELOAD") == 1 and all(b - a >= 120 for a, b in zip(tl, tl[1:])), tl)
    # adoption: a previous instance left the fallback in place
    open(UTST, "w").write("fb dead")
    o11 = subprocess.run([sim_x, "sim", "200"] + BASE_NV + ["0:rewrite", "1:dump"], capture_output=True, text=True, timeout=60).stdout
    d1 = [l.split(" ", 2)[2] for l in o11.splitlines() if l.startswith("T=1 SRV ")]
    check("sim: a restarted daemon adopts the fallback a previous one left (it is re-asserted at once) and ends it when the forwarder answers",
          "server=203.0.113.1" in d1 and "server=127.0.1.1" not in d1 and "END st=ok swapped=0" in o11 and not os.path.exists(UTST), o11[:900])
# the loop: every wait gives the fallback its second; it runs whether or not the health check is switched on
loop = cut(src, "int rdnshc_main(int argc, char *argv[])", "\nvoid stop_rdnshc(void)")
check("uptls: the loop calls it every pass and every second of every wait (no plain sleep loop left)",
      "uptls_tick(&ut);" in loop and loop.count("hc_nap(") == 3 and "sleep(1)" not in loop and "uptls_adopt(&ut);" in loop)
check("uptls: it runs before the health check's own switch is looked at", loop.find("uptls_tick(&ut);") < loop.find("if (!enabled) {"))
check("uptls: the state is cleared when the daemon stops, the fallback file is kept for the next instance",
      'nvram_set("reaper_uptls_state", "");' in loop)
mw = rd(os.path.join(SRC, "rc", "multi_wan.c"))
check("uptls: a Multi-WAN group's other servers follow the fallback too", "if (dnspriv_enable && !reaper_uptls_plain)" in mw)
rch = rd(os.path.join(SRC, "rc", "rc.h"))
check("uptls: the writer is declared for rc", "extern int update_resolvconf_plain(void);" in rch and "extern int reaper_uptls_plain;" in rch)
rw2 = rd(os.path.join(SRC, "rc", "rwatch.c"))
check("uptls: rwatch starts rdnshc again in router mode when it is not running",
      "pidof rdnshc >/dev/null 2>&1" in rw2 and "service restart_rdnshc" in rw2)

# ------------------------------------------------------------------ the page
pg = rd(os.path.join(SRC, "www", "Reaper_Failover.asp"))
NODE = shutil.which("node")
tdef = cut(pg, "var T = {", "\n};\n") + "\n};\n"
fns = cut(pg, "function render(state, enable){", "/* 2026-10-10: the LAN name resolution check")
if not NODE or not tdef or not fns:
    check("page: the strings and the render code are found", bool(tdef) and bool(fns))
else:
    en = {}
    for line in open(os.path.join(SRC, "www", "EN.dict"), encoding="utf-8"):
        if "=" in line: k, v = line.rstrip("\n").split("=", 1); en[k] = v
    sub = lambda s: re.sub(r"<#([A-Za-z0-9_]+)#>", lambda mm: en.get(mm.group(1), "MISSING:" + mm.group(1)), s)
    js = ("var E={};function $id(i){if(!E[i])E[i]={className:'',textContent:'',title:'',hidden:false};return E[i];}\n"
          "var ORIG={target:'1.1.1.3',target6:''};var V6ON=false;function held(s){return s+' s';}\n" + sub(tdef) + sub(fns) +
          "\nvar out={};['up 5 1 - - t','down 30 0 - - t','up 5 1 - - s','down 9 0 - - s','up 5 1 1 - p','down 5 0 0 - p','up 5 1 1 -'].forEach(function(s){"
          "E={};render(s,'1');out[s]=[E.st_v.textContent,E.st_dot?E.st_dot.hidden:'none',E.st_dot?E.st_dot.textContent:''];});"
          "E={};render('off 0 -1','1');out.off=[E.st_v.textContent,E.st_dot.hidden];console.log(JSON.stringify(out));\n")
    jf = os.path.join(tmp, "p.js"); open(jf, "w", encoding="utf-8").write(js)
    r = subprocess.run([NODE, jf], capture_output=True, text=True, timeout=60)
    try: out = json.loads(r.stdout)
    except Exception: out = {}
    check("page: the render code runs", bool(out), r.stderr[:500])
    if out:
        check("page: over DNS-over-TLS, answering - the DoT words and the note for the server itself",
              out["up 5 1 - - t"] == [en["RDHC_65"], False, en["RDHC_67"]], out["up 5 1 - - t"])
        check("page: over DNS-over-TLS, not answering", out["down 30 0 - - t"][0] == en["RDHC_66"] and out["down 30 0 - - t"][2] == en["RDHC_67"])
        check("page: through the forwarder - its note", out["up 5 1 - - s"] == [en["RDHC_65"], False, en["RDHC_68"]] and out["down 9 0 - - s"][0] == en["RDHC_66"])
        check("page: port 53 - the old words, no note", out["up 5 1 1 - p"] == [en["RDHC_14"], True, ""] and out["down 5 0 0 - p"][0] == en["RDHC_15"])
        check("page: a five-field state from an older daemon reads as port 53", out["up 5 1 1 -"] == [en["RDHC_14"], True, ""])
        check("page: not running - no note", out["off"][1] is True)

# ------------------------------------------------------------------ the diag
dg = rd(os.path.join(SRC, "others", "reaper_diag"))
check("diag: v1.3.58", 'VER="REAPER-DIAG v1.3.62"' in dg and "REAPER-DIAG v1.3.62</span>" in rd(os.path.join(SRC, "www", "Reaper_Diag.asp")))
snip = cut(dg, "# v1.3.58: under DNS-over-TLS the check asks", "# v1.3.34 (2026-10-10)")
check("diag: the lines are found", "HCM=" in snip and "elif [" in snip)
def diag(state, order):
    pre = ("finding() { echo \"FIND [$1] $2\"; }\nnvram() { case \"$2\" in reaper_dnshc_enable) echo 1;; reaper_dnshc_state) echo '%s';; esac; }\n"
           "HCT=1.1.1.3; HCO='%s'\n") % (state, order)
    sf = os.path.join(tmp, "d.sh"); open(sf, "w").write(pre + snip)
    outs = [subprocess.run(["sh", sf], capture_output=True, text=True).stdout]
    if shutil.which("busybox"): outs.append(subprocess.run(["busybox", "ash", sf], capture_output=True, text=True).stdout)
    return outs
for o in diag("up 5 1 - - t", " ext-v4"):
    check("diag: over DNS-over-TLS - says how it asks, and no 'not first in the list' finding", "health probe      : DNS-over-TLS, the watched server itself" in o and "FIND" not in o, o)
for o in diag("down 40 0 - - s", " ext-v4"):
    check("diag: through the forwarder, not answering - its own finding", "the DNS-over-TLS forwarder (the watched server" in o and "FIND [WARN] DNS health check: the DNS-over-TLS forwarder does not answer" in o, o)
for o in diag("up 5 1 1 - p", " ext-v4 watched-v4"):
    check("diag: port 53 - the old order finding still fires when the watched server is not first", "health probe      : port 53" in o and "is not first in the router's DNS list" in o, o)
for o in diag("down 40 0 0 - p", " ext-v4"):
    check("diag: port 53, down - the old finding", "the watched resolver is DOWN" in o, o)

shutil.rmtree(tmp, ignore_errors=True)
print("\n%d failed" % len(fails) if fails else "\nall passed")
for f in fails: print("  " + f)
sys.exit(1 if fails else 0)
