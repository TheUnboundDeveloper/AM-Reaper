#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest Portal: the sign-in success page goes on to the address the device first asked for (2026-11-12).

WHY THIS EXISTS. Field report on the owner's router: after "Continue" the sign-in page showed "Successful!" and
nothing else. chilli (coovachilli/src/redir.c, REDIR_LOGIN) replaces the address the device first asked for with
"<sign-in page>?auth_status=pass", so nothing sent the browser on - on a phone the system's sign-in sheet was left
on a page that never changes.
2026-11-13: a fixed 3 s was not enough. For some seconds after a sign-in a phone still holds the stand-in address
chilli gave it for every name before the sign-in (first new lookup seen 6 s after it on the owner's router), and a
page load sent there never answers. The success page now asks for the first address in the background until it
answers, and only then goes on.

WHAT IT DOES. Runs the real uam.js under node against a stub page (window / document / jQuery / sessionStorage /
fetch on a virtual clock) and checks: the first address is kept while the sign-in page is shown (plain and
twice-encoded), only http(s) addresses are kept or followed, the success page goes on once the first address
answers (at once, after tries that never answer, after a refused try, never twice), goes on regardless after the
last try, goes on at once where it cannot ask (no fetch, http address from an https page), and a page with no
stored address or no working sessionStorage stays as it was. Then pins the call sites.
Exit 0 pass, 1 fail, 77 skipped (no router tree - argv[1] or REAPER_ROUTER_SRC = .../release/src/router).
Without node the behaviour part is skipped and only the pins run."""
import json, os, shutil, subprocess, sys, tempfile

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
UAM = os.path.join(SRC, "lighttpd-1.4.39", "external_file", "css", "uam.js") if SRC else ""
if not SRC or not os.path.isfile(UAM):
    print("SKIP: no router tree with lighttpd-1.4.39/external_file/css/uam.js (argv[1] or REAPER_ROUTER_SRC)")
    sys.exit(77)

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:400] if detail else ""))

uam = open(UAM, encoding="latin-1").read()

# ---- pins
check("uam.js keeps the first address while the sign-in page is shown",
      'if (res == "notyet") {\n\t\treaperKeepNext();' in uam.replace("\r\n", "\n"))
check("uam.js goes on from the success page after a pause",
      'if (reaperQuery("auth_status") == "pass")' in uam and "setTimeout(reaperGoNext, REAPER_NEXT_MS);" in uam)
check("only http(s) addresses are kept or followed",
      '(p.protocol == "http:" || p.protocol == "https:") ? p.href : ""' in uam)
check("the stored address is read through the same test before it is followed",
      'u = reaperNextUrl(window.sessionStorage.getItem(REAPER_NEXT_KEY) || "");' in uam)
check("the success page asks for the first address before it goes on",
      "\tif (u != \"\")\n\t\treaperTryNext(u, 0);\n" in uam.replace("\r\n", "\n") and 'mode: "no-cors"' in uam)
check("uam.js is plain ASCII", all(ord(c) < 128 for c in uam))
mk = os.path.join(SRC, "Makefile")
if os.path.isfile(mk):
    check("the image still installs uam.js",
          "lighttpd-1.4.39/external_file/css/uam.js" in open(mk, encoding="latin-1").read())

# ---- behaviour
HARNESS = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[2], "latin1");
// net: undefined = the first address answers at once; null = the page has no fetch; else one word per try:
//      "ok" answers, "no" is refused, "late" answers 6 s on (after the try gave up); past the end = never answers
function run(href, store, broken, net) {
  const ready = [], q = [], els = {}, waits = [], asked = [], modes = [];
  let now = 0, seq = 0, replaced = null, replacedAt = null, replaces = 0, aborted = 0;
  const later = (f, ms) => { q.push({ at: now + ms, id: ++seq, f: f }); return seq; };
  const document = {
    createElement: () => ({ setAttribute() {}, innerHTML: "" }),
    body: { appendChild() {} },
    getElementById: (id) => els[id] || (els[id] = { value: "", href: "", style: {} })
  };
  const $ = function (a) { if (typeof a == "function") { ready.push(a); return; } return { ready: (f) => ready.push(f) }; };
  const good = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
                 removeItem: (k) => { delete store[k]; } };
  const bad = { getItem() { throw new Error("x"); }, setItem() { throw new Error("x"); }, removeItem() { throw new Error("x"); } };
  const window = { location: { href: href, replace: (u) => { replaced = u; replacedAt = now; replaces++; } } };
  if (broken == 1) window.sessionStorage = bad;
  else if (broken != 2) window.sessionStorage = good;
  if (net !== null) window.fetch = (u, o) => {
    const how = net === undefined ? "ok" : (net[asked.length] || "hang");
    asked.push(u); modes.push(o && o.mode);
    return { then: (yes, no) => {
      if (how == "ok") later(yes, 50); else if (how == "no") later(no, 50); else if (how == "late") later(yes, 6000);
    } };
  };
  class AbortController { constructor() { this.signal = {}; } abort() { aborted++; } }
  const ctx = { window, document, $, URL, decodeURIComponent, alert() {}, AbortController,
                setTimeout: (f, ms) => { waits.push(ms); return later(f, ms); },
                clearTimeout: (id) => { const i = q.findIndex((t) => t.id == id); if (i >= 0) q.splice(i, 1); } };
  let threw = "", guard = 0;
  try {
    vm.runInNewContext(src, ctx);
    ready.forEach((f) => f());
    while (q.length && guard++ < 2000) {
      q.sort((a, b) => a.at - b.at || a.id - b.id);
      const t = q.shift(); now = t.at; t.f();
    }
  } catch (e) { threw = String(e); }
  return { waits, asked: asked.length, modes, aborted, replaced, replacedAt, replaces, store, threw };
}
const P = "http://192.168.52.1:8083/FreeUam";
const PS = "https://192.168.52.1:8083/FreeUam";
const APPLE = "http://captive.apple.com/hotspot-detect.html";
const enc = encodeURIComponent;
const K = () => ({ reaper_uam_next: APPLE });
const out = {};
out.keep = run(P + "?res=notyet&uamip=192.168.52.1&uamport=3990&challenge=ab&userurl=" + enc(APPLE), {});
out.keep2 = run(P + "?res=notyet&uamip=192.168.52.1&uamport=3990&challenge=ab&userurl=" + enc(enc(APPLE)), {});
out.keepq = run(P + "?res=notyet&userurl=" + enc("http://example.com/a?b=1&c=2"), {});
out.nojs = run(P + "?res=notyet&userurl=" + enc("javascript:alert(1)"), {});
out.noftp = run(P + "?res=notyet&userurl=" + enc("ftp://example.com/x"), {});
out.nourl = run(P + "?res=notyet&uamip=192.168.52.1", {});
out.go = run(P + "?auth_status=pass", K());
out.stale = run(P + "?auth_status=pass", K(), 0, ["hang", "hang", "ok"]);
out.refused = run(P + "?auth_status=pass", K(), 0, ["no", "ok"]);
out.late = run(P + "?auth_status=pass", K(), 0, ["late", "ok"]);
out.never = run(P + "?auth_status=pass", K(), 0, []);
out.nofetch = run(P + "?auth_status=pass", K(), 0, null);
out.mixed = run(PS + "?auth_status=pass", K());
out.secure = run(PS + "?auth_status=pass", { reaper_uam_next: "https://example.com/" });
out.goempty = run(P + "?auth_status=pass", {});
out.gobad = run(P + "?auth_status=pass", { reaper_uam_next: "javascript:alert(1)" });
out.already = run(P + "?res=already&uamip=192.168.52.1&uamport=3990", K());
out.brokenkeep = run(P + "?res=notyet&userurl=" + enc(APPLE), {}, 1);
out.brokengo = run(P + "?auth_status=pass", {}, 1);
out.nostore = run(P + "?auth_status=pass", {}, 2);
console.log(JSON.stringify(out));
"""
NODE = shutil.which("node") or shutil.which("nodejs")
if not NODE:
    print("SKIP (part): no node - the behaviour checks did not run")
else:
    tmp = tempfile.mkdtemp()
    try:
        h = os.path.join(tmp, "h.js")
        open(h, "w", encoding="ascii").write(HARNESS)
        r = subprocess.run([NODE, h, UAM], capture_output=True, text=True, timeout=60)
        o = {}
        try:
            o = json.loads(r.stdout)
        except Exception:
            pass
        check("the harness ran", bool(o), (r.stdout + r.stderr)[-400:])
        if o:
            APPLE = "http://captive.apple.com/hotspot-detect.html"
            K = "reaper_uam_next"
            check("no case threw", not any(o[k]["threw"] for k in o), {k: o[k]["threw"] for k in o if o[k]["threw"]})
            check("sign-in page: the first address is kept", o["keep"]["store"].get(K) == APPLE, o["keep"])
            check("sign-in page: a twice-encoded address is kept decoded", o["keep2"]["store"].get(K) == APPLE, o["keep2"])
            check("sign-in page: an address with its own query string is kept whole",
                  o["keepq"]["store"].get(K) == "http://example.com/a?b=1&c=2", o["keepq"])
            check("sign-in page: no pause is started, nothing is asked for or followed",
                  o["keep"]["waits"] == [] and o["keep"]["asked"] == 0 and o["keep"]["replaced"] is None, o["keep"])
            for k, what in (("nojs", "a javascript: address"), ("noftp", "an ftp: address"), ("nourl", "a missing address")):
                check("sign-in page: %s is not kept" % what, K not in o[k]["store"], o[k])
            g = o["go"]
            check("success page: 3 s pause, then the first address is asked for without a page load",
                  g["waits"][:1] == [3000] and g["asked"] == 1 and g["modes"] == ["no-cors"], g)
            check("success page: it answers - the page goes on to it, once",
                  g["replaced"] == APPLE and g["replacedAt"] == 3050 and g["replaces"] == 1, g)
            check("success page: the kept address is forgotten once used", K not in g["store"], g)
            s = o["stale"]
            check("success page: two tries never answer (stand-in address still held) - no page load is sent there",
                  s["asked"] == 3 and s["aborted"] == 2 and s["replaces"] == 1, s)
            check("success page: ... and it goes on when the third try answers (4 s a try, 1 s between)",
                  s["replaced"] == APPLE and s["replacedAt"] == 3000 + 2 * 5000 + 50, s)
            f = o["refused"]
            check("success page: a refused try is tried again after 1 s",
                  f["asked"] == 2 and f["replaced"] == APPLE and f["replacedAt"] == 3050 + 1000 + 50 and f["replaces"] == 1, f)
            l = o["late"]
            check("success page: an answer that arrives after its try gave up does not send the page on twice",
                  l["asked"] == 2 and l["replaces"] == 1 and l["replacedAt"] == 3000 + 5000 + 50, l)
            n = o["never"]
            check("success page: nothing ever answers - 12 tries, then the page is sent on regardless",
                  n["asked"] == 12 and n["replaced"] == APPLE and n["replacedAt"] == 3000 + 12 * 5000 and n["replaces"] == 1, n)
            check("success page: a browser with no fetch goes on at once, as before",
                  o["nofetch"]["replaced"] == APPLE and o["nofetch"]["replacedAt"] == 3000, o["nofetch"])
            check("success page: an http address cannot be asked for from an https page - goes on at once",
                  o["mixed"]["asked"] == 0 and o["mixed"]["replaced"] == APPLE and o["mixed"]["replacedAt"] == 3000, o["mixed"])
            check("success page: an https address from an https page is asked for first",
                  o["secure"]["asked"] == 1 and o["secure"]["replaced"] == "https://example.com/", o["secure"])
            check("success page: nothing kept - nothing asked for, the page stays",
                  o["goempty"]["replaced"] is None and o["goempty"]["asked"] == 0, o["goempty"])
            check("success page: a planted javascript: address is not asked for or followed, and is dropped",
                  o["gobad"]["replaced"] is None and o["gobad"]["asked"] == 0 and K not in o["gobad"]["store"], o["gobad"])
            check("an already-signed-in page starts no pause and follows nothing",
                  o["already"]["waits"] == [] and o["already"]["replaced"] is None, o["already"])
            check("sessionStorage that throws: nothing followed", o["brokenkeep"]["replaced"] is None
                  and o["brokengo"]["replaced"] is None, (o["brokenkeep"], o["brokengo"]))
            check("no sessionStorage at all: nothing followed", o["nostore"]["replaced"] is None, o["nostore"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if fails:
    print("\n%d FAILED:" % len(fails)); [print("  " + f) for f in fails]; sys.exit(1)
print("\nall checks passed"); sys.exit(0)
