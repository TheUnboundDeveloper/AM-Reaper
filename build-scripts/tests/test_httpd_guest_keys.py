#!/usr/bin/env python3
"""The per-network guest keys never leak into a new network, and the zone switch travels in the settings backup
(image 2, 2026-11-19).

WHY. Image 2 stores two Reaper keys per network under its apg index: apgN_rg_devs (the main-network devices its
guests may reach) and apgN_rg_mdns (device discovery). A new network takes the lowest free apg index, so a network
created after a delete would inherit the deleted network's choices - an opening nobody asked for. The Network page
clears both on delete (sdn.js); the app / Alexa / IFTTT create paths in httpd write only the stock apgN_ keys, so
they clear the two keys themselves. The global switch reaper_fw_zpol_guest ("Zone policies may open one-way paths
from the main network into isolated guest networks") belongs to the Firewall settings and travels in the settings
file with them.

WHAT IT DOES. Reads httpd/web.c, rc/init.c and shared/amas_apg_shared.h and checks:
- rcfg_flags carries { "fw", "reaper_fw_zpol_guest", 2 } (the fw section: imported with the zone lists, refused
  while a firewall change awaits confirmation, kept with them);
- reaper_apg_rg_clear() unsets both keys for an index > 0, is defined once under RTCONFIG_MULTILAN_CFG before its
  first use, and is called once - after the new network's sdn_rl record - in each of the three paths that create an
  apg network (create_alexa_ifttt_sdn_profile, create_sdn_profile, create_sdn_guest_profile); never in
  update_apgx_profile (an EXISTING app network keeps its choices) nor in create_sdn_mwl_profile (apm, a main network);
- neither key is in APGx_NVRAM_LIST / APXx_NVRAM_LIST (those lists drive the stock writers and AiMesh sync: the keys
  stay router-only);
- the Network page's light save "restart_reaper_guest;" is a guest-network service token in httpd's reaper_sdn_tok AND
  rc's twin reaper_sdn_list_has_svc (rc/sdn.c), so on an AiMesh router (cfg_server path) the router still runs it once;
- rc/init.c apgx_default[] (boot seed + restore-defaults unset of every apgN_ key) has rg_devs and rg_mdns with an
  empty default, and apmx_default[] does not.

Exit 0 pass, 1 fail, 77 skipped (no router source tree: argv[1] or REAPER_ROUTER_SRC = .../release/src/router).
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(os.path.join(SRC, p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

web, init, apg = rd("httpd/web.c"), rd("rc/init.c"), rd("shared/amas_apg_shared.h")

def body(src, header):
    """the text of the function whose definition starts with header, up to its closing brace at column 0"""
    i = src.find(header)
    if i < 0: return ""
    j = src.find("\n}\n", i)
    return src[i:j + 3] if j > 0 else ""

def guards_at(src, pos):
    """the #if stack in force at offset pos"""
    st = []
    for m in re.finditer(r"^[ \t]*#[ \t]*(if|ifdef|ifndef|else|elif|endif)\b(.*)$", src[:pos], re.M):
        k = m.group(1)
        if k.startswith("if"): st.append(m.group(0).strip())
        elif k == "endif" and st: st.pop()
    return st

# ---- the settings backup ----
t = web.find("rcfg_flags[] = {")
tbl = web[t:web.find("\n};\n", t)] if t >= 0 else ""
check("rcfg_flags: the zone switch is in the fw section, 0 / 1 (max 2)", '{ "fw",     "reaper_fw_zpol_guest", 2 },' in tbl, tbl[-300:])
check("rcfg_flags: listed once", web.count('"reaper_fw_zpol_guest"') == 1)

# ---- the create paths ----
helper = body(web, "static void reaper_apg_rg_clear(int apg_idx)")
check("reaper_apg_rg_clear: defined once, unsets both keys of a real index",
      web.count("static void reaper_apg_rg_clear(int apg_idx)") == 1 and "if (apg_idx <= 0)" in helper
      and 'snprintf(k, sizeof(k), "apg%d_rg_devs", apg_idx);\n\tnvram_unset(k);' in helper
      and 'snprintf(k, sizeof(k), "apg%d_rg_mdns", apg_idx);\n\tnvram_unset(k);' in helper and web.count("REAPER-RG-CLEAR") == 1, helper)
# 2026-11-19: the AP Isolation choice (apgN_ap_isolate_lan, read by rc/lan.c reaper_brport_wired_open) goes with them
check("reaper_apg_rg_clear: also unsets the AP Isolation choice apgN_ap_isolate_lan",
      re.search(r'snprintf\(k, sizeof\(k\), "apg%d_ap_isolate_lan", apg_idx\);[^\n]*\n\tnvram_unset\(k\);', helper) is not None, helper)
hpos =web.find("static void reaper_apg_rg_clear(int apg_idx)")
calls = [m.start() for m in re.finditer(r"\treaper_apg_rg_clear\(apg_idx\);", web)]
check("reaper_apg_rg_clear: three calls, all after the definition", len(calls) == 3 and all(c > hpos for c in calls), len(calls))
check("reaper_apg_rg_clear: defined and called under RTCONFIG_MULTILAN_CFG (one build flag for both)",
      any("RTCONFIG_MULTILAN_CFG" in g for g in guards_at(web, hpos)) and all(any("RTCONFIG_MULTILAN_CFG" in g for g in guards_at(web, c)) for c in calls))
