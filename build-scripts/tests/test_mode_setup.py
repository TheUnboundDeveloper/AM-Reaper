#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reaper_ModeSetup.asp writes what the stock wizard writes, and the wizard is no longer the way in (2026-10-15).

WHY THIS EXISTS. Changing the operation mode to Access Point, Media Bridge or back to Router used to
leave the shell for ASUS's QIS wizard. Rung B of docs/backlog/qis-aimesh-only.md replaces those three
with a native step page, and rung C points the MLO page's "Get started" at the Wireless console. The
page is only correct while it posts the same nvram the wizard would, so this test reads the wizard's
own source (www/sysdep/FUNCTION/QIS_V3/mobile/js) and holds the page to it: a GPL merge that changes
what the wizard writes for a mode fails here instead of silently diverging.

WHAT IT CHECKS.
  - per mode, every literal qisPostData.<key> = <value> in handler.js goTo.apMode / mbMode / rtMode
    (and the wlc_psta / sw_mode pair of the bcmwifi + amas branch) is written by postData() with the
    same value; the LAN keys of lanDHCP / apply.lanStatic; generalObj for Media Bridge;
  - the service: restart_all for Router, reboot otherwise (plugins.js getRestartService);
  - the parent security names map onto the auth modes setupWLCNvram() uses;
  - Advanced_OperationMode_Content.asp jumps to the page for ap / mb / rt and names the wizard only
    for Repeater and AiMesh Node; mlo.js no longer names the wizard;
  - the page is skip-listed in reaper_inject.c and listed in reaper_langcheck.py OUR[];
  - RMOD_1..85 exist non-empty in all 25 packs, every token on the page resolves, none sits in a
    single-quoted string (rule 29), the page is ASCII (rule 1);
  - self-test: the pre-rung chooser lines fail the chooser rule.

