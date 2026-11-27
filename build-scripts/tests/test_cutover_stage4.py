#!/usr/bin/env python3
"""Native-UI cutover, stage 4 (2026-11-26): the sign-in, password, error, block, node-message and logout pages and the six
status bodies are self-contained Reaper files.

  Main_Login.asp        sign-in. The exchange with httpd is the stock one (get_Nonce.cgi, then a form POST to login_v2.cgi with
                        sha256(name:nonce:password:cnonce)); the state comes from login_error_info(), printed once.
  Main_Password.asp     set / change the router login: the stock rules in the stock order, the apply form, then chpass.cgi.
  error_page.htm        "no Internet connection", shown to LAN devices by the connection watcher (and ?flag=9 by a mesh node).
  blocking.asp          "this device is blocked" (parental control; a mobile-data limit).
  message.htm           what a mesh node shows instead of its settings pages.
  Logout.asp            only drawn for the address with a query; signing out is the plain address, answered by httpd.
  Restarting / Updating / UpdateError / UpdateError_reboot / Uploading / UploadError
                        bodies httpd writes into the answer of a reboot / upload request; they act on the sender's page when it
                        has the stock functions and leave any other sender alone.
None of them loads a script file or anything of the stock UI. The pages read before sign-in ask only for addresses httpd
serves before sign-in. Each page's behaviour is compared with the page it replaces by the maintainer's harnesses (both run in
a DOM on the same scripted httpd answers); this suite pins the source facts those rest on.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, shutil, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "reaper_inject.c")):
    print("SKIP: no router source tree with httpd/reaper_inject.c (argv[1] or REAPER_ROUTER_SRC)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name + (" - " + str(detail)[:600] if detail else ""))
def rd(*p): return open(os.path.join(SRC, *p), encoding="utf-8", errors="surrogateescape").read()
def has(*p): return os.path.isfile(os.path.join(SRC, *p))
def table(text, name):
    m = re.search(r"%s\[\]\s*=\s*\{(.*?)\n\};" % re.escape(name), text, re.S)
    return re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S) if m else ""

inj = rd("httpd", "reaper_inject.c"); web = rd("httpd", "web.c")
PAGES = ["Main_Login.asp", "Main_Password.asp", "error_page.htm", "blocking.asp", "message.htm", "Logout.asp"]
BODIES = ["Restarting.asp", "Updating.asp", "UpdateError.asp", "UpdateError_reboot.asp", "Uploading.asp", "UploadError.asp"]
P = dict((f, rd("www", f)) for f in PAGES + BODIES)

# ---------------------------------------------------------------- nothing of the stock UI
for f in PAGES + BODIES:
    s = P[f]
    check("%s: no script file, no stock script or stylesheet, ASCII" % f,
          not re.search(r"<script[^>]+src=", s) and not re.search(r"jquery|state\.js|httpApi\.js|popup\.js|general\.js|require\.min|https_redirect\.js|other\.css|form_style|index_style", s)
          and all(ord(c) < 127 for c in s), [w for w in ("jquery", "state.js", "httpApi.js", "other.css") if w in s])
    check("%s: no eval, no document.write, no markup built from text" % f, "eval(" not in s and "document.write" not in s and "innerHTML" not in s)
for f in PAGES:
    check("%s: dictionary texts live in the markup, never inside the script" % f, "<#" not in "".join(re.findall(r"<script>(.*?)</script>", P[f], re.S)) or f == "Main_Login.asp")
check("none of them names the stock wizard or the retired stock landing page",
      all("QIS_wizard" not in P[f] and "index.asp" not in P[f] for f in PAGES + BODIES))

# ---------------------------------------------------------------- pages read before sign-in ask only for what httpd serves then
OPEN_OK = re.compile(r"^(/favicon\.ico|/fonts/[a-z0-9-]+\.woff2|images/RT-96U_REAPER_Header(_anim)?\.webp|Main_Login\.asp|/|/Logout\.asp|)$")
for f in ("Main_Login.asp", "error_page.htm", "blocking.asp", "message.htm"):
    refs = re.findall(r"""(?:src|href)=["']([^"'<>]*)["']""", P[f]) + re.findall(r"url\('(/[^']+)'\)", P[f])
    refs = [r for r in refs if not r.startswith("data:")]
    bad = [r for r in refs if not OPEN_OK.match(r)]
    check("%s: every file it names is served before sign-in (fonts, the header image, the icon)" % f, not bad and "/reaper/" not in P[f] and "reaper_util" not in P[f], bad)
for name in ("Main_Login.asp", "error_page.htm*", "blocking.asp", "WAN_info.asp", "get_Nonce.cgi", "login_v2.cgi", "captcha.gif", "chdom.json"):
    m = re.search(r'\{\s*"%s"[^\n]*\}' % re.escape(name), web)
    check("httpd serves %s before sign-in" % name, m is not None and re.search(r",\s*NULL\s*\}", m.group(0)) is not None, m.group(0) if m else "no row")

# ---------------------------------------------------------------- sign-in
lg = P["Main_Login.asp"]
check("sign-in: the login state is printed once (httpd resets it as it prints it)", lg.count("<% login_error_info(); %>") == 1 and "var login_info = tryParseJSON('<% login_error_info(); %>');" in lg)
check("sign-in: the nonce request, then the form post to login_v2.cgi",
      "fetch('get_Nonce.cgi', {" in lg and "body: JSON.stringify({id: id})" in lg and '<form method="post" name="form" action="login_v2.cgi" target="">' in lg and "f.submit();" in lg)
check("sign-in: the digest is sha256(name:nonce:password:cnonce) and the typed fields are not sent",
      "f.login_authorization.value = sha256(f.login_username.value + ':' + nonce + ':' + f.login_passwd.value + ':' + cnonce);" in lg
      and all(("f.%s.disabled = true;" % n) in lg for n in ("login_username", "login_passwd", "captcha_text")) and "f.login_captcha.value = btoa(f.captcha_text.value);" in lg)
check("sign-in: the page to open afterwards is filtered as before (no other site, no script address, never the sign-in or logout page)",
      all(w in lg for w in ('redirect_page == "Logout.asp"', 'redirect_page == "Main_Login.asp"', 'redirect_page.indexOf("//") != -1', 'redirect_page.indexOf("http") != -1',
                            'redirect_page.indexOf(".asp") == -1 && redirect_page.indexOf(".htm") == -1')))
check("sign-in: the form fields httpd reads are there",
      all(('name="%s"' % n) in lg for n in ("group_id", "action_mode", "action_script", "action_wait", "next_page", "login_authorization", "id", "cnonce", "login_captcha"))
      and '<input type="hidden" name="current_page" value="Main_Login.asp">' in lg)
check("sign-in: every state httpd can report has its text (wrong login, lock with countdown, permanent lock, captcha, other admin, logged out)",
      all(('id="%s"' % i) in lg for i in ("error_text_3", "error_text_7", "rtime", "error_text_11", "error_captcha_field", "nologin_field", "logout_field", "last_time_lock_warning"))
      and all(("flag == %d" % n) in lg for n in (3, 7, 8, 9, 10, 11)))
check("sign-in: the HTTPS notice keeps the stock rule (SG / AA / EU unit, secure defaults, both protocols on, plain HTTP)",
      "if (!/^(SG|AA|EU)/.test(ttc) || !isSupport(\"secure_default\") || <% nvram_get_js(\"http_enable\"); %> != \"2\" || location.protocol === 'https:') return;" in lg)
check("sign-in: the redirect to the admin's own address is still decided by the probe (REAPER-DUT-REDIR)",
      "REAPER-DUT-REDIR" in lg and "ROUTERHOSTNAME = h;" in lg and "loadScript(domainNameUrl + '/chdom.json?hostname=' + header_info.host);" in lg
      and 'var chdom = function(){if(getQueryString("redirct")!=="false" && !loadScriptTimeout)window.location.href=domainNameUrl};' in lg)
check("sign-in: httpd still knows the page by name (served during a lock, never bounced, on the node whitelist)",
      '\t"Main_Login.asp",' in table(inj, "reaper_skip") and 'strncmp(file, "Main_Login.asp", 14)' in rd("httpd", "httpd.c") and "window.top.location.href='/Main_Login.asp';" in rd("httpd", "httpd.c"))

# ---------------------------------------------------------------- password
pw = P["Main_Password.asp"]
vf = pw[pw.find("function validForm(){"):pw.find("/* POST /chpass.cgi")]
order = ["text('m_cur_blank')", "chkLoginId(f.http_username_x)", "byId('defpassCheckbox').checked) return true;", "text('m_pw_blank')", "text('m_pw_differ')", "text('m_pw_is_name')",
         "strictPw ? !chkLoginPw_KR(pw) : !chkLoginPw(pw)", "text('m_pw_default')", "check_common_string(pw.value)"]
pos = [vf.find(w) for w in order]
check("password: the rules run in the stock order", all(p >= 0 for p in pos) and pos == sorted(pos), list(zip(order, pos)))
check("password: the two password rules (5-32 characters; or 10+ with a letter, a digit and a symbol) and the shared tail",
      "if (obj.value.length > 0 && obj.value.length < 5) return reject(obj, text('m_pw_short'), false);" in pw and "v.length < 10" in pw
      and "if (v.length > 32) return reject(obj, text('m_pw_long').replace(\"%1$@\", min), false);" in pw and 'return chkTail(obj, "5", false);' in pw and 'return chkTail(obj, "10", true);' in pw)
check("password: the login name rule (letters, digits, - and _, not first; not root / guest / anonymous)",
      "/^[a-zA-Z0-9][a-zA-Z0-9\\-_]+$/i.test(obj.value)" in pw and 'obj.value == "root" || obj.value == "guest" || obj.value == "anonymous"' in pw)
check("password: the apply form goes to the hidden frame and carries the page token itself",
      '<form method="post" name="form" action="/start_apply.htm" target="hidden_frame">' in pw and '<input type="hidden" name="http_id" value="">' in pw
      and "f.http_id.value = HTTPID;" in pw and 'var HTTPID = <% nvram_get_js("http_id"); %>;' in pw and '<input type="hidden" name="current_page" value="Main_Password.asp">' in pw)
check("password: chpass.cgi gets base64 for the new pair, lower-case hex MD5 for the current pair, and the token",
      "x.open('POST', '/chpass.cgi', true);" in pw and "if (postData.new_username) postData.new_username = btoa(postData.new_username);" in pw
      and "if (postData.new_passwd) postData.new_passwd = btoa(postData.new_passwd);" in pw and "if (postData.cur_username) postData.cur_username = md5hex(postData.cur_username);" in pw
      and "if (postData.cur_passwd) postData.cur_passwd = md5hex(postData.cur_passwd);" in pw and "if (!postData.http_id) postData.http_id = HTTPID;" in pw)
check("password: the current pair is sent only when a password is already set; the name is a script literal from httpd",
      re.search(r'if \(!defaultPass\)\{\s*postData\.cur_username = <% nvram_get_js\("http_username"\); %>;\s*postData\.cur_passwd = byId\(\'http_passwd_cur\'\)\.value;\s*\}', pw) is not None
      and 'var defaultPass = ("<% check_pw(); %>" == "1");' in pw)
check("password: the answer is read (200 lands on the start page; 401 and 402 have their own text) and chpass follows the apply by 100 ms",
      'if (rc != "200"){' in pw and "rc == \"401\" ? 'm_wrong_cur' : rc == \"402\" ? 'm_five' : 'm_fail'" in pw and 'setTimeout(function(){ location.href = "/"; }, showLoading_time);' in pw
      and re.search(r"f\.submit\(\);\s*setTimeout\(function\(\)\{.*?chpass\(postData, function\(rc\)\{.*?\}, 100\);", pw, re.S) is not None)
check("password: Modify does nothing while the DST table is awaited (button and Enter alike)", "if (byId('btn_apply').disabled || !validForm()) return;" in pw)
check("password: the page keeps its own chrome - httpd adds the banner, not the stock-page stylesheet, and never bounces it",
      '"Main_Password.asp"' in table(inj, "reaper_banner_only") and '"Main_Password.asp"' not in table(inj, "reaper_css_only") and '"Main_Password.asp"' in table(inj, "reaper_skip"))
node = shutil.which("node")
if node:
    js = ("var s=require('fs').readFileSync(process.argv[1],'utf8');"
          "var m=s.slice(s.indexOf('function md5hex(s){'));m=m.slice(0,m.indexOf('\\nfunction defpassChange'));eval(m);"
          "var c=require('crypto'),bad=0,i,t='';for(i=0;i<200;i++){t+=String.fromCharCode((i*37+11)%256);"
          "if(md5hex(t)!==c.createHash('md5').update(Buffer.from(t,'latin1')).digest('hex'))bad++;}"
          "var l=require('fs').readFileSync(process.argv[2],'utf8');var k=l.slice(l.indexOf('const sha256 = '));k=k.slice(0,k.indexOf('\\n'));eval(k.replace('const sha256','var sha256'));"
          "for(i=0,t='';i<200;i++){t+=String.fromCharCode(32+(i*7)%95);if(sha256(t)!==c.createHash('sha256').update(t).digest('hex'))bad++;}"
          "console.log(md5hex('admin')+' '+bad);")
    r = subprocess.run([node, "-e", js, os.path.join(SRC, "www", "Main_Password.asp"), os.path.join(SRC, "www", "Main_Login.asp")], capture_output=True, text=True, timeout=60)
    check("the MD5 of the password page and the SHA-256 of the sign-in page equal the reference ones on 400 inputs", r.stdout.strip() == "21232f297a57a5a743894a0e4a801fc3 0", (r.stdout + r.stderr)[:300])
else:
    print("note: node not found - the MD5 / SHA-256 replay is skipped")

# ---------------------------------------------------------------- error / block / node message / logout
ep = P["error_page.htm"]
check("error page: every case of the connection watcher has its block (1, 2 x3, 3, 4, 5 x2, 6, 8, 9) and an unknown one goes to the start page",
      all(('id="%s"' % i) in ep for i in ("c_1", "c_2a", "c_3", "c_4", "c_5a", "c_5b", "c_6", "c_8", "c_9", "c_admin", "animation_field")) and "parent.location = '/';" in ep)
check("error page: reconnecting asks httpd for the WAN state every second and reads three numbers, nothing else",
      "x.open('GET', '/WAN_info.asp', true);" in ep and "setTimeout(detect_ppp_connect, 1000);" in ep and "/wanstate\\s*=\\s*(-?\\d+)/.exec(t)" in ep and has("www", "WAN_info.asp"))
check("error page: the buttons lead to settings pages by their old names (httpd moves them to the Reaper page after sign-in)",
      all(w in ep for w in ("go('/Advanced_Modem_Content.asp')", "go('/Advanced_WAN_Content.asp')", "go('/updateSubnet.htm')"))
      and all(('"%s"' % n) in inj for n in ("advanced_modem_content.asp", "advanced_wan_content.asp", "advanced_operationmode_content.asp")) and has("www", "updateSubnet.htm"))
check("error page: a visitor while another admin is signed in is told to ask the administrator (the stock test could never be true)",
      'var other_admin = [<% is_logined_hook(); %>][0] === "0";' in ep and "body = other_admin ? 'c_admin' : 'c_8';" in ep)
bl = P["blocking.asp"]
check("block page: the two cases of this build; the button leads to the settings by an old page name httpd maps",
      'location.href = limit ? "Advanced_Modem_Content.asp" : "ParentalControl.asp";' in bl and '"parentalcontrol.asp"' in inj and "trendmicro" not in bl and "chdom" not in bl)
ms = P["message.htm"]
check("node message page: the probe of the mesh router and the 'router not found' page, as before",
      's.src = "http://" + cfg_master_ipaddr + "/chdom.json?hostname=" + cfg_master_ipaddr;' in ms and ms.count('window.location.href = "/error_page.htm?flag=9";') == 2
      and 'var chdom = function(){ window.location.href = "http://" + cfg_master_ipaddr; };' in ms and "}, 5000);" in ms)
check("logout: the file only offers the plain address, which httpd answers itself", 'href="/Logout.asp"' in P["Logout.asp"] and '!strcmp(file, "Logout.asp")' in rd("httpd", "httpd.c"))
for f in ("error_page.htm", "blocking.asp"):
    check("httpd never themes, bounces or banners %s (it is read by devices, not by the admin)" % f, ('"%s"' % f) in table(inj, "reaper_skip"))

# ---------------------------------------------------------------- status bodies
for f in BODIES:
    n = f[:-4]
    check("%s: names itself, is still what httpd writes, and leaves a sender without the stock functions alone" % f,
          ('var reaper_status = "%s";' % n) in P[f] and ('"%s"' % f) in web and ("function has(n){ try { return typeof P[n] === 'function'; }" in P[f] or f == "UploadError.asp"))
fwp = rd("www", "Reaper_Firmware.asp") if has("www", "Reaper_Firmware.asp") else ""
check("a refused firmware upload is recognised by the Firmware page: both refusal bodies carry the word it looks for, the accepted one does not",
      "indexOf('UpdateError') >= 0" in fwp and "UpdateError" in P["UpdateError.asp"] and "UpdateError" in P["UpdateError_reboot.asp"] and "UpdateError" not in P["Updating.asp"])
rs = P["Restarting.asp"]
check("Restarting: waits the reboot time, asks httpd_check.xml every second, then the start page - the default address after any factory reset",
      "setTimeout(check_httpd, reboot_needed_time * 1000);" in rs and 'x.open(\'GET\', "/httpd_check.xml", true);' in rs and "setTimeout(check_httpd, 1000);" in rs
      and 'action_mode == "Restore" || action_mode == "restore" || action_mode == "restore_erase"' in rs and 'P.location.href = "/";' in rs)
check("Updating: the stock bar times (reboot time + 40 on these models; 270 s for a sender without the model flag)",
      "bar(reboot_needed_time + 40, reboot_needed_time + 42);" in P["Updating.asp"] and "else bar(270, 272);" in P["Updating.asp"])

if fails:
    print("\n%d FAILED" % len(fails)); [print("  - " + f) for f in fails]; sys.exit(1)
print("\nall checks passed")
