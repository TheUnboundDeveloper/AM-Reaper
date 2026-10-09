#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Site Survey page must list every network a radio can hear, parsed from the
wl utility's own text, and must be wired in everywhere a Reaper page needs to be.

WHY THIS EXISTS. Field (RT-BE86U, v3.3.3, 2026-10-04): Network Tools > WiFi Site
Survey showed no network beyond channel 44 while a GT-BE98 Pro four feet away
listed eleven of them. The stock page runs the prebuilt wlcscan_core_escan(),
which gathers the driver's escan events into a fixed buffer ("Memory not enough
for scan results") and so keeps only the first networks the scan meets, in
channel order; a single-radio 5 GHz band overflows it, a split 5 GHz-1/5 GHz-2
pair does not. Reaper_Survey.asp reads `wl escanresults` text per radio through
httpd/reaper_survey.c instead.

WHAT IT DOES.
  1. Compiles httpd/reaper_survey.c on the host with a tiny main and feeds it a
     synthetic escanresults transcript (2.4 / 5 / 6 GHz, hidden SSID, WPA2+WPA3,
     WEP, open, 40 MHz l/u, 320 MHz block, raw inner quotes, wl's own escapes,
     a record with no BSSID). Asserts the record count and every parsed field.
  2. Asserts the wiring on the real source: the parser object in httpd/Makefile,
     the include and the three CGI actions in web.c, the busy guards between the
     survey and the capture/auto-scan workers, the menu entries (both trees), the
     SUP redirect and reaper_native entry in reaper_inject.c, the page's tokens
     present in every dictionary, and no non-ASCII byte in the page.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the
