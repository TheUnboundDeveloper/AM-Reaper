#!/usr/bin/env python3
"""Reaper_QoS: the user-defined classification rules editor (qos_rulelist), 2026-10-22.

WHY. The stock rules page has been redirected to Reaper_QoS since the QoS page was built, but Reaper_QoS only
reported on the rules - the list had no editor at all (found in the Reaper-native UI inventory). This pins the
editor: the panel, the hidden field, the engines it shows for, the format rc parses, the limits, the preset
catalogue, the dict keys in all 25 packs, and that the page script still parses.

WHAT IT DOES. Source checks on Reaper_QoS.asp, then the page's last <script> through `node --check` with the
<% %> / <# #> markers stubbed (the same stub every www check uses).
"""
import os, re, shutil, subprocess, sys, tempfile

SRC = os.environ.get("REAPER_SRC", "/home/reaper/asuswrt-be96u/release/src/router")
P = os.path.join(SRC, "www", "Reaper_QoS.asp")
if not os.path.exists(P):
    print("SKIP: Reaper_QoS.asp not found"); sys.exit(0)
t = open(P, encoding="utf-8", errors="surrogateescape").read()
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:300] if detail else ""))

check("rules panel with its table, add row and budget line",
      all(x in t for x in ('id="rulespanel"', 'id="rulestbody"', 'id="rl_preset"', 'id="rl_desc"', 'id="rl_addr"', 'id="rl_port"',
                           'id="rl_proto"', 'id="rl_min"', 'id="rl_max"', 'id="rl_prio"', 'id="rbudget"', 'onclick="ruleAdd()"')))
check("hidden qos_rulelist field, disabled until an engine that uses it is applied",
      '<input type="hidden" name="qos_rulelist" value="" disabled>' in t
      and "if (sel === '0' || sel === '11'){\n    f.qos_rulelist.disabled = false; f.qos_rulelist.value = serializeRules();" in t)
check("the panel shows for Traditional (0) and HW QoS Classful (11) only - the engines rc feeds the rules to",
      "document.getElementById('rulespanel').style.display = (sel === '0' || sel === '11') ? '' : 'none';" in t)
check("format: '<' before every row, 6 '>'-joined fields, a bare '~' normalised away",
      "out += '<' + [r.desc, r.addr, r.port, r.proto, r.xfer, r.prio].join('>');" in t and "xfer: (f[4] === '~' ? '' : f[4])" in t)
check("limits: 128 rules (the stock page's) and httpd's 4096-character validator (qos_rulelist is nvram-whitelisted)",
      "RULE_MAX = 128, RULE_BYTES = 4096" in t and "if (serializeRules().length > RULE_BYTES){ RULES.pop(); alert(`<#RQOS_133#>`); return; }" in t)
check("source forms: empty, IPv4, a.b.c.d-e, a.b.c.*, a.b.c.d/nn, MAC (what rc's address_format_checker takes)",
      all(x in t for x in ("RX_IPSTAR", "RX_IPRANGE", "RX_IPMASK", "/^([0-9A-F]{2}:){5}[0-9A-F]{2}$/.test(a)")))
check("ports: multiport grammar, at most 15 entries, ranges ascending", "if (items.length > 15) return false;" in t and "parseInt(ab[1], 10) <= parseInt(ab[0], 10)" in t)
check("under the classful engine the priority menu names the classes in table order, relabelled when classes change",
      "if (sel === '11'){\n    var rows = document.querySelectorAll('#ctbody tr')" in t
      and "document.getElementById('ctbody').addEventListener('input', function(){ if (sel === '11') prioRelabel(); });" in t   # review 2026-10-24 Q-C2-6: relabel in place
      and "function prioRelabel(){" in t and "if (typeof renderRules === 'function' && sel === '11') renderRules();" in t)
check("the stock preset catalogue is offered (group headers = port 0000)",
      "x.open('GET', '/ajax_qos_default.xml?_=' + Date.now(), true);" in t and "if (port === '0000'){ grp = document.createElement('optgroup');" in t
      and os.path.exists(os.path.join(SRC, "www", "ajax_qos_default.xml")))
check("the transferred-range warning reads the live rules, not the boot-time nvram copy",
      "for(i = 0; i < RULES.length; i++) if(RULES[i].xfer) bad.push" in t and "Rules are edited on the stock user-rules page" not in t)
check("rules parsed before the first panel sync, which renders them once the modes are known (review 2026-10-24 Q-C2-6: no second boot render)",
      "parseRules(); renderModes(); syncPanels(); buildEditor();" in t and "pollStats(); fetchPresets();" in t and "pollStats(); renderRules();" not in t)
js = t[t.rfind("<script>"):]
js_wo = re.sub(r"`[^`]*`", "", js)            # backtick strings may carry tokens (translations with apostrophes are safe there)
js_wo = re.sub(r'"[^"\n]*"', "", js_wo)       # double-quoted too (the dict escapes double quotes)
check("every token used in JS sits inside backticks or double quotes (rule 29)", "<#" not in js_wo,
      [m.group(0) for m in re.finditer(r".{0,40}<#[A-Za-z0-9_]+#>.{0,20}", js_wo)][:3])
