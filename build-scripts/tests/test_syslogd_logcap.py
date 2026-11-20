#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""System log: one kind of line cannot flood the log on flash (2026-11-13).

WHY THIS EXISTS. Every system log line is appended to the log on flash and nothing in the path limited how fast.
A device looping on DHCP, a daemon repeating one error or a driver printing a line per packet wrote without bound:
the real history rotated out of the 1 MB file in seconds, and the flash and a CPU stayed busy. Several of the
sources are closed, so the limit sits in the log daemon, where every line passes: one kind of line (the program's
tag and the first characters of its text, digits levelled) may be written 300 times at once and 10 times a second
after that; what is held back is counted and reported in one line.

WHAT IT DOES. Compiles the REAPER-LOGCAP block of busybox/sysklogd/syslogd.c on the host with a clock it controls
and runs it: how lines are grouped into kinds, the burst and the steady rate, the "not logged" count while a flood
lasts and after it stops, that one kind never costs another its lines, and that the table copes with more kinds
than it has room for. Then it pins the wiring in timestamp_and_log(): only lines the level filter would write are
counted, severity crit and above always goes through, the count is written through the same path, and the remote
log server is untouched. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree - argv[1] or REAPER_ROUTER_SRC
= .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
SL = os.path.join(SRC, "busybox", "sysklogd", "syslogd.c") if SRC else ""
if not SL or not os.path.isfile(SL):
    skip("no router tree with busybox/sysklogd/syslogd.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:500] if detail else ""))

def done():
    print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
    if fails:
        print("\n".join(fails))
    sys.exit(1 if fails else 0)

src = open(SL, encoding="utf-8", errors="surrogateescape").read()
m = re.search(r"/\* REAPER-LOGCAP-BEGIN.*?\*/(.*?)/\* REAPER-LOGCAP-END \*/", src, re.S)
check("syslogd.c carries the REAPER-LOGCAP block", m is not None)
if not m:
    done()
block = m.group(1)
def const(name):
    mm = re.search(r"#define %s\s+(\d+)" % name, block)
    return int(mm.group(1)) if mm else -1
BURST, RATE, REPORT, QUIET, SLOTS = const("RLC_BURST"), const("RLC_RATE"), const("RLC_REPORT"), const("RLC_QUIET"), const("RLC_SLOTS")
check("the limits: 300 at once, 10 a second, a count every 30 s while it lasts and 5 s after it stops, 24 kinds tracked",
      (BURST, RATE, REPORT, QUIET, SLOTS) == (300, 10, 30, 5, 24), (BURST, RATE, REPORT, QUIET, SLOTS))

# a script on stdin: "k <msg>" print the kind; "t <sec>" set the clock; "m <count> <msg>" send count lines ->
# "<passed> <held>" plus one "told <n> <kind>" per count reported on the way
MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
%s
int main(void)
{
	static struct rlc c;
	char line[512], key[RLC_KEY + 1], like[RLC_KEY + 1];
	unsigned now = 1000, told;
	while (fgets(line, sizeof(line), stdin)) {
		line[strcspn(line, "\n")] = 0;
		if (line[0] == 'k') { rlc_key(line + 2, key); printf("[%%s]\n", key); }
		else if (line[0] == 't') now = 1000 + (unsigned)atoi(line + 2);
		else if (line[0] == 'm') {
			char *msg; long n = strtol(line + 2, &msg, 10), i, pass = 0, held = 0;
			while (*msg == ' ') msg++;
			for (i = 0; i < n; i++) {
				if (rlc_check(&c, now, msg, &told, like)) held++; else pass++;
				if (told) printf("told %%u %%s\n", told, like);
			}
			printf("%%ld %%ld\n", pass, held);
		}
	}
	return 0;
}
'''
tmp = tempfile.mkdtemp()
try:
    cf = os.path.join(tmp, "c.c"); exe = os.path.join(tmp, "c")
    open(cf, "w").write(MAIN % block)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wshadow", "-Wdeclaration-after-statement", "-Werror", "-o", exe, cf],
                       capture_output=True, text=True)
    check("the block compiles with -Wall -Wextra -Wshadow -Wdeclaration-after-statement -Werror", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        def run(script):
            return subprocess.run([exe], input="\n".join(script) + "\n", capture_output=True, text=True).stdout.splitlines()

        kinds = {
            "dnsmasq-dhcp[2211]: DHCPDISCOVER(br0) 00:11:22:33:44:55": "[dnsmasq-dhcp:DHCPDISCOVER]",
            "dnsmasq-dhcp[9]: DHCPDISCOVER(br52) aa:bb:cc:dd:ee:ff": "[dnsmasq-dhcp:DHCPDISCOVER]",
            "kernel: [ 1234.567890] dhd_pktfwd_lut_lkup: no entry 7": "[kernel:dhd_pktfwd_l]",
            "kernel: dhd_pktfwd_lut_lkup: no entry 912": "[kernel:dhd_pktfwd_l]",
            "kernel: Unable to handle kernel paging request": "[kernel:Unable to ha]",
            "hostapd: wl0.1: STA a4:11 IEEE 802.11: associated": "[hostapd:wl#.#: STA a]",
            "hostapd: wl1.1: STA a4:11 IEEE 802.11: associated": "[hostapd:wl#.#: STA a]",
            "bsd: bsd: Sending act Frame to 12:34": "[bsd:bsd: Sending]",
            "rc_service: watchdog 1234:notify_rc restart_x": "[rc_service:watchdog ###]",
            "averyveryverylongprogramname[1]: text here": "[averyveryverylo:text here]",
            "no colon at all in this line": "[no:colon at all]",
            "tag:": "[tag:]",
            "": "[:]",
            "kernel: [text] not a clock": "[kernel:[text] not a]",
        }
        got = run(["k " + k for k in kinds])
        check("kinds: the tag and the first 12 characters of the text; a pid, the kernel's clock and digits do not split a kind",
              got == list(kinds.values()), [(k, g) for (k, g) in zip(kinds, got) if kinds[k] != g])

        F = "dnsmasq-dhcp[1]: DHCPDISCOVER(br0) 00:11:22:33:44:55"
        o = run(["m %d %s" % (BURST + 50, F)])
        check("a flood: the first 300 lines are written, the rest held back", o == ["%d %d" % (BURST, 50)], o)
        o = run(["m %d %s" % (BURST, F), "t 1", "m 100 " + F, "t 2", "m 100 " + F])
        check("after the burst: 10 lines a second get through", o == ["300 0", "10 90", "10 90"], o)
        o = run(["m %d %s" % (BURST, F), "t 60", "m %d %s" % (BURST + 5, F)])
        check("a pause refills the allowance (to 300, never more)", o == ["300 0", "300 5"], o)
        o = run(["m 5 a: one", "m 5 b: two", "m %d %s" % (BURST + 400, F), "m 5 a: one", "m 5 b: two"])
        check("one kind flooding costs no other kind a line", o == ["5 0", "5 0", "300 400", "5 0", "5 0"], o)

        # the count while the flood lasts: nothing in the first 30 s, then one line with everything held back so far
        script = ["m %d %s" % (BURST + 100, F)]
        for t in range(1, 31):
            script += ["t %d" % t, "m 50 " + F]
        o = run(script)
        told = [x for x in o if x.startswith("told")]
        held_before = 100 + 29 * 40      # everything held back up to the first line of second 30, which itself is written
        check("while a flood lasts the count is written once every 30 s, not per line",
              len(told) == 1 and told[0] == "told %d dnsmasq-dhcp:DHCPDISCOVER" % held_before
              and o.index(told[0]) == len(o) - 2, (told, o[-3:]))
        # the count after the flood stops: the next line of any other kind, 5 s later, carries it
        o = run(["m %d %s" % (BURST + 7, F), "t 3", "m 1 other: line", "t 5", "m 1 other: line", "t 6", "m 1 other: line"])
        check("after a flood stops the count is written once it has been quiet for 5 s, by whatever line comes next",
              o == ["300 7", "1 0", "told 7 dnsmasq-dhcp:DHCPDISCOVER", "1 0", "1 0"], o)
        o = run(["m %d %s" % (BURST + 7, F), "t 40", "m 1 " + F])
        check("a kind that comes back slowly reports its own count with its next line", o == ["300 7", "told 7 dnsmasq-dhcp:DHCPDISCOVER", "1 0"], o)

        # more kinds than slots: nothing is held back, and a kind with a count to report is not the one given up
        script = ["m %d %s" % (BURST + 9, F), "t 1"] + ["m 1 prog%02d: line" % i for i in range(SLOTS * 3)] + ["t 2", "m 300 " + F]
        o = run(script)
        mid = o[1:1 + SLOTS * 3]
        check("more kinds than the table holds: every one of them is still written", all(x == "1 0" for x in mid), mid[:5])
        check("... and the flooding kind kept its place: no fresh allowance, its count intact",
              o[-1] == "20 280" and not any(x.startswith("told") for x in o), o[-3:])
        o = run(["m 3 x: y"])
        check("ordinary traffic is untouched", o == ["3 0"], o)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# wiring in timestamp_and_log()
fn = src[src.find("static void timestamp_and_log(int pri, char *msg, int len)\n"):src.find("static void timestamp_and_log_internal(")]
check("timestamp_and_log() found", len(fn) > 300)
i_kmsg = fn.find("log_to_kmsg(pri, msg);"); i_cap = fn.find("rlc_check(&reaper_rlc, monotonic_sec(), msg, &told, like)"); i_fmt = fn.find("if (option_mask32 & OPT_small)")
check("the cap runs once, after the time stamp is split off and before the line is formatted or written", 0 <= i_kmsg < i_cap < i_fmt and fn.count("rlc_check(") == 1, (i_kmsg, i_cap, i_fmt))
check("only lines the level filter would write are counted, and severity crit and above always goes through",
      "if (LOG_PRI(pri) < G.logLevel && LOG_PRI(pri) > LOG_CRIT) {" in fn)
check("the count is one line of its own, written through the same path, then the held line is dropped",
      re.search(r'snprintf\(say, sizeof\(say\), "syslogd: %u line\(s\) not logged[^"]*%s\.\.\.",\s*told, RLC_RATE, like\);\s*timestamp_and_log\(LOG_SYSLOG \| LOG_NOTICE, say, 0\);', fn) is not None
      and re.search(r"if \(hold\)\s*return;", fn) is not None)
check("the state is one static table next to the block", src.count("static struct rlc reaper_rlc;") == 1)
loop = src[src.find("static void do_syslogd(void)"):]
i_remote = loop.find("sendto(rh->remoteFD, recvbuf, sz+1,"); i_local = loop.find("split_escape_and_log(recvbuf, sz);")
check("the remote log server is sent every line before the local cap is reached", 0 <= i_remote < i_local and "rlc_" not in loop[:i_local], (i_remote, i_local))

done()
