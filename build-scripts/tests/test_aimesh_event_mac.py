#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AiMesh MAC fields reach the closed cfg_server only as MAC addresses (or an empty target_bssid).

WHY THIS EXISTS (2026-10-23). httpd prints re_mac / new_re_mac / target_bssid unescaped into
JSON events for the closed, root-run cfg_server (HTTPD_OB_LOCK_MSG, HTTPD_OB_SELECTION_MSG,
HTTPD_CONFIG_CHANGED_MSG): cfg_onboarding.cgi and the applyapp action_modes onboarding,
ob_selection, config_changed and prefer_node_apply. A value with a quote or brace rewrote the
event. prefer_node_apply also ran ether_atoe() on a missing value (NULL) before checking it,
which crashed httpd. On the 40585 base (merge stop 63) every site is ASUS's own isValidMacAddress()
check (Reaper's reaper_mac_or_empty() wrapper is gone); empty values are refused except
target_bssid "" ("Auto" on the topology page), which prefer_node_apply lets through by length.

WHAT IT DOES. Compiles the real isValidMacAddress() (shared/misc.c) on the host and checks
accepted/refused values, including a brute-force sweep that inserts or substitutes every non-MAC
printable character at every position of a valid MAC, and a run of non-hex text ahead of the
first separator (a count-only check lets that through). Then checks statically that each event
site is gated and that prefer_node_apply converts only inside the check.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
WEB = os.path.join(SRC, "httpd", "web.c")
MISC = os.path.join(SRC, "shared", "misc.c")
if not SRC or not os.path.isfile(WEB) or not os.path.isfile(MISC):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

web = open(WEB, encoding="utf-8", errors="surrogateescape").read()
misc = open(MISC, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def func(text, sig):
    a = text.find(sig)
    if a < 0:
        return None
    return text[a:text.find("\n}\n", a) + 3]

ivm = func(misc, "int isValidMacAddress(const char* mac) {")
check("isValidMacAddress() found in shared/misc.c", ivm is not None)
if ivm is None:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)

# ---- every event site is gated (40585 base, merge stop 63: ASUS's isValidMacAddress() at each site)
LOCK = re.compile(r"if \(isValidMacAddress\(re_mac\) && isValidMacAddress\(new_re_mac\)\) \{\s*"
                  r"snprintf\(event_msg, sizeof\(event_msg\), HTTPD_OB_LOCK_MSG,")
check("both HTTPD_OB_LOCK_MSG sites (cfg_onboarding.cgi, applyapp onboarding) are gated",
      len(LOCK.findall(web)) == 2 and web.count("HTTPD_OB_LOCK_MSG,") == 2, len(LOCK.findall(web)))
sel = web[web.find('!strcmp(action_mode, "ob_selection")'):]
sel = sel[:sel.find("send_cfgmnt_event")]
check("ob_selection refuses a non-MAC new_re_mac before HTTPD_OB_SELECTION_MSG",
      "if (new_re_mac && !isValidMacAddress(new_re_mac)) {" in sel
      and sel.find("isValidMacAddress") < sel.find("} else {") < sel.find("HTTPD_OB_SELECTION_MSG"))
cc = web[web.find('!strcmp(action_mode, "config_changed")'):]
cc = cc[:cc.find("send_cfgmnt_event")]
check("config_changed gates re_mac", "if (re_mac && config) {" in cc and "if (!isValidMacAddress(re_mac)) {" in cc
      and cc.find("isValidMacAddress") < cc.find("} else {") < cc.find("HTTPD_CONFIG_CHANGED_MSG"))
pn = web[web.find('!strcmp(action_mode, "prefer_node_apply")'):]
pn = pn[:pn.find("send_cfgmnt_event")]
n = pn.find("if (re_mac && target_bssid) {")
g = pn.find("if (!isValidMacAddress(re_mac) || (strlen(target_bssid) > 0 && !isValidMacAddress(target_bssid))) {")
c = pn.find("prefer_node_convert_nvram(re_mac, target_bssid")
check("prefer_node_apply converts only inside the check (no ether_atoe on NULL)", 0 <= n < g < pn.find("} else {", g) < c, (n, g, c))
check("HTTPD_CONFIG_CHANGED_MSG has exactly the two gated users", web.count("HTTPD_CONFIG_CHANGED_MSG,") == 2)

# carried from ASUS GPL 102_40585 (via Merlin): the remaining cfg_server events
def block(start, end):
    a = web.find(start)
    return web[a:web.find(end, a)] if a >= 0 else ""
rs = block('!strcmp(action_mode, "remove_slave")', '!strcmp(action_mode, "reset_default")')
check("remove_slave/self_optimize send HTTPD_SLAVE_MSG only for a valid slave_mac",
      "if (slave_mac && isValidMacAddress(slave_mac)) {" in rs and rs.find("isValidMacAddress") < rs.find("HTTPD_SLAVE_MSG"))
rd = block('!strcmp(action_mode, "reset_default")', '!strcmp(action_mode, "start_wps_registrar")')
check("reset_default aborts the whole list on one non-MAC entry",
      "if (!isValidMacAddress(b)) {" in rd and "if (invalid_mac)" in rd and rd.find("if (invalid_mac)") < rd.find("HTTPD_SLAVE_LIST_MSG"))
dv = block('!strcmp(action_mode, "device_reboot")', 'HTTPD_ACTION_MSG,')
check("device_reboot/re_reconnect/force_roaming: device_list entries, client_mac, target_ap are MACs, block_time is digits",
      "if (!isValidMacAddress(b)) {" in dv and "if (invalid_dev_mac)" in dv
      and "if (client_mac && isValidMacAddress(client_mac)) {" in dv
      and "if (isValidMacAddress(target_ap)) {" in dv and "if (isValid_digit_string(block_time)) {" in dv)

# ---- behaviour, compiled on the host
harness = r'''
#include <stdio.h>
#include <string.h>
#include <ctype.h>
''' + ivm + r'''
int main(int argc, char **argv)
{
	int i;
	for (i = 1; i < argc; i++)
		printf("%d\n", isValidMacAddress(argv[i]));
	return 0;
}
'''
ACCEPT = ["AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff", "AA-BB-CC-DD-EE-FF", "AABBCCDDEEFF"]
# "" is refused here; the one site that takes an empty value (target_bssid) skips the check by length
REFUSE = ['AA:BB:CC:DD:EE:FF","x":"1', 'AA:BB:CC:DD:EE:F"', "{}", "AA:BB:CC:DD:EE", "AA:BB:CC:DD:EE:FF:00",
          "AA:BB:CC:DD:EE:GG", "AABBCCDDEEFF0", " AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF\n", "A\":A:BB:CC:DD:EEFF", "",
          # one hex digit, a run of non-hex text, then a separator: a separator-count check resets and lets the text
          # through into the cfg_server JSON event (reaper_mac_or_empty's character whitelist refused these)
          'A":A:BB:CC:DD:EE:FF', 'A","x":"y":A:BB:CC:DD:EE:FF', '0}],"k":[{"q":0:BB:CC:DD:EE:FF']
base = "AA:BB:CC:DD:EE:FF"
junk = [chr(c) for c in range(32, 127) if chr(c) not in "0123456789abcdefABCDEF:-"]
sweep = []
for p in range(len(base) + 1):
    for j in junk:
        sweep.append(base[:p] + j + base[p:])
        if p < len(base):
            sweep.append(base[:p] + j + base[p + 1:])
for j in junk:
    sweep.append(base[0] + j + ":" + base[1:])
    sweep.append(base[0] + j + j + "-" + base[1:].replace(":", "-"))
with tempfile.TemporaryDirectory() as td:
    cf = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(cf, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-o", exe, cf], capture_output=True, text=True)
    check("isValidMacAddress() compiles on the host (-Wall -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
    def run(vals):
        return subprocess.run([exe] + vals, capture_output=True, text=True).stdout.split()
    got = run(ACCEPT)
    check("accepted: colon/dash/bare MACs in either case", got == ["1"] * len(ACCEPT), list(zip(ACCEPT, got)))
    got = run(REFUSE)
    check("refused: injection strings (incl. non-hex text ahead of the first separator), short/long/non-hex/padded/empty values",
          got == ["0"] * len(REFUSE),
          [v for v, o in zip(REFUSE, got) if o != "0"])
    got = run(sweep)
    passed = [v for v, o in zip(sweep, got) if o != "0"]
    check("brute force: none of %d strings with a non-MAC character passes" % len(sweep), not passed and len(got) == len(sweep), passed[:5])

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_aimesh_event_mac")
