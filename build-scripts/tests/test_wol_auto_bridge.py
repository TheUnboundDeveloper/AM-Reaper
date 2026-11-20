#!/usr/bin/env python3
"""Wake on LAN sends on the device's own network (bug review 2026-11-16, A6 item 2).

WHY. Reaper_WOL.asp lists the devices of every network (main, guest, VLAN) but always posted iface=br0. A magic
packet is a broadcast that stays on the bridge it is sent on, so a wake for a device on another network went nowhere
and the page still said it was sent. The page now posts iface=auto and reaper_net.cgi picks the bridge itself: the ARP
table (and the IPv6 neighbour table), then the DHCP lease files, else br0 - and the reply says which bridge was used.
A source is used only when it names exactly ONE bridge. The packet is never sent on every bridge: it carries the
target's MAC, which would show a main-network device to every guest station.

WHAT IT DOES. Source checks on the page, the 25 packs and httpd/web.c; with gcc, lifts the helpers between the
REAPER-WOL-AUTO markers out of web.c, compiles them on the host (-Wall -Werror) against a fake /sys/class/net and runs
them on fmemopen fixtures: br52 from ARP, two bridges = ambiguous, a lease hit, unknown = none, and a name that is not
a bridge (eth0, or a brN that is no bridge) refused.
Fixtures use documentation values (192.0.2.x, 2001:db8::, MAC 00:00:5e:00:53:xx).
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Reaper_WOL.asp")):
    print("SKIP: no router source tree with www/Reaper_WOL.asp (argv[1] / REAPER_ROUTER_SRC / REAPER_SRC)"); sys.exit(77)
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

# ---------------------------------------------------------------- the page
W = rd("www", "Reaper_WOL.asp")
code = re.sub(r"<!--.*?-->", "", W, flags=re.S)
check("page: posts iface=auto, never a fixed bridge",
      "call('action=start&tool=wake&iface=auto&target=' + encodeURIComponent(mac), function(d){" in code
      and "iface=br" not in code)
check("page: the message comes from the server's reply (bridge, source, network address)",
      "function sentText(mac, d){" in code and "msg('wakemsg', sentText(mac, d), d.src !== 'none');" in code)
st = code[code.find("function sentText(mac, d){"):]; st = st[:st.find("\n}\n") + 3]
check("page: the main network keeps RNT_47 + MAC; another network adds RNT_85 + its address; unknown adds RNT_86",
      "var t = `<#RNT_47#>` + ' ' + mac;" in st and "if (d && d.src === 'none') return t + '. ' + `<#RNT_86#>`;" in st
      and "if (d && d.iface && d.iface !== 'br0') return t + ' ' + `<#RNT_85#>` + ' ' + (d.net || d.iface);" in st
      and st.rstrip().endswith("return t;\n}"), st)
check("page: the reply is shown as text (textContent), never as HTML", "m.textContent = t || '';" in code and "wakemsg').innerHTML" not in code)
check("page: ASCII", all(ord(c) < 128 for c in W))

# ---------------------------------------------------------------- packs
wd = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(wd) if f.endswith(".dict") and f != "temp.dict")
badp, vals = [], {}
for p in packs:
    t = open(os.path.join(wd, p), encoding="utf-8").read()
    for k in ("RNT_85", "RNT_86"):
        m = re.findall(r"^%s=(.*)$" % k, t, re.M)
        if len(m) != 1 or not m[0].strip() or any(c in m[0] for c in ('"', "'", "`", "${", "<", ">")):
            badp.append((p, k))
        else:
            vals[(p, k)] = m[0]
check("RNT_85 / RNT_86 once in all %d packs, safe in a template literal" % len(packs), len(packs) == 25 and not badp, badp[:6])
en85, en86 = vals.get(("EN.dict", "RNT_85"), ""), vals.get(("EN.dict", "RNT_86"), "")
check("EN wording, plain ASCII", en85 == "on the network" and en86.startswith("The network of this device is not known, so the packet went to the main network only.")
      and all(31 < ord(c) < 127 for c in en85 + en86), (en85, en86))
same = [p for p in packs if p != "EN.dict" and vals.get((p, "RNT_86")) == en86]
check("RNT_86 is translated in every other pack", not same, same)

# ---------------------------------------------------------------- web.c: the runner
web = rd("httpd", "web.c")
b0, b1 = web.find("/* REAPER-WOL-AUTO-BEGIN */"), web.find("/* REAPER-WOL-AUTO-END */")
i_build = web.find("static const char *rnet_build(struct rnet_job *j)\n{")
check("web.c: one marked helper block, placed before rnet_build",
      web.count("/* REAPER-WOL-AUTO-BEGIN */") == 1 and web.count("/* REAPER-WOL-AUTO-END */") == 1 and 0 < b0 < b1 < i_build)
blk = web[b0:b1 + len("/* REAPER-WOL-AUTO-END */")] if 0 < b0 < b1 else ""
check("helpers: the brN gate (br + 1-4 digits) also needs the kernel to list a bridge",
      'strncmp(s, "br", 2) || !s[2] || strlen(s) > 6 || strspn(s + 2, "0123456789") != strlen(s + 2)' in blk
      and 'RNET_SYSNET "/%s/bridge"' in blk and "S_ISDIR(st.st_mode)" in blk and '#define RNET_SYSNET "/sys/class/net"' in blk)
check("helpers: ARP lines parsed as the Devices list parses them (complete = flags & 2, MAC without case)",
      '"%*s 0x%*x 0x%x %63s %*s %31s"' in blk and "if (!(flags & 2) || strcasecmp(hw, mac))" in blk)
check("helpers: host-only code (no nvram, no network list, no file opened by name, no command run)",
      not re.search(r"\b(nvram_\w+|get_mtlan|fopen|popen|system|opendir|readdir|eval)\s*\(", blk))

rb0 = web.find("static const char *rnet_wake_bridge(const char *mac, char *br, size_t brn)\n{")
rb1 = web.find("\n}\n", rb0)
RB = web[rb0:rb1] if 0 < b1 < rb0 < rb1 < i_build else ""
check("resolver found between the helpers and rnet_build", RB != "")
order = [RB.find(s) for s in ('fopen("/proc/net/arp", "r")', "reaper_nd_load(ndt, 256)", 'fopen("/var/lib/misc/dnsmasq.leases", "r")',
                              '"/var/lib/misc/dnsmasq-%d.leases"', "return rnet_wake_pick(narp, arpbr, nlease, leasebr, br, brn);")]
check("resolver order: ARP, IPv6 neighbours, the main lease file, each network's lease file, then the decision",
      all(x > 0 for x in order) and order == sorted(order), order)
check("resolver: the main lease file means br0; a network's file means that row's bridge (enabled rows with their own subnet)",
      'nlease = rnet_wake_seen(leasebr, sizeof(leasebr), nlease, "br0");' in RB
      and "if (!pmtl[i].enable || !pmtl[i].sdn_t.sdn_idx || !pmtl[i].nw_t.idx)\n\t\t\t\tcontinue;" in RB
      and "nlease = rnet_wake_seen(leasebr, sizeof(leasebr), nlease, pmtl[i].nw_t.br_ifname);" in RB)
fmts = re.findall(r'snprintf\(path, sizeof\(path\), ("[^"]*")((?:, [^;]*)?)\);', RB)
check("resolver: the lease path is built from the row's integer index only - no %s, no request text",
      fmts == [('"/var/lib/misc/dnsmasq-%d.leases"', ", pmtl[i].sdn_t.sdn_idx")] and "get_cgi" not in RB and "%s" not in "".join(f[0] for f in fmts), fmts)
check("resolver: never walks the bridges (no directory listing, no loop that sends)",
      not re.search(r"\b(opendir|readdir|scandir|glob)\s*\(", RB + blk) and "rnet_arg" not in RB and "ether-wake" not in RB + blk)

wk0 = web.find('} else if (!strcmp(tool, "wake")) {', i_build)
wk1 = web.find("\t} else\n\t\treturn \"E_TOOL\";", wk0)
WK = web[wk0:wk1] if 0 < wk0 < wk1 else ""
check("wake branch found", WK != "")
check("wake: iface=auto calls the resolver; no iface stays br0; a named bridge still passes the gate",
      'if (ifc && !strcmp(ifc, "auto")) {\n\t\t\tstrlcpy(j->src, rnet_wake_bridge(target, j->iface, sizeof(j->iface)), sizeof(j->src));' in WK
      and 'if (!ifc || !*ifc)\n\t\t\t\tifc = "br0";\n\t\t\tif (!rnet_br_ok(ifc))\n\t\t\t\treturn "E_IFACE";' in WK)
check("wake: the MAC is checked first and the chosen bridge passes the gate before the tool's arguments are built",
      0 < WK.find("if (!rnet_mac_ok(target))") < WK.find("rnet_wake_bridge(") < WK.find('if (!rnet_br_ok(j->iface))\n\t\t\treturn "E_IFACE";')
      < WK.find('rnet_arg(j, "ether-wake");'))
check("wake: ONE ether-wake on ONE bridge", WK.count('rnet_arg(j, "ether-wake");') == 1 and WK.count('rnet_arg(j, "-i"); rnet_arg(j, j->iface);') == 1
      and not re.search(r"\b(for|while)\s*\(", WK))
check("job: carries the bridge, the source and the network address",
      re.search(r"struct rnet_job \{[^}]*\tchar iface\[16\];[^}]*\tchar src\[8\];[^}]*\tchar net\[16\];[^}]*\};", web) is not None)
check("start reply names the bridge, the source and the network; the log line names the bridge",
      'websWrite(stream, "{\\"ok\\":1,\\"iface\\":\\"%s\\",\\"src\\":\\"%s\\",\\"net\\":\\"%s\\"}",\n\t\t\t\t  rnet_job.iface, rnet_job.src, rnet_job.net);' in web
      and 'logmessage("reaper_net", "%s %s on %s (%s)", rnet_job.tool, rnet_job.target, rnet_job.iface, rnet_job.src);' in web
      and 'websWrite(stream, "{\\"ok\\":1}");' in web)
nt0 = web.find("static void rnet_wake_net(const char *br, char *net, size_t n)\n{"); NT = web[nt0:web.find("\n}\n", nt0)]
check("the network address reaches the reply only as a well-formed IPv4 address",
      0 < nt0 < i_build and 'snprintf(net, n, "%s", inet_pton(AF_INET, addr, &a4) == 1 ? addr : "");' in NT)
check("the stock command path still takes br0 only (Main_WOL_Content.asp, the ASUS app)", web.count('!strcmp(tok[2], "br0")') == 2)
bad_c = [m.group(0)[:60] for m in re.finditer(r"/\*(?:[^*]|\*(?!/))*\*/", blk + RB + NT) if "/*" in m.group(0)[2:]]
check("no comment opener inside a comment in the new C", not bad_c, bad_c)

# ---------------------------------------------------------------- gcc: the helpers on fixtures
gcc = shutil.which("gcc")
if gcc and blk and sys.platform.startswith("linux"):
    td = tempfile.mkdtemp(prefix="wolauto_")
    try:
        net = os.path.join(td, "net")
        for br in ("br0", "br52", "br53"):
            os.makedirs(os.path.join(net, br, "bridge"))
        os.makedirs(os.path.join(net, "br99"))      # a brN name the kernel does not list as a bridge
        os.makedirs(os.path.join(net, "eth0"))
        harness = r'''#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
''' + blk + r'''
static int bad;
static FILE *mem(const char *s){ return *s ? fmemopen((void *)s, strlen(s), "r") : NULL; }
#define HDR "IP address       HW type     Flags       HW address            Mask     Device\n"
#define M1 "00:00:5e:00:53:01"
#define M2 "00:00:5e:00:53:02"
static int arp(const char *txt, const char *mac, char *br, size_t n){ FILE *f = mem(txt); int c = rnet_wake_arp(f, mac, br, n); if (f) fclose(f); return c; }
static int lease(const char *txt, const char *mac){ FILE *f = mem(txt); int c = rnet_wake_in_leases(f, mac); if (f) fclose(f); return c; }
static void A(const char *name, const char *txt, const char *mac, int want, const char *wbr){
  char br[16] = "zz"; int c = arp(txt, mac, br, sizeof(br));
  if (c != want || (want == 1 && strcmp(br, wbr))){ printf("ARP %s: %d [%s]\n", name, c, br); bad++; } }
static void B(const char *s, int want){ if (rnet_br_ok(s) != want){ printf("BR [%s] != %d\n", s ? s : "(null)", want); bad++; } }
static void L(const char *name, const char *txt, const char *mac, int want){ if (lease(txt, mac) != want){ printf("LEASE %s != %d\n", name, want); bad++; } }
/* the whole decision as the resolver makes it: ARP text, then (only when ARP is not exactly one) the lease files */
static void R(const char *name, const char *arptxt, const char *mainlease, const char *l52, const char *l53, const char *mac, const char *wsrc, const char *wbr){
  char abr[16] = "", lbr[16] = "", br[16] = ""; int na = arp(arptxt, mac, abr, sizeof(abr)), nl = 0; const char *src;
  if (na != 1){
    if (lease(mainlease, mac)) nl = rnet_wake_seen(lbr, sizeof(lbr), nl, "br0");
    if (lease(l52, mac)) nl = rnet_wake_seen(lbr, sizeof(lbr), nl, "br52");
    if (lease(l53, mac)) nl = rnet_wake_seen(lbr, sizeof(lbr), nl, "br53");
  }
  src = rnet_wake_pick(na, abr, nl, lbr, br, sizeof(br));
  if (strcmp(src, wsrc) || strcmp(br, wbr)){ printf("PICK %s: %s %s (want %s %s)\n", name, src, br, wsrc, wbr); bad++; } }
int main(void){
  char br[16] = ""; int c;
  B("br0", 1); B("br52", 1); B("br53", 1); B("br99", 0); B("eth0", 0); B("br", 0); B("br12345", 0); B("br5x", 0); B("br52/../br0", 0);
  B("bridge0", 0); B("BR0", 0); B("", 0); B(NULL, 0); B("auto", 0); B("br-1", 0);
  A("br52 from ARP", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n192.0.2.11 0x1 0x2 " M2 " * br0\n", M1, 1, "br52");
  A("the other MAC is on br0", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n192.0.2.11 0x1 0x2 " M2 " * br0\n", M2, 1, "br0");
  A("MAC compared without case", HDR "192.0.2.10 0x1 0x2 00:00:5E:00:53:01 * br52\n", M1, 1, "br52");
  A("two addresses on one bridge = one bridge", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n192.0.2.12 0x1 0x6 " M1 " * br52\n", M1, 1, "br52");
  A("two bridges = ambiguous", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n198.51.100.10 0x1 0x2 " M1 " * br0\n", M1, 2, "");
  A("three bridges = ambiguous", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n198.51.100.10 0x1 0x2 " M1 " * br0\n203.0.113.10 0x1 0x2 " M1 " * br53\n", M1, 2, "");
  A("an incomplete entry does not count", HDR "192.0.2.10 0x1 0x0 " M1 " * br52\n", M1, 0, "");
  A("eth0 in the device column is refused", HDR "192.0.2.10 0x1 0x2 " M1 " * eth0\n", M1, 0, "");
  A("eth0 beside a bridge: the bridge only", HDR "192.0.2.10 0x1 0x2 " M1 " * eth0\n192.0.2.10 0x1 0x2 " M1 " * br53\n", M1, 1, "br53");
  A("a brN that is no bridge is refused", HDR "192.0.2.10 0x1 0x2 " M1 " * br99\n", M1, 0, "");
  A("a shell-shaped device name is refused", HDR "192.0.2.10 0x1 0x2 " M1 " * br0;reboot\n", M1, 0, "");
  A("unknown MAC", HDR "192.0.2.11 0x1 0x2 " M2 " * br0\n", M1, 0, "");
  A("header only", HDR, M1, 0, "");
  A("empty table", "", M1, 0, "");
  if (rnet_wake_arp(NULL, M1, br, sizeof(br)) != 0 || br[0]){ printf("ARP NULL file\n"); bad++; }
  L("lease hit", "1700000000 " M1 " 192.0.2.10 nas 01:00:00:5e:00:53:01\n", M1, 1);
  L("lease hit without case", "1700000000 00:00:5E:00:53:01 192.0.2.10 * *\n", M1, 1);
  L("lease on a later line", "duid 00:01:00:01:2a:2b:2c:2d:00:00:5e:00:53:99\n1700000000 " M2 " 192.0.2.11 pc *\n1700000000 " M1 " 192.0.2.10 nas *\n", M1, 1);
  L("lease miss", "1700000000 " M2 " 192.0.2.11 pc *\n", M1, 0);
  L("a DHCPv6 line (IAID in the MAC column) never matches", "1700000000 5459265 2001:db8::10 nas 00:01:00:01:2a:2b:2c:2d:00:00:5e:00:53:01\n", M1, 0);
  L("the MAC in the host or client-id column is not a lease of that MAC", "1700000000 " M2 " 192.0.2.11 " M1 " " M1 "\n", M1, 0);
  L("empty file", "", M1, 0);
  c = rnet_wake_seen(br, sizeof(br), 0, "eth0"); if (c != 0){ printf("SEEN eth0\n"); bad++; }
  c = rnet_wake_seen(br, sizeof(br), 0, "br52"); c = rnet_wake_seen(br, sizeof(br), c, "br52"); if (c != 1 || strcmp(br, "br52")){ printf("SEEN same\n"); bad++; }
  c = rnet_wake_seen(br, sizeof(br), c, "br0"); if (c != 2){ printf("SEEN two\n"); bad++; }
  c = rnet_wake_seen(br, sizeof(br), c, "br0"); if (c != 2){ printf("SEEN stays ambiguous\n"); bad++; }
  R("br52 from ARP", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n", "", "", "", M1, "arp", "br52");
  R("ARP wins over a lease elsewhere", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n", "1 " M1 " 198.51.100.10 x *\n", "", "", M1, "arp", "br52");
  R("no ARP, a lease on br53", HDR, "", "", "1 " M1 " 192.0.2.10 nas *\n", M1, "lease", "br53");
  R("no ARP, a lease on the main network", HDR, "1 " M1 " 192.0.2.10 nas *\n", "", "", M1, "lease", "br0");
  R("ARP on two bridges falls through to the one lease", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n198.51.100.10 0x1 0x2 " M1 " * br0\n", "", "1 " M1 " 192.0.2.10 nas *\n", "", M1, "lease", "br52");
  R("ARP on two bridges and no lease = none, main network", HDR "192.0.2.10 0x1 0x2 " M1 " * br52\n198.51.100.10 0x1 0x2 " M1 " * br0\n", "", "", "", M1, "none", "br0");
  R("leases on two networks = none, main network", HDR, "", "1 " M1 " 192.0.2.10 nas *\n", "1 " M1 " 198.51.100.10 nas *\n", M1, "none", "br0");
  R("unknown = none, main network", HDR "192.0.2.11 0x1 0x2 " M2 " * br52\n", "1 " M2 " 192.0.2.11 pc *\n", "", "", M1, "none", "br0");
  if (strcmp(rnet_wake_pick(1, "eth0", 0, "", br, sizeof(br)), "none") || strcmp(br, "br0")){ printf("PICK refuses a non-bridge\n"); bad++; }
  if (strcmp(rnet_wake_pick(2, "br52", 1, "br99", br, sizeof(br)), "none") || strcmp(br, "br0")){ printf("PICK refuses a brN that is no bridge\n"); bad++; }
  printf("%d bad\n", bad); return bad != 0;
}
'''
        open(os.path.join(td, "t.c"), "w").write(harness)
        r = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Werror", '-DRNET_SYSNET="%s"' % net, "-o", os.path.join(td, "t"), os.path.join(td, "t.c")],
                           capture_output=True, text=True)
        check("the helpers compile on the host without a warning (-Wall -Werror)", r.returncode == 0, r.stderr[-600:])
        if r.returncode == 0:
            r = subprocess.run([os.path.join(td, "t")], capture_output=True, text=True, timeout=60)
            last = (r.stdout.strip().splitlines() or ["no output"])[-1]
            check("fixtures: br52 from ARP, two bridges = ambiguous, a lease hit, unknown = none, a non-bridge refused (%s)" % last,
                  r.returncode == 0 and last == "0 bad", r.stdout[-700:] + r.stderr[-200:])
        # the resolver itself and the network-address lookup, over stand-ins for the router's own lists (the network
        # table, the IPv6 neighbour table, nvram). This host's ARP table and lease files do not know the test MAC.
        i_job = web.find("struct rnet_job {\n"); i_state = web.find("static void rnet_state(const char *word", i_job)
        i_gk = web.find("static int\ngk_valid_mac(const char *m)")
        RUNNER = (web[i_gk:web.find("\n}\n", i_gk) + 3] + web[i_job:i_state]) if 0 < i_job < b0 and i_state > i_build and i_gk > 0 else ""
        check("the runner's request builder is found whole (job, validators, helpers, resolver, rnet_build)", RUNNER != "")
        if RB and NT and RUNNER:
            h2 = r'''#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <sys/stat.h>
#include <arpa/inet.h>
#include <net/if.h>
#include "reaper_nd.h"
typedef struct { int idx; char br_ifname[IFNAMSIZ]; char addr[INET_ADDRSTRLEN]; } SUBNET_T;
typedef struct { int sdn_idx; } SDNFT_T;
typedef struct { int enable; SUBNET_T nw_t; SDNFT_T sdn_t; } MTLAN_T;
static const MTLAN_T ROWS[4] = { {1, {0, "br0", "192.0.2.1"}, {0}}, {1, {1, "br52", "192.0.2.129"}, {3}},
                                 {1, {2, "br53", "not-an-address"}, {4}}, {0, {3, "br54", "198.51.100.1"}, {5}} };
static void *INIT_MTLAN(const unsigned int sz){ return calloc(8, sz); }
static void FREE_MTLAN(void *p){ free(p); }
static MTLAN_T *get_mtlan(MTLAN_T *l, size_t *n){ memcpy(l, ROWS, sizeof(ROWS)); *n = 4; return l; }
static struct reaper_nd ND[2]; static int NDN;
int reaper_nd_load(struct reaper_nd *t, int max){ int n = NDN < max ? NDN : max; memcpy(t, ND, sizeof(ND[0]) * n); return n; }
static const char *nvram_safe_get(const char *k){ const char *e = getenv(k); return e ? e : ""; }
static size_t strlcpy(char *d, const char *s, size_t n){ size_t l = strlen(s); if (n){ size_t k = l >= n ? n - 1 : l; memcpy(d, s, k); d[k] = 0; } return l; }
static const char *CGI[8]; /* name, value pairs of the request under test */
static char *get_cgi(const char *k){ int i; for (i = 0; i < 8 && CGI[i]; i += 2) if (!strcmp(CGI[i], k)) return (char *)CGI[i + 1]; return NULL; }
''' + RUNNER + r'''
static int bad;
#define M1 "00:00:5e:00:53:01"
/* one start request through the real rnet_build: the error code, or the argv it built + bridge / source / address */
static void Q(const char *name, const char *iface, const char *mac, const char *want){
  char got[200]; const char *err; int i = 0;
  CGI[i++] = "tool"; CGI[i++] = "wake"; CGI[i++] = "target"; CGI[i++] = mac; if (iface){ CGI[i++] = "iface"; CGI[i++] = iface; } CGI[i] = NULL;
  err = rnet_build(&rnet_job);
  if (err) snprintf(got, sizeof(got), "%s", err);
  else snprintf(got, sizeof(got), "%d:%s %s %s %s %s|%s|%s|%s|%d", rnet_job.argc, rnet_job.argv[0], rnet_job.argv[1], rnet_job.argv[2], rnet_job.argv[3],
                rnet_job.argv[4], rnet_job.iface, rnet_job.src, rnet_job.net, rnet_job.argv[5] == NULL);
  if (strcmp(got, want)){ printf("BUILD %s: [%s] want [%s]\n", name, got, want); bad++; } }
static void W(const char *name, const char *wsrc, const char *wbr){ char br[16] = ""; const char *s = rnet_wake_bridge("00:00:5E:00:53:01", br, sizeof(br));
  if (strcmp(s, wsrc) || strcmp(br, wbr)){ printf("BRIDGE %s: %s %s\n", name, s, br); bad++; } }
static void N(const char *br, const char *want){ char net[16] = "zz"; rnet_wake_net(br, net, sizeof(net));
  if (strcmp(net, want)){ printf("NET %s: [%s]\n", br, net); bad++; } }
int main(void){
  W("unknown everywhere", "none", "br0");
  NDN = 1; strcpy(ND[0].mac, M1); strcpy(ND[0].br, "br53"); W("IPv6 neighbour on br53", "arp", "br53");
  NDN = 2; strcpy(ND[1].mac, M1); strcpy(ND[1].br, "br53"); W("two IPv6 neighbours on one bridge", "arp", "br53");
  strcpy(ND[1].br, "br52"); W("IPv6 neighbours on two bridges, no lease", "none", "br0");
  strcpy(ND[1].br, "eth0"); W("a neighbour on a non-bridge does not count", "arp", "br53");
  setenv("lan_ipaddr", "192.0.2.1", 1); N("br0", "192.0.2.1"); N("br52", "192.0.2.129"); N("br53", ""); N("br54", ""); N("br77", "");
  setenv("lan_ipaddr", "192.0.2.1\"x", 1); N("br0", "");
  /* the request builder itself (the neighbour table now says: M1 on one bridge only) */
  setenv("lan_ipaddr", "192.0.2.1", 1); NDN = 1; strcpy(ND[0].br, "br53");
  Q("auto: the device's own bridge", "auto", "00:00:5E:00:53:01", "5:ether-wake -i br53 -b 00:00:5E:00:53:01|br53|arp||1");
  strcpy(ND[0].br, "br52");
  Q("auto: the bridge and that network's router address", "auto", "00:00:5E:00:53:01", "5:ether-wake -i br52 -b 00:00:5E:00:53:01|br52|arp|192.0.2.129|1");
  Q("auto: an unknown device goes to the main network only", "auto", "00:00:5E:00:53:77", "5:ether-wake -i br0 -b 00:00:5E:00:53:77|br0|none|192.0.2.1|1");
  Q("no iface stays br0", NULL, "00:00:5E:00:53:01", "5:ether-wake -i br0 -b 00:00:5E:00:53:01|br0|set|192.0.2.1|1");
  Q("an empty iface stays br0", "", "00:00:5E:00:53:01", "5:ether-wake -i br0 -b 00:00:5E:00:53:01|br0|set|192.0.2.1|1");
  Q("a named bridge is used as given", "br53", "00:00:5E:00:53:01", "5:ether-wake -i br53 -b 00:00:5E:00:53:01|br53|set||1");
  Q("a name that is not a bridge is refused", "eth0", "00:00:5E:00:53:01", "E_IFACE");
  Q("a brN the kernel does not list as a bridge is refused", "br99", "00:00:5E:00:53:01", "E_IFACE");
  Q("an option-shaped name is refused", "-b", "00:00:5E:00:53:01", "E_IFACE");
  Q("a path-shaped name is refused", "br0/../br52", "00:00:5E:00:53:01", "E_IFACE");
  Q("AUTO in capitals is not the keyword", "AUTO", "00:00:5E:00:53:01", "E_IFACE");
  Q("a bad MAC is refused before any lookup", "auto", "00:00:5E:00:53", "E_MAC");
  Q("an option-shaped MAC is refused", "auto", "-i", "E_MAC");
  printf("%d bad\n", bad); return bad != 0;
}
'''
            open(os.path.join(td, "t2.c"), "w").write(h2)
            r = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Werror", '-DRNET_SYSNET="%s"' % net, "-I", os.path.join(SRC, "shared"),
                                "-o", os.path.join(td, "t2"), os.path.join(td, "t2.c")], capture_output=True, text=True)
            check("the whole request builder compiles over stand-ins for the router lists (-Wall -Werror)", r.returncode == 0, r.stderr[-600:])
            if r.returncode == 0:
                r = subprocess.run([os.path.join(td, "t2")], capture_output=True, text=True, timeout=60)
                last = (r.stdout.strip().splitlines() or ["no output"])[-1]
                check("real rnet_build: auto / no iface / named bridge / refusals; IPv6 neighbours count like ARP; the address is IPv4 or empty (%s)" % last,
                      r.returncode == 0 and last == "0 bad", r.stdout[-700:] + r.stderr[-200:])
    finally:
        shutil.rmtree(td, ignore_errors=True)
else:
    print("note: gcc not found (or not Linux) - the helper run is skipped")

node = shutil.which("node")
if node:
    s = re.findall(r"<script>(.*?)</script>", W, re.S)[-1]
    s = re.sub(r"<%.*?%>", "0", re.sub(r"<%\s*nvram_get_js\([^%]*%>", '""', s))
    EN = dict(l.split("=", 1) for l in open(os.path.join(wd, "EN.dict"), encoding="utf-8").read().splitlines() if "=" in l)
    f0 = s.find("function sentText(mac, d){"); f1 = s.find("\n}\n", f0)
    fn = re.sub(r"<#([A-Za-z0-9_]+)#>", lambda m: EN.get(m.group(1), "?" + m.group(1)), s[f0:f1 + 3])
    js = fn + r'''
var M = '00:00:5E:00:53:01';
console.log(JSON.stringify([sentText(M, {ok: 1, iface: 'br0', src: 'arp', net: '192.0.2.1'}), sentText(M, {ok: 1, iface: 'br52', src: 'lease', net: '192.0.2.129'}),
  sentText(M, {ok: 1, iface: 'br52', src: 'arp', net: ''}), sentText(M, {ok: 1, iface: 'br0', src: 'none', net: '192.0.2.1'}), sentText(M, {ok: 1})]));
'''
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(js); jp = f.name
    r = subprocess.run([node, jp], capture_output=True, text=True); os.unlink(jp)
    import json
    try: got = json.loads(r.stdout)
    except Exception: got = []
    want = ["Magic packet sent to 00:00:5E:00:53:01", "Magic packet sent to 00:00:5E:00:53:01 on the network 192.0.2.129",
            "Magic packet sent to 00:00:5E:00:53:01 on the network br52", "Magic packet sent to 00:00:5E:00:53:01. " + en86,
            "Magic packet sent to 00:00:5E:00:53:01"]
    check("node: the page's text for the main network, another network, an unknown device and an old reply", got == want, (r.stderr[-300:], got))
else:
    print("note: node not found - the message run is skipped")

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
