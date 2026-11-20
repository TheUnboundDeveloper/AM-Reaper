#!/usr/bin/env python3
"""reaper_symshadow - which programs in a staged router filesystem call a C-library function that a vendor library
replaces.

Why: libshared.so exports its own timer_create()/timer_settime() (shared/linux_timer_ax.c). Every program that loads
libshared before the C library gets those, not glibc's. In test image _r14 that made httpd exit on its first
connection (the vendor timer_create exits on CLOCK_MONOTONIC). A host test could not see it: it links the real C
library. This tool resolves every program's imports the way the dynamic linker does (breadth-first over DT_NEEDED,
first definition wins) and reports each import that is defined by the C library AND resolved to another library first.

Usage: reaper_symshadow.py <staged fs root> [--allow FILE] [--json OUT] [--quiet]
  --allow FILE  lines "<program path> <symbol>" or "* <symbol>" accepted as known/intended (stock behaviour)
Exit: 0 nothing new, 1 a shadowed import not in the allow list, 2 usage / tool error.
Needs: readelf (binutils) on PATH or REAPER_READELF."""
import json, os, re, subprocess, sys

READELF = os.environ.get("REAPER_READELF", "readelf")
LIBC_SONAMES = ("libc.so.", "libpthread.so.", "librt.so.", "libm.so.", "libdl.so.", "libresolv.so.", "ld-linux")
LIBDIRS = ("lib", "usr/lib", "lib/public", "lib/private", "usr/lib/public", "usr/lib/private")

def run(args):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True).stdout

def is_elf(p):
    try:
        with open(p, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False

_dyn = {}
def dynsyms(p):
    """(defined set, undefined set) of the dynamic symbol table, versions stripped."""
    if p in _dyn:
        return _dyn[p]
    d, u = set(), set()
    for ln in run([READELF, "--dyn-syms", "-W", p]).splitlines():
        f = ln.split()
        if len(f) < 8 or not f[0].rstrip(":").isdigit():
            continue
        typ, bind, ndx, name = f[3], f[4], f[6], f[7].split("@")[0]
        if not name or typ not in ("FUNC", "OBJECT", "IFUNC", "NOTYPE"):
            continue
        if ndx == "UND":
            if bind != "WEAK" or typ != "NOTYPE":
                u.add(name)
        elif bind in ("GLOBAL", "WEAK"):
            d.add(name)
    _dyn[p] = (d, u)
    return _dyn[p]

_need = {}
def needed(p):
    if p not in _need:
        _need[p] = re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", run([READELF, "-d", "-W", p]))
    return _need[p]

def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__); return 2
    root = a[0]
    allow, out_json, quiet = set(), None, "--quiet" in a
    if "--allow" in a:
        for ln in open(a[a.index("--allow") + 1]):
            ln = ln.split("#")[0].split()
            if len(ln) == 2:
                allow.add((ln[0], ln[1]))
    if "--json" in a:
        out_json = a[a.index("--json") + 1]
    # soname -> path
    lib = {}
    for d in LIBDIRS:
        dd = os.path.join(root, d)
        if os.path.isdir(dd):
            for n in os.listdir(dd):
                p = os.path.join(dd, n)
                if n not in lib and os.path.isfile(p) and is_elf(os.path.realpath(p)):
                    lib[n] = os.path.realpath(p)
    libc_defs = set()
    for n, p in lib.items():
        if n.startswith(LIBC_SONAMES):
            libc_defs |= dynsyms(p)[0]
    if not libc_defs:
        print("no C library found under %s" % root); return 2
    findings = []
    for dp, dn, fn in os.walk(root):
        for n in fn:
            p = os.path.join(dp, n)
            if os.path.islink(p) or not is_elf(p):
                continue
            rel = "/" + os.path.relpath(p, root)
            undef = dynsyms(p)[1] & libc_defs
            if not undef:
                continue
            # breadth-first load order, as ld.so does
            order, seen, q = [], set(), list(needed(p))
            while q:
                s = q.pop(0)
                if s in seen or s not in lib:
                    continue
                seen.add(s); order.append(s); q.extend(needed(lib[s]))
            for sym in sorted(undef):
                for s in order:
                    if sym in dynsyms(lib[s])[0]:
                        if not s.startswith(LIBC_SONAMES):
                            findings.append((rel, sym, s))
                        break
    new = [f for f in findings if (f[0], f[1]) not in allow and ("*", f[1]) not in allow]
    if out_json:
        json.dump([{"program": f[0], "symbol": f[1], "resolved_to": f[2]} for f in findings], open(out_json, "w"), indent=1)
    if not quiet:
        by = {}
        for prog, sym, s in findings:
            by.setdefault((sym, s), []).append(prog)
        for (sym, s), progs in sorted(by.items()):
            mark = "NEW " if any((p, sym) not in allow and ("*", sym) not in allow for p in progs) else "ok  "
            print("%s%-22s -> %-22s %3d program(s): %s" % (mark, sym, s, len(progs), " ".join(sorted(progs)[:6]) + (" ..." if len(progs) > 6 else "")))
    print("symshadow: %d shadowed import(s) in %d program(s); %d not in the allow list" % (
        len(findings), len({f[0] for f in findings}), len(new)))
    return 1 if new else 0

if __name__ == "__main__":
    sys.exit(main())
