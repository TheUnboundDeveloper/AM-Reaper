#!/usr/bin/env python3
"""Audit Findings remediation of 2026-11-24: the three small fixes.

  REAPER-DUT-REDIR-SELF  httpd: the address typed for the login redirect counts as the router's own name only
                         while the redirect is on (review 2026-11-24).
  REAPER-TWO-OPT         dnsmasq: a query with more than one OPT record is answered FORMERR (RFC 6891 6.1.1),
                         over UDP and TCP; one OPT, no OPT and a packet that cannot be walked behave as before
                         (review 2026-11-11, Appendix A).
  REAPER-MC-MAXNODES     AiMesh channel fit: room for every node AiMesh can pair plus the router (17), and the
                         nodes' lists are read whole (review 2026-11-11, C-8).

The dnsmasq half builds the tree's dnsmasq on the host and talks to it on 127.0.0.1 (no root, no namespace).
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, shutil, socket, struct, subprocess, sys, tempfile, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "dnsmasq", "src", "edns0.c")):
    skip("no router source tree with dnsmasq/src/edns0.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

# ---------------------------------------------------------------- login redirect
h = rd("httpd", "httpd.c")
m = re.search(r"static int reaper_host_is_self\(const char \*h\)\n\{.*?\n\}\n", h, re.S)
check("httpd: reaper_host_is_self() is there", bool(m))
body = m.group(0) if m else ""
check("the typed redirect address is compared only while http_dut_redir is 1",
      'if (!strcmp(nvram_safe_get("http_dut_redir"), "1") && dh[0] && rdr_host_ok(dh) && !strcasecmp(h, dh))' in body)
check("...and no second, ungated comparison of that address is left",
      len(re.findall(r"strcasecmp\(h, dh\)", body)) == 1)
check("the router's address and own names are still accepted without the switch",
      'nvram_safe_get("lan_ipaddr")' in body and "DUT_DOMAIN_NAME" in body and "lan_hostname" in body)

# ---------------------------------------------------------------- channel fit
mc = rd("rc", "reaper_meshchan.c")
check("channel fit: 17 entries (16 nodes and the router)", re.search(r"^#define MC_MAXNODES\t17$", mc, re.M) is not None)
check("...with a compile-time guard against a larger AiMesh node limit",
      "#if defined(RTCONFIG_MAX_RE) && (RTCONFIG_MAX_RE + 1 > MC_MAXNODES)\n#error" in mc)
check("...and the nodes' lists are read into 65536-byte buffers", "static char buf[65536], have[65536]," in mc and "[24576]" not in mc)
cfg = os.path.join(SRC, ".config")
if os.path.isfile(cfg):
    mm = re.search(r"^RTCONFIG_MAX_RE=(\d+)$", open(cfg, errors="replace").read(), re.M)
    check("the tree's AiMesh node limit fits (RTCONFIG_MAX_RE + 1 <= 17)", mm is None or int(mm.group(1)) + 1 <= 17, mm and mm.group(1))

# ---------------------------------------------------------------- dnsmasq: source pins
ed = rd("dnsmasq", "src", "edns0.c"); fw = rd("dnsmasq", "src", "forward.c"); dh = rd("dnsmasq", "src", "dnsmasq.h")
check("dnsmasq: reaper_two_opt_reply() defined once and declared", ed.count("size_t reaper_two_opt_reply(struct dns_header *header, size_t plen)\n{") == 1
      and "size_t reaper_two_opt_reply(struct dns_header *header, size_t plen);" in dh)
check("...called on the UDP path before the query is logged or read", fw.count("reaper_two_opt_reply(header, (size_t)n)") == 1
      and fw.find("reaper_two_opt_reply(header, (size_t)n)") < fw.find("  else if (extract_request(header, (size_t)n, daemon->namebuff, &type, NULL))"))
check("...and on the TCP path before the edns0 options are edited", fw.count("reaper_two_opt_reply(header, (size_t)size)") == 1
      and fw.find("reaper_two_opt_reply(header, (size_t)size)") < fw.find("size = add_edns0_config(header, size, daemon->packet_buff_sz, &peer_addr, now, &cacheable);"))

# ---------------------------------------------------------------- dnsmasq: the real thing
def qname(n):
    return b"".join(bytes([len(x)]) + x.encode() for x in n.split(".")) + b"\0"

def opt(rdata=b"", size=1232):
    return b"\0" + struct.pack(">HHIH", 41, size, 0, len(rdata)) + rdata

def query(qid, name, extra=(), raw_tail=b"", arcount=None):
    ar = len(extra) if arcount is None else arcount
    return struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, ar) + qname(name) + struct.pack(">HH", 1, 1) + b"".join(extra) + raw_tail

def udp(port, pkt, wait=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(wait)
    try:
        s.sendto(pkt, ("127.0.0.1", port))
        return s.recvfrom(4096)[0]
    except socket.timeout:
        return None
    finally:
        s.close()

def tcp(port, pkts, wait=3.0):
    """several queries on one connection; the list of replies (None for a missing one)"""
    out = []
    s = socket.create_connection(("127.0.0.1", port), timeout=wait)
    try:
        for pkt in pkts:
            s.sendall(struct.pack(">H", len(pkt)) + pkt)
            try:
                hd = b""
                while len(hd) < 2:
                    c = s.recv(2 - len(hd))
                    if not c:
                        raise OSError("closed")
                    hd += c
                n = struct.unpack(">H", hd)[0]; b = b""
                while len(b) < n:
                    c = s.recv(n - len(b))
                    if not c:
                        raise OSError("closed")
                    b += c
                out.append(b)
            except (OSError, socket.timeout):
                out.append(None)
    finally:
        s.close()
    return out

def hdr(r):
    qid, fl, qd, an, ns, ar = struct.unpack(">HHHHHH", r[:12])
    return dict(id=qid, qr=fl >> 15, rcode=fl & 15, qd=qd, an=an, ns=ns, ar=ar)

if not CC or not shutil.which("make"):
    print("note the run needs make and a C compiler on the host - the source pins above were checked, the run is skipped")
else:
    tmp = tempfile.mkdtemp(prefix="dnsmasq_twoopt_")
    proc = None
    try:
        db = os.path.join(tmp, "dnsmasq")
        shutil.copytree(os.path.join(SRC, "dnsmasq"), db, symlinks=True,
                        ignore=shutil.ignore_patterns("*.o", "dnsmasq", ".git", "po", "contrib"))
        b = subprocess.run(["make", "-C", db, "COPTS=-DNO_DBUS -DNO_INOTIFY -DHAVE_BROKEN_RTC", "CC=" + CC, "-j4"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=900)
        exe = os.path.join(db, "src", "dnsmasq")
        check("dnsmasq builds on the host", b.returncode == 0 and os.path.isfile(exe), b.stdout[-600:])
        warn = [l for l in b.stdout.splitlines() if "warning" in l and ("two_opt" in l or "REAPER-TWO-OPT" in l)]
        check("...with no compiler warning from the new code", not warn, warn[:3])
        if os.path.isfile(exe):
            s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
            log = os.path.join(tmp, "log")
            # -d: no fork and no change of user; no upstream, one local name
            proc = subprocess.Popen([exe, "-d", "--conf-file=/dev/null", "--port=%d" % port, "--listen-address=127.0.0.1",
                                     "--bind-interfaces", "--no-resolv", "--no-hosts", "--address=/one.test/192.0.2.7",
                                     "--pid-file=" + os.path.join(tmp, "pid"), "--cache-size=0"],
                                    stdout=open(log, "w"), stderr=subprocess.STDOUT)
            up = None
            for _ in range(50):
                time.sleep(0.1)
                if proc.poll() is not None:
                    break
                up = udp(port, query(1, "one.test"), wait=0.3)
                if up:
                    break
            check("dnsmasq starts and answers a plain query", bool(up) and hdr(up)["rcode"] == 0 and hdr(up)["an"] == 1,
                  open(log, errors="replace").read()[-600:])
            if up:
                client = struct.pack(">HH", 65400, 5) + b"\x01" + bytes([192, 0, 2, 99])	# the private device option
                r = udp(port, query(2, "one.test", [opt()]))
                check("UDP, one OPT: answered as before (NOERROR, one answer)", bool(r) and hdr(r)["rcode"] == 0 and hdr(r)["an"] == 1, r and hdr(r))
                r = udp(port, query(3, "one.test", [opt(), opt()]))
                check("UDP, two OPT: FORMERR", bool(r) and hdr(r)["rcode"] == 1, r and hdr(r))
                check("...a reply to this query (same id, QR set), question kept, no other record",
                      bool(r) and hdr(r)["id"] == 3 and hdr(r)["qr"] == 1 and (hdr(r)["qd"], hdr(r)["an"], hdr(r)["ns"], hdr(r)["ar"]) == (1, 0, 0, 0)
                      and r[12:] == qname("one.test") + struct.pack(">HH", 1, 1), r and (hdr(r), r[12:]))
                r = udp(port, query(4, "one.test", [opt(client), opt()]))
                check("UDP, two OPT with the device option in the first: FORMERR", bool(r) and hdr(r)["rcode"] == 1, r and hdr(r))
                r = udp(port, query(5, "one.test", [opt(), opt(), opt()]))
                check("UDP, three OPT: FORMERR", bool(r) and hdr(r)["rcode"] == 1, r and hdr(r))
                txt = b"\0" + struct.pack(">HHIH", 16, 1, 0, 2) + b"\x01x"
                r = udp(port, query(6, "one.test", [txt, opt()]))
                check("UDP, another record and one OPT: not a format error", bool(r) and hdr(r)["rcode"] == 0 and hdr(r)["an"] == 1, r and hdr(r))
                # two OPT announced, the second cut short: the packet cannot be walked - not ours to answer
                r = udp(port, query(7, "one.test", [opt()], raw_tail=b"\0\0\x29\x04", arcount=2), wait=1.0)
                check("UDP, a second record cut short: no FORMERR from the new code", r is None or hdr(r)["rcode"] != 1, r and hdr(r))
                rs = tcp(port, [query(8, "one.test", [opt()]), query(9, "one.test", [opt(), opt()]), query(10, "one.test")])
                check("TCP, one OPT: answered as before", bool(rs[0]) and hdr(rs[0])["rcode"] == 0 and hdr(rs[0])["an"] == 1, rs[0] and hdr(rs[0]))
                check("TCP, two OPT: FORMERR, same id, question only", bool(rs[1]) and hdr(rs[1])["rcode"] == 1 and hdr(rs[1])["id"] == 9
                      and (hdr(rs[1])["qd"], hdr(rs[1])["an"], hdr(rs[1])["ar"]) == (1, 0, 0), rs[1] and hdr(rs[1]))
                check("TCP: the connection goes on to serve the next query", bool(rs[2]) and hdr(rs[2])["rcode"] == 0 and hdr(rs[2])["an"] == 1, rs[2] and hdr(rs[2]))
                r = udp(port, query(11, "one.test"))
                check("dnsmasq is still running and answering after all of it", proc.poll() is None and bool(r) and hdr(r)["an"] == 1)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: the login redirect gate, the two-OPT refusal and the channel fit's node limit hold")
