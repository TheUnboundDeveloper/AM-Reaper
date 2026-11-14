#!/usr/bin/env python3
"""mDNS across networks (owner, 2026-11-14).

WHY. Devices on the main network could not find a TV, printer or AirPlay speaker on another network (an IoT or
Employee network, or a guest network the admin gave Access Intranet): avahi answered for the router on every LAN-side
bridge but never relayed between them. The owner asked for the reflector with three rules: the main network and every
network with Access Intranet on take part (those devices are main-network devices on another SSID); a network with
the Network page's "Set AP Isolated" on must never be joined to another one; isolated guest networks and Guest Portals
stay out. The 2026-11-11 review (Appendix A) also noted that avahi announced the router onto guest bridges.

HOW. avahi has no per-interface reflector option, so a Reaper patch adds `reflect-interfaces` (avahi-core/server.c
reflect_iface_ok, checked on the receiving AND the sending interface in all four reflect paths). rc/reaper_guest.c
reaper_mdns_ifaces() picks the bridges, rc/services.c writes them into avahi-daemon.conf (only with two or more), adds
the networks guest isolation closes to deny-interfaces, and restarts avahi after restart_sdn / sdn_del only when that
plan changed. Tweaks > Advanced tweaks has the switch (reaper_mdns_reflect, on by default; only "0" is off).

WHAT IT DOES. Compiles reaper_mdns_ifaces() (with rm_add and rg_access_on) and avahi's reflect_iface_ok() on the
host against small stand-ins and runs the owner's cases; pins the avahi patch, the rc wiring, the page, the default,
the settings-file row and the two dictionary keys in every pack. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no
router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router)."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_guest.c")):
    skip("no router tree with rc/reaper_guest.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:700] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

def cfunc(src, head):
    """the text of the C function whose definition starts with head, up to its closing brace at column 0"""
    i = src.find(head)
    if i < 0:
        return None
    j = src.find("\n}\n", i)
    return src[i:j + 3] if j > 0 else None

# ---------------------------------------------------------------- rc: which bridges
gsrc = read("rc/reaper_guest.c")
acc = cfunc(gsrc, "static int rg_access_on(")
add = cfunc(gsrc, "static void rm_add(")
ifs = cfunc(gsrc, "void reaper_mdns_ifaces(")
check("reaper_guest.c: rg_access_on, rm_add and reaper_mdns_ifaces are there", acc and add and ifs)

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <net/if.h>
static size_t t_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t k = l < n - 1 ? l : n - 1; memcpy(d, s, k); d[k] = 0; } return l; }
static size_t t_strlcat(char *d, const char *s, size_t n) { size_t l = strlen(d); return l < n ? l + t_strlcpy(d + l, s, n - l) : l + strlen(s); }
#define strlcpy t_strlcpy
#define strlcat t_strlcat
#define MTLAN_MAXINUM 8
#define MAX_NR_WL_IF 4
typedef struct { int idx; char br_ifname[IFNAMSIZ]; char ifname[IFNAMSIZ]; } SUBNET_T;
typedef struct { int sdn_idx, apg_idx, cp_idx; } SDNFT_T;
typedef struct { int enable; char name[64]; SUBNET_T nw_t; SDNFT_T sdn_t; } MTLAN_T;
typedef struct { int cp_type; } CP_TYPE_RL;
static MTLAN_T NETS[MTLAN_MAXINUM]; static int NN, ROUTING = 1, CPT[8];
static const char *NV[32][2]; static int NNV;
static void nv(const char *k, const char *v) { NV[NNV][0] = k; NV[NNV][1] = v; NNV++; }
static const char *nvram_safe_get(const char *k) { int i; for (i = 0; i < NNV; i++) if (!strcmp(NV[i][0], k)) return NV[i][1]; return ""; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int is_routing_enabled(void) { return ROUTING; }
#define INIT_MTLAN(sz) calloc(MTLAN_MAXINUM, (sz))
#define FREE_MTLAN(p) free(p)
static MTLAN_T *get_mtlan(MTLAN_T *p, size_t *sz) { memcpy(p, NETS, sizeof(MTLAN_T) * NN); *sz = NN; return p; }
static int get_cp_type_byidx(int idx, CP_TYPE_RL *c) { c->cp_type = CPT[idx]; return 1; }
static void net(int en, const char *name, int sdn, int nwidx, const char *br, const char *ifn, int apg, int cp)
{ MTLAN_T *m = &NETS[NN++]; m->enable = en; strlcpy(m->name, name, sizeof(m->name)); m->sdn_t.sdn_idx = sdn;
  m->nw_t.idx = nwidx; strlcpy(m->nw_t.br_ifname, br, IFNAMSIZ); strlcpy(m->nw_t.ifname, ifn, IFNAMSIZ);
  m->sdn_t.apg_idx = apg; m->sdn_t.cp_idx = cp; }
@@ACC@@
@@ADD@@
@@IFS@@
int main(int argc, char **argv)
{
	char d[256], r[256], w[384];
	int s = atoi(argv[1]);
	nv("lan_ifname", "br0");
	net(1, "MAINFH", 0, 1, "br0", "br0", 1, 0);			/* the Main Network */
	net(1, "MAINBH", 0, 1, "br0", "br0", 5, 0); nv("apg5_ap_isolate", "1");	/* AiMesh backhaul: never looked at */
	switch (s) {
	case 0: break;
	case 1: net(1, "IoT", 1, 2, "br53", "br53", 2, 0); nv("sdn_access_rl", "<1>0"); break;
	case 2: net(1, "IoT", 1, 2, "br53", "br53", 2, 0); net(1, "Guest", 2, 3, "br54", "br54", 3, 0); nv("sdn_access_rl", "<1>0"); break;
	case 3: net(1, "Guest", 2, 3, "br54", "br54", 3, 0); nv("sdn_access_rl", "<2>0"); nv("apg3_ap_isolate", "1"); break;
	case 4: net(1, "IoT", 1, 2, "br53", "br53", 2, 0); net(1, "Portal", 3, 4, "br55", "tun22", 4, 1); CPT[1] = 2;
		nv("sdn_access_rl", "<1>0<3>0"); break;
	case 5: net(1, "IoT", 1, 2, "br53", "br53", 2, 0); nv("sdn_access_rl", "<1>0"); nv("apm1_ap_isolate", "1"); break;
	case 6: net(1, "IoT", 1, 2, "br53", "br53", 2, 0); nv("sdn_access_rl", "<1>0"); nv("wl1_ap_isolate", "1"); break;
	case 7: ROUTING = 0; net(1, "Guest", 2, 3, "br54", "br54", 3, 0); break;
	case 8: net(1, "IoT", 1, 2, "br53", "br53", 2, 0); net(1, "Guest", 4, 0, "br0", "br0", 6, 0); nv("sdn_access_rl", "<1>0");
		nv("apg6_ap_isolate", "1"); break;
	case 9: net(1, "IoT", 1, 2, "br53", "br53", 2, 0); net(0, "Guest", 2, 3, "br54", "br54", 3, 0); nv("sdn_access_rl", "<1>0");
		nv("apg3_ap_isolate", "1"); break;
	case 10: net(1, "Guest", 2, 3, "br54", "br54", 3, 0); nv("sdn_access_rl", "<2>0"); break;
	case 11: net(1, "Kids", 1, 2, "br53", "br53", 2, 0); net(1, "IoT", 2, 2, "br53", "br53", 3, 0); nv("sdn_access_rl", "<1>0<2>0");
		nv("apg3_ap_isolate", "1"); break;
	}
	reaper_mdns_ifaces(d, sizeof(d), r, sizeof(r), w, sizeof(w));
	printf("deny=%s\nrefl=%s\nwhy=%s\n", d, r, w);
	return 0;
}
'''

AVH = r'''
#include <stdio.h>
#include <string.h>
#include <strings.h>
typedef struct AvahiStringList { struct AvahiStringList *next; size_t size; char text[16]; } AvahiStringList;
typedef struct { const char *name; } HW;
typedef struct { HW *hardware; } AvahiInterface;
typedef struct { struct { AvahiStringList *reflect_interfaces; } config; } AvahiServer;
@@FN@@
int main(void)
{
	HW h0 = { "br0" }, h1 = { "BR53" }, h2 = { "br54" }; AvahiInterface i0 = { &h0 }, i1 = { &h1 }, i2 = { &h2 };
	AvahiStringList b = { NULL, 4, "br53" }, a = { &b, 3, "br0" };
	AvahiServer s; s.config.reflect_interfaces = NULL;
	printf("%d%d%d", reflect_iface_ok(&s, &i0), reflect_iface_ok(&s, &i1), reflect_iface_ok(&s, &i2));
	s.config.reflect_interfaces = &a;
	printf(" %d%d%d\n", reflect_iface_ok(&s, &i0), reflect_iface_ok(&s, &i1), reflect_iface_ok(&s, &i2));
	return 0;
}
'''

asrc = read("avahi/avahi-core/server.c")
rok = cfunc(asrc, "static int reflect_iface_ok(")
check("avahi server.c: reflect_iface_ok is there", rok is not None)

with tempfile.TemporaryDirectory() as td:
    if acc and add and ifs:
        c, exe = os.path.join(td, "m.c"), os.path.join(td, "m")
        open(c, "w").write(HARNESS.replace("@@ACC@@", acc).replace("@@ADD@@", add).replace("@@IFS@@", ifs))
        rr = subprocess.run([CC, "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
        check("reaper_mdns_ifaces compiles on the host (-Wall -Werror)", rr.returncode == 0, rr.stderr)
        if rr.returncode == 0:
            def run(n):
                out = subprocess.run([exe, str(n)], capture_output=True, text=True).stdout
                return dict(l.split("=", 1) for l in out.strip().split("\n"))
            o = run(0)
            check("main network only: br0 is the one reflector bridge, nothing denied; the AiMesh backhaul is not looked at",
                  o == {"deny": "", "refl": "br0", "why": ""}, o)
            o = run(1)
            check("a network with Access Intranet on joins the main LAN", o["refl"] == "br0,br53" and o["deny"] == "", o)
            o = run(2)
            check("a guest network without intranet access: avahi denied on it, left out of the reflector",
                  o["refl"] == "br0,br53" and o["deny"] == "br54" and o["why"] == "br54 no intranet access", o)
            o = run(10)
            check("owner 2026-11-14: a guest network WITH Access Intranet on takes part (main-network devices on another SSID)",
                  o["refl"] == "br0,br54" and o["deny"] == "", o)
            o = run(3)
            check("Set AP Isolated on (apgN_ap_isolate): left out of the reflector, avahi still serves it",
                  o["refl"] == "br0" and o["deny"] == "" and o["why"] == "br54 AP isolated", o)
            o = run(4)
            check("a Guest Portal, even with Access Intranet on: its bridge and chilli interface denied, never reflected",
                  o["refl"] == "br0,br53" and o["deny"] == "br55,tun22" and o["why"] == "br55 Guest Portal", o)
            o = run(5)
            check("the Main Network's Set AP Isolated (apmN_ap_isolate): br0 is left out", o["refl"] == "br53" and "br0 AP isolated" in o["why"], o)
            o = run(6)
            check("a main radio's wlN_ap_isolate: br0 is left out", o["refl"] == "br53" and "br0 AP isolated" in o["why"], o)
            o = run(8)
            check("a network riding br0 with Set AP Isolated on takes br0 out", o["refl"] == "br53" and "br0 AP isolated" in o["why"], o)
            o = run(11)
            check("two networks on one bridge: one AP isolated takes the bridge out", o["refl"] == "br0" and o["why"] == "br53 AP isolated", o)
            o = run(9)
            check("a disabled network is not looked at", o["refl"] == "br0,br53" and o["why"] == "", o)
            o = run(7)
            check("outside routing modes: nothing", o == {"deny": "", "refl": "", "why": ""}, o)
    if rok:
        c, exe = os.path.join(td, "a.c"), os.path.join(td, "a")
        open(c, "w").write(AVH.replace("@@FN@@", rok))
        rr = subprocess.run([CC, "-Wall", "-Werror", "-o", exe, c], capture_output=True, text=True)
        check("reflect_iface_ok compiles on the host", rr.returncode == 0, rr.stderr)
        if rr.returncode == 0:
            out = subprocess.run([exe], capture_output=True, text=True).stdout.strip()
            check("reflect_iface_ok: no list = every interface (stock); a list = only those, names case-insensitive", out == "111 110", out)

# ---------------------------------------------------------------- avahi patch pins
for fn in ("static void reflect_response(", "static void reflect_query(", "static void reflect_probe(",
           "static void reflect_legacy_unicast_query_packet("):
    body = cfunc(asrc, fn) or ""
    check("avahi %s: the receiving and the sending interface are both checked" % fn.split()[2].split("(")[0],
          "!s->config.enable_reflector || !reflect_iface_ok(s, i)" in body and "reflect_iface_ok(s, j)" in body)
lb = cfunc(asrc, "static void reflect_legacy_unicast_query_packet(") or ""
check("avahi legacy unicast: refused before a reflect slot is taken",
      lb.find("reflect_iface_ok(s, i)") >= 0 and lb.find("reflect_iface_ok(s, i)") < lb.find("allocate_slot("))
check("avahi config: reflect_interfaces initialised, freed and deep-copied",
      "c->reflect_interfaces = NULL;" in asrc and "avahi_string_list_free(c->reflect_interfaces);" in asrc
      and "rifs = avahi_string_list_copy(c->reflect_interfaces)" in asrc and "ret->reflect_interfaces = rifs;" in asrc)
core = read("avahi/avahi-core/core.h")
check("avahi core.h: the field is the LAST member (nothing after it moves)",
      re.search(r"AvahiStringList \*reflect_interfaces;[^\n]*\n\} AvahiServerConfig;", core) is not None)
check("avahi-daemon: [reflector] reflect-interfaces is parsed", 'strcasecmp(p->key, "reflect-interfaces") == 0' in read("avahi/avahi-daemon/main.c"))

# ---------------------------------------------------------------- rc wiring
svc = read("rc/services.c")
gen = cfunc(svc, "int generate_mdns_config(void)") or ""
check("generate_mdns_config: [reflector] only when the plan says so, with reflect-ipv off and the chosen bridges",
      "if (rm_on) {" in gen and 'enable-reflector=yes' in gen and 'reflect-ipv=no' in gen and 'reflect-interfaces=%s' in gen)
check("generate_mdns_config: the networks guest isolation closes go on deny-interfaces", "if (*rm_deny)" in gen)
check("generate_mdns_config: the plan is logged when it changes (signature file)", "REAPER_MDNS_SIG" in gen and "logmessage(\"mdns\"" in gen)
plan = cfunc(svc, "static int reaper_mdns_plan(") or ""
check("reaper_mdns_plan: on unless reaper_mdns_reflect is \"0\", and only with two or more bridges",
      '!nvram_match("reaper_mdns_reflect", "0") && n >= 2' in plan)
fol = cfunc(svc, "void reaper_mdns_follow(void)") or ""
check("reaper_mdns_follow: only a running avahi, only a changed plan, stop+start directly (no notify_rc from inside rc)",
      'if (!pids("avahi-daemon"))' in fol and "if (!strcmp(old, sig))" in fol and "stop_mdns();" in fol
      and "start_mdns();" in fol and "notify_rc" not in fol)
check("restart_sdn and sdn_del: avahi follows the network set (RTCONFIG_MDNS builds)",
      svc.count("#if defined(RTCONFIG_MDNS)\n\t\tif (action & RC_SERVICE_START)\n\t\t\treaper_mdns_follow();") == 1
      and svc.count("#if defined(RTCONFIG_MDNS)\n\t\treaper_mdns_follow();") == 1)
rch = read("rc/rc.h")
check("rc.h: both prototypes", "extern void reaper_mdns_ifaces(char *deny, size_t dn, char *refl, size_t rn, char *why, size_t wn);" in rch
      and "extern void reaper_mdns_follow(void);" in rch)
for f, t in (("rc/reaper_guest.c", gsrc), ("rc/services.c", svc)):
    bad = [l for l in t.split("\n") if "mdns" in l.lower() and re.search(r"\*/[A-Za-z_]", l)]
    check(f + ": no '*/' followed by a name in the new comments", not bad, bad[:2])

# ---------------------------------------------------------------- setting, page, backup, dicts
check("defaults.c: reaper_mdns_reflect defaults to 1",
      '{ "reaper_mdns_reflect", "1", CKN_STR1, CKN_TYPE_DEFAULT, CKN_ACC_LEVEL_DEFAULT, CKN_ENC_DEFAULT, 0 },' in read("shared/defaults.c"))
check("web.c: the settings file carries it (misc)", '{ "misc",   "reaper_mdns_reflect", 2 },' in read("httpd/web.c"))
tw = read("www/Reaper_Tweaks.asp")
check("Tweaks: the switch, shown on unless \"0\", hidden outside routing modes, value kept there",
      'id="t_mdns_reflect"' in tw and "setChk('t_mdns_reflect', NV.reaper_mdns_reflect !== '0');" in tw
      and "if (!ROUTING) q('r_mdns_reflect').classList.add('off');" in tw
      and "c.reaper_mdns_reflect = ROUTING ? chk('t_mdns_reflect') : NV.reaper_mdns_reflect;" in tw)
check("Tweaks: a change restarts avahi; an empty value reads as the default on",
      "if (has('reaper_mdns_reflect')) S.push('restart_mdns');" in tw and "reaper_mdns_reflect: '1'}" in tw)
www = os.path.join(SRC, "www")
packs = sorted(f for f in os.listdir(www) if re.match(r"^[A-Z]{2}\.dict$", f))
miss, lens = [], set()
for f in packs:
    t = open(os.path.join(www, f), encoding="utf-8").read()
    lens.add(t.count("\n"))
    for k in ("RTWK_47", "RTWK_48"):
        mm = re.search(r"^%s=(.+)$" % k, t, re.M)
        if not mm or any(x in mm.group(1) for x in ('"', "`", "\\", "${", "</")):
            miss.append(f + ":" + k)
check("RTWK_47/48 in all %d packs, quote-safe, packs in lockstep" % len(packs), len(packs) == 25 and not miss and len(lens) == 1, (miss, lens))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
