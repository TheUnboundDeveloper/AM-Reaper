#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A leftover stock VPN list row does not switch a VPN client on or off (2026-11-10).

WHY THIS EXISTS. Field report: WireGuard client 5 (a Surfshark profile kept from the stock firmware, re-made by
hand) "lost its private key" at every reboot. The key was never erased. shared/vpn_utils.c vpnc_load_profile()
mirrors each vpnc_clientlist row's active flag into vpn_clientx_eas / wgcN_enable - right for stock VPN Fusion,
whose page owns the list, wrong on this build, whose pages write those settings directly. Merlin's
adjust_vpnc_config() drops the rows typed OpenVPN and WireGuard at boot but not the provider rows, and the
loader reads Surfshark as WireGuard and CyberGhost as OpenVPN: such a row switched its client off (or on)
again at every vpnc_init() - boot, a Guest Network Pro restart, an IPsec restart. The page never shows a stored
key, so a client that was off read as a lost key.

WHAT IT DOES. Compiles the gate out of the real source both ways, pins that both writes sit behind it and that
the reason (the provider rows survive the boot clean-up) still holds, and checks the VPN Client page now says
whether a key is saved, in all 25 packs.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: release/src/router as argv[1] or REAPER_ROUTER_SRC)."""
import glob, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
VU = os.path.join(SRC, "shared", "vpn_utils.c") if SRC else ""
if not VU or not os.path.isfile(VU):
    skip("no router source tree with shared/vpn_utils.c (argv[1] or REAPER_ROUTER_SRC)")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

vu = open(VU, encoding="utf-8", errors="surrogateescape").read()
mg = re.search(r"^static int vpnc_list_sets_enable\(void\)\n\{\n.*?^\}\n", vu, re.S | re.M)
check("the gate is a function the test can cut out", mg is not None)
cc = shutil.which("gcc") or shutil.which("cc")
if mg and cc:
    for define, want in (("-DRTCONFIG_VPN_FUSION_MERLIN", "0"), ("-UREAPER_NOTHING", "1")):
        with tempfile.TemporaryDirectory() as td:
            c = os.path.join(td, "g.c"); x = os.path.join(td, "g")
            open(c, "w").write("#include <stdio.h>\n" + mg.group(0) + 'int main(void){ printf("%d", vpnc_list_sets_enable()); return 0; }\n')
            r = subprocess.run([cc, "-Wall", "-Werror", define, "-o", x, c], capture_output=True, text=True)
            got = subprocess.run([x], capture_output=True, text=True).stdout if r.returncode == 0 else r.stderr
            check("gate compiled with %s returns %s" % (define, want), got == want, got)
elif mg:
    print("note no C compiler on the host - the gate is not compiled")
body = vu[vu.index("int vpnc_load_profile("):] if "int vpnc_load_profile(" in vu else ""
check("the OpenVPN / CyberGhost row writes vpn_clientx_eas only behind the gate",
      "list[cnt].config.ovpn.ovpn_idx = (int)strtol(server, NULL, 0);\n\t\t\t\tif (vpnc_list_sets_enable())\n\t\t\t\t\t_update_ovpn_client_enable(list[cnt].config.ovpn.ovpn_idx, list[cnt].active);\n\t\t\t}\n#endif\n#ifdef RTCONFIG_WIREGUARD" in body)
check("the WireGuard / Surfshark row writes wgcN_enable only behind the gate",
      'else if (!strcmp(proto, PROTO_WG) || !strcmp(proto, PROTO_SURFSHARK))' in body
      and 'WG_CLIENT_NVRAM_PREFIX, list[cnt].config.wg.wg_idx);\n\t\t\t\tif (vpnc_list_sets_enable())\n\t\t\t\t\tnvram_pf_set_int(prefix, "enable", list[cnt].active);\n\t\t\t}\n#endif\n#ifdef RTCONFIG_TPVPN' in body)
fm = os.path.join(SRC, "rc", "format.c")
if os.path.isfile(fm):
    f = open(fm, encoding="utf-8", errors="surrogateescape").read()
    check("the reason still holds: the boot clean-up drops only the rows typed OpenVPN or WireGuard",
          'if (!strcmp(proto, "OpenVPN") || !strcmp(proto,"WireGuard")) {' in f and "Surfshark" not in f and "CyberGhost" not in f)
cb = os.path.join(SRC, "config_base")
if os.path.isfile(cb):
    c = open(cb, encoding="utf-8", errors="replace").read()
    check("Surfshark and NordVPN stay out of the build (the closed provider code is not reachable)",
          "# RTCONFIG_SURFSHARK is not set" in c and "# RTCONFIG_NORDVPN is not set" in c)

# ---- the page says whether a key is saved
pg = open(os.path.join(SRC, "www", "Reaper_VPNClient.asp"), encoding="utf-8", errors="replace").read()
check("VPN Client: a state text beside the private key and the pre-shared key",
      '<span class="unit" id="wg_priv_st"></span>' in pg and '<span class="unit" id="wg_psk_st"></span>' in pg)
check("VPN Client: wgLoad fills both from priv_set / psk_set",
      "q('wg_priv_st').textContent = w.priv_set ? `<#RVCL_165#>` : `<#RVCL_166#>`;" in pg
      and "q('wg_psk_st').textContent = w.psk_set ? `<#RVCL_165#>` : `<#RVCL_166#>`;" in pg)
check("VPN Client: the stored key still never reaches the page", "priv: ''" in pg and "priv_set: '<% nvram_match(\"wgc5_priv\"" in pg)
def val(text, key):
    m = re.search(r"^%s=(.*)$" % key, text, re.M)
    return m.group(1).rstrip("\r") if m else None
packs = sorted(p for p in glob.glob(os.path.join(SRC, "www", "*.dict")) if os.path.basename(p) != "temp.dict")
texts = {os.path.basename(p)[:-5]: open(p, encoding="utf-8", errors="replace").read() for p in packs}
en = texts.get("EN", "")
check("EN: the two state texts", (val(en, "RVCL_165"), val(en, "RVCL_166")) == ("A key is saved (hidden).", "No key saved."), (val(en, "RVCL_165"), val(en, "RVCL_166")))
bad = {}
for l, t in texts.items():
    a, b = val(t, "RVCL_165"), val(t, "RVCL_166")
    if not a or not b or a == b: bad[l] = (a, b)
    elif l != "EN" and (a == val(en, "RVCL_165") or b == val(en, "RVCL_166")): bad[l] = ("still English", a, b)
check("25 packs carry both texts, translated", len(texts) == 25 and not bad, bad)

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  " + f)
sys.exit(1 if fails else 0)
