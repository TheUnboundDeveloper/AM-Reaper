#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""What may sit AHEAD of the Reaper front chains is decided by one classifier in two
generated scripts, and both must give the answers the firewall depends on.

WHY THIS EXISTS. hook.sh (rc/reaper_hook.c, _front_pos) re-pins the Reaper front jump
behind any rule it judges harmless, and rwatch 3d (rc/rwatch.c) reports drift by the same
judgement. A rule judged "narrow" that is not stays ahead of Warden, Gatekeeper and the
rules engine for good - the crawl of 2026-09-26 (F3) found a port-only ACCEPT in FORWARD
treated that way. The narrowness patterns now live in ONE place (rc/reaper_hook.h,
REAPER_FCNARROW_IO / _FWD) and both emitters use them; this pins what they mean.

WHAT IT DOES. Lifts the generated shell out of the two C sources (the C string literal of
each fputs(), macros resolved from reaper_hook.h), runs the classifier under /bin/sh with
a fake `iptables -S` fed from fixtures, and checks: a port-only ACCEPT in FORWARD is
displaced (hook lands at 1, rwatch reports drift), an interface-only or negated one too,
a source-only ACCEPT anywhere; a destination carve-out (REAPER_DNSV), the lab's
`-i br0 --dport` in INPUT, a terminal DROP, a chain that only RETURNs/DROPs (F3b - a RETURN
inside a user chain resumes the base chain and cannot bypass us) and a declared chain are
tolerated; and the two emitters carry byte-identical patterns and _fc_narrow bodies.
Exit 0 pass, 1 fail, 77 skipped (no router source tree - pass release/src/router as argv[1]
or REAPER_ROUTER_SRC - or no /bin/sh).
"""
import os, re, subprocess, sys, tempfile, shutil

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

def die(msg):
    print("FAIL: " + msg); sys.exit(1)

src_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
hook_c = os.path.join(src_root, "rc", "reaper_hook.c") if src_root else ""
hook_h = os.path.join(src_root, "rc", "reaper_hook.h") if src_root else ""
rwatch_c = os.path.join(src_root, "rc", "rwatch.c") if src_root else ""
if not hook_c or not os.path.isfile(hook_c):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
for p in (hook_h, rwatch_c):
    if not os.path.isfile(p):
        die("missing " + p)
SH = "/bin/sh" if os.path.exists("/bin/sh") else shutil.which("sh")
if not SH:
    skip("no /bin/sh to run the lifted shell")

def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()

# ---- the string macros of reaper_hook.h, resolved in order
def macros_of(header):
    m = {}
    for line in header.splitlines():
        mm = re.match(r'\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*)$', line)
        if not mm: continue
        name, rest = mm.group(1), mm.group(2)
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"|([A-Za-z_][A-Za-z0-9_]*)', rest)
        if not parts or not any(s for s, _ in parts): continue
        val = ""
        okay = True
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
            out.append(table.get(s[i + 1], "\\" + s[i + 1])); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)

# the C string-literal concatenation of the fputs() call that contains `needle`
def lifted_script(csrc, needle, macros):
    at = csrc.find(needle)
    if at < 0: die("%r not found in the generator" % needle)
    start = csrc.rfind("fputs(", 0, at)
    end = csrc.find(", f);", at)
    if start < 0 or end < 0: die("could not frame the fputs() around %r" % needle)
    body = csrc[start + 6:end]
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)          # C comments between the pieces
    text = ""
    for s, ident in re.findall(r'"((?:[^"\\]|\\.)*)"|([A-Za-z_][A-Za-z0-9_]*)', body):
        if ident:
            # a macro from another header (REAPER_NV_HELPER, the _nv shell helper from
            # rc/reaper_nv.h) is outside the units lifted here; it drops out as empty
            text += macros.get(ident, "")
        else:
            text += c_unescape(s)
    return text

macros = macros_of(read(hook_h))
for k in ("REAPER_FCNARROW_IO", "REAPER_FCNARROW_FWD", "REAPER_FRONT_EXEMPT"):
    if k not in macros: die("reaper_hook.h no longer defines %s" % k)
hook_sh = lifted_script(read(hook_c), "_front_pos()", macros)
rwatch_sh = lifted_script(read(rwatch_c), "FCNARROW='", macros)

def between(text, a, b, what):
    i = text.find(a)
    if i < 0: die("%s: %r not found" % (what, a))
    j = text.find(b, i)
    if j < 0: die("%s: %r not found after %r" % (what, b, a))
    return text[i:j + len(b)]

# ---- 1. lockstep: both emitters carry the same patterns and the same _fc_narrow
hook_fc = between(hook_sh, "FCNARROW='", "\n}\n", "hook.sh")
rw_fc = between(rwatch_sh, "FCNARROW='", "\n}\n", "rwatch")
passed = 0
def ok(cond, what):
    global passed
    if not cond: die(what)
    passed += 1
ok(hook_fc == rw_fc, "the FCNARROW patterns / _fc_narrow body differ between hook.sh and rwatch 3d:\n--- hook.sh\n%s\n--- rwatch\n%s" % (hook_fc, rw_fc))
ok("FCNARROW='%s'" % macros["REAPER_FCNARROW_IO"] in hook_fc and "FCNARROW_F='%s'" % macros["REAPER_FCNARROW_FWD"] in hook_fc,
   "the generated FCNARROW lines are not the reaper_hook.h macros")
ok("-j ACCEPT$" in hook_fc and "RETURN" not in hook_fc.split("_fc_narrow()")[1],
   "_fc_narrow must count a chain's ACCEPTs only (a RETURN inside a user chain cannot bypass the base chain)")

# ---- the lifted units: hook.sh's _front_pos; rwatch's per-base-chain loop
front_pos = between(hook_sh, "_front_pos() {", "\n}\n", "hook.sh _front_pos")
rw_loop = between(rwatch_sh, "  for HP in INPUT:", "\n  done\n", "rwatch 3d loop")

FAKE = r'''
iptables() {
  [ "$1" = "-S" ] || return 0
  case "$2" in
    INPUT) printf '%s\n' "$FX_INPUT";;
    FORWARD) printf '%s\n' "$FX_FORWARD";;
    OUTPUT) printf '%s\n' "$FX_OUTPUT";;
    *) eval "_v=\${FX_$2:-}"; [ -n "$_v" ] || return 1; printf '%s\n' "$_v";;
  esac
}
'''

def run_sh(script, env):
    e = dict(os.environ); e.update(env)
    p = subprocess.run([SH, "-c", script], capture_output=True, text=True, env=e, timeout=30)
    if p.returncode != 0 and p.stderr:
        die("lifted shell failed:\n%s\n--- script\n%s" % (p.stderr, script))
    return p.stdout

def hook_pos(chain, hook, fixtures, fex=""):
    script = FAKE + 'FEX="%s"\n' % fex + hook_fc + "\n" + front_pos + '\n_front_pos iptables %s %s\n' % (chain, hook)
    return run_sh(script, fixtures).strip()

def rwatch_verdict(fixtures, fex=""):
    script = (FAKE + 'T=iptables; FEX="%s"; CHDRIFT=""; FCTOL=""; UP=99999; HEALGRACE=0\n' % fex
              + hook_fc + "\n" + rw_loop + '\necho "DRIFT=$CHDRIFT"\necho "TOL=$FCTOL"\n')
    out = run_sh(script, fixtures)
    d = re.search(r"^DRIFT=(.*)$", out, re.M); t = re.search(r"^TOL=(.*)$", out, re.M)
    return (d.group(1).strip() if d else "?", t.group(1).strip() if t else "?")

def fx(**chains):
    """fixtures: base chains always carry a policy line first, the hooks are present"""
    base = {"FX_INPUT": "-P INPUT ACCEPT\n-A INPUT -j REAPER_HOOK",
            "FX_FORWARD": "-P FORWARD ACCEPT\n-A FORWARD -j REAPER_HOOK_F",
            "FX_OUTPUT": "-P OUTPUT ACCEPT\n-A OUTPUT -j REAPER_HOOK_O"}
    for k, v in chains.items():
        base["FX_" + k] = v
    return base

DNSV = "-N REAPER_DNSV\n-A REAPER_DNSV -d 10.20.0.98/32 -p udp -m udp --dport 53 -j ACCEPT\n-A REAPER_DNSV -d 10.20.0.98/32 -p tcp -m tcp --dport 53 -j ACCEPT"
SKYNET = "-N Skynet\n-A Skynet -m set --match-set Skynet-Whitelist src -j RETURN\n-A Skynet -m set --match-set Skynet-Blacklist src -j DROP\n-A Skynet -m set --match-set Skynet-Blacklist dst -j DROP"
BROAD = "-N Wide\n-A Wide -m set --match-set Trusted src -j ACCEPT"

cases = [
    # (name, chain, hook, base listing (without policy line), extra chains, fex, expected hook pos, expect drift?)
    ("port-only ACCEPT in FORWARD is displaced",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -p tcp -m tcp --dport 443 -j ACCEPT\n-A FORWARD -j REAPER_HOOK_F", {}, "", "1", True),
    ("destination carve-out chain (REAPER_DNSV) in FORWARD is tolerated",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -j REAPER_DNSV\n-A FORWARD -j REAPER_HOOK_F", {"REAPER_DNSV": DNSV}, "", "2", False),
    ("the lab rule (-i br0 --dport 5219) in INPUT is tolerated",
     "INPUT", "REAPER_HOOK", "-A INPUT -i br0 -p tcp -m tcp --dport 5219 -j ACCEPT\n-A INPUT -j REAPER_HOOK", {}, "", "2", False),
    ("a chain that only RETURNs and DROPs (Skynet shape) is tolerated (F3b)",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -j Skynet\n-A FORWARD -j REAPER_HOOK_F", {"Skynet": SKYNET}, "", "2", False),
    ("a chain with an unqualified ACCEPT is displaced",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -j Wide\n-A FORWARD -j REAPER_HOOK_F", {"Wide": BROAD}, "", "1", True),
    ("interface-only ACCEPT in FORWARD is displaced",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -i br0 -j ACCEPT\n-A FORWARD -j REAPER_HOOK_F", {}, "", "1", True),
    ("a negated destination narrows nothing",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD ! -d 10.0.0.1/32 -j ACCEPT\n-A FORWARD -j REAPER_HOOK_F", {}, "", "1", True),
    ("source-only ACCEPT in INPUT is displaced",
     "INPUT", "REAPER_HOOK", "-A INPUT -s 1.2.3.4/32 -j ACCEPT\n-A INPUT -j REAPER_HOOK", {}, "", "1", True),
    ("inline destination ACCEPT in FORWARD is tolerated",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -d 10.20.0.98/32 -j ACCEPT\n-A FORWARD -j REAPER_HOOK_F", {}, "", "2", False),
    ("two tolerated rules ahead: a carve-out then a DROP",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -j REAPER_DNSV\n-A FORWARD -s 5.6.7.8/32 -j DROP\n-A FORWARD -j REAPER_HOOK_F", {"REAPER_DNSV": DNSV}, "", "3", False),
    ("a declared chain is tolerated whatever it holds",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -j Wide\n-A FORWARD -j REAPER_HOOK_F", {"Wide": BROAD}, "Wide", "2", False),
    ("tolerated first, then a broad rule: the hook goes in front of the broad one",
     "FORWARD", "REAPER_HOOK_F", "-A FORWARD -j REAPER_DNSV\n-A FORWARD -p udp -m udp --dport 53 -j ACCEPT\n-A FORWARD -j REAPER_HOOK_F", {"REAPER_DNSV": DNSV}, "", "2", True),
    ("port-only ACCEPT in OUTPUT stays tolerated (the router's own services)",
     "OUTPUT", "REAPER_HOOK_O", "-A OUTPUT -p udp -m udp --dport 123 -j ACCEPT\n-A OUTPUT -j REAPER_HOOK_O", {}, "", "2", False),
]
for name, chain, hook, listing, extra, fex, want_pos, want_drift in cases:
    f = fx(**extra)
    f["FX_" + chain] = "-P %s ACCEPT\n%s" % (chain, listing)
    pos = hook_pos(chain, hook, f, fex)
    ok(pos == want_pos, "hook.sh: %s: expected position %s, got %r" % (name, want_pos, pos))
    drift, tol = rwatch_verdict(f, fex)
    ok((chain in drift) == want_drift, "rwatch 3d: %s: expected drift=%s, got DRIFT=%r TOL=%r" % (name, want_drift, drift, tol))

# a fresh table (no jump of ours yet) pins at 1
ok(hook_pos("FORWARD", "REAPER_HOOK_F", fx(FORWARD="-P FORWARD ACCEPT\n-A FORWARD -j Skynet", Skynet=SKYNET)) == "1",
   "no jump of ours in the table must answer position 1")

print("PASS: %d checks" % passed)
