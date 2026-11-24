#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unused request handlers, small batch (owner 2026-11-20; review 2026-11-17 B-28 / P6-2-2 / D-12).

WHY THIS EXISTS. httpd registered request handlers no shipped page calls; each is an untested parser of admin input.
The owner approved a small batch first:
  - backup_jffs*.tar (tar of /jffs on download) and jffsupload.cgi (erased /jffs with rm -rf, then unpacked an
    uploaded tar): only the stock backup page used them, and it is not shipped (www/Makefile removes it). The rows,
    their three handler functions and the static-file exemption for backup_jffs*.tar in httpd.c are gone.
  - set_fw_path.cgi: no page calls it; the handler is in a closed object, so only the row goes.
  - strongSwan vici: load_modular = yes loaded every shipped plugin, so the vici control socket opened though nothing
    uses it. rc now writes "vici { load = no }" inside charon.plugins after the include (later values replace earlier
    ones in strongswan.conf).

WHAT IT DOES. Pins the absences in httpd/web.c and httpd/httpd.c; scans every www file that ships (the www/Makefile
"rm -f $(INSTALLDIR)/www/<page>" lines name the unshipped ones; symlinks resolved) for a call to the removed names;
renders rc_strongswan_conf_set()'s fixed text and merges it with the shipped vici.conf the include pulls in, by
strongswan.conf's documented rules, and requires charon.plugins.vici.load = no, braces balanced, nothing else in
the plugins section changed. Exit 0 pass, 1 fail, 77 skipped (no router source tree).
"""
import os, re, sys

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

FAILS = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or not detail else ": " + str(detail)[:600]))
    if not cond:
        FAILS.append(name)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(os.path.join(SRC, "httpd")):
    skip("no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)")

def rd(rel):
    with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as f:
        return f.read()

web = rd("httpd/web.c")
hc = rd("httpd/httpd.c")
mh = re.search(r"struct mime_handler mime_handlers\[\] =\s*\{(.*?)\n\};", web, re.S)
rows = mh.group(1) if mh else ""
check("web.c: the mime_handlers[] table is there", bool(rows))
for name in ("backup_jffs*.tar", "jffsupload.cgi*", "set_fw_path.cgi"):
    check("mime_handlers[]: no %s row" % name, '{ "%s"' % name not in rows)
check("web.c: do_jffs_file / do_jffsupload_cgi / do_jffsupload_post and JFFS_BACKUP_FILE are gone (the stock wipe-and-unpack restore and the archive download)",
      not re.search(r"\bdo_jffs_file\s*\(|\bdo_jffsupload_(cgi|post)\s*\(|JFFS_BACKUP_FILE", web)
      and "Restoring JFFS backup" not in web and "tar -xf /tmp/backup_jffs.tar" not in web
      and "tar cf /tmp/backup_jffs.tar" not in web)
check("web.c: the removals are marked (REAPER-UNUSED-V384; the later batch tags REAPER-UNUSED-V384B / V384C are not counted)",
      len(re.findall(r"REAPER-UNUSED-V384(?![A-Z])", web)) == 3)
check("httpd.c: the static-file exemption for backup_jffs*.tar is gone",
      'fnmatch("backup_jffs*.tar"' not in hc and ("!(strstr(file_path,\"uploadIconFile.tar\"))" in hc
      or "!(strstr(file,\"uploadIconFile.tar\"))" in hc))  # the 3006.102.8 line names it file; the
      # networkmap.tar exemption beside it went with its row (REAPER-UNUSED-V384B, test_unused_handlers_v384b.py)
check("the set_fw_path handler stays declared for the closed object (row only)", "do_set_fw_path_cgi" in rd("httpd/httpd.h"))

# ---------------------------------------------------------------- shipped www: nothing calls the removed names
www = os.path.join(SRC, "www")
mk = rd("www/Makefile")
gone = set(re.findall(r"rm -f \$\(INSTALLDIR\)/www/([A-Za-z0-9_.\-]+)", mk))
check("www/Makefile: the stock backup page is not shipped", "Advanced_SettingBackup_Content.asp" in gone)
hits = []
for root, dirs, files in os.walk(www):
    for f in files:
        p = os.path.join(root, f)
        if not re.search(r"\.(asp|htm|html|js|json)$", f):
            continue
        real = os.path.realpath(p)
        if os.path.basename(p) in gone or os.path.basename(real) in gone:
            continue
        try:
            t = open(real, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for n in ("jffsupload.cgi", "backup_jffs", "set_fw_path.cgi"):
            if n in t:
                hits.append("%s: %s" % (os.path.relpath(p, www), n))
check("no shipped www file (symlinks resolved) calls jffsupload.cgi, backup_jffs*.tar or set_fw_path.cgi", not hits, hits[:6])

# ---------------------------------------------------------------- strongSwan: vici off at run time
ips = rd("rc/rc_ipsec.c")
fm = re.search(r"void rc_strongswan_conf_set\(\)\n\{.*?fprintf\(fp,\n(.*?),\n\t\tuser,", ips, re.S)
check("rc_strongswan_conf_set: the fixed charon text is found", fm is not None)
def c_literals(block):
    out = []
    for ln in block.split("\n"):
        ln = ln.strip()
        if ln.startswith("/*") or ln.startswith("*") or not ln:
            continue
        m = re.fullmatch(r'"(.*)"', ln)
        if not m:
            return None
        out.append(m.group(1).replace("\\n", "\n").replace("%%", "%"))
    return "".join(out)

def parse_conf(text, include=None):
    """strongswan.conf by its manual: sections extend sections of the same name, a key set again replaces the value,
    an include adds the file's settings relative to the section the statement is in."""
    root, stack = {}, []
    cur = root
    toks = []
    for ln in text.split("\n"):
        ln = ln.split("#", 1)[0].strip()
        if ln:
            toks.append(ln)
    for ln in toks:
        if ln.startswith("include "):
            if include:
                sub = parse_conf(include)
                merge(cur, sub)
            continue
        if ln.endswith("{"):
            name = ln[:-1].strip()
            nxt = cur.get(name)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[name] = nxt
            stack.append(cur)
            cur = nxt
        elif ln == "}":
            if not stack:
                raise ValueError("unbalanced }")
            cur = stack.pop()
        elif "=" in ln:
            k, v = ln.split("=", 1)
            cur[k.strip()] = v.strip()
        elif re.fullmatch(r"[a-z_]+ \{ [a-z_]+ = [a-z]+ \}", ln):   # starter { load_warning = no }
            n, kv = ln.split(" { ", 1)
            k, v = kv.rstrip(" }").split(" = ")
            cur.setdefault(n, {})[k] = v
        else:
            raise ValueError("unparsed: " + ln)
    if stack:
        raise ValueError("unbalanced {")
    return root

