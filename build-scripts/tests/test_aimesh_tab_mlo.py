#!/usr/bin/env python3
"""AiMesh tab: MLO devices flagged MLO on the main router too (v3.8.1 alpha field report, 2026-11-17).

WHY. The AiMesh tab (stock aimesh_topology.html) and the stock client lists (client_function.js) show a client as
MLO from "mlo" in the get_clientlist hook, which is networkmap's (closed) client list. networkmap leaves it 0 for
the stations Reaper's own scan knows are MLO (the PSEUDO_MLO_CAP links cfg_mnt maps through mld_mac), so the Devices
page said MLO and the AiMesh tab did not. Reaper's overlay on the hook ran only on a box that is not routing, and even
there never set "mlo" on a row networkmap already had.

THE FIX (httpd/web.c, REAPER-AIMESH-MLO). ej_get_clientlist calls rdev_mark_mlo() in every mode: while MLO is on it
raises "mlo" to "1" on each row whose device is MLO in Reaper's device table (as the last collect left it, no older
than RMLO_TAB_AGE) or in cfg_mnt's live client list (a randomized per-link MAC naming another MAC as mld_mac - the
same fold rdev_scan_wl makes), a per-link MAC row folding to its device. A "1" is never cleared, no row is added, no
other field changes, nodes and backhaul stations are left alone, and the hook never scans the radios for it. AP mode's
merge raises the same flag on a row networkmap already has.

WHAT IT DOES. Source pins (call site in both modes, AP-mode branch, cached sources only, one MLO-on rule, the cfg_mnt
parse cache shared, the stub without AiMesh sync); with gcc and the in-tree json-c, lifts the marked block, the
cfg_mnt walker, rmlo_link_cb and rdev_mark_mlo out of web.c, compiles them (-Wall -Werror) with stand-ins for nvram,
the device table and the cfg_mnt file, and runs them on a networkmap-shaped fixture. Fixtures use documentation
MACs (00:00:5E:00:53:xx and locally administered variants).
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import json, os, re, shutil, subprocess, sys, tempfile

SRC = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC") or os.environ.get("REAPER_SRC", ""))
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree with httpd/web.c (argv[1] / REAPER_ROUTER_SRC / REAPER_SRC)"); sys.exit(77)
rd = lambda *p: open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

web = rd("httpd", "web.c")
def fn(sig, start=0):
    """a function definition from its signature line to its closing brace at column 0"""
    i = web.find(sig + "\n{", start)
    if i < 0:
        return ""
    j = web.find("\n}\n", i)
    return web[i:j + 3] if j > i else ""

MB, ME = "/* REAPER-AIMESH-MLO-BEGIN */", "/* REAPER-AIMESH-MLO-END */"
b0, b1 = web.find(MB), web.find(ME)
i_merge = web.find("static void rdev_merge_clientlist(struct json_object *clients, struct json_object *macArray)\n{")
i_mark = web.find("static void rdev_mark_mlo(struct json_object *clients)\n{")
i_cgi = web.find("static void do_reaper_dev_cgi(char *url, FILE *stream)\n{")
check("web.c: one marked block, after rdev_merge_clientlist, before rdev_mark_mlo and do_reaper_dev_cgi",
      web.count(MB) == 1 and web.count(ME) == 1 and 0 < i_merge < b0 < b1 < i_mark < i_cgi, (i_merge, b0, b1, i_mark, i_cgi))
BLK = web[b0:b1 + len(ME)] if 0 < b0 < b1 else ""
TAIL = web[b1 + len(ME):i_cgi] if 0 < b1 < i_cgi else ""     # RMLO_TAB_AGE + rmlo_link_cb + rdev_mark_mlo
check("web.c: rdev_mark_mlo declared once up top (the hook comes 20000 lines earlier)",
      web.count("static void rdev_mark_mlo(struct json_object *clients);") == 1
      and web.find("static void rdev_mark_mlo(struct json_object *clients);") < web.find("static int ej_get_clientlist(int eid"))

# ---------------------------------------------------------------- the hook: both modes
hook = fn("static int ej_get_clientlist(int eid, webs_t wp, int argc, char_t **argv)")
seq = ("\tif (rdev_nonrouting())\n\t\trdev_merge_clientlist(clients, macArray);\n\t/* reaper 2026-11-19 REAPER-AIMESH-MLO")
k_seq, k_call = hook.find(seq), hook.find("\n\trdev_mark_mlo(clients);\n\tjson_object_object_add(clients, \"maclist\", macArray);\n")
check("hook: rdev_mark_mlo(clients) runs in EVERY mode - at function level after the AP-only merge, not under its if",
      hook.count("rdev_mark_mlo(") == 1 and 0 < k_seq < k_call and "\t\trdev_mark_mlo(" not in hook, (k_seq, k_call))
check("hook: the mark is made before the reply is written and before the networkmap cache file is saved",
      0 < k_call < hook.find('websWrite(wp, "%s", json_object_to_json_string(clients));\n\n\tjson_object_to_file(NMP_CACHE_FILE, clients);'))

# ---------------------------------------------------------------- rdev_mark_mlo: cached sources only
MARK = fn("static void rdev_mark_mlo(struct json_object *clients)")
body = MARK[MARK.find("{"):]
check("rdev_mark_mlo: MLO off (or no list) returns before anything else",
      re.search(r"\{\n\tstatic struct rmlo_set s;[^\n]*\n\ttime_t now = time\(NULL\);\n\tint i;\n\n\tif \(!clients \|\| !rdev_mlo_active\(\)\)\n\t\treturn;\n\trmlo_reset\(&s\);", body) is not None, body[:300])
check("rdev_mark_mlo: never collects - no rdev_snapshot / rdev_collect / popen / wl / file open of its own",
      body != "" and not re.search(r"\b(rdev_snapshot|rdev_collect|rdev_scan_\w+|popen|system|fopen|eval|_eval|doSystem)\s*\(", body)
      and '"wl ' not in body and "nvram_" not in body)
check("rdev_mark_mlo: reads the device table only when it was built with MLO on and is at most RMLO_TAB_AGE old",
      "#define RMLO_TAB_AGE 60" in TAIL
      and "if (rdev_tab_t && rdev_tab_mlo && now >= rdev_tab_t && now - rdev_tab_t <= RMLO_TAB_AGE)" in body
      and "if (rdev_tab[i].mlo && !rdev_tab[i].node && !rdev_tab[i].bh_sta)" in body)
check("rdev_mark_mlo: cfg_mnt fold through the shared cache walker, then sort, then mark",
      0 < body.find("rdev_amesh_mld_walk(rmlo_link_cb, &s);") < body.find("rmlo_finish(&s);") < body.find("rmlo_mark_rows(clients, &s);"))
LCB = fn("static void rmlo_link_cb(const char *link, const char *mld, void *arg)")
check("rmlo_link_cb: the rdev_scan_wl fold rule - a well-formed randomized link naming ANOTHER MAC",
      "if (!link || !mld || strlen(link) != 17 || !rdev_is_rand(link) || !strcasecmp(link, mld))\n\t\treturn;" in LCB
      and 0 < LCB.find("rmlo_add_link(s, link, mld);") < LCB.find("rmlo_add_dev(s, mld);"))

# ---------------------------------------------------------------- the block: host-only code
check("block: json-c and libc only (no nvram, no command, no file, no networkmap table, no websWrite)",
      BLK != "" and not re.search(r"\b(nvram_\w+|popen|system|fopen|open|eval|websWrite|rdev_snapshot|rdev_collect|shmat)\s*\(", BLK)
      and "p_client_info_tab" not in BLK and "CLIENT_DETAIL_INFO" not in BLK)
check("block: only ever WRITES \"1\" into \"mlo\" - no delete, no other key, no row added",
      BLK.count("json_object_object_add(") == 1 and 'json_object_object_add(row, "mlo", json_object_new_string("1"));' in BLK
      and "json_object_object_del" not in BLK and "json_object_array_add" not in BLK)
check("block: a row that already says \"1\" is skipped; non-object values are skipped",
      'if (cur && !strcmp(cur, "1"))\n\t\t\t\tcontinue;' in BLK
      and "if (!row || !json_object_is_type(row, json_type_object) || !rmlo_hit(s, key))" in BLK)
check("block: MACs need the 17-char shape (ether_atoe takes junk) and are compared uppercased",
      "if ((i % 3 == 2) ? (c != ':') : !isxdigit(c))" in BLK and "out[i] = (char)toupper(c);" in BLK)
check("block: the tables are bounded (RMLO_MAX) and the set is static, off httpd's stack",
      "if (s->ndev < RMLO_MAX && rmlo_norm(mac, s->dev[s->ndev]))" in BLK
      and "if (s->nlink < RMLO_MAX && rmlo_norm(link, s->link[s->nlink][0]) && rmlo_norm(dev, s->link[s->nlink][1]))" in BLK
      and "\tstatic struct rmlo_set s;" in MARK)

# ---------------------------------------------------------------- AP mode: the existing-row branch
merge = fn("static void rdev_merge_clientlist(struct json_object *clients, struct json_object *macArray)")
r0 = merge.find("if (json_object_object_get_ex(clients, d->mac, &row) && row) {")
r1 = merge.find("\t\t\tcontinue;\n\t\t}", r0)
raise_ln = ('\t\t\tif (rdev_tab_mlo && d->mlo && (!json_object_object_get_ex(row, "mlo", &o) || !o || !(s = json_object_get_string(o)) || strcmp(s, "1")))\n'
            '\t\t\t\tjson_object_object_add(row, "mlo", json_object_new_string("1"));\n')
check("AP merge: a row networkmap already has gets the same raise (inside the existing-row branch)",
      0 < r0 < merge.find(raise_ln) < r1 and merge.count(raise_ln) == 1, (r0, merge.find(raise_ln), r1))
check("AP merge: still takes the cached snapshot and still adds its own rows with d->mlo",
      "rdev_snapshot(RDEV_TTL);" in merge and 'json_object_object_add(row, "mlo", json_object_new_string(d->mlo ? "1" : "0"));' in merge)

# ---------------------------------------------------------------- one MLO-on rule; the shared cache
coll = fn("static void rdev_collect(void)")
act = fn("static int rdev_mlo_active(void)")
check("one MLO-on rule: rdev_collect calls rdev_mlo_active(), which keeps mld_enable + an mldN_ifnames",
      "\tmlo_on = rdev_mlo_active();\n" in coll and 'mlo_on = (nvram_match("mld_enable"' not in web
      and 'nvram_match("mld_enable", "1")' in act and all('*nvram_safe_get("mld%d_ifnames")' % u in act for u in range(3))
      and 0 < web.find("static int rdev_mlo_active(void)\n{") < web.find("static void rdev_collect(void)\n{"))
cache = fn("static json_object *rdev_amesh_wl_cache(void)")
mldof = fn("static int rdev_amesh_mld_of(const char *linkmac, char *out, size_t n)")
walk = fn("static void rdev_amesh_mld_walk(void (*cb)(const char *link, const char *mld, void *arg), void *arg)")
check("cfg_mnt cache: re-read only on mtime/size change, under cfg_mnt's lock, non-object dropped",
      "if (!cache || st.st_mtime != cmtime || st.st_size != csize) {" in cache and "int lock = file_lock(ALLWEVENT_FILE_LOCK);" in cache
      and "if (cache && !json_object_is_type(cache, json_type_object)) {" in cache and "\treturn cache;\n}" in cache)
check("rdev_amesh_mld_of keeps its checks and uses the shared cache",
      "if (!out || n < 18) return 0;" in mldof and "if (!linkmac || strlen(linkmac) != 17) return 0;" in mldof
      and "if ((cache = rdev_amesh_wl_cache()) == NULL) return 0;" in mldof and "json_object_from_file" not in mldof)
check("walker: same cache, type-guarded at every level, passes only stations with a well-formed mld_mac",
      "json_object *cache = rdev_amesh_wl_cache();" in walk and walk.count("json_type_object)) continue;") == 2
      and "const char *mld = rdev_sta_mldmac(staval);" in walk and "if (mld) cb(stamac, mld, arg);" in walk
      and "json_object_from_file" not in walk)
els = web[web.find("#else\nstatic void rdev_scan_amesh(struct rdev *v, int *n)"):web.find("#endif\t/* RTCONFIG_CFGSYNC */")]
check("without AiMesh sync: a no-op walker stub sits in the #else",
      "static void rdev_amesh_mld_walk(void (*cb)(const char *link, const char *mld, void *arg), void *arg)\n{ (void)cb; (void)arg; }" in els)
check("networkmap's row is still built from its own table field (no struct touched)",
      'snprintf(mlo, sizeof(mlo), "%d", p_client_info_tab->mlo[i]);' in web)
new_c = BLK + TAIL + cache + walk + act
check("new C is ASCII", all(ord(c) < 128 for c in new_c))
bad_c = [m.group(0)[:60] for m in re.finditer(r"/\*(?:[^*]|\*(?!/))*\*/", new_c) if "/*" in m.group(0)[2:]]
check("no comment opener inside a comment in the new C", not bad_c, bad_c)

# ---------------------------------------------------------------- gcc + in-tree json-c: run it
gcc = shutil.which("gcc")
jsonc = os.path.join(SRC, "json-c")
jsrc = [os.path.join(jsonc, f) for f in ("json_object.c", "json_tokener.c", "json_util.c", "linkhash.c", "arraylist.c",
                                         "printbuf.c", "debug.c", "random_seed.c", "json_c_version.c", "json_object_iterator.c")]
s0 = web.find("struct rdev {\n"); RDEV = web[s0:web.find("\n};\n", s0) + 4] if s0 > 0 else ""
RAND = fn("static int rdev_is_rand(const char *mac)")
MLDMAC = fn("static const char *rdev_sta_mldmac(json_object *staval)")
if not (gcc and sys.platform.startswith("linux") and all(os.path.isfile(p) for p in jsrc)):
    print("note: gcc or the in-tree json-c sources absent - run skipped, source pins above stand")
elif not (BLK and TAIL and walk and RDEV and RAND and MLDMAC):
    check("the pieces to compile were all found", False, [bool(x) for x in (BLK, TAIL, walk, RDEV, RAND, MLDMAC)])
else:
    harness = r'''#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <time.h>
#include "json.h"
''' + RDEV + r'''
static struct rdev rdev_tab[700];
static int rdev_tab_n = 0, rdev_tab_mlo = 0;
static time_t rdev_tab_t = 0;
static int g_mlo_on = 1;
static json_object *g_cache = NULL;
static int rdev_mlo_active(void) { return g_mlo_on; }
static json_object *rdev_amesh_wl_cache(void) { return g_cache; }
''' + RAND + "\n" + MLDMAC + "\n" + walk + "\n" + BLK + "\n" + TAIL + r'''
static int bad;
#define NM "{\"00:00:5E:00:53:01\":{\"sdn_idx\":\"0\",\"mlo\":\"0\",\"type\":\"0\",\"mac\":\"00:00:5E:00:53:01\",\"isWL\":\"5\",\"isOnline\":\"1\"}," \
 "\"00:00:5E:00:53:02\":{\"mlo\":\"0\",\"mac\":\"00:00:5E:00:53:02\",\"isWL\":\"2\"}," \
 "\"00:00:5E:00:53:03\":{\"mlo\":\"1\",\"mac\":\"00:00:5E:00:53:03\"}," \
 "\"00:00:5E:00:53:04\":{\"mlo\":\"0\",\"mac\":\"00:00:5E:00:53:04\"}," \
 "\"06:00:5E:00:53:44\":{\"mlo\":\"0\",\"mac\":\"06:00:5E:00:53:44\"}," \
 "\"00:00:5E:00:53:05\":{\"mac\":\"00:00:5E:00:53:05\",\"name\":\"no mlo field \\\"q\\\"\"}," \
 "\"00:00:5e:00:53:06\":{\"mlo\":\"0\",\"mac\":\"00:00:5e:00:53:06\"}," \
 "\"00:00:5E:00:53:07\":{\"mlo\":\"0\",\"mac\":\"00:00:5E:00:53:07\"}," \
 "\"00:00:5E:00:53:08\":{\"mlo\":\"0\"},\"00:00:5E:00:53:09\":{\"mlo\":\"0\"},\"0A:00:5E:00:53:0A\":{\"mlo\":\"0\"}," \
 "\"zz:zz:zz:zz:zz:zz\":{\"mlo\":\"0\"},\"maclist\":[\"00:00:5E:00:53:01\"],\"ClientAPILevel\":\"2\"}"
/* cfg_mnt: node -> band -> link station {mld_mac}; lowercase on purpose */
#define CFG "{\"00:00:5E:00:53:F0\":{\"6G\":{\"06:00:5e:00:53:44\":{\"mld_mac\":\"00:00:5e:00:53:04\"}," \
 "\"00:00:5E:00:53:08\":{\"mld_mac\":\"00:00:5E:00:53:09\"},\"0A:00:5E:00:53:0A\":{\"mld_mac\":\"0A:00:5E:00:53:0A\"}," \
 "\"0E:00:5E:00:53:0E\":{\"mld_mac\":\"short\"},\"0E:00:5E:00:53:0F\":{\"mld_mac\":5}},\"2G\":[1]},\"x\":3}"
static void dev(const char *mac, int mlo, int node)
{ struct rdev *d = &rdev_tab[rdev_tab_n++]; memset(d, 0, sizeof(*d)); snprintf(d->mac, sizeof(d->mac), "%s", mac); d->mlo = mlo; d->node = node; }
static void table(void)
{ rdev_tab_n = 0; dev("00:00:5E:00:53:01", 1, 0); dev("00:00:5E:00:53:02", 0, 0); dev("00:00:5E:00:53:05", 1, 0);
  dev("00:00:5E:00:53:06", 1, 0); dev("00:00:5E:00:53:07", 1, 512); rdev_tab_mlo = 1; rdev_tab_t = time(NULL); }
static const char *mlo_of(json_object *c, const char *k)
{ json_object *r = NULL, *o = NULL; if (!json_object_object_get_ex(c, k, &r) || !json_object_object_get_ex(r, "mlo", &o)) return "-"; return json_object_get_string(o); }
/* the marks, as one string "0123..." over the fixture rows ('-' = field absent) */
static void marks(json_object *c, char *out)
{ static const char *k[] = { "00:00:5E:00:53:01", "00:00:5E:00:53:02", "00:00:5E:00:53:03", "00:00:5E:00:53:04", "06:00:5E:00:53:44",
  "00:00:5E:00:53:05", "00:00:5e:00:53:06", "00:00:5E:00:53:07", "00:00:5E:00:53:08", "00:00:5E:00:53:09", "0A:00:5E:00:53:0A", "zz:zz:zz:zz:zz:zz" };
  int i; for (i = 0; i < 12; i++) out[i] = mlo_of(c, k[i])[0]; out[12] = 0; }
static void run(const char *name, const char *want, int same)
{
	json_object *c = json_tokener_parse(NM);
	char before[4096], got[16];
	snprintf(before, sizeof(before), "%s", json_object_to_json_string(c));
	rdev_mark_mlo(c);
	marks(c, got);
	if (strcmp(got, want)) { printf("%s: marks %s, want %s\n", name, got, want); bad++; }
	if (same && strcmp(before, json_object_to_json_string(c))) { printf("%s: output changed\n", name); bad++; }
	json_object_put(c);
}
int main(int argc, char **argv)
{
	json_object *c, *r;
	char a[4096], b[4096], got[16];
	(void)argc; (void)argv;
	g_cache = json_tokener_parse(CFG);
	if (!g_cache || !json_tokener_parse(NM)) { puts("fixture parse"); return 2; }

	/* 1. the whole mark: table + cfg_mnt fold, MACs in any case */
	table(); g_mlo_on = 1;
	c = json_tokener_parse(NM);
	snprintf(a, sizeof(a), "%s", json_object_to_json_string(c));
	rdev_mark_mlo(c);
	marks(c, got);
	/* 01 table -> 1 | 02 not MLO | 03 networkmap 1 kept | 04 mld of a cfg_mnt link | 44 the link row itself |
	   05 field absent -> inserted | 06 lowercase key | 07 a node | 08/09 global link (not folded) | 0A link==mld | junk */
	if (strcmp(got, "101111100000")) { printf("marks %s want 101111100000\n", got); bad++; }
	r = NULL; json_object_object_get_ex(c, "00:00:5E:00:53:01", &r);
	if (strcmp(json_object_to_json_string(r), "{ \"sdn_idx\": \"0\", \"mlo\": \"1\", \"type\": \"0\", \"mac\": \"00:00:5E:00:53:01\", \"isWL\": \"5\", \"isOnline\": \"1\" }"))
		{ printf("replace not in place / other field touched: %s\n", json_object_to_json_string(r)); bad++; }
	r = NULL; json_object_object_get_ex(c, "00:00:5E:00:53:05", &r);
	if (strcmp(json_object_to_json_string(r), "{ \"mac\": \"00:00:5E:00:53:05\", \"name\": \"no mlo field \\\"q\\\"\", \"mlo\": \"1\" }"))
		{ printf("insert: %s\n", json_object_to_json_string(r)); bad++; }
	if (json_object_object_length(c) != 14) { puts("a row was added or removed"); bad++; }
	printf("OUT %s\n", json_object_to_json_string(c));
	snprintf(b, sizeof(b), "%s", json_object_to_json_string(c));
	rdev_mark_mlo(c);	/* a second pass changes nothing */
	if (strcmp(b, json_object_to_json_string(c))) { puts("second pass changed the output"); bad++; }
	printf("IN  %s\n", a);
	json_object_put(c);

	/* the fixture as given ('-' = 05 has no field): "00100-000000" */
	/* 2. MLO off: byte-identical, whatever the table and cfg_mnt say */
	g_mlo_on = 0; run("MLO off", "00100-000000", 1);
	g_mlo_on = 1;
	/* 3. table older than RMLO_TAB_AGE: only the cfg_mnt fold (04 and its link row) */
	table(); rdev_tab_t = time(NULL) - RMLO_TAB_AGE - 1; run("stale table", "00111-000000", 0);
	/* 4. table built while MLO was off: only the cfg_mnt fold */
	table(); rdev_tab_mlo = 0; run("table MLO off", "00111-000000", 0);
	/* 5. no table yet (router mode, nothing polled the Devices page) and no cfg_mnt list: byte-identical */
	rdev_tab_t = 0; json_object_put(g_cache); g_cache = NULL; run("no sources", "00100-000000", 1);
	/* 6. table only: 01, 05 (inserted), 06 (lowercase key); the node 07 is not a client */
	table(); run("table only", "101001100000", 0);
	/* 7. cfg_mnt shapes the walker must skip (non-object node / band values): byte-identical */
	rdev_tab_t = 0; g_cache = json_tokener_parse("{\"a\":[1],\"b\":{\"6G\":3,\"5G\":{\"06:00:5E:00:53:44\":7}}}");
	run("odd cfg_mnt shapes", "00100-000000", 1);
	json_object_put(g_cache); g_cache = NULL;

	/* 8. norm: the 17-char shape only */
	{ char o[18]; const char *junk[] = { "zz:zz:zz:zz:zz:zz", "00-00-5E-00-53-01", "00:00:5E:00:53:01x", "00:00:5E:00:53:0", "", "000:0:5E:00:53:01", "00:00:5E:00:53:0G", NULL };
	  int i; for (i = 0; junk[i]; i++) if (rmlo_norm(junk[i], o)) { printf("norm took [%s]\n", junk[i]); bad++; }
	  if (!rmlo_norm("0a:bc:de:f0:12:34", o) || strcmp(o, "0A:BC:DE:F0:12:34")) { puts("norm upper"); bad++; }
	  if (rmlo_norm(NULL, o)) { puts("norm NULL"); bad++; } }
	/* 9. bounded: more devices than RMLO_MAX are refused, never written past the table */
	{ static struct rmlo_set s; int i; char m[18];
	  rmlo_reset(&s);
	  for (i = 0; i < 700; i++) { snprintf(m, sizeof(m), "00:00:5E:00:%02X:%02X", i >> 8, i & 255); rmlo_add_dev(&s, m); rmlo_add_link(&s, m, m); }
	  if (s.ndev != RMLO_MAX || s.nlink != RMLO_MAX) { printf("cap %d %d\n", s.ndev, s.nlink); bad++; }
	  rmlo_finish(&s);
	  if (!rmlo_hit(&s, "00:00:5e:00:01:ff") || rmlo_hit(&s, "00:00:5E:00:02:00")) { puts("hit after cap"); bad++; } }
	/* 10. cost: a full table (RMLO_MAX devices + RMLO_MAX links) against 512 networkmap rows */
	{ json_object *big = json_object_new_object(); int i, it, n = 0; char m[18]; struct timespec t0, t1; double us;
	  rdev_tab_n = 0;
	  for (i = 0; i < 512; i++) { json_object *row = json_object_new_object(); snprintf(m, sizeof(m), "00:00:5E:00:%02X:%02X", i >> 8, i & 255);
	    json_object_object_add(row, "mlo", json_object_new_string("0")); json_object_object_add(big, m, row); if (i % 2 == 0) dev(m, 1, 0); }
	  rdev_tab_mlo = 1; rdev_tab_t = time(NULL);
	  g_cache = json_object_new_object();
	  { json_object *band = json_object_new_object(), *node = json_object_new_object();
	    for (i = 0; i < 256; i++) { json_object *st = json_object_new_object(); char l[18], d[18];
	      snprintf(l, sizeof(l), "02:00:5E:01:%02X:%02X", i >> 8, i & 255); snprintf(d, sizeof(d), "00:00:5E:00:%02X:%02X", (i * 2 + 1) >> 8, (i * 2 + 1) & 255);
	      json_object_object_add(st, "mld_mac", json_object_new_string(d)); json_object_object_add(band, l, st); }
	    json_object_object_add(node, "6G", band); json_object_object_add(g_cache, "00:00:5E:00:53:F0", node); }
	  clock_gettime(CLOCK_MONOTONIC, &t0);
	  for (it = 0; it < 200; it++) rdev_mark_mlo(big);
	  clock_gettime(CLOCK_MONOTONIC, &t1);
	  us = ((t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3) / 200;
	  { json_object_object_foreach(big, k, v) { json_object *o = NULL; (void)k; if (json_object_object_get_ex(v, "mlo", &o) && !strcmp(json_object_get_string(o), "1")) n++; } }
	  if (n != 512) { printf("cost fixture: %d of 512 rows marked\n", n); bad++; }
	  printf("COST %.1f us per hook call (host x86; 256 table devices + 256 cfg_mnt links, 512 rows)\n", us);
	  json_object_put(big); json_object_put(g_cache); g_cache = NULL; }
	return bad ? 1 : 0;
}
'''
    td = tempfile.mkdtemp(prefix="aimeshmlo_")
    try:
        cs, ob, bn = os.path.join(td, "h.c"), os.path.join(td, "h.o"), os.path.join(td, "h")
        open(cs, "w").write(harness)
        p = subprocess.run([gcc, "-std=gnu99", "-Wall", "-Werror", "-Wno-unused-function", "-O1", "-I", jsonc, "-c", "-o", ob, cs],
                           capture_output=True, text=True)
        check("the lifted code compiles on the host (-Wall -Werror) against the in-tree json-c", p.returncode == 0, p.stderr[:1500])
        if p.returncode == 0:
            p = subprocess.run([gcc, "-w", "-I", jsonc, "-o", bn, ob] + jsrc + ["-lm"], capture_output=True, text=True)
            check("links with json-c", p.returncode == 0, p.stderr[:800])
        if p.returncode == 0:
            p = subprocess.run([bn], capture_output=True, text=True, timeout=60)
            lines = p.stdout.splitlines()
            errs = [l for l in lines if not l.startswith(("OUT ", "IN  ", "COST "))]
            check("fixture: table + cfg_mnt fold + any-case MACs marked; non-MLO, node, global and self links, junk "
                  "left; an existing 1 kept; replace in place, insert appended; no row added; second pass idempotent; "
                  "MLO off / no sources byte-identical; stale or MLO-off table ignored; 17-char MACs only; bounded",
                  p.returncode == 0 and not errs, errs or p.stderr[:400])
            out = [l[4:] for l in lines if l.startswith("OUT ")]
            inp = [l[4:] for l in lines if l.startswith("IN  ")]
            try:
                jo, ji = json.loads(out[0]), json.loads(inp[0])
                diff = sorted(k for k in ji if ji[k] != jo.get(k))
                other = [k for k in diff if {kk: vv for kk, vv in jo[k].items() if kk != "mlo"} != {kk: vv for kk, vv in ji[k].items() if kk != "mlo"}]
                check("the marked reply is valid JSON, same keys, only \"mlo\" differs, on exactly the 5 MLO rows",
                      list(jo) == list(ji) and other == [] and diff == ["00:00:5E:00:53:01", "00:00:5E:00:53:04", "00:00:5E:00:53:05",
                                                                         "00:00:5e:00:53:06", "06:00:5E:00:53:44"]
                      and all(jo[k]["mlo"] == "1" for k in diff), (diff, other))
            except Exception as e:
                check("the marked reply is valid JSON", False, e)
            cost = [l for l in lines if l.startswith("COST ")]
            if cost:
                print("note: " + cost[0])
    finally:
        shutil.rmtree(td, ignore_errors=True)

if fails:
    print("\nFAILED %d:" % len(fails))
    for f in fails: print("  - " + f)
    sys.exit(1)
print("PASS: the AiMesh tab gets the MLO flag Reaper knows, in router and AP mode, from cached sources only")
sys.exit(0)