tree's release/src/router as argv[1] or REAPER_ROUTER_SRC).
"""
import glob, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

def ok(msg):
    print("ok   " + msg)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
if not shutil.which("gcc"):
    skip("no gcc on the host")

def read(rel, binary=False):
    p = os.path.join(SRC, rel)
    if binary:
        return open(p, "rb").read()
    return open(p, encoding="utf-8", errors="surrogateescape").read()

# wl prints inner quotes raw, a backslash doubled and non-printables as backslash-x pairs
SAMPLE = (
    'SSID: "HomeNet"\n'
    'Mode: Managed\tRSSI: -45 dBm\tSNR: 50 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 36/80\n'
    'BSSID: 00:11:22:33:44:55\tCapability: ESS WEP ShortSlot RRM \n'
    'Supported Rates: [ 6(b) 9 12(b) 18 24(b) 36 48 54 ]\n'
    'HT Capable:\n'
    '\tChanspec: 5GHz channel 42 80MHz (0xe02a)\n'
    '\tPrimary channel: 36\n'
    'VHT Capable:\n'
    'HE Capable:\n'
    'EHT Capable:\n'
    'RSN (WPA2 + WPA3-SAE):\n'
    '\tmulticast cipher: AES-CCMP\n'
    '\tunicast ciphers(1): AES-CCMP \n'
    '\tAKM Suites(2): WPA2-PSK SAE \n'
    '\tCapabilities(0x00cc): 16 PTKSA replay counters MFPR MFPC \n'
    'SSID: "\\x00\\x00\\x00"\n'
    'Mode: Managed\tRSSI: -71 dBm\tSNR: 24 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 149/80\n'
    'BSSID: AA:BB:CC:DD:EE:01\tCapability: ESS WEP \n'
    'HT Capable:\n'
    'VHT Capable:\n'
    'RSN (WPA2):\n'
    '\tAKM Suites(1): WPA2-PSK \n'
    'SSID: "Shop "Guest" Net"\n'
    'Mode: Managed\tRSSI: -60 dBm\tSNR: 35 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 157l\n'
    'BSSID: aa:bb:cc:dd:ee:02\tCapability: ESS \n'
    'HT Capable:\n'
    'SSID: "OldPrinter"\n'
    'Mode: Managed\tRSSI: -80 dBm\tSNR: 15 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 6\n'
    'BSSID: aa:bb:cc:dd:ee:03\tCapability: ESS WEP \n'
    'Supported Rates: [ 1(b) 2(b) 5.5(b) 11(b) ]\n'
    'SSID: "Caf\\xC3\\xA9 \\\\ bar"\n'
    'Mode: Managed\tRSSI: -66 dBm\tSNR: 29 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 11\n'
    'BSSID: aa:bb:cc:dd:ee:04\tCapability: ESS \n'
    'HT Capable:\n'
    'SSID: "Six"\n'
    'Mode: Managed\tRSSI: -52 dBm\tSNR: 43 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 6g37/320-1\n'
    'BSSID: aa:bb:cc:dd:ee:05\tCapability: ESS WEP \n'
    'HE Capable:\n'
    'EHT Capable:\n'
    'RSN (WPA3-SAE):\n'
    '\tAKM Suites(2): SAE SAE-EXT \n'
    'SSID: "Broken"\n'
    'Mode: Managed\tRSSI: -50 dBm\tSNR: 40 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 44\n'
    'SSID: "Upper"\n'
    'Mode: Managed\tRSSI: -58 dBm\tSNR: 37 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 40u\n'
    'BSSID: aa:bb:cc:dd:ee:06\tCapability: ESS WEP \n'
    'HT Capable:\n'
    'WPA:\n'
    '\tAKM Suites(1): WPA-PSK \n'
    'RSN (WPA2):\n'
    '\tAKM Suites(1): WPA2-PSK \n'
    # field 2026-10-06: wl names the privacy bit WEP on every protected network; these must not read WEP
    'SSID: "Corp"\n'
    'Mode: Managed\tRSSI: -61 dBm\tSNR: 34 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 44/80\n'
    'BSSID: aa:bb:cc:dd:ee:07\tCapability: ESS WEP RRM \n'
    'RSN (WPA2):\n'
    '\tAKM Suites(2): WPA2 FT-802.1x \n'
    'SSID: "Enhanced"\n'
    'Mode: Managed\tRSSI: -63 dBm\tSNR: 32 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 6g5/160\n'
    'BSSID: aa:bb:cc:dd:ee:08\tCapability: ESS WEP \n'
    'RSN (WPA2):\n'
    '\tAKM Suites(1): Unknown-00:0F:AC(#18)  \n'
    'SSID: "NoAkm"\n'
    'Mode: Managed\tRSSI: -70 dBm\tSNR: 25 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 1\n'
    'BSSID: aa:bb:cc:dd:ee:09\tCapability: ESS WEP \n'
    'RSN (WPA2):\n'
    '\tmulticast cipher: AES-CCMP\n'
    'SSID: "OldHeader"\n'
    'Mode: Managed\tRSSI: -72 dBm\tSNR: 23 dB\tnoise: -95 dBm\tFlags: RSSI on-channel\tChannel: 11\n'
    'BSSID: aa:bb:cc:dd:ee:0a\tCapability: ESS WEP \n'
    'RSN:\n'
    '\tAKM Suites(3): WPA2-PSK SAE None \n'
)

HOME_IN = "40/160\n36/80\n100/160\n149/80\n157l\n40u\n36\n6g5/320-1\n6g37/320-2\n6g37/160\n6g69/80\n9l\n6\nxyz\n"
HOME_EXPECT = {
    "40/160": "36,40,44,48,52,56,60,64",
    "36/80": "36,40,44,48",
    "100/160": "100,104,108,112,116,120,124,128",
    "149/80": "149,153,157,161",
    "157l": "157,161",
    "40u": "36,40",
    "36": "36",
    "6g5/320-1": ",".join("6g%d" % (1 + 4 * i) for i in range(16)),
    "6g37/320-2": ",".join("6g%d" % (33 + 4 * i) for i in range(16)),
    "6g37/160": ",".join("6g%d" % (33 + 4 * i) for i in range(8)),
    "6g69/80": "6g65,6g69,6g73,6g77",
    "9l": "9,13",
    "6": "6",
    "xyz": "",
}
ERR_IN = "wl: Scan Rejected\n"
NONR_IN = "36,40,44,48,52,56,60,64\n100,104,108,112,116,120,124,128\n149,153,157,161\n6g1,6g5,6g9\n40\n60\n"
NONR_EXPECT = {
    "36,40,44,48,52,56,60,64": "36,40,44,48",
    "100,104,108,112,116,120,124,128": "",
    "149,153,157,161": "149,153,157,161",
    "6g1,6g5,6g9": "6g1,6g5,6g9",
    "40": "40",
    "60": "",
}

MAIN = r'''
#include <stdio.h>
#include <string.h>
#include "reaper_survey.h"
static int cb(const struct rsvy_ap *a, void *ctx)
{
	(void)ctx;
	printf("REC ssid=");
	rsvy_json_str(stdout, a->ssid);
	printf(" bssid=%s band=%d chan=%d width=%d rssi=%d noise=%d snr=%d phy=%d sec=[%s] hidden=%d cs=%s\n",
		a->bssid, a->band, a->chan, a->width, a->rssi, a->noise, a->snr, a->phy, a->sec, a->hidden, a->cs);
	return 0;
}
int main(int argc, char **argv)
{
	if (argc > 1 && strcmp(argv[1], "nonradar") == 0) {
		char line[96];
		while (fgets(line, sizeof(line), stdin)) {
			char in[96];
			line[strcspn(line, "\r\n")] = 0;
			strcpy(in, line);
			printf("NONR %s -> %d [%s]\n", in, rsvy_chans_nonradar(line), line);
		}
		return 0;
	}
	if (argc > 1 && strcmp(argv[1], "home") == 0) {
		char line[64], out[160];
		while (fgets(line, sizeof(line), stdin)) {
			line[strcspn(line, "\r\n")] = 0;
			printf("HOME %s -> %d [%s]\n", line, rsvy_home_chans(line, out, sizeof(out)), out);
		}
		return 0;
	}
	if (argc > 1) {
		char err[96];
		int n = rsvy_parse_escan_err(stdin, 5, cb, NULL, err, sizeof(err));
		printf("COUNT %d ERR [%s]\n", n, err);
		return 0;
	}
	int n = rsvy_parse_escan(stdin, 5, cb, NULL);
	printf("COUNT %d\n", n);
	return 0;
}
'''

tmp = tempfile.mkdtemp(prefix="rsvy_")
try:
    shutil.copy(os.path.join(SRC, "httpd", "reaper_survey.c"), tmp)
    shutil.copy(os.path.join(SRC, "httpd", "reaper_survey.h"), tmp)
    open(os.path.join(tmp, "main.c"), "w").write(MAIN)
    exe = os.path.join(tmp, "t")
    r = subprocess.run(["gcc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", "-o", exe,
                        os.path.join(tmp, "reaper_survey.c"), os.path.join(tmp, "main.c")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        die("host compile failed:\n" + r.stderr)
    ok("httpd/reaper_survey.c compiles on the host with -Wall -Wextra -Werror")
    out = subprocess.run([exe], input=SAMPLE.encode("utf-8"), capture_output=True).stdout.decode("utf-8")
    hout = subprocess.run([exe, "home"], input=HOME_IN.encode("utf-8"), capture_output=True).stdout.decode("utf-8")
    eout = subprocess.run([exe, "err"], input=ERR_IN.encode("utf-8"), capture_output=True).stdout.decode("utf-8")
    nout = subprocess.run([exe, "nonradar"], input=NONR_IN.encode("utf-8"), capture_output=True).stdout.decode("utf-8")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

recs = [l for l in out.splitlines() if l.startswith("REC ")]
count = int(re.search(r"COUNT (\d+)", out).group(1))
if count != 11 or len(recs) != 11:
    die("expected 11 records (the BSSID-less one dropped), got %d / %d\n%s" % (count, len(recs), out))
ok("11 of 12 records delivered - the record without a BSSID is dropped")
for cs, want in HOME_EXPECT.items():
    m = re.search(r"^HOME " + re.escape(cs) + r" -> (\d+) \[([^\]]*)\]$", hout, re.M)
    if not m:
        die("no HOME line for %s\n%s" % (cs, hout))
    if m.group(2) != want:
        die("home block of %s: got [%s] want [%s]" % (cs, m.group(2), want))
ok("home-block lists: 160/80/40/20 MHz on 5 GHz, 320-1/320-2/160/80 on 6 GHz, 2.4 GHz pairs, a non-chanspec gives nothing")
m = re.search(r"COUNT (\d+) ERR \[([^\]]*)\]", eout)
if not m or m.group(1) != "0" or "Scan Rejected" not in m.group(2):
    die("error capture: %s" % eout)
ok("a rejected scan delivers no record and the utility's own line reaches the caller")
for lst, want in NONR_EXPECT.items():
    m = re.search(r"^NONR " + re.escape(lst) + r" -> (\d+) \[([^\]]*)\]$", nout, re.M)
    if not m:
        die("no NONR line for %s\n%s" % (lst, nout))
    if m.group(2) != want:
        die("non-radar part of %s: got [%s] want [%s]" % (lst, m.group(2), want))
ok("radar channels 52-144 drop out of a 5 GHz list; 6 GHz and UNII-1/3 lists are untouched")

def rec(bssid):
    for l in recs:
        if ("bssid=" + bssid) in l:
            return l
    die("no record for " + bssid + "\n" + out)

l = rec("00:11:22:33:44:55")
for want in ('ssid="HomeNet"', "band=5", "chan=36", "width=80", "rssi=-45", "noise=-95", "snr=50", "phy=7",
             "sec=[WPA2/WPA3-Personal]", "hidden=0", "cs=36/80"):
    if want not in l: die("HomeNet: missing %s in %s" % (want, l))
ok("5 GHz 80 MHz WPA2+WPA3 EHT record parsed in full")

l = rec("aa:bb:cc:dd:ee:01")
for want in ('ssid=""', "hidden=1", "chan=149", "width=80", "phy=5", "sec=[WPA2-Personal]"):
    if want not in l: die("hidden: missing %s in %s" % (want, l))
ok("all-zero SSID flagged hidden, upper-case BSSID lower-cased")

l = rec("aa:bb:cc:dd:ee:02")
for want in ('ssid="Shop \\"Guest\\" Net"', "chan=157", "width=40", "phy=4", "sec=[Open]"):
    if want not in l: die("quoted: missing %s in %s" % (want, l))
ok("raw inner quotes kept and JSON-escaped once; 157l = 40 MHz; no RSN = Open")

l = rec("aa:bb:cc:dd:ee:03")
for want in ("band=2", "chan=6", "width=20", "phy=0", "sec=[WEP]"):
    if want not in l: die("WEP: missing %s in %s" % (want, l))
ok("2.4 GHz legacy WEP network: Capability flag read as WEP")

l = rec("aa:bb:cc:dd:ee:04")
for want in ('ssid="Café \\\\ bar"', "band=2", "chan=11"):
    if want not in l: die("escapes: missing %s in %s" % (want, l))
ok("wl escapes undone: the hex pairs became UTF-8, the doubled backslash became one (then JSON-escaped)")

l = rec("aa:bb:cc:dd:ee:05")
for want in ("band=6", "chan=37", "width=320", "phy=7", "sec=[WPA3-Personal]", "cs=6g37/320-1"):
    if want not in l: die("6 GHz: missing %s in %s" % (want, l))
ok("6 GHz 320 MHz block parsed")

l = rec("aa:bb:cc:dd:ee:06")
for want in ("chan=40", "width=40", "sec=[WPA/WPA2-Personal]"):
    if want not in l: die("40u: missing %s in %s" % (want, l))
ok("40u = 40 MHz; WPA and RSN AKMs folded into one label (WPA/WPA2-Personal)")

# the field defect: the privacy bit is on every protected network; WEP only without an RSN/WPA block
for b, want in (("aa:bb:cc:dd:ee:07", "sec=[WPA2-Enterprise]"), ("aa:bb:cc:dd:ee:08", "sec=[OWE]"),
                ("aa:bb:cc:dd:ee:09", "sec=[WPA2]"), ("aa:bb:cc:dd:ee:0a", "sec=[WPA2/WPA3-Personal]")):
    l = rec(b)
    if want not in l: die("security: %s missing %s in %s" % (b, want, l))
if sum(1 for l in recs if "sec=[WEP]" in l) != 1:
    die("only the legacy WEP record may read WEP:" + chr(10) + out)
ok("RSN (...) headers, wl AKM names and suite numbers labelled; privacy bit alone = WEP (one record)")

# ---- wiring on the real source ----
mk = read("httpd/Makefile")
if not re.search(r"^OBJS \+= reaper_survey\.o", mk, re.M):
    die("httpd/Makefile does not list reaper_survey.o")
ok("httpd/Makefile builds reaper_survey.o")

web = read("httpd/web.c")
for want in ('#include "reaper_survey.h"', '"svystart"', '"svystop"', '"svydata"', "rwifi_survey_worker(",
             "RWIFI_VRUN", "RWIFI_SVY", "busysvy"):
    if want not in web:
        die("web.c lacks %s" % want)
ok("web.c carries the survey worker, the three actions and the busy guards")
if web.count("busysvy") < 2:
    die("capstart and scanstart must both refuse while a survey runs")
ok("capture and auto-scan both refuse while a survey runs")
for want in (' -t passive', ' -c %s', 'rsvy_home_chans(', 'rsvy_chans_nonradar(nonr)', 'rsvy_parse_escan_err(', ' 2>&1', 't == 4 ? prim', 'dfs_status', '((r->dfs && !r->mvtry) ? 4 : 1)', '\\"tries\\":%d', '\\"passive\\":%d', '\\"home\\":%d', '\\"moved\\":\\"%s\\"',
             'r->err = m.heard > 0 ? 0 : (rc != 0 || r->msg[0]) ? ((r->dfs && !r->mvtry) ? 4 : 1) : 3',
             'rwifi_survey_restore(', 'RWIFI_SVYMV', 'get_cgi("move")', 'chanspecs -b 5 -w 80', '"exit %d"', 'rwifi_survey_worker(unit, move)'):
    if want not in web:
        die("web.c survey worker lacks %s" % want)
if 'escanresults 2>/dev/null' in web:
    die("the survey worker must keep the wl utility's stderr, not discard it")
ok("a silent radio is retried, listened to passively, then on its own channel block; the utility's error text reaches the page")
# lab metal 2026-10-06: a clean, empty full-band scan (6 GHz with no network in range) is the answer, not a refusal
if 'if (t >= 2 && rc == 0 && !r->msg[0])' not in web:
    die("the survey worker must not narrow to the own block after a clean, empty full-band scan")
ok("narrowing to the own block happens only after a rejected try; an empty band is reported as empty")
# r12 metal (owner, 2026-10-05): `wl chanspec X` alone only changes the configured chanspec of a running radio, and the
# worker inherited httpd's SIGCHLD reaper (every pclose -1). The move now goes the stock way and is verified.
for want in ('signal(SIGCHLD, SIG_DFL);', 'wl_iovar_setint(ifname, "chanspec", (int)cs)', 'wl_iovar_setint(ifname, "acs_update", -1)',
             'rsvy_cmd_hex(cmd, "Chanspec:") == ncs', 'rsvy_cmd_has(cmd, "bgdfs")', 'wl_iovar_setint(ifname, "dfs_ap_move", (int)ocs)',
             'if (move && m.heard == 0 && r->nband == 1 && csbuf[0])', 'RWIFI_SVYBK', 'the radio did not leave %.40s - not scanned',
             'fprintf(rf, "%s %s 0x%x\\n", ifname, csbuf, ocs)', 'rsvy_cs_apply(ifn, hx)', '\\"dfsl\\":\\"%s\\"',
             'rsvy_safe_line(r->dfsl, sizeof(r->dfsl), dl)'):
    if want not in web:
        die("web.c live channel move lacks %s" % want)
w0 = web.index('signal(SIGCHLD, SIG_DFL);'); w1 = web.index('rwifi_token_own(RWIFI_VRUN, "survey")', w0 - 400)
if not (w0 < w1 and w1 - w0 < 200):
    die("SIGCHLD must be reset at the top of the survey worker")
if 'r->dfs && csbuf[0]) {' in web:
    die("the move is still gated on our radar probe instead of the click")
ok("the move is applied live (chanspec + acs_update), verified on the operating chanspec, returned through dfs_ap_move when bgdfs; exit codes are real")

inj = read("httpd/reaper_inject.c")
if '"advanced_wireless_survey.asp\\":\\"Reaper_Survey.asp\\"' not in inj:
    die("reaper_inject.c SUP map lacks the survey redirect")
if '"Reaper_Survey.asp",' not in inj:
    die("reaper_inject.c reaper_native[] lacks Reaper_Survey.asp")
ok("stock survey URL redirects to the native page; native page gets the bounce without the stock CSS")

for tree in ("www/require/menuTrees/menuTree.js", "www/require/menuTrees/menuTree_ROG.js"):
    t = read(tree)
    if "Advanced_Wireless_Survey.asp" in t:
        die("%s still points at the stock survey page" % tree)
    if 'url: "Reaper_Survey.asp", tabName: "<#WiFi_sitesurvey#>"' not in t:
        die("%s lacks the Reaper_Survey.asp tab" % tree)
ok("both menu trees open Reaper_Survey.asp under Network Tools")

page = read("www/Reaper_Survey.asp", binary=True)
bad = [b for b in page if b > 0x7f]
if bad:
    die("Reaper_Survey.asp carries %d non-ASCII byte(s) - the packaging step strips them" % len(bad))
ok("page is pure ASCII")
page = page.decode("ascii")
toks = sorted(set(re.findall(r"<#(RSVY_\d+)#>", page)))
if len(toks) < 15:
    die("page uses only %d RSVY tokens" % len(toks))
dicts = [p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if not p.endswith("temp.dict")]
if len(dicts) != 25:
    die("expected 25 dictionaries, found %d" % len(dicts))
for d in dicts:
    text = open(d, encoding="utf-8", errors="surrogateescape").read()
    keys = set(re.findall(r"^(RSVY_\d+)=", text, re.M))
    missing = [t for t in toks if t not in keys]
    if missing:
        die("%s lacks %s" % (os.path.basename(d), ", ".join(missing)))
ok("every RSVY token the page uses exists in all 25 dictionaries (%d tokens)" % len(toks))
if re.search(r"'[^'\n]*<#[A-Za-z_0-9]+#>[^'\n]*'", page):
    die("a dict token sits inside a single-quoted JS string (rule 29)")
ok("no token inside a single-quoted JS string")
for want in ('id="svyradios"', '<#RSVY_25#>', '<#RSVY_26#>', '<#RSVY_27#>', 'r.passive', 'r.home', 'r.msg', 'r.err===2', 'r.err===4',
             'id="svymove"', '<#RSVY_31#>', '<#RSVY_32#>', '<#RSVY_33#>', '<#RSVY_34#>', 'r.moved', '&move=1', 'svyStart(1)', 'flex-direction:column', 'r.dfsl', '"</span>"+(r.moved?'):
    if want not in page:
        die("Reaper_Survey.asp lacks the per-radio result strip (%s)" % want)
ok("page shows each radio's own result: count and time, passive fallback, radio off, or the driver's error")
for want in ('id="svychan"', 'chcards', 'chcard t', '<#RSVY_28#>', '<#RSVY_29#>', '<#RSVY_30#>', 'run_chanspec', '<#RSYS_02#>', 'c>=4?3:c>=2?2:1'):
    if want not in page:
        die("Reaper_Survey.asp lacks the channel cards (%s)" % want)
if 'chrow' in page:
    die("Reaper_Survey.asp still carries the channel bars (chrow)")
ok("channel occupancy is rendered as cards (channel, count, 0-1/2-3/4+ colour, this router marked)")
# audit 2026-10-06 V10 (2026-10-09): an SSID that a spreadsheet would run as a formula is exported as text
if "function svyCsvSafe(s)" not in page or "/^[-=+@]/.test(v)" not in page or "c===9" not in page or "c===13" not in page:
    die("Reaper_Survey.asp lacks the CSV formula guard (svyCsvSafe: = + - @ tab CR)")
if "function q(s){ s=svyCsvSafe(s);" not in page:
    die("the CSV quoting q() does not pass values through svyCsvSafe")
ok("CSV export: a value starting with = + - @ tab or CR is prefixed with ' (spreadsheet formula guard)")
print("all checks passed")
