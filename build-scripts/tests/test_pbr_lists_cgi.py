#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reaper_pbr.cgi action=lists: the status of the fetched lists, as JSON (REAPER-FW-LISTS, 2026-11-22).

WHY. /tmp/reaper_fw/lists.status is written by a root script that has just read downloaded data, and httpd prints
it into a JSON reply the Policy Routing page evaluates. A word that carried a quote, a bracket or markup would
break the reply or reach the page. Every field is checked again in httpd; this test compiles the real functions
and feeds them a good file, a hostile file, an over-long file and no file.
Exit 0 pass, 1 fail, 77 skipped (no compiler or no router source: pass release/src/router or set REAPER_ROUTER_SRC).
"""
import json, os, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")):
    print("SKIP: no router source tree"); sys.exit(77)
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    print("SKIP: no host C compiler"); sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def extract(src, signature):
    i = src.index(signature); j = src.index("{", i); depth = 0; k = j
    while k < len(src):
        if src[k] == "{": depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0: return src[i:k + 1]
        k += 1
    raise ValueError("unbalanced braces after " + signature)

web = open(os.path.join(SRC, "httpd", "web.c"), encoding="utf-8", errors="surrogateescape").read()
if "rpbr_lists_json" not in web:
    print("SKIP: this tree has no fetched lists"); sys.exit(77)
td = tempfile.mkdtemp(prefix="pbrcgi-")
try:
    stf = os.path.join(td, "lists.status"); runf = os.path.join(td, "lists.run"); scf = os.path.join(td, "lists.sh")
    STUB = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <unistd.h>
#include <sys/stat.h>
#define websWrite fprintf
#define RPBR_LISTS_STATUS "%s"
#define RPBR_LISTS_RUN "%s"
#define RPBR_LISTS_SCRIPT "%s"
#define RPBR_LISTS_LINES 256
''' % (stf, runf, scf)
    parts = [STUB] + [extract(web, s) for s in ("static int rpbr_word_ok(", "static int rpbr_lists_split(", "static void rpbr_lists_json(")]
    parts.append("int main(void) { rpbr_lists_json(stdout); return 0; }\n")
    c = os.path.join(td, "w.c"); x = os.path.join(td, "w")
    with open(c, "w") as fh: fh.write("\n".join(parts))
    r = subprocess.run([CC, "-std=gnu99", "-w", "-o", x, c], capture_output=True, text=True)
    check("the real functions compile on the host", r.returncode == 0, r.stderr[:1500])
    if r.returncode != 0:
        raise SystemExit
    def run(text=None, running=False, script=True):
        for p in (stf, runf, scf):
            if os.path.exists(p): os.unlink(p)
        if text is not None:
            with open(stf, "w") as fh: fh.write(text)
        if running: open(runf, "w").close()
        if script: open(scf, "w").close()
        out = subprocess.run([x], capture_output=True, text=True).stdout
        try: return json.loads(out), out
        except ValueError: return None, out

    GOOD = ("T|1795000000|update\n"
            "K|as2906|ipverse|1794990000|16|7|1795000000|ok|ok|-|-\n"
            "K|cc_nl|warden|1794990001|5731|0|1795000001|fail|empty|conn|http\n"
            "O|netflix|asn|ok|16|ok|7\n"
            "O|nl_list|geo|big|300000|none|0\n")
    j, raw = run(GOOD, running=True)
    check("a good status file gives valid JSON with the time, the running flag and the script flag",
          j is not None and j["ok"] == 1 and j["t"] == 1795000000 and j["running"] == 1 and j["script"] == 1 and j["now"] > 1700000000, raw)
    check("saved lists: name, source, counts as numbers, the last check and what each source said",
          j and j["keys"] == [{"k": "as2906", "src": "ipverse", "chg": 1794990000, "n4": 16, "n6": 7, "chk": 1795000000, "res": "ok", "e": ["ok", "-", "-"]},
                              {"k": "cc_nl", "src": "warden", "chg": 1794990001, "n4": 5731, "n6": 0, "chk": 1795000001, "res": "fail", "e": ["empty", "conn", "http"]}], raw)
    check("objects: name, kind, state and loaded count per family",
          j and j["objs"] == [{"n": "netflix", "kind": "asn", "s4": "ok", "c4": 16, "s6": "ok", "c6": 7},
                              {"n": "nl_list", "kind": "geo", "s4": "big", "c4": 300000, "s6": "none", "c6": 0}], raw)
    BAD = ("T|1795000000|update\n"
           'K|as1|ip"verse|1|1|1|1|ok|ok|-|-\n'
           "K|as2|<script>|1|1|1|1|ok|ok|-|-\n"
           "K|as3|ipverse|1|1|1|1|ok|ok|-\n"                      # a field short
           "K|as4|ipverse|1|1|1|1|ok|ok|-|-|extra\n"              # a field too many
           "K|" + "a" * 40 + "|ipverse|1|1|1|1|ok|ok|-|-\n"       # a word too long
           "K|as5|ipverse||1|1|1|ok|ok|-|-\n"                     # an empty field
           "K|as6|ip verse|1|1|1|1|ok|ok|-|-\n"
           "K|as7|ipverse|1|1|1|1|ok|ok|-|\\\n"
           "O|x1|asn|ok|1|ok\n"
           'O|x2|asn|ok|1|ok|1"}],"x":[{\n'
           "K|as9|ipverse|12abc|3|4|5|ok|ok|-|-\n"                # a count that is not a number prints as its leading digits
           "junk line\n"
           "O|good|asn|ok|2|none|0\n")
    j, raw = run(BAD)
    check("a hostile status file still gives valid JSON", j is not None, raw)
    check("every line with a field that is not a plain word, or with the wrong number of fields, is left out",
          j and [k["k"] for k in j["keys"]] == ["as9"] and [o["n"] for o in j["objs"]] == ["good"], raw)
    check("no quote, bracket or markup from the file reaches the reply", '<' not in raw and 'ip"verse' not in raw and '"x":' not in raw, raw)
    check("a count is always printed as a number", j and j["keys"][0]["chg"] == 12, raw)
    j, raw = run("T|5|fill\n" + "".join("K|as%d|ipverse|1|1|1|1|ok|ok|-|-\n" % i for i in range(1000)))
    check("an over-long file is cut at 256 lines", j is not None and len(j["keys"]) == 255, len(j["keys"]) if j else raw[:200])
    j, raw = run(None, script=False)
    check("no status file: empty lists, not running, no script", j == {"ok": 1, "t": 0, "now": j["now"], "running": 0, "script": 0, "keys": [], "objs": []} if j else False, raw)
    check("the update verb asks rc and refuses when there is no script (source)",
          'notify_rc("start_reaper_fw_lists");' in web and 'if (access(RPBR_LISTS_SCRIPT, F_OK) != 0) {' in web and "E_NOLISTS" in web)
    check("both verbs sit behind the request-token gate of the handler (source order)",
          web.index("int why = reaper_gate();", web.index("\ndo_reaper_pbr_cgi(char *url, FILE *stream)")) < web.index('if (strcmp(action, "lists") == 0) {') < web.index('if (strcmp(action, "lists_update") == 0) {'))
finally:
    shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
