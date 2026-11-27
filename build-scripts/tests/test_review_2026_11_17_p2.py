#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review 2026-11-17, remediation phase 2 (image space): pins for each removal as it lands.

WHY THIS EXISTS. The root filesystem sits about 2.2 MB under its flash slot. The review listed files that ship and
that nothing can reach or load. A removal is only safe while its reason holds, so each one is pinned together
with the condition it depends on - and with the files the review proposed that must NOT go:
  - libnss_mdns4_minimal.so.2: glibc loads it by the name in nsswitch.conf ("hosts: files mdns4_minimal ...");
  - lib64/libnss_files.so.2: the 64-bit ebtables resolves protocol names through it.
(libsmbclient.so.0.7.0 was on that list while it shared its soname with the library the portal web server links;
since 2026-11-19 that soname is the portal's stand-in, router/libsmbclient-stub, and 0.7.0 goes - REAPER-SMBSTUB,
pinned in full by test_portal_smb_stub.py; here only while the router Makefile installs the stand-in.)

WHAT IT DOES. Reads www/Makefile, the router Makefile, httpd/reaper_inject.c, www/reaper/menu.js, targets/buildFS and the name-service
configuration of the tree. Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, sys


def skip(msg):
    print("SKIP: " + msg); sys.exit(77)


SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Makefile")):
    skip("no router source tree with www/Makefile (argv[1] or REAPER_ROUTER_SRC)")
PLAT = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916"))
fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))


def rd(path):
    return open(path, encoding="utf-8", errors="surrogateescape").read()


mk = rd(os.path.join(SRC, "www", "Makefile"))
inj = rd(os.path.join(SRC, "httpd", "reaper_inject.c"))
menu = rd(os.path.join(SRC, "www", "reaper", "menu.js"))

# ---------------------------------------------------------------- the stock portal editors and the old guest page
i = mk.find("REAPER-UNSHIP-CP")
j = mk.find("REAPER-UNSHIP-WL")
blk = mk[i:j] if 0 < i < j else ""
check("www: the removal block for the stock portal editors is present", bool(blk))
m = re.search(r"\nifeq \(\$\(RTCONFIG_MULTILAN_CFG\), y\)\n(.*?)\nifneq \(\$\(RTCONFIG_CP_ADVANCED\), y\)\n(.*?)\nendif\nendif\n", blk, re.S)
check("www: removed only on a model with the Network page; the Advanced editor only where its build flag is off",
      m is not None, blk[-900:])
if m:
    outer, inner = m.group(1), m.group(2)
    names = lambda t: sorted(re.findall(r"\$\(INSTALLDIR\)/www/(\S+)", t))
    check("www: the Free WiFi editor set and the old Guest Network page go with the Network page",
          names(outer) == sorted(["Captive_Portal.asp", "Captive_Portal.css", "Captive_Portal_Preview.asp",
                                  "Captive_Portal_template.js", "Guest_network.asp", "Guest_network.css"]), names(outer))
    check("www: the Advanced editor set, the two helper pages only the editors call, and its colour picker",
          names(inner) == sorted(["Captive_Portal_Advanced.asp", "Captive_Portal_Advanced.css",
                                  "Captive_Portal_Advanced_Preview.asp", "Captive_Portal_Advanced_template.js",
                                  "ajax_captive_portal.asp", "ajax_captive_portal_log.asp", "jscolor"]), names(inner))
check("www: the Guest Portal that IS offered keeps its templates (nothing under SDN/ is named in the block)",
      "www/SDN" not in blk)
# 2026-11-25 (native-UI cutover stage 1): the menu rows are gone as well - they needed a build WITHOUT the Network page,
# and rc adds mtlancfg on every MULTILAN_CFG build (lean test_cutover_stage1.py holds the proof)
check("menu: the two editors' rows are gone (no supported build could show them)",
      "Captive_Portal.asp" not in menu and "Captive_Portal_Advanced.asp" not in menu)
check("menu: the guest tab is the Network page",
      "T('Reaper_Network.asp', sup('sdn_mwl')" in menu and "Guest_network.asp" not in menu)
g = re.search(r"#ifdef RTCONFIG_MULTILAN_CFG\n(?:(?!#endif).)*?REAPER-GONE-CP.*?\n#endif\n#endif\n", inj, re.S)
check("httpd: the old addresses bounce to the Network page, under the same build conditions",
      g is not None and '{ "captive_portal.asp", "Reaper_Network.asp", 0 },' in g.group(0)
      and '{ "guest_network.asp", "Reaper_Network.asp", 0 },' in g.group(0)
      # v3.8.4 (REAPER-GONE-V384): the Advanced preview and the two portal data pages follow the editor's row
      and re.search(r'#ifndef RTCONFIG_CP_ADVANCED\n\t\{ "captive_portal_advanced\.asp", "Reaper_Network\.asp", 0 \},\n'
                    r'(?:\t\{ "[a-z_]+\.asp", "Reaper_Network\.asp", 0 \},[^\n]*\n)*#endif', g.group(0)) is not None)

