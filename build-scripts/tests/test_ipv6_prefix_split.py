#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IPv6 for guest and VLAN networks from a /57 to /63 provider prefix, and new routers ask for a /56. 2026-11-19.

WHY THIS EXISTS. Each guest / VLAN network gets its IPv6 prefix by splitting the provider's delegated prefix
(shared/mtlan_utils.c mtlan_extend_prefix_by_subnet_idx). That split works on whole bytes only, so it gave a /64
from a /56 or larger and a /72 (no SLAAC) between /57 and /63; the callers therefore split only "<= 56 ||
ipv6_prefix_div" and every other network fell back to a private (ULA) prefix. Providers often hand out a /60.
The new mtlan_prefix_subnet64() puts the network's subnet index into bits plen..63 and returns a /64, refusing an
index that does not fit (idx >= 2^(64-plen)); the main LAN is index 0 and keeps the first /64 (no renumbering).
Order at the guest-network sites (rc/sdn.c per-network dnsmasq, rc/services.c set_ip6_sdnaddr): /56 and larger as
before; /57-/63 one /64 while the index fits, otherwise ULA even with ipv6_prefix_div (review 2026-11-19: the old
split's /72 would sit inside the main LAN's /64); /64 and longer: ipv6_prefix_div as before; else ULA, now logged
once per boot. With a /57-/63 the main LAN (rc/services.c main dnsmasq range and _add_ip6_lansdnaddr) keeps its stock
path: its address comes from ipv6_router_address() and is never rebuilt from the prefix (a Static IPv6 LAN address
is not overwritten). The old function is unchanged (pinned by hash).
New routers ask for a /56: shared/defaults.c ipv6_prefix_len_wan 64 -> 56 (factory reset / first boot only; a stored
value is kept). The key is also the Static IPv6 WAN address length (rc/wan.c), so the IPv6 page shows 64 when Static
is picked while the key still holds that native 56, and puts 56 back if Static is left with the field untouched.

