#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Encrypted DNS for devices (rednsd, 2026-10-21): the router's own DNS-over-TLS server.

WHY THIS EXISTS. A device that encrypts its DNS to an outside provider never reaches the router's
resolver, so Dreadwatch cannot see or block it. rednsd lets devices encrypt TO the router: it ends
TLS on port 853 and hands each query to the dnsmasq instance of the device's own network over
loopback, naming the device in EDNS0 option 65400 so Dreadwatch still records the right device
(dnsmasq believes the option from loopback only and cuts it out before anything goes upstream -
test_dreadwatch.py covers that half). Nothing else exercises the daemon before metal.

WHAT IT DOES.
  1. Builds rednsd and the patched dnsmasq for the host (temporary copies, never in the tree),
     makes a throwaway certificate, and runs both on loopback. Clients connect from 127.0.0.2 and
     friends, so "the device" and "the router" are different addresses.
  2. Over real TLS: an answer comes back with the device's own ID; a listed name is NXDOMAIN and
     the hit log records the DEVICE (127.0.0.2), not the router; a device that forges option 65400
     is not believed; ten pipelined queries all come back; a device that sent no EDNS gets none
     back; an answer too big for UDP arrives whole over the TCP retry; ALPN "dot" is chosen.
  3. Refusals, all before TLS: a peer outside the configured subnets, a DNS Director deny, the
     per-device connection cap; a malformed frame and a silent handshake are dropped; an
     upstream that never answers gives SERVFAIL; SIGHUP reloads the policy.
  4. A C harness (RED_TEST) checks the policy against a fake ARP table and the OPT surgery.
  5. Pins the wiring: rc, firewall, defaults, Makefile, page, menu, CGI, markers.