Exit 0 pass, 1 fail, 77 skipped (no router tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import glob, os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
W = os.path.join(SRC, "www") if SRC else ""
PAGE = os.path.join(W, "Reaper_ModeSetup.asp")
QIS = os.path.join(W, "sysdep", "FUNCTION", "QIS_V3", "mobile", "js")
if not SRC or not os.path.isfile(PAGE) or not os.path.isdir(QIS):
    skip("no router source tree with www/Reaper_ModeSetup.asp and the QIS_V3 wizard")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def rd(p):
    return open(p, encoding="utf-8", errors="replace").read()

page = rd(PAGE)
handler = rd(os.path.join(QIS, "handler.js"))
plugins = rd(os.path.join(QIS, "plugins.js"))
qisdata = rd(os.path.join(QIS, "qisData.js"))

def fn_body(src, name):
    m = re.search(r"\n" + re.escape(name) + r" = function\(\)\{\n(.*?)\n\};\n", src, re.S)
    return m.group(1) if m else ""

def wizard_literals(body):
    """qisPostData.key = <literal> outside any if/else branch body we do not take."""
    out = {}
    for k, v in re.findall(r"qisPostData\.(\w+) = (\"[^\"]*\"|'[^']*'|\d+);", body):
        out[k] = v.strip("\"'")
    return out

pd = re.search(r"function postData\(\)\{(.*?)\n\}\n", page, re.S)
check("page: postData() found", pd is not None)
pd = pd.group(1) if pd else ""
def page_branch(mode):
    if mode == "rt":
        m = re.search(r"if \(MODE === 'rt'\)\{(.*?)\n  \} else \{", pd, re.S)
    elif mode == "ap":
        m = re.search(r"if \(MODE === 'ap'\)\{(.*?)\}", pd, re.S)
    else:
        m = re.search(r"else \{\n      var p = parent\(\);(.*?)\n    \}", pd, re.S)
    return m.group(1) if m else ""
def page_keys(txt):
    return dict(re.findall(r"d\.(\w+)\s*=\s*'([^']*)'", txt))

# -- the per-mode keys -----------------------------------------------------------------------
ap_w = wizard_literals(fn_body(handler, "goTo.apMode"))
rt_w = wizard_literals(fn_body(handler, "goTo.rtMode").split("if(systemVariable.advSetting")[0])
mb_body = fn_body(handler, "goTo.mbMode")
mb_w = wizard_literals(mb_body.split("else{", 1)[1] if "else{" in mb_body else "")	# the non-qca/ra branch
rp_body = fn_body(handler, "goTo.rpMode")
check("wizard: goTo.apMode / rtMode / mbMode parsed", bool(ap_w and rt_w and mb_w), (ap_w, rt_w, mb_w))
for mode, w in (("ap", ap_w), ("rt", rt_w), ("mb", mb_w)):
    pk = page_keys(page_branch(mode))
    miss = ["%s=%s (page: %s)" % (k, v, pk.get(k)) for k, v in w.items() if pk.get(k) != v]
    check("%s: every literal the wizard writes, the page writes with the same value" % mode, not miss, miss)
check("aimesh: cfg_master 1 for ap/rt, 0 for mb (aimeshObj + the mode functions)",
      page_keys(page_branch("ap")).get("cfg_master") == "1" and page_keys(page_branch("rt")).get("cfg_master") == "1"
      and page_keys(page_branch("mb")).get("cfg_master") == "0"
      and 'qisPostData.cfg_master = "0"' in mb_body and 'qisPostData.cfg_master = "1"' in fn_body(handler, "goTo.apMode"))
rt_adv = fn_body(handler, "goTo.rtMode").split("if(systemVariable.advSetting", 1)[-1]
check("rt: the advSetting branch's LAN reset (static, lan_ipaddr_rt / lan_netmask_rt, DNS cleared)",
      all(s in rt_adv for s in ('qisPostData.lan_proto = "static"', "lan_ipaddr_rt", 'qisPostData.lan_dns1_x = ""'))
      and all(s in page_branch("rt") for s in ("d.lan_proto='static'", "d.lan_ipaddr=NV.lan_ipaddr_rt",
                                               "d.lan_netmask=NV.lan_netmask_rt", "d.lan_dns1_x=''")))
dhcp = fn_body(handler, "goTo.lanDHCP")
static = fn_body(handler, "apply.lanStatic")
check("lan: dhcp writes lan_proto=dhcp + lan_dnsenable_x=1 like lanDHCP",
      'qisPostData.lan_proto = "dhcp"' in dhcp and 'qisPostData.lan_dnsenable_x = "1"' in dhcp
      and "d.lan_proto='dhcp'; d.lan_dnsenable_x='1';" in pd)
check("lan: static writes the five fields + lan_dnsenable_x=0 like apply.lanStatic",
      'qisPostData.lan_dnsenable_x = "0"' in static
      and all(("d.%s=" % k) in pd for k in ("lan_ipaddr", "lan_netmask", "lan_gateway", "lan_dns1_x", "lan_dns2_x"))
      and "d.lan_dnsenable_x='0'" in pd)
gen = re.search(r"var generalObj = \{(.*?)\}", qisdata, re.S)
gk = dict(re.findall(r'"(\w+)":\s*"([^"]*)"', gen.group(1))) if gen else {}
check("mb: generalObj (x_Setting / w_Setting / qis_Setting) as the MB apply inserts it",
      gk and all(page_keys(page_branch("mb")).get(k) == v for k, v in gk.items()), gk)
check("mb: transformWLCObj folds wlcN_* into wlc_* - the page posts wlc_band/ssid/auth_mode/crypto/wpa_psk/ap_mac",
      "key.replace(\"wlc\" + wlcUnit, \"wlc\")" in plugins
      and all(("d.%s=" % k) in pd or ("d.%s =" % k) in pd for k in
              ("wlc_band", "wlc_ssid", "wlc_auth_mode", "wlc_crypto", "wlc_wpa_psk", "wlc_ap_mac", "wlc_wep")))

# -- MLO + service ----------------------------------------------------------------------------
mld = re.search(r"function handle_mld_enable\(mode\) \{(.*?)\n\}\n", plugins, re.S)
mld = mld.group(1) if mld else ""
check("mld: RT/AP take the default on a mode change, RP/MB force 0 (handle_mld_enable)",
      'nvramDefaultGet(["mld_enable"])' in mld and 'qisPostData.mld_enable = "0"' in mld
      and "if (MODE === 'mb') return '0';" in page and "return NV.mld_default || '0';" in page
      and "if (m !== null && CUR !== MODE) d.mld_enable = m;" in pd)
grs = re.search(r"var getRestartService = function\(\)\{(.*?)\n\};?\n", plugins, re.S)
grs = grs.group(1) if grs else ""
check("service: restart_all for a change to Router, reboot otherwise (getRestartService)",
      re.search(r'isSwModeChanged\(\) && isSwMode\("RT"\)\)\{\s*return "restart_all";', grs) is not None
      and "rc_service:(MODE === 'rt') ? 'restart_all' : 'reboot'" in pd)

# -- the parent's security -> auth modes setupWLCNvram uses ---------------------------------------
sw = re.search(r"function setupWLCNvram\(apProfileID\) \{(.*?)\n\}\n", plugins, re.S)
sw = sw.group(1) if sw else ""
stock_auth = set(re.findall(r'_auth_mode"\] = "(\w+)"', sw))
page_auth = set(re.findall(r"auth:'(\w+)'", page))
check("security: every auth mode the page posts is one setupWLCNvram() posts",
      page_auth and page_auth <= stock_auth, (sorted(page_auth), sorted(stock_auth)))
check("security: WPA2/WPA3 -> psk2sae, WPA3 -> sae, WPA/WPA2 -> pskpsk2, Open -> open, OWE -> owe",
      all(a in page_auth for a in ("psk2sae", "sae", "pskpsk2", "psk2", "open", "owe")))

# -- the ways in ------------------------------------------------------------------------------------
def chooser_bad(txt):
    code = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    bad = [f for f in set(re.findall(r"QIS_wizard\.htm\?flag=(\w+)", code))
           if f not in ("amasnode_page", "sitesurvey_rep", "sitesurvey_exp2", "sitesurvey_exp5")]
    bad += ["no mode=%s" % m for m in ("ap", "mb", "rt") if "/Reaper_ModeSetup.asp?mode=%s'" % m not in code]
    return bad
om = rd(os.path.join(W, "Advanced_OperationMode_Content.asp"))
check("chooser: ap / mb / rt go to the page; the wizard only for Repeater and AiMesh Node",
      not chooser_bad(om), chooser_bad(om))
mlo = rd(os.path.join(W, "sysdep", "FUNCTION", "SDN", "SDN", "mlo.js"))
check("mlo: Get started goes to the Wireless console, not the wizard",
      "QIS_wizard.htm" not in re.sub(r"/\*.*?\*/", "", mlo, flags=re.S)
      and '"/reaper_shell.asp#Reaper_WiFiSettings.asp"' in mlo)
inj_p = os.path.join(SRC, "httpd", "reaper_inject.c")
if os.path.isfile(inj_p):
    inj = rd(inj_p)
    sk = re.search(r"static const char \*reaper_skip\[\] = \{(.*?)\n\};", inj, re.S)
    check("inject: the page is in reaper_skip[] (own theme, never bounced into the shell)",
          sk is not None and '"Reaper_ModeSetup.asp",' in sk.group(1))
lc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reaper_langcheck.py")
if os.path.isfile(lc):
    check("langcheck: the page is in OUR[]", "'Reaper_ModeSetup.asp'" in rd(lc))

# -- i18n ---------------------------------------------------------------------------------------------
packs = sorted(p for p in glob.glob(os.path.join(W, "*.dict")) if os.path.basename(p) != "temp.dict")
used = set(re.findall(r"<#([A-Za-z0-9_]+)#>", page))
missing = []
for p in packs:
    keys = dict(l.split("=", 1) for l in rd(p).splitlines() if "=" in l)
    missing += ["%s:%s" % (os.path.basename(p), k) for k in sorted(used) if not keys.get(k)]
    missing += ["%s:RMOD_%d" % (os.path.basename(p), i) for i in range(1, 86) if not keys.get("RMOD_%d" % i)]
check("i18n: 25 packs, RMOD_1..85 + every token on the page non-empty in each", len(packs) == 25 and not missing,
      missing[:8])
check("i18n: no token inside a single-quoted string (rule 29)",
      not re.search(r"'[^'\n`]*<#[A-Za-z0-9_]+#>[^'\n`]*'", page))
check("page: ASCII only (rule 1)", all(ord(c) < 128 for c in page))

# -- self-test ------------------------------------------------------------------------------------------
old = om.replace("/Reaper_ModeSetup.asp?mode=ap'", "/QIS_wizard.htm?flag=lanip'")
check("self-test: the pre-rung chooser line fails the chooser rule", bool(chooser_bad(old)))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
