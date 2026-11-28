#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Device pictures and device types (REAPER-DEVICON, owner 2026-11-27: "both steps", and close the old upload paths).

WHAT IS PINNED.
  httpd/web.c, reaper_dev.cgi:
    - set_icon accepts only data:image/png | image/jpeg | image/webp in base64 (never SVG, no other type, no parameter),
      decodes it strictly, checks the first bytes against the type, caps it at 32 KB decoded, at 256 pictures and at
      256 KB left free on /jffs; the MAC passes the 17-character shape check and isValidMacAddress() BEFORE any path
      is built from it (never ether_atoe); the file is written O_EXCL | O_NOFOLLOW to a temporary name and renamed;
      the stock storage format stays (/jffs/usericon/<MAC12>.log holding the data URL, usericon_md5.json kept).
    - icon_list / icon_get read the store without following a link or waiting on a FIFO and serve only a picture that
      passes the same check; set_type writes field 3 of the custom_clientlist record and keeps every other record byte
      for byte; set_type / set_icon / del_icon must be POSTs; every action sits behind the page token gate.
    - set_name: clearing a name keeps the type chosen for the device (it used to drop the whole record).
    - the old paths are closed: the custom_usericon / custom_usericon_del apply fields (dropped, never stored), the
      stock writers, and get_usericon_md5.cgi / backup_all_usericon.cgi / upload_all_usericon.cgi. renew_upload_icon()
      and the read hook get_upload_icon (the stock network page reads it) stay.
    When gcc is there, the new code is compiled on the host with stubs (-Wall -Werror) and driven end to end: the
    validator, the MAC check, planted links and FIFOs, the caps, GET refusal, set_type on the record format.
  www/reaper_util.js, ReaperIcons (under node with a DOM stub): own picture > picture of the device type > type glyph
    (from the stock device-map.css, the newer types from extend_custom_icon.json) > generic; a data URL outside the
    whitelist is never used (an SVG answer falls back to the glyph); the placeholder markup carries only checked
    characters; no innerHTML; its colours switch with colour-blind mode.
  The pages: the Devices page (icon in the name cell, the picture + type dialog, POSTs, ?mac= deep link), the AiMesh
    page (device icons open the Devices page for that MAC) and the dashboard client list use the helper; the type
    list matches the stock picker; the stock glyph sheet still ships.
