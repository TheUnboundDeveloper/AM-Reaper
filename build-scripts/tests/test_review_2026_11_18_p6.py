#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-17, Phase 6 fixes (batch p8, 2026-11-18) - each fix RUN on the host where it can be.

  P6-5-P1  Guest Portal (CoovaChilli) DNS answer: the question is copied label by label within the payload
           (reaper_dns_qcopy, compiled from the REAPER-PREAUTH block); a question ending in a compression pointer,
           running past the payload or too long for the buffer is not answered. The stock zero-byte loop is gone.
  P6-4-W1  Wallguard safe search: wallguard.sh RUN under stand-in tools - a file left without addresses is logged,
           marked owed (0 at WAN up, back-off once the WAN is up), refreshed by `retry` with no list owed and by an
           update restricted to one list, and the mark clears (with a log line) once every group has an address.
  P6-4-G1  diag: the new arg stage, run under busybox awk / gawk / mawk on made-up lines (cron line with a token,
           command line with an API key, a Bearer header, URL credentials; and lines that must stay as they are).
  P6-4-G2/G3 diag: the literal classifier, run on a made-up nvram dump: wanN_domain, log_ipaddr, the VPN client
           servers and a typed NTP server are host names; the shipped NTP pools stay readable.
  P6-3-D2  rc/sdn.c _write_dhcp_reservation compiled on the host with shutils' own MAC helpers: the MAC is canonical
           in every line of a row (the DNS option's tag now matches the host line), a row with a bad MAC writes
           nothing, and a line break hidden after a MAC never reaches the file.
  P6-3-S1/S2/S3  rc/services.c, source pins: the UPnP reload forks in rc (notify_rc only outside), the network
           handlers restart the resolvers directly, the UPnP deny list reads each WireGuard server's own keys.
Exit 0 pass, 1 fail, 77 skipped (no router source: pass release/src/router or set REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile, time

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "services.c")):
    print("SKIP: no router source tree"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
SH = shutil.which("sh")
if not CC or not SH:
    print("SKIP: no host C compiler or no sh"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

def extract(src, signature):
    i = src.index(signature); j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    raise ValueError(signature)

def rd(p):
    try:
        with open(p) as fh: return fh.read()
    except OSError:
        return ""

td = tempfile.mkdtemp(prefix="p8p6-")
try:
    # ======================= P6-5-P1 chilli =======================
    dh = read("coovachilli/src/dhcp.c")
    m = re.search(r"/\* REAPER-PREAUTH-BEGIN.*?\*/(.*?)/\* REAPER-PREAUTH-END \*/", dh, re.S)
    check("chilli: the REAPER-PREAUTH block holds reaper_dns_qcopy", m is not None and "static size_t reaper_dns_qcopy(" in (m.group(1) if m else ""))
    if m:
        c1 = os.path.join(td, "q.c"); g1 = os.path.join(td, "q")
        with open(c1, "w") as fh:
            fh.write("#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <stdint.h>\n" + m.group(1) + r'''
static unsigned char hx(char c) { return (unsigned char)(c <= '9' ? c - '0' : c - 'a' + 10); }
int main(int argc, char **argv) { unsigned char b[600], o[600]; size_t n = 0; const char *h = argv[1]; size_t r;
	while (h[0] && h[1] && n < sizeof(b)) { b[n++] = (unsigned char)(hx(h[0]) << 4 | hx(h[1])); h += 2; }
	r = reaper_dns_qcopy(b, n, o, (size_t)atoi(argv[2]));
	printf("%zu %d\n", r, r ? !memcmp(o, b, r) : 1); return 0; }
''')
        r = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", g1, c1], capture_output=True, text=True)
        check("chilli: the block compiles with -Wall -Werror", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            def q(hexs, outmax=256):
                return subprocess.run([g1, hexs, str(outmax)], capture_output=True, text=True).stdout.split()
            L = "066c6f676f7574"                       # \6logout
            check("chilli: a plain question (logout, A, IN) is copied whole: 12 bytes, byte for byte",
                  q(L + "00" + "00010001") == ["12", "1"], q(L + "00" + "00010001"))
            check("chilli: with trailing records, only the question is copied",
                  q(L + "00" + "00010001" + "c00c00010001") == ["12", "1"])
            check("chilli: a question ending in a COMPRESSION POINTER (the leak) is refused",
                  q(L + "c004" + "00010001")[0] == "0" and q("c00c00010001")[0] == "0")
            check("chilli: type / class cut short by the end of the payload is refused",
                  q(L + "00" + "0001")[0] == "0" and q(L + "00")[0] == "0")
            check("chilli: a label running past the end of the payload is refused (no zero byte follows)",
                  q("3f" + "61" * 20)[0] == "0" and q("")[0] == "0")
            long_q = ("3f" + "61" * 63) * 3 + "3d" + "61" * 61 + "00" + "00010001"   # 254-byte name + 4
            check("chilli: a long name that fits the payload and the buffer is copied (259 bytes, outmax 300)",
                  q(long_q, 300) == ["259", "1"], q(long_q, 300))
            check("chilli: the same name is refused when the buffer is smaller than the question (outmax 256)",
                  q(long_q, 256)[0] == "0")
            check("chilli: a reserved label type (0x40 / 0x80 high bits) is refused", q("40" + L[2:] + "0000010001")[0] == "0")
    fn = dh[dh.index("static \nint dhcp_dns("):] if "static \nint dhcp_dns(" in dh else ""
    check("chilli: dhcp_dns uses the bounded copy on the payload length, and the stock zero-byte loop is gone",
          "query_len = reaper_dns_qcopy(p, olen, query, sizeof(query));" in fn and "while (*p++ != 0); /* TODO */" not in dh
          and fn.index("query_len = reaper_dns_qcopy(") < fn.index("if (query_len + 16 > sizeof(query))") < fn.index("query[query_len++] = 0xc0;"), "")

    # ======================= P6-4-W1 wallguard =======================
    wsh = os.path.join(SRC, "wallguard", "wallguard.sh")
    D = os.path.join(td, "wg"); os.mkdir(D)
    b = os.path.join(td, "wgbin"); os.mkdir(b)
    def fake(name, body):
        p = os.path.join(b, name)
        with open(p, "w", newline="\n") as fh: fh.write("#!/bin/sh\n" + body)
        os.chmod(p, 0o755)
    fake("curl", 'exit 22\n')                                   # no Google domain list: the script keeps .google.com
    fake("logger", 'shift 2; echo "$*" >> "$WGLOG"\n')
    fake("wgresolve", '[ -n "$RES_FAIL" ] && exit 1\ncase "$2" in forcesafesearch.google.com) a=216.239.38.120;; strict.bing.com) a=203.0.113.20;;'
                      ' safe.duckduckgo.com) a=203.0.113.21;; restrictmoderate.youtube.com) a=216.239.38.119;; restrict.youtube.com) a=216.239.38.120;; esac\n'
                      '[ -n "$RES_NO_Y" ] && [ "$2" = restrict.youtube.com ] && exit 1\necho "$2 v4 $a"\n')
    log = os.path.join(td, "wg.log")
    def wg(action, wan, **envx):
        env = dict(os.environ, PATH=b + os.pathsep + os.environ.get("PATH", ""), WALLGUARD_DIR=D, WALLGUARD_JFFS=os.path.join(td, "jffs"),
                   WALLGUARDC=os.path.join(b, "wgresolve"), WALLGUARD_WAN=str(wan), WALLGUARD_KEYTMP=td,
                   RSTORE_PUB_F=os.path.join(td, "nostore"), WGLOG=log, **envx)
        return subprocess.run([SH, wsh, action], capture_output=True, text=True, env=env, cwd=td)
    def ss(): return rd(os.path.join(D, "safesearch"))
    def addr(): return [l.split()[1] for l in ss().splitlines() if l.startswith("addr ")]
    def pend(): return rd(os.path.join(D, "pending")).strip()
    open(os.path.join(D, "feeds"), "w").close()
    pol = os.path.join(D, "policy")
    # no profile asks for safe search (rc's policy: default <mask> <flags>, mac ... <flags>): a failed lookup is
    # NOT owed - the full update refreshes the file for everyone, and nobody must be told searches are unrestricted
    with open(pol, "w") as fh: fh.write("default 7 0\nmac AA:BB:CC:DD:EE:01 3 0\n")
    open(log, "w").close()
    p = wg("safe", 0, RES_FAIL="1")
    check("wallguard: with no profile asking for safe search, a failed lookup logs nothing and arms no retry",
          rd(log) == "" and pend() == "" and "name g google.com" in ss(), rd(log) + "|" + pend())
    p = wg("retry", 1, RES_FAIL="1")
    check("wallguard: ... and retry leaves such a file alone", rd(log) == "" and pend() == "", rd(log) + "|" + pend())
    os.unlink(os.path.join(D, "safesearch"))
    with open(pol, "w") as fh: fh.write("default 7 0\nmac AA:BB:CC:DD:EE:01 3 1\n")   # one device's profile has SafeSearch
    open(log, "w").close()
    p = wg("safe", 0, RES_FAIL="1")
    check("wallguard: before the WAN, `safe` writes the names and no address (the field state after a reboot)",
          "name g google.com" in ss() and addr() == [], ss()[:300] + p.stderr)
    check("wallguard: ... and now SAYS so, naming every engine, and marks it owed for WAN up (pending 0)",
          "safe search: no enforcement address could be looked up for Google Bing DuckDuckGo YouTube-moderate YouTube-strict" in rd(log)
          and "trying again when the internet is up" in rd(log) and pend() == "0", rd(log) + "|" + pend())
    open(log, "w").close()
    p = wg("retry", 1, RES_FAIL="1")
    pe = pend()
    check("wallguard: retry with the WAN up but lookups still failing keeps it owed with a back-off (pending in ~10 min)",
          addr() == [] and pe.isdigit() and 500 < int(pe) - int(time.time()) < 700 and "trying again in 10 min" in rd(log),
          rd(log) + "|" + pe)
    with open(os.path.join(D, "pending"), "w") as fh: fh.write("1\n")      # due
    open(log, "w").close()
    p = wg("retry", 1, RES_FAIL="1")
    pe = pend()
    check("wallguard: the next due retry that still fails doubles the wait (20 min)",
          pe.isdigit() and 1100 < int(pe) - int(time.time()) < 1300 and "trying again in 20 min" in rd(log), rd(log) + "|" + pe)
    with open(os.path.join(D, "pending"), "w") as fh: fh.write("1\n")
    open(log, "w").close()
    p = wg("retry", 1)
    check("wallguard: once the lookups work, retry (no list owed) fills every group and clears the mark",
          sorted(set(addr())) == ["Y", "b", "d", "g", "y"] and pend() == "" and not os.path.exists(os.path.join(D, "tries")),
          ss()[-300:] + "|" + pend())
    check("wallguard: ... with a log line that it is in place", "safe search: the enforcement addresses of every search engine are in place" in rd(log), rd(log))
    open(log, "w").close()
    p = wg("retry", 1)
    check("wallguard: a complete file and no list owed: retry does nothing and logs nothing", rd(log) == "" and pend() == "", rd(log))
    p = wg("safe", 1, RES_NO_Y="1")
    check("wallguard: a lookup that fails for ONE group keeps that group's previous address (never switched off)",
          "Y" in addr(), ss()[-200:])
    os.unlink(os.path.join(D, "safesearch"))
    open(log, "w").close()
    p = wg("safe", 1, RES_NO_Y="1")
    check("wallguard: with no previous address for it, only that group is named as not restricted",
          "looked up for YouTube-strict - searches there are NOT restricted" in rd(log) and "Y" not in addr() and "g" in addr(), rd(log))
    check("wallguard: no temp file is left behind (the temp names carry the pid)",
          not [n for n in os.listdir(D) if ".new" in n], repr(os.listdir(D)))
    wsrc = read("wallguard/wallguard.sh")
    check("wallguard: an update restricted to some lists (Update button, WAN-up retry) refreshes an incomplete file a profile needs",
          '{ [ -z "${ONLY+x}" ] || [ ! -f "$D/safesearch" ] || { ss_wanted && [ -n "$(ss_missing)" ]; }; } && safesearch' in wsrc)
    for nm, opt in (("sh", [SH]), ("busybox ash", ["busybox", "ash"]) if shutil.which("busybox") else (None, None)):
        if nm:
            check("wallguard: the script parses (%s -n)" % nm, subprocess.run(opt + ["-n", wsh], capture_output=True).returncode == 0)

    # ======================= P6-4-G1/G2/G3 diag =======================
    dg = read("others/reaper_diag")
    check("diag: v1.3.61 in the script and on the page", 'VER="REAPER-DIAG v1.3.61"' in dg and "REAPER-DIAG v1.3.61</span>" in read("www/Reaper_Diag.asp"))
    check("diag: the arg stage runs second - after the literals, before client names and e-mail (URL credentials before the e-mail shape)",
          re.search(r'^SAN_STAGES="lit arg ctx mail mac ip6 ip4"$', dg, re.M) is not None)
    ma = re.search(r"^cat > \"\$AWKP\.arg\" <<'AWKEOF'\n(.*?)^AWKEOF$", dg, re.S | re.M)
    check("diag: the arg stage program is in the script", ma is not None)
    if ma:
        ap = os.path.join(td, "arg.awk")
        with open(ap, "w") as fh: fh.write(ma.group(1))
        IN = ('  15 3 * * * curl -s "https://api.example.net/up?token=Zk9xQ2vLr8TnW4pJ&x=1" #mine#\n'
              '  1234 admin  2560 S  /opt/bin/agent --api_key=SECRETVALUE123 -v\n'
              '  curl -H "Authorization: Bearer abcdefghijklmnop" https://user1:' 'hunter22@files.example.net/x\n'
              '  {"token":"abcd1234efgh","n":1}  PASSWORD=Opensesame99\n'
              '  password: set   secret=0   auth_mode=psk2   tokenizer=fine   bearer id   psk:ab\n'
              '  wl0_wpa_psk=[R\001EDACTED-SECRET-1]  https://example.net/a:b@c\n')
        ip = os.path.join(td, "arg.in")
        with open(ip, "w") as fh: fh.write(IN)
        awks = [("busybox awk", ["busybox", "awk"])] if shutil.which("busybox") else []
        awks += [(a, [a]) for a in ("gawk", "mawk") if shutil.which(a)]
        if not awks and shutil.which("awk"): awks = [("awk", ["awk"])]
        for nm, cmd in awks:
            r = subprocess.run(cmd + ["-f", ap, ip], capture_output=True, text=True)
            o = r.stdout.split("\n")
            ok = (len(o) >= 6 and r.returncode == 0
                  and "Zk9xQ2vLr8TnW4pJ" not in r.stdout and "token=[R\001EDACTED-ARG-1]&x=1" in o[0]
                  and "SECRETVALUE123" not in r.stdout and "--api_key=[R\001EDACTED-ARG-" in o[1]
                  and "abcdefghijklmnop" not in r.stdout and "Bearer [R\001EDACTED-ARG-" in o[2]
                  and "hunter22" not in r.stdout and "user1" not in r.stdout and "https://[R\001EDACTED-ARG-" in o[2] and "@files.example.net/x" in o[2]
                  and '"token":"[R\001EDACTED-ARG-' in o[3] and "Opensesame99" not in r.stdout
                  and o[4] == IN.split("\n")[4] and o[5] == IN.split("\n")[5]
                  and "free-text secrets redacted : 6" in r.stderr)
            check("diag arg stage (%s): tokens, API keys, Bearer, URL credentials masked; short values, other names, tokens kept" % nm, ok,
                  r.stdout.replace("\001", "^A") + r.stderr)
        r = subprocess.run((awks[0][1] if awks else ["awk"]) + ["-f", ap, ip, ip], capture_output=True, text=True)
        o = r.stdout.split("\n")
        check("diag arg stage: one token per distinct value (the same value twice = the same token)", o[0] == o[6] and "ARG-1]" in o[6], r.stdout[:400])
    mc = re.search(r"^awk -F= '\n(.*?)\n  \}' \"\$NVS\" > \"\$SLIST\" 2>/dev/null$", dg, re.S | re.M)
    check("diag: the literal classifier is in the script", mc is not None)
    if mc:
        cp = os.path.join(td, "cls.awk")
        with open(cp, "w") as fh: fh.write(mc.group(1) + "\n  }\n")
        nv = os.path.join(td, "nvram.txt")
        with open(nv, "w") as fh:
            fh.write("wan0_domain=hsd1.ca.exampleisp.net\nwan1_domain=dsl.otherisp.example\nlog_ipaddr=syslog.home.example.org\n"
                     "wgc1_ep_addr=us-nyc-042.vpnprovider.example\nwgc1_ep_addr_r=203.0.113.44 203.0.113.45\nvpn_client2_addr=ovpn.example.com\n"
                     "ntp_server0=ntp.mycorp.example\nntp_server1=pool.ntp.org\nntp_server2=2.asia.pool.ntp.org\nntp_server3=time.google.com\n"
                     "wan0_ifname=eth0\nlan_domain=home.example.lan\nntp_ready=1\n")
        r = subprocess.run((awks[0][1] if awks else ["awk"]) + ["-F=", "-f", cp, nv], capture_output=True, text=True)
        H = [l.split("\t", 1)[1] for l in r.stdout.splitlines() if l.startswith("HOST\t")]
        want = ["hsd1.ca.exampleisp.net", "dsl.otherisp.example", "syslog.home.example.org", "us-nyc-042.vpnprovider.example",
                "203.0.113.44", "203.0.113.45", "ovpn.example.com", "ntp.mycorp.example", "home.example.lan"]
        check("diag: ISP domains, the log server, VPN servers (name and resolved addresses) and a typed NTP server are host names",
              all(w in H for w in want), r.stdout + r.stderr)
        check("diag: the shipped NTP pools and plain settings are NOT host names (they stay readable)",
              not [h for h in H if "pool.ntp.org" in h or h == "time.google.com" or h == "eth0"], H)
    bb = shutil.which("busybox")
    check("diag: the script parses (sh -n%s)" % (", busybox ash -n" if bb else ""),
          subprocess.run([SH, "-n", os.path.join(SRC, "others", "reaper_diag")], capture_output=True).returncode == 0
          and (not bb or subprocess.run(["busybox", "ash", "-n", os.path.join(SRC, "others", "reaper_diag")], capture_output=True).returncode == 0))

    # ======================= P6-3-D2 sdn.c =======================
    sd = read("rc/sdn.c"); su = read("shared/shutils.c")
    fwr = extract(sd, "static int _write_dhcp_reservation(")
    c4 = os.path.join(td, "res.c"); g4 = os.path.join(td, "res")
    with open(c4, "w") as fh:
        fh.write(r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#define ETHER_ADDR_LEN 6
#define RTCONFIG_IPV6
static const char *nvram_safe_get(const char *k) { (void)k; const char *v = getenv("RL"); return v ? v : ""; }
static int is_valid_hostname(const char *n) { for (; *n; n++) if (!isalnum((unsigned char)*n) && *n != '-' && *n != '.') return 0; return 1; }
static int _vstrsep(char *buf, const char *sep, ...) { va_list ap; char **p; int n = 0; va_start(ap, sep); while ((p = va_arg(ap, char **)) != NULL) { *p = strsep(&buf, sep); if (!*p) break; n++; } va_end(ap); return n; }
#define vstrsep(buf, sep, args...) _vstrsep(buf, sep, args, NULL)
''' + extract(su, "ether_atoe(const char *a, unsigned char *e)").replace("ether_atoe(", "int ether_atoe(", 1)
    + "\n" + extract(su, "ether_etoa(const unsigned char *e, char *a)").replace("ether_etoa(", "char *ether_etoa(", 1)
    + "\n" + fwr + "\nint main(void) { return _write_dhcp_reservation(stdout, 1); }\n")
    r = subprocess.run([CC, "-std=gnu99", "-w", "-o", g4, c4], capture_output=True, text=True)
    check("sdn: _write_dhcp_reservation compiles on the host with shutils' MAC helpers", r.returncode == 0, r.stderr[:800])
    if r.returncode == 0:
        def res(rl):
            return subprocess.run([g4], capture_output=True, text=True, env=dict(os.environ, RL=rl)).stdout
        o = res("<aa:bb:cc:dd:ee:01>192.168.52.10>192.168.52.1>printer1<aa:bb:cc:dd:ee:02>>192.168.52.1>")
        check("sdn: a lower-case MAC is written in canonical form in EVERY line of its row; the DNS tag matches the host line",
              o == ("dhcp-option=tag:AA:BB:CC:DD:EE:01,6,192.168.52.1\ndhcp-host=AA:BB:CC:DD:EE:01,set:AA:BB:CC:DD:EE:01,printer1,192.168.52.10\n"
                    "dhcp-option=tag:AA:BB:CC:DD:EE:02,6,192.168.52.1\ndhcp-host=AA:BB:CC:DD:EE:02,set:AA:BB:CC:DD:EE:02\n"), o)
        o = res("<aa:bb:cc:dd:ee:03\nconf-file=/tmp/evil>>192.168.52.1><aa-bb-cc-dd-ee-04>>192.168.52.1>")
        check("sdn: a row with text hidden after its MAC (a line break and a directive) writes nothing; the next row is written",
              "conf-file" not in o and "evil" not in o and "EE:03" not in o
              and o == "dhcp-option=tag:AA:BB:CC:DD:EE:04,6,192.168.52.1\ndhcp-host=AA:BB:CC:DD:EE:04,set:AA:BB:CC:DD:EE:04\n", o)
        o = res("<notamac>192.168.52.11>192.168.52.1>x<zz:zz>>192.168.52.1><aa:bb:cc:dd:ee:0g>192.168.52.12>><aa:bb:cc:dd:ee:0>192.168.52.13>>")
        check("sdn: a row whose MAC is not six hex pairs writes nothing at all (ether_atoe alone took 'zz:zz' as all zeros)", o == "", o)
    check("sdn: the MAC check sits before the first line written for the row (source)",
          fwr.index("REAPER-SDN-RESMAC") < fwr.index('fprintf(fp, "dhcp-option=tag:%s,option6:23,%s\\n", mac, dns);'))

    # ======================= P6-3-S1/S2/S3 services.c (source) =======================
    sv = read("rc/services.c")
    ru = extract(sv, "void reload_upnp(void)")
    check("services: reload_upnp forks the stop/start in rc (never waits on start_upnp), notify_rc only outside rc",
          "if (getpid() == 1) {" in ru and "pid_t pid = fork();" in ru and "stop_upnp();\n\t\t\tstart_upnp();" in ru and "_exit(0);" in ru
          and ru.index("if (getpid() == 1)") < ru.index('notify_rc("restart_upnp")') and "} else\n\t\tnotify_rc(\"restart_upnp\");" in ru
          and "signal(sig, SIG_DFL);" in ru and "sigprocmask(SIG_SETMASK, &none, NULL);" in ru and 'file_lock("reaper_upnp")' in ru)
    rs = extract(sv, "static void reaper_sdn_dnsmasq_restart(void)")
    check("services: the resolver restart helper does what the restart_dnsmasq handler does (in rc), notify_rc outside",
          "stop_dnsmasq(ALL_SDN);\n\tstart_dnsmasq(ALL_SDN);" in rs and "if (getpid() != 1) {\n\t\tnotify_rc(\"restart_dnsmasq\");" in rs)
    i1 = sv.index('else if(strcmp(script, "sdn_del") == 0)')
    blk = sv[i1 - 3000:i1 + 1500]
    check("services: both network handlers call the helper; no notify_rc(\"restart_dnsmasq\") is left in them",
          blk.count("reaper_sdn_dnsmasq_restart();") == 2 and 'notify_rc("restart_dnsmasq")' not in blk
          and sv.index("static void reaper_sdn_dnsmasq_restart(void)") < i1)
    check("services: the UPnP deny list reads each WireGuard server's own keys (wgsN_enable / wgsN_port)",
          'nvram_get_int("wgs_enable")' not in sv and 'snprintf(wk, sizeof(wk), "wgs%d_enable", wu);' in sv
          and 'snprintf(wk, sizeof(wk), "wgs%d_port", wu);' in sv and "REAPER-UPNP-WGS" in sv)
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f.replace("\001", "^A"))
sys.exit(1 if fails else 0)
