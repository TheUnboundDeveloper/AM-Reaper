#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Encrypted DNS for devices (rednsd, 2026-10-21): the router's own DNS-over-TLS server, and
since 2026-11-10 its DNS-over-HTTPS server (RFC 8484, HTTP/2 only, nghttp2 vendored in rednsd/).

WHY THIS EXISTS. A device that encrypts its DNS to an outside provider never reaches the router's
resolver, so Dreadwatch cannot see or block it. rednsd lets devices encrypt TO the router: it ends
TLS on port 853 (DoT) or 443 (DoH) and hands each query to the dnsmasq instance of the device's own
network over loopback, naming the device in EDNS0 option 65400 so Dreadwatch still records the right
device (dnsmasq believes the option from loopback only and cuts it out before anything goes upstream -
test_dreadwatch.py covers that half). Nothing else exercises the daemon before metal.

WHAT IT DOES.
  1. Builds rednsd - with the vendored nghttp2 sources and the Makefile's own defines - and the
     patched dnsmasq for the host (temporary copies, never in the tree), makes a throwaway
     certificate, and runs both on loopback with a DoT and a DoH listener. Clients connect from
     127.0.0.2 and friends, so "the device" and "the router" are different addresses.
  2. Over real TLS (DoT): an answer comes back with the device's own ID; a listed name is NXDOMAIN and
     the hit log records the DEVICE (127.0.0.2), not the router; a device that forges option 65400
     is not believed; ten pipelined queries all come back; a device that sent no EDNS gets none
     back; an answer too big for UDP arrives whole over the TCP retry; ALPN "dot" is chosen.
  2b. Over HTTP/2 (DoH), with curl and with a small hand-written HTTP/2 client: POST and GET resolve
     end to end with the same answer bytes DoT gives, the client's DNS ID, content-type and a
     cache-control from the record's TTL; a listed name is NXDOMAIN and the hit log names the DEVICE;
     a client without "h2" fails the handshake; 404 / 405 / 415 / 413 / 400 / 431 without a body;
     past 8 streams the extra ones are refused and the first 8 answered; requests reset before their
     answer leave no pending query behind (more resets than the pending table has slots); the
     rapid-reset limit ends a connection.
  3. Refusals, all before TLS: a peer outside the configured subnets, a DNS Director deny, the
     per-device connection cap; a malformed frame and a silent handshake are dropped; an
     upstream that never answers gives SERVFAIL; SIGHUP reloads the policy. The status file: both
     listeners with their protocol, the counters, and the devices that use them (64 rows at most).
  3b. The DoH checks once more against a build with AddressSanitizer + UBSan, time and disk capped
     (skipped quietly where the host has no sanitizer runtime).
  4. A C harness (RED_TEST) checks the policy against a fake ARP table and the OPT surgery.
  5. Pins the wiring: rc, firewall, defaults, Makefile, page, menu, CGI, markers, the vendored library.
