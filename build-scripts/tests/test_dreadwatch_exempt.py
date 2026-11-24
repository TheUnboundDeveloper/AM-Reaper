#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dreadwatch: devices that skip the threat list (v3.8.4, owner 2026-11-22).

WHY THIS EXISTS. Dreadwatch answered every device alike, so a device the admin wanted unfiltered could only be sent
to another DNS server with DNS Director (which then lost it the router's Encrypted DNS - the field report behind
test_dnr_policy_step.py). Now the Dreadwatch page keeps a list of at most 16 devices (MAC addresses, the /jffs list
store "dnsexempt") that skip the threat list.

THE DANGER. Dreadwatch judges a name in forward.c AFTER dnsmasq's cache. If an exempt device's lookup of a listed
name were cached like any other answer, the next device asking for it would be answered from the cache and never
judged: one exempt lookup would unblock the name for everybody. So where a query comes in (UDP and TCP), an exempt
device asking for a listed name makes the query NOT CACHEABLE: it does not read the cache, its answer is not kept,
and it cannot join another device's query in flight. This test proves that with a real dnsmasq.

WHAT IT RUNS.
  1. The patched dnsmasq, built for the host (a copy whose neighbour lookup is replaced: 10.9.0.N has the MAC
     aa:bb:cc:dd:ee:NN), against a fake upstream; devices are named the way rednsd names them (EDNS option 65400
     from loopback). An exempt and a normal device ask for the same listed name, over UDP and TCP, one after the
     other and at the same moment; the list file is edited while dnsmasq runs; Wallguard keeps its own block.
  2. rc's writer of the list (rw_dns_exempt_sync) and httpd's check (rdw_exempt_clean), cut out of the source and
     run on the host.
  3. Source pins: both writers of the dnsmasq include, the save / read / export / import path.
