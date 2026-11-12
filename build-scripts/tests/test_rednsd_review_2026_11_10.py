#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rednsd (Encrypted DNS for devices): the five defects of the independent review of 2026-11-10.

WHY THIS EXISTS. The day DNS-over-HTTPS was added to rednsd, a read-only review of the daemon found five
defects, four of them older than the change. All five are fixed in rednsd.c; each was first shown with a
script that had to be run by hand against the real dnsmasq. This file keeps the same five proofs as one
regression test, so a later edit that brings one of them back fails here by name:
  F1  only rednsd may name a device to the resolver (EDNS0 option 65400). A query built so that the resolver
      would read a different OPT RR than the one rednsd edits - two OPT RRs, a type-250 (TSIG) RR next to the
      OPT RR, a TKEY question - used to be forwarded with the device's own forged option believed.
  F2  the DoH header-list limit counted only the fields the HTTP/2 library handed over. A field the library
      drops as invalid was free, so a one-byte HPACK reference to a 4 KB table entry cost a 4 KB scan each,
      without limit: one device could keep the single-threaded daemon busy and every other device waiting.
  F3  a client that stopped reading with answers left in the daemon's write buffer was never timed out, and
      once it had been silent for the idle time the main loop's poll() timeout stayed 0: one core spinning.
  F4  a policy reload (SIGHUP) refused a newly denied device's NEW connections but left its open ones working.
  F5  queries already decrypted inside the TLS library are not shown by poll(): after 16 queries in flight
      the rest of a TLS record could wait for ever.

WHAT IT DOES. Builds rednsd and the vendored nghttp2 from the given tree into a temporary directory, makes a
throwaway certificate, and runs two instances on loopback ports that are free at that moment (never the fixed
ports of test_rednsd.py). The resolver is a small UDP stand-in inside this process, not dnsmasq: it answers
every query and records, for each one, how many OPT RRs it carried and which address option 65400 named -
all that is needed to judge F1 at rednsd's own boundary - and it can hold answers back (F5) or make them
large (F3). The second instance serves F3 alone: its client is left blocked while the other four groups run
on the first, because the idle time (IDLE_MS, 30 s, a plain #define the build cannot shorten) has to pass.
  F1  over DoT and over DoH: the control (one OPT RR with a forged option) is answered and the resolver is
      told the real peer; each of the four constructions is refused (DoT: closed without an answer, DoH: 400)
      and never reaches the resolver.
  F2  30 requests whose header block is HPACK references to one invalid 4 KB field: none is answered 200 and
      the daemon's CPU time stays under a bound far above the fixed cost and far below the old one; the same
      block with a valid field still ends the session with GOAWAY ENHANCE_YOUR_CALM.
  F3  the blocked connection is held before the idle time, gone after it, and the daemon is not spinning.
  F4  after the reload the device's open DoT and DoH connections answer nothing more; a new one is refused.
  F5  36 queries in one TLS record, the first 32 filling the daemon's read buffer exactly: all 36 answered.
Then two source pins. Children are killed and the temporary directory removed at the end, also on failure.

REAPER_REDNSD_C=<path> tests that rednsd.c in place of the tree's (the vendored nghttp2 still comes from the
tree): run against the source as it was before the fixes, the F1-F5 checks must FAIL - that is how this test
was shown to have teeth.

