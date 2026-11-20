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
  held (v1.15)         a zone ACCEPT the guest isolation layer keeps closed is its own state on
                       every surface (walker, page, dashboard, diag, MCP text), never red, never
                       an alarm; RFW_417-419 in all 25 packs
  guest paths (v1.16)  G5 / G6 / F2 reverse rows add no state: held stays F2-only and is
                       never set on a row the zone switch should have opened

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
check("rwatch 3g: logs one advisory line per change", 'firewall witnesses (advisory)' in rw and "/tmp/reaper/rwatch_witness" in rw)
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
check("dashboard: the dead rail badge is gone - no setter, no .nbadge CSS, no data-fwred span (Q-C2-8, 2026-11-05)",
      "setFwBadge" not in dash and "nbadge" not in dash and "fwred" not in dash)
check("dashboard: the row still reads the CACHED report (no run=1)", "action=witness&http_id" in dash and "action=witness&run=1" not in dash)

sh = rd(router, "www", "reaper_shell.asp")
check("shell: no witness poll at all (the request, not the word - the comment may explain why it is gone)", "/reaper_fw.cgi?action=witness" not in sh)
check("shell: the dead rail badge is gone - no FW_RED, no setter, no .nbadge CSS, no data-fwred span (Q-C2-8, 2026-11-05)",
      "setFwBadge" not in sh and "FW_RED" not in sh and "nbadge" not in sh and "fwred" not in sh)

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

# v1.15 (image 1, 2026-11-19): the third outcome "held" - a zone policy ACCEPT the guest isolation layer keeps
# closed by design. It is never red and never an alarm on any surface, and no surface shows it as green or breaks
# on it (a consumer that does not know a state must fall back to a neutral one).
check("walker: summary carries held, and total stays every row", '\\"red\\":%d,\\"held\\":%d,' in fw and "nwit, green, red, held, dep, na);" in fw)
check("walker: held is its own state, after green and before red", 'w->ok ? "green" : w->held ? "held" : "red"' in fw)
check("walker: the text report counts and marks held rows", "%d red, %d held, %d depends" in fw and 'w->held ? "HELD" : "RED"' in fw)
check("firewall page: held rows get the outlined amber pill, never the red one",
      "held:['h',`<#RFW_417#>`]" in fp and ".wpill.h{" in fp and "--danger" not in fp.split(".wpill.h{", 1)[1].split("}", 1)[0])
check("firewall page: an unknown state falls back to Not applicable, never to OK", "var st=WT_STATE[w.state]||WT_STATE.na;" in fp)
check("firewall page: the summary counts held, the legend explains it, the row shows its note",
      "g+=kvRow(`<#RFW_417#>`,(s.held||0)>0?'warn':'off',String(s.held||0));" in fp and '<p class="note"><#RFW_418#></p>' in fp
      and "(w.state==='held'&&w.rule&&w.note?'<div class=\"whn\">'+esc(w.note)+'</div>':'')" in fp and fp.count("REAPER-FWSIM-HELD") == 1)
check("firewall page: the Status note and the confirm preview add the held count (RFW_419), red stays uncoloured",
      "+((s.held||0)>0?(' &middot; '+(s.held||0)+' '+esc(`<#RFW_419#>`)):'')" in fp and "+(held>0?(' &middot; '+held+' '+esc(`<#RFW_419#>`)):'')" in fp)
check("dashboard: held is counted in the line, the pill still keys off red only",
      "+ ((s.held||0)>0 ? (' \\u00b7 '+(s.held||0)+' '+`<#RFW_417#>`) : '')" in dash and "tag.className = 'tag '+(skel ? 'warn' : (red>0 ? 'adv' : 'ok'));" in dash)
check("diag 14g: HELD rows are listed with their note, never as a finding",
      "grep -A3 '^  [A-Za-z0-9.]* *HELD '" in dg and dg.count("REAPER-FWSIM-HELD") == 1 and "finding WARN \"firewall witnesses" not in dg
      and 'finding INFO "firewall witnesses (advisory): $_held' not in dg)
check("rwatch 3g: only red rows reach its advisory line (held is by design)", '"state":"red"' in rw.replace('\\"', '"') and "held" not in rw.split("3g) firewall witnesses", 1)[1][:1500])
check("rmcpd: the tool description names the held state", "state (green/red/held/depends/na;" in mc)
bad = []
for p in packs:
    lines = rd(p).split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("RFW_417=")]
    if len(idx) != 1 or not lines[idx[0] + 1].startswith("RFW_418=") or not lines[idx[0] + 2].startswith("RFW_419="):
        bad.append(os.path.basename(p)); continue
    vals = [lines[idx[0] + k].split("=", 1)[1] for k in range(3)]
    if sum(1 for l in lines if l.startswith(("RFW_417=", "RFW_418=", "RFW_419="))) != 3 or not all(vals) \
       or any(c in v for v in vals for c in ("`", "${", '"', "'")):
        bad.append(os.path.basename(p))
check("dicts: RFW_417 / RFW_418 / RFW_419 once each, in order, non-empty, safe in a template literal, in all 25 packs", not bad, bad)

# v1.16 (image 2, 2026-11-19): the opt-in guest paths add rows (G5 chosen devices, G6 discovery, F2.Nr reverse
# companions) but no new state and no new surface: held stays F2-only and is never set while the Firewall switch says
# the path should be open (that row is judged - red is still only an advisory count); a G5 row decided by the admin's
# own engine rule carries a note, printed in the text report like a held note, never a finding.
check("walker v1.16: held is still F2-only, and never set on a row the zone switch should have opened",
      '!w->noheld && !strncmp(w->id, "F2.", 3) && !strcmp(want, "ACCEPT")' in fw and "zw->noheld = 1;" in fw)
check("walker v1.16: the text report prints any row's note (held, or a G5 row an engine rule decided)",
      'if (w->note[0]) printf("          note: %s\\n", w->note);' in fw and 'if (w->held && w->note[0])' not in fw)
check("walker v1.16: the summary states are unchanged (green / red / held / depends / na)",
      fw.count('w->na ? "na" : w->dep ? "depends" : w->ok ? "green" : w->held ? "held" : "red"') == 1)

mk = rd(lean, "verify_markers.txt")
check("markers: the rwatch marker follows the rename", "sbin/rc|firewall witnesses (advisory)|1" in mk and "witness-red" not in mk)

if fails:
    print("\n%d check(s) failed:\n  " % len(fails) + "\n  ".join(fails)); sys.exit(1)
print("all checks passed: the walker is advisory on every surface it feeds")