Exit 0 pass, 1 fail, 77 skipped (no router source, no compiler or OpenSSL headers, no openssl CLI).
"""
import json, os, re, shutil, signal, socket, ssl, struct, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rednsd", "rednsd.c")):
    skip("no router source tree with rednsd (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
OPENSSL = shutil.which("openssl")
if not CC or not OPENSSL or not os.path.exists("/usr/include/openssl/ssl.h"):
    skip("needs a host compiler, OpenSSL headers and the openssl CLI")

def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

REAPER_OPT = 65400
work = tempfile.mkdtemp(prefix="rednsd_")
procs = []
try:
    # ---- 1. build both, make a certificate
    RB = os.path.join(work, "rednsd")
    b = subprocess.run([CC, "-O2", "-Wall", "-Wextra", "-Wformat-security", "-o", RB, os.path.join(SRC, "rednsd", "rednsd.c"),
                        "-lssl", "-lcrypto"], capture_output=True, text=True)
    check("rednsd builds for the host without warnings", b.returncode == 0 and not b.stderr.strip(), b.stderr[-800:])
    db = os.path.join(work, "dnsmasq")
    shutil.copytree(os.path.join(SRC, "dnsmasq"), db, symlinks=True, ignore=shutil.ignore_patterns("*.o", "dnsmasq"))
    b = subprocess.run(["make", "-C", db, "COPTS=-DNO_DBUS -DNO_INOTIFY", "CC=" + CC, "-j4"], capture_output=True, text=True, timeout=900)
    DB = os.path.join(db, "src", "dnsmasq")
    check("the patched dnsmasq builds for the host", b.returncode == 0 and os.path.exists(DB), (b.stdout + b.stderr)[-600:])
    if fails:
        raise SystemExit
    cert, key = os.path.join(work, "cert.pem"), os.path.join(work, "key.pem")
    r = subprocess.run([OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", "/CN=test.example",
                        "-addext", "subjectAltName=DNS:test.example,DNS:alt.example", "-keyout", key, "-out", cert],
                       capture_output=True, text=True)
    if r.returncode != 0:   # OpenSSL 1.1.0 and older have no -addext
        skip("openssl CLI cannot make a test certificate: " + r.stderr[-200:])

    DPORT, RPORT, DEAD = 5389, 8853, 5391
    hits = os.path.join(work, "hits", "dns.hits"); os.makedirs(os.path.dirname(hits))
    big = ",".join('"%s"' % ("x" * 200) for _ in range(9))   # ~1.8 KB: past edns-packet-max, so UDP truncates
    open(os.path.join(work, "d.conf"), "w").write(
        "port=%d\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\npid-file=\nedns-packet-max=1232\n"
        "address=/ok.test/192.0.2.1\ntxt-record=big.test,%s\nreaper-hitlog=%s\nreaper-nx=/bad.example/\n" % (DPORT, big, hits))
    procs.append(subprocess.Popen([DB, "-k", "-C", os.path.join(work, "d.conf"), "--log-facility=-"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    status = os.path.join(work, "status.json")
    conf = os.path.join(work, "r.conf")
    def write_conf(extra=""):
        open(conf, "w").write(
            "cert %s\nkey %s\nstatus %s\nlisten 127.0.0.1 %d\n"
            "peer 127.0.0.2/32 127.0.0.1#%d\npeer 127.0.0.3/32 127.0.0.1#%d\npeer 127.0.0.4/32 127.0.0.1#%d\n"
            "peer 127.0.0.5/32 127.0.0.1#%d\ndeny-net 127.0.0.4/32\n%s" % (cert, key, status, RPORT, DPORT, DPORT, DPORT, DEAD, extra))
    write_conf()
    rp = subprocess.Popen([RB, "-f", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    procs.append(rp)
    time.sleep(0.8)
    check("rednsd starts and stays up", rp.poll() is None, rp.stderr.read().decode() if rp.poll() is not None else "")

    # ---- 2. over real TLS
    def tls(src="127.0.0.2", alpn=None):
        cx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); cx.check_hostname = False; cx.verify_mode = ssl.CERT_NONE
        if alpn: cx.set_alpn_protocols(alpn)
        raw = socket.socket(); raw.settimeout(6); raw.bind((src, 0)); raw.connect(("127.0.0.1", RPORT))
        return cx.wrap_socket(raw)
    def query(name, qtype=1, qid=0x1234, opts=None):
        m = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 1 if opts is not None else 0)
        m += b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\0" + struct.pack(">HH", qtype, 1)
        if opts is not None:
            rd = b"".join(struct.pack(">HH", c, len(d)) + d for c, d in opts)
            m += b"\0" + struct.pack(">HHIH", 41, 1232, 0, len(rd)) + rd
        return struct.pack(">H", len(m)) + m
    def recv_msg(s):
        h = b""
        while len(h) < 2:
            c = s.recv(2 - len(h))
            if not c: return None
            h += c
        n, body = struct.unpack(">H", h)[0], b""
        while len(body) < n:
            c = s.recv(n - len(body))
            if not c: return None
            body += c
        return body
    hitlines = lambda: open(hits).read().splitlines() if os.path.exists(hits) else []

    s = tls(alpn=["dot"])
    check("ALPN: the device's 'dot' is chosen", s.selected_alpn_protocol() == "dot", s.selected_alpn_protocol())
    s.sendall(query("ok.test", qid=0x4242)); a = recv_msg(s)
    check("an answer comes back with the device's own ID and the record",
          a and a[:2] == b"\x42\x42" and (a[3] & 0x0f) == 0 and a.endswith(socket.inet_aton("192.0.2.1")), a)
    check("a device that sent no EDNS gets no OPT RR back", a and struct.unpack(">H", a[10:12])[0] == 0, a)
    s.sendall(query("bad.example", qid=0x0101)); a = recv_msg(s); time.sleep(0.2)
    check("a listed name is NXDOMAIN over DoT", a and (a[3] & 0x0f) == 3, a)
    check("Dreadwatch records the DEVICE (127.0.0.2), not the router's loopback",
          hitlines() and hitlines()[-1].split()[1:3] == ["127.0.0.2", "bad.example"], hitlines())
    s.sendall(query("x.bad.example", qid=0x0102, opts=[(REAPER_OPT, b"\x01" + socket.inet_aton("192.0.2.66"))])); a = recv_msg(s); time.sleep(0.2)
    check("a device that forges the client option is not believed",
          a and (a[3] & 0x0f) == 3 and hitlines()[-1].split()[1] == "127.0.0.2", hitlines()[-1:])
    s.sendall(query("ok.test", qid=0x0103, opts=[(10, b"12345678")])); a = recv_msg(s)
    check("a device that sent EDNS gets its OPT RR back", a and struct.unpack(">H", a[10:12])[0] == 1, a)
    s.sendall(b"".join(query("ok.test", qid=0x2000 + i) for i in range(10)))
    ids = set()
    for _ in range(10):
        a = recv_msg(s)
        if a: ids.add(struct.unpack(">H", a[:2])[0])
    check("ten pipelined queries in one write: ten answers, every ID", ids == set(0x2000 + i for i in range(10)), sorted(ids))
    s.sendall(query("big.test", qtype=16, qid=0x0104)); a = recv_msg(s)
    check("an answer too big for UDP arrives whole (TCP retry), TC clear", a and len(a) > 1232 and not (a[2] & 0x02) and (a[3] & 0x0f) == 0,
          len(a) if a else None)
    # review 2026-10-24 (S-A-2): the retry no longer blocks the loop - two truncated answers in flight at once both arrive,
    # and an ordinary query sent between them is answered meanwhile
    s.sendall(query("big.test", qtype=16, qid=0x0106) + query("ok.test", qid=0x0108) + query("big.test", qtype=16, qid=0x0107))
    got = {}
    for _ in range(3):
        a = recv_msg(s)
        if a: got[a[:2]] = a
    check("two truncated answers in flight at once both arrive whole over the non-blocking TCP retry, the plain query between them too",
          set(got) == {b"\x01\x06", b"\x01\x07", b"\x01\x08"} and len(got[b"\x01\x06"]) > 1232 and len(got[b"\x01\x07"]) > 1232
          and got[b"\x01\x08"].endswith(socket.inet_aton("192.0.2.1")), sorted(got))
    s.close()

    def refused(src):
        try:
            x = tls(src); x.sendall(query("ok.test")); return recv_msg(x) is None
        except (ssl.SSLError, OSError, ConnectionError):
            return True
    check("a peer outside the configured subnets is closed before TLS", refused("127.0.0.6"))
    check("a DNS Director deny (deny-net) is closed before TLS", refused("127.0.0.4"))
    raws = []
    t_conn = time.time()
    for i in range(9):
        r0 = socket.socket(); r0.settimeout(0.15); r0.bind(("127.0.0.3", 0)); r0.connect(("127.0.0.1", RPORT)); raws.append(r0)
    time.sleep(0.3)
    def closed(sk):
        try: return sk.recv(1) == b""
        except socket.timeout: return False
        except OSError: return True
    # nine short probes (~1.4 s) finish well inside the 5 s handshake limit
    check("per-device cap: 8 connections stay, the 9th is closed", [closed(x) for x in raws] == [False] * 8 + [True])
    time.sleep(max(0, 5.6 - (time.time() - t_conn)))
    check("a connection that never starts TLS is dropped after the 5 s handshake limit", all(closed(x) for x in raws[:8]))
    for x in raws: x.close()
    s = tls(); s.sendall(b"\x00\x05hello")
    check("a malformed frame (shorter than a DNS header) closes the connection", recv_msg(s) is None)
    s.close()
    s = tls("127.0.0.5"); s.sendall(query("ok.test", qid=0x0105)); t0 = time.time(); a = recv_msg(s); dt = time.time() - t0
    check("an upstream that never answers: SERVFAIL after about 4 s, with the device's ID",
          a and a[:2] == b"\x01\x05" and (a[3] & 0x0f) == 2 and 3.5 < dt < 6, (a, round(dt, 1)))
    s.close()

    rp.send_signal(signal.SIGUSR1); time.sleep(1.2)   # the poll loop wakes at least once a second
    st = json.load(open(status)) if os.path.exists(status) else {}
    check("status file: running, the listener, counters", st.get("state") == "running" and st["listen"][0]["ok"] == 1
          and st["queries"] >= 15 and st["refused_peer"] >= 1 and st["refused_policy"] >= 1 and st["refused_busy"] >= 1, st)
    check("status file: the certificate's names, self-signed, not trusted",
          st.get("cert", {}).get("names") == ["test.example", "alt.example"] and st["cert"]["self_signed"] == 1 and st["cert"]["trusted"] == 0, st.get("cert"))

    write_conf("deny-net 127.0.0.2/32\n"); rp.send_signal(signal.SIGHUP); time.sleep(0.5)
    check("SIGHUP re-reads the policy: the newly denied device is refused", refused("127.0.0.2"))
    write_conf(); rp.send_signal(signal.SIGHUP); time.sleep(0.5)
    check("...and allowed again after the next reload", not refused("127.0.0.2"))
    rp.send_signal(signal.SIGTERM)
    try: rp.wait(timeout=5)
    except subprocess.TimeoutExpired: pass
    check("SIGTERM stops it cleanly and marks the status file", rp.poll() == 0 and json.load(open(status)).get("state") == "stopped")

    # ---- 4. C harness: policy against a fake ARP table, OPT surgery
    harness = os.path.join(work, "h.c")
    open(harness, "w").write(r'''
#define RED_TEST
#include "%s"
static int bad;
#define T(c) do { if (!(c)) { printf("FAIL line %%d: %%s\n", __LINE__, #c); bad++; } } while (0)
static sockaddr_u v4(const char *s) { sockaddr_u a; memset(&a, 0, sizeof(a)); a.in.sin_family = AF_INET; inet_pton(AF_INET, s, &a.in.sin_addr); return a; }
int main(int argc, char **argv) {
    struct cfg c; sockaddr_u a; unsigned char m[600]; size_t n; int added; struct msginfo mi;
    (void)argc; arp_path = argv[1];
    memset(&c, 0, sizeof(c));
    parse_mac("aa:bb:cc:00:00:01", c.deny_mac[c.ndeny_mac++]);
    parse_mac("aa:bb:cc:00:00:02", c.allow_mac[c.nallow_mac++]);
    parse_net("192.168.50.0/24", &c.deny_net[c.ndeny_net++]);
    a = v4("10.0.0.1"); T(policy_allows(&c, &a) == 0);   /* deny-mac */
    a = v4("192.168.50.7"); T(policy_allows(&c, &a) == 1); /* allow-mac beats deny-net */
    a = v4("192.168.50.8"); T(policy_allows(&c, &a) == 0); /* deny-net, MAC not listed */
    a = v4("10.0.0.9"); T(policy_allows(&c, &a) == 1);     /* nothing applies */
    a = v4("10.0.0.3"); T(policy_allows(&c, &a) == 1);     /* incomplete ARP entry: no MAC */
    { struct net n1; parse_net("10.20.0.0/22", &n1); a = v4("10.20.3.255"); T(net_match(&n1, &a)); a = v4("10.20.4.0"); T(!net_match(&n1, &a)); }
    /* a query with no OPT: one is added, and taken off the answer again */
    n = 12; memset(m, 0, sizeof(m)); m[5] = 1; memcpy(m + 12, "\2ok\4test\0\0\1\0\1", 13); n += 13;
    a = v4("192.168.50.20");
    n = add_client_opt(m, n, sizeof(m), &a, &added);
    T(added == 1 && m[11] == 1 && n == 25 + 11 + 9 && msg_scan(m, n, &mi) == 0 && mi.has_opt);
    T(m[25 + 11] == 0xff && m[25 + 12] == 0x78 && m[25 + 15] == 1 && m[25 + 16] == 192 && m[25 + 19] == 20);
    n = strip_opt_rr(m, n); T(n == 25 && m[11] == 0);
    /* a query with an OPT holding a forged 65400 and a cookie: forged one out, ours in, cookie kept */
    { unsigned char opt[] = { 0,0,41, 4,0xd0, 0,0,0,0, 0,21, 0xff,0x78,0,5,1,1,2,3,4, 0,10,0,8,'c','o','o','k','i','e','!','!' };
      m[11] = 1; memcpy(m + 25, opt, sizeof(opt)); n = 25 + sizeof(opt);
      n = add_client_opt(m, n, sizeof(m), &a, &added);
      T(added == 0 && msg_scan(m, n, &mi) == 0 && n == 25 + 11 + 12 + 9);
      T(!memcmp(m + 36, "\0\12\0\10cookie!!", 12) && m[48] == 0xff && m[49] == 0x78 && m[52] == 1 && m[53] == 192); }
    /* garbage is refused, not forwarded */
    T(add_client_opt(m, 14, sizeof(m), &a, &added) == 0);
    printf(bad ? "harness: %%d failed\n" : "harness: all passed\n", bad);
    return bad != 0;
}
''' % os.path.join(SRC, "rednsd", "rednsd.c"))
    arp = os.path.join(work, "arp")
    open(arp, "w").write("IP address       HW type     Flags       HW address            Mask     Device\n"
                         "10.0.0.1         0x1         0x2         aa:bb:cc:00:00:01     *        br0\n"
                         "192.168.50.7     0x1         0x2         aa:bb:cc:00:00:02     *        br0\n"
                         "192.168.50.8     0x1         0x2         aa:bb:cc:00:00:08     *        br0\n"
                         "10.0.0.3         0x1         0x0         aa:bb:cc:00:00:01     *        br0\n")
    hb = os.path.join(work, "h")
    b = subprocess.run([CC, "-O1", "-Wall", "-o", hb, harness, "-lssl", "-lcrypto"], capture_output=True, text=True)
    r = subprocess.run([hb, arp], capture_output=True, text=True) if b.returncode == 0 else None
    check("C harness: policy (deny-mac, allow-mac over deny-net, incomplete ARP), subnets, OPT add/strip/forgery",
          r is not None and r.returncode == 0, (b.stderr + (r.stdout if r else ""))[-600:])
except SystemExit:
    pass
finally:
    for p in procs:
        if p.poll() is None:
            p.terminate()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill()
    shutil.rmtree(work, ignore_errors=True)

# ---- 5. wiring (each check names the place a later edit must keep)
def has(rel, *needles):
    try: t = read(rel)
    except OSError: return False
    return all(n in t for n in needles)
check("Makefile: rednsd is built and installed", has("Makefile", "obj-y += rednsd") and has("rednsd/Makefile", "install -D rednsd $(INSTALLDIR)/usr/sbin/rednsd"))
check("defaults: reaper_dot_srv is off", has("shared/defaults.c", '{ "reaper_dot_srv", "0",'))
check("rc: start/stop and the config writer (encdns.c), wired into boot, stop, the service verb, dnsmasq, firewall and certificate refresh",
      has("rc/encdns.c", "void start_rednsd(void)", "void stop_rednsd(void)", "void rednsd_refresh(void)", '"/tmp/rednsd"', "rednsd.conf")
      and has("rc/services.c", "start_rednsd();\t/* reaper 2026-10-21", "stop_rednsd();\t/* reaper 2026-10-21", 'strcmp(script, "rednsd") == 0',
              "rednsd_refresh();\n\tTRACE_PT(", "rednsd_cert_changed();")
      and read("rc/services.c").count("rednsd_cert_changed();") == 2
      and has("rc/firewall.c", "rednsd_refresh();") and has("rc/Makefile", "OBJS += encdns.o")
      and has("rc/rwatch.c", "service restart_rednsd"))
# review 2026-10-24: S-A-2 the TCP retry is a polled slot, S-A-3 the cap counts the device's MAC and a full table makes room,
# S-A-5 rwatch never reads the status file through a link or a FIFO, S-A-9 no root without the nobody account
check("rednsd: non-blocking TCP retry slots, per-device cap by MAC with eviction of the longest-idle connection, no root without nobody",
      has("rednsd/rednsd.c", "tcpre_start(p);", "static void tcpre_io(struct tcpre *r, short ev)", "map[np++] = -2000 - i;",
          "the longest-idle open connection makes room", "has_mac = (fam == AF_INET ? mac_v4(&a, mac) : mac_v6(&a, mac)) == 0;",
          "no 'nobody' account - stopping") and "tcp_retry(" not in read("rednsd/rednsd.c"))
check("rwatch: rednsd's status file is read only when it is a plain file (no link, no FIFO)",
      has("rc/rwatch.c", '_rsj=/tmp/rednsd/run/status.json; [ -f \\"$_rsj\\" ] && [ ! -L \\"$_rsj\\" ] || _rsj=/dev/null', 'bind)_error\\"\' \\"$_rsj\\"'))
check("rc: DNS Director's DoT chain also catches UDP 853", has("rc/dnsfilter.c", "-A FORWARD -i br+ -p udp -m udp --dport 853 -j DNSFILTER_DOT"))
check("firewall: WAN input to 853 is dropped while rednsd is on", has("rc/firewall.c", "rednsd_wan_drop"))
# 2026-10-21: Wallguard (the ad & tracker blocker) sits between them: Warden | Dreadwatch | Wallguard | Encrypted DNS
check("page + menu: the Encrypted DNS tab sits right of Dreadwatch and Wallguard",
      has("www/Reaper_EncryptedDNS.asp", "reaper_encdns.cgi") and
      re.search(r'\{url: "Reaper_Dreadwatch\.asp"[^\n]*\n(?:\s*/\*[^\n]*\*/\n)?\s*\{url: "Reaper_Wallguard\.asp", tabName: "<#RSHD_00#>"\},\n'
                r'(?:\s*/\*[^\n]*\*/\n)?\s*\{url: "Reaper_EncryptedDNS\.asp", tabName: "<#RENC_00#>"\}',
                read("www/require/menuTrees/menuTree.js")) is not None)
check("httpd: the status CGI and the native-page entry", has("httpd/web.c", "do_reaper_encdns_cgi") and has("httpd/reaper_inject.c", '"Reaper_EncryptedDNS.asp",'))

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
