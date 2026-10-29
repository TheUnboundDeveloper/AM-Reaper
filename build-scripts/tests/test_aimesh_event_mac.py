#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AiMesh MAC fields reach the closed cfg_server only as MAC addresses (or empty).

WHY THIS EXISTS (2026-10-23). httpd prints re_mac / new_re_mac / target_bssid unescaped into
JSON events for the closed, root-run cfg_server (HTTPD_OB_LOCK_MSG, HTTPD_OB_SELECTION_MSG,
HTTPD_CONFIG_CHANGED_MSG): cfg_onboarding.cgi and the applyapp action_modes onboarding,
ob_selection, config_changed and prefer_node_apply. A value with a quote or brace rewrote the
event. prefer_node_apply also ran ether_atoe() on a missing value (NULL) before checking it,
which crashed httpd. httpd/web.c now gates every site on reaper_mac_or_empty(): a character
whitelist (hex digits, ':' and '-') and the stock isValidMacAddress(), or an empty value (stock
passes empties through; the topology page sends target_bssid "" for "Auto").

WHAT IT DOES. Compiles the real isValidMacAddress() (shared/misc.c) and reaper_mac_or_empty()
(httpd/web.c) on the host and checks accepted/refused values, including a brute-force sweep that
inserts or substitutes every non-MAC printable character at every position of a valid MAC. Then
checks statically that each event site is gated and that prefer_node_apply converts only inside
the check.

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
helper = func(web, "static inline int reaper_mac_or_empty(const char *m)")
check("isValidMacAddress() found in shared/misc.c", ivm is not None)
check("reaper_mac_or_empty() found in httpd/web.c", helper is not None)
if ivm is None or helper is None:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)

# ---- the helper sits outside every #if (its users are under RTCONFIG_AMAS and RTCONFIG_CFGSYNC)
depth = 0
for line in web[:web.find("static inline int reaper_mac_or_empty")].split("\n"):
    s = line.strip()
    if re.match(r"#\s*if", s):
        depth += 1
    elif re.match(r"#\s*endif", s):
        depth -= 1
check("reaper_mac_or_empty() is defined outside any #if block", depth == 0, depth)

# ---- every event site is gated
LOCK = ("else if (re_mac && new_re_mac && reaper_mac_or_empty(re_mac) && reaper_mac_or_empty(new_re_mac))\n"
        "\t\t\tsnprintf(event_msg, sizeof(event_msg), HTTPD_OB_LOCK_MSG,")
check("both HTTPD_OB_LOCK_MSG sites (cfg_onboarding.cgi, applyapp onboarding) are gated",
      web.count(LOCK) == 2 and web.count("HTTPD_OB_LOCK_MSG,") == 2, web.count(LOCK))
sel = web[web.find('!strcmp(action_mode, "ob_selection")'):]
sel = sel[:sel.find("send_cfgmnt_event")]
check("ob_selection refuses a non-empty non-MAC new_re_mac before HTTPD_OB_SELECTION_MSG",
      "if (new_re_mac && !reaper_mac_or_empty(new_re_mac))" in sel and sel.find("reaper_mac_or_empty") < sel.find("HTTPD_OB_SELECTION_MSG"))
check("config_changed gates re_mac", "if (re_mac && config && reaper_mac_or_empty(re_mac)) {" in web)
pn = web[web.find('!strcmp(action_mode, "prefer_node_apply")'):]
pn = pn[:pn.find("send_cfgmnt_event")]
g = pn.find("if (re_mac && target_bssid && reaper_mac_or_empty(re_mac) && reaper_mac_or_empty(target_bssid)) {")
c = pn.find("prefer_node_convert_nvram(re_mac, target_bssid")
check("prefer_node_apply converts only inside the check (no ether_atoe on NULL)", 0 <= g < c, (g, c))
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
''' + ivm + "\n" + helper + r'''
int main(int argc, char **argv)
{
	int i;
	for (i = 1; i < argc; i++)
		printf("%d\n", reaper_mac_or_empty(argv[i]));
	return 0;
}
'''
ACCEPT = ["AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff", "AA-BB-CC-DD-EE-FF", "AABBCCDDEEFF", ""]
REFUSE = ['AA:BB:CC:DD:EE:FF","x":"1', 'AA:BB:CC:DD:EE:F"', "{}", "AA:BB:CC:DD:EE", "AA:BB:CC:DD:EE:FF:00",
          "AA:BB:CC:DD:EE:GG", "AABBCCDDEEFF0", " AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF\n", "A\":A:BB:CC:DD:EEFF"]
base = "AA:BB:CC:DD:EE:FF"
junk = [chr(c) for c in range(32, 127) if chr(c) not in "0123456789abcdefABCDEF:-"]
sweep = []
for p in range(len(base) + 1):
    for j in junk:
        sweep.append(base[:p] + j + base[p:])
        if p < len(base):
            sweep.append(base[:p] + j + base[p + 1:])
with tempfile.TemporaryDirectory() as td:
    cf = os.path.join(td, "t.c"); exe = os.path.join(td, "t")
    open(cf, "w").write(harness)
    r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-o", exe, cf], capture_output=True, text=True)
    check("the helpers compile on the host (-Wall -Werror)", r.returncode == 0, r.stderr)
    if r.returncode != 0:
        print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
    def run(vals):
        return subprocess.run([exe] + vals, capture_output=True, text=True).stdout.split()
    got = run(ACCEPT)
    check("accepted: colon/dash/bare MACs in either case, and the empty value", got == ["1"] * len(ACCEPT), list(zip(ACCEPT, got)))
    got = run(REFUSE)
    check("refused: injection strings, short/long/non-hex/padded values", got == ["0"] * len(REFUSE),
          [v for v, o in zip(REFUSE, got) if o != "0"])
    got = run(sweep)
    passed = [v for v, o in zip(sweep, got) if o != "0"]
    check("brute force: none of %d strings with a non-MAC character passes" % len(sweep), not passed and len(got) == len(sweep), passed[:5])

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_aimesh_event_mac")