WHAT IT CHECKS. Source pins; with gcc, the unchanged old function plus the REAPER-V6SPLIT block compiled on the host
and run for /48 /56 /57 /60 /62 /63 /64 (fits / does not fit / precedence with prefix_div); with node, the page's
staticFill() run against a stub DOM. Tree from argv[1] or REAPER_ROUTER_SRC. Exit 0 pass, 1 fail, 77 skip."""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile

SRC = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC")
       or os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router"))
P = {k: os.path.join(SRC, *v) for k, v in {
    "mc": ("shared", "mtlan_utils.c"), "mh": ("shared", "mtlan_utils.h"), "sdn": ("rc", "sdn.c"),
    "svc": ("rc", "services.c"), "def": ("shared", "defaults.c"), "pg": ("www", "Reaper_IPv6Setup.asp")}.items()}
if not all(os.path.isfile(p) for p in P.values()):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
rd = lambda p: open(p, encoding="utf-8", errors="surrogateescape").read()
S = {k: rd(p) for k, p in P.items()}
fails = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name); print("FAIL " + name + ((" :: " + str(detail)[:400]) if detail else ""))

mc, sdn, svc = S["mc"], S["sdn"], S["svc"]
# ---- shared/mtlan_utils.[ch]
OLD_SHA = "2941e86adb6e772106fb283924a420b82a924bb9a86d11f55ea6161d30261faf"
om = re.search(r"\nint mtlan_extend_prefix_by_subnet_idx\(.*?\n\}\n", mc, re.S)
check("the whole-byte split mtlan_extend_prefix_by_subnet_idx() is unchanged (hash of the 3.8.2 body)",
      om is not None and hashlib.sha256(om.group(0).encode()).hexdigest() == OLD_SHA)
bm = re.search(r"/\* REAPER-V6SPLIT-BEGIN \*/\n(.*?)/\* REAPER-V6SPLIT-END \*/", mc, re.S)
check("one REAPER-V6SPLIT block, right after the old function",
      bm is not None and mc.count("/* REAPER-V6SPLIT-BEGIN */") == 1 and om is not None and om.end() < bm.start() < om.end() + 4)
mh = S["mh"]
check("the six new functions are declared in mtlan_utils.h (shared library: both lines carry the same file)",
      all(x in mh for x in ("extern int mtlan_prefix_subnet64_fits(int prefix_length, int subnet_idx);",
                            "extern int mtlan_prefix_subnet64(const char *prefix, int prefix_length, int subnet_idx, char *buf, size_t len);",
                            "extern int mtlan_prefix_split_ok(int prefix_length, int subnet_idx, int prefix_div);",
                            "extern int mtlan_prefix_by_subnet(const char *prefix, int prefix_length, int subnet_idx, char *buf, size_t len);",
                            "extern int mtlan_prefix_same64(const char *a, const char *b);",
                            "extern int mtlan_prefix_split_ok_lan(const char *prefix, int prefix_length, int subnet_idx, int prefix_div, const char *lan_addr);")))

# ---- call sites (precedence)
check("the guest-network callers no longer use the old gate `<= 56 || v6_prefix_div` (only the main LAN's range keeps it)",
      "<= 56 || v6_prefix_div" not in sdn and svc.count("<= 56 || v6_prefix_div") == 1)
check("rc/sdn.c per-network dnsmasq: the new gate (main-LAN clash refused, br0's address from its stock path) and the new prefix call, ULA fallback kept",
      re.search(r"\t\tif \(share_subnet\) \{\n\t\t\tchar lan6\[INET6_ADDRSTRLEN\];[^\n]*REAPER-V6SPLIT-LANCLASH[^\n]*\n\n"
                r"\t\t\tstrlcpy\(lan6, ipv6_router_address\(NULL\), sizeof\(lan6\)\);\n"
                r"\t\t\tif \(mtlan_prefix_split_ok_lan\(v6_prefix, v6_prefix_length, pmtl->nw_t.idx, v6_prefix_div, lan6\)\) \{[^\n]*\n"
                r"\t\t\t\tsdn_prefix_length = mtlan_prefix_by_subnet\(\n\t\t\t\t\tv6_prefix, v6_prefix_length, pmtl->nw_t.idx, sdn_prefix, sizeof\(sdn_prefix\)\);\n"
                r"\t\t\t\tif \(sdn_prefix_length < 64\)\n\t\t\t\t\tsdn_prefix_length = 64;\n\t\t\t\}\n\t\t\telse \{\n"
                r"\t\t\t\tsdn_prefix_length = mtlan_extend_prefix_by_subnet_idx\(\n\t\t\t\t\tnvram_safe_get\(\"ipv6_ula_random\"\), 48, pmtl->nw_t.idx, 16,", sdn) is not None)
check("rc/services.c main dnsmasq range: with a /57-/63 the main LAN keeps its stock path (REAPER-V6SPLIT-MAIN)",
      svc.count("REAPER-V6SPLIT-MAIN") == 1
      and re.search(r"\t\t\tif \(v6_sdn_num && \(v6_prefix_length <= 56 \|\| v6_prefix_div\) && \(v6_prefix_length < 57 \|\| v6_prefix_length > 63\)\) \{\n"
                    r"\t\t\t\tsdn_prefix_length = mtlan_extend_prefix_by_subnet_idx\(\n\t\t\t\t\tv6_prefix, v6_prefix_length, 0, 8, sdn_prefix, sizeof\(sdn_prefix\)\);\n", svc) is not None)
s0 = svc.find("int set_ip6_sdnaddr(void)\n{"); s1 = svc.find("\n}\n", s0); sa = svc[s0:s1]
check("set_ip6_sdnaddr: the new gate (main-LAN clash refused; br0's address read once from ipv6_router_address()), "
      "both provider-prefix calls on the new order, ULA calls unchanged",
      "if (share_subnet && mtlan_prefix_split_ok_lan(v6_prefix[0] ? v6_prefix : ipv6_prefix_by_unit(NULL, wan6_unit),\n"
      "\t\t\t\t\t\tv6_prefix_length, pmtl[i].nw_t.idx, v6_prefix_div, lan6)) {" in sa
      and "\tchar lan6[INET6_ADDRSTRLEN] = {0};" in sa
      and sa.count("strlcpy(lan6, ipv6_router_address(NULL), sizeof(lan6));") == 1
      and sa.index("strlcpy(lan6, ipv6_router_address(NULL)") < sa.index("for (i = 1; i < mtl_sz; i++)")
      and sa.count("sdn_prefix_length = mtlan_prefix_by_subnet(v6_prefix, v6_prefix_length, pmtl[i].nw_t.idx, sdn_prefix, sizeof(sdn_prefix));") == 2
      and "mtlan_extend_prefix_by_subnet_idx(v6_prefix" not in sa)
l0 = svc.find("char* _add_ip6_lansdnaddr()\n{"); l1 = svc.find("\n}\n", l0); la = svc[l0:l1]
check("_add_ip6_lansdnaddr: with a /57-/63 the main LAN keeps the stock address path (ipv6_router_address(), no rewrite of "
      "a Static LAN address); set_ip6_sdnaddr() still runs first (REAPER-V6SPLIT-LAN0)",
      svc.count("REAPER-V6SPLIT-LAN0") == 1
      and "\tif (set_ip6_sdnaddr() && (v6_prefix_length < 57 || v6_prefix_length > 63)) {\n" in la
      and la.count("sdn_prefix_length = mtlan_extend_prefix_by_subnet_idx(v6_prefix, v6_prefix_length, 0, 8, sdn_prefix, sizeof(sdn_prefix));") == 2
      and "mtlan_prefix_by_subnet(" not in la and "mtlan_prefix_subnet64(" not in la
      and la.index("v6_prefix_length = nvram_get_int(") < la.index("if (set_ip6_sdnaddr() && ")
      and "p = (char*)ipv6_router_address(NULL);" in la[la.index("if (set_ip6_sdnaddr() && "):])
d0 = sdn.find("int write_dnsmasq_conf_sdn_ra_dhcp6_range(FILE* fp, const MTLAN_T *pmtl)"); d1 = sdn.find("\n}\n", d0)
check("the guest-network sites (sdn.c dnsmasq, set_ip6_sdnaddr) call the old function only for the ULA /48 split",
      d0 > 0 and all(", 48, " in m for m in re.findall(r"mtlan_extend_prefix_by_subnet_idx\(\s*([^;]*);", sdn[d0:d1] + sa)))
check("ULA fallback for a too-small provider prefix is logged once per boot (flag under /tmp/reaper)",
      svc.count("/* REAPER-V6SPLIT-ULA */") == 1 and svc.count("REAPER-V6SPLIT-NOTE") == 1
      and "if (share_subnet && v6_prefix_length > 56 && (v6_prefix[0] || v6_rtr_addr[0]))\t/* REAPER-V6SPLIT-ULA */\n\t\t\t\t\t\treaper_v6split_ula_note(pmtl[i].nw_t.ifname, v6_prefix_length, pmtl[i].nw_t.idx);" in sa
      and 'snprintf(flag, sizeof(flag), "/tmp/reaper/v6split_ula.%d.%d", plen, idx);\n\tif (f_exists(flag))\n\t\treturn;' in svc
      and svc.index("static void reaper_v6split_ula_note(") < s0)

# ---- default + page
check("shared/defaults.c: ipv6_prefix_len_wan defaults to 56 (once)",
      S["def"].count('{ "ipv6_prefix_len_wan", "56", CKN_STR3,') == 1 and '"ipv6_prefix_len_wan", "64"' not in S["def"])
pg = S["pg"]; js = pg[pg.rfind("<script>"):]
check("page: ASCII only", not any(ord(c) > 127 for c in pg))
check("page: Static pre-fill constants match the default (56 native, 64 static)",
      "var PLEN_NATIVE = '56', PLEN_STATIC = '64', PLEN_FILLED = false;" in js)
check("page: staticFill runs on a type change before sync; a typed value clears the pre-fill",
      "  on('s_service', 'change', staticFill);" in js and "  on('i_plenwan', 'input', plenTyped);" in js
      and js.index("on('s_service', 'change', staticFill);") < js.index("['s_service', 's_ifdev', 't_pd', 't_6rddhcp', 's_ac', 't_dnsauto'].forEach(function(id){ on(id, 'change', sync); });"))

# ---- host compile + run
gcc = shutil.which("gcc")
if gcc and om and bm:
    harness = r'''
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <arpa/inet.h>
@@OLD@@
@@NEW@@
static void s64(const char *name, const char *p, int plen, int idx)
{
	char b[INET6_ADDRSTRLEN] = "untouched";
	int r = mtlan_prefix_subnet64(p, plen, idx, b, sizeof(b));
	printf("%s=%d %s\n", name, r, b);
}
static void bys(const char *name, const char *p, int plen, int idx)
{
	char b[INET6_ADDRSTRLEN] = "untouched", o[INET6_ADDRSTRLEN] = "untouched";
	int r = mtlan_prefix_by_subnet(p, plen, idx, b, sizeof(b));
	int ro = mtlan_extend_prefix_by_subnet_idx(p, plen, (uint8_t)idx, 8, o, sizeof(o));
	printf("%s=%d %s|%d %s\n", name, r, b, ro, o);
}
int main(void)
{
	int i;
	char nm[32], small[8] = "keep";

	bys("b48", "2001:db8:1::", 48, 5);
	bys("b56", "2001:db8:1:ab00::", 56, 5);
	bys("b56_0", "2001:db8:1:ab00::", 56, 0);
	bys("b56_255", "2001:db8:1:ab00::", 56, 255);
	for (i = 0; i <= 16; i++) { snprintf(nm, sizeof(nm), "p60_%d", i); s64(nm, "2001:db8:1:ab70::", 60, i); }
	for (i = 0; i <= 4; i++) { snprintf(nm, sizeof(nm), "p62_%d", i); s64(nm, "2001:db8:1:ab7c::", 62, i); }
	for (i = 0; i <= 2; i++) { snprintf(nm, sizeof(nm), "p63_%d", i); s64(nm, "2001:db8:1:ab7e::", 63, i); }
	s64("p57_127", "2001:db8:1:ab80::", 57, 127);
	s64("p57_128", "2001:db8:1:ab80::", 57, 128);
	s64("p64_0", "2001:db8:1:ab7e::", 64, 0);
	s64("p56_1", "2001:db8:1:ab00::", 56, 1);
	s64("host", "2001:db8:1:ab7f::1", 60, 2);
	s64("neg", "2001:db8:1:ab70::", 60, -1);
	s64("junk", "not-an-address", 60, 1);
	printf("small=%d %s\n", mtlan_prefix_subnet64("2001:db8:1:ab70::", 60, 1, small, sizeof(small)), small);
	printf("ok=%d%d%d%d%d%d%d%d\n", mtlan_prefix_split_ok(48, 200, 0), mtlan_prefix_split_ok(56, 255, 0),
	       mtlan_prefix_split_ok(60, 15, 0), mtlan_prefix_split_ok(60, 16, 0), mtlan_prefix_split_ok(60, 16, 1),
	       mtlan_prefix_split_ok(64, 1, 0), mtlan_prefix_split_ok(64, 1, 1), mtlan_prefix_split_ok(63, 1, 0));
	bys("div60_16", "2001:db8:1:ab70::", 60, 16);
	bys("div64_1", "2001:db8:1:ab7e::", 64, 1);
	bys("fit60_3", "2001:db8:1:ab70::", 60, 3);
	{	/* /57-/63: never a length other than 64, never a split the index does not fit, prefix_div or not */
		int p, k, d, bad = 0;
		char b[INET6_ADDRSTRLEN];
		for (p = 57; p <= 63; p++)
			for (k = 0; k <= 255; k++)
				for (d = 0; d <= 1; d++) {
					int ok = mtlan_prefix_split_ok(p, k, d), r = mtlan_prefix_by_subnet("2001:db8:1:ab00::", p, k, b, sizeof(b));
					if (ok != mtlan_prefix_subnet64_fits(p, k) || (r != 0 && r != 64) || (r == 64) != (k < (1 << (64 - p))))
						bad++;
				}
		printf("strict=%d\n", bad);
	}
	/* main-LAN clash: Static LAN prefix ::a0/60 with the router at ::a5:1 (outside the first /64) */
	printf("clash=%d%d%d%d|%d%d%d|%d%d%d%d\n",
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 4, 0, "2001:db8:1:a5::1"),
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 5, 0, "2001:db8:1:a5::1"),
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 6, 0, "2001:db8:1:a5::1"),
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 5, 1, "2001:db8:1:a5::1"),
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 5, 0, "2001:db8:1:a0::1"),
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 5, 0, ""),
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 16, 0, "2001:db8:1:a5::1"),
	       mtlan_prefix_split_ok_lan("2001:db8:1::", 56, 5, 0, "2001:db8:1:5::1"),
	       mtlan_prefix_split_ok_lan("2001:db8:1:a0::", 60, 5, 0, "junk"),
	       mtlan_prefix_same64("2001:db8:1:a5::", "2001:db8:1:a5:ffff::9"),
	       mtlan_prefix_same64("2001:db8:1:a5::", "2001:db8:1:a4::1"));
	return 0;
}
'''
    harness = harness.replace("@@OLD@@", om.group(0)).replace("@@NEW@@", bm.group(1))
    d = tempfile.mkdtemp(prefix="v6split_")
    try:
        c = os.path.join(d, "t.c"); exe = os.path.join(d, "t")
        open(c, "w").write(harness)
        r = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Werror", "-o", exe, c], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        check("old function + new block compile on the host with -Wall -Werror", r.returncode == 0, r.stdout[-600:])
        if r.returncode == 0:
            out = dict(l.split("=", 1) for l in subprocess.run([exe], stdout=subprocess.PIPE, universal_newlines=True).stdout.splitlines())
            check("/48: whole-byte split unchanged (new order = old function; the callers raise its 56 to 64)",
                  out["b48"] == "56 2001:db8:1:500::|56 2001:db8:1:500::", out["b48"])
            check("/56: unchanged, index 0 and 255 too",
                  out["b56"] == "64 2001:db8:1:ab05::|64 2001:db8:1:ab05::" and out["b56_0"] == "64 2001:db8:1:ab00::|64 2001:db8:1:ab00::"
                  and out["b56_255"] == "64 2001:db8:1:abff::|64 2001:db8:1:abff::", (out["b56"], out["b56_0"], out["b56_255"]))
            check("/60: index 0 to 15 each get their own /64 (0 = the main LAN keeps the first)",
                  all(out["p60_%d" % i] == "64 2001:db8:1:ab7%x::" % i for i in range(16)), [out["p60_%d" % i] for i in (0, 1, 15)])
            check("/60: index 16 refused, buffer untouched", out["p60_16"] == "0 untouched", out["p60_16"])
            check("/62: index 0 to 3, 4 refused",
                  [out["p62_%d" % i] for i in range(5)] == ["64 2001:db8:1:ab7c::", "64 2001:db8:1:ab7d::", "64 2001:db8:1:ab7e::", "64 2001:db8:1:ab7f::", "0 untouched"])
            check("/63: index 0 and 1, 2 refused", [out["p63_%d" % i] for i in range(3)] == ["64 2001:db8:1:ab7e::", "64 2001:db8:1:ab7f::", "0 untouched"])
            check("/57: index 127 fits, 128 refused", out["p57_127"] == "64 2001:db8:1:abff::" and out["p57_128"] == "0 untouched", (out["p57_127"], out["p57_128"]))
            check("/64 and /56 are not this function's (refused)", out["p64_0"] == "0 untouched" and out["p56_1"] == "0 untouched")
            check("bits after the provider prefix are cleared before the index goes in", out["host"] == "64 2001:db8:1:ab72::", out["host"])
            check("negative index, a junk prefix and a too-small buffer are refused without touching the buffer",
                  out["neg"] == "0 untouched" and out["junk"] == "0 untouched" and out["small"] == "0 keep", (out["neg"], out["junk"], out["small"]))
            check("precedence: /48 and /56 any index; /60 index 15 yes, 16 never (not even with prefix_div); /64 only with prefix_div; /63 index 1 yes",
                  out["ok"] == "11100011", out["ok"])
            check("/60 index 16 with prefix_div: no split (ULA) - the old function's /72 would sit inside the main LAN's /64",
                  out["div60_16"] == "0 untouched|72 2001:db8:1:ab70:1000::", out["div60_16"])
            check("/57-/63, every index 0-255, prefix_div on and off: only /64 or nothing, and only when the index fits",
                  out.get("strict") == "0", out.get("strict"))
            check("main-LAN clash (::a0/60, router ::a5:1): index 4 and 6 split, index 5 refused (ULA) even with prefix_div",
                  out.get("clash", "").split("|")[0] == "1010", out.get("clash"))
            check("no clash when the router is in the first /64 or unknown; index 16 still refused",
                  out.get("clash", "|").split("|")[1] == "110", out.get("clash"))
            check("/56 is not checked (the main LAN is renumbered to index 0 there as before); a junk address is no clash; same64 compares 64 bits",
                  out.get("clash", "||").split("|")[2] == "1110", out.get("clash"))
            check("precedence: /64 with prefix_div keeps the old behaviour exactly", out["div64_1"].split("|")[0] == out["div64_1"].split("|")[1], out["div64_1"])
            check("precedence: /60 index 3 takes the new /64 (the old function gave a /72)",
                  out["fit60_3"] == "64 2001:db8:1:ab73::|72 2001:db8:1:ab70:300::", out["fit60_3"])
    finally:
        shutil.rmtree(d, ignore_errors=True)
elif not gcc:
    print("note: gcc not found - the host run is skipped")
else:
    check("old function and new block found for the host run", False)

# ---- page: staticFill under node
node = shutil.which("node")
f0 = js.find("var PLEN_NATIVE = "); f1 = js.find("function plenTyped(){ PLEN_FILLED = false; }\n")
if node and f0 > 0 and f1 > f0:
    code = js[f0:f1 + len("function plenTyped(){ PLEN_FILLED = false; }\n")]
    harness = r"""