The let-through count kept by dns.sh is tested in test_dreadwatch.py.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] or REAPER_ROUTER_SRC - or no host compiler)."""
import os, random, re, shutil, socket, struct, subprocess, sys, tempfile, threading, time

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:500] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "dnsmasq", "src", "reaper_nx.c")):
    skip("no router source tree with dnsmasq/src/reaper_nx.c (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host compiler")
def read(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()
def cut(text, start, end):
    a = text.find(start); b = text.find(end, a + 1) if a >= 0 else -1
    return text[a:b] if 0 <= a < b else ""

nx, fw, wg, rw, web = read("dnsmasq/src/reaper_nx.c"), read("dnsmasq/src/forward.c"), read("dnsmasq/src/wallguard.c"), read("rc/rwarden.c"), read("httpd/web.c")

# ============================================================ 3. source pins (first: they need no build)
udp = cut(fw, "n = add_edns0_config(header, n, daemon->edns_pktsz, &source_addr, now, &cacheable);", "saved_question = blockdata_alloc(")
check("UDP: an exempt device's lookup of a listed name is made not cacheable right after add_edns0_config(), before Wallguard and the cache",
      "if (wallguard_q && reaper_nx_pass(daemon->namebuff, reaper_client(&source_addr), now))\n\tcacheable = 0;" in udp
      and udp.find("reaper_nx_pass(") < udp.find("wallguard_answer("), udp[:600])
tcp = cut(fw, "else if (!(gotname = extract_request(header, (unsigned int)size, daemon->namebuff, &qtype, NULL)))", "m = answer_request(out_header")
check("TCP: the same, once the name is known and before the answer is looked for",
      "if (reaper_nx_pass(daemon->namebuff, reaper_client(&peer_addr), now))\n\t\tcacheable = 0;" in tcp and "!cacheable" in fw[fw.find(tcp) + len(tcp):][:200])
check("a query joins another device's query in flight only when Dreadwatch judges both alike",
      "reaper_nx_merge_ok(&forward->frec_src.wallguard_client, reaper_client(udpaddr), now)) || (forward = NULL, 0)))" in fw)
judge = cut(nx, "int reaper_nx_judge(", "\n}\n")
check("the judge lets an exempt device through only after the name is found listed (no neighbour lookup for other names)",
      0 < judge.find("nx_longest(name, &bits, &at)") < judge.find("if (reaper_nx_exempt(client, now))") < judge.find("*flags = check_for_local_domain"), judge)
pas = cut(nx, "int reaper_nx_pass(", "\n}\n")
check("reaper_nx_pass: nothing is looked at while nobody is exempt; the list, then the device, then one count record",
      0 < pas.find("if (!nxe.n)\n    return 0;") < pas.find("nx_longest(name, &bits, &at)") < pas.find("nx_pass_rec(mac);"), pas)
rec = cut(nx, "static void nx_pass_rec(", "\n}\n")
check("the count record is the date and the address only: no name is handed to it, O_NOFOLLOW, bounded",
      "static void nx_pass_rec(const unsigned char *mac)" in nx and '"%ld %02x:%02x:%02x:%02x:%02x:%02x\\n"' in rec and "O_NOFOLLOW" in rec
      and "NX_PASS_MAX" in rec and "NX_PASS_RATE" in rec and "name" not in rec)
check("at most 16 devices; a line must be exactly one MAC address", "#define NX_EXEMPT_MAX 16" in nx
      and "while (nxe.n < NX_EXEMPT_MAX && fgets(line, sizeof(line), f))" in nx and "if (s[17] && s[17] != '\\n' && s[17] != '\\r')" in nx)
check("Wallguard stands back for Dreadwatch only where Dreadwatch answers: not for an exempt device",
      "(reaper_nx_listed(name) && !reaper_nx_exempt(client, now)))" in wg
      and "static int wallguard_config_answer(char *name, unsigned short qtype, union mysockaddr *client, time_t now)" in wg
      and wg.count(", qtype, client, now)") == 3 and not re.search(r"wallguard_config_answer\([^)]*qtype\)", wg))
inc_c = 'fprintf(f, "reaper-hitlog=%s\\nreaper-nx-db=%s\\nreaper-nx-exempt=%s\\n", RW_HITS, RW_NX_DB, RW_DNS_EXEMPT);'
inc_sh = '{ echo \\"reaper-hitlog=$RW_DNSH\\"; echo \\"reaper-nx-db=$RW_NXDB\\"; echo \\"reaper-nx-exempt=$RW_NXDIR/dns.exempt\\"; } > $RW_DNSC.new;'
check("both writers of the dnsmasq include write the same three lines (rc compares them byte for byte before a restart)",
      inc_c in rw and inc_sh in rw and '#define RW_DNS_EXEMPT RW_NX_DIR "/dns.exempt"' in rw and '"RW_NXDIR=" RW_NX_DIR "\\n"' in rw)
check("rc writes the list with every dnsmasq configuration and after the page's save",
      "\trw_hits_dir();\n\trw_dns_exempt_sync();" in rw and "\trw_gen_dns();\t\t/* 2026-10-20: Dreadwatch hit collector */\n\trw_dns_exempt_sync();" in rw)
sv = cut(web, 'if (!strcmp(action, "save_lists")) {', 'websWrite(stream, "{\\"ok\\":1,\\"saved\\":%d}", saved);')
check("httpd save: MAC addresses only through rdw_exempt_clean, before anything is written; an unchanged list writes and logs nothing",
      0 < sv.find('get_cgi("dnsexempt")') < sv.find("rdw_exempt_clean(ex, exc, sizeof(exc))) < 0") < sv.find('if (!exo || strcmp(exo, exc)) {')
      < sv.find('rw_list_set("dnsexempt", exc)') < sv.find('reaper_audit("dreadwatch", "save", msg);'), sv[:300])
check("httpd: the page reads the list; the settings file and the full backup carry it; an import goes through the same check",
      'strcmp(name, "dnssrc") && strcmp(name, "dnsexempt")) return 0;' in web and '{ "warden", "rwarden_dnsexempt", 512 },' in web
      and '!strcmp(nv + 8, "dnsexempt"))' in web
      and 0 < web.find('if (!strcmp(ln, "dnsexempt")) {') < web.find('if (!(strcmp(ln, "dnsallow") ? rcfg_ok(v, rcfg_flags[i].max)'))
check("no nvram key and no factory default: an empty list is the default",
      "rwarden_dnsexempt" not in read("shared/defaults.c"))

# ============================================================ 4. the pages, their texts, the diagnostics report
pg, wgp, util, diag = read("www/Reaper_Dreadwatch.asp"), read("www/Reaper_Wallguard.asp"), read("www/reaper_util.js"), read("others/reaper_diag")
KEYS = ["RDWT_%d" % i for i in range(70, 78)] + ["RSHD_226"]
packs = sorted(f[:-5] for f in os.listdir(os.path.join(SRC, "www")) if f.endswith(".dict") and f != "temp.dict")
def pack(p):
    return dict(l.split("=", 1) for l in open(os.path.join(SRC, "www", p + ".dict"), encoding="utf-8").read().splitlines() if "=" in l)
D = {p: pack(p) for p in packs}
bad = [(p, k) for p in packs for k in KEYS if not D[p].get(k, "").strip() or any(c in D[p][k] for c in '"`<>{}')]
check("%d new texts in all %d packs, non-empty, nothing in them that could break a page or a template" % (len(KEYS), len(packs)), len(packs) == 25 and not bad, bad[:6])
same = [(p, k) for p in packs if p != "EN" for k in ("RDWT_70", "RDWT_71", "RSHD_226") if D[p].get(k) == D["EN"].get(k)]
check("the three sentences are translated in every pack (not the English text)", not same, same[:6])
en = D["EN"]
check("English: the card says what is lost, what still applies, how a device is recognised and the limit",
      "not checked against the threat lists" in en["RDWT_71"] and "Wallguard and Warden still apply" in en["RDWT_71"]
      and "MAC address" in en["RDWT_71"] and "16 devices" in en["RDWT_71"] and "Save applies" in en["RDWT_71"], en.get("RDWT_71"))
check("every pack's Bypass hint names its own Bypass word and its own card title",
      all(D[p]["RSHD_226"].startswith(D[p]["RSHD_46"]) and D[p]["RDWT_70"] in D[p]["RSHD_226"] and "Dreadwatch" in D[p]["RSHD_226"] and "Wallguard" in D[p]["RSHD_226"] for p in packs),
      [p for p in packs if not D[p]["RSHD_226"].startswith(D[p]["RSHD_46"])])
card = cut(pg, '<div class="card" id="excard">', '<div class="card">\n  <h2><#RWDN_116#></h2>')
check("page: the card sits above the never-block names: title, description, table (device, MAC, count), picker, address box, Add",
      all(x in card for x in ("<h2><#RDWT_70#></h2>", '<div class="desc"><#RDWT_71#></div>', "<th><#RDWT_19#></th><th><#MAC_Address#></th>", '<th class="num"><#RDWT_72#></th>',
                              '<tbody id="exbody">', '<select id="exsel" onchange="dwExPick()">', 'id="exmac" maxlength="17"', 'onclick="dwExAdd()"><#RDWT_73#></button>')), card[:300])
check("page: every new text is used, in the card or alone in a backtick template",
      all(("<#%s#>" % k) in pg for k in KEYS[:8]) and all(("`<#%s#>`" % k) in pg for k in ("RDWT_74", "RDWT_75", "RDWT_76", "RDWT_77")))
js = cut(pg, "/* ---- devices that skip Dreadwatch", "/* ---- your own sources")
check("page: a typed address is checked as a MAC address; 16 devices at most; nothing is sent before Save",
      "function dwExOk(m){ return /^[0-9a-f]{2}(:[0-9a-f]{2}){5}$/.test(m); }" in js and "if(DWX.length >= 16){ alert(`<#RDWT_77#>`); return; }" in js
      and "XMLHttpRequest" not in js and "dwGet(" not in js)
check("page: the list is read from the list store, sent with the page's Save, part of the unsaved-changes snapshot, repainted with each status",
      "dnsexempt: decodeURIComponent('<% rwarden_list(\"dnsexempt\"); %>')," in pg and "lf.append('dnsexempt', DWX.join(' '));" in pg
      and "exempt: DWX.join(' ')," in pg and "DWXP[p.mac] = p.n; }); dwExPaint();" in pg)
check("page: still pure ASCII (the dash for a nameless device is a JS escape)", all(ord(c) < 128 for c in pg) and "byMac(m, '\\u2014')" in pg)
check("the device picker's source: ReaperNames.macs() - MAC-shaped keys of the Name and Hostname maps",
      "macs: function(){ var s = {}, k; for(k in nameOf) s[k] = 1; for(k in hostOf) s[k] = 1;" in util)
check("Wallguard page: the hint under the profiles text says Bypass does not lift Dreadwatch",
      '<div class="desc"><#RSHD_44#></div>\n  <!-- 2026-11-22 (REAPER-DREAD-EXEMPT)' in wgp and '<div class="desc" id="bypassdw"><#RSHD_226#></div>' in wgp)
dl = cut(diag, 'echo "  dreadwatch exempt :', "\n")
check("diagnostics report: counts only - how many devices, how many lookups; no address is printed",
      "devices=${_dxe:-0}" in dl and "listed-lookups-let-through=" in dl and '$1=="PASS"{n+=$3}' in dl
      and "_dxe=$(grep -c . /tmp/reaper_nx/dns.exempt 2>/dev/null)" in diag and "cat /tmp/reaper_nx/dns.exempt" not in diag)

work = tempfile.mkdtemp(prefix="dwex_")
procs, stop = [], threading.Event()
try:
    # ============================================================ 2. rc's writer and httpd's check on the host
    def build(name, code):
        c = os.path.join(work, name + ".c"); x = os.path.join(work, name)
        open(c, "w").write(code)
        r = subprocess.run([CC, "-O1", "-Wall", "-Werror", "-Wno-unused-function", "-o", x, c], capture_output=True, text=True)
        return (x if r.returncode == 0 else None), r.stderr
    clean = cut(web, "#define RDW_EXEMPT_MAX 16", "static void\ndo_reaper_warden_cgi(")
    x, err = build("clean", "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <ctype.h>\n" + clean +
                   'int main(int c, char **v) { char o[RDW_EXEMPT_MAX * 18 + 1]; int n = rdw_exempt_clean(c > 1 ? v[1] : NULL, o, sizeof(o)); printf("%d|%s", n, o); return 0; }\n')
    check("httpd's check compiles on the host", x is not None, err)
    if x:
        cl = lambda s: subprocess.run([x, s], capture_output=True, text=True).stdout
        M = ["aa:bb:cc:dd:ee:%02x" % i for i in range(1, 18)]
        check("check: lower case, one space between, repeats dropped; spaces, commas and line ends separate",
              cl("AA:BB:CC:DD:EE:01,aa:bb:cc:dd:ee:02\n aa:bb:cc:dd:ee:01\r\n") == "2|aa:bb:cc:dd:ee:01 aa:bb:cc:dd:ee:02", cl("AA:BB:CC:DD:EE:01,aa:bb:cc:dd:ee:02\n aa:bb:cc:dd:ee:01\r\n"))
        check("check: an empty list is a list (0 devices)", cl("") == "0|" and cl("  \n") == "0|")
        check("check: 16 devices pass, the 17th refuses the whole list", cl(" ".join(M[:16])).startswith("16|") and cl(" ".join(M)).startswith("-1|"))
        bad = ["zz:zz:zz:zz:zz:zz", "aa:bb:cc:dd:ee", "aa:bb:cc:dd:ee:011", "aa-bb-cc-dd-ee-01", "aabb.ccdd.ee01", "aa:bb:cc:dd:ee:01;reboot", "a:b:c:d:e:f",
               "aa:bb:cc:dd:ee:01<x>", "aa:bb:cc:dd:ee:0g"]
        check("check: anything that is not exactly a MAC address refuses the whole list",
              all(cl("aa:bb:cc:dd:ee:02 " + b).startswith("-1|") for b in bad), [b for b in bad if not cl("aa:bb:cc:dd:ee:02 " + b).startswith("-1|")])
    sync = cut(rw, "static void rw_dns_exempt_sync(void)\n{", "const char *reaper_warden_dns_conf(void)")
    NXD = os.path.join(work, "nxdir")
    x, err = build("sync", r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <sys/stat.h>
#define RW_NX_DIR "%s"
#define RW_DNS_EXEMPT RW_NX_DIR "/dns.exempt"
static const char *LIST; static int WRITES;
static char *rw_list_get(const char *n) { return strcmp(n, "dnsexempt") ? NULL : strdup(LIST); }
static int f_read_string(const char *p, char *b, int max) { FILE *f = fopen(p, "r"); size_t n; if (!f) return -1; n = fread(b, 1, max - 1, f); b[n] = 0; fclose(f); return (int)n; }
static int reaper_write_atomic(const char *p, const void *d, size_t l, mode_t m) { FILE *f = fopen(p, "w"); (void)m; if (!f) return -1; fwrite(d, 1, l, f); fclose(f); WRITES++; return 0; }
#define logmessage(tag, ...) (printf("log: " __VA_ARGS__), printf("\n"))
''' % NXD.replace("\\", "/") + sync + r'''
int main(int c, char **v) { int i; for (i = 1; i < c; i++) { LIST = v[i]; rw_dns_exempt_sync(); } printf("writes=%d\n", WRITES); return 0; }
''')
    check("rc's writer compiles on the host", x is not None, err)
    if x:
        sy = lambda *a: subprocess.run([x] + list(a), capture_output=True, text=True).stdout
        exf = os.path.join(NXD, "dns.exempt")
        o = sy("aa:bb:cc:dd:ee:01")
        check("writer: without the table's directory nothing is written", "writes=0" in o and not os.path.exists(exf), o)
        os.makedirs(NXD)
        o = sy("AA:BB:CC:DD:EE:01 zz:zz:zz:zz:zz:zz,aa:bb:cc:dd:ee:02<aa:bb:cc:dd:ee:01>aa:bb:cc:dd:ee:03x\naa:bb:cc:dd:ee")
        check("writer: one lower-case address a line; junk, a repeat and an address with text after it are dropped",
              open(exf).read() == "aa:bb:cc:dd:ee:01\naa:bb:cc:dd:ee:02\n" and "writes=1" in o and "2 device(s) skip the threat list" in o, (o, open(exf).read()))
        o = sy("aa:bb:cc:dd:ee:01 aa:bb:cc:dd:ee:02", "aa:bb:cc:dd:ee:01 aa:bb:cc:dd:ee:02")
        check("writer: an unchanged list is not written again (dnsmasq would only re-read it)", "writes=0" in o, o)
        o = sy(" ".join("aa:bb:cc:dd:ee:%02x" % i for i in range(1, 30)))
        check("writer: never more than 16 lines", open(exf).read().count("\n") == 16, open(exf).read())
        o = sy("")
        check("writer: an emptied list empties the file (the devices are judged again)", open(exf).read() == "" and "writes=1" in o, o)

    # ============================================================ 1. the real dnsmasq
    SC = os.path.join(work, "wallguardc")
    b = subprocess.run([CC, "-O2", "-o", SC, os.path.join(SRC, "wallguard", "wallguardc.c")], capture_output=True, text=True)
    check("wallguardc builds for the host", b.returncode == 0, b.stderr[-400:])
    db = os.path.join(work, "dnsmasq")
    shutil.copytree(os.path.join(SRC, "dnsmasq"), db, symlinks=True, ignore=shutil.ignore_patterns("*.o", "dnsmasq"))
    arp = os.path.join(db, "src", "arp.c"); a = open(arp).read()
    sig = "int find_mac(union mysockaddr *addr, unsigned char *mac, int lazy, time_t now)\n{"
    check("the copy's neighbour lookup can be replaced (one find_mac in arp.c)", a.count(sig) == 1)
    open(arp, "w").write(a.replace(sig, "int find_mac_real(union mysockaddr *addr, unsigned char *mac, int lazy, time_t now)\n{") + r'''
/* test_dreadwatch_exempt.py: 10.9.0.N (N < 200) has the MAC aa:bb:cc:dd:ee:NN; nothing else has one */
int find_mac(union mysockaddr *addr, unsigned char *mac, int lazy, time_t now)
{
  (void)lazy; (void)now;
  if (addr && mac && addr->sa.sa_family == AF_INET)
    {
      unsigned int a = ntohl(addr->in.sin_addr.s_addr);
      if ((a >> 8) == 0x0a0900 && (a & 0xff) < 200)
	{ mac[0] = 0xaa; mac[1] = 0xbb; mac[2] = 0xcc; mac[3] = 0xdd; mac[4] = 0xee; mac[5] = (unsigned char)(a & 0xff); return 6; }
    }
  return 0;
}
''')
    b = subprocess.run(["make", "-C", db, "COPTS=-DNO_DBUS -DNO_INOTIFY -DHAVE_BROKEN_RTC", "CC=" + CC, "-j4"], capture_output=True, text=True, timeout=900)
    DB = os.path.join(db, "src", "dnsmasq")
    check("the patched dnsmasq builds for the host", b.returncode == 0 and os.path.exists(DB), (b.stdout + b.stderr)[-800:])
    warn = [l for l in (b.stdout + b.stderr).splitlines() if "warning" in l and re.search(r"(reaper_nx|forward|option|wallguard)\.c|dnsmasq\.h", l)]
    check("...without warnings from the patched files", not warn, warn[:5])
    if b.returncode != 0 or not os.path.exists(DB):
        raise SystemExit	# nothing to run; the failures above are reported below (a failed pin does not stop the run)

    L = os.path.join(work, "lists"); os.makedirs(L)
    def wf(name, text):
        p = os.path.join(L, name); open(p, "w").write(text); return p
    TABLE = os.path.join(work, "threat.db")
    r = subprocess.run([SC, "build", "--subtree", "--out", TABLE, "--list", "1:urlhaus:" + wf("urlhaus", "evil.example\nboth.example\nslow.example\ntcp.example\n")],
                       capture_output=True, text=True)
    check("the threat table builds", r.returncode == 0, r.stderr)
    SD = os.path.join(work, "sd"); RUN = os.path.join(SD, "run"); os.makedirs(RUN)
    subprocess.run([SC, "build", "--out", os.path.join(SD, "db"), "--list", "1:ads:" + wf("ads", "ads.example\nboth.example\n")], check=True, capture_output=True)
    open(os.path.join(SD, "policy"), "w").write("default 7fffffff\n")

    UP, PORT = 5431, 5432
    seen = {}
    def enc(name):
        return b"".join(bytes([len(l)]) + l.encode() for l in name.split(".")) + b"\0"
    def qname_of(m):
        i, parts = 12, []
        while m[i]:
            parts.append(m[i + 1:i + 1 + m[i]].decode()); i += m[i] + 1
        return ".".join(parts), i + 5
    us = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); us.bind(("127.0.0.1", UP)); us.settimeout(0.3)
    def reply(m):
        name, qend = qname_of(m)
        qtype = struct.unpack(">H", m[qend - 4:qend - 2])[0]
        seen[name.lower()] = seen.get(name.lower(), 0) + 1
        if name.lower().startswith("slow."):
            time.sleep(1.2)
        rr, an = (b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 300, 4) + socket.inet_aton("192.0.2.53"), 1) if qtype == 1 else (b"", 0)
        opt = b"\0" + struct.pack(">HHIH", 41, 1232, 0, 0) if struct.unpack(">H", m[10:12])[0] else b""
        return m[:2] + b"\x81\x80" + m[4:6] + struct.pack(">HHH", an, 0, 1 if opt else 0) + m[12:qend] + rr + opt
    def serve():
        while not stop.is_set():
            try: m, a = us.recvfrom(4096)
            except socket.timeout: continue
            threading.Thread(target=lambda m=m, a=a: us.sendto(reply(m), a), daemon=True).start()
    threading.Thread(target=serve, daemon=True).start()
    # dnsmasq forwards a query that came in over TCP over TCP
    ut = socket.socket(socket.AF_INET, socket.SOCK_STREAM); ut.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ut.bind(("127.0.0.1", UP)); ut.listen(8); ut.settimeout(0.3)
    def tcp_one(c):
        try:
            c.settimeout(3); b = b""
            while len(b) < 2 or len(b) < 2 + struct.unpack(">H", b[:2])[0]:
                d = c.recv(4096)
                if not d: return
                b += d
            r = reply(b[2:]); c.sendall(struct.pack(">H", len(r)) + r)
        except Exception:
            pass
        finally:
            c.close()
    def serve_tcp():
        while not stop.is_set():
            try: c, _ = ut.accept()
            except socket.timeout: continue
            threading.Thread(target=tcp_one, args=(c,), daemon=True).start()
    threading.Thread(target=serve_tcp, daemon=True).start()

    HITLOG, LOG, EX = os.path.join(work, "dns.hits"), os.path.join(work, "dnsmasq.log"), os.path.join(work, "dns.exempt")
    conf = os.path.join(work, "d.conf")
    open(conf, "w").write("port=%d\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\npid-file=\nserver=127.0.0.1#%d\n"
                          "wallguard-dir=%s\nreaper-hitlog=%s\nreaper-nx-db=%s\nreaper-nx-exempt=%s\nlog-facility=%s\n" % (PORT, UP, SD, HITLOG, TABLE, EX, LOG))
    dp = subprocess.Popen([DB, "-k", "-C", conf], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE); procs.append(dp); time.sleep(0.8)
    check("dnsmasq starts with --reaper-nx-exempt naming a file that does not exist yet", dp.poll() is None, dp.stderr.read().decode()[-300:] if dp.poll() is not None else "")
    if dp.poll() is not None:
        raise SystemExit

    E, N, U = "10.9.0.5", "10.9.0.6", "10.9.0.250"	# exempt (once listed), a normal device, a device with no known MAC
    def q(name, dev, tcp=False, timeout=4):
        """a lookup as rednsd hands it over: from loopback, the device named in EDNS option 65400"""
        o = struct.pack(">HH", 65400, 5) + b"\x01" + socket.inet_aton(dev)
        m = struct.pack(">HHHHHH", random.randint(1, 65535), 0x0100, 1, 0, 0, 1) + enc(name) + struct.pack(">HH", 1, 1)
        m += b"\0" + struct.pack(">HHIH", 41, 1232, 0, len(o)) + o
        if tcp:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=timeout); s.sendall(struct.pack(">H", len(m)) + m)
            try:
                r = b""
                while len(r) < 2 or len(r) < 2 + struct.unpack(">H", r[:2])[0]:
                    c = s.recv(4096)
                    if not c: break
                    r += c
            finally: s.close()
            r = r[2:]
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(timeout); s.sendto(m, ("127.0.0.1", PORT))
            try: r = s.recv(4096)
            finally: s.close()
        rcode, an = r[3] & 0x0f, struct.unpack(">H", r[6:8])[0]
        _, i = qname_of(r)
        addrs = []
        for _ in range(an):
            if r[i] & 0xc0 == 0xc0: i += 2
            else:
                while r[i]: i += r[i] + 1
                i += 1
            t, _c, _ttl, rdl = struct.unpack(">HHIH", r[i:i + 10]); i += 10
            if t == 1: addrs.append(socket.inet_ntoa(r[i:i + 4]))
            i += rdl
        return rcode, addrs
    OK, NXD_ = (0, ["192.0.2.53"]), (3, [])
    hits = lambda: [l.split() for l in open(HITLOG).read().splitlines() if not l.startswith("#")] if os.path.exists(HITLOG) else []
    passes = lambda: open(HITLOG + ".pass").read() if os.path.exists(HITLOG + ".pass") else ""
    def setlist(*macs):
        open(EX + ".new", "w").write("".join(m + "\n" for m in macs)); os.rename(EX + ".new", EX); time.sleep(2.4)	# NX_RECHECK is 2 s

    check("nobody exempt (no file): the listed name is NXDOMAIN for the device", q("evil.example", E) == NXD_ and "evil.example" not in seen)
    check("...and the block is recorded for that device (rednsd's name for it reaches Dreadwatch)", hits() and hits()[-1][1] == E and hits()[-1][2] == "evil.example", hits()[-1:])
    setlist("aa:bb:cc:dd:ee:05")
    n_hits = len(hits())
    check("the list is picked up without a restart: the exempt device now gets the real answer", q("evil.example", E) == OK and seen.get("evil.example") == 1, seen)
    check("THE CACHE: right after it, another device asking for the same name is still blocked", q("evil.example", N) == NXD_)
    check("...and so is a device whose address has no known MAC", q("evil.example", U) == NXD_)
    check("the exempt device's answer is never kept: every lookup of the name goes upstream again", q("evil.example", E) == OK and q("evil.example", E) == OK and seen.get("evil.example") == 3, seen)
    check("a name under the listed one: through for the exempt device, blocked for the other", q("a.b.evil.example", E) == OK and q("a.b.evil.example", N) == NXD_)
    check("a name that is not listed is cached as before, also when the exempt device asked first",
          q("news.example", E) == OK and q("news.example", N) == OK and q("news.example", E) == OK and seen.get("news.example") == 1, seen)
    check("TCP: through for the exempt device, blocked for the other, and still blocked over UDP afterwards",
          q("tcp.example", E, tcp=True) == OK and q("tcp.example", N, tcp=True) == NXD_ and q("tcp.example", N) == NXD_ and q("tcp.example", E, tcp=True) == OK
          and seen.get("tcp.example") == 2, seen)
    # at the same moment: the exempt device's query is in flight (the upstream waits 1.2 s) when the other device asks
    res = {}
    t0 = time.time()
    th = threading.Thread(target=lambda: res.__setitem__("E", q("slow.example", E, timeout=6))); th.start()
    time.sleep(0.3)
    rn = q("slow.example", N); tn = time.time() - t0
    th.join()
    check("IN FLIGHT: a device asking while the exempt device's query is still out is blocked at once, not handed that answer",
          rn == NXD_ and tn < 1.0 and res.get("E") == OK, (rn, round(tn, 2), res))
    h = hits()[n_hits:]
    check("blocked lookups are recorded for the devices that were blocked, never for the exempt one",
          h and all(x[1] in (N, U) for x in h) and {x[2] for x in h} == {"evil.example", "tcp.example", "slow.example"}, h)
    p = passes().splitlines()
    check("the let-through record: one line per lookup - the date and the device's MAC",
          len(p) == 7 and all(re.fullmatch(r"\d{9,11} aa:bb:cc:dd:ee:05", l) for l in p) and abs(int(p[-1].split()[0]) - time.time()) < 120, p)
    check("...and nothing of what was asked: no name is in the file", not re.search(r"evil|example|tcp|slow", passes()))
    # Wallguard keeps its own lists for an exempt device
    wgh = os.path.join(RUN, "hits")
    r_e = q("both.example", E); w_e = open(wgh).read() if os.path.exists(wgh) else ""
    check("a name on Dreadwatch's AND Wallguard's list: for the exempt device Wallguard's block applies (not forwarded, Wallguard's record)",
          r_e != OK and "both.example" not in seen and "both.example" in w_e, (r_e, seen, w_e[-200:]))
    nh = len(hits())
    check("...for another device it stays Dreadwatch's block and record", q("both.example", N) == NXD_ and len(hits()) == nh + 1 and hits()[-1][2] == "both.example", hits()[-1:])
    # the list changes while dnsmasq runs
    setlist("aa:bb:cc:dd:ee:06")
    check("the list edited: the device taken off is blocked again, the one put on gets through", q("evil.example", E) == NXD_ and q("evil.example", N) == OK)
    setlist(*(["aa:bb:cc:dd:ee:%02x" % i for i in range(0x40, 0x50)] + ["aa:bb:cc:dd:ee:05"]))
    check("the 17th line of the file is not read (16 devices at most)", q("evil.example", E) == NXD_ and q("evil.example", "10.9.0.64") == OK)
    setlist("aa:bb:cc:dd:ee:05x", "zz:bb:cc:dd:ee:05", "aa:bb:cc:dd:ee:5", " aa:bb:cc:dd:ee:05")
    check("a line that is not exactly a MAC address exempts nobody", q("evil.example", E) == NXD_)
    setlist("AA:BB:CC:DD:EE:05")
    check("upper case in the file is read as the same address", q("evil.example", E) == OK)
    os.remove(EX); time.sleep(2.4)
    check("the file removed: everybody is judged again, dnsmasq keeps running", q("evil.example", E) == NXD_ and dp.poll() is None)
except SystemExit:
    if not fails:
        fails.append("the run stopped early without a recorded failure")
except Exception as e:		# a lookup that got no answer, a socket error: a failure, never a silent pass
    fails.append("the run broke off: %r" % (e,))
finally:
    stop.set()
    for p in procs:
        try: p.kill()
        except Exception: pass
    shutil.rmtree(work, ignore_errors=True)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
sys.exit(1 if fails else 0)
