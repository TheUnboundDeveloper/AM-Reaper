#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal networks: exempt from Gatekeeper, and the wizard offers the passcode (owner, 2026-11-10).

WHY THIS EXISTS. Gatekeeper hooked every network's bridge, a Guest Portal network's too. A portal network has
its own gate: chilli reads the bridge directly and hands a signed-in device's traffic to the kernel on tun22. With
both on one network the waiting room and the portal sign-in competed for the same device's port 80 and DNS, and
Gatekeeper's MAC rules never saw the tun22 traffic. The owner's decision: the portal network is exempt.
rc/gatekeeper.c leaves such a bridge out of the hooked set (it stays in GKNETS, so an Internet-only device still
cannot reach it) and writes the names to /tmp/gk/exempt; gkd neither lists devices seen on those bridges nor counts
them as missed hooks.

Second, the Guest Portal wizard had no passcode field (stock offered it only on the Portal tab of an existing
network); the wizard now carries the same switch and field. Stock shows every row under the chosen portal type,
so the row sits in its own wrapper and is a required field only while the switch is on.

WHAT IT DOES. Pins the skip in rc, compiles gkd's two helpers on the host and runs them on sample lists, pins
their three callers, and pins the wizard's switch, wrapper, checks and save. node --check on sdn.js when node exists.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
GK = os.path.join(SRC, "rc", "gatekeeper.c") if SRC else ""
if not GK or not os.path.isfile(GK):
    skip("no router source tree with rc/gatekeeper.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

gk = open(GK, encoding="utf-8", errors="surrogateescape").read()
a = gk.find("gk_add_net(gknets, sizeof(gknets), nm, &pmtl[k].nw_t);")
b = gk.find("if (pmtl[k].sdn_t.cp_idx != 0 && strcmp(nm, lanif)) {")
c = gk.find("if (!strcmp(nm, lanif)) continue;      /* $LANIF already covers it */")
check("rc: a network with a portal is skipped after it joined GKNETS and before it could join the hooked set",
      0 < a < b < c, (a, b, c))
blk = gk[b:c] if 0 < b < c else ""
check("rc: the skip records the bridge and continues", 'strcat(gkex, " "); strcat(gkex, nm);' in blk and "continue;" in blk)
check("rc: the main LAN can never be exempted", "strcmp(nm, lanif)" in blk)
check("rc: the list is written for gkd right after the sinkhole conf, and logged when not empty",
      'gk_gen_sink(gkifs);' in gk and gk.find('f_write_string(GK_DIR "/exempt", gkex, 0, 0600);') > gk.find("gk_gen_sink(gkifs);") > 0
      and 'if (gkex[0]) logmessage("gatekeeper", "Guest Portal network(s)%s: exempt, the portal sign-in is their gate", gkex);' in gk)
check("rc: the sinkhole and the hooks still follow the hooked set only", "gk_gen_sink(gkifs);" in gk and 'GKIFS=\\"$LANIF%s\\"' in gk)

GD = os.path.join(SRC, "gkd", "gkd.c")
gd = open(GD, encoding="utf-8", errors="surrogateescape").read()
m = re.search(r"^static void gk_exempt_load\(char \*buf, size_t len\)\n\{.*?^\}\n\nstatic int gk_exempt_has\(const char \*list, const char \*ifn\)\n\{.*?^\}\n", gd, re.S | re.M)
check("gkd: the two helpers are a block the test can cut out", m is not None)
cc = shutil.which("gcc") or shutil.which("cc")
if m and cc:
    with tempfile.TemporaryDirectory() as td:
        src = ('#include <stdio.h>\n#include <string.h>\n#define GK_DIR "%s"\n' % td) + m.group(0) + r"""
int main(int argc, char **argv){ char ex[256]; int i; gk_exempt_load(ex, sizeof(ex));
  for (i = 1; i < argc; i++) putchar(gk_exempt_has(ex, argv[i]) ? '1' : '0');
  return 0; }
"""
        c_ = os.path.join(td, "t.c"); x = os.path.join(td, "t"); open(c_, "w").write(src)
        r = subprocess.run([cc, "-Wall", "-Werror", "-o", x, c_], capture_output=True, text=True)
        check("gkd: the helpers compile clean (-Wall -Werror)", r.returncode == 0, r.stderr)
        if r.returncode == 0:
            names = ["br55", "br57", "br5", "br0", "r55", "br555", ""]
            def run(content):
                p = os.path.join(td, "exempt")
                if content is None:
                    if os.path.exists(p): os.remove(p)
                else:
                    open(p, "w").write(content)
                return subprocess.run([x] + names, capture_output=True, text=True).stdout
            check("gkd: ' br55 br57' exempts exactly br55 and br57 (no prefix, suffix or empty match)", run(" br55 br57\n") == "1100000", run(" br55 br57\n"))
            check("gkd: a single name with no trailing newline", run(" br55") == "1000000", run(" br55"))
            check("gkd: an empty file exempts nothing", run("") == "0000000", run(""))
            check("gkd: a missing file exempts nothing", run(None) == "0000000", run(None))
elif m:
    print("note no C compiler on the host - the helpers are not compiled")
check("gkd: the ARP scan loads the list and skips a portal bridge's rows",
      "gk_exempt_load(ex, sizeof(ex));\n\tif (!fgets(line, sizeof(line), f)) { fclose(f); return; }" in gd
      and 'if (strncmp(dev_if, "br", 2)) continue;     /* LAN bridge only */\n\t\tif (gk_exempt_has(ex, dev_if)) continue;' in gd)
check("gkd: the IPv6 neighbour scan does the same, by the row's dev name",
      'char ifn[32] = "", *dv = strstr(line, " dev ");' in gd and 'sscanf(dv + 5, "%31s", ifn) == 1 && gk_exempt_has(ex, ifn)) continue;' in gd)
check("gkd: the heal does not count a portal bridge as a missed hook",
      '"EX_=\\"$(cat " GK_DIR "/exempt 2>/dev/null)\\"; "' in gd and '"case \\" $EX_ \\" in *\\" $B \\"*) continue;; esac; "' in gd
      and gd.find('case \\" $EX_ \\"') < gd.find("ip -4 addr show dev $B"))

SJ = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "sdn.js")
sj = open(SJ, encoding="utf-8", errors="surrogateescape").read().replace("\r\n", "\n")
w0 = sj.find("\tfunction Get_Wizard_Portal(view_mode){\n")
w1 = sj.find("\n\tfunction Get_Wizard_", w0 + 10)
wz = sj[w0:w1] if 0 < w0 < w1 else ""
check("wizard: Get_Wizard_Portal is a block the test can cut out", bool(wz))
# 2026-11-12 (owner): no passcode for a Free Wi-Fi portal - the wizard's switch (added 2026-11-10) and the portal's
# own switch are gone; a portal saved with one before is treated as terms-only by rc and the sign-in page
check("wizard: no passcode switch, field or check; the preview's passcode box stays hidden",
      "FWF_passcode_enabled" not in wz and "wizard_FWF_passcode_wrap" not in wz and "var rpc_bad" not in wz
      and '.find("[data-component=FWF_passcode]").hide();' in wz)
check("wizard: the save is terms-only",
      'sdn_profile.cp_rl.auth_type = "0";//Reaper 2026-11-12 (owner): no passcode - a Free Wi-Fi portal is terms-only' in wz
      and 'sdn_profile.cp_rl.local_auth_profile = "";' in wz)
check("the portal's own settings: no passcode switch, field or check; the save is terms-only; the card prints none",
      "FWF_passcode_enabled" not in sj and "Get_Component_Input(FWF_passcode_parm)" not in sj and "$FWF_passcode" not in sj
      and 'sdn_profile.cp_rl.auth_type = "0";//Reaper 2026-11-12 (owner): no passcode - terms-only' in sj
      and '"passcode": ""/* Reaper 2026-11-12: no passcode */' in sj)
if shutil.which("node"):
    r = subprocess.run(["node", "--check", SJ], capture_output=True, text=True)
    check("sdn.js parses (node --check)", r.returncode == 0, r.stderr)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
sys.exit(1 if fails else 0)