for fn, hdr in (("create_alexa_ifttt_sdn_profile", "\ncreate_alexa_ifttt_sdn_profile(int from_app, char *ssid"),
                ("create_sdn_profile", "int create_sdn_profile(struct json_object *wgn_obj)\n{"),
                ("create_sdn_guest_profile", "int create_sdn_guest_profile(struct json_object *wl_obj)\n{")):
    b = body(web, hdr)
    k = b.find('nvram_set("sdn_rl", b);\n')
    check("%s: clears the two keys of its new apg index once, right after the sdn_rl record" % fn,
          b.count("reaper_apg_rg_clear(apg_idx);") == 1 and k > 0
          and b[k:].startswith('nvram_set("sdn_rl", b);\n\treaper_apg_rg_clear(apg_idx);'), b[k:k + 120] if k > 0 else fn)
for fn, hdr in (("update_apgx_profile", "update_apgx_profile(int from_app, char *apg_idx, int expiretime, int bss_enabled)\n{"),
                ("create_sdn_mwl_profile", "int create_sdn_mwl_profile(struct json_object *mwl_obj)\n{")):
    b = body(web, hdr)
    check("%s: does not clear (an existing network / a main network)" % fn, b and "reaper_apg_rg_clear" not in b, fn)

# ---- router-only keys ----
m = re.search(r"APGx_NVRAM_LIST\[\] = \{(.*?)\};", apg, re.S)
check("APGx_NVRAM_LIST (stock writers, AiMesh sync) does not carry the Reaper keys", m and "RG_" not in m.group(1).upper(), m and m.group(1)[:200])
m = re.search(r"APXx_NVRAM_LIST\[\] = \{(.*?)\};", web, re.S)
check("APXx_NVRAM_LIST does not carry them either", m and "RG_" not in m.group(1).upper())

# ---- the light save on an AiMesh router (cfg_server path) ----
# The Network page sends "restart_reaper_guest;" when only a network's chosen devices / discovery changed. On an AiMesh
# router apply_cgi hands the list to cfg_server; httpd records guest-network requests in RSDN_PENDING
# (reaper_sdn_pending, by reaper_sdn_tok) and reaper_sdn_settle applies one on the router when rc ran none - rc stamps
# that from its own twin list (rc/sdn.c reaper_sdn_list_has_svc). Both lists must hold the token, and the same set:
# httpd-only would make the settle run it a second time and log "saved but not applied".
sdn = rd("rc/sdn.c")
def toklist(src, fn):
    b = body(src, fn)
    m = re.search(r"static const char \*const tok\[\] = \{(.*?)\};", b, re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []
th = toklist(web, "static int reaper_sdn_tok(const char *t, size_t n)")
tr = toklist(sdn, "int reaper_sdn_list_has_svc(const char *list)")
check("httpd reaper_sdn_tok records restart_reaper_guest (the light save reaches the settle on an AiMesh router)",
      "restart_reaper_guest" in th and "restart_sdn" in th, th)
check("rc reaper_sdn_list_has_svc stamps it (no second run by the settle), and both lists are the same set",
      "restart_reaper_guest" in tr and sorted(th) == sorted(tr), (th, tr))
check("the recording is still done on the cfg_server path, right after the action_script is handed over",
      "reaper_sdn_pending(action_para);" in web)
check("no token holds a '+' or a space (the settle turns '+' into ' ' and a name ends at the first space)",
      all("+" not in t and " " not in t for t in th))
check("rc runs the token: the reaper_guest service exists in rc/services.c",
      'strcmp(script, "reaper_guest") == 0' in rd("rc/services.c"))

# ---- boot seed / restore-defaults ----
a = init.find("apgx_default[] = {")
apgx = init[a:init.find("};", a)] if a >= 0 else ""
b_ = init.find("apmx_default[] = {")
apmx = init[b_:init.find("};", b_)] if b_ >= 0 else ""
check("init.c apgx_default: rg_devs and rg_mdns rows with an empty default, once each",
      len(re.findall(r'\{\s*"rg_devs",\s*""\s*\}', apgx)) == 1 and len(re.findall(r'\{\s*"rg_mdns",\s*""\s*\}', apgx)) == 1, apgx[-400:])
check("init.c apgx_default: the rows sit before the NULL terminator", apgx.find('"rg_mdns"') < apgx.find("{   NULL,") if apgx else False)
check("init.c apmx_default (main networks) has no guest rows", apmx and "rg_devs" not in apmx and "rg_mdns" not in apmx)
check("init.c: the table still drives the boot seed and the restore-defaults unset",
      "for (p=&apgx_default[0]; p->key != NULL; p++)" in init and "for (apgx_default_p = &apgx_default[0]; apgx_default_p->key != NULL; apgx_default_p++)" in init)

if fails:
    print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
print("all checks passed: no new network inherits a deleted network's guest paths, and the zone switch travels with the firewall settings")
