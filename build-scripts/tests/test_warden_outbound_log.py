"""Prove warden-outbound-log actually catches the regressions it claims to.

Run:  python3 build-scripts/tests/test_warden_outbound_log.py
      REAPER_ROUTER_SRC=/home/reaper/port/rt-be88u/release/src/router python3 ...

Exit 0 = the baseline passes AND every scenario is caught.

Builds a throwaway router dir holding just the four files the check reads,
mutates ONE thing per scenario - each one a real regression this class has
suffered or could suffer - and asserts the check fails with the right reason.
A regression check that has never been observed to fail is not evidence."""
import importlib.util
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "rsc", os.path.join(HERE, os.pardir, "reaper_static_checks.py"))
rsc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rsc)

# the router source to test against; override for a sibling worktree
SRC = os.environ.get("REAPER_ROUTER_SRC",
                     "/home/reaper/asuswrt-be96u/release/src/router")
FILES = ["rc/rwarden.c", "rc/rwatch.c", "www/Reaper_Firewall.asp", "httpd/web.c"]

# This suite reads canon router source, which is on a maintainer's machine but
# NOT on a CI runner that checks out the lean repo (it carries patches, not a
# source tree). Exit 77 - the autotools "skipped" convention - rather than
# fail: an absent tree means "nothing to check here", which is different from
# a regression, and different again from a pass. The CI step counts skips
# separately and refuses a run in which NOTHING executed, so a skip can never
# be mistaken for a green gate.
EXIT_SKIP = 77


def _unavailable():
    if not os.path.isdir(SRC):
        return "no router source tree at %s" % SRC
    missing = [r for r in FILES if not os.path.isfile(os.path.join(SRC, r))]
    if missing:
        return "%s is missing %s" % (SRC, ", ".join(missing))
    return None


_why = _unavailable()
if _why:
    print("SKIP test_warden_outbound_log: %s" % _why)
    print("     set REAPER_ROUTER_SRC=<router source tree> to run it")
    sys.exit(EXIT_SKIP)


def build(tmp):
    for rel in FILES:
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(SRC, rel), dst)
    return tmp


def mutate(tmp, rel, old, new, count=1):
    """count=None replaces every occurrence."""
    p = os.path.join(tmp, rel)
    s = io.open(p, encoding="utf-8", errors="surrogateescape", newline="").read()
    n = s.count(old)
    assert n >= (count or 1), "scenario setup failed: %r x%d in %s" % (old[:60], n, rel)
    out = s.replace(old, new) if count is None else s.replace(old, new, count)
    io.open(p, "w", encoding="utf-8", errors="surrogateescape", newline="").write(out)


SCENARIOS = []


def scenario(name, expect):
    def deco(fn):
        SCENARIOS.append((name, fn, expect))
        return fn
    return deco


@scenario("outbound drops jump back to the shared inbound target (the v2.4.2 regression)",
          "no longer targets")
def s1(tmp):
    mutate(tmp, "rc/rwarden.c",
           'rw_emit_dst_group(f, "iptables", "RW_OUT", "RW_ODROP", 0);',
           'rw_emit_dst_group(f, "iptables", "RW_OUT", "RW_DROP", 0);')


@scenario("only the IPv4 dst group is reverted (half-regression)", "no longer targets")
def s1b(tmp):
    mutate(tmp, "rc/rwarden.c",
           'rw_emit_dst_group(f, "iptables", "RW_OUT", "RW_ODROP", 0);',
           'rw_emit_dst_group(f, "iptables", "RW_OUT", "RW_DROP", 0);')


@scenario("one stack loses its outbound dst group entirely", "has lost its outbound")
def s1c(tmp):
    mutate(tmp, "rc/rwarden.c",
           '\t\trw_emit_dst_group(f, "ip6tables", "RW_OUT", "RW_ODROP", 1);\n', "")


@scenario("the outbound LOG rule is deleted", "drops but never logs")
def s2(tmp):
    mutate(tmp, "rc/rwarden.c",
           '\t\t\tfprintf(f, "iptables -A RW_ODROP -j LOG --log-prefix '
           '\\"REAPER-WARDEN-OUT \\" --log-level 4\\n");\n', "")


@scenario("the outbound prefix is reverted to the inbound one", "no longer emits")
def s3(tmp):
    mutate(tmp, "rc/rwarden.c", 'REAPER-WARDEN-OUT ', 'REAPER-WARDEN ', None)


