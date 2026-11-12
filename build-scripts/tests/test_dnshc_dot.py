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
check("diag: v1.3.58", 'VER="REAPER-DIAG v1.3.59"' in dg and "REAPER-DIAG v1.3.59</span>" in rd(os.path.join(SRC, "www", "Reaper_Diag.asp")))
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
