#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hostapd sends no AUTHORIZED update back for a disconnect the driver reported (2026-10-15).

WHY THIS EXISTS. The kernel log carried, in pairs,
    CFG80211-ERROR) wl_cfg80211_change_station :
    WLC_SCB_DEAUTHORIZE error (-30)
right after hostapd logged a client as disassociated. -30 is BCME_NOTFOUND (bcmutils.h): hostapd
(nl80211 SET_STATION, AUTHORIZED cleared) asked the driver to de-authorize a client the driver had
already removed. The path is hostapd_notif_disassoc() (src/ap/drv_callbacks.c - driver DISASSOC
and DEAUTH events both land there), which pushes the flags, then ap_free_sta()
(src/ap/sta_info.c), which pushes them again "just in case". Broadcom's own patch already marks
this case (WLAN_STA_DRIVER_IND) and skips the station REMOVE for it in ap_free_sta(): "Do not send
deauth/disassoc notification back to driver, if it is due to driver deauth/disassoc event." The
AUTHORIZED push was left out of that rule. It showed most when the router itself disconnected a
client (a Roaming Assistant kick in the log just before it, for example).

THE FIX (open hostapd, impl103 router_tools). Under
CONFIG_DRIVER_BRCM: hostapd_notif_disassoc() no longer pushes the flags (a debug line says so),
and ap_free_sta() skips its push when WLAN_STA_DRIVER_IND is set, exactly as it already skips
the remove. hostapd's own state is cleared as before; every hostapd-initiated path
(ap_sta_disassociate, ap_sta_deauthenticate, ap_handle_timer, ap_sta_disconnect) still pushes.

WHAT IT DOES. Runs the C preprocessor over the two real functions with and without
-DCONFIG_DRIVER_BRCM and checks where hostapd_set_sta_flags() survives; checks the
hostapd-initiated paths are untouched and that the build enables CONFIG_DRIVER_BRCM. A negative
self-test puts the stock function bodies back and expects the BRCM checks to fail.

Exit 0 pass, 1 fail, 77 skipped (no tree: release/src/router as argv[1] or REAPER_ROUTER_SRC;
hostapd is found at ../../src-rt-5.04behnd.4916/bcmdrivers/.../router_tools/hostapd)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
H = os.path.normpath(os.path.join(SRC, "..", "..", "src-rt-5.04behnd.4916", "bcmdrivers", "broadcom", "net",
                                  "wl", "impl103", "main", "components", "opensource", "router_tools",
                                  "hostapd")) if SRC else ""
DRV = os.path.join(H, "src", "ap", "drv_callbacks.c")
STA = os.path.join(H, "src", "ap", "sta_info.c")
if not H or not os.path.isfile(DRV) or not os.path.isfile(STA):
    skip("no hostapd tree (argv[1] = release/src/router, or REAPER_ROUTER_SRC)")
cpp = shutil.which("cpp") or shutil.which("gcc")
if not cpp:
    skip("no host C preprocessor")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

def func(text, sig):
    # the signature may wrap onto a second line before the opening brace
    m = re.search(r"\n" + re.escape(sig) + r"[^\n]*\n(?:[^\n{]*\n)?\{\n.*?\n\}\n", text, re.S)
    return m.group(0) if m else ""

def pp(body, brcm):
    """preprocess one function body: only its own #ifdefs matter here"""
    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
        f.write(body); p = f.name
    try:
        args = [cpp] + (["-E"] if os.path.basename(cpp).startswith("gcc") else []) + ["-P"]
        if brcm:
            args.append("-DCONFIG_DRIVER_BRCM")
        r = subprocess.run(args + [p], capture_output=True, text=True)
        return re.sub(r"\s+", " ", r.stdout)
    finally:
        os.unlink(p)

def notif_ok(body):
    """BRCM: no flag push; non-BRCM: the stock push is still there"""
    b, n = pp(body, True), pp(body, False)
    return ("WLAN_STA_DRIVER_IND" in b and "hostapd_set_sta_flags" not in b
            and "hostapd_set_sta_flags(hapd, sta);" in n and "ap_free_sta(hapd, sta);" in b)

def free_ok(body):
    """BRCM: the push in ap_free_sta() sits behind the DRIVER_IND test; non-BRCM: unconditional"""
    b, n = pp(body, True), pp(body, False)
    return (re.search(r"ap_sta_set_authorized\(hapd, sta, 0\); if \(!\(sta->flags & WLAN_STA_DRIVER_IND\)\) "
                      r"hostapd_set_sta_flags\(hapd, sta\);", b) is not None
            and re.search(r"ap_sta_set_authorized\(hapd, sta, 0\); hostapd_set_sta_flags\(hapd, sta\);", n)
            is not None)

drv = open(DRV, encoding="utf-8", errors="replace").read()
sta = open(STA, encoding="utf-8", errors="replace").read()
notif = func(drv, "void hostapd_notif_disassoc(struct hostapd_data *hapd, const u8 *addr)")
free = func(sta, "void ap_free_sta(struct hostapd_data *hapd, struct sta_info *sta)")
check("hostapd_notif_disassoc() found", bool(notif))
check("ap_free_sta() found", bool(free))
check("hostapd_notif_disassoc(): no AUTHORIZED push for a driver-reported disconnect (BRCM), stock otherwise",
      notif_ok(notif), pp(notif, True)[-400:])