Exit 0 pass, 1 fail, 77 skipped (no router source tree with rednsd and its nghttp2: release/src/router as
argv[1] or REAPER_ROUTER_SRC; no host compiler, no OpenSSL headers, no openssl command)."""
import base64, ctypes, glob, json, os, re, shutil, signal, socket, ssl, struct, subprocess, sys, tempfile, threading, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name); sys.stdout.flush()
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
NG = os.path.join(SRC, "rednsd", "nghttp2", "lib") if SRC else ""
REDC = os.environ.get("REAPER_REDNSD_C") or (os.path.join(SRC, "rednsd", "rednsd.c") if SRC else "")
if not SRC or not os.path.isfile(REDC) or not os.path.isfile(os.path.join(NG, "includes", "nghttp2", "nghttp2.h")):
    skip("no router source tree with rednsd and its vendored nghttp2 (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
OPENSSL = shutil.which("openssl")
if not CC or not OPENSSL or not os.path.exists("/usr/include/openssl/ssl.h"):
    skip("needs a host compiler, OpenSSL headers and the openssl command")
if not os.path.isdir("/proc/self"):
    skip("needs /proc (the daemon's CPU time is read there)")

REAPER_OPT = 65400
T_START = T_BUILT = time.time()
work = tempfile.mkdtemp(prefix="rednsd_rv_")
procs = []

def cleanup():
    for p in procs:
        if p.poll() is None:
            p.kill()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: pass
    shutil.rmtree(work, ignore_errors=True)

def watchdog():                              # nothing here may run without an end
    print("FAIL the test did not finish within 240 s"); sys.stdout.flush()
    cleanup(); os._exit(1)
wd = threading.Timer(240, watchdog); wd.daemon = True; wd.start()

def child_setup():                           # a child dies with this process, however this process ends
    try: ctypes.CDLL(None).prctl(1, signal.SIGKILL)      # PR_SET_PDEATHSIG
    except (OSError, AttributeError): pass

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p

# ---- DNS messages
def name_wire(name):
    return b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\0"
def opt_rr(opts):
    rd = b"".join(struct.pack(">HH", c, len(d)) + d for c, d in opts)
    return b"\0" + struct.pack(">HHIH", 41, 1232, 0, len(rd)) + rd
def dnsmsg(name, qtype=1, qid=0, opts=None, before_opt=b"", arcount=None):
    """one question; opts: an OPT RR with these options; before_opt: raw additional RRs placed ahead of it"""
    ar = arcount if arcount is not None else (1 if opts is not None else 0)
    m = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, ar) + name_wire(name) + struct.pack(">HH", qtype, 1) + before_opt
    return m + (opt_rr(opts) if opts is not None else b"")
def dot_frame(m): return struct.pack(">H", len(m)) + m
def skip_name(m, o):
    while o < len(m):
        l = m[o]
        if l == 0: return o + 1
        if l & 0xc0: return o + 2
        o += 1 + l
    raise ValueError("name runs off the message")
def scan(m):
    """(name, question type, where the question ends, OPT RRs in the additional section, addresses named by option 65400)"""
    qd, an, ns, ar = struct.unpack(">HHHH", m[4:12])
    labels, o = [], 12
    while m[o]:
        labels.append(m[o + 1:o + 1 + m[o]].decode("latin-1")); o += 1 + m[o]
    qtype = struct.unpack(">H", m[o + 1:o + 3])[0]
    o = qend = o + 5
    for _ in range(qd - 1): o = skip_name(m, o) + 4
    nopt, named = 0, []
    for i in range(an + ns + ar):
        o = skip_name(m, o)
        typ, _cls, _ttl, rdlen = struct.unpack(">HHIH", m[o:o + 10]); rd = m[o + 10:o + 10 + rdlen]; o += 10 + rdlen
        if i < an + ns or typ != 41: continue
        nopt += 1; p = 0
        while p + 4 <= len(rd):
            code, l = struct.unpack(">HH", rd[p:p + 4]); v = rd[p + 4:p + 4 + l]; p += 4 + l
            if code != REAPER_OPT: continue
            if len(v) == 5 and v[0] == 1: named.append(socket.inet_ntoa(v[1:]))
            elif len(v) == 17 and v[0] == 2: named.append(socket.inet_ntop(socket.AF_INET6, v[1:]))
            else: named.append("?" + v.hex())
    return ".".join(labels), qtype, qend, nopt, named

# ---- the resolver stand-in: answers every query, records what it was sent
class Resolver(threading.Thread):
    """A label "padN" in the name: a TXT answer with N bytes of data. A label "slow": the answer waits until
    16 such queries have arrived, then all 16 go out together (rednsd has 16 in flight per DoT connection)."""
    def __init__(self):
        threading.Thread.__init__(self); self.daemon = True
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); self.s.bind(("127.0.0.1", 0)); self.s.settimeout(0.2)
        self.port = self.s.getsockname()[1]
        self.lock = threading.Lock(); self.log = {}; self.held = []; self.stop = False; self.bad = 0
    def run(self):
        while not self.stop:
            try: m, frm = self.s.recvfrom(65535)
            except socket.timeout: continue
            except OSError: break
            try: name, qtype, qend, nopt, named = scan(m)
            except (ValueError, IndexError, struct.error, UnicodeError):
                self.bad += 1; continue
            with self.lock: self.log.setdefault(name, []).append((qtype, nopt, named))
            pad = [int(l[3:]) for l in name.split(".") if re.match(r"pad\d+$", l)]
            if pad:
                rd, left = b"", pad[0]
                while left > 0:
                    k = min(255, left - 1); rd += bytes([k]) + b"x" * k; left -= k + 1
                rr = struct.pack(">HHHIH", 0xc00c, 16, 1, 300, len(rd)) + rd
            else:
                rr = struct.pack(">HHHIH", 0xc00c, 1, 1, 300, 4) + socket.inet_aton("192.0.2.1")
            a = m[:2] + struct.pack(">HHHHH", 0x8180, 1, 1, 0, 0) + m[12:qend] + rr
            if "slow" in name.split("."):
                self.held.append((a, frm))
                if len(self.held) < 16: continue
                out, self.held = self.held, []
            else:
                out = [(a, frm)]
            for x, to in out:
                try: self.s.sendto(x, to)
                except OSError: pass
    def seen(self, name):
        with self.lock: return list(self.log.get(name, []))
    def count(self, name):
        with self.lock: return len(self.log.get(name, []))

# ---- one rednsd under test
class Daemon:
    def __init__(self, tag, binary, cert, key, upstream):
        self.dot, self.doh = free_port(), free_port()
        self.status, self.conf = os.path.join(work, tag + ".status"), os.path.join(work, tag + ".conf")
        open(self.conf, "w").write("cert %s\nkey %s\nstatus %s\nlisten 127.0.0.1 %d\nlisten 127.0.0.1 %d doh\npeer 127.0.0.0/24 127.0.0.1#%d\n"
                                   % (cert, key, self.status, self.dot, self.doh, upstream))
        self.err = open(os.path.join(work, tag + ".err"), "wb")
        self.p = subprocess.Popen([binary, "-f", "-c", self.conf], stdout=subprocess.DEVNULL, stderr=self.err, preexec_fn=child_setup)
        procs.append(self.p)
    def up(self):
        for _ in range(60):
            if self.p.poll() is not None: return False
            try:
                socket.create_connection(("127.0.0.1", self.dot), 1).close(); socket.create_connection(("127.0.0.1", self.doh), 1).close()
                return True
            except OSError: time.sleep(0.1)
        return False
    def alive(self): return self.p.poll() is None
    def cpu(self):                           # user + system seconds so far
        f = open("/proc/%d/stat" % self.p.pid).read().rsplit(")", 1)[1].split()
        return (int(f[11]) + int(f[12])) / float(os.sysconf("SC_CLK_TCK"))
    def stat(self):                          # a fresh status file (SIGUSR1), as a dict
        try: before = os.stat(self.status).st_mtime_ns
        except OSError: before = 0
        self.p.send_signal(signal.SIGUSR1)
        for _ in range(60):
            time.sleep(0.05)
            try:
                if os.stat(self.status).st_mtime_ns != before: return json.load(open(self.status))
            except (OSError, ValueError): pass
        return {}

# ---- clients
def tls(src, port, alpn, rcvbuf=None, timeout=5):
    cx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); cx.check_hostname = False; cx.verify_mode = ssl.CERT_NONE
    cx.set_alpn_protocols(alpn)
    raw = socket.socket(); raw.settimeout(timeout)
    if rcvbuf: raw.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
    raw.bind((src, 0)); raw.connect(("127.0.0.1", port))
    return cx.wrap_socket(raw)
def recv_msg(s):
    """one DoT answer; None when the connection ends or nothing comes"""
    try:
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
    except (socket.timeout, ssl.SSLError, OSError):
        return None

# a hand-written HTTP/2 client: frames, and header fields as HPACK literals
PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
DATA, HEADERS, RST, SETTINGS, GOAWAY, WUPD, CONT = 0, 1, 3, 4, 7, 8, 9
ST200, ST400 = b"\x88", b"\x8c"              # ":status: 200" and ":status: 400" as HPACK static-table references
def frame(typ, flags, sid, payload=b""):
    return struct.pack(">I", len(payload))[1:] + bytes([typ, flags]) + struct.pack(">I", sid) + payload
def hp_str(sv):
    b = sv if isinstance(sv, bytes) else sv.encode()
    n = len(b)
    if n < 127: return bytes([n]) + b
    n -= 127; out = b"\x7f"
    while n >= 128: out += bytes([n % 128 + 128]); n //= 128
    return out + bytes([n]) + b
def req_headers(method="POST", path="/dns-query", clen=None):
    hs = [(":method", method), (":scheme", "https"), (":authority", "test.example"), (":path", path)]
    if method == "POST": hs.append(("content-type", "application/dns-message"))
    if clen is not None: hs.append(("content-length", str(clen)))
    return b"".join(b"\x00" + hp_str(k) + hp_str(v) for k, v in hs)          # literal, not indexed
def h2_post(sid, msg):
    return frame(HEADERS, 0x4, sid, req_headers(clen=len(msg))) + frame(DATA, 0x1, sid, msg)
b64u = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
class H2:
    def __init__(self, src, port, settings=b"", rcvbuf=None, connwin=0):
        self.s = tls(src, port, ["h2"], rcvbuf); self.buf = b""; self.fr = []; self.eof = False
        self.s.sendall(PREFACE + frame(SETTINGS, 0, 0, settings) + (frame(WUPD, 0, 0, struct.pack(">I", connwin)) if connwin else b""))
    def send(self, b): self.s.sendall(b)
    def read(self, until, timeout=5):
        """frames so far as (type, flags, stream, payload); reads until until(frames), the end of the connection or the timeout"""
        end = time.time() + timeout; self.s.settimeout(0.2)
        while not self.eof and not until(self.fr) and time.time() < end:
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
    def status(self, sid):                   # the first byte of the response's header block
        for f in self.fr:
            if f[0] == HEADERS and f[2] == sid: return f[3][:1]
        return None
    def body(self, sid): return b"".join(f[3] for f in self.fr if f[0] == DATA and f[2] == sid)
    def ended(self, sid): return any(f[2] == sid and (f[0] == RST or (f[0] in (DATA, HEADERS) and f[1] & 1)) for f in self.fr)
    def goaway(self): return [struct.unpack(">II", f[3][:8])[1] for f in self.fr if f[0] == GOAWAY]
    def close(self):
        try: self.s.close()
        except OSError: pass

res = None
skipped = ""
try:
    # ---- build: nghttp2 the way the firmware Makefile does (its own -D list in place of config.h), then rednsd
    red = open(REDC, encoding="utf-8", errors="replace").read()
    mk = open(os.path.join(SRC, "rednsd", "Makefile"), encoding="utf-8", errors="replace").read()
    m = re.search(r"^NGH2_DEFS[ \t]*=((?:.*\\\n)*.*)$", mk, re.M)
    NGDEFS = m.group(1).replace("\\\n", " ").split() if m else []
    ngsrc = sorted(glob.glob(os.path.join(NG, "*.c")))
    ngdir = os.path.join(work, "ng"); os.makedirs(ngdir)
    jobs = [subprocess.Popen([CC, "-c", "-O2", "-DNGHTTP2_STATICLIB"] + NGDEFS + ["-I", os.path.join(NG, "includes"), "-I", NG] + ngsrc[i::4],
                             cwd=ngdir, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for i in range(4)]
    errs = b"".join(j.communicate(timeout=600)[1] for j in jobs)
    NGOBJ = sorted(glob.glob(os.path.join(ngdir, "*.o")))
    RB = os.path.join(work, "rednsd")
    b = subprocess.run([CC, "-O2", "-Wall", "-DNGHTTP2_STATICLIB", "-I", os.path.join(NG, "includes"), "-o", RB, REDC] + NGOBJ + ["-lssl", "-lcrypto"],
                       capture_output=True, text=True, timeout=600)
    check("rednsd and the vendored nghttp2 (%d sources) build for the host" % len(ngsrc),
          NGDEFS and ngsrc and len(NGOBJ) == len(ngsrc) and all(j.returncode == 0 for j in jobs) and b.returncode == 0,
          (errs.decode(errors="replace")[-300:], b.stderr[-500:]))
    if fails: raise SystemExit
    cert, key = os.path.join(work, "cert.pem"), os.path.join(work, "key.pem")
    r = subprocess.run([OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", "/CN=test.example", "-keyout", key, "-out", cert],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        skipped = "the openssl command cannot make a test certificate: " + r.stderr[-200:]
        raise SystemExit
    m = re.search(r"^#define\s+IDLE_MS\s+(\d+)", red, re.M)
    IDLE = int(m.group(1)) / 1000.0 if m else 30.0

    res = Resolver(); res.start()
    d1 = Daemon("one", RB, cert, key, res.port)          # F1, F2, F4, F5
    d2 = Daemon("two", RB, cert, key, res.port)          # F3 alone: its CPU time and its connection count are its own
    check("two rednsd instances start on ports free at this moment (DoT %d / DoH %d, DoT %d / DoH %d), resolver stand-in on UDP %d"
          % (d1.dot, d1.doh, d2.dot, d2.doh, res.port), d1.up() and d2.up(), (d1.alive(), d2.alive()))
    if fails: raise SystemExit
    T_BUILT = time.time()

    # ---- F3, first half: fill the daemon's socket and write buffer with answers the client never reads
    # The window is opened wide, so only TCP holds the answers back. While rednsd cannot write to a DoH client it
    # reads nothing more from it: the moment the stand-in stops seeing queries, answers are waiting in rednsd.
    F3N = "pad4000.f3.test"
    c3 = H2("127.0.0.3", d2.doh, struct.pack(">HI", 4, 0x7fffffff), rcvbuf=4096, connwin=0x7fffffff - 65535)
    c3.s.settimeout(1.0)
    blocked, quiet, sid = False, 0, 1
    for _ in range(2500):                                # 8 x 4 KB a turn: 80 MB at the very most, far past any socket buffer
        n0 = res.count(F3N)
        try: c3.s.sendall(b"".join(h2_post(sid + 2 * i, dnsmsg(F3N, 16, i)) for i in range(8)))
        except (socket.timeout, ssl.SSLError, OSError): blocked = True; break
        sid += 16
        end = time.time() + 0.75
        while res.count(F3N) == n0 and time.time() < end: time.sleep(0.002)
        quiet = quiet + 1 if res.count(F3N) == n0 else 0
        if quiet >= 2: blocked = True; break             # two turns in a row not read at all
        time.sleep(0.002)
    t_block = time.time()
    st = d2.stat()
    check("F3: a DoH client that reads nothing gets rednsd write-blocked (%d queries answered, then no more are read), and its connection is held"
          % res.count(F3N), blocked and res.count(F3N) >= 8 and st.get("conns") == 1, (blocked, res.count(F3N), st.get("conns")))

    # ---- F1: only rednsd names the device
    forged = (REAPER_OPT, b"\x01" + socket.inet_aton("192.0.2.66"))
    T250_IN = b"\0" + struct.pack(">HHIH", 250, 1, 0, 0)                 # a type-250 (TSIG) RR, class IN, empty
    T250_ANY = b"\0" + struct.pack(">HHIH", 250, 255, 0, 0)              # ... class ANY, as a real TSIG has
    DEV = "127.0.0.2"
    cases = [
        ("two OPT RRs, the forged option in the second", lambda n: dnsmsg(n, opts=[forged], before_opt=opt_rr([]), arcount=2)),
        ("a type-250 RR ahead of the OPT RR", lambda n: dnsmsg(n, opts=[forged], before_opt=T250_IN, arcount=2)),
        ("an OPT RR followed by a type-250 class-ANY RR", lambda n: dnsmsg(n, opts=[forged], arcount=2) + T250_ANY),
        ("a TKEY (type 249) question", lambda n: dnsmsg(n, qtype=249)),
    ]
    for proto in ("DoT", "DoH"):
        def ask(m, qid_ok=None):
            """(answered, what came back)"""
            if proto == "DoT":
                s = tls(DEV, d1.dot, ["dot"], timeout=3); s.sendall(dot_frame(m)); a = recv_msg(s); s.close()
                return (a is not None, a[:4] if a else None)
            c = H2(DEV, d1.doh); c.send(h2_post(1, m)); c.read(lambda fr: c.ended(1), 3); r = (c.status(1), c.body(1)[:4]); c.close()
            return (r[0] == ST200, r)
        n = "f1-ctl-%s.test" % proto.lower()
        got, what = ask(dnsmsg(n, qid=0x4242, opts=[forged])); time.sleep(0.1)
        seen = res.seen(n)
        check("F1 %s control: a query with one OPT RR and a forged option 65400 is answered, and the resolver is told the real peer (%s) in the one OPT RR"
              % (proto, DEV), got and len(seen) == 1 and seen[0][1] == 1 and seen[0][2] == [DEV], (what, seen))
        for i, (what, mk) in enumerate(cases):
            n = "f1-%s-%d.test" % (proto.lower(), i)
            got, back = ask(mk(n)); time.sleep(0.15)
            seen = res.seen(n)
            refused = not got and (proto == "DoT" or back[0] == ST400)
            check("F1 %s: %s is refused (%s) and never reaches the resolver" % (proto, what, "closed, no answer" if proto == "DoT" else "400"),
                  refused and not seen, (back, seen))

    # ---- F2: fields the HTTP/2 library drops count toward the header list
    # One field of about 4 KB goes into the HPACK dynamic table (index 62); after it every byte 0xBE is that field again.
    def hpack_run(src, value, rounds):
        c = H2(src, d1.doh); c.read(lambda fr: any(f[0] == SETTINGS for f in fr), 3)
        sent, sid, cpu0 = 0, 1, d1.cpu()
        for r in range(rounds):
            hb = req_headers("GET", "/dns-query?dns=" + b64u(dnsmsg("f2.test")))
            if r == 0: hb += b"\x40" + hp_str("x") + hp_str(value)       # literal with incremental indexing
            hb += b"\xbe" * (3 * 16384 - len(hb))
            fr = frame(HEADERS, 0x1, sid, hb[:16384]) + frame(CONT, 0, sid, hb[16384:32768]) + frame(CONT, 0x4, sid, hb[32768:])
            try: c.send(fr)
            except (ssl.SSLError, OSError): break
            sent += len(fr)
            c.read(lambda f: c.ended(sid) or c.goaway(), 20)
            if c.goaway() or c.eof: break
            sid += 2
        used = d1.cpu() - cpu0
        ok200 = sorted(f[2] for f in c.fr if f[0] == HEADERS and f[3][:1] == ST200)
        go = c.goaway(); c.close()
        return sent, used, ok200, go
    ROUNDS = 30
    sent, used, ok200, go = hpack_run("127.0.0.6", b"a" * 4050 + b"\x01", ROUNDS)      # a control byte: the library drops the field
    bound = max(0.4, 0.25 * sent / 1048576.0)
    check("F2: %d requests made of HPACK references to one invalid 4 KB field: none is answered 200" % ROUNDS,
          sent >= 49000 and not ok200, (sent, ok200, go))
    check("F2: ...and they cost the daemon little CPU (%.2f s for %.1f MB sent; the bound is %.2f s, the unfixed daemon needed about 1 s per MB)"
          % (used, sent / 1048576.0, bound), sent >= 49000 and used <= bound, (sent, used, bound))
    sent, used, ok200, go = hpack_run("127.0.0.6", b"a" * 4051, 3)                     # the same block, the field valid
    check("F2 control: the same block with a valid field ends the session with GOAWAY ENHANCE_YOUR_CALM (11), unanswered", go == [11] and not ok200, (go, ok200))

    # ---- F4: a policy reload reaches the connections that are open
    GONE = "127.0.0.4"
    h4 = H2(GONE, d1.doh); h4.send(h2_post(1, dnsmsg("f4-a.test", qid=1))); h4.read(lambda fr: h4.ended(1), 3)
    t4 = tls(GONE, d1.dot, ["dot"], timeout=3); t4.sendall(dot_frame(dnsmsg("f4-b.test", qid=2))); a = recv_msg(t4)
    check("F4: before the reload the device is served over DoT and over DoH", h4.status(1) == ST200 and a is not None, (h4.status(1), a))
    open(d1.conf, "a").write("deny-net %s/32\n" % GONE)
    d1.p.send_signal(signal.SIGHUP); time.sleep(0.6)
    try:
        x = tls(GONE, d1.dot, ["dot"], timeout=3); x.sendall(dot_frame(dnsmsg("f4-c.test", qid=3))); new = recv_msg(x); x.close()
    except (ssl.SSLError, OSError):
        new = None
    check("F4: after a reload that denies the device, a new connection from it is refused", new is None and not res.seen("f4-c.test"), new)
    try: t4.sendall(dot_frame(dnsmsg("f4-d.test", qid=4))); a = recv_msg(t4)
    except (ssl.SSLError, OSError): a = None
    check("F4: ...and the DoT connection it already had answers nothing more", a is None and not res.seen("f4-d.test"), a)
    try: h4.send(h2_post(3, dnsmsg("f4-e.test", qid=5))); h4.read(lambda fr: h4.ended(3), 3)
    except (ssl.SSLError, OSError): pass
    check("F4: ...nor does the DoH connection it already had", h4.status(3) is None and not res.seen("f4-e.test"), (h4.status(3), h4.eof))
    h4.close(); t4.close()
    y = tls(DEV, d1.dot, ["dot"], timeout=3); y.sendall(dot_frame(dnsmsg("f4-f.test", qid=6))); a = recv_msg(y); y.close()
    check("F4: a device the reload did not deny is still served", a is not None and a[:2] == b"\0\6", a)

    # ---- F5: the whole TLS record is read
    # rednsd's read buffer takes 4098 bytes at a time and at most 16 queries are in flight on a connection. 32 "slow"
    # queries fill the buffer exactly; the stand-in answers them 16 at a time, so the buffer is empty at the very
    # moment 16 are in flight - and the last four queries of the record are still inside the TLS library.
    def sized(total, qid):                   # a DoT message of exactly this many bytes on the wire, with a label "slow"
        left = total - 2 - 12 - 4 - 1 - 5    # length prefix, header, type + class, root, the label "slow"
        labels = ["slow"]
        while left > 0:
            k = min(63, left - 1)
            if left - (k + 1) == 1: k -= 1   # never leave a single byte: a label needs two
            labels.append("q" * k); left -= k + 1
        f = dot_frame(dnsmsg(".".join(labels), qid=qid)); assert len(f) == total, (len(f), total)
        return f
    first = b"".join(sized(128, i) for i in range(31)) + sized(130, 31)
    assert len(first) == 4098
    tail = b"".join(dot_frame(dnsmsg("f5-tail-%d.test" % i, qid=100 + i)) for i in range(4))
    s5 = tls("127.0.0.5", d1.dot, ["dot"], timeout=1)
    s5.sendall(first + tail)                 # well under 16 KB: one TLS record
    ids, end = set(), time.time() + 6
    while len(ids) < 36 and time.time() < end:
        a = recv_msg(s5)
        if a: ids.add(struct.unpack(">H", a[:2])[0])
    s5.close()
    check("F5: 36 DoT queries in one TLS record, the first 32 filling the read buffer exactly: all 36 are answered (the last four too)",
          ids == set(range(32)) | set(range(100, 104)), (len(ids), sorted(i for i in ids if i >= 100)))
    check("rednsd is still up after F1, F2, F4 and F5, and the stand-in parsed everything it was sent", d1.alive() and res.bad == 0, (d1.alive(), res.bad))

    # ---- F3, second half: past the idle time
    wait = t_block + IDLE + 1.5 - time.time()
    if wait > 0: time.sleep(wait)
    cpu0 = d2.cpu(); time.sleep(2.0); spin = d2.cpu() - cpu0
    st = d2.stat()
    check("F3: %.0f s after its last answer the client that never read is disconnected (the daemon holds no connection)" % IDLE,
          d2.alive() and st.get("conns") == 0, (d2.alive(), st.get("conns")))
    check("F3: ...and the daemon is not spinning: %.2f s of CPU in the 2 s after that (the unfixed daemon used all 2 s)" % spin,
          spin <= 0.5, spin)
    c3.close()

    # ---- source pins
    check("source: the DoH session registers a callback for the header fields nghttp2 drops (F2)",
          "nghttp2_session_callbacks_set_on_invalid_header_callback(" in red)
    check("source: the main loop asks the TLS library whether it holds more than poll() shows (F5)", "SSL_pending(" in red)
except SystemExit:
    pass
except (OSError, ssl.SSLError, ValueError, IndexError, KeyError, struct.error, subprocess.SubprocessError) as e:
    check("the checks ran to their end", False, repr(e))
finally:
    wd.cancel()
    if res: res.stop = True
    cleanup()

if skipped:
    skip(skipped)
print("")
if fails:
    print("%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed (%.0f s, %.0f s of it the build)" % (time.time() - T_START, T_BUILT - T_START))