# ---------------------------------------------------------------- three pages that only bounced
k = mk.find("\n", mk.find("jquery-ui.css stay", j)) if j > 0 else -1
wl = ""
for line in (mk[k + 1:].split("\n") if k > 0 else []):      # the recipe lines that follow the comment, and no further
    if not line.startswith("\trm "):
        break
    wl += line + "\n"
wn = sorted(re.findall(r"\$\(INSTALLDIR\)/www/(\S+)", wl))
check("www: the three superseded pages, the schedule script, its style sheet and the tutorial images are removed",
      wn == sorted(["Advanced_Wireless_Content.asp", "Advanced_WAdvanced_Content.asp", "Advanced_SwitchCtrl_Content.asp",
                    "js/weekSchedule/weekSchedule.js", "js/weekSchedule/weekSchedule.css",
                    "images/New_ui/weekSchedule/tutorial_guide"]), wn)
check("www: that block is outside every condition (the pages are superseded on every model)",
      j > 0 and mk[:j].count("\nifeq") + mk[:j].count("\nifneq") + mk[:j].count("\nifdef") + mk[:j].count("\nifndef")
      == mk[:j].count("\nendif"))
check("www: the removal comes after the stock line that copies a schedule variant of the page into place",
      0 < mk.find("WL_SCHED_V1/Advanced_WAdvanced_Content.asp $(INSTALLDIR)/www/Advanced_WAdvanced_Content.asp") < j)
for n, to in (("advanced_switchctrl_content.asp", "Reaper_LAN.asp?tab=switch"),
              ("advanced_wireless_content.asp", "Reaper_WiFiSettings.asp"),
              ("advanced_wadvanced_content.asp", "Reaper_WiFiSettings.asp")):
    check("httpd: %s is answered as a page that no longer ships" % n, ('{ "%s", "%s", 0 },' % (n, to)) in inj)
for keep in ("schedule_ui.js", "schedule_ui.css", "jquery-ui.css"):
    check("www: js/weekSchedule/%s is not removed (the Network page and the LED schedule load it)" % keep,
          ("weekSchedule/" + keep) not in mk)

# ---------------------------------------------------------------- libraries nothing loads
bf = os.path.join(PLAT, "targets", "buildFS")
if os.path.isfile(bf):
    b = rd(bf)
    i = b.find("REAPER-RM-LIBS-1117")
    blk = b[i:b.find("\n# sample configs", i)] if i > 0 else ""
    code = "\n".join(l for l in blk.split("\n")[1:] if not l.startswith("#"))
    libs = re.findall(r"(?:^|\s)((?:usr/)?lib/\S+\.so[\w.]*|lib\S+samba4\.so[\w.]*)", code)
    want = ["lib/libnl-route-3.so.200.20.0", "lib/libnl-nf-3.so.200.20.0", "usr/lib/libdcerpc.so.0.0.1",
            "usr/lib/libyaml-0.so.2.0.5", "usr/lib/libev.so.4.0.0", "usr/lib/libnetfilter_queue.so.1",
            "usr/lib/libpcreposix.so.0.0.1", "usr/lib/libnetsnmphelpers.so.40.2.1", "usr/lib/libiptc.so",
            "libsmbclient-raw-samba4.so", "libhdb-samba4.so.11.0.2", "libdcerpc-samba4.so", "libgpo-samba4.so",
            "libhttp-samba4.so", "libLIBWBCLIENT-OLD-samba4.so", "libauth-unix-token-samba4.so",
            "usr/lib/libsmbclient.so.0.7.0"]
    check("image: the seventeen unneeded libraries go through reaper_rm_lib (it clears the links they leave)",
          sorted(libs) == sorted(want) and code.count("reaper_rm_lib") == 3, sorted(libs))
    rmk = rd(os.path.join(SRC, "Makefile")) if os.path.isfile(os.path.join(SRC, "Makefile")) else ""
    check("image: libsmbclient.so.0.7.0 goes only while the portal server's libsmbclient.so.0 is the stand-in",
          "$(MAKE) -C libsmbclient-stub install INSTALLDIR=$(INSTALLDIR)/lighttpd-1.4.39" in rmk
          and "obj-$(RTCONFIG_CAPTIVE_PORTAL) += samba-3.5.8" not in rmk)
    check("image: the 64-bit DNS name-service file goes only while no 64-bit resolver library ships",
          "[ -e $R_FS/lib64/libresolv.so.2 ] || rm -f $R_FS/lib64/libnss_dns.so.2" in code)
    whole = "\n".join(l for l in b.split("\n") if not l.lstrip().startswith("#"))
    for keep, why in (("libnss_mdns4_minimal", "glibc loads it by the name in nsswitch.conf"),
                      ("libnss_files", "the 64-bit ebtables resolves protocol names through it"),
                      ("libbcmcrypto", "closed; not before a boot test")):
        check("image: %s is NOT removed (%s)" % (keep, why), keep not in whole)
    ns = [os.path.join(dp, n) for dp, dn, fn in os.walk(os.path.join(SRC, "others")) for n in fn if n == "nsswitch.conf"]
    ns += [p for p in (os.path.join(SRC, "rom", "rom", "etc", "nsswitch.conf"),) if os.path.isfile(p)]
    if ns:
        check("the name-service configuration still names mdns4_minimal (the reason that library stays)",
              any("mdns4_minimal" in rd(p) for p in ns), ns)

