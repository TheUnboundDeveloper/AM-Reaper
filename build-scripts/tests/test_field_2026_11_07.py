#!/usr/bin/env python3
"""Field reports 2026-11-07 (source pins + a node run of the dashboard's USB tiles).

usage: test_field_2026_11_07.py <release/src/router dir>   (or REAPER_ROUTER_SRC)

1. ZenWiFi BQ16 + a 4 TB Seagate: get_usb_info's size_int / used_int were 32-bit (a partition past 2 TB of
   kilobytes came out negative: USB Disks "0 B", the dashboard "not mounted") - now int64, the totals too.
2. The dashboard drew two USB tiles on a one-port model: the count is rc_support's usbX<n>, and on one port
   the USB 3 and USB 2 buses (usb_path1 / usb_path2 of the same socket) land on the one tile.
3. USB Application: the USB Disks table headers right-align like their number cells.
4. Wallguard: a per-row Update button (that list alone: CGI id -> $D/only), an allow-only source shows
   "%1 allowed"; RSHD_183 / RSHD_184 right after RSHD_182 in all 25 packs, packs in lockstep.
5. wallguardc takes $dnsrewrite=<sinkhole> rules (AdGuard DNS Popup Hosts) and one-bar exact rules; the D-1
   gate counts allows; wallguard.sh has the WAN gate, the pending epoch, retry and the ONLY subset.
"""
import json, os, re, shutil, subprocess, sys, tempfile

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- %s" % (detail,)))
    if not cond:
        fails.append(name)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "www", "Main_ReaperDash.asp")):
    print("skip: give the release/src/router directory"); sys.exit(0)
def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8").read()

# ---- 1. httpd
w = read("httpd/web.c")
usb = w[w.find("/* tmpParts.size */"):w.find("json_object_array_add(jarray,item);")]
check("httpd: size_int and used_int are int64; nothing in get_usb_info still builds them with new_int",
      'json_object_new_int64((int64_t)follow_partition->size_in_kilobytes)' in usb
      and 'json_object_new_int64((int64_t)follow_partition->used_kilobytes)' in usb
      and "json_object_new_int(follow_partition->" not in usb)
check("httpd: the disk totals are summed and printed as 64-bit",
      "long long total_size = 0, total_use = 0;" in usb and usb.count("json_object_get_int64(part_array_obj_") == 2
      and 'snprintf(disk_size, sizeof(disk_size), "%lld", total_size);' in usb and "json_object_get_int(part_array_obj" not in usb)

# ---- 2. dashboard
d = read("www/Main_ReaperDash.asp")
check("dashboard: rc_support reaches the page beside the usb_path facts",
      '  rcs:      <% nvram_get_js("rc_support"); %>,' in d)
ru = d[d.find("function renderUsb(USBINFO){"):d.find("\nrenderUsb(USBINFO);")]
check("dashboard: the tile count is usbX<n>, clamped to the two tiles; one port folds usb_path2 onto the first tile",
      "var np=(function(){ var m=/(?:^|\\s)usbX(\\d)(?:\\s|$)/.exec(String(SSI.rcs||'')); return m?Math.min(2,+m[1]):2; })();" in ru
      and "if(np<2){ byPort['1']=byPort['1'].concat(byPort['2']); byPort['2']=[]; defs[0].v=defs[0].v||defs[1].v; defs[0].s=defs[0].s||defs[1].s; defs.length=np; }" in ru)

