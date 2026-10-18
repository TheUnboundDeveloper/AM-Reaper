#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Channels fitted to the AiMesh nodes (rc/reaper_meshchan.c, 2026-10-16).

WHY THIS EXISTS. AiMesh records what every unit's radios can do (/tmp/chanspec_all.json)
and excludes the channels a node cannot use from the main router's channel picker. On the
owner's RT-BE96U with an RT-AX92U node the picker's own fall-back after a failed DFS check
left 5 GHz on 48/80 - already excluded, unusable by the node - for two hours, and nothing said
that every channel left for the node was a DFS one. reaper_meshchan.c reads the same lists,
decides which of the chanspecs a radio offers every node can follow (the sub-block rule), keeps
the result in /jffs so a reboot applies it before the nodes report, and the minimum-width daemon
watches the live channel against it.

WHAT IT DOES.
  A. Compiles the pure block of reaper_meshchan.c on the host and checks the chanspec decoder
     against every chanspec the owner's three radios print (`wl chanspecs`, all widths, 320 MHz
     included - 439 values): band, width and control channel must match the driver's label.
  B. Runs the fit rule on the owner's own chanspec_all.json: the 5 GHz result must agree with the
     AiMesh controller's own 49 exclusions in all but 165/20 (which stock excludes anyway); the
     bands the node has no radio on are unconstrained; DFS flags come from the router's own entry;
     a dual-5 GHz node counts its upper radio; two nodes intersect; a hole inside a block is seen
     (a control-channel-only rule would not see it); a mutated decoder fails the label check.
  C. Static: the rule never writes nvram, reads under the controller's file lock, keeps DFS; the
     minimum-width module calls it, holds during a join and re-picks one radio; the switch, the
     page row, the httpd field, the markers and the diag lines exist.

Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC - or no cc).
"""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:300] if detail else ""))

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "reaper_meshchan.c")):
    skip("no router source tree with rc/reaper_meshchan.c (argv[1] or REAPER_ROUTER_SRC)")

def rd(rel):
    p = os.path.join(SRC, rel)
    return open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""

MC = rd("rc/reaper_meshchan.c")
m = re.search(r"/\* ---- MESHCHAN_PURE_BEGIN.*?\*/\n(.*?)/\* ---- MESHCHAN_PURE_END ---- \*/", MC, re.S)
check("reaper_meshchan.c carries the pure block markers", m is not None)
PURE = m.group(1) if m else ""

# ---------------------------------------------------------------- fixtures (owner RT-BE96U, 2026-10-16)
DUMP = {
"wl0": """
1 (0x1001) 2 (0x1002) 3 (0x1003) 4 (0x1004) 5 (0x1005) 6 (0x1006) 7 (0x1007) 8 (0x1008)
9 (0x1009) 10 (0x100a) 11 (0x100b) 1l (0x1803) 5u (0x1903) 2l (0x1804) 6u (0x1904) 3l (0x1805)
7u (0x1905) 4l (0x1806) 8u (0x1906) 5l (0x1807) 9u (0x1907) 6l (0x1808) 10u (0x1908) 7l (0x1809)
11u (0x1909)
""",
"wl1": """
36 (0xd024) 40 (0xd028) 44 (0xd02c) 48 (0xd030) 52 (0xd034) 56 (0xd038) 60 (0xd03c) 64 (0xd040)
100 (0xd064) 104 (0xd068) 108 (0xd06c) 112 (0xd070) 116 (0xd074) 120 (0xd078) 124 (0xd07c) 128 (0xd080)
132 (0xd084) 136 (0xd088) 140 (0xd08c) 144 (0xd090) 149 (0xd095) 153 (0xd099) 157 (0xd09d) 161 (0xd0a1)
165 (0xd0a5) 36l (0xd826) 40u (0xd926) 44l (0xd82e) 48u (0xd92e) 52l (0xd836) 56u (0xd936) 60l (0xd83e)
64u (0xd93e) 100l (0xd866) 104u (0xd966) 108l (0xd86e) 112u (0xd96e) 116l (0xd876) 120u (0xd976) 124l (0xd87e)
128u (0xd97e) 132l (0xd886) 136u (0xd986) 140l (0xd88e) 144u (0xd98e) 149l (0xd897) 153u (0xd997) 157l (0xd89f)
161u (0xd99f) 36/80 (0xe02a) 40/80 (0xe12a) 44/80 (0xe22a) 48/80 (0xe32a) 52/80 (0xe03a) 56/80 (0xe13a) 60/80 (0xe23a)
64/80 (0xe33a) 100/80 (0xe06a) 104/80 (0xe16a) 108/80 (0xe26a) 112/80 (0xe36a) 116/80 (0xe07a) 120/80 (0xe17a) 124/80 (0xe27a)
128/80 (0xe37a) 132/80 (0xe08a) 136/80 (0xe18a) 140/80 (0xe28a) 144/80 (0xe38a) 149/80 (0xe09b) 153/80 (0xe19b) 157/80 (0xe29b)
161/80 (0xe39b) 36/160 (0xe832) 40/160 (0xe932) 44/160 (0xea32) 48/160 (0xeb32) 52/160 (0xec32) 56/160 (0xed32) 60/160 (0xee32)
64/160 (0xef32) 100/160 (0xe872) 104/160 (0xe972) 108/160 (0xea72) 112/160 (0xeb72) 116/160 (0xec72) 120/160 (0xed72) 124/160 (0xee72)
128/160 (0xef72)
""",
"wl2": """
6g1 (0x5001) 6g5 (0x5005) 6g9 (0x5009) 6g13 (0x500d) 6g17 (0x5011) 6g21 (0x5015) 6g25 (0x5019) 6g29 (0x501d)
6g33 (0x5021) 6g37 (0x5025) 6g41 (0x5029) 6g45 (0x502d) 6g49 (0x5031) 6g53 (0x5035) 6g57 (0x5039) 6g61 (0x503d)
6g65 (0x5041) 6g69 (0x5045) 6g73 (0x5049) 6g77 (0x504d) 6g81 (0x5051) 6g85 (0x5055) 6g89 (0x5059) 6g93 (0x505d)
6g97 (0x5061) 6g101 (0x5065) 6g105 (0x5069) 6g109 (0x506d) 6g113 (0x5071) 6g117 (0x5075) 6g121 (0x5079) 6g125 (0x507d)
6g129 (0x5081) 6g133 (0x5085) 6g137 (0x5089) 6g141 (0x508d) 6g145 (0x5091) 6g149 (0x5095) 6g153 (0x5099) 6g157 (0x509d)
6g161 (0x50a1) 6g165 (0x50a5) 6g169 (0x50a9) 6g173 (0x50ad) 6g177 (0x50b1) 6g181 (0x50b5) 6g185 (0x50b9) 6g189 (0x50bd)
6g193 (0x50c1) 6g197 (0x50c5) 6g201 (0x50c9) 6g205 (0x50cd) 6g209 (0x50d1) 6g213 (0x50d5) 6g217 (0x50d9) 6g221 (0x50dd)
6g225 (0x50e1) 6g229 (0x50e5) 6g1/40 (0x5803) 6g5/40 (0x5903) 6g9/40 (0x580b) 6g13/40 (0x590b) 6g17/40 (0x5813) 6g21/40 (0x5913)
6g25/40 (0x581b) 6g29/40 (0x591b) 6g33/40 (0x5823) 6g37/40 (0x5923) 6g41/40 (0x582b) 6g45/40 (0x592b) 6g49/40 (0x5833) 6g53/40 (0x5933)
6g57/40 (0x583b) 6g61/40 (0x593b) 6g65/40 (0x5843) 6g69/40 (0x5943) 6g73/40 (0x584b) 6g77/40 (0x594b) 6g81/40 (0x5853) 6g85/40 (0x5953)
6g89/40 (0x585b) 6g93/40 (0x595b) 6g97/40 (0x5863) 6g101/40 (0x5963) 6g105/40 (0x586b) 6g109/40 (0x596b) 6g113/40 (0x5873) 6g117/40 (0x5973)
6g121/40 (0x587b) 6g125/40 (0x597b) 6g129/40 (0x5883) 6g133/40 (0x5983) 6g137/40 (0x588b) 6g141/40 (0x598b) 6g145/40 (0x5893) 6g149/40 (0x5993)
6g153/40 (0x589b) 6g157/40 (0x599b) 6g161/40 (0x58a3) 6g165/40 (0x59a3) 6g169/40 (0x58ab) 6g173/40 (0x59ab) 6g177/40 (0x58b3) 6g181/40 (0x59b3)
6g185/40 (0x58bb) 6g189/40 (0x59bb) 6g193/40 (0x58c3) 6g197/40 (0x59c3) 6g201/40 (0x58cb) 6g205/40 (0x59cb) 6g209/40 (0x58d3) 6g213/40 (0x59d3)
6g217/40 (0x58db) 6g221/40 (0x59db) 6g225/40 (0x58e3) 6g229/40 (0x59e3) 6g1/80 (0x6007) 6g5/80 (0x6107) 6g9/80 (0x6207) 6g13/80 (0x6307)
6g17/80 (0x6017) 6g21/80 (0x6117) 6g25/80 (0x6217) 6g29/80 (0x6317) 6g33/80 (0x6027) 6g37/80 (0x6127) 6g41/80 (0x6227) 6g45/80 (0x6327)
6g49/80 (0x6037) 6g53/80 (0x6137) 6g57/80 (0x6237) 6g61/80 (0x6337) 6g65/80 (0x6047) 6g69/80 (0x6147) 6g73/80 (0x6247) 6g77/80 (0x6347)
6g81/80 (0x6057) 6g85/80 (0x6157) 6g89/80 (0x6257) 6g93/80 (0x6357) 6g97/80 (0x6067) 6g101/80 (0x6167) 6g105/80 (0x6267) 6g109/80 (0x6367)
6g113/80 (0x6077) 6g117/80 (0x6177) 6g121/80 (0x6277) 6g125/80 (0x6377) 6g129/80 (0x6087) 6g133/80 (0x6187) 6g137/80 (0x6287) 6g141/80 (0x6387)
6g145/80 (0x6097) 6g149/80 (0x6197) 6g153/80 (0x6297) 6g157/80 (0x6397) 6g161/80 (0x60a7) 6g165/80 (0x61a7) 6g169/80 (0x62a7) 6g173/80 (0x63a7)
6g177/80 (0x60b7) 6g181/80 (0x61b7) 6g185/80 (0x62b7) 6g189/80 (0x63b7) 6g193/80 (0x60c7) 6g197/80 (0x61c7) 6g201/80 (0x62c7) 6g205/80 (0x63c7)
6g209/80 (0x60d7) 6g213/80 (0x61d7) 6g217/80 (0x62d7) 6g221/80 (0x63d7) 6g1/160 (0x680f) 6g5/160 (0x690f) 6g9/160 (0x6a0f) 6g13/160 (0x6b0f)
6g17/160 (0x6c0f) 6g21/160 (0x6d0f) 6g25/160 (0x6e0f) 6g29/160 (0x6f0f) 6g33/160 (0x682f) 6g37/160 (0x692f) 6g41/160 (0x6a2f) 6g45/160 (0x6b2f)
6g49/160 (0x6c2f) 6g53/160 (0x6d2f) 6g57/160 (0x6e2f) 6g61/160 (0x6f2f) 6g65/160 (0x684f) 6g69/160 (0x694f) 6g73/160 (0x6a4f) 6g77/160 (0x6b4f)
6g81/160 (0x6c4f) 6g85/160 (0x6d4f) 6g89/160 (0x6e4f) 6g93/160 (0x6f4f) 6g97/160 (0x686f) 6g101/160 (0x696f) 6g105/160 (0x6a6f) 6g109/160 (0x6b6f)
6g113/160 (0x6c6f) 6g117/160 (0x6d6f) 6g121/160 (0x6e6f) 6g125/160 (0x6f6f) 6g129/160 (0x688f) 6g133/160 (0x698f) 6g137/160 (0x6a8f) 6g141/160 (0x6b8f)
6g145/160 (0x6c8f) 6g149/160 (0x6d8f) 6g153/160 (0x6e8f) 6g157/160 (0x6f8f) 6g161/160 (0x68af) 6g165/160 (0x69af) 6g169/160 (0x6aaf) 6g173/160 (0x6baf)
6g177/160 (0x6caf) 6g181/160 (0x6daf) 6g185/160 (0x6eaf) 6g189/160 (0x6faf) 6g193/160 (0x68cf) 6g197/160 (0x69cf) 6g201/160 (0x6acf) 6g205/160 (0x6bcf)
6g209/160 (0x6ccf) 6g213/160 (0x6dcf) 6g217/160 (0x6ecf) 6g221/160 (0x6fcf) 6g1/320-1 (0x7000) 6g5/320-1 (0x7040) 6g9/320-1 (0x7080) 6g13/320-1 (0x70c0)
6g17/320-1 (0x7100) 6g21/320-1 (0x7140) 6g25/320-1 (0x7180) 6g29/320-1 (0x71c0) 6g33/320-1 (0x7200) 6g37/320-1 (0x7240) 6g41/320-1 (0x7280) 6g45/320-1 (0x72c0)
6g49/320-1 (0x7300) 6g53/320-1 (0x7340) 6g57/320-1 (0x7380) 6g61/320-1 (0x73c0) 6g33/320-2 (0x7001) 6g37/320-2 (0x7041) 6g41/320-2 (0x7081) 6g45/320-2 (0x70c1)
6g49/320-2 (0x7101) 6g53/320-2 (0x7141) 6g57/320-2 (0x7181) 6g61/320-2 (0x71c1) 6g65/320-2 (0x7201) 6g69/320-2 (0x7241) 6g73/320-2 (0x7281) 6g77/320-2 (0x72c1)
6g81/320-2 (0x7301) 6g85/320-2 (0x7341) 6g89/320-2 (0x7381) 6g93/320-2 (0x73c1) 6g65/320-1 (0x7002) 6g69/320-1 (0x7042) 6g73/320-1 (0x7082) 6g77/320-1 (0x70c2)
6g81/320-1 (0x7102) 6g85/320-1 (0x7142) 6g89/320-1 (0x7182) 6g93/320-1 (0x71c2) 6g97/320-1 (0x7202) 6g101/320-1 (0x7242) 6g105/320-1 (0x7282) 6g109/320-1 (0x72c2)
6g113/320-1 (0x7302) 6g117/320-1 (0x7342) 6g121/320-1 (0x7382) 6g125/320-1 (0x73c2) 6g97/320-2 (0x7003) 6g101/320-2 (0x7043) 6g105/320-2 (0x7083) 6g109/320-2 (0x70c3)
6g113/320-2 (0x7103) 6g117/320-2 (0x7143) 6g121/320-2 (0x7183) 6g125/320-2 (0x71c3) 6g129/320-2 (0x7203) 6g133/320-2 (0x7243) 6g137/320-2 (0x7283) 6g141/320-2 (0x72c3)
6g145/320-2 (0x7303) 6g149/320-2 (0x7343) 6g153/320-2 (0x7383) 6g157/320-2 (0x73c3) 6g129/320-1 (0x7004) 6g133/320-1 (0x7044) 6g137/320-1 (0x7084) 6g141/320-1 (0x70c4)
6g145/320-1 (0x7104) 6g149/320-1 (0x7144) 6g153/320-1 (0x7184) 6g157/320-1 (0x71c4) 6g161/320-1 (0x7204) 6g165/320-1 (0x7244) 6g169/320-1 (0x7284) 6g173/320-1 (0x72c4)
6g177/320-1 (0x7304) 6g181/320-1 (0x7344) 6g185/320-1 (0x7384) 6g189/320-1 (0x73c4) 6g161/320-2 (0x7005) 6g165/320-2 (0x7045) 6g169/320-2 (0x7085) 6g173/320-2 (0x70c5)
6g177/320-2 (0x7105) 6g181/320-2 (0x7145) 6g185/320-2 (0x7185) 6g189/320-2 (0x71c5) 6g193/320-2 (0x7205) 6g197/320-2 (0x7245) 6g201/320-2 (0x7285) 6g205/320-2 (0x72c5)
6g209/320-2 (0x7305) 6g213/320-2 (0x7345) 6g217/320-2 (0x7385) 6g221/320-2 (0x73c5)
""",
}
BAND_OF = {"wl0": 0, "wl1": 1, "wl2": 2}

# the router's own entry (..:53:F0) and the RT-AX92U node (..:53:10), documentation MACs, in the
# shape the controller wrote them
JSON_OWNER = ('{"00:00:5E:00:53:10":{"2G":{"bandwidth":3,"channel":"1 00000001 00000002 00000003 00000004 00000005 00000006 00000007 00000008 00000009 00000010 00000011 "},'
              '"5G":{"bandwidth":7,"channel":"1 00001036 00001040 00001044 00001048 "},'
              '"5G1":{"bandwidth":15,"channel":"1 00002100 00002104 00002108 00002112 00008116 00008120 00008124 00008128 00002132 00002136 00002140 00002144 00001149 00001153 00001157 00001161 00001165 "},'
              '"cfg_bandnum":3,"is_re":1},'
              '"00:00:5E:00:53:F0":{"2G":{"bandwidth":3,"channel":"1 00000001 00000002 00000003 00000004 00000005 00000006 00000007 00000008 00000009 00000010 00000011 "},'
              '"5G":{"bandwidth":15,"channel":"1 00001036 00001040 00001044 00001048 00002052 00002056 00002060 00002064 00002100 00002104 00002108 00002112 00002116 00002120 00002124 00002128 00002132 00002136 00002140 00002144 00001149 00001153 00001157 00001161 00001165 "},'
              '"6G":{"bandwidth":31,"channel":"1 ' + " ".join("%08d" % c for c in range(1, 230, 4)) + ' "},'
              '"cfg_bandnum":3,"is_re":0}}')
# the controller's own 5 GHz exclusion for that mesh (wl1_acs_excl_chans_cfg, 49 entries)
CFG_EXCL_WL1 = set("0xd024,0xd028,0xd02c,0xd030,0xd034,0xd038,0xd03c,0xd040,0xd074,0xd078,0xd07c,0xd080,0xd0a5,0xd826,0xd926,0xd82e,0xd92e,0xd836,0xd936,0xd83e,0xd93e,0xd876,0xd976,0xd87e,0xd97e,0xe02a,0xe12a,0xe22a,0xe32a,0xe03a,0xe13a,0xe23a,0xe33a,0xe07a,0xe17a,0xe27a,0xe37a,0xe832,0xe932,0xea32,0xeb32,0xec32,0xed32,0xee32,0xef32,0xec72,0xed72,0xee72,0xef72".split(","))

def labels(txt):
    out = []
    for lab, hx in re.findall(r"(\S+) \((0x[0-9a-f]{4})\)", txt):
        m2 = re.match(r"^(?:6g)?(\d+)(?:/(\d+)(?:-(\d))?|([lu]))?$", lab)
        assert m2, lab
        ctl = int(m2.group(1))
        width = int(m2.group(2)) if m2.group(2) else (40 if m2.group(4) else 20)
        out.append((hx, ctl, width))
    return out

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static size_t host_strlcat(char *d, const char *s, size_t n) {
	size_t dl = strlen(d), sl = strlen(s), room = n > dl ? n - dl - 1 : 0, k = sl < room ? sl : room;
	memcpy(d + dl, s, k); d[dl + k] = 0; return dl + sl; }
#define strlcat host_strlcat
@PURE@
static char *slurp(const char *p) { FILE *f = fopen(p, "r"); static char b[65536]; size_t n = f ? fread(b, 1, sizeof(b) - 1, f) : 0; if (f) fclose(f); b[n] = 0; return b; }
int main(int argc, char **argv) {
	int i;
	if (argc < 2) return 2;
	if (!strcmp(argv[1], "decode")) {
		for (i = 2; i < argc; i++) { int b, w, c, cov[MC_MAXCOV], n = mc_decode(strtoul(argv[i], NULL, 16), &b, &w, &c, cov), k;
			printf("%s %d %d %d", argv[i], b, w, c); for (k = 0; k < n; k++) printf(" %d", cov[k]); printf("\n"); }
		return 0;
	}
	if (!strcmp(argv[1], "lift")) {	/* lift <json> <floor> <excl-list> <hex>... -> "<n> <lifted>" then the list after */
		static struct mc_nodes nds; static unsigned short off[512]; static unsigned char fit[512], dfs[512]; static char cur[8192], lifted[2048];
		int n = 0, k, fl = atoi(argv[3]);
		if (mc_parse_json(slurp(argv[2]), &nds) < 0) { printf("PARSE-ERROR\n"); return 1; }
		strcpy(cur, argv[4]); lifted[0] = 0;
		for (i = 5; i < argc && n < 512; i++) { int d = -1, f = mc_compat(&nds, strtoul(argv[i], NULL, 16), &d);
			off[n] = (unsigned short)strtoul(argv[i], NULL, 16); fit[n] = f == 1; dfs[n] = d == 1; n++; }
		k = mc_lift(off, fit, dfs, n, fl, cur, lifted, sizeof(lifted));
		printf("%d %s\n%s\n", k, lifted[0] ? lifted : "-", cur); return 0;
	}
	if (!strcmp(argv[1], "relift")) {	/* relift <excl-list> <old-lifted> -> "<n> <lifted>" then the list after */
		static char cur[8192], lifted[2048];
		strcpy(cur, argv[2]); lifted[0] = 0;
		i = mc_relift(argv[3], cur, lifted, sizeof(lifted));
		printf("%d %s\n%s\n", i, lifted[0] ? lifted : "-", cur); return 0;
	}
	if (!strcmp(argv[1], "nodes") || !strcmp(argv[1], "compat")) {
		static struct mc_nodes nds; if (mc_parse_json(slurp(argv[2]), &nds) < 0) { printf("PARSE-ERROR\n"); return 1; }
		if (!strcmp(argv[1], "nodes")) { printf("%d %d %d\n", nds.n, nds.res, nds.cap);
			for (i = 0; i < nds.n; i++) { int c, mn = 0; for (c = 1; c < MC_NCH && !mn; c++) if (nds.v[i].b[1].flag[c] >= 1 && nds.v[i].b[1].flag[c] <= 3) mn = c;
				printf("%s %d %d %d %d %d %d %d\n", nds.v[i].mac, nds.v[i].is_re, nds.v[i].dual5g, mn, nds.v[i].b[1].bwmask, nds.v[i].b[0].present, nds.v[i].b[1].present, nds.v[i].b[2].present); }
			return 0; }
		for (i = 3; i < argc; i++) { int d = -1, f = mc_compat(&nds, strtoul(argv[i], NULL, 16), &d); printf("%s %d %d\n", argv[i], f, d); }
		return 0;
	}
	return 2;
}
'''

cc = shutil.which("gcc") or shutil.which("cc")
if not cc:
    skip("no host C compiler")
tmp = tempfile.mkdtemp(prefix="meshchan_")
def build(pure, name):
    c = os.path.join(tmp, name + ".c"); exe = os.path.join(tmp, name)
    open(c, "w").write(HARNESS.replace("@PURE@", pure))
    r = subprocess.run([cc, "-std=gnu99", "-Wall", "-Werror", "-Wno-unused-function", "-o", exe, c], capture_output=True, text=True)
    return exe if r.returncode == 0 else ("", r.stderr)
def run(exe, *args):
    return subprocess.run([exe] + list(args), capture_output=True, text=True).stdout.strip().splitlines()
def wjson(name, txt):
    p = os.path.join(tmp, name); open(p, "w").write(txt); return p

try:
    exe = build(PURE, "t")
    check("pure block compiles with -Wall -Werror", isinstance(exe, str) and exe != "", exe if isinstance(exe, tuple) else "")
    if not isinstance(exe, str) or not exe:
        print(exe[1] if isinstance(exe, tuple) else 'no compiler output')
        raise SystemExit(1)

    # ---- A. the decoder against the driver's own labels
    total, bad = 0, []
    for r_, txt in DUMP.items():
        labs = labels(txt)
        out = run(exe, "decode", *[h for h, _, _ in labs])
        got = {l.split()[0]: l.split() for l in out}
        for hx, ctl, width in labs:
            total += 1
            g = got.get(hx)
            if not g or int(g[1]) != BAND_OF[r_] or int(g[2]) != width or int(g[3]) != ctl:
                bad.append((hx, ctl, width, g))
    check("decoder: band, width and control channel match the driver's label for all %d chanspecs" % total, total >= 430 and not bad, bad[:5])
    # covered channels: ascending, 4 apart, width/20 of them, control inside (sample every entry)
    out = run(exe, "decode", *[h for txt in DUMP.values() for h, _, _ in labels(txt)])
    okcov = True
    for l in out:
        p = l.split(); w = int(p[2]); ctl = int(p[3]); cov = [int(x) for x in p[4:]]
        if len(cov) != w // 20 or ctl not in cov or any(cov[i + 1] - cov[i] != 4 for i in range(len(cov) - 1)):
            okcov = False; break
    check("decoder: every chanspec covers width/20 channels 4 apart with the control inside", okcov, l if not okcov else "")

    # ---- B. the rule on the owner's mesh
    jo = wjson("owner.json", JSON_OWNER)
    nd = run(exe, "nodes", jo)
    check("owner json: 2 units, 1 node, the router's own entry found", nd and nd[0] == "2 1 1", nd[:1])
    ax = [l for l in nd[1:] if l.startswith("00:00:5E:00:53:10")]
    check("RT-AX92U: two 5 GHz radios -> the upper one (100-165) is the backhaul band, 160 MHz capable, no 6 GHz",
          ax and ax[0].split()[1:] == ["1", "1", "100", "15", "1", "1", "0"], ax)
    wl1 = [h for h, _, _ in labels(DUMP["wl1"])]
    res = {l.split()[0]: (int(l.split()[1]), int(l.split()[2])) for l in run(exe, "compat", jo, *wl1)}
    compat = {h for h, (f, _) in res.items() if f == 1}
    noncompat = set(wl1) - compat
    check("5 GHz: 41 of %d chanspecs fit the node" % len(wl1), len(compat) == 41, len(compat))
    check("5 GHz: the chanspecs that do not fit = the controller's own 49 exclusions minus 165/20 (stock excludes it anyway)",
          noncompat == CFG_EXCL_WL1 - {"0xd0a5"}, sorted(noncompat ^ (CFG_EXCL_WL1 - {"0xd0a5"})))
    check("5 GHz: 100/160 with the control on 100-112 fits (the node's 80 MHz sub-block is usable), on 116-128 it does not",
          all(res[h][0] == 1 for h in ("0xe872", "0xe972", "0xea72", "0xeb72")) and all(res[h][0] == 0 for h in ("0xec72", "0xed72", "0xee72", "0xef72")))
    check("5 GHz: DFS from the router's own entry - 100/80 DFS, 149/80 and 36/80 not",
          res["0xe06a"][1] == 1 and res["0xe09b"][1] == 0 and res["0xe02a"][1] == 0)
    for r_ in ("wl0", "wl2"):
        hs = [h for h, _, _ in labels(DUMP[r_])]
        rr = run(exe, "compat", jo, *hs)
        check("%s: a band the node has no backhaul constraint on is unconstrained (%d chanspecs all fit)" % (r_, len(hs)),
              all(int(l.split()[1]) == 1 for l in rr) and len(rr) == len(hs))
    rr = run(exe, "compat", jo, "0x7042")
    check("6 GHz: no DFS flag on 6g69/320-1", rr and rr[0].split()[2] == "0")

    # a Wi-Fi 7 node = the router's own capabilities as a node: nothing excluded anywhere
    # the router's own entry alone, as a node: a Wi-Fi 7 node with full lists on every band
    jb = wjson("be.json", "{" + JSON_OWNER[JSON_OWNER.index('"00:00:5E:00:53:F0'):-1].replace('"is_re":0', '"is_re":1') + "}")
    allh = [h for txt in DUMP.values() for h, _, _ in labels(txt)]
    rr = run(exe, "compat", jb, *allh)
    check("a BE node with the router's own lists: every chanspec of every band fits", all(int(l.split()[1]) == 1 for l in rr) and len(rr) == len(allh))
    # two nodes intersect: add a node that lacks 149-165
    j2 = JSON_OWNER[:-1] + ',"AA:BB:CC:DD:EE:01":{"5G":{"bandwidth":7,"channel":"1 00002100 00002104 00002108 00002112 00002132 00002136 00002140 00002144 "},"is_re":1}}'
    rr = {l.split()[0]: int(l.split()[1]) for l in run(exe, "compat", wjson("two.json", j2), *wl1)}
    check("two nodes: 149/80 fits the first and not the second -> excluded; 100/80 still fits both",
          rr["0xe09b"] == 0 and rr["0xe06a"] == 1 and rr["0xd095"] == 0)
    # a hole inside the block: control-channel-only would pass 100/80, the sub-block rule does not
    jh = '{"CAP":{"5G":{"bandwidth":15,"channel":"1 00001100 00001104 00001108 00001112 "},"is_re":0},"NODE":{"5G":{"bandwidth":15,"channel":"1 00002100 00002104 00002112 "},"is_re":1}}'
    rr = {l.split()[0]: int(l.split()[1]) for l in run(exe, "compat", wjson("hole.json", jh), "0xe06a", "0xd064", "0xd866")}
    check("a hole in the node's block: 100/20 fits, 100l (100+104) fits, 100/80 (needs 108) does not", rr["0xd064"] == 1 and rr["0xd866"] == 1 and rr["0xe06a"] == 0)
    # garbage is refused, not misread
    rr = run(exe, "compat", wjson("bad.json", '{"X": [1,2'), "0xe06a")
    check("a truncated file is refused (PARSE-ERROR), never read as an empty mesh", rr and rr[0] == "PARSE-ERROR")

    # ---- the lift (owner ruling 2026-10-16) on the box's live exclusion list (acs_cli2 -i wl1 -S, 56 entries)
    EXCL56 = ("0xd0a5,0xd8a7,0xe0ab,0xeca3,0xe09b,0xe19b,0xe29b,0xe39b,0xd024,0xd028,0xd02c,0xd030,0xd034,0xd038,0xd03c,0xd040,"
              "0xd074,0xd078,0xd07c,0xd080,0xd826,0xd926,0xd82e,0xd92e,0xd836,0xd936,0xd83e,0xd93e,0xd876,0xd976,0xd87e,0xd97e,"
              "0xe02a,0xe12a,0xe22a,0xe32a,0xe03a,0xe13a,0xe23a,0xe33a,0xe07a,0xe17a,0xe27a,0xe37a,0xe832,0xe932,0xea32,0xeb32,"
              "0xec32,0xed32,0xee32,0xef32,0xec72,0xed72,0xee72,0xef72")
    out = run(exe, "lift", jo, "80", EXCL56, *wl1)
    k, lifted = out[0].split(" ", 1); after = out[1]
    check("lift @80: exactly the four 149-161/80 entries of the stock Auto-width rule are un-excluded",
          k == "4" and set(lifted.split(",")) == {"0xe09b", "0xe19b", "0xe29b", "0xe39b"}, out[0])
    aft = set(after.split(","))
    check("lift @80: the list keeps everything else (52 left, 48/80 still excluded, nothing added)",
          len(aft) == 52 and "0xe32a" in aft and aft == set(EXCL56.split(",")) - {"0xe09b", "0xe19b", "0xe29b", "0xe39b"})
    out = run(exe, "lift", jo, "0", EXCL56, *wl1)
    check("lift @0 (no floor): 149/20 is already allowed, so nothing is lifted", out[0] == "0 -" and out[1] == EXCL56)
    out = run(exe, "lift", jo, "80", EXCL56.replace("0xe29b,", ""), *wl1)
    check("lift @80 with 157/80 already allowed: nothing is lifted", out[0] == "0 -")

    # ---- the held plan keeps its lift (audit 2026-10-16 B1): the recorded entries come out of the list again
    FOUR = {"0xe09b", "0xe19b", "0xe29b", "0xe39b"}
    out = run(exe, "relift", EXCL56, "0xe09b,0xe19b,0xe29b,0xe39b")
    k, lifted = out[0].split(" ", 1)
    check("relift: the four recorded entries are taken out again and carried forward",
          k == "4" and set(lifted.split(",")) == FOUR and set(out[1].split(",")) == set(EXCL56.split(",")) - FOUR, out[0])
    out = run(exe, "relift", EXCL56.replace("0xe09b,", ""), "0xe09b,0xe19b")
    check("relift: an entry already allowed is not counted, the other still comes out", out[0] == "1 0xe19b", out[0])
    out = run(exe, "relift", EXCL56, "")
    check("relift: nothing recorded, nothing changes", out[0] == "0 -" and out[1] == EXCL56)

    # ---- negative control: a decoder with the 40 MHz sideband flipped must fail the label check
    mut = PURE.replace("*width = 40; *ctl = sb ? c + 2 : c - 2;", "*width = 40; *ctl = sb ? c - 2 : c + 2;")
    check("self-test: the mutation applies", mut != PURE)
    mexe = build(mut, "m")
    if isinstance(mexe, str) and mexe:
        labs = labels(DUMP["wl1"])
        out = {l.split()[0]: l.split() for l in run(mexe, "decode", *[h for h, _, _ in labs])}
        wrong = sum(1 for hx, ctl, width in labs if int(out[hx][3]) != ctl)
        check("self-test: the flipped decoder fails the label check (%d wrong)" % wrong, wrong >= 20)
    else:
        check("self-test: the flipped decoder compiles", False, mexe)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---- C. static
check("meshchan: never writes nvram (knowledge only; the minimum-width module owns the list)", "nvram_set(" not in MC)
check("meshchan: reads the controller's file under its own lock", 'file_lock("chanspec")' in MC and '/tmp/chanspec_all.json' in MC)
check("meshchan: the result is held in /jffs and mirrored to /tmp/reaper", '"/jffs/reaper_meshchan"' in MC and '"/tmp/reaper/meshchan"' in MC)
check("meshchan: the nodes' lists are kept in /jffs (RAM-only on the router) and used at boot, less nodes that left the registry",
      'MC_REC "/nodes.json"' in MC and "reaper_write_atomic(MC_NODES_SNAP, buf, n, 0600)" in MC and "mc_only_registered(nds)" in MC and 'nds.snap ? "snapshot" : "reported"' in MC)
check("meshchan: DFS channels are kept (flag 2 = code 3 counts as usable)", "f >= 1 && f <= 3" in MC and "MC_DFS_CODE	3" in MC)
check("meshchan: the held plan re-applies its recorded lift, and only a plan built from lists speaks the lift line (audit 2026-10-16 B1)",
      "nlifted = mc_relift(old, cur, lifted, sizeof(lifted));" in MC and 'if (nlifted && loaded && !mc_said(u, "lifted", st.sig))' in MC)
check("meshchan: the kept copy of the node lists is rewritten only when the bytes differ (audit 2026-10-16 C2)",
      "if (!mc_snap_same(buf, n))" in MC and "return m == n && memcmp(have, buf, n) == 0;" in MC)
check("meshchan: a dual-5 GHz node counts its upper radio", "band_min(&b5[1]) > band_min(&b5[0])" in MC)
check("meshchan: ASCII only", all(ord(ch) < 128 for ch in MC))
BF = rd("rc/reaper_bwfloor.c")
check("bwfloor: the fit runs inside excl_unit after the floor, with the floor as it stands", "reaper_meshchan_excl(u, ifn, band, mfl, cur, sizeof(cur), added, sizeof(added))" in BF)
check("bwfloor: puncturing implies the 80 MHz floor", re.search(r'static int configured\(int u\)\s*\{[^}]*"punct"', BF) is not None)
check("bwfloor: the watcher holds while a node joins and for a settle after", '"cfg_obstatus"' in BF and "hold=onboarding" in BF and "hold=settle" in BF)
check("bwfloor: a correction re-picks ONE radio the way the AiMesh controller does", '"acs_restart"' in BF and '"acscli2_acs_restart"' in BF)
check("bwfloor: a correction waits 60 s outside the set and backs off", "BF_FIT_BAD" in BF and "BF_FIT_COOL" in BF and "BF_FIT_MAXFIX" in BF)
check("bwfloor: the corrective is a direct move to a node-usable non-DFS chanspec (the survey's mechanism), verified on the operating chanspec",
      '"acs_update"' in BF and "reaper_meshchan_target(u," in BF and '"Chanspec:"' in BF and "oper_chanspec(ifn, &oper)" in BF)
check("bwfloor: the tick judges the radio by the chanspec iovar; `wl status` is forked only inside move_to()'s verification (audit 2026-10-16 C1)",
      "if (w && oper_chanspec(ifn, &ocs))" not in BF and "oper_chanspec(ifn, &oper) && oper == to" in BF)
check("bwfloor: the list is written whenever it changed (a lift alone removes entries) and handed to the running picker - daemon only, no re-pick",
      "if (strcmp(cur, orig) != 0) {" in BF and 'eval("acs_cli2", "-i", ifn, "set", "acs_excl_chans", cur);' in BF and "if (g_daemon && ifname_ok(ifn))" in BF
      and "g_daemon = 1;" in BF.split("int reaper_bwfloor_main(int argc, char *argv[])")[-1])
check("meshchan: the lift lives in the pure block, is recorded (line 4) and restored before every recomputation",
      "mc_lift(offer, fit, dfs, n, floor, cur, lifted, sizeof(lifted))" in MC and "mc_read_line(u, 4, old, sizeof(old))" in MC and "int reaper_meshchan_target(int u, int floor, unsigned *cs)" in MC)
check("bwfloor: no re-pick when the plan leaves the nodes no non-DFS landing (the driver's DFS fall-back would repeat)",
      "if (reaper_meshchan_nondfs(u) == 0) {" in BF and "hold=nolanding" in BF and "int reaper_meshchan_nondfs(int u)" in MC)
check("bwfloor: the daemon stays up while the fit is on", "if (reaper_meshchan_enabled())" in BF.split("void start_reaper_bwfloor(void)")[-1])
check("defaults: amas_chanfit is on by default", re.search(r'\{\s*"amas_chanfit",\s*"1"', rd("shared/defaults.c")) is not None)
check("rc/Makefile builds reaper_meshchan.o", "reaper_meshchan.o" in rd("rc/Makefile"))
check("rwatch: restarts the daemon with the fit on and a node registered", "amas_chanfit" in rd("rc/rwatch.c"))
WEB = rd("httpd/web.c")
check("httpd: the fit fields reach the page as wlN_chanfit_st", "wl%d_chanfit_st" in WEB and '" fit="' in WEB)
PG = rd("www/Reaper_WiFiSettings.asp")
check("page: the switch row (global key), GNV entry and status renderer", 'key:"amas_chanfit"' in PG and 'amas_chanfit:"<% nvram_get("amas_chanfit"); %>"' in PG and "function fitStatus(u)" in PG)
check("page: the floor status shows when puncturing implies it", "RWFP_136" in PG)
check("page: a nolanding hold shows the DFS-only note, not the join note", 'f[5]==="nolanding"' in PG)
DG = rd("others/reaper_diag")
check("diag: v1.3.40 reports the node fit", 'VER="REAPER-DIAG v1.3.40"' in DG and "node fit:" in DG and "REAPER-DIAG v1.3.40</span>" in rd("www/Reaper_Diag.asp"))
packs = [f for f in os.listdir(os.path.join(SRC, "www")) if f.endswith(".dict") and f != "temp.dict"]
missing = []
for p in sorted(packs):
    d = rd("www/" + p)
    for k in range(130, 140):
        m3 = re.search(r"^RWFP_%d=(.+)$" % k, d, re.M)
        if not m3 or not m3.group(1).strip() or "`" in m3.group(1) or "${" in m3.group(1):
            missing.append("%s:RWFP_%d" % (p, k))
check("RWFP_130..139 present and template-safe in all %d packs" % len(packs), len(packs) == 25 and not missing, missing[:6])

print("\n%d failure(s)" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
