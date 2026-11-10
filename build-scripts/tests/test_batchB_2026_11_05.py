#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code-review batch B (2026-11-05): the netfilter fork storms (CODE-REVIEW-2026-08-18 section 2.1) and the
do_reaper_conn_cgi nested scan. Owner-approved; deferred until now only for blast radius, so the bar is "the same
result, provably".

WHAT CHANGED.
  Warden (rc/rwarden.c). The build was already one iptables-restore --noflush payload per stack (2026-09-28). What
  was left: TWO teardowns per arm - start_rwarden() -> stop_rwarden() tore the chains down from C (36 doSystem()
  calls, one shell each) and apply.sh then tore them down again with a byte-identical loop. Now the loop is ONE
  macro (RW_SH_TEARDOWN) that apply.sh emits and rw_teardown_rules() runs through one sh; start_rwarden() keeps the
  chains (rw_stop(0)) when apply.sh runs at once and tears down after a deferred/failed apply.
  Gatekeeper (rc/gatekeeper.c). The build was one iptables process per rule. It now uses Warden's idiom per stack
  AND table (filter: REAPER_GKF/GKI, nat: REAPER_GKN): a shim collects -N/-A, _gk_commit hands each payload to
  <tool>-restore --noflush, and a refused payload is replayed rule by rule through _rt_add (the old path, so a bad
  rule still fails alone, logged and counted in failcount). ebtables stays per rule. start_gk() has the same single
  teardown as Warden.
  httpd (web.c do_reaper_conn_cgi). The conntrack TCP table is sorted once (s, sp, d, dp, line order) and each flow
  does two binary searches; the lower line order wins, which is the row the old front-to-back scan met first. The
  conntrack read stays outside the single-flight lock, and the comment says why.

WHAT THIS PINS.
  (A) the source shapes above;
  (B) on the host, with the real generators compiled against a stateful netfilter/ipset model (every chain of
      filter+nat, v4+v6, ebtables, ipset; rule validity incl. missing ipsets and missing jump targets):
      - each generated apply.sh three ways - per rule (the batch shim stripped = the pre-batch script), batched,
        and batched with every restore refused (the fallback) - must leave the SAME state, for several Warden and
        Gatekeeper configurations, including a rule the kernel rejects (one bad line: batch refused -> fallback);
      - the start/stop flows: start+start == start+stop+start (the old double-teardown sequence), a deferred
        apply leaves no chain, stop leaves no chain, restart keeps the jump positions;
      - the batched build spawns far fewer iptables processes than the per-rule one;
  (C) do_reaper_conn_cgi: the real handler vs the same handler with the old linear scan put back, byte for byte,
      on a fixture with duplicate tuples and reverse-direction rows; and a mutant that prefers the reply-direction
      row must DIFFER (so the fixture really exercises the tie-break).
Exit 0 pass, 1 fail, 77 skipped (no router tree; (B)/(C) also need gcc and dash on Linux).
"""
import fcntl, json, os, random, re, shutil, subprocess, sys, tempfile

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not src_root or not os.path.isfile(os.path.join(src_root, "rc", "rwarden.c")):
    print("SKIP: no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
    sys.exit(77)

FAILS = []


def check(name, cond, detail=""):
    print("%s %s%s" % ("ok  " if cond else "FAIL", name, ("  -- " + detail) if (detail and not cond) else ""))
    if not cond:
        FAILS.append(name)


def rd(rel):
    with open(os.path.join(src_root, rel), encoding="utf-8", errors="surrogateescape") as fh:
        return fh.read()


def sl(t, a, b=None):
    i = t.index(a)
    return t[i:] if b is None else t[i:t.index(b, i)]


rw = rd("rc/rwarden.c")
gk = rd("rc/gatekeeper.c")
web = rd("httpd/web.c")

# ------------------------------------------------------------------ (A) source pins
print("== (A) source")
td = sl(rw, "#define RW_SH_TEARDOWN", "static void rw_teardown_rules(void)")
check("Warden: one teardown text (RW_SH_TEARDOWN) - both stacks, front-chain + legacy jumps, all six chains",
      all(x in td for x in ('"for T in iptables ip6tables; do\\n"', 'REAPER_HOOK_IN " -j REAPER_WARDEN',
                            'REAPER_HOOK_FWD " -j REAPER_WARDEN', 'REAPER_HOOK_OUT " -j RW_SELF',
                            "-D INPUT -j REAPER_WARDEN", "-D FORWARD -j REAPER_WARDEN", "-D OUTPUT -j RW_SELF",
                            "$T -X REAPER_WARDEN", "$T -X RW_SELF", "$T -X RW_OUT", "$T -X RW_SDROP",
                            "$T -X RW_ODROP", "$T -X RW_DROP")) and "%" not in td)
check("Warden: rw_teardown_rules() runs it through ONE sh (no per-command doSystem)",
      "static void rw_teardown_rules(void)\n{\n\tsystem(RW_SH_TEARDOWN);\n}" in rw and 'doSystem("while %s -D' not in rw)
ga = sl(rw, "static void rw_gen_apply(void)", "/* The updater: fetches")
check("Warden: apply.sh emits the same text, after the set replay and before the batched build",
      "fputs(RW_SH_TEARDOWN, f);" in ga and ga.index("rw_emit_cidrs(f, \"rw_ban\"") < ga.index("fputs(RW_SH_TEARDOWN, f);")
      < ga.index("fputs(RW_SH_BATCH_BEGIN, f);") < ga.index("fputs(RW_SH_BATCH_COMMIT, f);") < ga.index("REAPER_HOOK_RUN"))
st = sl(rw, "static void rw_stop(int teardown);", "/* 1 when the whitelist")
check("Warden: stop_rwarden() = rw_stop(1); the teardown is conditional only inside rw_stop",
      "void stop_rwarden(void)\n{\n\trw_stop(1);\n}" in st and "\tif (teardown)\n\t\trw_teardown_rules();\n" in st)
sr = sl(rw, "void start_rwarden(void)")
check("Warden: start keeps the chains only when apply.sh runs at once (routing, Warden on, a firewall build since boot)",
      'arm_now = is_routing_enabled() && nvram_match("rwarden_enable", "1") && f_exists(REAPER_FW_BUILT_MARK);' in sr
      and "rw_stop(!arm_now);" in sr and "stop_rwarden();" not in sr
      and sr.index("rw_stop(!arm_now);") < sr.index("rw_gen_apply();"))
check("Warden: a deferred / failed apply tears the kept chains down (the state stop-then-apply left)",
      'system("sh " RW_APPLY) != 0)) {' in sr and "\t\tif (arm_now)\n\t\t\trw_teardown_rules();\n\t\tlogmessage(\"rwarden\", \"LAN not ready at boot" in sr)

gm = sl(gk, "#define GK_SH_WRAPPERS", "static void gk_gen_apply(void)")
check("Gatekeeper: batch shim collects -N/-A per stack AND table, passes every other verb through",
      "_gkb() { _s=$1; _b=$2; shift 2; _t=filter; if [ \\\"$1\\\" = -t ]; then _t=$2; shift 2; fi;" in gm
      and "-N) echo \\\":$2 - [0:0]\\\" >> \\\"$GKB.$_s.$_t.h\\\";;" in gm and "-A) _gkq \\\"$GKB.$_s.$_t.r\\\" \\\"$@\\\";;" in gm
      and 'GKB=" GK_DIR "/batch' in gm)
check("Gatekeeper: one restore --noflush per stack and table; a refused payload is logged once and replayed via _rt_add",
      "/usr/sbin/$_b-restore --noflush <" in gm and "rebuild refused ($_e) - replaying rule by rule" in gm
      and 'eval \\"_rt_add /usr/sbin/$_b $_o $_r\\"' in gm
      and all(("\"_gk_commit %s\\n\"" % x) in gm for x in ("4 iptables filter", "4 iptables nat", "6 ip6tables filter", "6 ip6tables nat"))
      and gm.index("_gk_commit() {") < gm.index("GK_SH_WRAPPERS \\\n  \"_gk_commit 4"))
gg = sl(gk, "static void gk_gen_apply(void)", "static void gk_teardown_rules(void)")
check("Gatekeeper: shim after the teardown (and the sink reap), commit before the hooks (-I acts at once)",
      gg.index('"# ---- teardown ----\\n"') < gg.index("GK_SINK_KILL, gkifs, gknets);") < gg.index("fputs(GK_SH_BATCH_BEGIN, f);")
      < gg.index('fputs("# ---- build ----\\n"') < gg.index("fputs(GK_SH_BATCH_COMMIT, f);") < gg.index('"# ---- hooks ----\\n"'))
check("Gatekeeper: the header wrappers are GK_SH_WRAPPERS (ebtables keeps its own, per rule)",
      "\t  GK_SH_WRAPPERS\n\t  \"ebtables()  { case" in gg)
check("Gatekeeper: stop_gk() = gk_stop(1); start_gk() keeps the chains only when apply.sh runs at once",
      "void stop_gk(void)\n{\n\tgk_stop(1);\n}" in gk and "\tif (teardown)\n\t\tgk_teardown_rules();\n" in gk
      and 'int gk_arming = is_routing_enabled() && nvram_match("gk_enable", "1") && !f_exists("/jffs/reaper/restore_pending.json");' in gk
      and "\tgk_stop(!gk_arming);\n" in gk and "\tif (gk_apply_locked() != 0) {\n" in gk and "\t\tif (gk_arming)\n\t\t\tgk_teardown_rules();\n" in gk)

cg = sl(web, "static void\ndo_reaper_conn_cgi(char *url, FILE *stream)", "/* reaper v1.3.0: stream a collector snapshot")
check("httpd: the conntrack table is sorted once, OUTSIDE the lock, and the lock scope is explained",
      "qsort(ctv, (size_t)ctn, sizeof(*ctv), rconn_ct_cmp);" in cg and "WHY THE CONNTRACK READ IS OUTSIDE THE LOCK" in cg
      and cg.index("qsort(ctv") < cg.index('cf = open("/tmp/reaper/reaper_conn.lock"'))
check("httpd: each flow does two lookups, lower line order wins; no per-flow scan of the table",
      "rconn_ct_find(ctv, ctn, sN, (unsigned)sp, dN, (unsigned)dp)" in cg and "rconn_ct_find(ctv, ctn, dN, (unsigned)dp, sN, (unsigned)sp)" in cg
      and "if (fw && (!rv || fw->ix < rv->ix))" in cg and "for (k = 0; k < ctn; k++)" not in cg and "ctv[ctn].ix = ctn;" in cg)

# ------------------------------------------------------------------ (B)/(C) host harness
CC = shutil.which("gcc") or shutil.which("cc")
# dash, not busybox: busybox ash runs its own applets (logger, ip, ...) ahead of PATH, so the model's stubs
# would never see them. The generated scripts are plain POSIX sh.
SHB = shutil.which("dash")
if not CC or not SHB or not sys.platform.startswith("linux"):
    print("SKIP (B)/(C): need gcc and dash on Linux")
    sys.exit(1 if FAILS else 0)

W = tempfile.mkdtemp(prefix="bbh_")
STUB, ROOT = W + "/stub", W + "/root"
NFMODEL = r'''"""Batch B host harness: a small STATEFUL model of iptables / ip6tables / *-restore / ebtables / ipset, plus the
other tools the generated Warden / Gatekeeper scripts call. Every stub is a symlink to this file; argv[0] picks
the tool. Every invocation is appended to $NF_LOG (one JSON line: tool, args, stdin for restores), which is the
spawn record. The model state lives in $NF_STATE (JSON), guarded by an flock.

