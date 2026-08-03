#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate/refresh build provenance for one release and fold it into
provenance/manifest.json + provenance/logs/<version>/.

Run in WSL after a build (the build clone + build log must be present):

    python3 build-scripts/gen_provenance.py --version v2.1.2 --commit 6c540aa1d8 \
        [--patch-count 309] [--model RT-BE96U] [--target rt-be96u]

What it does (all read-only against the build clone):
  * resolves the release/src/router and release/src-rt Git TREE hashes from the
    build commit - the content-addressed, independently-reproducible fingerprint;
  * SHA-256s the four shipped images on the firmware ladder;
  * extracts a scrubbed build + reaper_verify summary from the build log into
    provenance/logs/<version>/ (build-host path normalized to /home/builder);
  * updates the matching release entry in provenance/manifest.json in place.

--patch-count marks the release "verifiable": true (do this only once the
patches/ series has been exported up to that release, so CI can reproduce it).
Without it the entry keeps its source_tree fingerprint but stays unverifiable.
"""
import argparse, hashlib, json, os, re, subprocess, sys

# Defaults match the standard RT-BE96U layout; override per model if needed.
CLONE   = "/home/reaper/asuswrt-be96u"
LOGDIR  = "/home/reaper"   # build_<target>_Reaper_<ver>.log is written here by the build lib
LEAN    = "/mnt/c/Users/natha/AppData/Roaming/VSC/ASUS/ASUS-Merlin-Reaper"
LADDER  = "/mnt/c/Users/natha/AppData/Roaming/VSC/ASUS/asuswrt-merlin.ng/reaper-firmware"

def git(commit, path):
    return subprocess.check_output(
        ["git", "-C", CLONE, "rev-parse", f"{commit}:{path}"], text=True).strip()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def scrub(text):
    # normalize the build-host path; the "reaper" build user is not PII but we
    # keep published logs host-neutral (matches the .mailmap /home/builder rule)
    return text.replace("/home/reaper", "/home/builder")

def extract_logs(version, target):
    src = f"{LOGDIR}/build_{target}_Reaper_{version}.log"
    if not os.path.exists(src):
        print(f"  ! build log not found: {src} (skipping log extraction)")
        return None, None
    lines = open(src, encoding="utf-8", errors="replace").read().splitlines()
    build_keep, verify_keep, in_verify = [], [], False
    build_pat = re.compile(
        r"^#{4,}|MAKE_EXIT=|pass1_exit=|Done! Image 96813GW|^\s*\[OK\]|"
        r"^\s*\[ship\+MATCH\]|^== BUILD|noMCP flip|^head:")
    for ln in lines:
        if build_pat.search(ln):
            build_keep.append(ln)
        if "reaper_verify:" in ln and "====" in ln:
            in_verify = True
        if in_verify:
            verify_keep.append(ln)
        if in_verify and ln.strip() == "== VERIFY OK ==":
            in_verify = False
    outdir = f"{LEAN}/provenance/logs/{version}"
    os.makedirs(outdir, exist_ok=True)
    bpath = f"{outdir}/build-{target}.summary.log"
    vpath = f"{outdir}/reaper_verify-{target}.log"
    open(bpath, "w", encoding="utf-8").write(scrub(
        f"# Build summary for {version} (from build_{target}_Reaper_{version}.log)\n"
        "# Key lines only; build-host path normalized. Full raw log is attached to the release.\n\n"
        + "\n".join(build_keep) + "\n"))
    open(vpath, "w", encoding="utf-8").write(scrub(
        f"# reaper_verify (17-check packaging gate) for {version}\n\n"
        + "\n".join(verify_keep) + "\n"))
    print(f"  wrote {os.path.relpath(bpath, LEAN)}")
    print(f"  wrote {os.path.relpath(vpath, LEAN)}")
    return (f"provenance/logs/{version}/build-{target}.summary.log",
            f"provenance/logs/{version}/reaper_verify-{target}.log")

def collect_images(version, prefix):
    imgs = []
    for variant, tag in (("MCP", ""), ("noMCP", "_noMCP")):
        for suf in ("_nand_squashfs.pkgtb", "_nand_squashfs_loader.pkgtb"):
            fn = f"{prefix}_3006_102.8_Reaper_{version}{tag}{suf}"
            fp = os.path.join(LADDER, fn)
            if os.path.exists(fp):
                imgs.append({"model": prefix, "variant": variant,
                             "file": fn, "sha256": sha256(fp)})
            else:
                print(f"  ! image not on ladder: {fn}")
    return imgs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--patch-count", type=int, default=None)
    ap.add_argument("--model", default="RT-BE96U")
    ap.add_argument("--target", default="rt-be96u")
    a = ap.parse_args()

    router = git(a.commit, "release/src/router")
    srcrt  = git(a.commit, "release/src-rt")
    print(f"{a.version}  build_commit={a.commit}")
    print(f"  release/src/router tree = {router}")
    print(f"  release/src-rt tree     = {srcrt}")

    imgs = collect_images(a.version, a.model)
    for i in imgs:
        print(f"  image {i['variant']:5} {i['file']}  {i['sha256'][:16]}...")
    blog, vlog = extract_logs(a.version, a.target)

    mpath = f"{LEAN}/provenance/manifest.json"
    m = json.load(open(mpath))
    rel = next((r for r in m["releases"] if r["version"] == a.version), None)
    if rel is None:
        rel = {"version": a.version, "firmware": f"3006.102.8_Reaper_{a.version}"}
        m["releases"].insert(0, rel)
    rel["build_commit"] = a.commit
    rel["source_tree"] = {"release/src/router": router, "release/src-rt": srcrt}
    if imgs:
        rel["images"] = imgs
    if blog:
        rel["logs"] = {"build": blog, "verify": vlog}
    if a.patch_count is not None:
        rel["patch_count"] = a.patch_count
        rel["verifiable"] = True
        rel.pop("pending", None)
    rel.setdefault("verifiable", False)
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  updated {os.path.relpath(mpath, LEAN)} "
          f"(verifiable={rel.get('verifiable')}, patch_count={rel.get('patch_count')})")

if __name__ == "__main__":
    main()