node = shutil.which("node")
if node and ru:
    # the tile part of renderUsb, run under plain node with the page's helpers stubbed (no layout needed)
    tiles = ru[:ru.find("  /* Storage card.")] + "\n}\n"		# the function's storage half is cut off: close it
    tiles = re.sub(r"<#RDSH_17#>", "devices", tiles); tiles = re.sub(r"<#RDSH_80#>", "EMPTY", tiles)
    js = r"""
var out = {}; function $id(i){ return out[i] || (out[i] = {style:{setProperty:function(){}}}); }
function esc(s){ return String(s); } function dname(d){ return String((d&&d.deviceName)||''); }
var SSI = {usb1:'', usb1_spd:'', usb2:'', usb2_spd:'', rcs:''};
%s
function tilesOf(rcs, info, s1, s2){ SSI.rcs = rcs; SSI.usb1 = s1; SSI.usb2 = s2; out = {}; renderUsb(info); return (out.usb_ports.innerHTML.match(/class="port[^"]*"/g) || []); }
var disk = [{deviceName:'Seagate', usbPath:'1', partition:[]}], disk2 = [{deviceName:'Stick', usbPath:'2', partition:[]}];
var r = {
  two: tilesOf('mssid usbX2 ipv6', disk, 'Seagate', ''),
  one: tilesOf('mssid usbX1 ipv6', disk, 'Seagate', ''),
  one_on_bus2: tilesOf('usbX1', disk2, '', 'Stick'),
  one_subs: (function(){ SSI.rcs='usbX1'; SSI.usb1=''; SSI.usb2='Stick'; out={}; renderUsb(disk2); return out.usb_ports.innerHTML; })(),
  none: tilesOf('mssid ipv6', disk, 'Seagate', ''),
  usbx_in_word: tilesOf('xusbX1', disk, 'Seagate', '')
};
console.log(JSON.stringify(r));
""" % tiles
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js); jp = f.name
    try:
        r = subprocess.run([node, jp], capture_output=True, text=True, timeout=30)
        o = json.loads(r.stdout) if r.returncode == 0 else {}
    finally:
        os.unlink(jp)
    check("dashboard (node): usbX2 = two tiles, the first up; usbX1 = one tile",
          o.get("two") == ['class="port up"', 'class="port"'] and o.get("one") == ['class="port up"'], (r.stderr[:400], o))
    check("dashboard (node): on one port a device on the USB 2 bus (usb_path2) lights the one tile and names the device",
          o.get("one_on_bus2") == ['class="port up"'] and "Stick" in o.get("one_subs", ""), o)
    check("dashboard (node): no usbX, or usbX inside another word = the two tiles as before",
          len(o.get("none", [])) == 2 and len(o.get("usbx_in_word", [])) == 2, o)
else:
    print("skip: node not found - the renderUsb run")

# ---- 3. USB Application
check("USB Application: the table's number headers right-align (rp.css left-aligns every th)",
      ".rtab th.num{text-align:right}" in read("www/Reaper_USBApps.asp"))

# ---- 4. Wallguard page + packs
p = read("www/Reaper_Wallguard.asp")
check("page: a per-row Update button on every subscribed list, asking for that list alone",
      "if(f) ac.appendChild(shBtn(`<#RSHD_183#>`, function(){ shAct('update&id=' + encodeURIComponent(r.id)); }, 1));" in p)
check("page: an allow-only source shows what it allows instead of 0 names",
      "shCell(tr, s ? (s.unique || !s.allows ? shNum(s.unique) : `<#RSHD_184#>`.replace('%1', shNum(s.allows))) : DASH, 'num');" in p)
packs = sorted(f for f in os.listdir(os.path.join(SRC, "www")) if re.fullmatch(r"[A-Z]{2}\.dict", f))
lens, bad = set(), []
for f in packs:
    lines = open(os.path.join(SRC, "www", f), encoding="utf-8").read().split("\n")
    lens.add(len(lines))
    i = [k for k, l in enumerate(lines) if l.startswith("RSHD_182=")]
    if len(i) != 1 or not lines[i[0] + 1].startswith("RSHD_183=") or not lines[i[0] + 2].startswith("RSHD_184=") \
       or len(lines[i[0] + 1]) < 10 or "%1" not in lines[i[0] + 2]:
        bad.append(f)
check("packs: 25 packs, RSHD_183 (a word) and RSHD_184 (with %%1) right after RSHD_182 in each, all the same length (%s)" % (sorted(lens),),
      len(packs) == 25 and not bad and len(lens) == 1, bad)