var EL = {}, SVC = 'disabled', ORIG = 'disabled', NV = {ipv6_prefix_len_wan: '56'};
function q(id){ return EL[id] || (EL[id] = {value: ''}); }
function svc(){ return SVC; }
""" + code + r"""
function reset(orig, stored){ ORIG = orig; SVC = orig; NV.ipv6_prefix_len_wan = stored; q('i_plenwan').value = stored; PLEN_FILLED = false; }
function pick(s){ SVC = s; staticFill(); return q('i_plenwan').value; }
var o = {};
reset('disabled', '56'); o.fresh = [pick('other'), pick('dhcp6'), pick('other'), pick('disabled')];
reset('dhcp6', '56'); pick('other'); q('i_plenwan').value = '60'; plenTyped(); o.typed = [pick('dhcp6'), pick('other')];
reset('dhcp6', '56'); pick('other'); q('i_plenwan').value = '64'; plenTyped(); o.typed64 = [pick('dhcp6')];
reset('other', '56'); o.savedstatic = [pick('dhcp6'), pick('other')];
reset('dhcp6', '64'); o.oldrouter = [pick('other'), pick('dhcp6')];
reset('dhcp6', '48'); o.other48 = [pick('other')];
reset('dhcp6', '56'); q('i_plenwan').value = '50'; o.edited = [pick('other')];
console.log(JSON.stringify(o));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
        fh.write(harness); jp = fh.name
    r = subprocess.run([node, jp], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True); os.unlink(jp)
    try: o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: o = {}
    check("node: a new router picking Static sees 64, back to Native 56 again (and again)", o.get("fresh") == ["64", "56", "64", "56"], (o.get("fresh"), r.stderr[-300:]))
    check("node: a value typed under Static is kept when the type changes", o.get("typed") == ["60", "60"], o.get("typed"))
    check("node: 64 typed by hand under Static is kept too", o.get("typed64") == ["64"], o.get("typed64"))
    check("node: a router saved as Static keeps its stored value", o.get("savedstatic") == ["56", "56"], o.get("savedstatic"))
    check("node: an upgraded router (stored 64) is not touched", o.get("oldrouter") == ["64", "64"], o.get("oldrouter"))
    check("node: a stored value other than 56 is not touched", o.get("other48") == ["48"], o.get("other48"))
    check("node: a field edited before picking Static is not touched", o.get("edited") == ["50"], o.get("edited"))
elif node:
    check("staticFill() found for the node run", False, (f0, f1))
else:
    print("note: node not found - the page run is skipped")

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