def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict):
            if not isinstance(dst.get(k), dict):
                dst[k] = {}
            merge(dst[k], v)
        else:
            dst[k] = v

if fm:
    conf = c_literals(fm.group(1))
    check("the fixed text is plain string literals (comments allowed between them)", conf is not None)
    if conf:
        conf = conf.replace("%s", "x").replace("%d", "1").replace("%b %e %T", "fmt") + "}\n"
        vici_conf = rd("strongswan/conf/plugins/vici.conf")
        try:
            tree = parse_conf(conf, include=vici_conf)
            err = ""
        except ValueError as e:
            tree, err = None, str(e)
        check("the rendered strongswan.conf parses, braces balanced", tree is not None, err)
        if tree:
            pl = tree.get("charon", {}).get("plugins", {})
            check("the shipped vici.conf says load = yes (what the include brings in)", "load = yes" in vici_conf)
            check("charon.plugins.vici.load = no after the include (the later value replaces it)",
                  pl.get("vici", {}).get("load") == "no", pl)
            check("load_modular stays on, and vici is the only plugin entry rc adds",
                  tree["charon"].get("load_modular") == "yes" and list(pl.keys()) == ["vici"], (tree["charon"].get("load_modular"), list(pl.keys())))
            try:
                order = parse_conf(conf.replace("load = no", "load = maybe"), include=None)
            except ValueError:
                order = None
            check("the vici entry sits inside charon { plugins { } } after the include line",
                  conf.find("include strongswan.d/charon/*.conf") < conf.find("vici {") < conf.find("filelog {")
                  and order is not None and order["charon"]["plugins"]["vici"]["load"] == "maybe")
    check("rc_ipsec.c: marked REAPER-VICI-OFF", "REAPER-VICI-OFF" in ips)

if FAILS:
    print("%d FAILED" % len(FAILS)); sys.exit(1)
print("all passed")
