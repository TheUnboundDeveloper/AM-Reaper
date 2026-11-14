#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traffic Analyzer: a network that has been removed leaves "By network" (2026-11-13).

WHY THIS EXISTS. Owner report: the Traffic Analyzer's "By network" kept showing br55 after that network (a Guest
Portal network) had been deleted. rtrafd gives a bridge a slot the first time it carries traffic (net_slot), the
slot is persisted in rtraf.db, and nothing ever let go of it: the bridge stayed in the live view at 0 for ever, in
every history window, and held one of the NNET slots for good - a network created after the slots ran out was
never counted at all.

WHAT IT DOES. Compiles the real REAPER-NETGONE block (net_iface_exists / net_gone_refresh / net_slot) on the host
with a stubbed interface list and asserts: a slot whose interface is gone is marked, the Router bucket never is,
a bridge that comes back (traffic through it again) is unmarked at once, a full table reuses a gone slot - with its
history and live rate cleared - and refuses only when no slot is gone. Then pins the wiring: the refresh runs with
the bridge list, the live payload skips gone slots, the history payload carries "netgone", and the page draws a
removed network only in a window where it carried traffic (checked under node with the page's own loop).
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router).
Without a host C compiler / node those parts are skipped and only the pins run."""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RTRAFD = os.path.join(SRC, "rtrafd", "rtrafd.c") if SRC else ""
PAGE = os.path.join(SRC, "www", "Reaper_Traffic.asp") if SRC else ""
if not SRC or not os.path.isfile(RTRAFD):
    print("SKIP: no router tree with rtrafd/rtrafd.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

src = open(RTRAFD, encoding="latin-1").read()
page = open(PAGE, encoding="latin-1").read() if os.path.isfile(PAGE) else ""

def func(sig):
    i = src.find(sig)
    if i < 0:
        return ""
    return src[i:src.find("\n}\n", i) + 3]

# ---- pins
check("exactly one REAPER-NETGONE block and one declaration (a re-applied patch once doubled them)",
      src.count("/* REAPER-NETGONE-BEGIN") == 1 and src.count("static unsigned char net_gone[NNET];") == 1)
check("the removed-network flags sit beside the slot names",
      "static unsigned char net_gone[NNET];" in src and "static void net_gone_refresh(void);" in src)
br = func("static void brsub_refresh(void)")
check("the flags are refreshed with the bridge list (same 30 s cadence)",
      br.rstrip().endswith("net_gone_refresh();	/* 2026-11-13: same human-speed cadence */\n}"), br[-200:])
lv = func("static void write_live(const char *store)")
m = re.search(r'fprintf\(o, ",\\"net\\":\{"\);(.*?)fprintf\(o, "\}"\);', lv, re.S)
check("the live payload leaves a removed network out", m is not None and "if (net_gone[i]) continue;" in m.group(1),
      m.group(1) if m else "no live net block")
check("...and still separates its entries correctly (first, not i)",
      m is not None and 'first ? "" : ","' in m.group(1) and 'i ? "," : ""' not in m.group(1))
check("the history payload names the removed networks",
      'fprintf(o, "},\\"netgone\\":[");' in src and 'fprintf(o, "],\\"class\\":{");' in src)
check("the history payload still carries every stored series", re.search(
      r'fprintf\(o, ",\\"nets\\":\{"\);\n\tfor \(i = 0; i < nnet; i\+\+\) \{\n', src) is not None)
check("the stored record layout is unchanged (no gone flag on disk)",
      "char netname[NNET][16];\n\tcli_t cli[NCLI];\n} dbhdr_t;" in src)
check("page draws a removed network only where it carried traffic",
      "var gone=d.netgone||[];" in page
      and "if(gone.indexOf(nm)>=0 && !narr.some(function(v){return v>0;}))continue;" in page)

# ---- the block, compiled and run
blk = re.search(r"/\* REAPER-NETGONE-BEGIN.*?\*/(.*?)/\* REAPER-NETGONE-END \*/", src, re.S)
check("REAPER-NETGONE block present", bool(blk))
rl = re.search(r'^#define RT_NETLBL\s+("[^"]*")', src, re.M)
nn = re.search(r"^#define NNET\s+(\d+)", src, re.M)
CC = shutil.which("gcc") or shutil.which("cc")
if blk and rl and nn and not CC:
    print("SKIP (part): no host C compiler - the slot logic was not run")
elif blk and rl and nn:
    prog = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define NNET %s
#define RT_NETLBL %s
typedef struct { uint64_t b5[288][2], hr[336][2]; } ring_t;
static ring_t rings[NNET], *r_net[NNET];
static uint64_t lv_net_rx[NNET], lv_net_tx[NNET];
static char netname[NNET][16];
static int nnet = 0;
static unsigned char net_gone[NNET];
static const char *ifs[16]; static int nifs;
static size_t strlcpy(char *d, const char *s, size_t n)
{ size_t l = strlen(s); if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; } return l; }
static unsigned if_nametoindex(const char *n)
{ int i; for (i = 0; i < nifs; i++) if (!strcmp(ifs[i], n)) return (unsigned)i + 1; return 0; }
%s
static void show(const char *tag)
{
	int i; printf("%%s nnet=%%d", tag, nnet);
	for (i = 0; i < nnet; i++) printf(" %%s%%s", netname[i], net_gone[i] ? "(gone)" : "");
	printf("\n");
}
int main(void)
{
	int i, s;
	for (i = 0; i < NNET; i++) r_net[i] = &rings[i];
	ifs[0] = "br0"; ifs[1] = "br54"; ifs[2] = "br55"; nifs = 3;
	net_slot("br0"); net_slot(RT_NETLBL); s = net_slot("br54");
	rings[s].b5[0][0] = 12345; lv_net_rx[s] = 99;	/* br54's history: must be cleared when its slot is reused */
	s = net_slot("br55");
	net_gone_refresh(); show("all-present");
	nifs = 2; net_gone_refresh(); show("br55-removed");
	printf("same-slot-again=%%d\n", net_slot("br55") == s);
	net_gone_refresh(); show("br55-traffic-again-then-refresh");
	ifs[2] = "br56"; nifs = 3; net_slot("br56"); net_gone_refresh(); show("br56-added");
	/* br55 is back, so at "full" nothing is gone */
	ifs[0] = "br0"; ifs[1] = "br54"; ifs[2] = "br55"; ifs[3] = "br56"; ifs[4] = "br57"; ifs[5] = "br58";
	ifs[6] = "br59"; ifs[7] = "br60"; nifs = 8;
	net_slot("br57"); net_slot("br58"); net_slot("br59"); net_gone_refresh(); show("full");
	printf("refused-when-none-gone=%%d\n", net_slot("br60") == -1);
	ifs[1] = "brXX"; net_gone_refresh(); show("br54-removed");
	s = net_slot("br60");
	printf("reuse-slot=%%d name=%%s gone=%%d ring-cleared=%%d live-cleared=%%d\n", s, s >= 0 ? netname[s] : "-",
	       s >= 0 ? net_gone[s] : -1, s >= 0 && rings[s].b5[0][0] == 0, s >= 0 && lv_net_rx[s] == 0);
	show("after-reuse");
	nifs = 0; net_gone_refresh(); show("no-interfaces");
	return 0;
}
''' % (nn.group(1), rl.group(1), blk.group(1))
    tmp = tempfile.mkdtemp()
    try:
        c, exe = os.path.join(tmp, "t.c"), os.path.join(tmp, "t")
        open(c, "w", encoding="latin-1").write(prog)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("the block compiles clean (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr[-600:])
        if r.returncode == 0:
            out = subprocess.run([exe], capture_output=True, text=True, timeout=30).stdout
            print(out, end="")
            has = lambda s: s in out
            check("every slot present: none marked", has("all-present nnet=4 br0 Router br54 br55\n"))
            check("a removed bridge is marked; the Router bucket and present bridges are not",
                  has("br55-removed nnet=4 br0 Router br54 br55(gone)\n"))
            check("traffic through a removed name finds its old slot", has("same-slot-again=1"))
            check("...and the next refresh marks it again while its interface is still missing",
                  has("br55-traffic-again-then-refresh nnet=4 br0 Router br54 br55(gone)\n"))
            check("a new bridge takes a free slot (the gone one is kept while slots remain)",
                  has("br56-added nnet=5 br0 Router br54 br55(gone) br56\n"))
            check("table full, every network present",
                  has("full nnet=%s br0 Router br54 br55 br56 br57 br58 br59\n" % nn.group(1)), out)
            check("full table, nothing gone: a new network is refused (as before)", has("refused-when-none-gone=1"))
            check("a removed network is marked in a full table", has("br54-removed nnet=8 br0 Router br54(gone) br55 "))
            check("full table, a gone slot available: it is reused, its history and live rate cleared",
                  has("reuse-slot=2 name=br60 gone=0 ring-cleared=1 live-cleared=1"), out)
            check("the reused slot is the removed network's, not a live one",
                  has("after-reuse nnet=8 br0 Router br60 br55 br56 br57 br58 br59\n"), out)
            check("no interfaces at all: only Router stays",
                  has("no-interfaces nnet=8 br0(gone) Router br60(gone) br55(gone) br56(gone) br57(gone) br58(gone) br59(gone)\n"), out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ---- the page's loop under node
NODE = shutil.which("node") or shutil.which("nodejs")
pm = re.search(r"  var nets=d\.nets\|\|\{\}, netLays=\[\], netCols=\[\], netLeg='', ni=0;\n(.*?\n)  document\.getElementById\('netlegend'\)",
               page, re.S)
if not NODE:
    print("SKIP (part): no node - the page loop was not run")
elif not pm:
    check("page history network loop found", False)
else:
    js = ("var NETCOLOR=['a','b','c'];function esc(s){return s;}function netTitle(s){return s;}function netLabel(s){return s;}\n"
          "function run(d){var nets=d.nets||{}, netLays=[], netCols=[], netLeg='', ni=0;\n" + pm.group(1) +
          "return netLays.length+':'+netLeg.replace(/<[^>]*>/g,'|');}\n"
          "var z=[[0,0],[0,0]], t=[[0,0],[5,1]];\n"
          "console.log(JSON.stringify({\n"
          " gonezero: run({nets:{br0:t,br55:z},netgone:['br55']}),\n"
          " gonedata: run({nets:{br0:t,br55:t},netgone:['br55']}),\n"
          " livezero: run({nets:{br0:t,br54:z},netgone:[]}),\n"
          " oldpayload: run({nets:{br0:t,br55:z}})\n"
          "}));\n")
    tmp = tempfile.mkdtemp()
    try:
        h = os.path.join(tmp, "p.js")
        open(h, "w", encoding="ascii").write(js)
        r = subprocess.run([NODE, h], capture_output=True, text=True, timeout=60)
        o = {}
        try:
            o = json.loads(r.stdout)
        except Exception:
            pass
        check("page loop ran under node", bool(o), (r.stdout + r.stderr)[-400:])
        if o:
            check("a removed network with no traffic in the window is not drawn", o["gonezero"].startswith("1:"), o)
            check("a removed network that carried traffic in the window is still drawn", o["gonedata"].startswith("2:"), o)
            check("a network that exists stays even when idle", o["livezero"].startswith("2:"), o)
            check("a payload from an older collector (no netgone) draws as before", o["oldpayload"].startswith("2:"), o)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
