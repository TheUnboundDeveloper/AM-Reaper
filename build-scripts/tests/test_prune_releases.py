#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The release pruner must fail CLOSED on anything it cannot plan from.

WHY THIS EXISTS. The 2026-09-12 v3.1.5 review (R08) ran build-scripts/prune_releases.sh
against fixtures and found that an empty or comment-only update manifest produced an
EMPTY keep-set - and therefore a plan that deleted every release. The script rested on
pipelines whose empty output was indistinguishable from "keep nothing". With --yes that
plan would have executed. A release tag can be re-cut; a fielded router's update path
cannot, and the manifest points every router at exactly those releases.

WHAT IT DOES. Runs the real script under bash with a fake `git` (serves a fixture
manifest) and a fake `gh` (serves a fixture release list and REFUSES any other verb, so a
deletion attempt fails the test loudly). Asserts:
  - a valid manifest plans exactly the rule: manifest-referenced + previous stable;
  - an empty manifest, a comment-only manifest, a manifest naming a release that does
    not exist, a manifest with no stable line, and a release list with no stable line
    below the manifest's are all REFUSED with a non-zero exit and no plan printed;
  - a refused plan under --yes never reaches `gh release delete`.
"""
import os, stat, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "build-scripts", "prune_releases.sh")

MANIFEST_OK = """# comment line
RT-BE96U#MCP#3.1.4#https://github.com/TheUnboundDeveloper/AM-Reaper/releases/download/v3.1.4-RT-BE96U/a.pkgtb#{h}#123
RT-BE96U#MCP-beta#3.1.5#https://github.com/TheUnboundDeveloper/AM-Reaper/releases/download/v3.1.5-beta-RT-BE96U/b.pkgtb#{h}#456
""".format(h="a" * 64)
RELEASES_OK = "v3.1.2-RT-BE96U\nv3.1.3-RT-BE96U\nv3.1.4-RT-BE96U\nv3.1.5-beta-RT-BE96U\nv3.0.9-beta-RT-BE96U\n"


def run(manifest, releases, yes=False):
    with tempfile.TemporaryDirectory(prefix="prune-test-") as td:
        binp = os.path.join(td, "bin"); os.mkdir(binp)
        mpath = os.path.join(td, "manifest.txt"); rpath = os.path.join(td, "releases.txt")
        hit = os.path.join(td, "mutation")
        with open(mpath, "w") as f: f.write(manifest)
        with open(rpath, "w") as f: f.write(releases)
        fakes = {
            "git": '#!/bin/sh\ncase " $* " in *" show "*) cat "$T_MANIFEST";; *" ls-remote "*) echo "x refs/tags/v1";; esac\nexit 0\n',
            "gh": '#!/bin/sh\ncase " $* " in *" release list "*) cat "$T_RELEASES";; *) echo "$*" >> "$T_HIT"; exit 90;; esac\n',
        }
        for name, body in fakes.items():
            p = os.path.join(binp, name)
            with open(p, "w") as f: f.write(body)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        env = dict(os.environ, PATH=binp + os.pathsep + os.environ.get("PATH", ""),
                   T_MANIFEST=mpath, T_RELEASES=rpath, T_HIT=hit)
        args = ["bash", SCRIPT] + (["--yes"] if yes else [])
        r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=60)
        mutated = os.path.exists(hit)
        return r.returncode, r.stdout, r.stderr, mutated


def main():
    failures = []
    def check(cond, msg):
        if not cond: failures.append(msg)

    rc, out, err, mut = run(MANIFEST_OK, RELEASES_OK)
    check(rc == 0, "valid manifest: exit %d, stderr=%r" % (rc, err))
    check("KEEP:" in out and "v3.1.4-RT-BE96U" in out and "v3.1.5-beta-RT-BE96U" in out and "v3.1.3-RT-BE96U" in out,
          "valid manifest: keep-set is not manifest + previous stable:\n" + out)
    check("v3.1.2-RT-BE96U" in out.split("DELETE:")[-1] and "v3.0.9-beta-RT-BE96U" in out.split("DELETE:")[-1],
          "valid manifest: the older stable and the stale beta should be planned for deletion:\n" + out)
    check("keep: 3   delete: 2" in out, "valid manifest: counts wrong:\n" + out)
    check(not mut, "valid manifest dry run must not touch gh")

    for label, manifest, releases in [
        ("empty manifest", "", RELEASES_OK),
        ("comment-only manifest", "# nothing\n\n# still nothing\n", RELEASES_OK),
        ("manifest names a missing release", MANIFEST_OK.replace("v3.1.4-RT-BE96U", "v9.9.9-RT-BE96U"), RELEASES_OK),
        ("manifest with no stable line", MANIFEST_OK.replace("RT-BE96U#MCP#3.1.4", "RT-BE96U#MCP-beta#3.1.4").replace("v3.1.4-RT-BE96U", "v3.1.4-beta-RT-BE96U"),
         RELEASES_OK.replace("v3.1.4-RT-BE96U", "v3.1.4-beta-RT-BE96U")),
        ("no previous stable below the manifest's", MANIFEST_OK, "v3.1.4-RT-BE96U\nv3.1.5-beta-RT-BE96U\n"),
        ("gh returns nothing", MANIFEST_OK, ""),
    ]:
        for yes in (False, True):
            rc, out, err, mut = run(manifest, releases, yes=yes)
            check(rc != 0, "%s%s: must be refused, exit was %d\n%s" % (label, " --yes" if yes else "", rc, out))
            check("REFUSED" in err, "%s%s: refusal must say so on stderr, got %r" % (label, " --yes" if yes else "", err))
            check("DELETE:" not in out, "%s%s: a refused run must print no plan" % (label, " --yes" if yes else ""))
            check(not mut, "%s --yes: reached gh release delete" % label)

    if failures:
        print("FAIL")
        for f in failures: print(" - " + f)
        return 1
    print("ok: prune_releases.sh fails closed on 6 unusable inputs and plans the rule on a valid one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