check("hostapd_notif_disassoc(): says so in the debug log",
      'reaper: driver-indicated disconnect of " MACSTR' in notif)
check("ap_free_sta(): the push is skipped when WLAN_STA_DRIVER_IND is set (BRCM), stock otherwise",
      free_ok(free))
check("ap_free_sta(): Broadcom's own remove skip is still there",
      "if (!(sta->flags & WLAN_STA_DRIVER_IND)) {" in free and "hostapd_drv_sta_remove(hapd, sta->addr);" in free)
check("WLAN_STA_DRIVER_IND is set only by the driver-event handler",
      len(re.findall(r"flags \|= WLAN_STA_DRIVER_IND", drv + sta)) == 1)

# third push (metal, _r3 still logged -30): hostapd_notif_disassoc() hands WPA_DISASSOC to the
# authenticator, whose WPA_PTK INITIALIZE (PSK/SAE/OWE) clears WPA_EAPOL_authorized ->
# ieee802_1x_set_sta_authorized(.., 0) -> hostapd_set_authorized() -> SET_STATION.
X1 = os.path.join(H, "src", "ap", "ieee802_1x.c")
WA = os.path.join(H, "src", "ap", "wpa_auth.c")
x1 = open(X1, encoding="utf-8", errors="replace").read() if os.path.isfile(X1) else ""
wa = open(WA, encoding="utf-8", errors="replace").read() if os.path.isfile(WA) else ""
setauth = func(x1, "void ieee802_1x_set_sta_authorized(struct hostapd_data *hapd,")
def setauth_ok(body):
    """BRCM: the unauthorize push sits behind DRIVER_IND; the authorize push and non-BRCM: stock"""
    b, n = pp(body, True), pp(body, False)
    return (re.search(r"ap_sta_set_authorized\(hapd, sta, 0\); if \(sta->flags & WLAN_STA_DRIVER_IND\) res = 0; "
                      r"else res = hostapd_set_authorized\(hapd, sta, 0\);", b) is not None
            and "res = hostapd_set_authorized(hapd, sta, 1);" in b
            and re.search(r"ap_sta_set_authorized\(hapd, sta, 0\); res = hostapd_set_authorized\(hapd, sta, 0\);", n)
            is not None)
check("premise: WPA_PTK INITIALIZE unauthorizes the port (the third push)",
      re.search(r"SM_STATE\(WPA_PTK, INITIALIZE\).*?WPA_EAPOL_authorized, 0\);.*?\n\}", wa, re.S) is not None)
check("premise: hostapd_notif_disassoc() sets WLAN_STA_DRIVER_IND before wpa_auth_sm_event()",
      0 <= notif.find("sta->flags |= WLAN_STA_DRIVER_IND;") < notif.find("wpa_auth_sm_event(sta->wpa_sm, WPA_DISASSOC);"))
check("ieee802_1x_set_sta_authorized() found", bool(setauth))
check("ieee802_1x_set_sta_authorized(): no unauthorize push for a driver-reported disconnect (BRCM), stock otherwise",
      setauth_ok(setauth), pp(setauth, True)[:400])

# every hostapd-initiated path keeps its push - those stations still exist in the firmware
for sig in ("void ap_sta_disassociate(", "void ap_sta_deauthenticate(", "void ap_handle_timer(",
            "void ap_sta_disconnect("):
    m = re.search(r"\n" + re.escape(sig) + r".*?\n\}\n", sta, re.S)
    body = m.group(0) if m else ""
    check("hostapd-initiated %s() still pushes the flags" % sig.split("(")[0].split()[-1],
          "hostapd_set_sta_flags(hapd, sta);" in body and "reaper" not in body)

cfg = os.path.join(H, "hostapd", ".config")
mk = os.path.join(H, "hostapd", "Makefile")
check("the build enables CONFIG_DRIVER_BRCM (hostapd/.config + Makefile -D)",
      os.path.isfile(cfg) and re.search(r"^CONFIG_DRIVER_BRCM=y$", open(cfg).read(), re.M) is not None
      and "-DCONFIG_DRIVER_BRCM" in open(mk).read())

# negative self-test: the stock bodies must fail the BRCM checks
stock_notif = re.sub(r"\t/\* reaper 2026-10-15:.*?#else\n\thostapd_set_sta_flags\(hapd, sta\);\n#endif /\* CONFIG_DRIVER_BRCM \*/",
                     "#endif /* CONFIG_DRIVER_BRCM */\n\thostapd_set_sta_flags(hapd, sta);", notif, flags=re.S)
stock_free = re.sub(r"#ifdef CONFIG_DRIVER_BRCM\n\t/\* reaper 2026-10-15:.*?#endif /\* CONFIG_DRIVER_BRCM \*/\n", "",
                    free, count=1, flags=re.S)
check("self-test: the stock hostapd_notif_disassoc() fails the check",
      stock_notif != notif and not notif_ok(stock_notif))
check("self-test: the stock ap_free_sta() fails the check", stock_free != free and not free_ok(stock_free))
stock_setauth = re.sub(r"#ifdef CONFIG_DRIVER_BRCM\n\t\t/\* reaper 2026-10-15:.*?#endif /\* CONFIG_DRIVER_BRCM \*/\n", "",
                       setauth, count=1, flags=re.S)
check("self-test: the stock ieee802_1x_set_sta_authorized() fails the check",
      stock_setauth != setauth and not setauth_ok(stock_setauth))

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
