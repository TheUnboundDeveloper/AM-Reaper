"""The BETA/STABLE channel contract, across every implementation that touches it.

Run:  python3 build-scripts/tests/test_channel_naming.py
Exit: 0 = all three implementations agree and the guards refuse what they should.

Four implementations have to agree about one string, and they live in four
languages in four files. Nothing at build time compares them, so a drift shows
up as either "CI built an image it cannot find" or - worse, and silently - a
pre-release published under a stable name:

  1. build-scripts/_reaper_build_lib.sh   stamps EXTENDNO, so it NAMES the file
  2. build-scripts/ci/container_build.sh  computes the name it will look for
  3. .github/workflows/release.yml        resolves tag -> channel -> file token,
                                          and refuses assets that disagree
  4. build-scripts/stage_release.ps1      stages by channel (checked by eye; its
                                          -Channel parameter is asserted present)

Note the two deliberate spellings: the TAG segment is "-beta" (lowercase,
hyphen) and the FILE token is "_BETA" (uppercase, underscore). release.yml is
the one place that translates. See docs/RELEASE-PROCESS.md.
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8",
                   errors="surrogateescape").read()


def slice_between(text, start, end, what):
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[i:j]


def run(script, env_prefix=""):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.sh")
    io.open(p, "w", newline="\n").write(env_prefix + script)
    return subprocess.run(["bash", p], capture_output=True, text=True)


fails = []


def check(ok, label, detail=""):
    print("%-4s %s" % ("OK" if ok else "FAIL", label))
    if detail:
        print("       %s" % detail)
    if not ok:
        fails.append(label)


# =========================================================================
print("== 1. the build library and CI agree on the image name ==")
# =========================================================================
cb = read("build-scripts/ci/container_build.sh")
cb_block = slice_between(cb, 'export REAPER_BETA="${REAPER_BETA:-0}"', "\nfi\n", "cb")

lib = read("build-scripts/_reaper_build_lib.sh")
lib_args = slice_between(lib, '  for a in "$@"; do', "  done\n", "args")
lib_stamp = slice_between(lib, '  if [ "${REAPER_BETA:-1}" = "0" ]; then', "  fi\n", "stamp")


def tail_ver(out):
    return out[out.rindex("Reaper_"):].strip() if "Reaper_" in out else "<none>"


for beta, want in ((0, "Reaper_v3.1.2"), (1, "Reaper_v3.1.2_BETA")):
    cbv = tail_ver(run(cb_block + '\nprintf "%s" "$VER"\n',
                       "set -euo pipefail\nREAPER_BETA=%d\nVER=Reaper_v3.1.2\n"
                       "SHORT_VER=v3.1.2\n" % beta).stdout)
    libv = tail_ver(run(lib_args + "\n" + lib_stamp + '\nprintf "%s" "$VER"\n',
                        "set -euo pipefail\nREAPER_BETA=%d\nDO_SHIP=''\n"
                        "VER=Reaper_v3.1.2\nset --\n" % beta).stdout)
    check(cbv == libv == want, "REAPER_BETA=%d -> %s" % (beta, want),
          "container_build=%s  build-lib=%s" % (cbv, libv))

# the library must default to BETA when nothing says otherwise, and CI must
# never inherit that default
libv = tail_ver(run(lib_args + "\n" + lib_stamp + '\nprintf "%s" "$VER"\n',
                    "set -euo pipefail\nDO_SHIP=''\nVER=Reaper_v3.1.2\nset --\n").stdout)
check(libv == "Reaper_v3.1.2_BETA",
      "the build library defaults to BETA when the channel is unstated", libv)
check('export REAPER_BETA="${REAPER_BETA:-0}"' in cb,
      "CI pins the channel explicitly so it cannot inherit that default")

# =========================================================================
print("\n== 2. release.yml resolves tag -> channel -> file token ==")
# =========================================================================
ry = read(".github/workflows/release.yml")
i = ry.index("          VERSION=$(printf")
j = ry.index("\n", ry.index('echo "resolved:', i)) + 1
resolve = "\n".join(l[10:] if l.startswith("          ") else l
                    for l in ry[i:j].split("\n"))

for tag, wv, wb, wc, wf in (
        ("v3.1.2-RT-BE96U", "v3.1.2", "v3.1.2", "stable", ""),
        ("v3.1.2-beta-RT-BE96U", "v3.1.2-beta", "v3.1.2", "beta", "_BETA"),
        ("v3.1.2-beta2-GT-BE98_PRO", "v3.1.2-beta2", "v3.1.2", "beta", "_BETA"),
        ("v3.1.2a-RT-BE88U", "v3.1.2a", "v3.1.2a", "stable", ""),
        ("v3.1.2-rc1-RT-BE92U", "v3.1.2-rc1", "v3.1.2", "rc", "_RC")):
    d = tempfile.mkdtemp()
    out = os.path.join(d, "out")
    io.open(out, "w").close()
    run(resolve, 'set -euo pipefail\nTAG="%s"\nGITHUB_OUTPUT="%s"\n' % (tag, out))
    kv = dict(l.split("=", 1) for l in io.open(out).read().split("\n") if "=" in l)
    got = (kv.get("version"), kv.get("base"), kv.get("channel"), kv.get("ftok", ""))
    check(got == (wv, wb, wc, wf), "%-26s -> %s" % (tag, wc), str(got))

# =========================================================================
print("\n== 3. release.yml refuses assets that contradict the channel ==")
# =========================================================================
i = ry.index("          bad=0")
j = ry.index("\n", ry.index('echo "   channel OK:', i)) + 1
assertion = "\n".join(l[10:] if l.startswith("          ") else l
                      for l in ry[i:j].split("\n"))
N = "RT-BE96U_3006_102.8_Reaper_v3.1.2"
for chan, files, accept in (
        ("stable", [N + "_nand_squashfs.pkgtb"], True),
        ("stable", [N + "_noMCP_nand_squashfs.pkgtb"], True),
        ("beta", [N + "_BETA_nand_squashfs.pkgtb"], True),
        ("beta", [N + "_BETA_noMCP_nand_squashfs.pkgtb"], True),
        ("beta", [N + "_nand_squashfs.pkgtb"], False),
        ("stable", [N + "_BETA_nand_squashfs.pkgtb"], False),
        ("beta", [N + "_BETA_nand_squashfs.pkgtb",
                  N + "_noMCP_nand_squashfs.pkgtb"], False)):
    d = tempfile.mkdtemp()
    stage = os.path.join(d, "assets")
    os.makedirs(stage)
    for f in files:
        io.open(os.path.join(stage, f), "w").write("x")
    r = run(assertion, 'set -euo pipefail\nstage="%s"\nCHANNEL="%s"\nFTOK="%s"\n'
                       'V="v3.1.2"\n'
                       % (stage, chan, "_BETA" if chan == "beta" else ""))
    check((r.returncode == 0) == accept,
          "%-7s + %-38s -> %s" % (chan, os.path.basename(files[-1])[26:],
                                  "accept" if accept else "refuse"))

# =========================================================================
print("\n== 4. staging takes a channel ==")
# =========================================================================
ps = read("build-scripts/stage_release.ps1")
check("[ValidateSet('Beta', 'Stable')]" in ps and "$Channel = 'Beta'" in ps,
      "stage_release.ps1 has -Channel, defaulting to Beta")
check("$chanTag = if ($Channel -eq 'Beta') { '_BETA' } else { '' }" in ps,
      "stage_release.ps1 maps the channel to the same _BETA file token")

print("\n%d failure(s)" % len(fails))
sys.exit(1 if fails else 0)
