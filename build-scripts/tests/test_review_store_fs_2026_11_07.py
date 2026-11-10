#!/usr/bin/env python3
"""Security Review and rwatch CRITICAL wording (backlog P3 x3, 2026-11-07).

1. A long-term store on a volume that keeps no Unix permissions (FAT / exFAT / NTFS; the stock mount gives every
   entry 0777 and chmod cannot change it) is no longer walked by _rv_ww - a GT-BE98 field report had the
   dashboard red for /tmp/mnt/Data/.reaper/rtraf.db with no way to clear it. One `wwfs <label> <base>` line
   instead: wwfs / wwfs_p in review.json, one syslog line per change, a note on the dashboard card (RDSH_120,
   never red) and on the Firewall review panel (RFW_411). An ext store is walked as before.
2. The dashboard bar (RDSH_117) and the panel text (RFW_384) name /jffs OR the long-term store.
3. The CRITICAL block logs one line per value in its own words: chain-disarmed had read as the Warden ingest
   breach. The repair runs first and the line says whether it ran.

The real _rv_ww, _rv_json and CRITICAL block are lifted out of rwatch.c's C literals and run under sh.
Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import codecs, json, os, re, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "rc", "rwatch.c")):
    print("SKIP: no router source tree (argv[1] / REAPER_ROUTER_SRC)"); sys.exit(77)
SH = shutil.which("sh")
def rd(rel): return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

def c_text(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "".join(codecs.decode(m.group(1), "unicode_escape") for m in re.finditer(r'"((?:\\.|[^"\\])*)"', text))

rw = rd("rc/rwatch.c")
w0 = rw.index('"_rv_ww() {\\n"'); w1 = rw.index('"}\\n"', rw.index('"  return 0\\n"', w0)) + 6
j0 = rw.index('"_rv_json() {\\n"'); j1 = rw.index('"}\\n"', rw.index('"    }\'\\n"', j0)) + 6
fn_ww, fn_json = c_text(rw[w0:w1]), c_text(rw[j0:j1])
c0 = rw.index('"if [ -n \\"$CRIT\\" ]; then\\n"'); c1 = rw.index('"fi\\n"', c0) + 6
crit = c_text(rw[c0:c1])

check("the review-off switch clears the store-type files",
      "$RV_TMP/review.wwfs $RV_TMP/wwfs.said $RV_TMP/review.wwt" in rw)
check("the store type comes from the mount table (RV_MOUNTS for tests), FAT / exFAT / NTFS only",
      "${RV_MOUNTS:-/proc/mounts}" in fn_ww and "vfat|msdos|fat|tfat) _fl=FAT" in fn_ww
      and "exfat|texfat) _fl=exFAT" in fn_ww and "ntfs|ntfs3|tntfs|ufsd) _fl=NTFS" in fn_ww and "hfs" not in fn_ww)
check("CRITICAL: the old one-text line is gone", "re-applied warden chain" not in rw and "CRITICAL:$CRIT" not in rw)
check("CRITICAL: the lifted block is whole", crit.startswith("if [ -n \"$CRIT\" ]; then") and crit.rstrip().endswith("fi"), crit[-80:])

# ---------------------------------------------------------------- pages
dash, fw = rd("www/Main_ReaperDash.asp"), rd("www/Reaper_Firewall.asp")
check("dashboard card: the note follows every state of a report, never sets red by itself",
      "var fsn=j.wwfs?' - '+`<#RDSH_120#>`.replace('%1',j.wwfs):'';" in dash
      and "p.join(' - ')+fsn); return;" in dash and "`<#RDSH_113#>`+fsn); return; }" in dash
      and "toLocaleTimeString():'')+fsn);" in dash and "if(u>0||nn>0||ww>0){" in dash)
bar = dash[dash.index("window.RVJ=j;"):dash.index("x.onerror=x.ontimeout", dash.index("window.RVJ=j;"))]
check("dashboard bar: the store type never turns the bar red", "wwfs" not in bar and "RDSH_120" not in bar)
check("Firewall panel: the note element, filled by textContent, re-hidden on refresh with the /tmp,/var note",
      'id="rv_wwfs"' in fw and "$('rv_wwfs').textContent=`<#RFW_411#>`.replace(/%1/g,j.wwfs).replace('%2',j.wwfs_p||'');" in fw
      and "$('rv_wwtwrap').classList.add('hidden');$('rv_wwfswrap').classList.add('hidden');" in fw)

# ---------------------------------------------------------------- packs
wd = os.path.join(SRC, "www")
dicts = sorted(f for f in os.listdir(wd) if f.endswith(".dict") and f != "temp.dict")
bad = []
for d in dicts:
    t = open(os.path.join(wd, d), encoding="utf-8").read()
    m = re.search(r"^RFW_410=.+\n^RDSH_119=.+\n^RFW_411=(.+)\n^RDSH_120=(.+)$", t, re.M)
    k117 = re.search(r"^RDSH_117=(.+)$", t, re.M); k384 = re.search(r"^RFW_384=(.+)$", t, re.M)
    if not (m and "%1" in m.group(1) and "%2" in m.group(1) and "%1" in m.group(2) and k117 and k384
            and re.search(r"/jffs \S", k117.group(1)) and re.search(r"/jffs \S", k384.group(1))):
        bad.append(d)
check("all %d packs: RFW_411 / RDSH_120 after RDSH_119, and RDSH_117 / RFW_384 name a second place" % len(dicts),
      len(dicts) == 25 and not bad, bad)
en = open(os.path.join(wd, "EN.dict"), encoding="utf-8").read()
check("EN wording", "RDSH_117=%1 file(s) or folder(s) under /jffs or the long-term store writable by any user\n" in en
      and "RFW_384=%1 file(s) or folder(s) under /jffs or the long-term store can be changed by any user" in en
      and "RDSH_120=the long-term store is on %1, which keeps no file permissions\n" in en)

# ---------------------------------------------------------------- runs
if not SH:
    print("note: no sh - the runs were not done")
else:
    td = tempfile.mkdtemp()
    try:
        mnt = os.path.join(td, "mnt")
        data, data2 = os.path.join(mnt, "Data"), os.path.join(mnt, "Data2")
        base, base2 = os.path.join(data, ".reaper"), os.path.join(data2, ".reaper")
        for b in (base, base2):
            os.makedirs(b)
            f = os.path.join(b, "rtraf.db"); open(f, "w").close(); os.chmod(f, 0o777)
        rv = os.path.join(td, "rv"); os.mkdir(rv)
        empty = os.path.join(td, "empty"); os.mkdir(empty)
        mounts = os.path.join(td, "mounts")
        def write_mounts(t1, t2="ext4"):
            with open(mounts, "w") as fh:
                fh.write("rootfs / rootfs rw 0 0\n/dev/x %s tmpfs rw 0 0\n/dev/sda1 %s %s rw,umask=0000 0 0\n"
                         "/dev/sda2 %s %s rw 0 0\n" % (td, data, t1, data2, t2))
        def run(b):
            script = os.path.join(td, "ww.sh")
            with open(script, "w", newline="\n") as fh:
                fh.write("RV_TMP=%s\nRV_WWT_ROOTS=%s\nRV_MOUNTS=%s\nBASE=%s\n" % (rv, empty, mounts, b)
                         + "logger() { shift 2; echo \"$*\" >> $RV_TMP/syslog; }\n"
                         + fn_ww.replace("_wr=/jffs;", "_wr=%s;" % empty) + "\n" + fn_json + "\n"
                         + "_rv_ww\n_rv_json 1 < /dev/null > $RV_TMP/review.json\n")
            r = subprocess.run([SH, script], capture_output=True, text=True)
            try:
                jj = json.load(open(os.path.join(rv, "review.json")))
            except Exception as e:
                jj = {"error": str(e), "stderr": r.stderr}
            return r, jj
        def slog():
            p = os.path.join(rv, "syslog")
            return open(p).read() if os.path.exists(p) else ""
        def ex(n): return os.path.exists(os.path.join(rv, n))

        write_mounts("tfat")
        r, jj = run(base)
        check("FAT store: not walked, one wwfs line, the json carries the label and the base",
              r.returncode == 0 and not ex("review.ww") and jj.get("ww") == 0 and jj.get("wwfs") == "FAT"
              and jj.get("wwfs_p") == base, (r.stderr, jj))
        l1 = slog()
        run(base)
        check("FAT store: one syslog line, not one per tick", l1.count("keeps no file permissions") == 1 and slog() == l1, slog())
        write_mounts("ntfs")
        r, jj = run(base)
        check("NTFS store: the label follows the type, one more line for the change",
              jj.get("wwfs") == "NTFS" and slog().count("keeps no file permissions") == 2, (jj, slog()))
        write_mounts("ext4")
        r, jj = run(base)
        check("ext4 store: walked as before, the file is reported and the note is gone",
              jj.get("ww") == 1 and jj.get("ww_p", "").endswith("rtraf.db") and jj.get("wwfs") == ""
              and not ex("review.wwfs") and not ex("wwfs.said"), jj)
        write_mounts("vfat", "ext4")
        r, jj = run(base2)
        check("the longest mount point wins: Data2 (ext4) is not taken for Data (vfat)",
              jj.get("ww") == 1 and jj.get("wwfs") == "", jj)
        r, jj = run("/jffs/reaper")
        check("a store on /jffs: no store type at all", jj.get("wwfs") == "" and not ex("review.wwfs"), jj)

        # CRITICAL lines
        ap = os.path.join(td, "apply.sh"); open(ap, "w").close()
        def crun(crit_v, up):
            script = os.path.join(td, "crit.sh")
            out = os.path.join(td, "crit.log")
            if os.path.exists(out): os.remove(out)
            with open(script, "w", newline="\n") as fh:
                fh.write("CRIT='%s'\nUP=%d\nHEALGRACE=300\n" % (crit_v, up)
                         + "logger() { shift 2; echo \"$*\" >> %s; }\n" % out
                         + "reaper_lockrun() { echo RAN >> %s; }\n" % out
                         + crit.replace("/tmp/rwarden/apply.sh", ap) + "\n")
            r = subprocess.run([SH, script], capture_output=True, text=True)
            return r, (open(out).read() if os.path.exists(out) else "")
        r, o = crun(" warden-poison:rw_ban chain-disarmed:iptables/RW_DROP", 900)
        ls = [l for l in o.splitlines() if l.startswith("CRITICAL")]
        check("CRITICAL: one line per value, each in its own words, after the repair ran",
              r.returncode == 0 and o.startswith("RAN\n") and len(ls) == 2
              and ls[0] == "CRITICAL: warden-poison:rw_ban - LAN/loopback found in a Warden block set (ingest filter breached); re-applied the Warden chains"
              and ls[1] == "CRITICAL: chain-disarmed:iptables/RW_DROP - a Warden drop chain holds an ACCEPT or RETURN (something else disarmed it); re-applied the Warden chains",
              (r.stderr, o))
        r, o = crun(" chain-disarmed:ip6tables/RW_SDROP", 120)
        check("CRITICAL: inside the boot grace nothing runs and the line says so",
              "RAN" not in o and o.strip().endswith("not re-applied (boot grace, or Warden is off)"), o)
        r, o = crun("", 900)
        check("CRITICAL: nothing set, nothing logged or run", o == "", o)
    finally:
        shutil.rmtree(td, ignore_errors=True)

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
