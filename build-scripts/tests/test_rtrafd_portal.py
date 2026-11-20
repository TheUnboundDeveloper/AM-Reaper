#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Traffic Analyzer: the Guest Portal panel (2026-11-13).

WHY THIS EXISTS. Owner request: a panel on the Live tab, shown only while a Guest Portal runs, listing the portal's
guests with their speed; the portal's share added to the total upload/download chart (owner chose two extra dashed
lines - the total is measured at the WAN port and already contains the guests); a Guest Portal row in By network
(not Top Devices); live only. A portal guest's address sits on the portal tunnel (tun22 / tun23), which the
conntrack pass never attributed, so rtrafd asks the portal itself: `chilli_query -P <port> list`.

WHAT IT DOES. Compiles the real REAPER-PORTAL block on the host with a stubbed tunnel list and a canned portal
reply in the exact long format (first line copied from the owner's router, 2026-11-13) and asserts: lines parse
(MAC normalised, short lines and junk refused), the first sight is a baseline with no rate, the next poll gives
bits/s from the session counters in the right direction (in = download), a counter that went down is a new
session (no spike), a reply cut mid-line is not read, guests that left are dropped, the table cap holds, a portal
that went away empties its guests, and the bytes reach the By network ring under the tunnel's name. Then pins the
collector wiring (label, main loop, live payload, By network rate) and the page (panel, legend, dashed lines, Live
only), runs the page's panel renderer and session-time formatter under node, and checks the five new dictionary
keys are in every pack, in lockstep.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router).
Without a host C compiler / node those parts are skipped and only the pins run."""
import glob, json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
RTRAFD = os.path.join(SRC, "rtrafd", "rtrafd.c") if SRC else ""
PAGE = os.path.join(SRC, "www", "Reaper_Traffic.asp") if SRC else ""
if not SRC or not os.path.isfile(RTRAFD):
    print("SKIP: no router tree with rtrafd/rtrafd.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

src = open(RTRAFD, encoding="latin-1").read()
page = open(PAGE, encoding="latin-1").read() if os.path.isfile(PAGE) else ""
svc_path = os.path.join(SRC, "rc", "services.c")
svc = open(svc_path, encoding="latin-1").read() if os.path.isfile(svc_path) else ""

# ---- collector pins
check("exactly one REAPER-PORTAL block (a re-applied patch once inserted a second)",
      src.count("/* REAPER-PORTAL-BEGIN") == 1 and src.count("\nstatic void portal_poll(long el_ms)\n") == 1,
      src.count("/* REAPER-PORTAL-BEGIN"))
check("the portal never swaps its octet counters (the in = download reading depends on it)",
      svc != "" and "swapoctets" not in svc)
check("tun22 asks port 42424, tun23 port 42425 (rc's cmdsocketport for each tundev)",
      'static const char *const portal_tun[2] = { "tun22", "tun23" };' in src
      and 'static const char *const portal_port[2] = { "42424", "42425" };' in src)
check("the main loop asks the portals on their own clock",
      "portal_poll(portal_last ? pms - portal_last : 0);" in src and "pms - portal_last >= PORTAL_MS" in src)
check("the portal tunnel carries its network's label",
      "if (portal_is_tun(pmtl[i].nw_t.ifname) >= 0 && nnetlbl < NNETLBL &&" in src)
check("live By network: a portal row takes the portal's own rate",
      "(unsigned long long)(pt >= 0 ? ptun_dn[pt] : lv_net_rx[i])," in src)
check("live payload carries the portal object only while a portal runs",
      "if (portal_up[0] || portal_up[1]) {" in src and '\\"portal\\":{\\"dn\\":%llu,\\"up\\":%llu,\\"cli\\":[' in src)
check("portal guests stay out of Top Devices (no cli_slot in the portal block)",
      "cli_slot" not in (re.search(r"REAPER-PORTAL-BEGIN(.*?)REAPER-PORTAL-END", src, re.S) or [None, "cli_slot"])[1])

# ---- the block, compiled and run
blk = re.search(r"/\* REAPER-PORTAL-BEGIN.*?\*/(.*?)/\* REAPER-PORTAL-END \*/", src, re.S)
check("REAPER-PORTAL block present", bool(blk))
CC = shutil.which("gcc") or shutil.which("cc")
L1 = ("02-00-5E-00-53-01 192.168.52.5 pass 6af70c6600000002 1 noauth 81/3600 1/0 %d/0 %d/0 0 0 0%%/0 0%%/0 "
      "http://192.168.52.1:8083/FreeUam?auth_status=pass vlan=\\n")
L2 = ("02-00-5E-00-53-02 192.168.52.6 dnat 6af7035c00000001 0 - 0/0 0/0 %d/0 %d/0 0 0 0%%/0 0%%/0 "
      "http://192.168.52.1:8083/FreeUam vlan=\\n")
if blk and not CC:
    print("SKIP (part): no host C compiler - the portal block was not run")
elif blk:
    prog = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/types.h>
#include <arpa/inet.h>
#define NNET 8
typedef struct { uint64_t rx, tx; } ring_t;
static ring_t rings[NNET], *r_net[NNET];
static char netname[NNET][16];
static int nnet = 0;
static int ifs_up[2];
static char reply[2][20000];
static int fail_exec = 0;
static size_t strlcpy(char *d, const char *s, size_t n)
{ size_t l = strlen(s); if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; } return l; }
static unsigned if_nametoindex(const char *n)
{ if (!strcmp(n, "tun22")) return ifs_up[0] ? 7 : 0; if (!strcmp(n, "tun23")) return ifs_up[1] ? 8 : 0; return 0; }
static int net_slot(const char *name)
{ int i; for (i = 0; i < nnet; i++) if (!strcmp(netname[i], name)) return i;
  strlcpy(netname[nnet], name, 16); return nnet++; }
static void ring_add(ring_t *r, uint64_t rx, uint64_t tx) { r->rx += rx; r->tx += tx; }
static ssize_t rt_exec_bounded(char *const argv[], char *out, size_t outsz, int secs)
{
	int t = !strcmp(argv[2], "42425"); (void)secs;
	if (fail_exec) return -1;
	if (strcmp(argv[0], "chilli_query") || strcmp(argv[1], "-P") || strcmp(argv[3], "list") || argv[4]) return -1;
	strlcpy(out, reply[t], outsz);
	return (ssize_t)strlen(out);
}
''' + blk.group(1) + r'''
static void show(const char *tag)
{
	int i;
	printf("%s n=%d tun=%llu/%llu", tag, npcl, (unsigned long long)ptun_dn[0], (unsigned long long)ptun_up[0]);
	for (i = 0; i < npcl; i++)
		printf(" [%s %s %s a%d s%d t%d dn%llu up%llu]", pcl[i].mac, pcl[i].ip, pcl[i].st, pcl[i].auth, pcl[i].sess,
		       pcl[i].tun, (unsigned long long)pcl[i].dn, (unsigned long long)pcl[i].up);
	for (i = 0; i < nnet; i++) printf(" {%s %llu/%llu}", netname[i], (unsigned long long)rings[i].rx, (unsigned long long)rings[i].tx);
	printf("\n");
}
int main(void)
{
	pcl_t g; int i;
	for (i = 0; i < NNET; i++) r_net[i] = &rings[i];
	printf("is-tun=%d,%d,%d,%d\n", portal_is_tun("tun22"), portal_is_tun("tun23"), portal_is_tun("br55"), portal_is_tun(NULL));
	printf("parse-full=%d\n", portal_parse_line("02-00-5E-00-53-01 192.168.52.5 pass 6af70c6600000002 1 noauth 81/3600 1/0 269415/0 138744/0 0 0 0%/0 0%/0 http://x vlan=", &g));
	printf("parsed %s %s %s %d %d %llu %llu\n", g.mac, g.ip, g.st, g.auth, g.sess, (unsigned long long)g.lin, (unsigned long long)g.lout);
	printf("parse-garden=%d\n", portal_parse_line("02-00-5E-00-53-01 192.168.52.5 pass 6af7 1 noauth 81/3600 1/0 500/0/7/9 400/0/1/2 0 0", &g));
	printf("garden-in=%llu out=%llu\n", (unsigned long long)g.lin, (unsigned long long)g.lout);
	printf("parse-short=%d\n", portal_parse_line("02-00-5E-00-53-01 dnat", &g));
	printf("parse-badmac=%d\n", portal_parse_line("02:00:5E:00:53:01 192.168.52.5 pass x 1 - 1/0 1/0 1/0 1/0", &g));
	printf("parse-badip=%d\n", portal_parse_line("02-00-5E-00-53-01 192.168.552.5 pass x 1 - 1/0 1/0 1/0 1/0", &g));
	printf("parse-badstate=%d\n", portal_parse_line("02-00-5E-00-53-01 192.168.52.5 PA<SS x 1 - 1/0 1/0 1/0 1/0", &g));
	printf("parse-garbage=%d\n", portal_parse_line("chilli_query: no such command", &g));

	ifs_up[0] = 1;
	sprintf(reply[0], "''' + L1 + L2 + r'''", 1000000, 500000, 0, 0);
	portal_poll(0); show("first");
	sprintf(reply[0], "''' + L1 + L2 + r'''", 1250000, 562500, 0, 0);
	portal_poll(2000); show("second");
	sprintf(reply[0], "''' + L1 + r'''", 1000, 10);
	portal_poll(2000); show("reset-and-left");
	sprintf(reply[0], "''' + L1 + r'''", 2000, 20);
	portal_poll(2000); show("after-reset");
	sprintf(reply[0], "''' + L1 + L2 + r'''", 3000, 30, 50, 60);
	reply[0][strlen(reply[0]) - 30] = 0;	/* the second line cut short, no newline */
	portal_poll(2000); show("cut");
	fail_exec = 1; portal_poll(2000); show("exec-failed"); fail_exec = 0;
	reply[0][0] = 0;
	for (i = 0; i < 70; i++) {
		char l[200];
		sprintf(l, "02-00-00-00-00-%02X 192.168.52.%d pass s 1 - 1/0 0/0 10/0 10/0 0 0\n", i, 10 + i);
		strcat(reply[0], l);
	}
	portal_poll(2000); show("cap");
	ifs_up[0] = 0; portal_poll(2000); show("portal-gone");
	ifs_up[1] = 1;
	sprintf(reply[1], "''' + L1 + r'''", 7000, 8000);
	portal_poll(2000); portal_poll(2000); show("tun23");
	return 0;
}
'''
    tmp = tempfile.mkdtemp()
    try:
        c, exe = os.path.join(tmp, "t.c"), os.path.join(tmp, "t")
        open(c, "w", encoding="latin-1").write(prog)
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-Wno-format-truncation", "-o", exe, c],
                           capture_output=True, text=True)
        check("the portal block compiles clean (-Wall -Wextra -Werror)", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            out = subprocess.run([exe], capture_output=True, text=True, timeout=30).stdout
            print(out, end="")
            has = lambda s: s in out
            line = lambda tag: next((l for l in out.splitlines() if l.startswith(tag + " ")), "")
            check("only tun22 / tun23 are portal tunnels", has("is-tun=0,1,-1,-1"))
            check("a whole line parses", has("parse-full=1"))
            check("...MAC normalised to aa:bb:.., address, state, signed-in flag, session time, in, out",
                  has("parsed 02:00:5e:00:53:01 192.168.52.5 pass 1 81 269415 138744"))
            check("garden-accounting counters (a/b/c/d) read the first figure", has("parse-garden=1") and has("garden-in=500 out=400"))
            for k in ("short", "badmac", "badip", "badstate", "garbage"):
                check("refused: %s line" % k, has("parse-%s=0" % k))
            f = line("first")
            check("first sight: both guests listed, no rate yet (baseline)",
                  "n=2 tun=0/0" in f and "[02:00:5e:00:53:01 192.168.52.5 pass a1 s81 t0 dn0 up0]" in f
                  and "[02:00:5e:00:53:02 192.168.52.6 dnat a0 s0 t0 dn0 up0]" in f and "{" not in f, f)
            s = line("second")
            check("next poll: in = download, out = upload, bits/s over the interval (250000 B / 2 s = 1 Mbit/s)",
                  "[02:00:5e:00:53:01 192.168.52.5 pass a1 s81 t0 dn1000000 up250000]" in s, s)
            check("the portal's live total is the sum of its guests", "tun=1000000/250000" in s, s)
            check("the bytes reach the By network ring under the tunnel's name (download = rx)", "{tun22 250000/62500}" in s, s)
            rl = line("reset-and-left")
            check("a counter that went down (new session) gives no spike", "dn0 up0]" in rl and "tun=0/0" in rl, rl)
            check("a guest no longer listed is dropped", "n=1 " in rl and "5a:c3" not in rl, rl)
            check("...and the ring took nothing for the reset", "{tun22 250000/62500}" in rl, rl)
            check("rates resume from the new baseline", "dn4000 up40]" in line("after-reset"), line("after-reset"))
            cu = line("cut")
            check("a reply cut mid-line: the cut line is not read (no guest from it)", "n=1 " in cu and "5a:c3" not in cu, cu)
            ef = line("exec-failed")
            check("the portal could not be asked: guests kept, no speed shown (total and each guest)",
                  "n=1 tun=0/0" in ef and "dn0 up0]" in ef, ef)
            mc = re.search(r"^cap n=(\d+) ", out, re.M)
            check("guest table capped at NPORTAL (70 listed; the one that left frees its slot after the poll)",
                  mc is not None and 63 <= int(mc.group(1)) <= 64, line("cap")[:60])
            check("portal gone: its guests leave and its rate is zero", has("portal-gone n=0 tun=0/0"), line("portal-gone"))
            t3 = line("tun23")
            check("a second portal (tun23) is asked on its own port and filed under its own name",
                  "t1 dn0 up0]" in t3 and "n=1 " in t3, t3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ---- page pins
check("the Guest Portal panel exists, hidden until a portal runs",
      '<div class="panel span" id="portalpanel" style="display:none">' in page and 'id="portaltbody"' in page)
check("the panel heading is the stock Guest Portal word", "<h2><#GuestNetwork_Portal#></h2>" in page)
check("the total chart's legend carries the two portal lines, hidden until a portal runs",
      'id="portleg_dn" style="display:none"' in page and 'id="portleg_up" style="display:none"' in page
      and "<#RTRF_104#>" in page and "<#RTRF_105#>" in page)
check("the total chart draws two more lines, dashed",
      "new LiveChart('wanchart',[],['var(--jade)','var(--crimson)','var(--jade)','var(--crimson)'])" in page
      and "setAttribute('stroke-dasharray','6 4')" in page)
check("...from the portal values in each sample, only while a portal runs",
      "pushSamp(wanSamp,[st, wan.rx_bps||0, wan.tx_bps||0, po?(po.dn||0):0, po?(po.up||0):0]);" in page
      and "clipSamples(wanSamp, t1-span, t1, 4)" in page and "if(portalOn){ d3+=" in page)
check("panel and lines on the Live tab only", "portalOn=!!po && curWin==='live';" in page)
check("panel set before the Live-only return (so a history tab hides it)",
      page.find("portalOn=!!po && curWin==='live';") < page.find("if(curWin!=='live') return;   /* rolling live charts"))
check("no latency or loss per guest", "probe" not in (re.search(r"function renderPortal\(po\)\{.*?\n\}\n", page, re.S) or [""])[0])
check("page is plain ASCII", all(ord(ch) < 128 for ch in page))

# ---- page renderer under node
NODE = shutil.which("node") or shutil.which("nodejs")
rp = re.search(r"function fmtDur\(s\)\{.*?\n\}\n.*?function renderPortal\(po\)\{.*?\n\}\n", page, re.S)
if not NODE:
    print("SKIP (part): no node - the panel renderer was not run")
elif not rp:
    check("page panel renderer found", False)
else:
    body = rp.group(0).replace("`<#RTRF_102#>`", "'SIGNED'").replace("`<#RTRF_103#>`", "'WAITING'").replace("`<#RLOG_84#>`", "'NONE'")
    js = ("var out={};var document={getElementById:function(id){return {set innerHTML(v){out[id]=v;}};}};\n"
          "function esc(s){return String(s);}function devCell(ip,mac){return '<D '+ip+' '+mac+'>';}\n"
          "function shareBar(v,t){return '<B '+(t>0?Math.round(v/t*100):0)+'>';}function fmtBps(b){return b+'bps';}\n"
          + body +
          "var r={};r.d0=fmtDur(0);r.d1=fmtDur(81);r.d2=fmtDur(3725);r.d3=fmtDur(-5);r.d4=fmtDur('x');\n"
          "renderPortal({cli:[{mac:'aa:bb',ip:'192.168.52.6',auth:0,sess:0,dn:0,up:0},"
          "{mac:'cc:dd',ip:'192.168.52.5',auth:1,sess:81,dn:3000,up:1000}]});r.rows=out.portaltbody;\n"
          "renderPortal({cli:[]});r.empty=out.portaltbody;renderPortal({});r.nocli=out.portaltbody;\n"
          "console.log(JSON.stringify(r));\n")
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
        check("panel renderer ran under node", bool(o), (r.stdout + r.stderr)[-500:])
        if o:
            check("session time as m:ss / h:mm:ss, never negative",
                  (o["d0"], o["d1"], o["d2"], o["d3"], o["d4"]) == ("0:00", "1:21", "1:02:05", "0:00", "0:00"), o)
            rows = o["rows"]
            check("busiest guest first", rows.find("192.168.52.5") < rows.find("192.168.52.6"), rows)
            check("signed-in guest: chip + session time; bar = its share of the portal (100%)",
                  "<span class=\"chip\">SIGNED</span> 1:21" in rows and "<B 100>" in rows, rows)
            check("guest not signed in yet: the waiting chip, no session time",
                  "<span class=\"chip warn\">WAITING</span></div>" in rows, rows)
            check("speeds in the two number columns", "<td class=\"num\">3000bps</td><td class=\"num\">1000bps</td>" in rows, rows)
            check("no guests: the empty line", "NONE" in o["empty"] and "NONE" in o["nocli"], (o["empty"], o["nocli"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ---- dictionaries
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if not p.endswith("temp.dict"))
if packs:
    counts, missing = set(), []
    for p in packs:
        t = open(p, encoding="utf-8").read()
        counts.add(t.count("\n"))
        for k in ("RTRF_101", "RTRF_102", "RTRF_103", "RTRF_104", "RTRF_105"):
            if not re.search(r"^%s=\S" % k, t, re.M):
                missing.append(os.path.basename(p) + ":" + k)
    check("RTRF_101-105 in all %d packs" % len(packs), not missing, missing[:6])
    check("packs still in lockstep (one line count)", len(counts) == 1, sorted(counts))
    check("the page uses all five new keys", all("<#RTRF_10%d#>" % n in page for n in range(1, 6)))

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
