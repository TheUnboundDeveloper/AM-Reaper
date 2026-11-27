#!/usr/bin/env python3
"""Old local firmware images move off the WSL disk, safely (2026-11-25).

WHY. Every local build writes a versioned <MODEL>_<serial>_Reaper_v<ver>_*.pkgtb pair into targets/<platform>/ and
nothing removed them: on 2026-11-25 the trees held 882 (65 GB, back to July) and the Windows drive holding the WSL disk
file was down to 42 GB. build-scripts/reaper_prune_images.sh now runs at the end of every successful local build.

WHAT IT CHECKS, on a throw-away git repo with a second worktree (no router source needed):
(1) images older than the keep window move to the archive, byte-identical, per tree; recent ones stay; (2) the newest
N per tree stay even when old; (3) the platform's own bcm*/rootfs outputs are never touched; (4) a name already in the
archive with the same bytes is not duplicated, with different bytes it is archived beside it, never overwritten;
(5) --dry moves nothing; (6) CI and a missing Windows-side folder are no-ops; (7) a low host drive is warned about;
(8) a second run moves nothing; (9) it always exits 0; (10) the build lib calls it after BUILD OK and cannot fail on it;
(11) the script names no developer's Windows profile folder.
"""
import os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "reaper_prune_images.sh")
LIB = os.path.join(HERE, "..", "_reaper_build_lib.sh")
for tool in ("bash", "git", "cmp"):
    if not shutil.which(tool):
        print("SKIP: %s not available" % tool); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))

DAY = 86400
def mk(path, data, age_days):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f: f.write(data)
    t = time.time() - age_days * DAY
    os.utime(path, (t, t))