The model is the NORMALISER: per-command adds (-A/-I/-D/-N/-F/-X) and restore batches both land in the same
chain -> [rule tokens] structure, so the final rule list per chain can be compared directly.

Rules are stored as token lists exactly as the tool received them (after shell / iptables-restore parsing).
iptables-restore parsing follows iptables-1.4.x/iptables/iptables-restore.c (quote handling, empty params dropped,
a parameter starting with -t refused). Validity, per rule (per-command and in a restore): the chain exists, a -j/-g
target is a built-in target or an existing chain of the table, a --match-set names an existing ipset, no empty
token, no token from $NF_CONF "reject" for that family. A restore that meets an invalid line commits NOTHING of
that table (libiptc commits at COMMIT) and exits 1; tables committed before stay.
"""
import fcntl, json, os, sys

BUILTIN_TARGETS = {"ACCEPT", "DROP", "RETURN", "LOG", "REJECT", "DNAT", "SNAT", "MASQUERADE", "REDIRECT", "MARK",
                   "CONNMARK", "TCPMSS", "NFLOG", "QUEUE", "NFQUEUE", "CT", "NOTRACK", "SET", "logdrop", "logaccept"}
BUILTIN_CHAINS = {
    "filter": ["INPUT", "FORWARD", "OUTPUT"],
    "nat": ["PREROUTING", "INPUT", "OUTPUT", "POSTROUTING"],
}


def env(k, d=""):
    return os.environ.get(k, d)


def load_conf():
    p = env("NF_CONF")
    if p and os.path.exists(p):
        with open(p) as fh:
            return json.load(fh)
    return {}


def fresh_state():
    st = {"ipt": {}, "ebt": {"FORWARD": {"policy": "ACCEPT", "builtin": True, "rules": []},
                             "INPUT": {"policy": "ACCEPT", "builtin": True, "rules": []},
                             "OUTPUT": {"policy": "ACCEPT", "builtin": True, "rules": []}},
          "ipset": {}}
    for fam in ("4", "6"):
        st["ipt"][fam] = {}
        for tbl, chains in BUILTIN_CHAINS.items():
            st["ipt"][fam][tbl] = {c: {"policy": "ACCEPT", "builtin": True, "rules": []} for c in chains}
    return st


class Locked:
    def __enter__(self):
        self.lf = open(env("NF_STATE") + ".lock", "a+")
        fcntl.flock(self.lf, fcntl.LOCK_EX)
        p = env("NF_STATE")
        if os.path.exists(p) and os.path.getsize(p):
            with open(p) as fh:
                self.st = json.load(fh)
        else:
            self.st = fresh_state()
        return self

    def save(self):
        p = env("NF_STATE")
        with open(p + ".tmp", "w") as fh:
            json.dump(self.st, fh, indent=0, sort_keys=True)
        os.replace(p + ".tmp", p)

    def __exit__(self, *a):
        fcntl.flock(self.lf, fcntl.LOCK_UN)
        self.lf.close()


def record(tool, args, stdin=None):
    p = env("NF_LOG")
    if not p:
        return
    rec = {"tool": tool, "args": args}
    if stdin is not None:
        rec["stdin"] = stdin
    with open(p, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(rec) + "\n")
        fcntl.flock(fh, fcntl.LOCK_UN)


class Err(Exception):
    pass


# ---------------------------------------------------------------- iptables
def rule_check(conf, st, fam, tbl, chains, spec):
    if any(t == "" for t in spec):
        raise Err("empty parameter")
    joined = " ".join(spec)
    for f, sub in conf.get("reject", []):
        if f == fam and sub in joined:
            raise Err("rejected by model: %s" % sub)
    for i, t in enumerate(spec):
        if t in ("-j", "-g"):
            if i + 1 >= len(spec):
                raise Err("no target")
            tg = spec[i + 1]
            if tg not in BUILTIN_TARGETS and tg not in chains:
                raise Err("Couldn't load target `%s'" % tg)
        if t == "--match-set":
            if i + 1 >= len(spec) or spec[i + 1] not in st["ipset"]:
                raise Err("Set %s doesn't exist." % (spec[i + 1] if i + 1 < len(spec) else "?"))
        if t in ("-s", "-d", "--source", "--destination"):
            v = spec[i + 1] if i + 1 < len(spec) else ""
            if not v or any(ch not in "0123456789abcdefABCDEF.:/" for ch in v):
                raise Err("host/network `%s' not found" % v)


def referenced(chains, name):
    for c in chains.values():
        for r in c["rules"]:
            for i, t in enumerate(r):
                if t in ("-j", "-g") and i + 1 < len(r) and r[i + 1] == name:
                    return True
    return False


def table_of(conf, st, fam, tbl):
    if fam == "6" and tbl == "nat" and conf.get("no_v6_nat"):
        raise Err("can't initialize ip6tables table `nat': Table does not exist")
    if tbl not in st["ipt"][fam]:
        raise Err("can't initialize table `%s'" % tbl)
    return st["ipt"][fam][tbl]


def fmt_rule(chain, r):
    out = []
    for t in r:
        out.append('"%s"' % t if (" " in t or t == "") else t)
    return "-A %s %s" % (chain, " ".join(out))


def ipt_cmd(conf, st, fam, args):
    a = list(args)
    tbl = "filter"
    if "-t" in a:
        i = a.index("-t")
        tbl = a[i + 1]
        del a[i:i + 2]
    a = [x for x in a if x not in ("-w",)]
    if not a:
        raise Err("no command")
    cmd = a[0]
    chains = table_of(conf, st, fam, tbl)
    out = []
    if cmd in ("-A", "-I", "-C", "-D"):
        ch = a[1] if len(a) > 1 else ""
        if ch not in chains:
            raise Err("No chain/target/match by that name.")
        rest = a[2:]
        if cmd == "-I":
            pos = 1
            if rest and rest[0].isdigit():
                pos = int(rest[0]); rest = rest[1:]
            rule_check(conf, st, fam, tbl, chains, rest)
            if pos < 1 or pos > len(chains[ch]["rules"]) + 1:
                raise Err("Index of insertion too big.")
            chains[ch]["rules"].insert(pos - 1, rest)
        elif cmd == "-A":
            rule_check(conf, st, fam, tbl, chains, rest)
            chains[ch]["rules"].append(rest)
        elif cmd == "-C":
            if rest not in chains[ch]["rules"]:
                raise Err("Bad rule (does a matching rule exist in that chain?).")
        else:
            if len(rest) == 1 and rest[0].isdigit():
                n = int(rest[0])
                if n < 1 or n > len(chains[ch]["rules"]):
                    raise Err("Index of deletion too big.")
                del chains[ch]["rules"][n - 1]
            else:
                if rest not in chains[ch]["rules"]:
                    raise Err("Bad rule (does a matching rule exist in that chain?).")
                chains[ch]["rules"].remove(rest)
    elif cmd == "-N":
        ch = a[1]
        if ch in chains:
            raise Err("Chain already exists.")
        chains[ch] = {"policy": None, "builtin": False, "rules": []}
    elif cmd == "-F":
        if len(a) > 1:
            if a[1] not in chains:
                raise Err("No chain/target/match by that name.")
            chains[a[1]]["rules"] = []
        else:
            for c in chains.values():
                c["rules"] = []
    elif cmd == "-X":
        if len(a) > 1:
            ch = a[1]
            if ch not in chains or chains[ch]["builtin"]:
                raise Err("No chain/target/match by that name.")
            if chains[ch]["rules"]:
                raise Err("Directory not empty.")
            if referenced(chains, ch):
                raise Err("Too many links.")
            del chains[ch]
        else:
            for ch in [k for k, v in chains.items() if not v["builtin"] and not v["rules"] and not referenced(chains, k)]:
                del chains[ch]
    elif cmd == "-P":
        chains[a[1]]["policy"] = a[2]
    elif cmd == "-Z":
        pass
    elif cmd == "-S":
        names = [a[1]] if len(a) > 1 else list(chains)
        for ch in names:
            if ch not in chains:
                raise Err("No chain/target/match by that name.")
            c = chains[ch]
            out.append("-P %s %s" % (ch, c["policy"]) if c["builtin"] else "-N %s" % ch)
            for r in c["rules"]:
                out.append(fmt_rule(ch, r))
    elif cmd.startswith("-") and cmd.endswith("L"):
        names = [x for x in a[1:] if not x.startswith("-")]
        names = names[:1] if names else list(chains)
        for ch in names:
            if ch not in chains:
                raise Err("No chain/target/match by that name.")
            c = chains[ch]
            out.append("Chain %s (%s)" % (ch, "policy %s" % c["policy"] if c["builtin"] else "0 references"))
            out.append("    pkts      bytes target     prot opt in     out     source               destination")
            for r in c["rules"]:
                tg = r[r.index("-j") + 1] if "-j" in r else ""
                out.append("       0        0 %-10s all  --  *      *       0.0.0.0/0            0.0.0.0/0  %s" % (tg, " ".join(r)))
            out.append("")
    else:
        raise Err("unknown command %s" % cmd)
    return out


def restore_tokens(line):
    """iptables-1.4.x iptables-restore.c parameter split (quotes, \\ in quotes, empty params dropped)."""
    params, buf, quote, esc = [], "", False, False
    s = line + "\n"
    i = 0
    while i < len(s):
        ch = s[i]
        if quote:
            if esc:
                buf += ch; esc = False; i += 1; continue
            if ch == "\\":
                esc = True; i += 1; continue
            if ch == '"':
                quote = False
                ch = " "
            else:
                buf += ch; i += 1; continue
        else:
            if ch == '"':
                quote = True; i += 1; continue
        if ch in " \t\n":
            if buf:
                if buf.startswith("-t") or buf.startswith("--table"):
                    raise Err("Line seems to have a -t table option.")
                params.append(buf)
                buf = ""
        else:
            buf += ch
        i += 1
    return params


def ipt_restore(conf, st, fam, args, data):
    noflush = "--noflush" in args or "-n" in args
    tbl, work, ln = None, None, 0
    for raw in data.split("\n"):
        ln += 1
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("*"):
            tbl = line[1:]
            base = table_of(conf, st, fam, tbl)
            work = json.loads(json.dumps(base))
            if not noflush:
                for k in [k for k, v in work.items() if not v["builtin"]]:
                    del work[k]
                for v in work.values():
                    v["rules"] = []
            continue
        if work is None:
            raise Err("line %d: no table" % ln)
        if line == "COMMIT":
            st["ipt"][fam][tbl] = work
            tbl, work = None, None
            continue
        if line.startswith(":"):
            parts = line[1:].split()
            ch = parts[0]
            if ch in BUILTIN_CHAINS.get(tbl, []):
                if parts[1] != "-":
                    work[ch]["policy"] = parts[1]
            elif ch in work:
                work[ch]["rules"] = []
            else:
                work[ch] = {"policy": None, "builtin": False, "rules": []}
            continue
        try:
            toks = restore_tokens(line)
            if toks[:1] not in (["-A"], ["-I"]):
                raise Err("unsupported line")
            ipt_cmd(conf, {"ipt": {fam: {tbl: work}}, "ipset": st["ipset"]}, fam, ["-t", tbl] + toks)
        except Err as e:
            raise Err("line %d failed (%s)" % (ln, e))
    if work is not None:
        raise Err("no COMMIT")


# ---------------------------------------------------------------- ebtables
def ebt_cmd(conf, st, args):
    a = list(args)
    if "-t" in a:
        i = a.index("-t"); del a[i:i + 2]
    ch_all = st["ebt"]
    cmd = a[0]
    out = []
    if cmd == "-N":
        if a[1] in ch_all:
            raise Err("Chain %s already exists." % a[1])
        pol = a[a.index("-P") + 1] if "-P" in a else "ACCEPT"
        ch_all[a[1]] = {"policy": pol, "builtin": False, "rules": []}
    elif cmd in ("-A", "-I", "-D"):
        ch = a[1]
        if ch not in ch_all:
            raise Err("Chain %s doesn't exist." % ch)
        rest = a[2:]
        if cmd == "-I":
            pos = 1
            if rest and rest[0].isdigit():
                pos = int(rest[0]); rest = rest[1:]
            ch_all[ch]["rules"].insert(pos - 1, rest)
        elif cmd == "-A":
            joined = " ".join(rest)
            for f, sub in conf.get("reject", []):
                if f == "eb" and sub in joined:
                    raise Err("rejected by model")
            for i, t in enumerate(rest):
                if t == "-j" and rest[i + 1] not in ("ACCEPT", "DROP", "RETURN", "CONTINUE") and rest[i + 1] not in ch_all:
                    raise Err("bad target")
            ch_all[ch]["rules"].append(rest)
        else:
            if rest not in ch_all[ch]["rules"]:
                raise Err("Illegal target name / rule not found")
            ch_all[ch]["rules"].remove(rest)
    elif cmd == "-F":
        if len(a) > 1:
            if a[1] not in ch_all:
                raise Err("Chain doesn't exist")
            ch_all[a[1]]["rules"] = []
    elif cmd == "-X":
        ch = a[1]
        if ch not in ch_all or ch_all[ch]["builtin"]:
            raise Err("Chain doesn't exist")
        for c in ch_all.values():
            for r in c["rules"]:
                if "-j" in r and r[r.index("-j") + 1] == ch:
                    raise Err("Chain is referenced")
        del ch_all[ch]
    elif cmd == "-L":
        names = a[1:2] or list(ch_all)
        for ch in names:
            if ch not in ch_all:
                raise Err("Chain doesn't exist")
            out.append("Bridge chain: %s, entries: %d, policy: %s" % (ch, len(ch_all[ch]["rules"]), ch_all[ch]["policy"]))
            for r in ch_all[ch]["rules"]:
                out.append(" ".join(r))
    else:
        raise Err("unknown ebtables command")
    return out


# ---------------------------------------------------------------- ipset
def ipset_one(st, a):
    sets = st["ipset"]
    exist = "-exist" in a or "-!" in a
    a = [x for x in a if x not in ("-exist", "-!")]
    if not a:
        return []
    cmd = a[0]
    out = []
    if cmd in ("create", "-N"):
        if a[1] in sets:
            if not exist:
                raise Err("Set cannot be created: set with the same name already exists")
        else:
            sets[a[1]] = {"hdr": " ".join(a[2:]), "e": []}
    elif cmd in ("add", "-A"):
        if a[1] not in sets:
            raise Err("The set with the given name does not exist")
        if a[2] in sets[a[1]]["e"]:
            if not exist:
                raise Err("Element cannot be added to the set: it's already added")
        else:
            sets[a[1]]["e"].append(a[2])
    elif cmd in ("flush", "-F"):
        for n in (a[1:2] or list(sets)):
            if n not in sets:
                raise Err("The set with the given name does not exist")
            sets[n]["e"] = []
    elif cmd in ("destroy", "-X"):
        if a[1] not in sets:
            raise Err("The set with the given name does not exist")
        del sets[a[1]]
    elif cmd == "swap":
        sets[a[1]], sets[a[2]] = sets[a[2]], sets[a[1]]
    elif cmd == "test":
        raise Err("is NOT in set")
    elif cmd in ("list", "-L", "-t"):
        terse = "-t" in a
        rest = [x for x in a[1:] if x not in ("-t", "list", "-n")]
        if "-n" in a:
            out.extend(sorted(sets))
        else:
            for n in (rest[:1] or sorted(sets)):
                if n not in sets:
                    raise Err("The set with the given name does not exist")
                out.append("Name: %s" % n)
                out.append("Type: hash:net")
                out.append("Number of entries: %d" % len(sets[n]["e"]))
                if not terse:
                    out.append("Members:")
                    out.extend(sets[n]["e"])
    elif cmd == "save":
        for n in (a[1:2] or sorted(sets)):
            out.append("create %s %s" % (n, sets[n]["hdr"]))
            out.extend("add %s %s" % (n, e) for e in sets[n]["e"])
    else:
        raise Err("unknown ipset command %s" % cmd)
    return out


# ---------------------------------------------------------------- main
def main():
    tool = os.path.basename(sys.argv[0])
    args = sys.argv[1:]
    conf = load_conf()
    if tool in ("iptables-restore", "ip6tables-restore", "ipset") and (tool != "ipset" or (args[:1] == ["restore"])):
        data = sys.stdin.read()
        record(tool, args, data)
    else:
        data = None
        record(tool, args)
    if tool in ("iptables", "ip6tables", "iptables-restore", "ip6tables-restore", "ebtables", "ipset"):
        fam = "6" if tool.startswith("ip6") else "4"
        with Locked() as L:
            try:
                if tool in ("iptables", "ip6tables"):
                    out = ipt_cmd(conf, L.st, fam, args)
                elif tool.endswith("-restore"):
                    if conf.get("restore_refuse", {}).get(fam):
                        raise Err("model: restore refused (forced)")
                    ipt_restore(conf, L.st, fam, args, data)
                    out = []
                elif tool == "ebtables":
                    out = ebt_cmd(conf, L.st, args)
                else:
                    if args[:1] == ["restore"]:
                        out = []
                        exist = "-exist" in args or "-!" in args
                        for ln in data.split("\n"):
                            ln = ln.strip()
                            if not ln:
                                continue
                            ipset_one(L.st, ln.split() + (["-exist"] if exist else []))
                    else:
                        out = ipset_one(L.st, args)
            except Err as e:
                sys.stderr.write("%s: %s\n" % (tool, e))
                L.save()        # a restore commits table by table: earlier COMMITs stay
                sys.exit(1)
            L.save()
        if out:
            sys.stdout.write("\n".join(out) + "\n")
        sys.exit(0)
    if tool == "logger":
        with open(env("NF_SYSLOG", "/dev/null"), "a") as fh:
            fh.write(" ".join(args) + "\n")
        sys.exit(0)
    if tool == "nvram":
        if args[:1] == ["get"] and len(args) > 1:
            v = ""
            with open(env("NF_NVRAM")) as fh:
                for ln in fh:
                    k, _, val = ln.rstrip("\n").partition("=")
                    if k == args[1]:
                        v = val
            sys.stdout.write(v + "\n")
        sys.exit(0)
    if tool == "ip":
        # ip -6 -o addr show scope global  |  ip -6 addr show dev X scope global
        ipc = conf.get("ip6", {})
        if "-o" in args:
            for br, addrs in sorted(ipc.items()):
                for i, ad in enumerate(addrs):
                    sys.stdout.write("%d: %s    inet6 %s scope global \\       valid_lft forever preferred_lft forever\n" % (i + 5, br, ad))
        elif "dev" in args:
            br = args[args.index("dev") + 1]
            for ad in ipc.get(br, []):
                sys.stdout.write("    inet6 %s scope global\n       valid_lft forever preferred_lft forever\n" % ad)
        sys.exit(0)
    if tool == "conntrack":
        sys.exit(1)     # -D with no matching flow: the normal case
    # fc, usleep, reaper_aimesh_sync, dnsmasq, cru, ...: succeed, do nothing
    sys.exit(0)


if __name__ == "__main__":
    main()
'''
STUBS_H = r'''/* Batch B host harness: the rc environment the extracted Warden / Gatekeeper code needs. @ROOT@ / @STUB@ are
 * substituted by bbh.py. system()/doSystem()/eval("sh") run @STUB@/sh (busybox ash) with PATH=@STUB@:... so the
 * generated scripts and the C teardowns hit the netfilter model. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdarg.h>
#include <unistd.h>
#include <errno.h>
#include <pwd.h>
#include <signal.h>
#include <fcntl.h>
#include <stdint.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <net/if.h>
#include <arpa/inet.h>

static size_t strlcpy(char *d, const char *s, size_t n)
{
	size_t l = strlen(s);
	if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; }
	return l;
}

#define H_ROOT "@ROOT@"
#define H_STUB "@STUB@"
#define H_NV   H_ROOT "/nvram.txt"

static const char *nvram_safe_get(const char *k)
{
	FILE *f = fopen(H_NV, "r");
	char line[8192];
	size_t kl = strlen(k);
	if (!f) return "";
	while (fgets(line, sizeof(line), f)) {
		line[strcspn(line, "\n")] = 0;
		if (strncmp(line, k, kl) == 0 && line[kl] == '=') {
			fclose(f);
			return strdup(line + kl + 1);
		}
	}
	fclose(f);
	return "";
}
#define nvram_get(k) nvram_safe_get(k)
static int nvram_match(const char *k, const char *v) { return strcmp(nvram_safe_get(k), v) == 0; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int nvram_set(const char *k, const char *v)
{
	FILE *f = fopen(H_NV, "r"), *o = fopen(H_NV ".tmp", "w");
	char line[8192];
	size_t kl = strlen(k);
	int done = 0;
	if (f) {
		while (fgets(line, sizeof(line), f)) {
			if (strncmp(line, k, kl) == 0 && line[kl] == '=') { fprintf(o, "%s=%s\n", k, v); done = 1; }
			else fputs(line, o);
		}
		fclose(f);
	}
	if (!done) fprintf(o, "%s=%s\n", k, v);
	fclose(o);
	rename(H_NV ".tmp", H_NV);
	return 0;
}

static void h_log(const char *file, const char *fmt, ...)
{
	FILE *f = fopen(file, "a");
	va_list ap;
	if (!f) return;
	va_start(ap, fmt);
	vfprintf(f, fmt, ap);
	va_end(ap);
	fputc('\n', f);
	fclose(f);
}
#define logmessage(tag, fmt, ...) h_log(H_ROOT "/syslog", "%s: " fmt, tag, ##__VA_ARGS__)

static int h_run(char *const argv[])
{
	pid_t p;
	int st = 0;
	fflush(NULL);
	p = fork();
	if (p == 0) {
		setenv("PATH", H_STUB ":/usr/bin:/bin", 1);
		execv(H_STUB "/sh", argv);
		_exit(127);
	}
	waitpid(p, &st, 0);
	return st;
}
static int h_system(const char *c)
{
	char *argv[] = { "sh", "-c", (char *)c, NULL };
	return h_run(argv);
}
#define system(c) h_system(c)
static int doSystem(const char *fmt, ...)
{
	char buf[4096];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	return h_system(buf);
}
static int h_eval(char *const argv[])
{
	if (strcmp(argv[0], "sh") == 0) {
		int st = h_run(argv);
		return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
	}
	{
		char line[1024] = "";
		int i;
		for (i = 0; argv[i]; i++) { strcat(line, argv[i]); strcat(line, " "); }
		h_log(H_ROOT "/eval.log", "%s", line);
	}
	return 0;
}
#define eval(cmd, ...) h_eval((char *const[]){ cmd, ##__VA_ARGS__, NULL })
#define xstart(cmd, ...) h_eval((char *const[]){ "xstart", cmd, ##__VA_ARGS__, NULL })

static int f_exists(const char *p) { struct stat st; return stat(p, &st) == 0; }
static int reaper_script_ok(const char *p) { struct stat st; return lstat(p, &st) == 0 && S_ISREG(st.st_mode); }
static int is_routing_enabled(void) { return !nvram_match("h_routing", "0"); }
static void reaper_secure_dir(const char *d, int mode)
{
	char b[512], *q;
	snprintf(b, sizeof(b), "%s", d);
	for (q = b + 1; *q; q++)
		if (*q == '/') { *q = 0; mkdir(b, 0755); *q = '/'; }
	mkdir(b, mode);
	chmod(b, mode);
}
static int pids(const char *n) { (void)n; return 0; }
static int killall_tk(const char *n) { (void)n; return 0; }
static int file_lock(const char *n) { (void)n; return 7; }
static void file_unlock(int l) { (void)l; }
static void start_httpd(void) { }
static void gk_rl_migrate(void) { }
static const char *gk_rl_get(void) { return nvram_safe_get("h_gk_rl"); }
static char *rw_list_get(const char *name)
{
	char k[64];
	snprintf(k, sizeof(k), "h_list_%s", name);
	return strdup(nvram_safe_get(k));
}

#define REAPER_AIMESH_MAX 64
static int reaper_aimesh_macs(char macs[][18], int max, int *dropped)
{
	char *l = strdup(nvram_safe_get("h_aimesh")), *t, *sp = NULL;
	int n = 0;
	*dropped = 0;
	for (t = strtok_r(l, " ", &sp); t; t = strtok_r(NULL, " ", &sp)) {
		if (n < max) snprintf(macs[n++], 18, "%s", t);
		else (*dropped)++;
	}
	return n;
}

typedef struct { char ifname[IFNAMSIZ]; char br_ifname[IFNAMSIZ]; char addr[INET_ADDRSTRLEN]; char netmask[INET_ADDRSTRLEN];
		 char subnet[INET_ADDRSTRLEN]; unsigned prefixlen; char dns[2][INET_ADDRSTRLEN]; } SUBNET_T;
typedef struct { int enable; SUBNET_T nw_t; } MTLAN_T;
#define INIT_MTLAN(sz) calloc(16, (sz))
#define FREE_MTLAN(p) free(p)
/* h_mtlan: "en,br,ifname,addr,mask,subnet,plen,dns1,dns2;..." */
static void get_mtlan(MTLAN_T *p, size_t *n)
{
	char *l = strdup(nvram_safe_get("h_mtlan")), *rec, *sp = NULL;
	*n = 0;
	for (rec = strtok_r(l, ";", &sp); rec && *n < 16; rec = strtok_r(NULL, ";", &sp)) {
		char f[9][64];
		int i = 0;
		char *s = rec, *c;
		memset(f, 0, sizeof(f));
		while (i < 9) {
			c = strchr(s, ',');
			if (c) *c = 0;
			snprintf(f[i++], 64, "%s", s);
			if (!c) break;
			s = c + 1;
		}
		p[*n].enable = atoi(f[0]);
		snprintf(p[*n].nw_t.br_ifname, IFNAMSIZ, "%s", f[1]);
		snprintf(p[*n].nw_t.ifname, IFNAMSIZ, "%s", f[2]);
		snprintf(p[*n].nw_t.addr, INET_ADDRSTRLEN, "%s", f[3]);
		snprintf(p[*n].nw_t.netmask, INET_ADDRSTRLEN, "%s", f[4]);
		snprintf(p[*n].nw_t.subnet, INET_ADDRSTRLEN, "%s", f[5]);
		p[*n].nw_t.prefixlen = (unsigned)atoi(f[6]);
		snprintf(p[*n].nw_t.dns[0], INET_ADDRSTRLEN, "%s", f[7]);
		snprintf(p[*n].nw_t.dns[1], INET_ADDRSTRLEN, "%s", f[8]);
		(*n)++;
	}
}

/* Warden helpers outside the extracted regions: not part of the netfilter picture */
static void rw_list_migrate(void) { }
static void rw_seed_allow(void) { }
static void rw_dns_sync(void) { }
static void rw_gen_stats(void) { }
static void rw_gen_fold(void) { }
static void rw_gen_update(int w) { (void)w; }
static void rw_gen_dns(void) { }
'''
TOOLS = ["iptables", "ip6tables", "iptables-restore", "ip6tables-restore", "ebtables", "ipset", "logger", "nvram",
         "ip", "conntrack", "fc", "usleep", "reaper_aimesh_sync", "dnsmasq", "cru"]
os.makedirs(STUB)
with open(STUB + "/nfmodel.py", "w") as fh:
    fh.write("#!" + sys.executable + "\n" + NFMODEL)
os.chmod(STUB + "/nfmodel.py", 0o755)
for t in TOOLS:
    os.symlink(STUB + "/nfmodel.py", STUB + "/" + t)
os.symlink(SHB, STUB + "/sh")


def subst(t):
    for a, b in (("/usr/sbin/", STUB + "/"), ("/sbin/reaper_aimesh_sync", STUB + "/reaper_aimesh_sync"),
                 ("/tmp/rwarden", ROOT + "/tmp/rwarden"), ("/jffs/rwarden", ROOT + "/jffs/rwarden"),
                 ("/tmp/reaper", ROOT + "/tmp/reaper"), ("/jffs/reaper", ROOT + "/jffs/reaper"),
                 ("/tmp/gk", ROOT + "/tmp/gk"), ("/tmp/resolv.dnsmasq", ROOT + "/tmp/resolv.dnsmasq"),
                 ("/sys/class/net", ROOT + "/sys/class/net")):
        t = t.replace(a, b)
    return t


def build(comp):
    head = "\n".join([STUBS_H.replace("@ROOT@", ROOT).replace("@STUB@", STUB), subst(rd("rc/reaper_nv.h")),
                      subst(rd("rc/reaper_hook.h")),
                      # 2026-11-08: every firewall log rule takes its target from shared/reaper_fwlog.h (NFLOG or the
                      # limited LOG); the canon's own header, its state file under ROOT, so the generator compiles
                      # with the real text (no state file here = the limited LOG, the model sees the `-m limit`)
                      subst(rd("shared/reaper_fwlog.h")),
                      '#define REAPER_FW_BUILT_MARK "%s/tmp/reaper/.reaper_firewall_built"' % ROOT,
                      subst(sl(rd("rc/reaper_hook.c"), "void reaper_hook_gen(void)", "/* v3.1.7: the firewall table walker"))])
    if comp == "rw":
        t = subst(rw)
        body = "\n".join([sl(t, "#define RW_DIR ", "static int rw_valid_cidr("), sl(t, "static int rw_valid_cidr(", "/* The updater: fetches"),
                          sl(t, "static void rw_stop(int teardown);", "/* 1 when the whitelist"), sl(t, "void start_rwarden(void)"),
                          "int main(int c, char **v) { int i; for (i = 1; i < c; i++) { if (!strcmp(v[i], \"start\")) start_rwarden();"
                          " else if (!strcmp(v[i], \"stop\")) stop_rwarden(); } return 0; }"])
    else:
        body = "\n".join(["#define RTCONFIG_CFGSYNC 1", sl(subst(gk), "#define GK_DIR "),
                          "int main(int c, char **v) { int i; for (i = 1; i < c; i++) { if (!strcmp(v[i], \"start\")) start_gk();"
                          " else if (!strcmp(v[i], \"stop\")) stop_gk(); else if (!strcmp(v[i], \"refresh\")) gk_refresh(); } return 0; }"])
    out = W + "/" + comp
    with open(out + ".c", "w") as fh:
        fh.write(head + "\n" + body + "\n")
    # -Darm=1: the router toolchain defines `arm`; a local of that name broke the _r11 build while this host harness passed
    r = subprocess.run([CC, "-w", "-O0", "-Darm=1", "-o", out, out + ".c"], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-3000:])
        check("compile the %s generator on the host" % comp, False)
        sys.exit(1)
    return out


BASE_NV = {"lan_ifname": "br0", "lan_ipaddr": "192.168.50.1", "lan_netmask": "255.255.255.0",
           "ipv6_prefix": "2001:db8:50::", "ipv6_prefix_length": "64", "wan0_ipaddr": "203.0.113.5", "wan1_ipaddr": "",
           "ipv6_wan_addr": "2001:db8:ffff::2", "ipv6_rtr_addr": "2001:db8:50::1", "wgs1_enable": "1", "wgs1_port": "51820",
           "wgs2_enable": "0", "rwarden_enable": "0", "rwarden_dns": "0", "rwarden_dir": "in", "rwarden_self": "0",
           "rwarden_log": "0", "rwarden_geo": "", "gk_enable": "0", "gk_default": "0", "gk_captive": "1", "http_enable": "1",
           "https_lanport": "8443", "http_lanport": "80",
           "h_mtlan": "1,br0,br0,192.168.50.1,255.255.255.0,192.168.50.0,24,192.168.50.10,;"
                      "1,br52,br52,192.168.52.1,255.255.255.0,192.168.52.0,24,192.168.50.10,9.9.9.9",
           "h_aimesh": "02:11:22:33:44:55 02:11:22:33:44:66"}
IP6 = {"br0": ["2001:db8:50::1/64"], "br52": ["2001:db8:52::1/64"]}


def macs(n, base):
    return ["02:aa:bb:cc:%02x:%02x" % ((base + i) >> 8, (base + i) & 0xff) for i in range(n)]


def setup(nv, conf):
    if os.path.exists(ROOT):
        shutil.rmtree(ROOT)
    for d in ("tmp/rwarden", "tmp/reaper", "tmp/gk", "jffs/rwarden", "jffs/reaper", "sys/class/net/br0", "sys/class/net/br52"):
        os.makedirs(ROOT + "/" + d)
    n = dict(BASE_NV)
    n.update(nv)
    with open(ROOT + "/nvram.txt", "w") as fh:
        fh.write("".join("%s=%s\n" % kv for kv in n.items()))
    c = dict(conf)
    c.setdefault("ip6", IP6)
    json.dump(c, open(ROOT + "/conf.json", "w"))
    open(ROOT + "/tmp/reaper/.reaper_firewall_built", "w").close()
    open(ROOT + "/tmp/resolv.dnsmasq", "w").write("server=9.9.9.9\nserver=2620:fe::fe\nserver=0.0.0.0/0\n")
    stt = {"ipt": {}, "ebt": {c_: {"policy": "ACCEPT", "builtin": True, "rules": []} for c_ in ("FORWARD", "INPUT", "OUTPUT")}, "ipset": {}}
    for fam in ("4", "6"):
        stt["ipt"][fam] = {"filter": {"INPUT": {"policy": "DROP", "builtin": True, "rules": [["-i", "lo", "-j", "ACCEPT"]]},
                                      "FORWARD": {"policy": "DROP", "builtin": True, "rules": [["-i", "br0", "-j", "ACCEPT"]]},
                                      "OUTPUT": {"policy": "ACCEPT", "builtin": True, "rules": []},
                                      "SDN_FI": {"policy": None, "builtin": False, "rules": []}},
                           "nat": {c_: {"policy": "ACCEPT", "builtin": True, "rules": []} for c_ in ("PREROUTING", "INPUT", "OUTPUT", "POSTROUTING")}}
    json.dump(stt, open(ROOT + "/nf.json", "w"))


def nv_set(k, v):
    lines = [ln for ln in open(ROOT + "/nvram.txt") if ln.split("=", 1)[0] != k]
    lines.append("%s=%s\n" % (k, v))
    open(ROOT + "/nvram.txt", "w").writelines(lines)


def env():
    e = dict(os.environ)
    e.update(NF_STATE=ROOT + "/nf.json", NF_CONF=ROOT + "/conf.json", NF_NVRAM=ROOT + "/nvram.txt", NF_SYSLOG=ROOT + "/syslog",
             NF_LOG=ROOT + "/calls.jsonl", PATH=STUB + ":/usr/bin:/bin")
    return e


def run(cmd):
    if os.path.exists(ROOT + "/calls.jsonl"):
        os.unlink(ROOT + "/calls.jsonl")
    r = subprocess.run(cmd, env=env(), capture_output=True, text=True, timeout=600)
    calls = {"build_adds": 0}
    if os.path.exists(ROOT + "/calls.jsonl"):
        for ln in open(ROOT + "/calls.jsonl"):
            j = json.loads(ln)
            t = j["tool"]
            calls[t] = calls.get(t, 0) + 1
            a = j["args"]
            # one iptables process per rule of the layer's OWN chains = the build the batch replaces
            if t in ("iptables", "ip6tables") and "-A" in a and a.index("-A") + 1 < len(a) and \
                    re.match(r"^(REAPER_WARDEN|RW_[A-Z]+|REAPER_GK[FIN])$", a[a.index("-A") + 1]):
                calls["build_adds"] += 1
    return r.returncode, calls


def state():
    s = json.load(open(ROOT + "/nf.json"))
    fc = {}
    for p in ("tmp/rwarden/failcount", "tmp/gk/failcount"):
        fc[p] = open(ROOT + "/" + p).read().strip() if os.path.exists(ROOT + "/" + p) else None
    return json.dumps({"ipt": s["ipt"], "ebt": s["ebt"], "ipset": {k: sorted(v["e"]) for k, v in s["ipset"].items()}, "fc": fc}, sort_keys=True)


def strip_shim(script, comp):
    """the per-rule script: the batch shim and commit block removed (what apply.sh was before the batch)"""
    out, skip = [], False
    begin = "RWB=" if comp == "rw" else "GKB="
    lines = script.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith(begin):
            # shim: this line + the quote fn, the collector and the two tool overrides
            i += 5
            continue
        if ln.startswith("_rw_commit() {") or ln.startswith("_gk_commit() {"):
            j = i
            while not lines[j].startswith('rm -f "$' + begin[:3]):
                j += 1
            # keep the two wrapper lines the commit block restores (they re-define the same per-rule wrappers)
            i = j + 1
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def three_ways(comp, binp, nv, conf, label):
    """generate apply.sh with the real start, then run it per-rule / batched / batched+refused from the same state"""
    setup(nv, conf)
    rc, _ = run([binp, "start"])
    ap = ROOT + ("/tmp/rwarden/apply.sh" if comp == "rw" else "/tmp/gk/apply.sh")
    script = open(ap).read()
    pre = open(ROOT + "/nf.json").read()
    pertule = strip_shim(script, comp)
    check("%s: the per-rule reference really is per rule (no restore left)" % label,
          "-restore" not in pertule and ("_rwb" not in pertule if comp == "rw" else "_gkb" not in pertule))
    results = {}
    for way, text, refuse in (("per-rule", pertule, False), ("batched", script, False), ("refused", script, True)):
        open(ROOT + "/nf.json", "w").write(pre)
        c = dict(conf)
        c.setdefault("ip6", IP6)
        if refuse:
            c["restore_refuse"] = {"4": True, "6": True}
        json.dump(c, open(ROOT + "/conf.json", "w"))
        for p in ("tmp/rwarden/failcount", "tmp/gk/failcount"):
            if os.path.exists(ROOT + "/" + p):
                os.unlink(ROOT + "/" + p)
        open(ROOT + "/x.sh", "w").write(text)
        if os.path.exists(ROOT + "/syslog"):
            os.unlink(ROOT + "/syslog")
        rc, calls = run([STUB + "/sh", ROOT + "/x.sh"])
        calls["refused"] = open(ROOT + "/syslog").read().count("rebuild refused") if os.path.exists(ROOT + "/syslog") else 0
        results[way] = (rc, state(), calls)
    if not conf.get("reject") and not conf.get("no_v6_nat"):
        check("%s: every restore payload is ACCEPTED when every rule is valid (no fallback taken)" % label,
              results["batched"][2]["refused"] == 0 and results["refused"][2]["refused"] > 0)
    same = results["per-rule"][1] == results["batched"][1] == results["refused"][1]
    check("%s: per-rule == batched == refused-then-replayed (every chain, v4+v6, filter+nat, ebtables, ipset, failcount)" % label, same)
    ipr = sum(results["per-rule"][2].get(t, 0) for t in ("iptables", "ip6tables"))
    ipb = sum(results["batched"][2].get(t, 0) for t in ("iptables", "ip6tables"))
    print("     spawns: iptables+ip6tables per-rule %d -> batched %d (+%d restore); own-chain rule adds %d -> %d"
          % (ipr, ipb, sum(results["batched"][2].get(t, 0) for t in ("iptables-restore", "ip6tables-restore")),
             results["per-rule"][2]["build_adds"], results["batched"][2]["build_adds"]))
    return results, results["per-rule"][2]["build_adds"], results["batched"][2]["build_adds"]


print("== (B) Warden / Gatekeeper on the netfilter model")
rwb = build("rw")
gkb = build("gk")
C20 = "CN RU KP IR BY SY CU VE NG PK BD VN ID TH PH MY BR AR CO MX"
LISTS = {"h_list_allow": "192.168.50.0/24 8.8.8.8 2001:db8:50::/64", "h_list_ban": "198.51.100.7 2001:db8:dead::1 10.9.9.0/24"}
three_ways("rw", rwb, dict(rwarden_enable="1"), {}, "Warden baseline")
_, ipr, ipb = three_ways("rw", rwb, dict(rwarden_enable="1", rwarden_geo=C20, rwarden_dir="both", rwarden_self="1", rwarden_log="1", **LISTS),
                         {}, "Warden 20 countries, both, self, log, lists")
check("Warden: the batched build runs NO per-rule iptables add for its own chains (the per-rule one runs one per rule)",
      ipb == 0 and ipr > 100, "%d vs %d" % (ipb, ipr))
three_ways("rw", rwb, dict(rwarden_enable="1", rwarden_geo="cn ru", rwarden_dir="both"), {"reject": [["4", "addrtype"]]},
           "Warden with a v4 rule the kernel rejects")
four = "".join("<%s>%d" % (m, s) for m, s in zip(macs(4, 0x10), [0, 1, 2, 3]))
twenty = "".join("<%s>%d" % (m, i % 4) for i, m in enumerate(macs(20, 0x40)))
_, ipr, ipb = three_ways("gk", gkb, dict(gk_enable="1", h_gk_rl=four), {}, "Gatekeeper quarantine, 4 devices, 2 networks, AiMesh")
r20, ipr, ipb = three_ways("gk", gkb, dict(gk_enable="1", gk_default="1", h_gk_rl=twenty), {}, "Gatekeeper open, 20 devices")
check("Gatekeeper: the batched build runs NO per-rule iptables add for its own chains (the per-rule one runs one per rule)",
      ipb == 0 and ipr > 100, "%d vs %d" % (ipb, ipr))
check("Gatekeeper: four restores per apply (filter + nat, both stacks)",
      sum(r20["batched"][2].get(t, 0) for t in ("iptables-restore", "ip6tables-restore")) == 4)
rr, _, _ = three_ways("gk", gkb, dict(gk_enable="1", h_gk_rl=four), {"reject": [["6", "--ctorigdstport"]]},
                      "Gatekeeper with a v6 rule the kernel rejects")
check("Gatekeeper: the rejected rule still fails ALONE and is counted (failcount equal to the per-rule run, non-zero)",
      json.loads(rr["batched"][1])["fc"]["tmp/gk/failcount"] not in (None, "0"))
three_ways("gk", gkb, dict(gk_enable="1", h_gk_rl=four), {"no_v6_nat": True}, "Gatekeeper on a kernel without ip6 nat")
three_ways("gk", gkb, dict(gk_enable="1", http_enable="0", gk_captive="1", h_gk_rl=four), {}, "Gatekeeper HTTP-only admin")

# flows: one teardown per arm must end where the old double teardown ended
for comp, binp, nv, chain in (("rw", rwb, dict(rwarden_enable="1", rwarden_geo="cn ru", rwarden_dir="both", rwarden_self="1"), "REAPER_WARDEN"),
                              ("gk", gkb, dict(gk_enable="1", h_gk_rl=four), "REAPER_GKF")):
    name = "Warden" if comp == "rw" else "Gatekeeper"
    setup(nv, {})
    run([binp, "start"])
    run([binp, "start"])
    a = state()
    setup(nv, {})
    run([binp, "start"])
    run([binp, "stop"])
    run([binp, "start"])
    b = state()
    check("%s: re-arm with ONE teardown == stop (C teardown) + arm (the old double-teardown sequence)" % name, a == b)
    s = json.loads(a)["ipt"]["4"]["filter"]
    check("%s: armed, hooked from the front chain, and the front chains first in the base chains" % name,
          chain in s and ["-j", "REAPER_HOOK_F"] == s["FORWARD"]["rules"][0] and any(chain in r for r in s["REAPER_HOOK_F"]["rules"]))
    nv_set("lan_ipaddr" if comp == "rw" else "lan_ifname", "")
    rc, _ = run([binp, "start"])
    s = json.loads(state())["ipt"]
    check("%s: an apply that defers (LAN not ready) leaves NO chain behind, v4 and v6 (as stop-then-apply did)" % name,
          chain not in s["4"]["filter"] and chain not in s["6"]["filter"]
          and not any(chain in r for r in s["4"]["filter"].get("REAPER_HOOK_F", {"rules": []})["rules"]))
    setup(nv, {})
    run([binp, "start"])
    nv_set("rwarden_enable" if comp == "rw" else "gk_enable", "0")
    run([binp, "stop"])
    s = json.loads(state())["ipt"]
    check("%s: stop leaves no chain of its own in either stack" % name,
          not [c for f in s.values() for t in f.values() for c in t if c.startswith("RW_") or c.startswith("REAPER_GK") or c == "REAPER_WARDEN"])
    setup(nv, {})
    rc0, c0 = run([binp, "start"])
    rc1, c1 = run([binp, "start"])
    print("     %s re-arm spawns: iptables+ip6tables %d (first arm %d)" % (name, c1.get("iptables", 0) + c1.get("ip6tables", 0),
                                                                          c0.get("iptables", 0) + c0.get("ip6tables", 0)))

# ------------------------------------------------------------------ (C) do_reaper_conn_cgi
print("== (C) do_reaper_conn_cgi")
CONN_STUB = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <ifaddrs.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <net/if.h>
#include <netinet/in.h>
#include <arpa/inet.h>
static size_t strlcpy(char *d, const char *s, size_t n)
{ size_t l = strlen(s); if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; } return l; }
#define websWrite(wp, fmt, ...) fprintf(wp, fmt, ##__VA_ARGS__)
static time_t h_time(time_t *t) { if (t) *t = 1762300000; return 1762300000; }
#define RGATE_OK 0
static int reaper_gate(void) { return RGATE_OK; }
static void reaper_gate_deny(FILE *s, int w, const char *c) { (void)s; (void)w; (void)c; }
static char *get_cgi(const char *n) { (void)n; return NULL; }
static const char *nvram_safe_get(const char *k)
{
	if (!strcmp(k, "lan_ipaddr")) return "192.168.50.1";
	if (!strcmp(k, "lan_netmask")) return "255.255.255.0";
	return "";
}
static int nvram_get_int(const char *k)
{
	if (!strcmp(k, "qos_type")) return 1;
	if (!strcmp(k, "rconn_names")) return getenv("H_NAMES") ? 1 : 0;
	return 0;
}
static void nvram_set_int(const char *k, int v) { (void)k; (void)v; }
static void nvram_commit(void) { }
static void notify_rc(const char *s) { (void)s; }
static void reaper_secure_dir(const char *d, int m) { (void)d; (void)m; }
static int f_write_string(const char *p, const char *s, int a, int b) { (void)p; (void)s; (void)a; (void)b; return 0; }
#define REAPER_TMPDIR "@H@/tmp"
struct reaper_nd { unsigned char ip[16]; char mac[18]; char br[16]; };
static int reaper_nd_load(struct reaper_nd *t, int max)
{
	FILE *f = fopen("@H@/nd.txt", "r"); char a[64], m[32]; int n = 0;
	if (!f) return 0;
	while (n < max && fscanf(f, "%63s %31s", a, m) == 2) {
		if (inet_pton(AF_INET6, a, t[n].ip) == 1) { snprintf(t[n].mac, 18, "%s", m); strcpy(t[n].br, "br0"); n++; }
	}
	fclose(f);
	return n;
}
static int reaper_nd_mac_of(const struct reaper_nd *t, int n, const unsigned char *ip6, char *mac, size_t ml, char *br, size_t bl)
{
	int i; (void)br; (void)bl;
	for (i = 0; i < n; i++) if (!memcmp(t[i].ip, ip6, 16)) { snprintf(mac, ml, "%s", t[i].mac); return 1; }
	return 0;
}
'''
CONN_MAIN = r'''
static int h_brsubs(struct rconn_brsub *o, int max)
{
	(void)max;
	o[0].addr = ntohl(inet_addr("192.168.50.1")); o[0].mask = 0xffffff00u; o[0].net = o[0].addr & o[0].mask;
	o[1].addr = ntohl(inet_addr("192.168.52.1")); o[1].mask = 0xffffff00u; o[1].net = o[1].addr & o[1].mask;
	return 2;
}
static int h_rtr6(struct in6_addr *o, int max)
{
	(void)max;
	inet_pton(AF_INET6, "2001:db8:50::1", &o[0]);
	return 1;
}
int main(int c, char **v)
{
	FILE *o = fopen(v[1], "w");
	struct timespec a, b;
	if (getenv("H_NAMES")) {	/* fill the name map from names.txt ("ip name") the way rdnsmapd would */
		int fd = open(RDM_PATH, O_RDWR);
		void *m = mmap(NULL, RDM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
		FILE *nf = fopen("@H@/names.txt", "r");
		char ip[64], nm[64];
		while (nf && fscanf(nf, "%63s %63s", ip, nm) == 2) {
			uint8_t k[16]; struct in_addr ia;
			if (!inet_aton(ip, &ia)) continue;
			rdm_key4(k, ia.s_addr);
			rdm_put(rdm_table(m), k, nm, (uint8_t)strlen(nm), 1762300000 + 7200);
		}
		if (nf) fclose(nf);
		munmap(m, RDM_SIZE); close(fd);
	}
	clock_gettime(CLOCK_MONOTONIC, &a);
	do_reaper_conn_cgi("", o);
	clock_gettime(CLOCK_MONOTONIC, &b);
	fclose(o);
	fprintf(stderr, "%.3f\n", (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / 1e9);
	return 0;
}
'''
OLD_SCAN = ("\t\t\t\tint k;\n"
            "\t\t\t\tfor (k = 0; k < ctn; k++) {\n"
            "\t\t\t\t\tif ((ctv[k].s == sN && ctv[k].sp == (unsigned)sp && ctv[k].d == dN && ctv[k].dp == (unsigned)dp) ||\n"
            "\t\t\t\t\t    (ctv[k].d == sN && ctv[k].dp == (unsigned)sp && ctv[k].s == dN && ctv[k].sp == (unsigned)dp)) {\n"
            "\t\t\t\t\t\tcstate = ctv[k].st;\n"
            "\t\t\t\t\t\tbreak;\n"
            "\t\t\t\t\t}\n"
            "\t\t\t\t}\n")
NEW_FIND = sl(cg, "\t\t\t\tconst struct rc_ctst *fw = rconn_ct_find(", "\t\t\t}\n")
CW = W + "/conn"
os.makedirs(CW + "/fx")


def conn_build(variant):
    reg = sl(web, "static void reaper_ip_strip_zeros(char *ip)", "/* reaper v1.3.0: stream a collector snapshot")
    if variant == "linear":
        reg = reg.replace(NEW_FIND, OLD_SCAN).replace("\tif (ctn > 1)\n\t\tqsort(ctv, (size_t)ctn, sizeof(*ctv), rconn_ct_cmp);\n", "")
    elif variant == "mutant":
        reg = reg.replace("if (fw && (!rv || fw->ix < rv->ix))", "if (fw && !rv)")
    reg = reg.replace("static void reaper_audit(const char *feat, const char *act, const char *detail);", "")
    reg = reg.replace("nbrs = rconn_brsubs(brs, RCONN_NBR);", "nbrs = h_brsubs(brs, RCONN_NBR);")
    reg = reg.replace("nrtr6 = rconn_rtr6_load(rtr6, RCONN_NBR);", "nrtr6 = h_rtr6(rtr6, RCONN_NBR);")
    reg = reg.replace("/proc/net/nf_conntrack", CW + "/fx/nf_conntrack").replace("/proc/fcache/nflist", CW + "/fx/nflist")
    reg = reg.replace("/tmp/reaper/reaper_conn_seen", CW + "/fx/seen").replace("/tmp/reaper/reaper_conn.lock", CW + "/conn.lock")
    reg = reg.replace("time(NULL)", "h_time(NULL)")
    reg = reg.replace("static int rconn_is_lan(", "static int h_brsubs(struct rconn_brsub *o, int max);\nstatic int h_rtr6(struct in6_addr *o, int max);\nstatic int rconn_is_lan(", 1)
    dm = rd("shared/reaper_dnsmap.h").replace('"/tmp/reaper/dnsmap"', '"%s/dnsmap"' % CW)
    src = CONN_STUB.replace("@H@", CW) + dm + \
        "static void reaper_audit(const char *feat, const char *act, const char *detail) { (void)feat; (void)act; (void)detail; }\n" + \
        reg + CONN_MAIN.replace("@H@", CW)
    out = CW + "/" + variant
    open(out + ".c", "w").write(src)
    r = subprocess.run([CC, "-O2", "-w", "-o", out, out + ".c"], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-3000:])
        check("compile do_reaper_conn_cgi (%s)" % variant, False)
        sys.exit(1)
    return out


check("the reference really carries the old scan (and no sort)", NEW_FIND in cg)
bins = {v: conn_build(v) for v in ("new", "linear", "mutant")}
H = CW


def v4(r, net):
    return "%s.%d" % (net, r.randint(2, 254))


def pad(ip):
    return ".".join("%03d" % int(x) for x in ip.split("."))


def ext(r):
    return "%d.%d.%d.%d" % (r.choice([8, 23, 31, 52, 93, 104, 142, 151, 172, 185]), r.randint(0, 255), r.randint(0, 255), r.randint(1, 254))


STATES = ["ESTABLISHED", "TIME_WAIT", "SYN_SENT", "CLOSE_WAIT", "FIN_WAIT", "LAST_ACK", "SYN_RECV", "CLOSE"]


def ct_line(proto, st, s, d, sp, dp, rs, rd_, pk=(3, 300, 4, 400)):
    if proto == "tcp":
        return ("ipv4     2 tcp      6 431999 %s src=%s dst=%s sport=%d dport=%d packets=%d bytes=%d src=%s dst=%s "
                "sport=%d dport=%d packets=%d bytes=%d [ASSURED] mark=0 use=2" % (st, s, d, sp, dp, pk[0], pk[1], rs, rd_, dp, sp, pk[2], pk[3]))
    return ("ipv4     2 udp      17 170 src=%s dst=%s sport=%d dport=%d packets=1 bytes=90 src=%s dst=%s sport=%d dport=%d "
            "packets=1 bytes=120 mark=0 use=2" % (s, d, sp, dp, rs, rd_, dp, sp))


def v6full(a):
    import ipaddress
    return ipaddress.IPv6Address(a).exploded


def gen(seed, n_ct, n_flow, d):
    r = random.Random(seed)
    os.makedirs(d, exist_ok=True)
    ct, flows = [], []
    wan = "203.0.113.5"
    tuples = []
    for i in range(n_ct):
        lan = v4(r, r.choice(["192.168.50", "192.168.52"]))
        rem = ext(r)
        sp, dp = r.randint(1024, 65535), r.choice([443, 80, 853, 22, 5222, r.randint(1, 65535)])
        st = r.choice(STATES)
        kind = r.random()
        if kind < 0.85:
            ct.append(ct_line("tcp", st, lan, rem, sp, dp, rem, wan))
            tuples.append((lan, sp, rem, dp))
        elif kind < 0.93:
            ct.append(ct_line("udp", "", lan, rem, sp, dp, rem, wan))
        else:
            # inbound (port forward): original tuple is remote -> wan
            ct.append(ct_line("tcp", st, rem, wan, sp, dp, lan, rem))
            tuples.append((rem, sp, wan, dp))
        if r.random() < 0.03 and tuples:
            # a duplicate original tuple with a different state (zones / a re-used tuple): first one must win
            t = tuples[-1]
            ct.append(ct_line("tcp", r.choice(STATES), t[0], t[2], t[1], t[3], t[2], wan))
        if r.random() < 0.03 and tuples:
            # the REVERSE tuple as its own row, different state: whichever comes first in the file must win
            t = tuples[r.randrange(len(tuples))]
            ct.append(ct_line("tcp", r.choice(STATES), t[2], t[0], t[3], t[1], t[0], t[2]))
        if r.random() < 0.01:
            ct.append("ipv4     2 icmp     1 29 src=%s dst=8.8.8.8 type=8 code=0 id=1 src=8.8.8.8 dst=%s type=0 code=0 id=1 mark=0 use=2" % (lan, wan))
        if r.random() < 0.004:
            ct.append("ipv4     2 tcp      6 431999 ESTABLISHEDXXXXXXXXXXXXXX src=%s dst=%s sport=1 dport=2 src=198.51.100.1 dst=203.0.113.2 sport=2 dport=1" % (lan, rem))
    # IPv6 rows (both ends tested against nd + rtr6)
    nd = []
    for i in range(max(8, n_ct // 50)):
        lan6 = "2001:db8:50::%x" % (0x20 + i)
        mac = "02:00:00:00:%02x:%02x" % (i >> 8 & 255, i & 255)
        nd.append("%s %s" % (lan6, mac))
        rem6 = "2606:4700::%x" % r.randint(1, 0xffff)
        sp, dp = r.randint(1024, 65535), 443
        if r.random() < 0.5:
            ct.append("ipv6     10 tcp      6 300 %s src=%s dst=%s sport=%d dport=%d packets=5 bytes=500 src=%s dst=%s sport=%d dport=%d packets=6 bytes=600 [ASSURED] mark=0 use=2"
                      % (r.choice(STATES), v6full(lan6), v6full(rem6), sp, dp, v6full(rem6), v6full(lan6), dp, sp))
        else:
            ct.append("ipv6     10 udp      17 60 src=%s dst=%s sport=%d dport=53 packets=1 bytes=80 src=%s dst=%s sport=53 dport=%d packets=1 bytes=200 mark=0 use=2"
                      % (v6full(lan6), v6full("2001:db8:50::1"), sp, v6full("2001:db8:50::1"), v6full(lan6), sp))
    ct.append("ipv6     10 udp      17 60 src=fe80:0000:0000:0000:0000:0000:0000:0001 dst=ff02:0000:0000:0000:0000:0000:0000:00fb sport=5353 dport=5353 packets=1 bytes=80 mark=0 use=2")
    r.shuffle(ct)
    # flows: forward hits, reply-direction hits (WAN side), misses, UDP flows on TCP tuples, zero-padded IPs
    flows.append("FlowId  Hits ... header line (skipped)")
    for i in range(n_flow):
        k = r.random()
        if tuples and k < 0.6:
            s, sp, d_, dp = tuples[r.randrange(len(tuples))]
        elif tuples and k < 0.8:
            d_, dp, s, sp = tuples[r.randrange(len(tuples))]      # the reply direction
        else:
            s, sp, d_, dp = v4(r, "192.168.50"), r.randint(1024, 65535), ext(r), 443
        prot = 6 if r.random() < 0.9 else 17
        tot, tb, sw, hw = r.randint(1, 10**6), r.randint(1, 10**9), r.randint(0, 1000), r.randint(0, 10**6)
        nfc = "%08x" % r.getrandbits(32)
        flows.append("%d a b c d e %d %d %d: 0 x y z %d 0 q 0 %d <%s:%d> <%s:%d> v0 v1 t %02x %d <aa:bb:cc:dd:ee:ff> <11:22:33:44:55:66> rx tx %s"
                     % (i + 1, tot, tb, sw, hw, prot, pad(s) if r.random() < 0.5 else s, sp, d_, dp, r.choice([0, 0x28, 0xb8]), r.randint(0, 7), nfc))
        if r.random() < 0.01:
            flows.append("%d a b c d e 1 1 1: 0 x y z 0 0 q 0 6 <2001:db8:1::5:443> <2001:db8::1:5000> v0 v1 t 00 0 <a> <b> rx tx 9" % (i + 1))
    with open(d + "/nf_conntrack", "w") as fh:
        fh.write("\n".join(ct) + "\n")
    with open(d + "/nflist", "w") as fh:
        fh.write("\n".join(flows) + "\n")
    with open(d + "/seen", "w") as fh:
        fh.write("".join("%08x %d\n" % (r.getrandbits(32), 1762290000 + i) for i in range(20)))
    with open(H + "/nd.txt", "w") as fh:
        fh.write("\n".join(nd) + "\n")
    with open(H + "/names.txt", "w") as fh:
        for t in tuples[: max(5, len(tuples) // 10)]:
            fh.write("%s host-%s.example\n" % (t[2], t[2].replace(".", "-")))
    return len(ct), len(flows) - 1


def make_dnsmap(n):
    # a v2 name map with names for some remote IPv4 ends (exercises srvn/srvx; rdm_touch writes into it)
    import struct
    slots, esz = 2048, 80
    buf = bytearray(64 + slots * esz)
    struct.pack_into("<IIII", buf, 0, 0x324d4452, slots, esz, 1)
    return buf

outs = {}
for seed, nct, nfl in ((1, 400, 300), (3, 4000, 2500)):
    gen(seed, nct, nfl, CW + "/fx")
    for mode in ("plain", "names", "contended"):
        for v, b in bins.items():
            if os.path.exists(CW + "/dnsmap"):
                os.unlink(CW + "/dnsmap")
            e = dict(os.environ)
            if mode == "names":
                e["H_NAMES"] = "1"
                open(CW + "/dnsmap", "wb").write(make_dnsmap(0))
            lk = None
            if mode == "contended":
                lk = open(CW + "/conn.lock", "a+")
                fcntl.flock(lk, fcntl.LOCK_EX)
            subprocess.run([b, CW + "/out_" + v], env=e, capture_output=True, timeout=300)
            if lk:
                fcntl.flock(lk, fcntl.LOCK_UN); lk.close()
            outs[(seed, mode, v)] = open(CW + "/out_" + v, "rb").read()
        check("conn seed %d %s: sorted lookup == the old linear scan, byte for byte (%d bytes)" % (seed, mode, len(outs[(seed, mode, "new")])),
              outs[(seed, mode, "new")] == outs[(seed, mode, "linear")] and len(outs[(seed, mode, "new")]) > 100)
check("conn: the fixture exercises the tie-break (a reply-direction-first mutant differs)",
      any(outs[(s, "plain", "mutant")] != outs[(s, "plain", "linear")] for s in (1, 3)))

shutil.rmtree(W, ignore_errors=True)
print("FAILED: %d" % len(FAILS) if FAILS else "ALL PASS")
sys.exit(1 if FAILS else 0)
