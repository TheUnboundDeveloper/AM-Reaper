#!/usr/bin/env python3
"""Shared closed objects on the alpha line: an object stays with the closed objects it shares a structure with.

WHY (field report 2026-11-25). overlays/common-blobs.list names the closed objects the models built with an older
ASUS drop take from this tree. rc's conn_diag-sql.o was on it for all four, while conn_diag.o is each model's own.
The two share the station record of the AiMesh diagnostics, and this tree's pair has one more field in that record
than the pair of the older drops. With one object from each generation the link succeeds and nothing looks wrong
until conn_diag runs on an AiMesh router: it restarted about every 94 seconds (BQ16, BQ16 Pro, GT-BE19000). The
GT-BE98's own objects are of this tree's generation, so its shared copy is right.

WHAT IT CHECKS (alpha lean only; the other lines have no such list and skip):
  - the conn_diag-sql.o line carries exactly the exceptions -GT-BE19000 -BQ16 -BQ16_PRO;
  - conn_diag.o is not on the list (putting it there means moving the pair: change both lines together);
  - in each of the three models' platform archives the two objects are the recorded pair of ONE ASUS drop. A model
    that takes a new drop takes both objects from it, and this table is updated in the same change.
RULE for the list: before an object goes on it, find every closed object that needs its exports and confirm they are
the same generation, or keep the model's own copy with a -MODEL mark.
Exit 0 pass, 1 fail, 77 skipped (no list in this lean)."""
import hashlib, os, sys, tarfile

LEAN = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LIST = os.path.join(LEAN, "overlays", "common-blobs.list")
if not os.path.isfile(LIST):
    print("SKIP: no overlays/common-blobs.list in this lean (only the alpha line swaps shared closed objects)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:400] if detail else ""))

rows = {}
for l in open(LIST, encoding="utf-8"):
    p = l.split()
    if len(p) >= 2 and p[0] in ("prebuild", "sysdep"): rows[p[1]] = sorted(p[2:])
SQL = "rc/prebuild/MODEL/conn_diag-sql.o"
check("the list still names conn_diag-sql.o (GT-BE98 takes this tree's copy)", SQL in rows)
check("conn_diag-sql.o: GT-BE19000, BQ16 and BQ16_PRO keep their own copy, and only they",
      rows.get(SQL) == ["-BQ16", "-BQ16_PRO", "-GT-BE19000"], rows.get(SQL))
check("conn_diag.o is not on the list (it and conn_diag-sql.o move together, never one alone)",
      "rc/prebuild/MODEL/conn_diag.o" not in rows and "rc/prebuild/MODEL/conn_diag-broadcom.o" not in rows)

# the pair each model's drop came with: (conn_diag.o, conn_diag-sql.o), sha256
PAIRS = {
    "BQ16":       ("dd5849b6fc29a3ca458fc2293ab47ce649f42fecb06431f5d5cc57aecbd20b94", "195305313c8fc064c6ee7c7ff22f365c55579675b874ed0c5bd7d2495a4db01d"),   # ASUS GPL 102_39256
    "BQ16_PRO":   ("73c33a80a9854ed007d62df4bf45b64fd24a63f4af958ac514afbbf8f4332483", "f3dbd834c4e48833192c7af84d784148420f61c7fe4da759143c6de1d50235a2"),   # ASUS GPL 102_39442
    "GT-BE19000": ("773c84beed500b174e29330f65daa6c1bcd1776a88cb00010729b6cbf66c161d", "195305313c8fc064c6ee7c7ff22f365c55579675b874ed0c5bd7d2495a4db01d"),   # ASUS GPL 102_39274
}
for model, (want_cd, want_sql) in sorted(PAIRS.items()):
    arch = os.path.join(LEAN, "overlays", model + "-platform.tar.gz")
    if not os.path.isfile(arch):
        check("%s: platform archive present" % model, False, arch); continue
    got = {}
    base = "release/src/router/rc/prebuild/%s/" % model
    with tarfile.open(arch, "r:gz") as t:
        for m in t:
            if m.name in (base + "conn_diag.o", base + "conn_diag-sql.o"):
                got[m.name[len(base):]] = hashlib.sha256(t.extractfile(m).read()).hexdigest()
                if len(got) == 2: break
    check("%s: conn_diag.o and conn_diag-sql.o in its archive are the pair of one drop" % model,
          got.get("conn_diag.o") == want_cd and got.get("conn_diag-sql.o") == want_sql,
          "conn_diag.o %s, conn_diag-sql.o %s" % (str(got.get("conn_diag.o"))[:12], str(got.get("conn_diag-sql.o"))[:12]))

if fails:
    print("\n%d FAILED" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
