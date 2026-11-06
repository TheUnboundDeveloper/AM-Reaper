#!/usr/bin/env python3
"""Security Review: world-writable, non-sticky FOLDERS under /tmp and /var (audit C-8, 2026-11-06).

rwatch's _rv_ww reported /jffs and the long-term store only. It now also lists folders under /tmp and
/var that any user may write and that lack the sticky bit (the review-2026-11-03 C-1 class: a nobody
process could hold rc's lock, redirect a mount or plant a file a root daemon trusts). Folders only (stock
files there churn); two levels; a symlinked folder is not followed and nothing under <root>/mnt (the USB
mount points) is listed, so a USB disk is never walked. Its own count (wwt / wwt_p in review.json) and its
own wording on the Firewall card (RFW_410) and the dashboard (RDSH_119): these are created that way at
every start, so the /jffs text ("the next reboot removes it") would be wrong.

The real _rv_ww and _rv_json are lifted out of rwatch.c's C literals and run under sh on a fixture tree
(RV_WWT_ROOTS points them at it). Exit 0 pass, 1 fail, 77 skipped (no router source tree).
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

rw = rd("rc/rwatch.c")
check("the review-off switch clears the new files too",
      "$RV_TMP/review.wwt $RV_TMP/wwt.said $RV_TMP/review.ww $RV_TMP/ww.said 2>/dev/null; return 0; fi" in rw)
fw, dash = rd("www/Reaper_Firewall.asp"), rd("www/Main_ReaperDash.asp")
check("Firewall card shows the count with its own text", "`<#RFW_410#>`.replace('%1',j.wwt).replace('%2',j.wwt_p||'')" in fw
      and 'id="rv_wwt"' in fw)
check("dashboard bar names it with its own text and the card sum includes it",
      "if(wwt>0)t.push(`<#RDSH_119#>`.replace('%1',wwt));" in dash and "ww=(j.ww||0)+(j.wwt||0);" in dash)
wd = os.path.join(SRC, "www")
dicts = sorted(f for f in os.listdir(wd) if f.endswith(".dict") and f != "temp.dict")
both = [d for d in dicts if re.search(r"^RFW_410=.+\n^RDSH_119=.+$", open(os.path.join(wd, d), encoding="utf-8").read(), re.M)]
check("both tokens in all %d language files, in the same order" % len(dicts), len(dicts) == 25 and both == dicts,
      sorted(set(dicts) - set(both)))

def c_text(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "".join(codecs.decode(m.group(1), "unicode_escape") for m in re.finditer(r'"((?:\\.|[^"\\])*)"', text))
w0 = rw.index('"_rv_ww() {\\n"'); w1 = rw.index('"}\\n"', rw.index('"  return 0\\n"', w0)) + 6
j0 = rw.index('"_rv_json() {\\n"'); j1 = rw.index('"}\\n"', rw.index('"    }\'\\n"', j0)) + 6
fn_ww, fn_json = c_text(rw[w0:w1]), c_text(rw[j0:j1])
check("the lifted functions are whole", fn_ww.startswith("_rv_ww() {") and fn_ww.rstrip().endswith("}")
      and fn_json.startswith("_rv_json() {") and fn_json.rstrip().endswith("}"))
check("the scan never recurses (-R) into /tmp or /var",
      "RV_WWT_ROOTS" in fn_ww and not re.search(r"ls -lanR \"?\$_r", fn_ww))

if not SH:
    print("note: no sh - the run was not done")
else:
    td = tempfile.mkdtemp()
    try:
        R = os.path.join(td, "root"); os.mkdir(R)
        def d(rel, mode):
            p = os.path.join(R, rel); os.makedirs(p, exist_ok=True); os.chmod(p, mode); return p
        d("ok", 0o755)
        d("lock", 0o777)                 # depth 1, non-sticky: reported
        d("stick", 0o1777)               # sticky: not reported
        d("ok/sub", 0o777)               # depth 2: reported
        d("ok/deep", 0o755); d("ok/deep/x", 0o777)   # depth 3: not walked
        d("mnt", 0o755); d("mnt/sda1", 0o777)        # a USB mount point: not listed
        out = os.path.join(td, "outside"); os.mkdir(out); os.chmod(out, 0o777)
        os.symlink(out, os.path.join(R, "lnk"))       # symlinked folder: not followed
        f = os.path.join(R, "file"); open(f, "w").close(); os.chmod(f, 0o666)   # files are not this check's
        tmpd = os.path.join(td, "rv"); os.mkdir(tmpd)
        empty = os.path.join(td, "empty"); os.mkdir(empty)
        script = os.path.join(td, "ww.sh")
        with open(script, "w", newline="\n") as fh:
            fh.write("RV_TMP=%s\nRV_WWT_ROOTS=%s\nlogger() { shift 2; echo \"$*\" >> $RV_TMP/syslog; }\n" % (tmpd, R)
                     + fn_ww.replace("_wr=/jffs;", "_wr=%s;" % empty) + "\n" + fn_json + "\n"
                     + "_rv_ww\n_rv_json 1 < /dev/null > $RV_TMP/review.json\n")
        run = lambda: subprocess.run([SH, script], capture_output=True, text=True)
        r = run()
        wwt = open(os.path.join(tmpd, "review.wwt")).read() if os.path.exists(os.path.join(tmpd, "review.wwt")) else ""
        check("two folders found (depth 1 and 2), the first path with them",
              r.returncode == 0 and wwt.startswith("wwt 2 ") and wwt.split(" ", 2)[2].strip() in (R + "/lock", R + "/ok/sub"), (r.stderr, wwt))
        for bad in ("stick", "deep/x", "sda1", "lnk", "outside", "/file"):
            check("not reported: " + bad, bad not in wwt)
        try:
            jj = json.load(open(os.path.join(tmpd, "review.json")))
        except Exception as e:
            jj = {"error": str(e)}
        check("review.json carries wwt / wwt_p and leaves ww alone",
              jj.get("wwt") == 2 and jj.get("wwt_p", "").startswith(R) and jj.get("ww") == 0, jj)
        log = open(os.path.join(tmpd, "syslog")).read() if os.path.exists(os.path.join(tmpd, "syslog")) else ""
        run()
        log2 = open(os.path.join(tmpd, "syslog")).read() if os.path.exists(os.path.join(tmpd, "syslog")) else ""
        check("one syslog line per change of the count", log.count("/tmp or /var") == 1 and log2 == log, log2)
        os.chmod(os.path.join(R, "lock"), 0o755); os.chmod(os.path.join(R, "ok", "sub"), 0o1777)
        run()
        jj = json.load(open(os.path.join(tmpd, "review.json")))
        check("fixed folders clear the count and its file",
              not os.path.exists(os.path.join(tmpd, "review.wwt")) and jj.get("wwt") == 0 and jj.get("wwt_p") == "", jj)
    finally:
        for root, dirs, files in os.walk(td):
            for x in dirs:
                try: os.chmod(os.path.join(root, x), 0o755)
                except OSError: pass
        shutil.rmtree(td, ignore_errors=True)

# 2026-11-06 (_r6 metal): the first read of the real box found 6 such folders, made 0777 by rc at every start
# through mkdir_if_none (it forces 0777). All are root's alone; rc takes them to 0755 right after making them.
usb, svc, sdn = rd("rc/usb.c"), rd("rc/services.c"), rd("rc/sdn.c")
mk = usb.find('mkdir_if_none("/var/cache/samba");')
pv = usb.find('chmod("/var/lib/samba/private", 0700);')
for d in ("/etc/samba", "/var/run/samba", "/var/log/samba", "/var/lib/samba", "/var/cache/samba"):
    at = usb.find('chmod("%s", 0755);' % d)
    check("Samba start: %s is taken to 0755 after rc makes it" % d, mk > 0 and pv > mk and at > pv, (mk, pv, at))
for name, src in (("services.c (main stubby)", svc), ("sdn.c (per-network stubby)", sdn)):
    check("%s: /etc/stubby is taken to 0755 right after rc makes it" % name,
          'mkdir_if_none("/etc/stubby");\n\tchmod("/etc/stubby", 0755);' in src)
check("the shared helper is left alone (45 callers, USB share folders among them)",
      'mkdir -m 0777 -p' in svc and "chmod(buf, 0777);" in rd("libdisk/disk_io_tools.c"))

print("\n%d check(s) failed" % len(fails) if fails else "\nall checks passed")
for f in fails: print("  - " + f)
sys.exit(1 if fails else 0)