Exit 0 pass, 1 fail, 77 skipped (no router source tree)."""
import os, re, shutil, subprocess, sys, tempfile, json

# the host harness for the web.c code (the extracted block is #included as helpers.inc / actions.inc)
HARNESS = r'''/* host harness for the REAPER-DEVICON code in httpd/web.c: compiles the extracted helpers and actions with stubs
 * (gcc -Wall -Werror) and drives the reaper_dev.cgi actions end to end against a temporary directory. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/types.h>

#ifndef RDIC_ROOT
#define RDIC_ROOT "/tmp/rdic_h"
#endif
#define RDIC_TESTDIR RDIC_ROOT "/usericon"
#define websWrite(wp, fmt, args...) ({ int TMPVAR = fprintf(wp, fmt, ## args); fflush(wp); TMPVAR; })
#define websWriteData(wp, buf, nChars) ({ int TMPVAR = fwrite(buf, 1, nChars, wp); fflush(wp); TMPVAR; })

static size_t strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; } return l; }
static size_t strlcat(char *d, const char *s, size_t n) { size_t l = strlen(d); if (l >= n) return l + strlen(s); return l + strlcpy(d + l, s, n - l); }

/* stubs */
int reaper_req_post = 1;
static char NV_CL[65536] = "";
static char *nvram_safe_get(const char *k) { return !strcmp(k, "custom_clientlist") ? NV_CL : ""; }
static int nvram_set(const char *k, const char *v) { if (!strcmp(k, "custom_clientlist")) strlcpy(NV_CL, v, sizeof(NV_CL)); return 0; }
static int nvram_commit(void) { return 0; }
static void rdev_audit(const char *a, const char *m, const char *d) { (void)a; (void)m; (void)d; }
static const char *CGI_K[8]; static const char *CGI_V[8]; static int CGI_N;
static char *get_cgi(const char *k) { int i; for (i = 0; i < CGI_N; i++) if (!strcmp(CGI_K[i], k)) return (char *)CGI_V[i]; return NULL; }

static int gk_valid_mac(const char *m)
{
	int i;
	if (!m || strlen(m) != 17) return 0;
	for (i = 0; i < 17; i++) {
		if ((i % 3) == 2) { if (m[i] != ':') return 0; }
		else if (!isxdigit((unsigned char)m[i])) return 0;
	}
	return 1;
}
int isValidMacAddress(const char* mac) {
	int i=0, s=0;
	while (*mac) {
		if (isxdigit(*mac)) i++;
		else if (*mac == ':' || *mac == '-') { if (i == 0 || i / 2 - 1 != s) return 0; ++s; }
		else return 0;
		++mac;
	}
	return (i == 12 && (s == 5 || s == 0));
}

#include "helpers.inc"

static void cgi(FILE *stream, const char *action)
{
#include "actions.inc"
	websWrite(stream, "{\"err\":\"action\"}");
}

static char OUT[200000];
static const char *run(const char *action, const char *k1, const char *v1, const char *k2, const char *v2)
{
	FILE *f = fmemopen(OUT, sizeof(OUT), "w");
	CGI_N = 0;
	if (k1) { CGI_K[CGI_N] = k1; CGI_V[CGI_N++] = v1; }
	if (k2) { CGI_K[CGI_N] = k2; CGI_V[CGI_N++] = v2; }
	cgi(f, action);
	fclose(f);
	return OUT;
}

static int fails;
static void chk(const char *name, int ok) { printf("%s %s\n", ok ? "ok  " : "FAIL", name); if (!ok) fails++; }

static char *b64(const unsigned char *b, size_t n, const char *prefix)
{
	static const char T[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
	char *o = malloc(strlen(prefix) + (n + 2) / 3 * 4 + 1), *p;
	size_t i;
	strcpy(o, prefix); p = o + strlen(o);
	for (i = 0; i < n; i += 3) {
		unsigned v = b[i] << 16 | (i + 1 < n ? b[i + 1] << 8 : 0) | (i + 2 < n ? b[i + 2] : 0);
		*p++ = T[v >> 18 & 63]; *p++ = T[v >> 12 & 63];
		*p++ = i + 1 < n ? T[v >> 6 & 63] : '=';
		*p++ = i + 2 < n ? T[v & 63] : '=';
	}
	*p = 0;
	return o;
}

int main(void)
{
	unsigned char png[64] = { 0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a }, jpg[40] = { 0xff, 0xd8, 0xff, 0xe0 },
		webp[40] = { 'R', 'I', 'F', 'F', 1, 0, 0, 0, 'W', 'E', 'B', 'P' }, svg[] = "<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>";
	static unsigned char big[RDIC_MAX_BYTES + 3];
	char *u;
	const char *r;
	struct stat st;

	if (mkdir(RDIC_ROOT, 0700) != 0 && errno != EEXIST) return 2;

	/* validator */
	chk("png accepted", rdic_check(u = b64(png, sizeof(png), "data:image/png;base64,")) == NULL); free(u);
	chk("jpeg accepted", rdic_check(u = b64(jpg, sizeof(jpg), "data:image/jpeg;base64,")) == NULL); free(u);
	chk("webp accepted", rdic_check(u = b64(webp, sizeof(webp), "data:image/webp;base64,")) == NULL); free(u);
	chk("svg+xml type refused", rdic_check(u = b64(svg, sizeof(svg) - 1, "data:image/svg+xml;base64,")) != NULL); free(u);
	chk("svg bytes labelled png refused (magic)", rdic_check(u = b64(svg, sizeof(svg) - 1, "data:image/png;base64,")) != NULL); free(u);
	chk("png bytes labelled jpeg refused", rdic_check(u = b64(png, sizeof(png), "data:image/jpeg;base64,")) != NULL); free(u);
	chk("gif type refused", rdic_check(u = b64(png, sizeof(png), "data:image/gif;base64,")) != NULL); free(u);
	chk("upper-case prefix refused", rdic_check(u = b64(png, sizeof(png), "DATA:image/png;base64,")) != NULL); free(u);
	chk("a parameter in the prefix refused", rdic_check(u = b64(png, sizeof(png), "data:image/png;charset=x;base64,")) != NULL); free(u);
	chk("bad base64 char refused", rdic_check("data:image/png;base64,iVBORw0KGgo\"AAAA") != NULL);
	chk("base64 length not x4 refused", rdic_check("data:image/png;base64,iVBORw0KGgoAAA") != NULL);
	chk("'=' inside refused", rdic_check("data:image/png;base64,iVBO=w0KGgoAAAAAAAAAAAAAAAAAAAA") != NULL);
	chk("empty refused", rdic_check("data:image/png;base64,") != NULL && rdic_check("") != NULL && rdic_check(NULL) != NULL);
	memcpy(big, png, 8);
	chk("33 KB refused as too large", (r = rdic_check(u = b64(big, sizeof(big), "data:image/png;base64,"))) && !strcmp(r, "RDIC_14")); free(u);
	chk("32 KB exactly accepted", rdic_check(u = b64(big, RDIC_MAX_BYTES, "data:image/png;base64,")) == NULL); free(u);
	chk("tiny refused", rdic_check(u = b64(png, 8, "data:image/png;base64,")) != NULL); free(u);
	/* MAC */
	{
		char m[13];
		chk("mac ok", rdic_mac12("aa:bb:cc:dd:ee:0f", m) && !strcmp(m, "AABBCCDDEE0F"));
		chk("mac zz:zz refused", !rdic_mac12("zz:zz", m));
		chk("mac + junk refused", !rdic_mac12("AA:BB:CC:DD:EE:FF\n/../x", m));
		chk("mac 12 hex refused (shape)", !rdic_mac12("AABBCCDDEEFF", m));
		chk("mac dashes refused", !rdic_mac12("AA-BB-CC-DD-EE-FF", m));
		chk("mac NULL refused", !rdic_mac12(NULL, m));
		chk("name kinds", rdic_name_kind("AABBCCDDEEFF.log", m) == 1 && rdic_name_kind("34.log", m) == 2 &&
			rdic_name_kind("usericon_md5.json", m) == 0 && rdic_name_kind("../x.log", m) == 0 && rdic_name_kind("1234.log", m) == 0 &&
			rdic_name_kind(".AABBCCDDEEFF.log.tmp", m) == 0);
		chk("tail typed", rdic_tail_typed("0>34>>0") && !rdic_tail_typed("0>0>>0") && !rdic_tail_typed("0>>>0") && !rdic_tail_typed("") && rdic_tail_typed("0>05>>0"));
	}
	/* actions */
	r = run("icon_list", NULL, NULL, NULL, NULL);
	chk("icon_list, no dir", !strcmp(r, "{\"ok\":1,\"cap\":256,\"icons\":{},\"types\":{},\"n\":0}"));
	u = b64(png, sizeof(png), "data:image/png;base64,");
	r = run("set_icon", "mac", "aa:bb:cc:dd:ee:ff", "icon", u);
	chk("set_icon ok", !strcmp(r, "{\"ok\":1}"));
	chk("file written under the upper-case name", stat(RDIC_TESTDIR "/AABBCCDDEEFF.log", &st) == 0 && st.st_size == (off_t)strlen(u));
	chk("no temp file left", stat(RDIC_TESTDIR "/.AABBCCDDEEFF.log.tmp", &st) != 0);
	r = run("icon_list", NULL, NULL, NULL, NULL);
	chk("icon_list lists it", strstr(r, "\"AABBCCDDEEFF\":\"") != NULL && strstr(r, "\"n\":1}") != NULL);
	r = run("icon_get", "ids", "AABBCCDDEEFF,../etc,34", NULL, NULL);
	{ char want[400]; snprintf(want, sizeof(want), "{\"ok\":1,\"src\":{\"AABBCCDDEEFF\":\"%s\"}}", u);
	  chk("icon_get returns it, ignores junk ids", !strcmp(r, want)); }
	/* a planted bad file is not served; a symlink is not followed; a FIFO does not block */
	{ FILE *f = fopen(RDIC_TESTDIR "/112233445566.log", "w"); fputs("data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=", f); fclose(f); }
	if (symlink("/etc/passwd", RDIC_TESTDIR "/AABBCCDDEE00.log")) return 2;
	if (mkfifo(RDIC_TESTDIR "/AABBCCDDEE11.log", 0600)) return 2;
	r = run("icon_get", "ids", "112233445566,AABBCCDDEE00,AABBCCDDEE11", NULL, NULL);
	chk("bad / linked / fifo files not served", !strcmp(r, "{\"ok\":1,\"src\":{}}"));
	r = run("icon_list", NULL, NULL, NULL, NULL);
	chk("icon_list skips the link and the fifo", strstr(r, "AABBCCDDEE00") == NULL && strstr(r, "AABBCCDDEE11") == NULL);
	/* set over a planted link: the link is replaced, its target untouched */
	unlink(RDIC_TESTDIR "/AABBCCDDEE00.log");
	{ FILE *f = fopen(RDIC_ROOT "/victim", "w"); fputs("keep", f); fclose(f); }
	if (symlink(RDIC_ROOT "/victim", RDIC_TESTDIR "/AABBCCDDEE00.log")) return 2;
	if (symlink(RDIC_ROOT "/victim", RDIC_TESTDIR "/.AABBCCDDEE00.log.tmp")) return 2;
	r = run("set_icon", "mac", "AA:BB:CC:DD:EE:00", "icon", u);
	{ char b[8] = ""; FILE *f = fopen(RDIC_ROOT "/victim", "r"); if (fgets(b, sizeof(b), f) == NULL) b[0] = 0; fclose(f);
	  chk("set over planted links: target untouched, file replaced", !strcmp(r, "{\"ok\":1}") && !strcmp(b, "keep") &&
	      lstat(RDIC_TESTDIR "/AABBCCDDEE00.log", &st) == 0 && S_ISREG(st.st_mode)); }
	r = run("set_icon", "mac", "AA:BB:CC:DD:EE:01", "icon", "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=");
	chk("set_icon svg refused", strstr(r, "\"ek\":\"RDIC_13\"") != NULL && stat(RDIC_TESTDIR "/AABBCCDDEE01.log", &st) != 0);
	r = run("set_icon", "mac", "zz:zz", "icon", u);
	chk("set_icon junk mac refused", strstr(r, "RDEVE_2") != NULL);
	reaper_req_post = 0;
	r = run("set_icon", "mac", "AA:BB:CC:DD:EE:02", "icon", u);
	chk("set_icon by GET refused", strstr(r, "RDIC_P") != NULL && stat(RDIC_TESTDIR "/AABBCCDDEE02.log", &st) != 0);
	r = run("set_type", "mac", "AA:BB:CC:DD:EE:02", "type", "34");
	chk("set_type by GET refused", strstr(r, "RDIC_P") != NULL);
	reaper_req_post = 1;
	/* an old lower-case stock file for the same device is replaced, not doubled */
	{ FILE *f = fopen(RDIC_TESTDIR "/a1b2c3d4e5f6.log", "w"); fputs(u, f); fclose(f); }
	r = run("set_icon", "mac", "A1:B2:C3:D4:E5:F6", "icon", u);
	chk("case twin dropped on set", !strcmp(r, "{\"ok\":1}") && stat(RDIC_TESTDIR "/a1b2c3d4e5f6.log", &st) != 0 && stat(RDIC_TESTDIR "/A1B2C3D4E5F6.log", &st) == 0);
	r = run("del_icon", "mac", "aa:bb:cc:dd:ee:ff", NULL, NULL);
	chk("del_icon", !strcmp(r, "{\"ok\":1}") && stat(RDIC_TESTDIR "/AABBCCDDEEFF.log", &st) != 0);
	/* the cap */
	{
		int i; char p[80];
		for (i = 0; i < RDIC_MAX_FILES; i++) { FILE *f; snprintf(p, sizeof(p), RDIC_TESTDIR "/0000000%05X.log", i); f = fopen(p, "w"); fputs(u, f); fclose(f); }
		r = run("set_icon", "mac", "AA:BB:CC:DD:EE:77", "icon", u);
		chk("file-count cap", strstr(r, "RDIC_15") != NULL);
		r = run("set_icon", "mac", "00:00:00:00:00:05", "icon", u);
		chk("replacing an existing picture is allowed at the cap", !strcmp(r, "{\"ok\":1}"));
	}
	free(u);
	/* set_type */
	strcpy(NV_CL, "<Laptop>AA:BB:CC:DD:EE:FF>0>0>>0<Other>11:22:33:44:55:66>1>9>cb>1");
	r = run("set_type", "mac", "aa:bb:cc:dd:ee:ff", "type", "34");
	chk("set_type keeps the name, others byte for byte", !strcmp(r, "{\"ok\":1}") && !strcmp(NV_CL, "<Other>11:22:33:44:55:66>1>9>cb>1<Laptop>AA:BB:CC:DD:EE:FF>0>34>>0"));
	r = run("set_type", "mac", "11:22:33:44:55:66", "type", "5");
	chk("set_type keeps the other fields", !strcmp(NV_CL, "<Laptop>AA:BB:CC:DD:EE:FF>0>34>>0<Other>11:22:33:44:55:66>1>5>cb>1"));
	r = run("set_type", "mac", "77:77:77:77:77:77", "type", "10");
	chk("set_type on an unnamed device adds a record with no name", strstr(NV_CL, "<>77:77:77:77:77:77>0>10>>0") != NULL);
	r = run("set_type", "mac", "77:77:77:77:77:77", "type", "0");
	chk("type 0 on a nameless record drops it", strstr(NV_CL, "77:77:77:77:77:77") == NULL);
	r = run("set_type", "mac", "aa:bb:cc:dd:ee:ff", "type", "999");
	chk("type 999 refused", strstr(r, "RDIC_18") != NULL);
	r = run("set_type", "mac", "aa:bb:cc:dd:ee:ff", "type", "3>x");
	chk("type with a delimiter refused", strstr(r, "RDIC_18") != NULL);
	r = run("set_type", "mac", "aa:bb:cc:dd:ee:ff<x", "type", "3");
	chk("set_type junk mac refused", strstr(r, "RDEVE_2") != NULL);
	printf("%d failing\n", fails);
	return fails ? 1 : 0;
}
'''

# the node harness for the ReaperIcons block (a DOM and XMLHttpRequest stub, the router's answers faked)
NODEJS = r'''/* node harness for the REAPER-DEVICON block of www/reaper_util.js: a tiny DOM and XMLHttpRequest stub, the router's
   answers faked; prints one JSON object of results. argv[2] = the block's source file. */
var fs = require('fs');
var SRC = fs.readFileSync(process.argv[2], 'latin1');
var PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
var PNG2 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAEklEQVR42mP8z8BQz0AEYBxVSF8A2hcH/V0X5DMAAAAASUVORK5CYII=';
var SVG = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxzY3JpcHQ+YWxlcnQoMSk8L3NjcmlwdD48L3N2Zz4=';
var GLY0 = 'data:image/png;base64,AAAA', GLY34 = 'data:image/png;base64,BBBB', GLY99 = 'data:image/png;base64,CCCC';
var timers = [], reqs = [];
global.window = global;
global.setTimeout = function(f){ timers.push(f); return timers.length; };
global.clearTimeout = function(){};
function flush(){ var n = 0; while(timers.length && n++ < 500) timers.shift()(); }
function El(tag){ this.tagName = String(tag).toUpperCase(); this.children = []; this.attrs = {}; this.className = ''; this.textContent = ''; this.parentNode = null; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
El.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
El.prototype.appendChild = function(c){ this.children.push(c); c.parentNode = this; return c; };
El.prototype.removeChild = function(c){ var i = this.children.indexOf(c); if(i >= 0) this.children.splice(i, 1); c.parentNode = null; return c; };
Object.defineProperty(El.prototype, 'firstChild', { get: function(){ return this.children[0] || null; } });
Object.defineProperty(El.prototype, 'innerHTML', { set: function(){ throw new Error('innerHTML used'); }, get: function(){ return ''; } });
El.prototype.querySelectorAll = function(){ return []; };
global.document = { head: new El('head'), createElement: function(t){ return new El(t); }, querySelectorAll: function(){ return []; } };
var LIST = {ok: 1, cap: 256, icons: {AABBCCDDEEFF: '1-10', '222222222222': '1-10', 'a1b2c3d4e5f6': '5-9'}, types: {'5': '1-10'}, n: 3};
global.XMLHttpRequest = function(){ this.readyState = 0; this.status = 0; this.responseText = ''; };
XMLHttpRequest.prototype.open = function(m, u){ this.m = m; this.u = u; };
XMLHttpRequest.prototype.send = function(){
  var x = this; reqs.push(x.u);
  timers.push(function(){
    var u = x.u, body = null, m;
    if(u.indexOf('/device-map/device-map.css') === 0) body = 'body{color:#000}\ni.type0 {\n\t--svg: url("' + GLY0 + '");\n}\ni.type1, i.type34{--svg:url(' + GLY34 + ')}\ni.type35{--svg:url("data:image/svg+xml;base64,AAAA")}\n';
    else if(u.indexOf('/ajax/extend_custom_icon.json') === 0) body = JSON.stringify({x: {list: [{num: 99, src: GLY99}, {num: 98, src: 'javascript:alert(1)'}]}});
    else if(u.indexOf('/reaper_dev.cgi?action=icon_list') === 0) body = JSON.stringify(LIST);
    else if((m = /^\/reaper_dev\.cgi\?action=icon_get&ids=([^&]*)/.exec(u))){
      var ids = decodeURIComponent(m[1]).split(','), src = {};
      ids.forEach(function(i){ if(i === 'AABBCCDDEEFF') src[i] = PNG; else if(i === '5') src[i] = PNG2; else if(i === '222222222222') src[i] = SVG; else if(i === 'a1b2c3d4e5f6') src[i] = PNG; });
      body = JSON.stringify({ok: 1, src: src});
    }
    x.readyState = 4; x.status = body === null ? 404 : 200; x.responseText = body || '';
    if(x.onreadystatechange) x.onreadystatechange();
  });
};
var s = SRC.indexOf('/* REAPER-DEVICON-BEGIN'), e = SRC.indexOf('/* REAPER-DEVICON-END */');
eval(SRC.slice(s, e));
var RI = window.ReaperIcons, out = {};
function k(p){ return p.k + (p.t ? ':' + p.t : '') + (p.u ? ':' + (p.u === PNG ? 'PNG' : p.u === PNG2 ? 'PNG2' : 'OTHER') : ''); }
out.before = k(RI.pick('AA:BB:CC:DD:EE:FF', '34'));
RI.init('tok&x');
flush();
/* the first look queues the pictures (one batched icon_get); the glyph shows until they arrive */
out.firstLook = k(RI.pick('aa:bb:cc:dd:ee:ff', '34'));
['A1:B2:C3:D4:E5:F6', '11:22:33:44:55:66', '22:22:22:22:22:22'].forEach(function(m){ RI.pick(m, '5'); RI.pick(m, '34'); });
flush();
out.custom = k(RI.pick('aa:bb:cc:dd:ee:ff', '34'));
out.customDash = k(RI.pick('AA-BB-CC-DD-EE-FF', ''));
out.lowerStem = k(RI.pick('A1:B2:C3:D4:E5:F6', '0'));
out.typePic = k(RI.pick('11:22:33:44:55:66', '5'));
out.glyph = k(RI.pick('11:22:33:44:55:66', '34'));
out.svgRefused = k(RI.pick('22:22:22:22:22:22', '34'));
out.unknownType = k(RI.pick('11:22:33:44:55:66', '42'));
out.noType = k(RI.pick('', ''));
out.svgGlyphDropped = k(RI.pick('', '35'));
out.ext1 = k(RI.pick('', '99'));
flush();
out.ext2 = k(RI.pick('', '99'));
out.extBad = k(RI.pick('', '98'));
var el = RI.icon('AA:BB:CC:DD:EE:FF', {type: '34', size: 'sm'});
out.elTag = el.tagName; out.elClass = el.className; out.elChild = el.firstChild && el.firstChild.tagName; out.elSrc = el.firstChild && el.firstChild.src === PNG;
var g = RI.icon('11:22:33:44:55:66', {type: '34'});
out.glyphChild = g.firstChild && g.firstChild.className;
out.html = RI.html('"><img src=x onerror=alert(1)>', '1" onmouseover="x', 'lg');
out.htmlOk = RI.html('aa:bb:cc:dd:ee:ff', '34', 'sm');
out.valid = [PNG, 'data:image/jpeg;base64,/9j/AAAA', 'data:image/webp;base64,UklGRgAA'].map(RI.valid);
out.invalid = [SVG, 'data:image/gif;base64,R0lGOD', 'javascript:alert(1)', 'data:text/html;base64,PHNjcmlwdD4=', 'DATA:image/png;base64,iVBO',
  'data:image/png;base64,iVBO"onerror="x', 'data:image/png;charset=utf-8;base64,iVBO', PNG + ' ', 'data:image/png;base64,' + new Array(44000).join('A'), null, 42].map(RI.valid);
out.has = [RI.has('AA:BB:CC:DD:EE:FF'), RI.has('11:22:33:44:55:66')];
out.reqs = reqs;
out.styleSheets = document.head.children.length;
out.glyphRules = document.head.children.map(function(c){ return c.textContent; }).join('').indexOf('.rdic .rdic-g.t34') >= 0;
console.log(JSON.stringify(out));
'''

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "httpd", "web.c")) or not os.path.isfile(os.path.join(SRC, "www", "reaper_util.js")):
    print("SKIP: no router source tree (argv[1] or REAPER_ROUTER_SRC = .../release/src/router)"); sys.exit(77)
fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:600] if detail else ""))
def rd(*p):
    return open(os.path.join(SRC, *p), encoding="latin-1").read()

web = rd("httpd", "web.c")
m = re.search(r"/\* REAPER-DEVICON-BEGIN.*?/\* REAPER-DEVICON-END \*/", web, re.S)
H = m.group(0) if m else ""
a = web.find("/* ---------------- REAPER-DEVICON (2026-11-27): device types and pictures")
b = web.find("/* ---------------- STORE_STATUS: durable-storage snapshot", a)
A = web[a:b] if a >= 0 and b > a else ""
cgi = web[web.find("static void do_reaper_dev_cgi(char *url, FILE *stream)"):]
cgi = cgi[:cgi.find("\n}\n") + 3]
def fn(name):
    i = H.find(name + "(")
    j = H.find("\n}\n", i)
    return H[i:j] if i >= 0 and j > i else ""
def action(name):
    i = A.find('if (!strcmp(action, "%s")) {' % name)
    j = A.find("\n\t}\n", i)
    return A[i:j] if i >= 0 and j > i else ""

# ---------------------------------------------------------------- the upload checks (static)
check("web.c: one REAPER-DEVICON helper block, the actions inside do_reaper_dev_cgi", web.count("REAPER-DEVICON-BEGIN") == 1 and A != "" and A in cgi)
pre = re.search(r"rdic_prefix\[\]\s*=\s*\{([^}]*)\}", H)
check("prefix whitelist is exactly png, jpeg, webp in base64 (no svg, no other type)",
      pre is not None and re.findall(r'"([^"]*)"', pre.group(1)) == ["data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,"]
      and "svg" not in pre.group(1).lower())
check("the prefix is compared exactly (strncmp, case-sensitive)", "strncmp(u, rdic_prefix[i], n)" in fn("static int rdic_kind"))
check("strict base64: length multiple of 4, alphabet only, '=' only at the end",
      "n % 4" in fn("static int rdic_b64dec") and "rdic_b64v(c)) < 0" in fn("static int rdic_b64dec") and "i + 4 == n && k >= 4 - pad" in fn("static int rdic_b64dec"))
check("magic bytes checked against the declared type (PNG signature, JPEG FFD8FF, RIFF....WEBP)",
      "0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a" in H and "b[0] == 0xff && b[1] == 0xd8 && b[2] == 0xff" in H and '!memcmp(b + 8, "WEBP", 4)' in H
      and "rdic_magic_ok(kind, rdic_buf, n)" in fn("static const char *rdic_check"))
check("size caps: 32 KB decoded, 256 pictures, 256 KB free on /jffs",
      "#define RDIC_MAX_BYTES\t32768" in H and "#define RDIC_MAX_FILES\t256" in H and "#define RDIC_MIN_FREE\t(256 * 1024)" in H
      and "n >= RDIC_MAX_FILES" in action("set_icon") and 'statvfs("/jffs", &v)' in action("set_icon") and "RDIC_MIN_FREE + len" in action("set_icon"))
mac12 = fn("static int rdic_mac12")
check("MAC: 17-character shape check, then isValidMacAddress, then the 12-hex stem; never ether_atoe",
      "!gk_valid_mac(mac) || !isValidMacAddress(mac)" in mac12 and "ether_atoe" not in H + A)
si = action("set_icon")
check("set_icon: MAC and picture checked before any path is built or /jffs touched",
      si.find("rdic_mac12(mac, m12)") >= 0 and si.find("rdic_mac12(mac, m12)") < si.find("rdic_check(icon)") < si.find("rdic_dir_ok(1)")
      < si.find('snprintf(fname, sizeof(fname), "%s.log", m12)') < si.find("rdic_put(fname"))
put = fn("static int rdic_put")
check("write: temporary file opened O_CREAT | O_EXCL | O_NOFOLLOW, synced, renamed over the old one",
      "O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW" in put and "fsync(fd)" in put and "rename(tmp, dst)" in put)
load = fn("static char *rdic_load")
check("read: O_NOFOLLOW | O_NONBLOCK, regular files only, size-capped, checked like an upload before it is served",
      "O_RDONLY | O_NOFOLLOW | O_NONBLOCK" in load and "S_ISREG(st.st_mode)" in load and "if (rdic_check(b) != NULL) {" in load
      and "rdic_load(p, &got)" in fn("static void rdic_emit"))
gu = web[web.find("ej_get_upload_icon(int eid, webs_t wp, int argc, char **argv) {"):]
gu = gu[:gu.find("\n}\n")]
check("the stock get_upload_icon hook serves a file only through the same check (it used to copy any file out raw)",
      "if((icon = rdic_load(file_name, &icon_len)) != NULL) {" in gu and "dump_file(" not in gu)
check("the store directory must be a real directory (lstat, not a link)", "lstat(RDIC_DIR, &st)" in fn("static int rdic_dir_ok") and "S_ISDIR(st.st_mode)" in fn("static int rdic_dir_ok"))
check("stock format kept: /jffs/usericon/<MAC12>.log holding the data URL, usericon_md5.json updated",
      '#define RDIC_DIR\t"/jffs/usericon"' in H and 'rdic_put(fname, icon, len)' in si and '"usericon_md5.json"' in H and "rdic_md5_set(m12, icon)" in si)
check("changes are POSTs; reads and writes sit behind the token gate",
      'if (!strcmp(action, "set_type") || !strcmp(action, "set_icon") || !strcmp(action, "del_icon")) {\n\t\tif (!reaper_req_post) {' in A
      and cgi.find("reaper_gate()") < cgi.find(A[:60]))
st = action("set_type")
check("set_type: digits only, 0..255; field 3 replaced, the name and the other fields kept; MAC checked",
      'strspn(ty, "0123456789") != strlen(ty)' in st and "(t = atoi(ty)) > 255" in st and "!gk_valid_mac(mac) || !isValidMacAddress(mac)" in st
      and '"%.*s>%d%s"' in st and "rdev_audit(\"type\"" in st)
check("set_name: clearing the name keeps a chosen type (record kept with an empty name)",
      "if (!keep && rdic_tail_typed(oldtail))\n\t\t\t\tkeep = 2;" in cgi and 'keep == 1 ? clean : ""' in cgi)
check("icon_get: at most 32 ids, each must be a MAC12 or a type number", "cnt < RDIC_GET_MAX" in action("icon_get") and "rdic_name_kind(nm, stem)" in action("icon_get")
      and "#define RDIC_GET_MAX\t32" in H)

ca = web[web.find("ej_get_customized_attribute(int eid, webs_t wp, int argc, char **argv) {"):]
ca = ca[:ca.find("\n}\n")]
check("REAPER-NET-FF385: the portal look reader puts only a 1..13-digit profile id into its /jffs path (else NoData)",
      "REAPER-NET-FF385" in ca and 'strlen(profile_id) > 13 || strspn(profile_id, "0123456789") != strlen(profile_id)' in ca
      and 0 < ca.find('profile_id = "";') < ca.find('snprintf(file_name, sizeof(file_name), "/jffs/customized_splash/%s.json", profile_id);'))

# ---------------------------------------------------------------- the old paths are closed
check("old writers gone (handle_upload_icon / del_upload_icon)", "handle_upload_icon(" not in web and "del_upload_icon(" not in web)
ap = web[web.find('else if(!strcmp(name, "custom_usericon") || !strcmp(name, "custom_usericon_del")) {'):][:600]
check("apply: custom_usericon / custom_usericon_del are dropped (logged, never stored, never left to the generic nvram branch)",
      ap.startswith("else if(") and "logmessage(" in ap and "nvram_set" not in ap.split("\n\t\t\t}\n")[0])
for row in ("get_usericon_md5.cgi", "backup_all_usericon.cgi", "upload_all_usericon.cgi"):
    check("closed: no %s row and no handler" % row, '{ "%s' % row not in web)
check("closed: the bulk handlers are gone", "do_get_usericon_md5_cgi" not in web and "do_backup_all_usericon_cgi" not in web and "do_upload_all_usericon" not in web)
check("kept: renew_upload_icon() at httpd start, the get_upload_icon read hook (the stock network page reads it)",
      "renew_upload_icon(void)" in web and "renew_upload_icon();" in rd("httpd", "httpd.c") and '{ "get_upload_icon", ej_get_upload_icon}' in web)
www = os.path.join(SRC, "www")
callers = []
for root, dirs, files in os.walk(www):
    if os.sep + "sysdep" in root:
        continue
    for f in files:
        if f.endswith((".asp", ".js", ".htm", ".html")):
            t = open(os.path.join(root, f), encoding="latin-1").read()
            if re.search(r"get_usericon_md5\.cgi|backup_all_usericon\.cgi|upload_all_usericon\.cgi", t):
                callers.append(os.path.relpath(os.path.join(root, f), www))
check("no shipped page calls the closed addresses", not callers, callers)

# ---------------------------------------------------------------- the C code, compiled and driven on the host
CC = shutil.which("gcc") or shutil.which("cc")
if CC and H and A and os.name == "posix":
    d = tempfile.mkdtemp(prefix="rdic_")
    try:
        open(os.path.join(d, "helpers.inc"), "w").write(H.replace('#define RDIC_DIR\t"/jffs/usericon"', "#define RDIC_DIR\tRDIC_TESTDIR"))
        open(os.path.join(d, "actions.inc"), "w").write(A.replace('statvfs("/jffs", &v)', "statvfs(RDIC_ROOT, &v)"))
        open(os.path.join(d, "harness.c"), "w").write(HARNESS)
        root = os.path.join(d, "root")
        exe = os.path.join(d, "h")
        r = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-O1", '-DRDIC_ROOT="%s"' % root, "-o", exe, os.path.join(d, "harness.c")],
                           capture_output=True, text=True, timeout=120)
        check("the new web.c code compiles with -Wall -Werror (stubs for httpd)", r.returncode == 0, r.stderr[-1500:])
        if r.returncode == 0:
            r = subprocess.run([exe], capture_output=True, text=True, timeout=60)
            bad = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
            check("host run: validator, MAC check, links / FIFOs, caps, POST rule, set_type record format (%d checks)" % r.stdout.count("\n"),
                  r.returncode == 0 and not bad and "0 failing" in r.stdout, bad or r.stdout[-800:] + r.stderr[-400:])
    finally:
        shutil.rmtree(d, ignore_errors=True)
else:
    print("SKIP (part): no C compiler - the host run of the web.c code")

# ---------------------------------------------------------------- the helper, under node
util = rd("www", "reaper_util.js")
mb = re.search(r"/\* REAPER-DEVICON-BEGIN.*?/\* REAPER-DEVICON-END \*/", util, re.S)
blk = mb.group(0) if mb else ""
check("reaper_util.js: one ReaperIcons block", util.count("REAPER-DEVICON-BEGIN") == 1 and "window.ReaperIcons" in blk)
check("helper: the same whitelist as the router, a picture only through img.src, never innerHTML",
      r"var PIC = /^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+\/]+={0,2}$/;" in blk and "c.src = p.u;" in blk and "innerHTML" not in blk)
check("helper: the glyphs come from the shipped stock sheet, read as text (it is never linked into a page)",
      "get('/device-map/device-map.css'" in blk and "<link" not in blk)
HEXRE = re.compile(r"#[0-9a-fA-F]{3,6}\b")
loose = [x for x in HEXRE.findall(re.sub(r"var\(--[a-z0-9-]+,\s*#[0-9a-fA-F]{3,6}\)", "", blk)) if x.upper() not in ("#FFF", "#000")]
rgbs = [x for x in re.findall(r"rgba?\([^)]*\)", blk) if not x.startswith(("rgba(var(--cb-", "rgb(var(--cb-")) and not re.match(r"rgba?\(\s*255\s*,\s*255\s*,\s*255", x)]
check("helper: every colour is a kit token or a palette role (colour-blind mode)", not loose and not rgbs, loose + rgbs)
NODE = shutil.which("node") or shutil.which("nodejs")
if NODE and blk:
    d = tempfile.mkdtemp(prefix="rdicn_")
    try:
        h = os.path.join(d, "h.js")
        open(h, "w").write(NODEJS)
        r = subprocess.run([NODE, h, os.path.join(www, "reaper_util.js")], capture_output=True, text=True, timeout=60)
        o = {}
        try:
            o = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            pass
        check("helper ran under node", bool(o), (r.stdout + r.stderr)[-600:])
        if o:
            check("nothing loaded yet: the generic glyph", o.get("before") == "generic", o.get("before"))
            check("the device's own picture first (any MAC spelling, a lower-case stock file name too)",
                  o.get("custom") == "pic:PNG" and o.get("customDash") == "pic:PNG" and o.get("lowerStem") == "pic:PNG", o)
            check("then a picture set for the device type", o.get("typePic") == "pic:PNG2", o.get("typePic"))
            check("then the type glyph; an unknown or missing type shows the generic (type 0) glyph",
                  o.get("glyph") == "glyph:34" and o.get("unknownType") == "glyph:0" and o.get("noType") == "glyph:0", o)
            check("an SVG answer from the router is not used (the glyph shows)", o.get("svgRefused") == "glyph:34", o.get("svgRefused"))
            check("a glyph that is not a PNG data URL is dropped (stock sheet and the newer-type list alike)",
                  o.get("svgGlyphDropped") == "glyph:0" and o.get("extBad") == "glyph:0", o)
            check("the newer types (78+) are read from extend_custom_icon.json, once, when first shown",
                  o.get("ext1") == "glyph:0" and o.get("ext2") == "glyph:99" and sum(1 for u in o.get("reqs", []) if "extend_custom_icon" in u) == 1, o)
            check("the element: a span holding an img with the picture (class pic), or the glyph class",
                  o.get("elTag") == "SPAN" and o.get("elChild") == "IMG" and o.get("elSrc") is True and "pic" in o.get("elClass", "")
                  and o.get("glyphChild") == "rdic-g t34", o)
            check("placeholder markup: a value that is not a MAC or a type number never reaches the attribute",
                  o.get("html") == '<span class="rdic lg" data-rdic-mac="" data-rdic-type="" aria-hidden="true"></span>'
                  and o.get("htmlOk") == '<span class="rdic sm" data-rdic-mac="aa:bb:cc:dd:ee:ff" data-rdic-type="34" aria-hidden="true"></span>', o)
            check("valid(): png / jpeg / webp yes; svg, gif, javascript:, text/html, upper case, quotes, parameters, padding, oversize, non-strings no",
                  o.get("valid") == [True, True, True] and o.get("invalid") == [False] * 11, (o.get("valid"), o.get("invalid")))
            reqs = o.get("reqs", [])
            check("the router is asked with the page token, the pictures in one batched icon_get",
                  any(u.startswith("/reaper_dev.cgi?action=icon_list&http_id=tok%26x") for u in reqs)
                  and sum(1 for u in reqs if "action=icon_get" in u) == 1, reqs)
    finally:
        shutil.rmtree(d, ignore_errors=True)
else:
    print("SKIP (part): no node - the helper run")

# ---------------------------------------------------------------- the pages
dev = rd("www", "Reaper_Devices.asp")
check("Devices: the icon in the name cell opens the picture + type dialog; the rows are filled by the helper",
      "ReaperIcons.html(d.mac, ReaperNames.type(d.mac), 'sm')" in dev and "ReaperIcons.fill(document.getElementById('rows'));" in dev
      and "n.onclick = function(){ picOpen(+n.getAttribute('data-dic')); };" in dev and "ReaperIcons.init(REAPER_HTTPID);" in dev)
check("Devices: set_icon / set_type / del_icon are POSTs with the token in the body",
      "x.open('POST', '/reaper_dev.cgi', true);" in dev and "xPost('set_icon', {mac: mac, icon: du}" in dev
      and "xPost('set_type', {mac: mac, type: t}" in dev and "xPost('del_icon', {mac: mac}" in dev and "action=set_icon" not in dev)
check("Devices: the picture is shrunk to 64 x 64 in a canvas and checked before it is sent; no SVG offered",
      "c.width = c.height = 64;" in dev and "c.toDataURL('image/png')" in dev and "if(!ReaperIcons.valid(du))" in dev
      and 'accept="image/png,image/jpeg,image/webp,image/gif,image/bmp"' in dev and "image/svg" not in dev.lower())
check("Devices: ?mac= opens that device's dialog", "/[?&]mac=([0-9A-Fa-f:%]{12,40})/" in dev and "if(di >= 0) picOpen(di);" in dev)
cf = rd("www", "client_function.js")
stock = []
i0 = cf.find("var custom_icon_list_api = {")
i1 = cf.find('"db":', i0) if i0 >= 0 else -1
if i1 >= 0:
    s0 = cf.find("{", i1); depth = 0
    for j in range(s0, len(cf)):
        if cf[j] == "{": depth += 1
        elif cf[j] == "}":
            depth -= 1
            if not depth:
                try:
                    stock = [it["num"] for c in json.loads(cf[s0:j + 1]).values() for it in c["list"]]
                except Exception:
                    stock = []
                break
mine = [int(x) for x in re.findall(r"\[(\d+),(?:`<#[A-Za-z0-9_]+#>`|'[^']*')\]", dev[dev.find("var DTYPES"):dev.find("var CUSTOM_RAW")])]
check("Devices: the type list is the stock picker's, in its order (%d types)" % len(stock), len(stock) >= 60 and mine == stock,
      ([x for x in stock if x not in mine], [x for x in mine if x not in stock]))
am = rd("www", "Reaper_AiMesh.asp")
check("AiMesh: client rows show the device icon (read only); a click opens that device on the Devices page",
      "ic.appendChild(ReaperIcons.icon(c.mac, {type: c.type, size: 'sm'}));" in am and "ic.addEventListener('click', function(){ openDevice(c.mac); });" in am
      and "'/reaper_shell.asp#Reaper_Devices.asp?mac=' + encodeURIComponent(mac)" in am and "ReaperIcons.init(HTTPID);" in am)
check("AiMesh: no product photo (the member glyph is the stock router / repeater type glyph)",
      "ReaperIcons.icon('', {type: n.mac === CAP ? 2 : 24})" in am and not re.search(r"\.(png|jpg|jpeg|webp)\b", am))
dash = rd("www", "Main_ReaperDash.asp")
check("Dashboard: the client list carries the icons", "ReaperIcons.html(list[i].m,ReaperNames.type(list[i].m),'sm')" in dash and "ReaperIcons.fill(box);" in dash
      and "ReaperIcons.init(HTTPID);" in dash)
dm = rd("www", "device-map", "device-map.css") if os.path.isfile(os.path.join(www, "device-map", "device-map.css")) else ""
mk = rd("www", "Makefile")
check("the stock glyph sheet still ships with its type rules", len(re.findall(r"i\.type\d+", dm)) >= 60
      and not re.search(r"^\s*rm -[rf]+ \$\(INSTALLDIR\)/www/device-map(/device-map\.css)?\s*$", mk, re.M))
nonascii = [f for f, t in (("Reaper_Devices.asp", dev), ("Reaper_AiMesh.asp", am), ("reaper_util.js", util), ("Main_ReaperDash.asp", dash)) if any(ord(c) > 127 for c in t)]
check("the pages and the helper are plain ASCII", not nonascii, nonascii)

print("\n%d failing" % len(fails))
for f in fails:
    print("  - " + f)
sys.exit(1 if fails else 0)
