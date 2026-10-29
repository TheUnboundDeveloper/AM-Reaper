#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASUS DDNS (asuscomm.com, WWW.ASUS.COM / WWW.ASUS.COM.CN) is unreachable on Reaper.

WHY THIS EXISTS. Owner decision 2026-10-23: asuscomm is removed fully (de-cloud). The stock DDNS page
already hid the option, but rc still ran it, so a box with it saved could not be edited, and the ASUS
app's remote-control switch (enable_remote_control.cgi) silently created <name>.asuscomm.com.

WHAT IT CHECKS (static, against the router source tree):
  - rc/init.c clears a saved WWW.ASUS.COM or WWW.ASUS.COM.CN at boot (DDNS off, server + hostname
    empty) and logs it;
  - rc/services.c start_ddns() refuses any WWW.ASUS.COM* server before the update is built - this
    also covers the AiDisk register path, which hard-codes the server;
  - httpd/web.c enable_remote_control.cgi never writes WWW.ASUS.COM or an asuscomm hostname;
  - unreg_ASUSDDNS.cgi (row and handler) is compiled out.
The vendor code behind these paths (rc/asus_ddns.c, the asus branches of start_ddns, the inadyn
asuscomm plugin, the Warden asuscomm seed) is dead and tracked on the backlog for deletion.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - argv[1] or REAPER_ROUTER_SRC).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "services.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def rd(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="replace").read()

def compiled_out(text, needle):
    """True when every occurrence of needle sits inside an #if 0 block"""
    out = []
    for m in re.finditer(re.escape(needle), text):
        depth0, stack = False, []
        for line in text[:m.start()].split("\n"):
            s = line.strip()
            if re.match(r"#\s*if", s):
                stack.append(bool(re.match(r"#\s*if\s+0\b", s)))
            elif re.match(r"#\s*endif", s) and stack:
                stack.pop()
        out.append(any(stack))
    return bool(out) and all(out)

init = rd("rc/init.c")
i = init.find('if(!strncmp(nvram_safe_get("ddns_server_x"), "WWW.ASUS.COM", 12)){')
blk = init[i:init.find("\t}\n", i)]
check("boot clears any saved WWW.ASUS.COM* setup, with a log line",
      i >= 0 and 'nvram_set("ddns_enable_x", "0");' in blk and 'nvram_set("ddns_server_x", "");' in blk
      and 'nvram_set("ddns_hostname_x", "");' in blk and "logmessage(" in blk)

sv = rd("rc/services.c")
a = sv.find("start_ddns(char *caller, int isAidisk)")
body = sv[a:sv.find("\n}\n", a)]
g = body.find('if (strncmp(server, "WWW.ASUS.COM", 12) == 0) {')
check("start_ddns refuses WWW.ASUS.COM* right after the server is chosen (AiDisk path included)",
      g >= 0 and body.find('server = "WWW.ASUS.COM";') < g and "return -1;" in body[g:g + 300]
      and g < body.find("inadyn"))

web = rd("httpd/web.c")
a = web.find("do_enable_remote_control_cgi(char *url, FILE *stream)")
rcb = web[a:web.find("\n}\n", a)]
check("enable_remote_control.cgi never writes WWW.ASUS.COM or an asuscomm hostname",
      a >= 0 and 'nvram_set("ddns_server_x", "WWW.ASUS.COM")' not in rcb and "asuscomm.com" not in rcb.replace("<name>.asuscomm.com", ""))
check("enable_remote_control.cgi enables DDNS only for another provider with a hostname",
      'strncmp(nvram_safe_get("ddns_server_x"), "WWW.ASUS.COM", 12) != 0' in rcb)
check("unreg_ASUSDDNS.cgi row is compiled out", compiled_out(web, '{ "unreg_ASUSDDNS.cgi*"'))
check("its handler is compiled out too (no unused static)", compiled_out(web, "do_unreg_ASUSDDNS_cgi(char *url, FILE *stream)"))

if fails:
    print("\n".join("FAIL: " + f for f in fails)); sys.exit(1)
print("PASS test_asuscomm_removed")