@scenario("REAPER_WARDEN stops jumping to RW_OUT (chain unreachable)", "unreachable")
def s4(tmp):
    mutate(tmp, "rc/rwarden.c",
           '"iptables -A REAPER_WARDEN -j RW_OUT\\n"',
           '"iptables -A REAPER_WARDEN -j RETURN\\n"')
    mutate(tmp, "rc/rwarden.c",
           '"ip6tables -A REAPER_WARDEN -j RW_OUT\\n"',
           '"ip6tables -A REAPER_WARDEN -j RETURN\\n"')


@scenario("RW_ODROP dropped from the counter-zeroing loop", "omits RW_ODROP")
def s5(tmp):
    mutate(tmp, "rc/rwarden.c",
           "for C in RW_DROP RW_SDROP RW_ODROP REAPER_WARDEN RW_OUT RW_SELF; do",
           "for C in RW_DROP RW_SDROP REAPER_WARDEN RW_OUT RW_SELF; do")


@scenario("the viewer collapses all three prefixes into one badge (today's regression)",
          "does not test for")
def s6(tmp):
    mutate(tmp, "www/Reaper_Firewall.asp",
           "  if(line.indexOf('REAPER-WARDEN-OUT')>=0)return {c:'warden',t:'WARDEN-OUT'};\n"
           "  if(line.indexOf('REAPER-WARDEN-SELF')>=0)return {c:'warden',t:'WARDEN-SELF'};\n",
           "")


@scenario("the viewer tests the bare stem first (longer prefixes unreachable)",
          "can never be reached")
def s7(tmp):
    mutate(tmp, "www/Reaper_Firewall.asp",
           "  if(line.indexOf('REAPER-WARDEN-OUT')>=0)return {c:'warden',t:'WARDEN-OUT'};\n"
           "  if(line.indexOf('REAPER-WARDEN-SELF')>=0)return {c:'warden',t:'WARDEN-SELF'};\n"
           "  if(line.indexOf('REAPER-WARDEN')>=0)return {c:'warden',t:'WARDEN'};\n",
           "  if(line.indexOf('REAPER-WARDEN')>=0)return {c:'warden',t:'WARDEN'};\n"
           "  if(line.indexOf('REAPER-WARDEN-OUT')>=0)return {c:'warden',t:'WARDEN-OUT'};\n"
           "  if(line.indexOf('REAPER-WARDEN-SELF')>=0)return {c:'warden',t:'WARDEN-SELF'};\n")


@scenario("the outbound LOG loses the rwarden_log gate", "not gated on rwarden_log")
def s8(tmp):
    mutate(tmp, "rc/rwarden.c",
           '\t\tif (nvram_match("rwarden_log", "1"))\n'
           '\t\t\tfprintf(f, "iptables -A RW_ODROP -j LOG',
           '\t\tif (nvram_match("rwarden_verbose", "1"))\n'
           '\t\t\tfprintf(f, "iptables -A RW_ODROP -j LOG')


@scenario("rwatch stops reporting the outbound state", "no longer inspects RW_ODROP")
def s9(tmp):
    mutate(tmp, "rc/rwatch.c", "RW_ODROP", "RW_XDROP", None)


# ---- baseline -------------------------------------------------------------
tmp = build(tempfile.mkdtemp(prefix="wchk_base_"))
ok, summary, details = rsc.check_warden_outbound_log(tmp)
print("BASELINE (unmodified tree): %s -- %s" % ("PASS" if ok else "FAIL", summary))
for d in details:
    print("    %s" % d)
shutil.rmtree(tmp)
if not ok:
    sys.exit("baseline must pass before the scenarios mean anything")

fails = 0
for name, fn, expect in SCENARIOS:
    tmp = build(tempfile.mkdtemp(prefix="wchk_"))
    try:
        fn(tmp)
        ok, summary, details = rsc.check_warden_outbound_log(tmp)
        blob = " | ".join(details)
        caught = (not ok) and (expect in blob)
        print("%-4s %s" % ("OK" if caught else "MISS", name))
        if not caught:
            fails += 1
            print("       got: %s / %s" % (summary, blob[:200]))
        else:
            hit = [d for d in details if expect in d][0]
            print("       -> %s" % hit[:150])
    finally:
        shutil.rmtree(tmp)

print("\n%d scenario(s) not caught" % fails)
sys.exit(1 if fails else 0)