# ---- 5. wallguardc + wallguard.sh
c = read("wallguard/wallguardc.c")
check("wallguardc: mods_ok takes important and dnsrewrite= to the five sinkholes on a block, nothing else; |name^ is exact",
      'static const char *const sink[] = { "ad-block.dns.adguard.com", "0.0.0.0", "::", "NXDOMAIN", "REFUSED", NULL };' in c
      and "if (p[0] == '|' || !strncmp(p, \"@@|\", 3)) {" in c and "*subtree = p[0] == '|';" in c
      and "if (!mods_ok(caret + 1, *allow))" in c and 'strcmp(caret + 1, "$important")' not in c)
s = read("wallguard/wallguard.sh")
check("wallguard.sh: the WAN gate, the pending epoch with backoff, retry, the ONLY subset and sync's new-lists-only update",
      "wan_up() {" in s and "pending_set() {" in s and '[ "$_m" -gt 360 ] && _m=360' in s and "  retry) retry ;;" in s
      and "ONLY=$_new update" in s and "ONLY=$ow update" in s and 'rm -f "$D/only"' in s
      and 'if [ -z "${ONLY+x}" ] && [ -f "$D/only" ] && [ ! -L "$D/only" ]; then' in s)
# metal _r1 (2026-11-07): nvram's wanN_state_t was a stale 2 at boot, the mark's time was computed on the 2023 clock,
# the retry found the USB copies usable and built nothing, the store hook restores only with no table
check("wallguard.sh (metal _r1): the WAN gate is a default route AND a set clock, never nvram's wan state",
      "{ ip -4 route show default 2>/dev/null; ip -6 route show default 2>/dev/null; } | grep -q '^default' || return 1" in s
      and '[ "$(date +%Y)" -ge 2024 ]' in s and "wan${_n}_state_t" not in s)
check("wallguard.sh (metal _r1): retry with nothing owed builds when the table was built without the lists; restore_build acts under the mark",
      "    grep -q ' missing ' \"$D/state\" 2>/dev/null && build\n" in s
      and '  [ -s "$D/db" ] && [ ! -f "$D/pending" ] && return 0\n' in s)
rcw = read("rc/wallguard.c")
check("rc (metal _r1): the USB-store hook restores with no table OR under the mark; the first NTP sync fetches the owed lists",
      '(!f_exists(SH_DIR "/db") || f_exists(SH_DIR "/pending")) && f_exists(SH_DIR "/feeds"))' in rcw
      and "\t\twallguard_on_firewall();\n" in read("rc/ntp.c"))
# metal _r2 (2026-11-07): the router's ash had no `command` builtin (CONFIG_ASH_CMDCMD off) - `command -v nvram` was 127
# and wan_up() said "the host"; and the first-sync block this firmware runs is rc/ntpd.c (busybox ntpd's -S hook)
check("wallguard.sh (metal _r2): host-or-router is decided by /bin/nvram's presence, never by `command -v`",
      "  [ -x /bin/nvram ] || return 0\n" in s and not re.search(r"^\s*command -v", s, re.M))
check("rc/ntpd.c (metal _r2): ntpd_synced fetches the owed lists when ntp_ready flips",
      'notify_rc("restart_diskmon");\n#endif\n\t\t/* reaper 2026-11-07 (metal _r2)' in read("rc/ntpd.c") and "\t\twallguard_on_firewall();\n" in read("rc/ntpd.c"))
check("busybox: the `command` builtin is on (owner, 2026-11-07; acme.sh uses it too)",
      "\nCONFIG_ASH_CMDCMD=y\n" in read("busybox/config_base") and "CONFIG_ASH_CMDCMD is not set" not in read("busybox/config_base"))
check("wallguard.sh: the D-1 gate counts a list's allows as names it carries",
      s.count('num(part[j], "names") + num(part[j], "allows")') == 2)
check("wallguard.sh: the safe-search refresh stays with the full update (or a reboot that took the file)",
      '{ [ -z "${ONLY+x}" ] || [ ! -f "$D/safesearch" ]; } && safesearch' in s)

print("%d failure(s)" % len(fails))
sys.exit(1 if fails else 0)
