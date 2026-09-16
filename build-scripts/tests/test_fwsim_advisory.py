#!/usr/bin/env python3
"""The firewall walker is ADVISORY by design (owner, 2026-09-16): passive and
informative, never actionable or authoritative. This suite pins the posture on
every surface the walker feeds, so a later edit cannot quietly turn a red COUNT
back into an alarm:

  rc/rwatch.c          3g never adds witness-red to FAIL (no FAILURE latch, no
                       incident bundle) - it logs one advisory line per change
  others/reaper_diag   the red count is an INFO finding, never WARN
  rmcpd/rmcpd.c        the tool description says advisory
  reaper_fwsim.c       the report carries mode=advisory
  Main_ReaperDash.asp  a red count is a steel Advisory pill, never .danger; the
                       rail badge setter is a no-op
  reaper_shell.asp     the shell no longer polls the witness report at all
  Reaper_Firewall.asp  the tab carries the advisory banner (RFW_320); the
                       Status note and the confirm preview never colour the
                       count red
  *.dict               RFW_319 / RFW_320 present exactly once in all 25 packs
  verify_markers.txt   the rwatch marker follows the rename

Arg: release/src/router. Exit 0 pass, 1 fail, 77 skipped (no source tree)."""
import glob, os, sys

router = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not router or not os.path.isfile(os.path.join(router, "rc", "rwatch.c")):
    print("skip: pass release/src/router (or set REAPER_ROUTER_SRC)"); sys.exit(77)
lean = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))
def rd(*p):
    with open(os.path.join(*p), encoding="utf-8", errors="replace") as f: return f.read()

rw = rd(router, "rc", "rwatch.c")
check("rwatch 3g: witness-red is never appended to FAIL", "witness-red" not in rw)
check("rwatch 3g: logs one advisory line per change", 'firewall witnesses (advisory)' in rw and "/tmp/rwatch_witness" in rw)
check("rwatch 3g: still re-walks (the report stays fresh with nobody looking)", "/usr/bin/reaper_fwsim --run" in rw)

dg = rd(router, "others", "reaper_diag")
check("diag 14g: the red count is INFO", 'finding INFO "firewall witnesses (advisory)' in dg)
check("diag 14g: never WARN on a red count", 'finding WARN "firewall witnesses:' not in dg)
check("diag 14g: the boot skeleton stays WARN (a real fault class, R15)", "finding WARN \"firewall: the filter table is the boot skeleton" in dg)

mc = rd(router, "rmcpd", "rmcpd.c")
check("rmcpd: get_firewall_status describes itself as advisory", "mode=advisory" in mc and "nothing is ever re-applied" in mc)

fw = rd(router, "reaper_fwsim", "reaper_fwsim.c")
check("walker: the report carries mode=advisory", '\\"mode\\":\\"advisory\\"' in fw)
check("walker: the text report says advisory", "[advisory: information only, nothing re-applied]" in fw)

dash = rd(router, "www", "Main_ReaperDash.asp")
check("dashboard: a red count is the steel Advisory pill, never .danger", "'adv' : 'ok'" in dash and "((skel||red>0) ? 'danger'" not in dash)
check("dashboard: the .tag.adv style exists", ".tag.adv{" in dash)
check("dashboard: the rail badge setter is a no-op", "function setFwBadge(red){}" in dash)
check("dashboard: the row still reads the CACHED report (no run=1)", "action=witness&http_id" in dash and "action=witness&run=1" not in dash)

sh = rd(router, "www", "reaper_shell.asp")
check("shell: no witness poll at all (the request, not the word - the comment may explain why it is gone)", "/reaper_fw.cgi?action=witness" not in sh)
check("shell: setFwBadge survives as a no-op for railFallback()", "function setFwBadge(red){ FW_RED=red; }" in sh)

fp = rd(router, "www", "Reaper_Firewall.asp")
check("firewall page: the advisory banner is on the Rule Status tab", "<#RFW_320#>" in fp)
check("firewall page: the Status note and confirm preview never colour the count red", "var(--danger)':'var(--jade)')+'\">'+red" not in fp)
check("firewall page: only the boot skeleton is a warning on the Status note", "el.className='note'+(skel?' warn':'');" in fp)

packs = sorted(p for p in glob.glob(os.path.join(router, "www", "*.dict")) if not p.endswith("temp.dict"))
check("dicts: 25 packs", len(packs) == 25, len(packs))
bad = []
for p in packs:
    d = rd(p)
    if d.count("\nRFW_319=") != 1 or d.count("\nRFW_320=") != 1: bad.append(os.path.basename(p))
check("dicts: RFW_319 and RFW_320 exactly once in every pack", not bad, bad)

mk = rd(lean, "verify_markers.txt")
check("markers: the rwatch marker follows the rename", "sbin/rc|firewall witnesses (advisory)|1" in mk and "witness-red" not in mk)

if fails:
    print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
print("all checks passed: the walker is advisory on every surface it feeds")