# ---------------------------------------------------------------- the two brand images every model shares
def webp(rel, maxb):
    p = os.path.join(SRC, "www", rel)
    if not os.path.isfile(p):
        return "missing"
    b = open(p, "rb").read()
    return "ok" if b[:4] == b"RIFF" and b[8:12] == b"WEBP" and len(b) <= maxb else "not a WebP of at most %d B (%d B)" % (maxb, len(b))


check("brand: the card backdrop ships as a WebP of at most 100 KB (was a 1.7 MB PNG)", webp("images/RLogo.webp", 100000) == "ok",
      webp("images/RLogo.webp", 100000))
check("brand: the Operation Mode picture ships as a WebP of at most 100 KB (was a 494 KB PNG)",
      webp("images/New_ui/rt_reaper.webp", 100000) == "ok", webp("images/New_ui/rt_reaper.webp", 100000))
check("brand: the two PNG files are gone from the tree",
      not os.path.exists(os.path.join(SRC, "www", "images", "RLogo.png"))
      and not os.path.exists(os.path.join(SRC, "www", "images", "New_ui", "rt_reaper.png")))
css1, css2 = rd(os.path.join(SRC, "www", "reaper", "reaper_content.css")), rd(os.path.join(SRC, "www", "reaper", "reaper_content_aimesh.css"))
opm = rd(os.path.join(SRC, "www", "Advanced_OperationMode_Content.asp"))
check("brand: both style sheets and the Operation Mode page name the new files, nothing names the old ones",
      css1.count('url("/images/RLogo.webp")') == 1 and css2.count('url("/images/RLogo.webp")') == 1
      and "url(/images/New_ui/rt_reaper.webp)" in opm
      and not any(x in t for x in ("RLogo.png", "rt_reaper.png") for t in (css1, css2, opm)))
web = rd(os.path.join(SRC, "httpd", "web.c"))
check("httpd: .webp is a served type and is exempt from the sign-in check like the other images",
      '{ "**.webp", "image/webp", cache_object, NULL, do_file, NULL },' in web and '{ "**.webp", NULL },' in web)

# ---------------------------------------------------------------- portal photos and the phone-as-modem help
import base64, json
cpd = os.path.join(SRC, "www", "sysdep", "FUNCTION", "SDN", "SDN", "Captive_Portal")
for name, n, key, maxb in (("FreeWiFi_template.json", 14, "group", 1242397), ("MessageBoard_template.json", 11, "id", 700000)):
    pth = os.path.join(cpd, name)
    if not os.path.isfile(pth):
        check("portal: %s is in the tree" % name, False)
        continue
    raw = open(pth, "rb").read()
    try:
        d = json.loads(raw.decode("utf-8-sig"))
    except ValueError as e:
        d = None
        check("portal: %s is valid JSON" % name, False, e)
    if d is not None:
        ok = (isinstance(d, list) and len(d) == n and all(sorted(x.keys()) == sorted([key, "image"]) for x in d)
              and all(x["image"].startswith("data:image/jpeg;base64,")
                      and base64.b64decode(x["image"].split(",", 1)[1])[:2] == bytes([0xFF, 0xD8]) for x in d))
        check("portal: %s still holds its %d photos, each a JPEG under the same two keys, and is no larger than %d B"
              % (name, n, maxb), ok and len(raw) <= maxb and raw[:3] == bytes([0xEF, 0xBB, 0xBF]), "%d B" % len(raw))
i = mk.find("REAPER-UNSHIP-PAM")
pam = []
if i > 0:
    for line in mk[mk.find(chr(10), i) + 1:].split(chr(10)):      # comment lines, then the recipe lines, and no further
        if line.startswith("#"):
            continue
        if not line.startswith(chr(9) + "rm "):
            break
        pam += [w.split("/www/", 1)[1] for w in line.split() if "/www/" in w]
check("www: the phone-as-modem help (photos + fragment) is not shipped; nothing else is named in that block",
      sorted(pam) == ["images/phone_as_modem", "phone_as_modem_instructions.html"], pam)
check("the reason the help can go: every request for the stock Network Map is sent to the dashboard",
      '{ "index.asp", "Main_ReaperDash.asp", 0 }' in inj)     # REAPER-CUT8: index.asp no longer ships; its address -> dashboard

print()
if fails:
    print("%d check(s) FAILED:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