def run(env_extra, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("CI", "GITHUB_ACTIONS", "WSL_DISTRO_NAME")}
    env.update(env_extra)
    p = subprocess.run(["bash", SCRIPT] + list(args), env=env, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr

tmp = tempfile.mkdtemp(prefix="prune_images_")
try:
    repo, wt2, win = os.path.join(tmp, "repo"), os.path.join(tmp, "wt2"), os.path.join(tmp, "win")
    os.makedirs(repo); os.makedirs(win)
    g = lambda *a, cwd=repo: subprocess.run(["git"] + list(a), cwd=cwd, check=True, capture_output=True)
    g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    open(os.path.join(repo, "README"), "w").write("x\n"); g("add", "README"); g("commit", "-qm", "init")
    g("worktree", "add", "-q", "--detach", wt2)
    T1 = os.path.join(repo, "release", "src-rt-5.04behnd.4916", "targets", "96813GW")
    T2 = os.path.join(wt2, "release", "src-rt-5.04behnd.4916", "targets", "96813GW")
    A1, A2 = os.path.join(win, "old-local-builds", "repo"), os.path.join(win, "old-local-builds", "wt2")
    img = lambda v, s="": "RT-BE96U_3006_102.10_Reaper_v%s_BETA%s_nand_squashfs.pkgtb" % (v, s)
    mk(os.path.join(T1, img("9.0.4")), b"new-a", 1)
    mk(os.path.join(T1, img("9.0.4", "_noMCP")), b"new-b", 1)
    mk(os.path.join(T1, img("9.0.1")), b"old-1", 30)
    mk(os.path.join(T1, img("9.0.0")), b"old-0", 40)
    mk(os.path.join(T1, img("8.9.9")), b"old-dup-same", 50)
    mk(os.path.join(T1, img("8.9.8")), b"old-dup-diff", 60)
    mk(os.path.join(T1, "bcm96813GW_nand256_ubifs_update.pkgtb"), b"platform", 90)
    mk(os.path.join(T2, img("7.0.1")), b"wt-newer", 30)
    mk(os.path.join(T2, img("7.0.0")), b"wt-older", 31)
    mk(os.path.join(A1, img("8.9.9")), b"old-dup-same", 50)     # already archived, same bytes
    mk(os.path.join(A1, img("8.9.8")), b"something-else", 60)   # same name, different bytes
    base = {"WIN_ASUS_ROOT": win, "REAPER_TREE": repo, "REAPER_KEEP_DAYS": "14", "REAPER_KEEP_NEWEST": "1",
            "REAPER_HOST_DRIVE": tmp, "REAPER_HOST_MIN_GB": "0"}

    rc, out = run(base, "--dry")
    check("(5) --dry exits 0 and moves nothing", rc == 0 and os.path.exists(os.path.join(T1, img("9.0.1")))
          and not os.path.exists(os.path.join(A1, img("9.0.1"))), out)
    check("(5) --dry lists what it would move", "would move repo/" + img("9.0.1") in out, out)

    rc, out = run(dict(base, GITHUB_ACTIONS="true"))
    check("(6) a CI run is a no-op", rc == 0 and "CI run - skipped" in out and os.path.exists(os.path.join(T1, img("9.0.1"))), out)
    rc, out = run(dict(base, WIN_ASUS_ROOT=os.path.join(tmp, "absent")))
    check("(6) no Windows-side folder is a no-op", rc == 0 and "skipped" in out and os.path.exists(os.path.join(T1, img("9.0.1"))), out)

    rc, out = run(base)
    check("(9) a real run exits 0", rc == 0, out)
    ok1 = all(not os.path.exists(os.path.join(T1, img(v))) and open(os.path.join(A1, img(v)), "rb").read() == d
              for v, d in (("9.0.1", b"old-1"), ("9.0.0", b"old-0")))
    check("(1) old images moved to the archive, byte-identical, under their tree's name", ok1, out)
    check("(1) images inside the keep window stay", os.path.exists(os.path.join(T1, img("9.0.4")))
          and os.path.exists(os.path.join(T1, img("9.0.4", "_noMCP"))), out)
    check("(2) the newest image of a tree stays even when old", os.path.exists(os.path.join(T2, img("7.0.1")))
          and not os.path.exists(os.path.join(T2, img("7.0.0"))) and os.path.exists(os.path.join(A2, img("7.0.0"))), out)
    check("(3) the platform's own outputs are never touched", os.path.exists(os.path.join(T1, "bcm96813GW_nand256_ubifs_update.pkgtb")), out)
    same = [f for f in os.listdir(A1) if f.startswith(img("8.9.9")[:-6])]
    check("(4) same name + same bytes: original removed, no duplicate", not os.path.exists(os.path.join(T1, img("8.9.9"))) and len(same) == 1, same)
    diff = sorted(f for f in os.listdir(A1) if "v8.9.8" in f)
    kept_other = open(os.path.join(A1, img("8.9.8")), "rb").read() == b"something-else"
    beside = [f for f in diff if re.search(r"\.\d{8}-\d{4}\.pkgtb$", f)]
    check("(4) same name + different bytes: archived beside it, the archive copy untouched",
          kept_other and len(beside) == 1 and open(os.path.join(A1, beside[0]), "rb").read() == b"old-dup-diff"
          and not os.path.exists(os.path.join(T1, img("8.9.8"))), diff)
    check("(7) the host drive's free space is reported", "host drive " + tmp in out, out)

    rc, out2 = run(base)
    check("(8) a second run moves nothing", rc == 0 and "moved 0 images" in out2, out2)
    rc, out3 = run(dict(base, REAPER_HOST_MIN_GB="999999999"))
    check("(7) a host drive under the floor is warned about", rc == 0 and "[LOW DISK]" in out3 and "fstrim" in out3, out3)
    rc, out4 = run(base, "--bogus")
    check("(9) a bad argument exits 2 and changes nothing", rc == 2, out4)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

lib = open(LIB, encoding="utf-8").read()
ok_at = lib.find("== BUILD OK:")
hook = re.search(r'reaper_prune_images\.sh"\n\s*\[ -f "\$_pi" \] && \{ REAPER_TREE="\$R" bash "\$_pi" \|\| true; \}', lib)
check("(10) the build lib runs it after BUILD OK and cannot fail on it", ok_at > 0 and hook and hook.start() > ok_at,
      (ok_at, bool(hook)))
src = open(SCRIPT, encoding="utf-8").read()
check("(11) the script names no Windows profile folder", not re.search(r"/mnt/c/Users/(?!<)[A-Za-z0-9_.-]+/", src)
      and "C:\\Users\\" not in src)
check("(11) the script is ASCII with LF line ends", all(ord(c) < 128 for c in src) and "\r" not in src)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
