#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The ALPHA test channel of the Dev-Uni branch (2026-11-14).

WHY THIS EXISTS. Dev-Uni builds every model from one source tree and publishes them for testers. Three things must
hold together, and none is visible at build time:
  1. Dev-Uni may tag and publish (always a pre-release, tags vX.Y.Z-alpha[N]-<MODEL>) but must never reach the job
     that writes the update manifest - that file is what every router reads, and Dev / Dev-102.8 keep publishing to it;
  2. the images it publishes are stamped _ALPHA (test_channel_naming.py covers the naming itself);
  3. a router running such an image looks for no update and is offered none: a Dev beta would take it off the tree
     it is testing, so the update check ends before it fetches anything.

WHAT IT DOES.
  - reads the workflows: the `tag` and `release` conditions name Dev-Uni, `refresh_manifest` does not; the build
    passes REAPER_CHANNEL=alpha for Dev-Uni only; the re-spin number reaches the shell through the step's env and is
    digits-only; a Dev-Uni publish is a pre-release;
  - with a router source tree (argv[1] or REAPER_ROUTER_SRC): lifts the gate out of reaper_webs_update.sh and runs
    it under sh with a stand-in nvram - _ALPHA and _ALPHA_noMCP end the check with channel=alpha and no offer, a
    beta or stable version string falls through; the gate sits after the state reset and before the first fetch;
    the Firmware page and all 25 language packs carry the explanation.