check("ASCII only", not any(ord(c) > 127 for c in t))
# 2026-10-22 parity sweep: link overhead (Traditional + Cake) and the Traditional per-class rates + flags
check("link overhead block: preset, bytes, framing, MPU; shown for types 0 and 9, MPU for Cake only",
      all(x in t for x in ('id="oh_preset"', 'id="oh_bytes"', 'id="oh_atm"', 'id="oh_mpu"', 'var OH_PRESETS = [["1","48","0","Conservative default"]'))
      and "document.getElementById('ohrow').style.display = (sel === '0' || sel === '9') ? '' : 'none';" in t
      and "document.getElementById('oh_mpuf').style.display = (sel === '9') ? '' : 'none';" in t)
check("overhead posted only for those engines; MPU kept as stored under Traditional",
      "if (sel === '0' || sel === '9'){\n    var oh = ohRead();" in t and "f.qos_mpu.value = (sel === '9') ? oh.mpu : (NV.mpu || '0');" in t
      and all('<input type="hidden" name="%s" value="" disabled>' % n in t for n in ("qos_overhead", "qos_atm", "qos_mpu")))
check("Traditional panel: five classes with upload min/max and download max, the five small-packet flags",
      all(x in t for x in ('id="tqpanel"', 'id="tqbody"', 'id="tg_ack"', 'id="tg_syn"', 'id="tg_fin"', 'id="tg_rst"', 'id="tg_icmp"'))
      and "document.getElementById('tqpanel').style.display = (sel === '0') ? '' : 'none';" in t)
check("Traditional apply writes qos_orates (5 pairs + 5 '0-0'), qos_irates (5 + 5 zeros) and the on/off flags",
      "for (i = 5; i < 10; i++){ ups.push('0-0'); dns.push('0'); }" in t
      and "f.qos_irates.disabled = false; f.qos_irates.value = tq.irates;" in t
      and "f[fk].value = document.getElementById(FL[fk]).checked ? 'on' : 'off';" in t
      and all('<input type="hidden" name="%s" value="" disabled>' % n in t for n in ("qos_irates", "qos_ack", "qos_syn", "qos_fin", "qos_rst", "qos_icmp")))
# 2026-10-22 metal (_r17): rc drops the port whenever the protocol is any (qos.c "if proto = any, no proto / dport") -
# a 192.168.50.250 / 5555 / any test rule became "-s 192.168.50.250/32" only. The editor must say so, never silently.
check("protocol any: port box off (protoSync), guard in ruleAdd, stored any+port rules struck through with the reason, hint and init wired, add row defaults to TCP/UDP",
      '<select id="rl_proto" onchange="protoSync()"><option value="tcp/udp">TCP/UDP</option>' in t
      and "if (proto === 'any' && port){ alert(`<#RQOS_145#>`); return; }" in t
      and "if (r.proto === 'any') return `<span class=\"rign\" title=\"<#RQOS_145#>\">` + esc(r.port) + '</span>';" in t
      and "+ '<td class=\"rcell\">' + rulePortCell(r) + '</td>'" in t
      and "+ ' ' + `<#RQOS_145#>`;" in t and "ohInit(); tqBuild(); protoSync();" in t
      and "p.disabled = any; if (any) p.value = ''; p.placeholder = any ? '*' : '80,443';" in t
      and ".rign{text-decoration:line-through;color:var(--steel)}" in t)
check("httpd/reaper_inject.c still redirects the stock rules page here",
      '{ "advanced_qosuserrules_content.asp", "Reaper_QoS.asp", ' in open(os.path.join(SRC, "httpd", "reaper_inject.c"), encoding="utf-8", errors="surrogateescape").read())
www = os.path.join(SRC, "www")
PACKS = "EN DE FR ES BR IT NL DA NO SV FI PL CZ SL HU RO RU UK TR MS TH JP KR CN TW".split()
packs = [p + ".dict" for p in PACKS if os.path.exists(os.path.join(www, p + ".dict"))]
missing = [f for f in packs if not all(("RQOS_%d=" % k) in open(os.path.join(www, f), encoding="utf-8", errors="replace").read() for k in range(127, 134))]
check("RQOS_127-133 in all %d packs" % len(packs), len(packs) == 25 and not missing, missing)
missing2 = [f for f in packs if not all(("RQOS_%d=" % k) in open(os.path.join(www, f), encoding="utf-8", errors="replace").read() for k in range(134, 146))]
check("RQOS_134-145 in all packs", not missing2, missing2)

node = shutil.which("node")
if node:
    s = re.findall(r"<script>(.*?)</script>", t, re.S)[-1]
    s = re.sub(r"<%.*?%>", "0", s); s = re.sub(r"<#[A-Za-z0-9_-]+#>", "X", s)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(s); jp = f.name
    r = subprocess.run([node, "--check", jp], capture_output=True, text=True)
    os.unlink(jp)
    check("page script parses (node --check)", r.returncode == 0, r.stderr)
else:
    print("note: node not found - syntax check skipped")

if fails:
    print("\n%d FAILED:" % len(fails))
    for x in fails: print("  - " + x)
    sys.exit(1)
print("\nall checks passed")
