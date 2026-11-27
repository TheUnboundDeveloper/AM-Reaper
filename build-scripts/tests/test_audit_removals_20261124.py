#!/usr/bin/env python3
"""Audit Findings remediation of 2026-11-24: what left the image, and the Encrypted DNS page note.

  REAPER-GONE-B6CD   twelve stock pages nothing reaches (audit B-6 groups C and D) are removed by www/Makefile;
                     each old .asp address has a reaper_pagemap[] row (a missing .asp bounces, it does not 404);
                     the two AiMesh node firmware pages are removed, and bounced, only where the option that
                     uses them is off (RT-BE88U keeps the revert page), with the SAME condition on both sides;
                     the two .htm files get no row (the bounce serves .asp names only).
  REAPER-UNUSED-B5   chilli_radconfig is removed from the image; nothing in rc or coova-chilli's programs runs it.
  RENC_112           the Encrypted DNS page says that devices on the router's VPN server are not served, in
                     every language pack (review 2026-11-11, C-8).
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import glob, os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree with httpd/reaper_inject.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))

def rd(*p):
    return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()

mk = rd("www", "Makefile"); inj = rd("httpd", "reaper_inject.c")

# ---------------------------------------------------------------- pages
PLAIN = ["cmdRet_check.htm", "detect_firmware.asp", "multi_vts_rule.asp", "result_of_get_changed_status_QIS.asp",
         "wds_aplist_5g_2.asp", "wlconn_apply.htm", "DDNS_info.asp", "SITE_info.asp", "Advanced_WProxy_Content.asp",
         "QoS_Stats.asp"]
COND = {"AiMesh_Node_RbkFirmware.asp": "RTCONFIG_ROLLBACKFW", "AiMesh_Node_RevertFirmware.asp": "RTCONFIG_REVERTFW"}
TARGET = {"detect_firmware.asp": "Reaper_Firmware.asp", "multi_vts_rule.asp": "Reaper_NAT.asp",
          "result_of_get_changed_status_QIS.asp": "Reaper_Internet.asp", "wds_aplist_5g_2.asp": "Reaper_WDS.asp",
          "DDNS_info.asp": "Reaper_DDNS.asp", "SITE_info.asp": "Reaper_Survey.asp",
          "Advanced_WProxy_Content.asp": "Reaper_ModeSetup.asp", "QoS_Stats.asp": "Reaper_QoS.asp",
          "AiMesh_Node_RbkFirmware.asp": "Reaper_Firmware.asp", "AiMesh_Node_RevertFirmware.asp": "Reaper_Firmware.asp"}

a = mk.find("REAPER-GONE-B6CD")
b = mk.find("\n# reaper", a + 1)
blk = mk[a:b + 1] if a >= 0 and b > a else ""
check("www/Makefile: the removal block is there, once", mk.count("REAPER-GONE-B6CD") == 1 and bool(blk))
for p in PLAIN:
    check("www/Makefile removes %s on every build" % p,
          "\trm -f $(INSTALLDIR)/www/%s\n" % p in blk and mk.count("rm -f $(INSTALLDIR)/www/%s\n" % p) == 1)
for p, opt in COND.items():
    check("www/Makefile removes %s only where %s is off" % (p, opt),
          "ifneq ($(%s),y)\n\trm -f $(INSTALLDIR)/www/%s\nendif\n" % (opt, p) in blk)
check("...and the conditional lines are balanced (two ifneq, two endif in the block)", blk.count("ifneq (") == 2 and blk.count("endif") == 2)

m = re.search(r"reaper_pagemap\[\]\s*=\s*\{(.*?)\n\};", inj, re.S)
tab = m.group(1) if m else ""
check("httpd: reaper_pagemap[] is found", bool(tab))
for p, tgt in TARGET.items():
    row = '\t{ "%s", "%s", 0 },\n' % (p.lower(), tgt)
    check("httpd: %s bounces to %s (one row, lower case)" % (p, tgt), tab.count(row) == 1 and tab.count('"%s"' % p.lower()) == 1)
    check("...and %s ships in www" % tgt, os.path.isfile(os.path.join(SRC, "www", tgt)))
for p, opt in COND.items():
    check("httpd: the %s row sits behind #ifndef %s, as its removal does" % (p, opt),
          '#ifndef %s\n\t{ "%s", "%s", 0 },\n#endif\n' % (opt, p.lower(), TARGET[p]) in tab)
for p in ("cmdRet_check.htm", "wlconn_apply.htm"):
    check("httpd: no row for %s (the bounce serves .asp names only)" % p, p.lower() not in tab.lower())
# nothing in the SHIPPED pages loads a removed page (the stock menu file lists two and drops both itself). The source
# www holds stock pages the Makefile never installs - a referrer that is itself removed does not count.
www = os.path.join(SRC, "www")
skip_dirs = ("sysdep", "menuTrees")
unshipped = set(re.findall(r"^\trm -r?f \$\(INSTALLDIR\)/www/(\S+)$", mk, re.M))
hits = {}
names = [p for p in PLAIN + list(COND)]
for root, dirs, files in os.walk(www):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        rel = os.path.relpath(os.path.join(root, f), www).replace(os.sep, "/")
        if not f.endswith((".asp", ".js", ".htm", ".html", ".json", ".css")) or f in names or rel in unshipped:
            continue
        try:
            t = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for p in names:
            if p in t:
                hits.setdefault(p, []).append(os.path.relpath(os.path.join(root, f), www))
allowed = {"Advanced_WProxy_Content.asp", "QoS_Stats.asp", "AiMesh_Node_RbkFirmware.asp", "AiMesh_Node_RevertFirmware.asp"}
bad = {p: v[:4] for p, v in hits.items() if p not in allowed}
check("no page or script in www names one of the eight plainly unreferenced pages", not bad, bad)
# the menu file every Reaper model installs is require/menuTrees/menuTree.js (the ROG / TUF / GS / UI4 variants are
# for builds no Reaper model makes; the ROG one lists QoS_Stats.asp with no exclude)
mtp = os.path.join(www, "require", "menuTrees", "menuTree.js")
mt = open(mtp, encoding="utf-8", errors="replace").read() if os.path.isfile(mtp) else ""
cfgp = os.path.join(SRC, ".config")
if os.path.isfile(cfgp):
    cf = open(cfgp, errors="replace").read()
    ui = [o for o in ("RTCONFIG_ROG_UI", "RTCONFIG_TUF_UI", "RTCONFIG_GS_UI", "RTCONFIG_UI4") if re.search(r"^%s=y$" % o, cf, re.M)]
    check("this tree builds the standard stock menu file (no ROG / TUF / GS / UI4 variant)", not ui, ui)
if mt:
    check("the stock menu file drops Advanced_WProxy_Content.asp unless the radio is Ralink / Realtek",
          re.search(r"if\(\(!Rawifi_support && ! ?Rtkwifi_support\) \|\| !concurrep_support \|\| !isSwMode\(\"RP\"\)\)\{\s*retArray\.push\(\"Advanced_WProxy_Content\.asp\"\);", mt) is not None)
    check("...and drops QoS_Stats.asp on Wi-Fi 7 models",
          re.search(r"if\(isSupport\(\"wifi7\"\)\)\{[^}]*retArray\.push\(\"QoS_Stats\.asp\"\);", mt) is not None)

# ---------------------------------------------------------------- the page hooks those pages were the only callers of
wc = rd("httpd", "web.c")
for hook, fn, page in (("ddns_info", "ej_ddnsinfo", "DDNS_info.asp"), ("dual_wanstate", "dual_wanstate_hook", "result_of_get_changed_status_QIS.asp"),
                       ("get_tcfilter_array", "ej_tcfilter_array", "QoS_Stats.asp"), ("wl_scan_5g_2", "ej_wl_scan_5g_2", "wds_aplist_5g_2.asp")):
    check("httpd: the %s hook went with %s (REAPER-UNUSED-B6CD)" % (hook, page),
          re.search(r'\{\s*"%s"\s*,' % re.escape(hook), wc) is None
          and '/* REAPER-UNUSED-B6CD: the %s hook is gone - its only page, %s, no longer ships */' % (hook, page) in wc)
for fn in ("ej_ddnsinfo", "dual_wanstate_hook"):
    check("httpd: %s() is gone with its hook (static, nothing else used it)" % fn,
          re.search(r"\b%s\s*\(int eid" % fn, wc) is None)
check("httpd: the sibling hook ajax_dualwanstate, which pages do call, is still there",
      '"ajax_dualwanstate"' in wc and "static int ajax_dualwanstate_hook(int eid, webs_t wp, int argc, char_t **argv){" in wc)

# ---------------------------------------------------------------- chilli_radconfig
bfs = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "targets", "buildFS"))
if os.path.isfile(bfs):
    bf = open(bfs, encoding="utf-8", errors="replace").read()
    check("buildFS removes chilli_radconfig (REAPER-UNUSED-B5), once", bf.count("rm -f $R_FS/usr/sbin/chilli_radconfig\n") == 1 and "REAPER-UNUSED-B5" in bf)
    check("...and still ships chilli itself and chilli_query", "usr/sbin/chilli " not in bf and "usr/sbin/chilli\n" not in bf and "chilli_query" not in bf)
else:
    print("note no targets/buildFS next to this tree - the chilli_radconfig line is not checked")
users = []
for f in glob.glob(os.path.join(SRC, "rc", "*.c")) + glob.glob(os.path.join(SRC, "httpd", "*.c")) + glob.glob(os.path.join(SRC, "shared", "*.c")):
    try:
        if "radconfig" in open(f, encoding="utf-8", errors="replace").read():
            users.append(os.path.relpath(f, SRC))
    except OSError:
        pass
check("nothing in rc, httpd or shared names chilli_radconfig", not users, users)
cs = [f for f in glob.glob(os.path.join(SRC, "coovachilli", "src", "*.c"))
      if os.path.basename(f) != "main-radconfig.c" and "chilli_radconfig" in open(f, encoding="utf-8", errors="replace").read()]
check("no other coova-chilli program runs it", not cs, [os.path.basename(f) for f in cs])

# ---------------------------------------------------------------- Encrypted DNS page note
pg = rd("www", "Reaper_EncryptedDNS.asp")
check("Encrypted DNS page: the VPN-server note follows the LAN-only note", "    <li><#RENC_43#></li>\n    <li><#RENC_112#></li>\n" in pg and pg.count("<#RENC_112#>") == 1)
packs = sorted(f for f in glob.glob(os.path.join(www, "*.dict")) if os.path.basename(f) != "temp.dict")
miss, same = [], []
en = None
for f in packs:
    mm = re.search(r"^RENC_112=(.+)$", open(f, encoding="utf-8").read(), re.M)
    if not mm or not mm.group(1).strip():
        miss.append(os.path.basename(f)); continue
    if os.path.basename(f) == "EN.dict":
        en = mm.group(1)
for f in packs:
    if os.path.basename(f) == "EN.dict":
        continue
    mm = re.search(r"^RENC_112=(.+)$", open(f, encoding="utf-8").read(), re.M)
    if mm and en and mm.group(1) == en:
        same.append(os.path.basename(f))
check("RENC_112 is in every language pack (%d)" % len(packs), len(packs) >= 25 and not miss, miss)
check("...translated in each (no pack carries the English text)", not same, same)
check("...and the English text says who is not served and why", bool(en) and "VPN server" in en and "not served" in en and "VPN tunnel" in en, en)

if fails:
    print("\n%d FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed: the twelve pages and chilli_radconfig are out, every old .asp address bounces, the page note is in every pack")
