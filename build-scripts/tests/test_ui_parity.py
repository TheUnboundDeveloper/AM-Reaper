#!/usr/bin/env python3
"""UI parity: every setting a replaced stock page could save is covered by its Reaper page, or dropped on purpose.

WHY (Reaper-native UI project, 2026-10-22). Reaper pages replace stock ASUS pages one by one; the stock page is
then redirected and finally deleted. A setting the stock page saved that the Reaper page forgot would vanish
without anyone noticing. So each conversion carries a parity file, ui_parity/<StockPage>.json:

    {"stock": "Advanced_X_Content.asp", "replacement": "Reaper_X.asp",
     "action_script": "restart_x",            # what the stock apply ran
     "fields": {"nvram_name": "covered",      # the Reaper page posts this name
                "widget_x_0": "dropped: add-row widget, not a setting"},
     "extra": ["name_built_in_js"]}           # stock fields a form scan cannot see

WHAT IT CHECKS. The stock page's form fields (every name="..." input/select/textarea, minus the plumbing
names every stock form carries) plus "extra" must all be listed; every "covered" name must appear
literally in the replacement page; the stock action_script must appear in the replacement too. Run with
--list <StockPage> to print the names a new parity file has to account for.
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
WWW = os.path.join(SRC, "www")
PAR = os.path.join(HERE, "ui_parity")
if not os.path.isdir(WWW):
    print("SKIP: www not found (%s)" % WWW); sys.exit(0)

PLUMBING = {"current_page", "next_page", "group_id", "modified", "action_mode", "action_script", "action_wait",
            "first_time", "preferred_lang", "firmver", "productid", "SystemCmd", "flag", "wl_unit", "wl_subunit",
            "wan_unit", "apps_action", "apps_path", "apps_name", "apps_flag", "wl_ssid"}

def read(p):
    return open(p, encoding="utf-8", errors="surrogateescape").read()

def stock_fields(page):
    t = read(os.path.join(WWW, page))
    names = set()
    for m in re.finditer(r'<(?:input|select|textarea)\b[^>]*\bname\s*=\s*["\']([A-Za-z0-9_\-\.\[\]]+)["\']', t, re.I):
        names.add(m.group(1))
    return names - PLUMBING, t

if len(sys.argv) == 3 and sys.argv[1] == "--list":
    names, t = stock_fields(sys.argv[2])
    scripts = sorted(set(re.findall(r'action_script[^;]{0,40}?value\s*=\s*["\']([^"\']+)["\']', t)))
    print("fields:"); [print("  " + n) for n in sorted(names)]
    print("action_script candidates:", scripts)
    sys.exit(0)

fails = []
files = sorted(glob.glob(os.path.join(PAR, "*.json")))
if not files:
    print("SKIP: no parity files"); sys.exit(0)
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    stock, rep = d["stock"], d["replacement"]
    tag = os.path.basename(f)
    sp, rp = os.path.join(WWW, stock), os.path.join(WWW, rep)
    if not os.path.exists(sp):
        print("note: %s: stock page %s is gone (fine after the cutover)" % (tag, stock)); continue
    if not os.path.exists(rp):
        fails.append("%s: replacement %s missing" % (tag, rep)); continue
    names, st = stock_fields(stock)
    names |= set(d.get("extra", []))
    rt = read(rp)
    fields = d.get("fields", {})
    for n in sorted(names):
        v = fields.get(n)
        if v is None:
            fails.append("%s: stock field %s is not accounted for" % (tag, n))
        elif v == "covered":
            if n not in rt:
                fails.append("%s: %s is marked covered but %s never mentions it" % (tag, n, rep))
        elif not str(v).startswith("dropped:"):
            fails.append("%s: %s must be 'covered' or 'dropped: <reason>'" % (tag, n))
    for n in fields:
        if n not in names and fields[n] == "covered" and n not in st:
            fails.append("%s: %s is listed but the stock page has no such field" % (tag, n))
    a = d.get("action_script")
    if a and a not in rt:
        fails.append("%s: stock action_script %r is not in %s" % (tag, a, rep))
    print("ok   %s: %d fields (%d covered)" % (tag, len(names), sum(1 for n in names if fields.get(n) == "covered")))

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