Exit 0 pass, 1 fail, 77 skip (never: the workflow half always runs)."""
import glob, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
fails = []
def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name); print("FAIL " + name + ((" :: " + str(detail)[:500]) if detail else ""))
def read(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read()

# ---------------------------------------------------------------- the workflows
pb = read(os.path.join(ROOT, ".github", "workflows", "public-build.yml"))
def job_if(name):
    m = re.search(r"\n  %s:\n(?:    .*\n|\n)*?    if: (.*)\n" % re.escape(name), pb)
    return m.group(1) if m else ""
UNI = "github.ref == 'refs/heads/Dev-Uni'"
check("Dev-Uni may create tags (with main and Dev, publish ticked, build green)",
      UNI in job_if("tag") and "inputs.publish" in job_if("tag") and "success()" in job_if("tag"), job_if("tag"))
check("Dev-Uni may publish releases", UNI in job_if("release") and "inputs.publish" in job_if("release"), job_if("release"))
rm = job_if("refresh_manifest")
check("the update manifest job runs for main and Dev ONLY - Dev-Uni never reaches it",
      rm == "success() && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/Dev') && inputs.publish", rm)
check("the manifest job is the only writer of updates/ in the build workflow",
      "git add updates/manifest_3006.txt" in pb and pb.index("git add updates/") > pb.index("\n  refresh_manifest:\n")
      and not re.search(r"\n  [a-z_]+:\n", pb[pb.index("\n  refresh_manifest:\n") + 5:]))
check("the build is told the channel: alpha for Dev-Uni, nothing otherwise (REAPER_BETA still decides Dev / main)",
      "-e REAPER_CHANNEL=\"${{ github.ref == 'refs/heads/Dev-Uni' && 'alpha' || '' }}\" \\" in pb
      and "-e REAPER_BETA=\"${{ github.ref == 'refs/heads/Dev' && '1' || '0' }}\" \\" in pb)
check("a Dev-Uni publish is always a pre-release",
      "prerelease: ${{ github.ref == 'refs/heads/Dev' || github.ref == 'refs/heads/Dev-Uni' }}" in pb)
check("the re-spin number reaches the shell through the step's env, never by interpolation",
      "          TEST_BUILD: ${{ inputs.test_build }}\n" in pb and "${{ inputs.test_build }}" not in pb.replace("TEST_BUILD: ${{ inputs.test_build }}", ""))
m = re.search(r'          if \[ "\$\{\{ github\.ref \}\}" = "refs/heads/Dev-Uni" \]; then\n(.*?)\n          fi\n', pb, re.S)
check("the tag step has the Dev-Uni branch", m is not None)
if m and shutil.which("bash"):
    body = "\n".join(l[12:] if l.startswith("            ") else l for l in m.group(1).split("\n"))
    def tagv(n):
        r = subprocess.run(["bash", "-c", 'set -euo pipefail\nV=v3.7.7\nTEST_BUILD="%s"\n%s\necho "$V"' % (n, body)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return r.returncode, r.stdout.strip().split("\n")[-1]
    check("tags: blank -> v3.7.7-alpha, 2 -> v3.7.7-alpha2", tagv("") == (0, "v3.7.7-alpha") and tagv("2") == (0, "v3.7.7-alpha2"), (tagv(""), tagv("2")))
    check("a re-spin number that is not digits stops the job (it would become part of a tag name)",
          tagv("2;x")[0] != 0 and tagv("-beta")[0] != 0 and tagv("a")[0] != 0, (tagv("2;x"), tagv("-beta")))
ry = read(os.path.join(ROOT, ".github", "workflows", "release.yml"))
check("release notes say what an alpha build is and that it is not in the update manifest",
      'if [ "$CHANNEL" = alpha ]; then' in ry and "It is not listed in the update manifest" in ry)
hy = read(os.path.join(ROOT, ".github", "workflows", "repo-hygiene.yml"))
check("the hygiene checks run on a push to Dev-Uni too", "branches: [main, Dev, Dev-Uni]" in hy)

# ---------------------------------------------------------------- the firmware
SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
scr = os.path.join(SRC, "rom", "webs_scripts", "reaper_webs_update.sh") if SRC else ""
if not SRC or not os.path.isfile(scr):
    print("note: no router source tree given - the firmware half is not run here (the workflow half ran)")
else:
    s = read(scr)
    g = re.search(r'\ncase "\$\(nvram get extendno\)" in\n\*_ALPHA\*\)\n.*?\nesac\n', s, re.S)
    check("reaper_webs_update.sh carries the test-build gate", g is not None)
    if g:
        check("the gate sits after the state reset and before anything is fetched",
              s.index('nvram set webs_state_channel=""') < g.start() < s.index('/usr/sbin/wget $wget_options "$MANIFEST_URL"'))
        SH = shutil.which("sh")
        def gate(ext):
            d = tempfile.mkdtemp(prefix="alpha_")
            try:
                st = os.path.join(d, "nv")
                pre = ('LOG="%s/log"\nnvram() { if [ "$1" = get ]; then [ "$2" = extendno ] && printf "%%s\\n" "%s"; '
                       'else shift; echo "$1" >> "%s"; fi; }\nlogger() { :; }\n' % (d, ext, st))
                r = subprocess.run([SH, "-c", pre + g.group(0) + "\necho REACHED\n"], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, universal_newlines=True)
                nv = open(st).read().split() if os.path.exists(st) else []
                return "REACHED" in r.stdout, nv
            finally:
                shutil.rmtree(d, ignore_errors=True)
        for ext in ("Reaper_v3.7.7_ALPHA", "Reaper_v3.7.7_ALPHA_noMCP"):
            reached, nv = gate(ext)
            check("%s: the check ends there - channel alpha, nothing offered, the page is told it finished" % ext,
                  not reached and nv == ["webs_state_channel=alpha", "webs_state_flag=0", "webs_state_update=1"], (reached, nv))
        for ext in ("Reaper_v3.7.7_BETA", "Reaper_v3.7.7", "Reaper_v3.7.7_BETA_noMCP", ""):
            reached, nv = gate(ext)
            check("%-26s falls through to the normal check, nothing set" % (ext or "(no version string)"), reached and nv == [], (reached, nv))
    pg = read(os.path.join(SRC, "www", "Reaper_Firmware.asp"))
    check("Firmware page: an alpha build is recognised, badged, and explained in place of 'up to date'",
          "var IS_ALPHA = /_ALPHA(_|$)/.test(EXTENDNO);" in pg and pg.count("<#RFWU_62#>") == 2
          and "(IS_ALPHA || FW.chan === 'alpha') ? `<#RFWU_62#>` : `<#RFWU_5#>`" in pg
          and '<span class="badge">ALPHA</span>' in pg)
    check("...and a node on a beta of the same number is not taken for the same build",
          "(/_ALPHA(_|$)/.test(String(s)) ? '-alpha' : '')" in pg)
    packs = sorted(glob.glob(os.path.join(SRC, "www", "??.dict")))
    bad = []
    for d in packs:
        t = open(d, "rb").read().decode("utf-8", "replace")
        m2 = re.search(r"^RFWU_62=(.+)$", t, re.M)
        if not m2 or any(x in m2.group(1) for x in ('"', "`", "\\", "${", "</", "'")):
            bad.append(os.path.basename(d))
    check("RFWU_62 in all %d language packs, none with a character that breaks a template string" % len(packs), len(packs) == 25 and not bad, bad)

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