Exit 0 pass, 1 fail, 77 skipped (no router source, no compiler or OpenSSL headers, no openssl CLI,
no curl with HTTP/2).
"""
import base64, glob, json, os, re, shutil, signal, socket, ssl, struct, subprocess, sys, tempfile, threading, time

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
CURL = shutil.which("curl")
if not CURL or "HTTP2" not in subprocess.run([CURL, "--version"], capture_output=True, text=True).stdout:
    skip("needs curl built with HTTP/2 (the DoH listener speaks nothing else)")

def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

REAPER_OPT = 65400
NG = os.path.join(SRC, "rednsd", "nghttp2", "lib")
NGINC = os.path.join(NG, "includes")
work = tempfile.mkdtemp(prefix="rednsd_")
procs = []
try:
    # ---- 1. build both, make a certificate
    # nghttp2 the way the firmware builds it: every lib/*.c, the Makefile's own -D list in place of config.h
    mk = read("rednsd/Makefile")
    m = re.search(r"^NGH2_DEFS[ \t]*=((?:.*\\\n)*.*)$", mk, re.M)
    NGDEFS = m.group(1).replace("\\\n", " ").split() if m else []
    ngsrc = sorted(glob.glob(os.path.join(NG, "*.c")))
    def build_ng(tag, flags):
        d = os.path.join(work, "ng" + tag); os.makedirs(d)
        b = subprocess.run([CC, "-c"] + flags + ["-DNGHTTP2_STATICLIB"] + NGDEFS + ["-I", NGINC, "-I", NG] + ngsrc,
                           cwd=d, capture_output=True, text=True, timeout=900)
        return b, sorted(glob.glob(os.path.join(d, "*.o")))
    b, NGOBJ = build_ng("", ["-O2", "-Wall"])
    check("the vendored nghttp2 builds for the host with the Makefile's defines (%d sources)" % len(ngsrc),
          b.returncode == 0 and NGDEFS and ngsrc and len(NGOBJ) == len(ngsrc), (NGDEFS, b.stderr[-800:]))
    RB = os.path.join(work, "rednsd")
    b = subprocess.run([CC, "-O2", "-Wall", "-Wextra", "-Wformat-security", "-DNGHTTP2_STATICLIB", "-I", NGINC, "-o", RB,
                        os.path.join(SRC, "rednsd", "rednsd.c")] + NGOBJ + ["-lssl", "-lcrypto"], capture_output=True, text=True)
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

    DPORT, RPORT, DEAD, HPORT = 5389, 8853, 5391, 8443
    IP = socket.inet_aton("192.0.2.1")
    hits = os.path.join(work, "hits", "dns.hits"); os.makedirs(os.path.dirname(hits))
    big = ",".join('"%s"' % ("x" * 200) for _ in range(9))   # ~1.8 KB: past edns-packet-max, so UDP truncates
    # local-ttl: the configured records get a TTL a DoH client may cache by (cache-control: max-age=300)
    open(os.path.join(work, "d.conf"), "w").write(
        "port=%d\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\npid-file=\nedns-packet-max=1232\nlocal-ttl=300\n"
        "address=/ok.test/192.0.2.1\ntxt-record=big.test,%s\nreaper-hitlog=%s\nreaper-nx=/bad.example/\n" % (DPORT, big, hits)
        + "".join("txt-record=huge.test,%s\n" % big for _ in range(5)))   # ~9 KB: eight of them are more than a connection may hold back
    procs.append(subprocess.Popen([DB, "-k", "-C", os.path.join(work, "d.conf"), "--log-facility=-"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    status = os.path.join(work, "status.json")
    conf = os.path.join(work, "r.conf")
    def write_conf(extra=""):
        # 127.0.1.0/24: a subnet of devices for the status file's device list; "doh wan" = the flags in either order
        open(conf, "w").write(
            "cert %s\nkey %s\nstatus %s\nlisten 127.0.0.1 %d\nlisten 127.0.0.1 %d doh\nlisten 127.0.0.1 %d doh wan\n"
            "peer 127.0.0.2/32 127.0.0.1#%d\npeer 127.0.0.3/32 127.0.0.1#%d\npeer 127.0.0.4/32 127.0.0.1#%d\n"
            "peer 127.0.0.5/32 127.0.0.1#%d\npeer 127.0.1.0/24 127.0.0.1#%d\ndeny-net 127.0.0.4/32\n%s"
            % (cert, key, status, RPORT, HPORT, HPORT + 1, DPORT, DPORT, DPORT, DEAD, DPORT, extra))
    write_conf()
    rp = subprocess.Popen([RB, "-f", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    procs.append(rp)
    time.sleep(0.8)
    check("rednsd starts and stays up", rp.poll() is None, rp.stderr.read().decode() if rp.poll() is not None else "")

    # ---- 2. over real TLS
    def tls(src="127.0.0.2", alpn=None, port=None):
        cx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); cx.check_hostname = False; cx.verify_mode = ssl.CERT_NONE
        if alpn: cx.set_alpn_protocols(alpn)
        raw = socket.socket(); raw.settimeout(6); raw.bind((src, 0)); raw.connect(("127.0.0.1", port or RPORT))
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
          a and a[:2] == b"\x42\x42" and (a[3] & 0x0f) == 0 and a.endswith(IP), a)
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
          and got[b"\x01\x08"].endswith(IP), sorted(got))
    s.close()

    # ---- 2b. DNS over HTTPS (HTTP/2 only). One function, run against the plain build here and against the
    # sanitizer build in 3b. T = a prefix for the check names, proc = the rednsd under test.
    dnsmsg = lambda name, qtype=1, qid=0, opts=None: query(name, qtype, qid, opts)[2:]
    b64u = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    CT = ["content-type: application/dns-message"]
    def curl(tail, src="127.0.0.2", data=None, method=None, headers=()):
        hf, of = os.path.join(work, "curl.h"), os.path.join(work, "curl.o")
        for f in (hf, of):
            if os.path.exists(f): os.remove(f)
        cmd = [CURL, "-sS", "-k", "--http2", "--interface", src, "--max-time", "10", "-D", hf, "-o", of]
        if method: cmd += ["-X", method]
        for h in headers: cmd += ["-H", h]
        if data is not None: cmd += ["--data-binary", "@-"]
        r = subprocess.run(cmd + ["https://127.0.0.1:%d%s" % (HPORT, tail)], input=data, capture_output=True, timeout=30)
        lines = open(hf, "rb").read().decode("latin-1").split("\r\n") if os.path.exists(hf) else [""]
        m = re.match(r"HTTP/(\S+) (\d+)", lines[0])
        hd = dict((l.split(":", 1)[0].lower(), l.split(":", 1)[1].strip()) for l in lines[1:] if ":" in l)
        body = open(of, "rb").read() if os.path.exists(of) else b""
        return (m.group(1) if m else None, int(m.group(2)) if m else 0, hd, body, r.stderr.decode(errors="replace")[-300:])

    # a hand-written HTTP/2 client: the frames only, header fields as HPACK literals (no table, no Huffman)
    PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
    DATA, HEADERS, RST, SETTINGS, PING, GOAWAY = 0, 1, 3, 4, 6, 7
    def frame(typ, flags, sid, payload=b""):
        return struct.pack(">I", len(payload))[1:] + bytes([typ, flags]) + struct.pack(">I", sid) + payload
    def hp_str(sv):
        b, n, out = sv.encode(), len(sv.encode()), b""
        if n < 127: return bytes([n]) + b
        n -= 127; out = b"\x7f"
        while n >= 128: out += bytes([n % 128 + 128]); n //= 128
        return out + bytes([n]) + b
    def h2_post(sid, msg, path="/dns-query"):
        hb = b"".join(b"\x00" + hp_str(k) + hp_str(v) for k, v in [
            (":method", "POST"), (":scheme", "https"), (":authority", "test.example"), (":path", path),
            ("content-type", "application/dns-message"), ("content-length", str(len(msg)))])
        return frame(HEADERS, 0x4, sid, hb) + frame(DATA, 0x1, sid, msg)   # END_HEADERS; END_STREAM
    class H2:
        def __init__(self, src, settings=b""):
            self.s = tls(src, ["h2"], HPORT); self.buf = b""; self.fr = []; self.pings = 0; self.eof = False
            self.s.sendall(PREFACE + frame(SETTINGS, 0, 0, settings))
        def send(self, b): self.s.sendall(b)
        def read(self, until, timeout=8):
            """frames so far as (type, flags, stream, payload), reading until until(frames), the end of the connection or the timeout"""
            end = time.time() + timeout; self.s.settimeout(0.3)
            while not until(self.fr) and time.time() < end:
                try: d = self.s.recv(65536)
                except socket.timeout: continue
                except (ssl.SSLError, OSError): self.eof = True; break
                if not d: self.eof = True; break
                self.buf += d
                while len(self.buf) >= 9 and len(self.buf) >= 9 + int.from_bytes(self.buf[:3], "big"):
                    n = int.from_bytes(self.buf[:3], "big")
                    self.fr.append((self.buf[3], self.buf[4], int.from_bytes(self.buf[5:9], "big") & 0x7fffffff, self.buf[9:9 + n]))
                    self.buf = self.buf[9 + n:]
            return self.fr
        def sync(self):
            """a PING and its acknowledgement: the server has worked through everything sent before"""
            self.pings += 1; tok = struct.pack(">Q", self.pings)
            self.send(frame(PING, 0, 0, tok))
            return any(f[0] == PING and f[1] & 1 and f[3] == tok for f in self.read(lambda fr: any(f[0] == PING and f[1] & 1 and f[3] == tok for f in fr)))
        def body(self, sid): return b"".join(f[3] for f in self.fr if f[0] == DATA and f[2] == sid)
        def ok200(self): return set(f[2] for f in self.fr if f[0] == HEADERS and f[3][:1] == b"\x88")   # 0x88 = ":status: 200" in HPACK
        def ended(self, sid): return any(f[0] == DATA and f[2] == sid and f[1] & 1 for f in self.fr)
        def close(self):
            try: self.s.close()
            except OSError: pass
    def burst(c, first, name="ok.test"):
        """8 requests and, in the same write, their 8 resets (CANCEL): opened and gone before any answer can arrive"""
        ids = [first + 2 * i for i in range(8)]
        c.send(b"".join(h2_post(sid, dnsmsg(name, qid=sid & 0xffff)) for sid in ids) + b"".join(frame(RST, 0, sid, struct.pack(">I", 8)) for sid in ids))
        return ids[-1] + 2

    def doh_checks(T, proc):
        def stat():
            proc.send_signal(signal.SIGUSR1); time.sleep(1.2)   # the poll loop wakes at least once a second
            try: return json.load(open(status))
            except (OSError, ValueError): return {}
        st0 = stat()
        q1 = dnsmsg("ok.test", qid=0xBEEF)
        ver, code, hd, body, err = curl("/dns-query", data=q1, headers=CT)
        check(T + "DoH POST over HTTP/2: 200, the record, the client's own DNS ID",
              ver == "2" and code == 200 and body[:2] == b"\xbe\xef" and (body[3] & 0x0f) == 0 and body.endswith(IP), (ver, code, body, err))
        check(T + "DoH POST: content-type, content-length, and cache-control from the record's TTL",
              hd.get("content-type") == "application/dns-message" and hd.get("content-length") == str(len(body)) and hd.get("cache-control") == "max-age=300", hd)
        s = tls(alpn=["dot"]); s.sendall(struct.pack(">H", len(q1)) + q1); a = recv_msg(s); s.close()
        check(T + "DoH and DoT give the same answer bytes for the same query (no OPT RR added, none left in)", a is not None and a == body, (a, body))
        ver, code, hd, body, err = curl("/dns-query?dns=" + b64u(dnsmsg("ok.test", qid=0)))
        check(T + "DoH GET ?dns=<base64url>: 200, the record, DNS ID 0 as RFC 8484 asks, the same headers",
              ver == "2" and code == 200 and body[:2] == b"\0\0" and body.endswith(IP) and hd.get("content-type") == "application/dns-message"
              and hd.get("cache-control") == "max-age=300", (ver, code, hd, body, err))
        ver, code, hd, body, err = curl("/dns-query?x=1&dns=" + b64u(dnsmsg("ok.test", qid=5)) + "&y=2")
        check(T + "DoH GET: dns= is found among other parameters", code == 200 and body[:2] == b"\0\5" and body.endswith(IP), (code, body, err))
        ver, code, hd, body, err = curl("/dns-query", src="127.0.0.3", data=dnsmsg("bad.example", qid=7), headers=CT); time.sleep(0.2)
        check(T + "a listed name is NXDOMAIN over DoH, not to be cached (max-age=0)",
              code == 200 and len(body) > 3 and (body[3] & 0x0f) == 3 and hd.get("cache-control") == "max-age=0", (code, hd, body, err))
        check(T + "Dreadwatch records the DoH DEVICE (127.0.0.3), not the router's loopback",
              hitlines() and hitlines()[-1].split()[1:3] == ["127.0.0.3", "bad.example"], hitlines()[-2:])
        ver, code, hd, body, err = curl("/dns-query", src="127.0.0.5", data=dnsmsg("ok.test", qid=9), headers=CT)
        check(T + "DoH: an upstream that never answers gives SERVFAIL in a 200, not to be cached",
              code == 200 and body[:2] == b"\0\x09" and (body[3] & 0x0f) == 2 and hd.get("cache-control") == "max-age=0", (code, hd, body, err))

        # refusals: at the handshake, then by status - never a body
        def no_h2(alpn):
            try: tls(alpn=alpn, port=HPORT).close(); return False
            except (ssl.SSLError, OSError): return True
        check(T + "a client that offers only http/1.1 fails the TLS handshake", no_h2(["http/1.1"]))
        check(T + "...so does one that offers no ALPN at all, and one that offers 'dot' to the DoH listener", no_h2(None) and no_h2(["dot"]))
        s = tls(alpn=["h2", "http/1.1"], port=HPORT)
        check(T + "ALPN: 'h2' is chosen on the DoH listener, whatever else is offered", s.selected_alpn_protocol() == "h2", s.selected_alpn_protocol())
        s.close()
        ver, code, hd, body, err = curl("/dns-query", data=dnsmsg("big.test", qtype=16, qid=0x0b16), headers=CT)
        check(T + "DoH: an answer too big for UDP arrives whole (TCP retry), TC clear",
              code == 200 and len(body) > 1232 and body[:2] == b"\x0b\x16" and not (body[2] & 0x02) and hd.get("content-length") == str(len(body)), (code, len(body), err))
        notq = bytearray(q1); notq[2] |= 0x80
        for name, want, kw in [
            ("another path is 404", 404, dict(tail="/other", data=q1, headers=CT)),
            ("a path that only begins like it is 404", 404, dict(tail="/dns-queryx", data=q1, headers=CT)),
            ("PUT is 405", 405, dict(tail="/dns-query", data=q1, headers=CT, method="PUT")),
            ("a POST with another content-type is 415", 415, dict(tail="/dns-query", data=q1, headers=["content-type: text/plain"])),
            ("a 5,000-byte body is 413", 413, dict(tail="/dns-query", data=b"\0" * 5000, headers=CT)),
            ("a 200,000-byte body is 413, answered before it has all arrived", 413, dict(tail="/dns-query", data=b"\0" * 200000, headers=CT)),
            ("?dns= that is not base64url is 400", 400, dict(tail="/dns-query?dns=!!!!")),
            ("?dns= of an impossible length is 400", 400, dict(tail="/dns-query?dns=AAAAA")),
            ("a GET without the dns parameter is 400", 400, dict(tail="/dns-query")),
            ("a POST shorter than a DNS header is 400", 400, dict(tail="/dns-query", data=b"hello", headers=CT)),
            ("a GET that decodes to less than a DNS header is 400", 400, dict(tail="/dns-query?dns=AAAA")),
            ("a DNS message that is no query (QR set) is 400", 400, dict(tail="/dns-query", data=bytes(notq), headers=CT)),
            ("more than 4 KB of request headers is 431", 431, dict(tail="/dns-query", data=q1, headers=CT + ["x-pad: " + "a" * 5000])),
        ]:
            ver, code, hd, body, err = curl(**kw)
            check(T + "DoH: " + name + ", without a body", ver == "2" and code == want and body == b"", (ver, code, body[:40], err))

        # the server's SETTINGS, and the stream limit before and after the client has acknowledged it
        c = H2("127.0.0.3")
        ids = [1 + 2 * i for i in range(12)]
        c.send(b"".join(h2_post(sid, dnsmsg("ok.test", qid=0x3000 + sid)) for sid in ids))
        fr = c.read(lambda fr: sum(1 for f in fr if f[0] == DATA and f[1] & 1) >= 8 and sum(1 for f in fr if f[0] == RST) >= 4)
        sv = fr[0][3] if fr and fr[0][0] == SETTINGS and not fr[0][1] & 1 else b""
        check(T + "the server's SETTINGS come first: 8 streams at once, a 4 KB header list, no push",
              dict(struct.unpack(">HI", sv[i:i + 6]) for i in range(0, len(sv), 6)) == {3: 8, 6: 4096, 2: 0}, fr[:1])
        ok200 = c.ok200()
        check(T + "12 streams at once: the first 8 are answered, each with its own DNS ID",
              ok200 == set(ids[:8]) and all(c.body(sid)[:2] == struct.pack(">H", 0x3000 + sid) and c.body(sid).endswith(IP) for sid in ids[:8]),
              (sorted(ok200), [(f[0], f[1], f[2]) for f in fr]))
        check(T + "...and the other 4 are refused (RST_STREAM REFUSED_STREAM), nothing else",
              dict((f[2], struct.unpack(">I", f[3])[0]) for f in fr if f[0] == RST) == dict((sid, 7) for sid in ids[8:])
              and not any(f[2] in ids[8:] for f in fr if f[0] in (DATA, HEADERS)), [(f[0], f[2], f[3][:4]) for f in fr if f[0] == RST])
        c.send(h2_post(25, dnsmsg("ok.test", qid=0x3333))); c.read(lambda fr: c.ended(25))
        check(T + "...and the connection lives on: the next request is answered", c.body(25)[:2] == b"\x33\x33" and c.body(25).endswith(IP), c.body(25))
        c.close()
        c = H2("127.0.0.5")                      # the upstream that never answers: the 8 stay open
        c.read(lambda fr: any(f[0] == SETTINGS and not f[1] & 1 for f in fr))
        c.send(frame(SETTINGS, 1, 0) + b"".join(h2_post(1 + 2 * i, dnsmsg("ok.test", qid=i)) for i in range(9)))
        fr = c.read(lambda fr: any(f[0] == GOAWAY for f in fr))
        go = [struct.unpack(">II", f[3][:8])[1] for f in fr if f[0] == GOAWAY]
        check(T + "a client that acknowledged the limit and opens a 9th stream all the same is disconnected (GOAWAY PROTOCOL_ERROR)", go == [1], go)
        c.close()

        # a body past 4096 bytes that did not announce its length (no content-length): refused as it arrives
        e0 = stat().get("h2_errors", 0)
        c = H2("127.0.0.3")
        hb = b"".join(b"\x00" + hp_str(k) + hp_str(v) for k, v in [(":method", "POST"), (":scheme", "https"), (":authority", "test.example"),
                                                                   (":path", "/dns-query"), ("content-type", "application/dns-message")])
        c.send(frame(HEADERS, 0x4, 1, hb) + frame(DATA, 0, 1, b"\0" * 3000) + frame(DATA, 0x1, 1, b"\0" * 2000))
        fr = c.read(lambda fr: any(f[0] == HEADERS and f[2] == 1 for f in fr))
        c.send(h2_post(3, dnsmsg("ok.test", qid=0x0303))); c.read(lambda fr: c.ended(3))
        check(T + "DoH: 5,000 bytes of body without a content-length are refused with a status and no body; the connection lives on",
              [f[1] & 1 for f in fr if f[0] == HEADERS and f[2] == 1] == [1] and 1 not in c.ok200() and not c.body(1)
              and c.body(3)[:2] == b"\x03\x03" and stat().get("h2_errors", 0) == e0 + 1, [(f[0], f[1], f[2]) for f in c.fr])
        c.close()

        # flow control: answers wait in the server until the client's window lets them go - and only so many of them
        zero = struct.pack(">HI", 4, 0)          # SETTINGS_INITIAL_WINDOW_SIZE 0: this client takes no answer bytes yet
        c = H2("127.0.0.3", zero)
        c.send(h2_post(1, dnsmsg("big.test", qtype=16, qid=0x0b01)) + h2_post(3, dnsmsg("ok.test", qid=0x0b03)))
        c.read(lambda fr: c.ok200() == {1, 3}); time.sleep(0.4); c.read(lambda fr: True, 0.5)
        held = c.ok200() == {1, 3} and not any(f[0] == DATA for f in c.fr)
        c.send(frame(8, 0, 1, struct.pack(">I", 65535)) + frame(8, 0, 3, struct.pack(">I", 65535)))   # WINDOW_UPDATE for both streams
        c.read(lambda fr: c.ended(1) and c.ended(3))
        check(T + "DoH: with the client's window shut the answers wait (headers only), and arrive whole once it opens",
              held and len(c.body(1)) > 1232 and c.body(1)[:2] == b"\x0b\x01" and c.body(3)[:2] == b"\x0b\x03" and c.body(3).endswith(IP),
              (held, len(c.body(1)), c.body(3)))
        c.close()
        c = H2("127.0.0.3", zero)
        c.send(b"".join(h2_post(1 + 2 * i, dnsmsg("huge.test", qtype=16, qid=i)) for i in range(8)))   # 8 x ~9 KB held back: past 64 KB
        c.read(lambda fr: False, 6)              # until the server ends the connection
        gone = c.eof
        check(T + "DoH: a client that takes no answers is disconnected once more than 64 KB of them wait for it (as a DoT device that never reads is)",
              gone and len(c.ok200()) < 8 and not any(f[0] == DATA for f in c.fr), (gone, sorted(c.ok200())))
        c.close()

        # requests reset before their answer: nothing answered, nothing left behind
        c = H2("127.0.0.3"); nxt = 1
        for _ in range(3): nxt = burst(c, nxt)
        c.send(h2_post(nxt, dnsmsg("ok.test", qid=0x4444))); fr = c.read(lambda fr: c.ended(nxt))
        check(T + "24 requests reset before their answers (more than a connection may have in flight): none is answered, the next one is",
              c.body(nxt)[:2] == b"\x44\x44" and c.body(nxt).endswith(IP) and set(f[2] for f in fr if f[0] == DATA) == {nxt},
              [(f[0], f[1], f[2]) for f in fr])
        c.close()
        sf0 = stat().get("servfail"); t0 = time.time(); synced = 0
        for _ in range(22):                      # 22 x 96 = 2112 resets from the device whose upstream never answers:
            c = H2("127.0.0.5"); nxt = 1         # more than the 2048 slots of the pending table
            for _ in range(12): nxt = burst(c, nxt)
            synced += c.sync(); c.close()
        dt = time.time() - t0
        time.sleep(4.6)                          # past the 4 s after which a query left behind would be failed
        ver, code, hd, body, err = curl("/dns-query", data=dnsmsg("ok.test", qid=0x5555), headers=CT)
        st1 = stat()
        check(T + "2112 requests reset before their answers (in %.1f s): no pending query is left to time out, and the next query is answered" % dt,
              synced == 22 and sf0 is not None and st1.get("servfail") == sf0 and code == 200 and body[:2] == b"\x55\x55" and body.endswith(IP),
              (synced, sf0, st1.get("servfail"), code, body, err))
        c = H2("127.0.0.5"); nxt = 1
        for _ in range(12): nxt = burst(c, nxt)              # 96 resets on one connection: still welcome
        alive = c.sync() and not any(f[0] == GOAWAY for f in c.fr)
        for _ in range(6):                                   # the allowance refills by 10 a second (whole seconds, so
            try: nxt = burst(c, nxt)                         # the 100th is not always the last): a few bursts more
            except (ssl.SSLError, OSError): break
            if any(f[0] == GOAWAY for f in c.read(lambda fr: any(f[0] == GOAWAY for f in fr), 0.3)): break
        check(T + "rapid reset: past 100 resets on one connection the client is told to go away, not before",
              alive and any(f[0] == GOAWAY for f in c.fr), (alive, nxt, [(f[0], f[2]) for f in c.fr][-5:]))
        c.close()

        st1 = stat()
        check(T + "status file: the DoH counters moved (doh_queries, h2_errors) and the refused handshakes are counted",
              st1.get("doh_queries", 0) - st0.get("doh_queries", 0) >= 2000 and st1.get("h2_errors", 0) - st0.get("h2_errors", 0) >= 15
              and st1.get("hs_fail", 0) - st0.get("hs_fail", 0) >= 3 and st1.get("queries", 0) - st0.get("queries", 0) >= st1.get("doh_queries", 0) - st0.get("doh_queries", 0),
              (st0, st1))
        check(T + "rednsd is still up after all of it", proc.poll() is None)

    def run_doh(T, proc):
        # a connection the server drops under the hand-written client is a failed check, not the end of the run
        try: doh_checks(T, proc)
        except (OSError, ssl.SSLError, ValueError, IndexError, KeyError, struct.error, subprocess.SubprocessError) as e:
            check(T + "the DoH checks ran to their end", False, repr(e))
    run_doh("", rp)

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
    # the same two limits on the DoH listener: the cap counts the device across both listeners
    raws = []
    t_conn = time.time()
    for i in range(9):
        if i == 8: time.sleep(0.2)   # the two listeners are served in turn: the 9th comes when the 8 are in
        r0 = socket.socket(); r0.settimeout(0.15); r0.bind(("127.0.0.3", 0)); r0.connect(("127.0.0.1", HPORT if i % 2 else RPORT)); raws.append(r0)
    time.sleep(0.3)
    check("per-device cap across the DoT and the DoH listener: 8 connections stay, the 9th is closed", [closed(x) for x in raws] == [False] * 8 + [True])
    time.sleep(max(0, 5.6 - (time.time() - t_conn)))
    check("a DoH connection that never starts TLS is dropped after the 5 s handshake limit too", all(closed(x) for x in raws[:8]))
    for x in raws: x.close()
    s = tls(); s.sendall(b"\x00\x05hello")
    check("a malformed frame (shorter than a DNS header) closes the connection", recv_msg(s) is None)
    s.close()
    s = tls(alpn=["h2"], port=HPORT); s.sendall(b"GET /dns-query HTTP/1.1\r\nHost: test.example\r\n\r\n")
    def drained(sk, secs=3):
        end = time.time() + secs; sk.settimeout(0.3)
        while time.time() < end:
            try:
                if sk.recv(4096) == b"": return True
            except socket.timeout: continue
            except OSError: return True
        return False
    check("bytes that are not HTTP/2 on the DoH listener close the connection", drained(s))
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
    check("status file: every listener says its protocol, and 'doh' / 'wan' are read in either order",
          [(l.get("p"), l.get("proto"), l.get("wan"), l.get("ok")) for l in st.get("listen", [])]
          == [(RPORT, "dot", 0, 1), (HPORT, "doh", 0, 1), (HPORT + 1, "doh", 1, 1)], st.get("listen"))
    check("status file: doh_queries and h2_errors are there, and no field it had before is gone",
          st.get("doh_queries", 0) >= 2000 and st.get("h2_errors", 0) >= 15 and
          all(k in st for k in ("state", "pid", "up", "listen", "conns", "conns_total", "queries", "refused_peer", "refused_policy",
                                "refused_busy", "hs_fail", "servfail", "cert")), sorted(st))

    # the devices that use the listeners: address + protocol, a count and the time of the last query; never a refused peer
    rows = lambda st: dict(((c["a"], c["proto"]), c) for c in st.get("clients", []))
    cl = rows(st)
    check("status file: clients has a row for each device and protocol used so far, with only address, protocol, count and time",
          {("127.0.0.2", "dot"), ("127.0.0.2", "doh"), ("127.0.0.3", "doh"), ("127.0.0.5", "dot"), ("127.0.0.5", "doh")} <= set(cl)
          and all(sorted(c) == ["a", "last", "proto", "q"] for c in st.get("clients", [])), st.get("clients"))
    check("status file: a peer refused by policy or outside the subnets never appears in clients",
          not any(a in ("127.0.0.4", "127.0.0.6") for a, _ in cl), sorted(cl))
    s = tls("127.0.1.201")   # the file was written a moment ago (the signal above): the worst case for what follows
    for i in range(3):
        s.sendall(query("ok.test", qid=i)); recv_msg(s)
    s.close()
    for i in range(2):
        curl("/dns-query", src="127.0.1.202", data=dnsmsg("ok.test", qid=i), headers=CT)
    t0 = time.time(); cl = {}
    while time.time() - t0 < 9 and not {("127.0.1.201", "dot"), ("127.0.1.202", "doh")} <= set(cl):
        time.sleep(0.25)
        try: cl = rows(json.load(open(status)))
        except (OSError, ValueError): pass
    d1, d2 = cl.get(("127.0.1.201", "dot"), {}), cl.get(("127.0.1.202", "doh"), {})
    check("status file: a DoT device and a DoH device appear on their own within seconds of their queries (%.1f s, no signal), "
          "with the right protocol and counts" % (time.time() - t0),
          d1.get("q") == 3 and d2.get("q") == 2 and abs(d1.get("last", 0) - time.time()) < 15 and abs(d2.get("last", 0) - time.time()) < 15, (d1, d2))
    for i in range(1, 71):   # 70 more devices, one query each: the table holds 64
        s = tls("127.0.1.%d" % i); s.sendall(query("ok.test", qid=i)); recv_msg(s); s.close()
    rp.send_signal(signal.SIGUSR1); time.sleep(1.2)
    cl = rows(json.load(open(status)))
    check("status file: clients holds 64 rows at most - the 65th device and those after it replace the ones longest silent",
          set(cl) == set(("127.0.1.%d" % i, "dot") for i in range(7, 71)) and all(c["q"] == 1 for c in cl.values()), sorted(cl))

    write_conf("deny-net 127.0.0.2/32\n"); rp.send_signal(signal.SIGHUP); time.sleep(0.5)
    check("SIGHUP re-reads the policy: the newly denied device is refused", refused("127.0.0.2"))
    write_conf(); rp.send_signal(signal.SIGHUP); time.sleep(0.5)
    check("...and allowed again after the next reload", not refused("127.0.0.2"))
    ver, code, hd, body, err = curl("/dns-query", data=dnsmsg("ok.test", qid=0x0666), headers=CT)
    check("...and the DoH listener is still a DoH listener after the reload", code == 200 and body[:2] == b"\x06\x66", (code, body, err))
    rp.send_signal(signal.SIGTERM)
    try: rp.wait(timeout=5)
    except subprocess.TimeoutExpired: pass
    check("SIGTERM stops it cleanly and marks the status file", rp.poll() == 0 and json.load(open(status)).get("state") == "stopped")

    # a configuration without a DoH listener is the DoT daemon it was: one listener, DoT answers, nothing on the DoH port
    open(conf, "w").write("cert %s\nkey %s\nstatus %s\nlisten 127.0.0.1 %d\npeer 127.0.0.2/32 127.0.0.1#%d\n" % (cert, key, status, RPORT, DPORT))
    rp = subprocess.Popen([RB, "-f", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    procs.append(rp)
    time.sleep(0.8)
    s = tls(alpn=["dot"]); s.sendall(query("ok.test", qid=0x0d07)); a = recv_msg(s); s.close()
    try: socket.create_connection(("127.0.0.1", HPORT), 1).close(); nodoh = False
    except OSError: nodoh = True
    rp.send_signal(signal.SIGUSR1); time.sleep(1.2)
    st = json.load(open(status))
    check("DoT only (no 'doh' listener in the configuration): DoT answers as before, nothing listens for DoH, the status file says so",
          a and a[:2] == b"\x0d\x07" and a.endswith(IP) and nodoh and [(l["p"], l["proto"]) for l in st["listen"]] == [(RPORT, "dot")]
          and st["doh_queries"] == 0 and st["h2_errors"] == 0 and st["queries"] == 1
          and [(c["a"], c["proto"], c["q"]) for c in st["clients"]] == [("127.0.0.2", "dot", 1)], (a, nodoh, st))
    rp.send_signal(signal.SIGTERM)
    try: rp.wait(timeout=5)
    except subprocess.TimeoutExpired: pass
    write_conf()

    # ---- 3b. the DoH checks once more, under AddressSanitizer + UBSan. Bounded in every direction, because a
    # sanitizer runtime older than the kernel it runs on can spin for ever printing one line (it once filled a
    # disk here): these processes run without address-space randomization (what that spin trips over), for 120 s
    # at most, with 20 MB of file at most, no log_path - the report goes to one capped file, never into a pipe.
    SAN = ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined"]
    def san_pre():
        import ctypes, resource
        libc, cap = ctypes.CDLL(None), 20000 * 1024
        def pre():
            libc.personality(libc.personality(0xffffffff) | 0x0040000)   # ADDR_NO_RANDOMIZE
            resource.setrlimit(resource.RLIMIT_FSIZE, (cap, cap))
        return pre
    probe = os.path.join(work, "probe")
    open(probe + ".c", "w").write("int main(void) { return 0; }\n")
    san_ok = False
    try:
        pre = san_pre()
        b = subprocess.run([CC] + SAN + ["-o", probe, probe + ".c"], capture_output=True, text=True, timeout=120)
        san_ok = b.returncode == 0 and subprocess.run([probe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                      timeout=20, preexec_fn=pre).returncode == 0
    except (OSError, AttributeError, ImportError, subprocess.SubprocessError):   # no runtime, no personality(), or it hung
        pass
    if not san_ok:
        print("skip sanitizer pass: this host has no usable AddressSanitizer/UBSan runtime")
    else:
        b, sobj = build_ng("san", SAN)
        RBS = os.path.join(work, "rednsd_san")
        b2 = subprocess.run([CC] + SAN + ["-Wall", "-DNGHTTP2_STATICLIB", "-I", NGINC, "-o", RBS, os.path.join(SRC, "rednsd", "rednsd.c")]
                            + sobj + ["-lssl", "-lcrypto"], capture_output=True, text=True, timeout=900)
        check("sanitizer build of rednsd + nghttp2", b.returncode == 0 and b2.returncode == 0, (b.stderr + b2.stderr)[-600:])
        if b.returncode == 0 and b2.returncode == 0:
            sanlog = os.path.join(work, "san.log")
            env = dict(os.environ, ASAN_OPTIONS="detect_leaks=1:exitcode=23", UBSAN_OPTIONS="print_stacktrace=1")
            env.pop("LSAN_OPTIONS", None)
            with open(sanlog, "wb") as lf:
                sp = subprocess.Popen([RBS, "-f", "-c", conf], stdout=subprocess.DEVNULL, stderr=lf, env=env, preexec_fn=pre)
            procs.append(sp)
            killer = threading.Timer(120, sp.kill); killer.daemon = True; killer.start()
            up = False
            for _ in range(100):                 # a sanitizer build takes its time to start
                time.sleep(0.1)
                try: socket.create_connection(("127.0.0.1", HPORT), 1).close(); up = True; break
                except OSError: pass
                if sp.poll() is not None: break
            check("sanitizer build of rednsd starts and listens", up, open(sanlog, "rb").read(3000))
            if up:
                run_doh("[sanitizer] ", sp)
            sp.send_signal(signal.SIGTERM)
            try: sp.wait(timeout=20)
            except subprocess.TimeoutExpired: sp.kill()
            killer.cancel()
            rep = open(sanlog, "rb").read(200000).decode(errors="replace")
            check("sanitizer pass: the run ended by itself, with no AddressSanitizer, LeakSanitizer or UBSan report",
                  sp.returncode == 0 and not re.search(r"Sanitizer|runtime error", rep), (sp.returncode, rep[-1500:]))
            os.remove(sanlog)

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
    /* listen lines: the protocol and the wan flag, in either order; a DoT line reads as it always did */
    { FILE *f = fopen(argv[2], "w"); struct cfg *k = calloc(1, sizeof(*k));
      fputs("listen 192.168.50.1 853\nlisten 192.168.50.1 443 doh\nlisten 203.0.113.9 853 wan\n"
            "listen 203.0.113.9 443 wan doh\nlisten 203.0.113.9 8443 doh wan\nlisten 192.168.50.1 444 dohx\n", f); fclose(f);
      T(k && load_conf(argv[2], k, 0) == 0 && k->nlisten == 6);
      T(k->listen[0].proto == P_DOT && !k->listen[0].wan && k->listen[1].proto == P_DOH && !k->listen[1].wan);
      T(k->listen[2].proto == P_DOT && k->listen[2].wan && k->listen[3].proto == P_DOH && k->listen[3].wan);
      T(k->listen[4].proto == P_DOH && k->listen[4].wan && k->listen[5].proto == P_DOT && !k->listen[5].wan && k->listen[5].port == 444);
      free(k); }
    /* cache-control for a DoH answer: the lowest answer TTL; 0 without answers, on SERVFAIL, on a message that does not parse */
    { unsigned char r[] = { 0,0,0x81,0x80, 0,1,0,2,0,0,0,0, 2,'o','k',4,'t','e','s','t',0, 0,1,0,1,
                            0xc0,12, 0,1,0,1, 0,0,1,44, 0,4, 192,0,2,1,  0xc0,12, 0,1,0,1, 0,0,0,60, 0,4, 192,0,2,2 };
      T(answer_ttl(r, sizeof(r)) == 60);
      r[47] = 0x80; T(answer_ttl(r, sizeof(r)) == 0);          /* RFC 2181: top bit set counts as 0 */
      r[47] = 0; r[3] = 0x82; T(answer_ttl(r, sizeof(r)) == 0); r[3] = 0x80;
      T(answer_ttl(r, sizeof(r) - 3) == 0);
      r[7] = 0; T(answer_ttl(r, 25) == 0); }
    /* ?dns=: base64url without padding */
    { struct h2s s1; const char *p1 = "/dns-query?a=b&dns=AAEC_-8", *p2 = "/dns-query?dns=AA=", *p3 = "/dns-queryy?dns=AAEC", *p4 = "/dns-query";
      memset(&s1, 0, sizeof(s1)); h2_path(&s1, (const uint8_t *)p1, strlen(p1));
      T(s1.path_ok && s1.has_dns && !s1.dns_err && s1.len == 5 && !memcmp(s1.buf, "\0\1\2\xff\xef", 5)); free(s1.buf);
      memset(&s1, 0, sizeof(s1)); h2_path(&s1, (const uint8_t *)p2, strlen(p2)); T(s1.path_ok && s1.has_dns && s1.dns_err == 400 && !s1.buf);
      memset(&s1, 0, sizeof(s1)); h2_path(&s1, (const uint8_t *)p3, strlen(p3)); T(!s1.path_ok && !s1.has_dns);
      memset(&s1, 0, sizeof(s1)); h2_path(&s1, (const uint8_t *)p4, strlen(p4)); T(s1.path_ok && !s1.has_dns && h2_judge(&s1) == 405);
      s1.method = H2M_GET; T(h2_judge(&s1) == 400); s1.method = H2M_POST; T(h2_judge(&s1) == 415); s1.ctype_ok = 1; T(h2_judge(&s1) == 0);
      s1.big_body = 1; T(h2_judge(&s1) == 413); s1.path_ok = 0; T(h2_judge(&s1) == 404); }
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
    b = subprocess.run([CC, "-O1", "-Wall", "-DNGHTTP2_STATICLIB", "-I", NGINC, "-o", hb, harness] + NGOBJ + ["-lssl", "-lcrypto"],
                       capture_output=True, text=True)
    r = subprocess.run([hb, arp, os.path.join(work, "listen.conf")], capture_output=True, text=True) if b.returncode == 0 else None
    check("C harness: policy (deny-mac, allow-mac over deny-net, incomplete ARP), subnets, OPT add/strip/forgery, "
          "listen flags, cache-control TTL, ?dns= decoding and the order of the DoH refusals",
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
# nghttp2 is vendored: the upstream library sources only, compiled into rednsd by name - no shared object, no second user
try: ver = re.search(r'#define NGHTTP2_VERSION "([0-9.]+)"', read("rednsd/nghttp2/lib/includes/nghttp2/nghttp2ver.h")).group(1)
except (OSError, AttributeError): ver = ""
mkobjs = set(re.findall(r"\b(\w+)\.o\b", (re.search(r"^NGH2_OBJS[ \t]*=((?:.*\\\n)*.*)$", read("rednsd/Makefile"), re.M) or [""])[0]))
check("nghttp2 %s is vendored in rednsd/: 1.64.0 or newer, licence and README (version, tarball checksum), every lib/*.c named in the Makefile"
      % ver, ver and tuple(int(x) for x in ver.split(".")) >= (1, 64, 0) and has("rednsd/nghttp2/COPYING", "The MIT License")
      and has("rednsd/nghttp2/README.reaper", ver, "sha256", "nghttp2-%s.tar" % ver)
      and mkobjs == set(os.path.basename(f)[:-2] for f in glob.glob(os.path.join(NG, "*.c"))) and len(mkobjs) > 20, (ver, sorted(mkobjs)))
check("rednsd/Makefile: nghttp2 is compiled in statically with the hardening flags, the binary still links only OpenSSL",
      has("rednsd/Makefile", "-DBUILDING_NGHTTP2", "NGH2_INC	= -I$(NGH2)/includes -DNGHTTP2_STATICLIB", "@$(CC) $(CFLAGS) $(NGH2_DEFS) $(NGH2_GC) -I$(NGH2) -c $< -o $@",
          "$(CC) -o $@ $(OBJS) $(NGH2_OBJS) $(LDFLAGS)", "LDFLAGS	= -L$(TOP)/openssl -lssl -lcrypto -ldl -pie -Wl,-z,relro,-z,now")
      and "nghttp2" not in read("Makefile") and "-lnghttp2" not in read("rednsd/Makefile"))
check("rednsd: the DoH limits are set, not left to defaults (streams, header list, memory, nghttp2's flood options, no push)",
      has("rednsd/rednsd.c", "#define H2_STREAMS	8", "#define H2_HDR_MAX	4096", "#define H2_MEM_MAX	(64 * 1024)",
          "{ NGHTTP2_SETTINGS_MAX_CONCURRENT_STREAMS, H2_STREAMS }", "{ NGHTTP2_SETTINGS_MAX_HEADER_LIST_SIZE, H2_HDR_MAX }",
          "{ NGHTTP2_SETTINGS_ENABLE_PUSH, 0 }", "nghttp2_option_set_stream_reset_rate_limit(h2_opt, 100, 10);",
          "nghttp2_option_set_max_continuations(h2_opt, 2);", "nghttp2_option_set_max_settings(h2_opt, 16);",
          "nghttp2_option_set_max_outbound_ack(h2_opt, 64);", "nghttp2_option_set_max_outbound_queue_size(h2_opt, 256);",
          "nghttp2_session_server_new3(&h->sess, h2_cbs, c, h2_opt, &mem)", "#define MAX_CLIENTS	64")
      and "nghttp2_submit_push_promise" not in read("rednsd/rednsd.c"))
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
          # review 2026-11-11 (D-4): the lookup goes through mac_of() (one lookup per address, kept two seconds)
          "the longest-idle open connection makes room", "has_mac = mac_of(&a, mac) == 0;",
          "r = fam == AF_INET ? mac_v4(a, mac) : mac_v6(a, mac);",
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
