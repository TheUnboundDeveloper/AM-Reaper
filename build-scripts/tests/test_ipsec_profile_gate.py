#!/usr/bin/env python3
"""test_ipsec_profile_gate.py - what rc accepts from a saved IPsec profile, from the Instant Guard client lists
and from the WAN address the IPsec server certificate is made for (2026-11-10).

WHY. rc/rc_ipsec.c parses the '>'-separated settings ipsec_profile_N / ipsec_profile_client_N (and their _ext
companions) into a table and prints the fields into /tmp/etc/ipsec.conf, ipsec.secrets, strongswan.conf and
quicksecpm.xml, most of them unquoted. strongSwan reads those files with lexers for which a space ends a token,
'=' is a token of its own and the word "include" followed by a space opens another file. Nothing in rc checked
the fields:
  * a line break in a saved value added a config line; "x include /tmp/mnt/sda1/y.conf" in an unquoted field
    loaded a file that can name a root command (leftupdown=); an unquoted certificate DN made the whole
    ipsec.conf fail to load; a '"' inside a quoted secret cut the secret short;
  * the parser walked off the end of a value that had fewer separators than it consumes, and wrote there;
  * an Instant Guard client whose name fails the name rule got no conn of its own but still got a credential,
    so it logged in on the parent conn with full LAN access;
  * get_virtual_subnet() (rc) and get_vpns_iprange_by_vpns_idx() (shared/mtlan_utils.c) read one field of the
    RAW saved value, past the table, into the filter / nat tables and a root shell script;
  * rc_ipsec_gen_cert() called the input check with its two arguments swapped, so it never ran;
  * the 3006.102.8 copy of the file lacked hardening the main line has.
The page writes fixed templates, but httpd's profile import and any authenticated apply can save anything.

WHAT IT DOES.
  1. Source pins on the real rc/rc_ipsec.c, rc/rc_ipsec.h and shared/mtlan_utils.c.
  2. Compiles the real source on the host - one slice of rc_ipsec.c from the top-of-file tables to the end of
     pre_ipsec_prof_set() (parser, sanitizers, gate), plus ipsec_wan_addr_ok(), get_virtual_subnet(),
     rc_ipsec_secrets_set() and shared's get_vpns_iprange_by_vpns_idx() - with stand-in nvram / log functions,
     under AddressSanitizer + UBSan when the host has them (bounded: one process, a time limit, an output cap),
     and runs:
       A. the gate over a table of accepted and refused values, field by field and rule by rule;
       B. the real parser on the page's two templates, on the site-to-site export / import form, and on bad
          saved values (slot cleared, one log line that names profile and field and never the value);
       C. the WAN address check and get_virtual_subnet();
       D. the secrets file: an Instant Guard client with a refused name gets no line;
       E. get_vpns_iprange_by_vpns_idx();
       F. short and malformed values straight into the parser on exact-size heap copies: it must stay inside.

Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router source tree - pass the tree's release/src/router as
argv[1] or REAPER_ROUTER_SRC).
"""
import os, platform, re, shutil, subprocess, sys, tempfile, threading

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isdir(SRC):
    skip("no router source tree (pass release/src/router as argv[1] or REAPER_ROUTER_SRC)")
C_PATH = os.path.join(SRC, "rc", "rc_ipsec.c")
H_PATH = os.path.join(SRC, "rc", "rc_ipsec.h")
M_PATH = os.path.join(SRC, "shared", "mtlan_utils.c")
for p in (C_PATH, H_PATH, M_PATH):
    if not os.path.isfile(p):
        skip("missing %s" % p)

def read(p):
    with open(p, encoding="utf-8", errors="surrogateescape") as f:
        return f.read()

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond or detail == "" else " - " + str(detail)[:300]))
    if not cond:
        fails.append(name)

def strip_comments(s):
    """the C source without comments (string and character literals kept as they are)"""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '"' or c == "'":
            j = i + 1
            while j < n and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            out.append(s[i:j + 1]); i = j + 1
        elif s.startswith("/*", i):
            j = s.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("\n" * s.count("\n", i, j)); i = j
        elif s.startswith("//", i):
            j = s.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(c); i += 1
    return "".join(out)

def extract(src, signature):
    """the whole function whose body opens after `signature` ('' when it is not there)"""
    i = src.find(signature)
    if i < 0:
        return ""
    j = src.find("{", i)
    depth, k, n = 0, j, len(src)
    while 0 <= k < n:
        c = src[k]
        if src.startswith("/*", k):
            k = src.find("*/", k + 2)
            k = n if k < 0 else k + 1
        elif src.startswith("//", k):
            k = src.find("\n", k)
            k = n if k < 0 else k
        elif c == '"' or c == "'":
            k += 1
            while k < n and src[k] != c:
                k += 2 if src[k] == "\\" else 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1
    return ""

def in_order(text, *needles):
    pos = -1
    for nd in needles:
        p = text.find(nd, pos + 1)
        if p < 0:
            return False
        pos = p
    return True

raw = read(C_PATH)
hdr = read(H_PATH)
mraw = read(M_PATH)
code = strip_comments(raw)
mcode = strip_comments(mraw)

# what each string field of a profile takes, beyond "no control character" (the specification; the source is
# pinned against it below and the compiled gate is run against it)
SPEC = {
    "remote_gateway": "IPSEC_F_HOST",
    "local_id": "IPSEC_F_ID", "remote_id": "IPSEC_F_ID",
    "local_subnet": "IPSEC_F_TOKEN", "remote_subnet": "IPSEC_F_TOKEN", "virtual_subnet": "IPSEC_F_TOKEN",
    "tun_type": "IPSEC_F_TOKEN", "rightauth2_method": "IPSEC_F_TOKEN", "leftauth_method": "IPSEC_F_TOKEN",
    "leftcert": "IPSEC_F_TOKEN", "leftsendcert": "IPSEC_F_TOKEN", "eap_identity": "IPSEC_F_TOKEN",
    "auth_method_key": "IPSEC_F_SECRET", "xauth_password": "IPSEC_F_SECRET", "leftkey": "IPSEC_F_SECRET",
    "samba_settings": "IPSEC_F_ADDRS",
}
CLASS = {"0": 0, "IPSEC_F_ID": 1, "IPSEC_F_HOST": 2, "IPSEC_F_TOKEN": 3, "IPSEC_F_SECRET": 4, "IPSEC_F_ADDRS": 5}

# ------------------------------------------------------------------------------------------------ 1. pins
print("1. source pins (%s)" % C_PATH)
m = re.search(r"typedef struct ipsec_prof_s\{(.*?)\}ipsec_prof_t;", strip_comments(hdr), re.S)
STR_FIELDS = re.findall(r"\bchar\s+(\w+)\s*\[", m.group(1)) if m else []
check("header: ipsec_prof_t found, with its string members (%d)" % len(STR_FIELDS), len(STR_FIELDS) >= 22, STR_FIELDS)
check("every field the specification names is a member", all(f in STR_FIELDS for f in SPEC), [f for f in SPEC if f not in STR_FIELDS])

B0, B1 = raw.find("/* reaper ipsec-profile-gate: begin"), raw.find("/* reaper ipsec-profile-gate: end */")
gate = raw[B0:B1] if 0 <= B0 < B1 else ""
gate_code = strip_comments(gate)
check("the gate block is in rc_ipsec.c (reaper ipsec-profile-gate: begin / end)", gate != "")
check("gate: every string member of ipsec_prof_t has a row, with the rule the specification gives it",
      all('{ "%s", p->%s, %s },' % (f, f, SPEC.get(f, "0")) in gate_code for f in STR_FIELDS),
      [f for f in STR_FIELDS if '{ "%s", p->%s, %s },' % (f, f, SPEC.get(f, "0")) not in gate_code])
fok = extract(gate_code, "static int ipsec_profile_fields_ok(const ipsec_prof_t *p, const char **bad, int *why)\n{")
check("gate: per field - control characters, include, the ID / host allowlist, token, quoted secret, address list",
      in_order(fok, "if(ipsec_str_has_ctl(v))", "else if(!(fl & IPSEC_F_SECRET) && ipsec_str_has_include(v))",
               "else if((fl & (IPSEC_F_ID | IPSEC_F_HOST)) && !ipsec_id_chars_ok(v, fl & IPSEC_F_HOST))",
               'else if((fl & IPSEC_F_TOKEN) && strpbrk(v, " \\t=") != NULL)',
               "else if((fl & IPSEC_F_SECRET) && strchr(v, '\"') != NULL)",
               "else if((fl & IPSEC_F_ADDRS) && !ipsec_addr_list_ok(v))"))
check("gate: control characters are < 0x20 and 0x7f", "*p < 0x20 || *p == 0x7f" in gate_code)
gap = extract(gate_code, "static void ipsec_profile_gate_apply(ipsec_prof_t *slot, int is_svr, int idx, int why, const char *bad)\n{")
check("gate: a refused slot is cleared, and the one log line names profile and reason",
      "memset(slot, 0, sizeof(*slot));" in gap
      and 'logmessage("ipsec", "%s profile %d skipped: malformed saved value", who, idx);' in gap
      and 'logmessage("ipsec", "%s profile %d skipped: include directive in %s", who, idx, bad);' in gap
      and 'logmessage("ipsec", "%s profile %d skipped: unsafe character in %s", who, idx, bad);' in gap
      and gate_code.count("logmessage(") == 3)
check("gate: never writes a setting", "nvram_set" not in gate_code and "nvram_unset" not in gate_code)

pre = extract(code, "int pre_ipsec_prof_set()\n{")
check("pre_ipsec_prof_set(): both raw values (control characters, then shape), then parse, then fields, then clear-or-keep",
      in_order(pre, "if(ipsec_str_has_ctl(p_tmp) || ipsec_str_has_ctl(p_tmp_ext)){",
               "else if(!ipsec_profile_shape_ok(p_tmp) || !ipsec_profile_ext_shape_ok(p_tmp_ext)){",
               "ipsec_prof_fill(i-1, p_tmp,prof_count);", "ipsec_prof_fill_ext(i-1, p_tmp_ext,prof_count);",
               "ipsec_profile_fields_ok(&prof[prof_count][i-1], &gate_bad, &gate_why);",
               "ipsec_profile_gate_apply(&prof[prof_count][i-1], PROF_SVR == prof_count, i, gate_why, gate_bad);", "rc = 1;"))
check("pre_ipsec_prof_set(): never writes a setting", pre != "" and "nvram_set" not in pre)
check("ipsec_prof_fill() and ipsec_prof_fill_ext() have one caller each, pre_ipsec_prof_set()",
      code.count("ipsec_prof_fill(") == 2 and pre.count("ipsec_prof_fill(") == 1
      and code.count("ipsec_prof_fill_ext(") == 2 and pre.count("ipsec_prof_fill_ext(") == 1,
      (code.count("ipsec_prof_fill("), code.count("ipsec_prof_fill_ext(")))
ipar = extract(code, "int ipsec_profile_int_parse(int ike_esp_type, char *p_end, int *nsize_shifft)\n{")
spar = extract(code, "void ipsec_profile_str_parse(char *p_end, char *p_tmp, ")
fill = extract(code, "void ipsec_prof_fill(int prof_idx, char *p_data, ipsec_prof_type_t prof_type)\n{")
check("parser: both helpers stop at the end of the value and keep the caller on its terminator",
      "while(*p_end++ != '>')" not in code
      and in_order(ipar, "while(*p_end != '\\0' && *p_end != '>'){ p_end++; i++; }", "if('\\0' == *p_end){", "*nsize_shifft = i - 1;")
      and in_order(spar, "while(*p_end != '\\0' && *p_end != '>'){", "if('\\0' == *p_end){", "*nsize_shifft = i - 1;", "return;", "*p_end = '\\0';"))
check("parser: the two one-character steps never pass the terminator",
      fill.count("if('\\0' != *p_end) p_end += 1;") == 2 and "\n    p_end += 1;" not in fill)
conv = extract(code, "void rc_ipsec_nvram_convert_check(void)\n{")
check("nvram_convert_check: the rewrite of a malformed ext value is bounded",
      "snprintf(tmpStr, sizeof(tmpStr), " in conv and " sprintf(tmpStr" not in conv.replace("\t", " "))
conf = extract(code, "void rc_ipsec_conf_set()\n{")
check("rc_ipsec_conf_set(): parses (and gates) before ipsec.conf is written",
      in_order(conf, "pre_ipsec_prof_set();", "rc_ipsec_topology_set();"))
rset = extract(code, "void rc_ipsec_set(ipsec_conn_status_t conn_status, ipsec_prof_type_t prof_type)\n{")
check("rc_ipsec_set(): the parse comes before every writer",
      in_order(rset, "rc_ipsec_conf_set();", "rc_ipsec_secrets_set();", "rc_strongswan_conf_set();",
               "rc_ipsec_topology_set_XML();", "_ipsec_export();"))
check("the writers have no other caller",
      code.count("rc_ipsec_topology_set();") == 2 and code.count("rc_ipsec_secrets_set();") == 1
      and code.count("rc_ipsec_topology_set_XML();") == 1 and code.count("rc_strongswan_conf_set();") == 1,
      [code.count(x) for x in ("rc_ipsec_topology_set();", "rc_ipsec_secrets_set();", "rc_ipsec_topology_set_XML();", "rc_strongswan_conf_set();")])
s2s = extract(code, "void update_ipsec_s2sc_conf()\n{")
check("update_ipsec_s2sc_conf(): the export also parses (and gates) first", in_order(s2s, "pre_ipsec_prof_set();", "_ipsec_export();"))
DOWN = "IPSEC_CONN_EN_DOWN != prof[prof_count][i].ipsec_conn_en"
sec = extract(code, "void rc_ipsec_secrets_set()\n{")
topo = extract(code, "void rc_ipsec_topology_set()\n{")
check("a cleared slot is one every writer skips (IPSEC_CONN_EN_DOWN = 0, empty name, vpn_type 0)",
      re.search(r"IPSEC_CONN_EN_DOWN\s*=\s*0\s*,", hdr) is not None and re.search(r"VPN_TYPE_NET_NET_SVR\s*=\s*1\s*,", hdr) is not None
      and DOWN in sec and DOWN in topo
      and extract(code, "void rc_ipsec_topology_set_XML()\n{").count(DOWN) == 3
      and "IPSEC_CONN_EN_UP == prof[PROF_SVR][i].ipsec_conn_en" in extract(code, "int pre_ipsec_samba_prof_set()\n{")
      and "if(0 != strlen(prof[prof_count][i].profilename)) {" in rset
      and "if (prof[PROF_SVR][i].vpn_type == VPN_TYPE_NET_NET_SVR) {" in extract(code, "static void _ipsec_export()\n{"))

IGNAME = "is_valid_ig_client_name" if "is_valid_ig_client_name(" in code else "ipsec_ig_client_name_ok"
check("ipsec.secrets: an Instant Guard client or guest whose name fails the name rule gets no credential",
      in_order(sec, "foreach_60(word, ig_client_list, word_next){", "&active)) != 5)", "if(!%s(name)){" % IGNAME,
               'logmessage("ipsec", "Instant Guard client %d skipped: unsafe name", ig_n);', "continue;", "snprintf(ig_client_buf,",
               "foreach_60(word, ig_guest_client_list, word_next){", "&lan_access)) != 6)", "if(!%s(name)){" % IGNAME,
               'logmessage("ipsec", "Instant Guard guest %d skipped: unsafe name", ig_n);', "continue;", "snprintf(ig_client_buf,")
      and sec.count("if(!%s(name)){" % IGNAME) == 2)
check("ipsec.conf: an Instant Guard guest name is checked before it becomes a conn name",
      in_order(topo, "!= 6)", "if(!%s(name))" % IGNAME, "continue;", 'fprintf(fp,"\\nconn %s_%s\\n"'))

gen = extract(code, "void rc_ipsec_gen_cert(int skip_checking)\n{")
check("gen_cert: the swapped validator call is gone", "validate_apply_input_value(remote_id, prefix)" not in code)
check("gen_cert: a stock validator call, where kept, has (name, value)",
      code.count("validate_apply_input_value(") == code.count("validate_apply_input_value(prefix, remote_id)"))
check("gen_cert: the WAN address is checked locally before the script is written",
      in_order(gen, 'snprintf(remote_id, sizeof(remote_id), "%s", nvram_safe_get(prefix));', "!ipsec_wan_addr_ok(remote_id)",
               "ipsec_token_is_strict(remote_id)", "ipsec_script_new("))
check("gen_cert: the refusal is logged, without the address",
      re.search(r'ipsec_wan_addr_ok\(remote_id\)[^{]*\{\s*DBG\(\(.*?\)\);\s*logmessage\("ipsec", "[^"%]*"\);\s*return;', gen, re.S) is not None)
check("gen_cert: the DDNS host name is used only when it is a valid domain name",
      in_order(gen, 'nvram_match("ddns_enable_x", "1")', 'nvram_safe_get("ddns_hostname_x");', "if (is_valid_domainname(s))",
               'snprintf(ddns_name, sizeof(ddns_name), "%s", s);')
      and 'snprintf(ddns_name, sizeof(ddns_name), "%s", nvram_safe_get("ddns_hostname_x"));' not in code)
wanok = extract(code, "static int ipsec_wan_addr_ok(const char *s)\n{")
check("ipsec_wan_addr_ok(): inet_pton(AF_INET) == 1 and not 0.0.0.0",
      "inet_pton(AF_INET, s, &a) == 1" in wanok and "a.s_addr != 0" in wanok)

gvs = extract(code, "char *get_virtual_subnet(char *nvram_name, char *output, int _size)\n{")
check("get_virtual_subnet(): the raw field must be three dotted octets, else it counts as unset",
      in_order(gvs, "get_string_in_62(ipsec_profile, 14, virtual_subnet, sizeof(virtual_subnet));",
               "if(!ipsec_subnet3_ok(virtual_subnet))", "virtual_subnet[0] = '\\0';", "if(strlen(virtual_subnet) == 0)", "snprintf(output, _size,"))
gvr = extract(mcode, "char* get_vpns_iprange_by_vpns_idx(int vpns_idx, char* buf, size_t len)\n{")
check("shared get_vpns_iprange_by_vpns_idx(): the raw field must be three dotted octets, else no range",
      in_order(gvr, "*p_end = '\\0';", "if (!vpns_subnet3_ok(p+1))", "continue;", 'snprintf(buf, len, "%s.1-%s.254", p+1, p+1);')
      and extract(mcode, "static int vpns_subnet3_ok(const char *s)\n{") != "")
check("shared/mtlan_utils.c still includes its own header only", re.findall(r"^#include\s+(\S+)", mcode, re.M) == ['"mtlan_utils.h"'],
      re.findall(r"^#include\s+(\S+)", mcode, re.M))
check("parser: local_subnet and virtual_subnet are cut to the subnet character set (both lines)",
      # 2026-11-10: the local subnet keeps IPv6 (hex and ':'), the virtual one stays IPv4
      fill.count("ipsec_subnet_sanitize(p_tmp);") == 1 and fill.count("ipsec_subnet_sanitize46(p_tmp);") == 1
      and "|| *p == ':' || *p == '.' || *p == '/' || *p == ','" in extract(code, "static void ipsec_subnet_sanitize46(char *subnet)\n{")
      and "!((*p >= '0' && *p <= '9') || *p == '.' || *p == '/' || *p == ',')" in extract(code, "static void ipsec_subnet_sanitize(char *subnet)\n{"))
check("parser: the profile name is reduced to a shell-safe token",
      "ipsec_profilename_sanitize(p_tmp);" in fill or "ipsec_strict_token(p_tmp);" in fill)
check("ipsec.conf: the raw-profile comment is a bounded copy, cut at CR/LF",
      in_order(topo, "strlcpy(s_tmp, nvram_safe_get(&buf[0]), SZ_BUF);", "ipsec_comment_sanitize(s_tmp);", "#Host-to-NET[prof#%d]:%s"))
check("no strcpy() is left in the file, and the interface name buffer is IFNAMSIZ",
      "strcpy(" not in code and "char interface[IFNAMSIZ];" in rset and "char interface[4];" not in code)

# ------------------------------------------------------------------------------------------------ 2. compiled
print("2. the real parser, gate and writers, compiled on the host")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    if fails:
        print("\n%d FAILED: %s" % (len(fails), "; ".join(fails))); sys.exit(1)
    skip("no host C compiler (the source pins passed)")

S0 = raw.find("char ikev[IKE_TYPE_MAX_NUM][SZ_MIN] = {")
pre_raw = extract(raw, "int pre_ipsec_prof_set()\n{")
S1 = raw.find(pre_raw) + len(pre_raw) if pre_raw else -1
slice_ok = 0 <= S0 < B0 < B1 < S1
check("the slice (tables .. pre_ipsec_prof_set) holds the gate block", slice_ok)
extra = [extract(raw, "static void ipsec_strict_token(char *s)\n{"),
         extract(raw, "static int ipsec_wan_addr_ok(const char *s)\n{"),
         extract(raw, "char *get_virtual_subnet(char *nvram_name, char *output, int _size)\n{"),
         extract(raw, "void rc_ipsec_secrets_set()\n{"),
         extract(mraw, "static int vpns_subnet3_ok(const char *s)\n{"),
         extract(mraw, "char* get_vpns_iprange_by_vpns_idx(int vpns_idx, char* buf, size_t len)\n{")]
check("ipsec_strict_token(), ipsec_wan_addr_ok(), get_virtual_subnet(), rc_ipsec_secrets_set(), vpns_subnet3_ok() and "
      "get_vpns_iprange_by_vpns_idx() are in the source", all(extra), [bool(x) for x in extra])
if not slice_ok or not all(extra) or not STR_FIELDS:
    print("\n%d FAILED: %s" % (len(fails), "; ".join(fails))); sys.exit(1)

# the shared helpers the compiled code calls: the tree's own text where the tree has it, else an equivalent
def shared(name):
    p = os.path.join(SRC, "shared", name)
    return read(p) if os.path.isfile(p) else ""
misc_c, shu_c, shu_h = shared("misc.c"), shared("shutils.c"), shared("shutils.h")
g62 = extract(misc_c, "get_string_in_62(char *in_list, int idx, char *out, int out_len)\n{")
g62 = ("static int " + g62) if g62 else r'''
static int get_string_in_62(char *in_list, int idx, char *out, int out_len)
{
	int n = 0; const char *g = in_list, *p;
	while ((p = strchr(g, '>')) != NULL && n < idx) { g = p + 1; n++; }
	if (n == idx) { size_t l = p ? (size_t)(p - g) : strlen(g); if (l > (size_t)out_len - 1) l = out_len - 1; memcpy(out, g, l); out[l] = 0; }
	return 0;
}
'''
vss = extract(shu_c, "int _vstrsep(char *buf, const char *sep, ...)\n{")
vss = ("static " + vss) if vss else r'''
static int _vstrsep(char *buf, const char *sep, ...)
{
	va_list ap; char **p; int n = 0;
	va_start(ap, sep);
	while ((p = va_arg(ap, char **)) != NULL) { if ((*p = strsep(&buf, sep)) == NULL) break; ++n; }
	va_end(ap);
	return n;
}
'''
m60 = re.search(r"#define foreach_60\(word, wordlist, next\) \\\n(?:.*\\\n)*.*\n", shu_h)
f60 = m60.group(0) if m60 else r'''
#define foreach_60(word, wordlist, next) \
		for (next = &wordlist[strspn(wordlist, "<")], strncpy(word, next, sizeof(word)), word[sizeof(word) - 1] = '\0', \
				word[strcspn(word, "<")] = '\0', next = strchr(next, '<'); strlen(word); \
				next = next ? &next[strspn(next, "<")] : "", strncpy(word, next, sizeof(word)), word[sizeof(word) - 1] = '\0', \
				word[strcspn(word, "<")] = '\0', next = strchr(next, '<'))
'''
igs = ""
if IGNAME == "is_valid_ig_client_name":
    igs = extract(misc_c, "int is_valid_ig_client_name(const char *name)\n{")
    check("the shared Instant Guard name rule is in shared/misc.c (the rc source calls it)", igs != "")
    igs = "static " + igs if igs else ""

FIELDS = "\n".join('\t{ "%s", offsetof(ipsec_prof_t, %s), sizeof(((ipsec_prof_t *)0)->%s), %d },'
                   % (f, f, f, CLASS[SPEC.get(f, "0")]) for f in STR_FIELDS)

HARNESS = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <stddef.h>
#include <ctype.h>
#include <arpa/inet.h>
#include <net/if.h>
#include "rc_ipsec.h"

#define DBG(args) do { } while (0)
#define RTCONFIG_INSTANT_GUARD 1
#define WAN_UNIT_FIRST 0
#define WAN_UNIT_MAX 2
#define VPN_PROTO_IPSEC_STR "IPSec"
#define wan_prefix(unit, prefix)	snprintf(prefix, sizeof(prefix), "wan%d_", unit)

/* ---- stand-ins for what the real code calls outside itself ---- */
static size_t t_strlcpy(char *d, const char *s, size_t n)
{
	size_t l = strlen(s);
	if (n) { size_t c = l >= n ? n - 1 : l; memcpy(d, s, c); d[c] = 0; }
	return l;
}
static size_t t_strlcat(char *d, const char *s, size_t n)
{
	size_t dl = strnlen(d, n);
	if (dl == n) return n + strlen(s);
	return dl + t_strlcpy(d + dl, s, n - dl);
}
#define strlcpy t_strlcpy
#define strlcat t_strlcat
static int safe_atoi(const char *s) { return s ? atoi(s) : 0; }
static int wan_primary_ifunit(void) { return 0; }
static int dualwan_unit__usbif(int unit) { (void)unit; return 0; }
static char *strcat_r(const char *a, const char *b, char *buf) { strcpy(buf, a); strcat(buf, b); return buf; }

static struct { char k[40]; char v[1024]; } g_nv[24];
static int g_nnv;
static void nv_clear(void) { g_nnv = 0; }
static void nv_set(const char *k, const char *v)
{
	int i;
	for (i = 0; i < g_nnv; i++) if (!strcmp(g_nv[i].k, k)) break;
	if (i == g_nnv) g_nnv++;
	snprintf(g_nv[i].k, sizeof(g_nv[i].k), "%s", k);
	snprintf(g_nv[i].v, sizeof(g_nv[i].v), "%s", v);
}
static char *nvram_safe_get(const char *k)
{
	int i;
	for (i = 0; i < g_nnv; i++) if (!strcmp(g_nv[i].k, k)) return g_nv[i].v;
	return (char *)"";
}
static char *nvram_safe_get_r(const char *k, char *buf, size_t len) { snprintf(buf, len, "%s", nvram_safe_get(k)); return buf; }
static int nvram_get_int(const char *k) { return atoi(nvram_safe_get(k)); }
static int nvram_match(const char *k, const char *v) { return strcmp(nvram_safe_get(k), v) == 0; }
static int g_sets;
static int nvram_set(const char *k, const char *v) { (void)k; (void)v; g_sets++; return 0; }

static char g_log[4096];
static int g_logs;
static void log_clear(void) { g_log[0] = 0; g_logs = 0; }
static void logmessage(const char *tag, const char *fmt, ...)
{
	va_list ap;
	size_t l = strlen(g_log);
	(void)tag;
	va_start(ap, fmt);
	vsnprintf(g_log + l, sizeof(g_log) - l, fmt, ap);
	va_end(ap);
	l = strlen(g_log);
	if (l < sizeof(g_log) - 1) { g_log[l] = '\n'; g_log[l + 1] = 0; }
	g_logs++;
}

static const char *g_out;	/* where the writers' files go */
static FILE *t_fopen(const char *path, const char *mode) { (void)path; return fopen(g_out, mode); }

__G62__
__VSS__
#define vstrsep(buf, sep, args...) _vstrsep(buf, sep, args, NULL)
__F60__
__IGS__

/* ---- the real source: rc_ipsec.c tables .. pre_ipsec_prof_set(), then single functions ---- */
__SLICE__

#define fopen(p, m) t_fopen((p), (m))
__EXTRA__
#undef fopen

/* ---- the test ---- */
enum { C_ANY = 0, C_ID, C_HOST, C_TOKEN, C_SECRET, C_ADDRS };
static const struct { const char *name; size_t off; size_t sz; int cls; } F[] = {
__FIELDS__
};
#define NF ((int)(sizeof(F) / sizeof(F[0])))

static int g_fail, g_n;
static void ck(int cond, const char *fmt, ...)
{
	va_list ap;
	g_n++;
	if (cond) return;
	g_fail++;
	printf("FAIL ");
	va_start(ap, fmt); vprintf(fmt, ap); va_end(ap);
	printf("\n");
}
static const char *show(const char *v)	/* a value, printable */
{
	static char d[4][600];
	static int k;
	char *o = d[k = (k + 1) & 3];
	size_t i, n = 0;
	for (i = 0; v[i] && n + 5 < sizeof(d[0]); i++) {
		unsigned char c = (unsigned char)v[i];
		if (c < 0x20 || c >= 0x7f) n += snprintf(o + n, sizeof(d[0]) - n, "\\x%02x", c); else o[n++] = (char)c;
	}
	o[n] = 0;
	return o;
}

static ipsec_prof_t P;
/* one field set, the gate asked: 1 accepted. *bad and *why as the gate left them. A value that does not fit the
 * field is not tried (returns -1). */
static int put(int fi, const char *v, size_t n, const char **bad, int *why)
{
	if (n > F[fi].sz - 1) return -1;
	memset(&P, 0, sizeof(P));
	memcpy((char *)&P + F[fi].off, v, n);
	*bad = NULL; *why = IPSEC_GATE_OK;
	return ipsec_profile_fields_ok(&P, bad, why);
}
static void want(int fi, const char *v, int ok, int w)
{
	const char *bad; int why, r = put(fi, v, strlen(v), &bad, &why);
	if (r < 0) return;
	if (ok)
		ck(r == 1 && bad == NULL && why == IPSEC_GATE_OK, "A: %s = \"%s\" must be accepted (bad=%s why=%d)", F[fi].name, show(v), bad ? bad : "-", why);
	else
		ck(r == 0 && bad && !strcmp(bad, F[fi].name) && why == w, "A: %s = \"%s\" must be refused with reason %d naming the field (r=%d bad=%s why=%d)",
		   F[fi].name, show(v), w, r, bad ? bad : "-", why);
}

static const char CTL[] = { 0x01, 0x08, '\t', '\n', 0x0b, '\r', 0x1b, 0x1f, 0x7f };

static void part_a(void)
{
	/* what every field takes, whatever its rule */
	static const char *const common[] = { "", "null", "abc", "vpn.example.com", "192.0.2.1", "2001:db8::1", "10.10.10",
		"include", "myinclude", "include.example.com", "preinclude" };
	/* the lexers' keyword: refused in every field but the quoted secrets */
	static const char *const incl[] = { "include /tmp/a", "x include /tmp/a", "1.2.3.4 include /tmp/mnt/x.conf",
		"a include  b" };
	static const char *const id_ok[] = { "%any", "@#0a0b0c", "@#0A0B0c1f", "@#0", "user@example.com", "@example.com", "@vpn.example.com",
		"a+b_c-d%e.f:g", "ID-MODEL", "RT-BE96U_1", "fe80::1", "::1", "0.0.0.0" };
	static const char *const id_no[] = { "C=US, O=Example, CN=vpn", "C=US,O=Example,CN=vpn", "CN=vpn", "a b", "a\"b", "a#b", "a<b", "a>b",
		"a&b", "a\\b", "a,b", "a=b", "@#", "@#zz", "@#0a0g", "@#0a 0b", "a/b", "[2001:db8::1]", "a;b", "a'b", "caf\xc3\xa9", "a*b",
		"$(x)", "`x`", "a|b", "a(b)", "a{b}", "a!b", "a~b", "a?b", " a", "a " };
	static const char *const host_ok[] = { "%any", "user@example.com", "10.0.0.0/8", "2001:db8::/64", "2001:db8::1/64", "vpn-1.example.com" };
	static const char *const host_no[] = { "@#0a0b0c", "a b", "host name", "a\"b", "a#b", "a<b", "a>b", "a&b", "a\\b", "a,b", "a=b", "a;b", "$(x)",
		"`x`", "[::1]", " a", "a " };
	static const char *const tok_ok[] = { "svrCert.pem", "eap-mschapv2", "192.168.1.0/24,10.0.0.0/8", "%identity", "always", "tunnel", "pubkey",
		"a\"b", "a#b", "a<b", "a&b", "a,b;c", "C:\\x" };
	static const char *const tok_no[] = { "a b", "my cert.pem", " lead", "trail ", "a=b", "=", "x =y" };
	static const char *const sec_ok[] = { "pass word with spaces", "please include me", "include /tmp/a", "a=b#c<d>e&f'g\\h", "12345678",
		" lead and trail ", "caf\xc3\xa9" };
	static const char *const sec_no[] = { "a\"bcdefgh", "\"", "abc\"", "\"abc", "a\" : PSK \"b" };
	static const char *const adr_ok[] = { ">1.1.1.1>8.8.8.8>>", ">>>>", ">2001:db8::1>", ">192.168.1.1>192.168.1.2>192.168.1.3>192.168.1.4" };
	static const char *const adr_no[] = { "1}", "{", "a b", "a=b", "a#b", ">1.1.1.1}", "a\"b", "a,b", "a;b", "a/b", "a-b", "a<b", "$(x)", "a\\b" };
	static const char *const any_ok[] = { "a b", "a=b", "a\"b", "a#b", "a<b", "a>b", "a&b", "C=US, O=Example, CN=vpn", " ~", "\x80\xff", "$(x);`y`|z" };
	char buf[160], long_v[128];
	const char *bad;
	int fi, i, pos, why, r;
	size_t k;

#define EACH(tab, ok, w) for (k = 0; k < sizeof(tab) / sizeof(tab[0]); k++) want(fi, tab[k], ok, w)
	memset(&P, 0, sizeof(P));
	bad = "x"; why = 77;
	ck(ipsec_profile_fields_ok(&P, &bad, &why) == 1 && !strcmp(bad, "x") && why == 77, "A: an empty profile is accepted, *bad and *why left alone");
	ck(ipsec_str_has_ctl(NULL) == 0 && ipsec_str_has_include(NULL) == 0 && ipsec_id_chars_ok(NULL, 0) == 1 && ipsec_addr_list_ok(NULL) == 1
	   && ipsec_subnet3_ok(NULL) == 0 && ipsec_profile_shape_ok(NULL) == 0 && ipsec_profile_ext_shape_ok(NULL) == 0, "A: NULL arguments");
	ck(NF >= 22, "A: field table too short (%d)", NF);
	/* a tab after the keyword counts too (in a saved value a tab is refused as a control character before that) */
	ck(ipsec_str_has_include("include\t/tmp/a") == 1 && ipsec_str_has_include("x include /a") == 1 && ipsec_str_has_include("include") == 0
	   && ipsec_str_has_include("include/a") == 0 && ipsec_str_has_include("xinclude y") == 1 && ipsec_str_has_include("Include /a") == 0,
	   "A: the include keyword rule");

	for (fi = 0; fi < NF; fi++) {
		EACH(common, 1, 0);
		memset(long_v, 'a', sizeof(long_v));
		r = put(fi, long_v, F[fi].sz - 1, &bad, &why);
		ck(r == 1, "A: %s filled to its last byte must be accepted", F[fi].name);
		r = put(fi, "abc\0\nrightid=%any", 17, &bad, &why);	/* text after the terminating NUL is not part of the value */
		ck(r == 1, "A: %s: bytes after the NUL must not count", F[fi].name);
		for (i = 0; i < (int)sizeof(CTL); i++) for (pos = 0; pos < 3; pos++) {	/* a control character anywhere, in every field */
			strcpy(buf, "abc");
			if (pos == 0) { buf[0] = CTL[i]; } else if (pos == 1) { buf[1] = CTL[i]; } else { buf[3] = CTL[i]; buf[4] = 0; }
			want(fi, buf, 0, IPSEC_GATE_CHAR);
		}
		if (F[fi].cls == C_SECRET) EACH(incl, 1, 0); else EACH(incl, 0, IPSEC_GATE_INCLUDE);
		switch (F[fi].cls) {
		case C_ANY:    EACH(any_ok, 1, 0); EACH(id_ok, 1, 0); EACH(tok_ok, 1, 0); break;
		case C_ID:     EACH(id_ok, 1, 0); EACH(id_no, 0, IPSEC_GATE_CHAR); break;
		case C_HOST:   EACH(host_ok, 1, 0); EACH(host_no, 0, IPSEC_GATE_CHAR); break;
		case C_TOKEN:  EACH(tok_ok, 1, 0); EACH(tok_no, 0, IPSEC_GATE_CHAR); break;
		case C_SECRET: EACH(sec_ok, 1, 0); EACH(sec_no, 0, IPSEC_GATE_CHAR); break;
		case C_ADDRS:  EACH(adr_ok, 1, 0); EACH(adr_no, 0, IPSEC_GATE_CHAR); break;
		default: ck(0, "A: unknown class for %s", F[fi].name);
		}
	}
#undef EACH
	memset(&P, 0, sizeof(P)); strcpy(P.local_id, "a\nb");
	ck(ipsec_profile_fields_ok(&P, NULL, NULL) == 0, "A: NULL out pointers still refuse");

	/* the refusal action */
	memset(&P, 0, sizeof(P)); strcpy(P.profilename, "keep"); P.ipsec_conn_en = IPSEC_CONN_EN_UP; P.vpn_type = VPN_TYPE_HOST_NET;
	log_clear();
	ipsec_profile_gate_apply(&P, 1, 3, IPSEC_GATE_OK, NULL);
	ck(!strcmp(P.profilename, "keep") && P.ipsec_conn_en == IPSEC_CONN_EN_UP && g_logs == 0, "A: a good profile is left alone, nothing logged");
	strcpy(P.local_id, "SECRETVALUE\"x");
	ipsec_profile_gate_apply(&P, 1, 3, IPSEC_GATE_CHAR, "local_id");
	{
		static const ipsec_prof_t zero;
		ck(memcmp(&P, &zero, sizeof(P)) == 0, "A: a refused slot is all zero");
		ck(P.ipsec_conn_en == IPSEC_CONN_EN_DOWN && P.profilename[0] == 0 && P.vpn_type != VPN_TYPE_NET_NET_SVR, "A: zero = down, unnamed, not a site-to-site server");
	}
	ck(g_logs == 1 && !strcmp(g_log, "server profile 3 skipped: unsafe character in local_id\n"), "A: log line is [%s] x%d", g_log, g_logs);
	log_clear(); ipsec_profile_gate_apply(&P, 0, 5, IPSEC_GATE_INCLUDE, "leftcert");
	ck(g_logs == 1 && !strcmp(g_log, "client profile 5 skipped: include directive in leftcert\n"), "A: include log line is [%s]", g_log);
	log_clear(); ipsec_profile_gate_apply(&P, 0, 2, IPSEC_GATE_SHAPE, NULL);
	ck(g_logs == 1 && !strcmp(g_log, "client profile 2 skipped: malformed saved value\n"), "A: shape log line is [%s]", g_log);
}

/* ---- saved profiles, built field by field ---- */
#define NFLD 43
static const char *const BASE2[NFLD] = {	/* the page's IKEv2 template (Reaper_VPNServer.asp buildP2) */
	"4", "Host-to-Netv2", "null", "null", "wan", "", "0", "null", "null", "null", "null", "null", "null", "1", "10.10.10", "null", "2",
	"null", "null", "0", "@vpn.example.com", "null", "null", "0", "", "", "eap-mschapv2", "1", "500", "4500", "10", "1", "null", "null",
	"null", "null", "<<<<", "1", "pubkey", "svrCert.pem", "always", "svrKey.pem", "%identity" };
static const char *const BASE1[38] = {		/* the page's IKEv1 template (buildP1) */
	"4", "Host-to-Net", "null", "null", "wan", "", "1", "12345678", "null", "null", "null", "null", "null", "1", "10.10.10", "null", "1",
	"null", "null", "0", "null", "null", "null", "1", "", "", "eap-md5", "1", "500", "4500", "10", "1", "null", "null", "null", "null",
	"<<<<", "1" };
static const char *const S2S_SVR[38] = {	/* the site-to-site server form (comment above _ipsec_export) */
	"1", "S2S", "null", "null", "wan", "", "1", "12345678", "<192.168.50.0/24", "0", "<192.168.1.0/24", "0", "tunnel", "null", "null", "null",
	"2", "auto", "auto", "0", "ID-MODEL", "", "172800", "0", "null", "null", "eap-md5", "1", "500", "4500", "10", "1", "auto", "auto",
	"3600", "3", "null", "1" };
static const char *const S2S_CLI[38] = {	/* what _ipsec_export() writes and httpd's import saves as ipsec_profile_client_N */
	"2", "S2S-c1", "1", "vpn.example.com", "wan", "", "1", "12345678", "<192.168.1.0/24", "0", "<192.168.50.0/24", "0", "tunnel", "null", "null",
	"2", "2", "auto", "auto", "0", "", "ID-MODEL", "172800", "0", "", "", "eap-md5", "1", "500", "4500", "10", "1", "auto", "auto", "3600",
	"3", "null", "1" };
static char *join(const char *const *base, int n, int at, const char *val)	/* static buffer: one profile at a time */
{
	static char v[1024];
	int i; size_t o = 0;
	v[0] = 0;
	for (i = 0; i < n; i++)
		o += snprintf(v + o, sizeof(v) - o, "%s%s", i ? ">" : "", i == at ? val : base[i]);
	return v;
}
#define EXT "0>0>0>0>0>0"

static void boot(void)
{
	memset(prof, 0, sizeof(prof));	/* as rc_ipsec_config_init() does */
	nv_clear(); log_clear(); g_sets = 0;
}
static void save_ext(const char *key, const char *v, const char *ext)
{
	char e[64];
	nv_set(key, v);
	snprintf(e, sizeof(e), "%s_ext", key);
	nv_set(e, ext);
}
static void save(const char *key, const char *v) { save_ext(key, v, EXT); }
static int slot_zero(const ipsec_prof_t *s)
{
	static const ipsec_prof_t zero;
	return memcmp(s, &zero, sizeof(zero)) == 0;
}

/* profile 2 = the IKEv2 template with one field replaced: must be refused with this log line */
static void refused(int at, const char *val, const char *reason, const char *secret)
{
	char wantl[200];
	int rc;

	boot();
	save("ipsec_profile_1", join(BASE1, 38, -1, ""));
	save("ipsec_profile_2", join(BASE2, NFLD, -1, ""));
	pre_ipsec_prof_set();						/* a good value was applied before */
	save("ipsec_profile_2", join(BASE2, NFLD, at, val));
	log_clear();
	rc = pre_ipsec_prof_set();
	snprintf(wantl, sizeof(wantl), "server profile 2 skipped: %s\n", reason);
	ck(rc == 1, "B: field %d = \"%s\": pre_ipsec_prof_set() must still return 1 (ipsec.conf is rewritten), got %d", at, show(val), rc);
	ck(slot_zero(&prof[PROF_SVR][1]), "B: field %d = \"%s\": the slot must be cleared (name=%s en=%d)", at, show(val), prof[PROF_SVR][1].profilename, prof[PROF_SVR][1].ipsec_conn_en);
	ck(!strcmp(prof[PROF_SVR][0].profilename, "Host-to-Net") && prof[PROF_SVR][0].ipsec_conn_en == IPSEC_CONN_EN_UP, "B: field %d = \"%s\": the other profile must stay", at, show(val));
	ck(g_logs == 1 && !strcmp(g_log, wantl), "B: field %d = \"%s\": log must be [%s], is [%s] x%d", at, show(val), show(wantl), show(g_log), g_logs);
	ck(secret == NULL || strstr(g_log, secret) == NULL, "B: field %d: the log line must not carry the value", at);
	ck(g_sets == 0, "B: field %d: no setting may be written", at);
	/* the same value as client profile 3, then corrected */
	boot();
	save("ipsec_profile_client_3", join(BASE2, NFLD, at, val));
	rc = pre_ipsec_prof_set();
	snprintf(wantl, sizeof(wantl), "client profile 3 skipped: %s\n", reason);
	ck(rc == 1 && slot_zero(&prof[PROF_CLI][2]) && g_logs == 1 && !strcmp(g_log, wantl), "B: field %d = \"%s\" as client profile 3: rc=%d log=[%s]", at, show(val), rc, show(g_log));
	save("ipsec_profile_client_3", join(BASE2, NFLD, -1, ""));
	log_clear();
	rc = pre_ipsec_prof_set();
	ck(rc == 1 && g_logs == 0 && !strcmp(prof[PROF_CLI][2].local_id, "@vpn.example.com") && prof[PROF_CLI][2].ipsec_conn_en == IPSEC_CONN_EN_UP,
	   "B: field %d: a corrected value must be applied again", at);
}
/* the same, but the value must be applied; returns the slot */
static ipsec_prof_t *applied(int at, const char *val)
{
	int rc;
	boot();
	save("ipsec_profile_2", join(BASE2, NFLD, at, val));
	rc = pre_ipsec_prof_set();
	ck(rc == 1 && g_logs == 0 && prof[PROF_SVR][1].ipsec_conn_en == IPSEC_CONN_EN_UP && !strcmp(prof[PROF_SVR][1].profilename, "Host-to-Netv2"),
	   "B: field %d = \"%s\" must be applied (logs=%d [%s])", at, show(val), g_logs, show(g_log));
	return &prof[PROF_SVR][1];
}

static void part_b(void)
{
	static const char *const ok_ids[] = { "@vpn.example.com", "192.0.2.1", "2001:db8::1", "user@example.com", "%any", "null", "", "@#0a0b0c" };
	ipsec_prof_t *s;
	size_t k;
	int rc;

	/* the page's two templates */
	boot();
	save("ipsec_profile_1", join(BASE1, 38, -1, ""));
	save("ipsec_profile_2", join(BASE2, NFLD, -1, ""));
	rc = pre_ipsec_prof_set();
	ck(rc == 1 && g_logs == 0, "B: templates: rc=%d logs=%d [%s]", rc, g_logs, show(g_log));
	ck(!strcmp(prof[PROF_SVR][0].profilename, "Host-to-Net") && prof[PROF_SVR][0].ipsec_conn_en == IPSEC_CONN_EN_UP
	   && !strcmp(prof[PROF_SVR][0].auth_method_key, "12345678") && !strcmp(prof[PROF_SVR][0].virtual_subnet, "10.10.10.0/24")
	   && prof[PROF_SVR][0].vpn_type == VPN_TYPE_HOST_NET,
	   "B: template 1 parsed (name=%s key=%s vsub=%s en=%d)", prof[PROF_SVR][0].profilename, prof[PROF_SVR][0].auth_method_key,
	   prof[PROF_SVR][0].virtual_subnet, prof[PROF_SVR][0].ipsec_conn_en);
	ck(!strcmp(prof[PROF_SVR][1].profilename, "Host-to-Netv2") && prof[PROF_SVR][1].ipsec_conn_en == IPSEC_CONN_EN_UP
	   && !strcmp(prof[PROF_SVR][1].local_id, "@vpn.example.com") && !strcmp(prof[PROF_SVR][1].remote_id, "null")
	   && !strcmp(prof[PROF_SVR][1].eap_identity, "%identity") && !strcmp(prof[PROF_SVR][1].leftcert, "svrCert.pem")
	   && !strcmp(prof[PROF_SVR][1].leftkey, "svrKey.pem") && !strcmp(prof[PROF_SVR][1].leftsendcert, "always"),
	   "B: template 2 parsed (name=%s lid=%s rid=%s eap=%s)", prof[PROF_SVR][1].profilename, prof[PROF_SVR][1].local_id,
	   prof[PROF_SVR][1].remote_id, prof[PROF_SVR][1].eap_identity);
	/* the local ID the page computes: "@<ddns host>" or the WAN address, or nothing while the WAN is down */
	s = applied(20, "192.0.2.77"); ck(!strcmp(s->local_id, "192.0.2.77"), "B: template 2 with the WAN address as local ID");
	s = applied(20, ""); ck(s->local_id[0] == 0, "B: template 2 with an empty local ID");
	s = applied(20, "@my-router_1.asuscomm.com"); ck(!strcmp(s->local_id, "@my-router_1.asuscomm.com"), "B: template 2 with a DDNS name as local ID");

	/* the site-to-site forms: what the server keeps and what the export / import hands to the client side */
	boot();
	save_ext("ipsec_profile_3", join(S2S_SVR, 38, -1, ""), "6>6>255>6>6>255");
	save_ext("ipsec_profile_client_1", join(S2S_CLI, 38, -1, ""), "6>6>255>6>6>255");
	rc = pre_ipsec_prof_set();
	ck(rc == 1 && g_logs == 0, "B: site-to-site forms: rc=%d logs=%d [%s]", rc, g_logs, show(g_log));
	ck(prof[PROF_SVR][2].vpn_type == VPN_TYPE_NET_NET_SVR && !strcmp(prof[PROF_SVR][2].profilename, "S2S") && !strcmp(prof[PROF_SVR][2].local_id, "ID-MODEL")
	   && !strcmp(prof[PROF_SVR][2].local_subnet, "192.168.50.0/24") && !strcmp(prof[PROF_SVR][2].remote_subnet, "192.168.1.0/24")
	   && !strcmp(prof[PROF_SVR][2].tun_type, "tunnel") && prof[PROF_SVR][2].ipsec_conn_en == IPSEC_CONN_EN_UP && prof[PROF_SVR][2].dh_group == 255,
	   "B: site-to-site server form parsed (name=%s lid=%s lsub=%s rsub=%s)", prof[PROF_SVR][2].profilename, prof[PROF_SVR][2].local_id,
	   prof[PROF_SVR][2].local_subnet, prof[PROF_SVR][2].remote_subnet);
	ck(prof[PROF_CLI][0].vpn_type == VPN_TYPE_NET_NET_CLI && !strcmp(prof[PROF_CLI][0].profilename, "S2S-c1") && !strcmp(prof[PROF_CLI][0].remote_gateway, "vpn.example.com")
	   && !strcmp(prof[PROF_CLI][0].remote_id, "ID-MODEL") && !strcmp(prof[PROF_CLI][0].remote_subnet, "192.168.50.0/24") && prof[PROF_CLI][0].ipsec_conn_en == IPSEC_CONN_EN_UP,
	   "B: imported client form parsed (name=%s gw=%s rid=%s)", prof[PROF_CLI][0].profilename, prof[PROF_CLI][0].remote_gateway, prof[PROF_CLI][0].remote_id);
	boot();		/* the export puts an address, a DDNS name, or an IPv6 address with its prefix length there */
	save("ipsec_profile_client_1", join(S2S_CLI, 38, 3, "2001:db8::1/64"));
	rc = pre_ipsec_prof_set();
	ck(rc == 1 && g_logs == 0 && !strcmp(prof[PROF_CLI][0].remote_gateway, "2001:db8::1/64"), "B: imported client form with an IPv6 gateway (logs [%s])", show(g_log));

	/* accepted through the real parser */
	for (k = 0; k < sizeof(ok_ids) / sizeof(ok_ids[0]); k++) {
		s = applied(20, ok_ids[k]); ck(!strcmp(s->local_id, ok_ids[k]), "B: local ID \"%s\" kept as it is", ok_ids[k]);
		s = applied(21, ok_ids[k]); ck(!strcmp(s->remote_id, ok_ids[k]), "B: remote ID \"%s\" kept as it is", ok_ids[k]);
	}
	s = applied(7, "please include me 12"); ck(!strcmp(s->auth_method_key, "please include me 12"), "B: a key with spaces and the word include");
	s = applied(3, "vpn.example.com"); ck(!strcmp(s->remote_gateway, "vpn.example.com"), "B: a host name as remote gateway");
	s = applied(36, "<1.1.1.1<8.8.8.8<<"); ck(!strcmp(s->samba_settings, ">1.1.1.1>8.8.8.8>>"), "B: a DNS list");
	s = applied(10, "<192.168.3.0/24<10.9.0.0/16"); ck(!strcmp(s->remote_subnet, "192.168.3.0/24,10.9.0.0/16"), "B: two remote subnets");

	/* control characters: in a string field, in a numeric field, in the _ext value */
	refused(20, "@vpn.example.com\n  leftsubnet=0.0.0.0/0", "unsafe character in the saved value", "leftsubnet");
	refused(20, "@vpn.example.com\r", "unsafe character in the saved value", "vpn.example");
	refused(20, "a\tb", "unsafe character in the saved value", NULL);
	refused(21, "peer\x7f", "unsafe character in the saved value", "peer");
	refused(28, "500\n  auto=start", "unsafe character in the saved value", "auto=start");
	boot();
	save_ext("ipsec_profile_2", join(BASE2, NFLD, -1, ""), "0>0>0>0>0>0\n4>evil>x");
	rc = pre_ipsec_prof_set();
	ck(rc == 1 && slot_zero(&prof[PROF_SVR][1]) && g_logs == 1 && !strcmp(g_log, "server profile 2 skipped: unsafe character in the saved value\n"),
	   "B: a line break in the _ext value: rc=%d log=[%s]", rc, show(g_log));
	/* too few separators in the _ext value */
	{
		static const char *const bad_ext[] = { "0", "0>0>0", "0>0>0>0>0", "x" };
		for (k = 0; k < sizeof(bad_ext) / sizeof(bad_ext[0]); k++) {
			boot();
			save_ext("ipsec_profile_2", join(BASE2, NFLD, -1, ""), bad_ext[k]);
			rc = pre_ipsec_prof_set();
			ck(rc == 1 && slot_zero(&prof[PROF_SVR][1]) && g_logs == 1 && !strcmp(g_log, "server profile 2 skipped: malformed saved value\n"),
			   "B: _ext value \"%s\": rc=%d log=[%s]", bad_ext[k], rc, show(g_log));
		}
	}
	/* the IDs: an allowlist. A certificate DN is refused - unquoted, its '=' breaks the whole ipsec.conf. */
	refused(20, "C=US, O=Example, CN=vpn", "unsafe character in local_id", "Example");
	refused(21, "C=US,O=Example,CN=vpn", "unsafe character in remote_id", "Example");
	refused(20, "vpn\"quoted", "unsafe character in local_id", "quoted");
	refused(20, "vpn #comment", "unsafe character in local_id", "comment");
	refused(20, "a<b", "unsafe character in local_id", "a<b");
	refused(20, "a&amp;b", "unsafe character in local_id", "amp");
	refused(20, "two words", "unsafe character in local_id", "words");
	refused(20, "@#0a0g", "unsafe character in local_id", "0a0g");
	refused(21, "peer\" flags=\"x", "unsafe character in remote_id", "flags");
	refused(21, "peer#x", "unsafe character in remote_id", "peer");
	refused(21, "a&b", "unsafe character in remote_id", "a&b");
	refused(21, "a\\b", "unsafe character in remote_id", NULL);
	/* the remote gateway: right= in ipsec.conf and the selector in ipsec.secrets */
	refused(3, "host name", "unsafe character in remote_gateway", "name");
	refused(3, "1.2.3.4 : PSK \"x\"", "unsafe character in remote_gateway", "PSK");
	refused(3, "1.2.3.4#", "unsafe character in remote_gateway", "1.2.3.4");
	/* include: wherever a token can start */
	refused(3, "1.2.3.4 include /tmp/mnt/sda1/x.conf", "include directive in remote_gateway", "sda1");
	refused(10, "<10.0.0.0/8 include /tmp/x", "include directive in remote_subnet", "/tmp");
	refused(12, "tunnel include /tmp/x", "include directive in tun_type", "/tmp");
	refused(26, "pubkey include /tmp/x", "include directive in rightauth2_method", "/tmp");
	refused(38, "pubkey include /tmp/x", "include directive in leftauth_method", "/tmp");
	refused(39, "a.pem include /tmp/mnt/sda1/x.conf", "include directive in leftcert", "sda1");
	refused(40, "always include /tmp/mnt/sda1/x.conf", "include directive in leftsendcert", "sda1");
	refused(42, "%identity include /tmp/mnt/sda1/x.conf", "include directive in eap_identity", "sda1");
	refused(24, "include /tmp/mnt/sda1/x.secrets", "include directive in xauth_account", "sda1");
	refused(20, "include /tmp/x", "include directive in local_id", "/tmp");
	/* one token on its own line */
	refused(39, "my cert.pem", "unsafe character in leftcert", "my cert");
	refused(40, "al ways", "unsafe character in leftsendcert", NULL);
	refused(42, "a b", "unsafe character in eap_identity", NULL);
	refused(12, "tunnel x", "unsafe character in tun_type", NULL);
	refused(26, "eap-md5 x", "unsafe character in rightauth2_method", NULL);
	refused(10, "<10.0.0.0/8, 10.1.0.0/16", "unsafe character in remote_subnet", NULL);
	refused(39, "a=b", "unsafe character in leftcert", NULL);
	/* a double quote inside a secret that is written between double quotes */
	refused(7, "a\"bcdefgh", "unsafe character in auth_method_key", "bcdefgh");
	refused(25, "x\"y", "unsafe character in xauth_password", NULL);
	refused(41, "k\"ey.pem", "unsafe character in leftkey", "ey.pem");
	/* the DNS / WINS list goes into strongswan.conf, where '}' closes the section */
	refused(36, "<1.1.1.1}<x", "unsafe character in samba_settings", NULL);
	refused(36, "<1 2<<<", "unsafe character in samba_settings", NULL);

	/* too few separators in the profile itself: refused, nothing parsed */
	{
		static const int nsep[] = { 0, 1, 7, 8, 9, 10, 20, 36, 38, 39, 40, 41 };
		for (k = 0; k < sizeof(nsep) / sizeof(nsep[0]); k++) {
			char v[1024], *p;
			int c = 0;
			snprintf(v, sizeof(v), "%s", join(BASE2, NFLD, -1, ""));
			for (p = v; *p; p++) if (*p == '>' && ++c > nsep[k]) { *p = 0; break; }
			boot();
			save("ipsec_profile_1", join(BASE1, 38, -1, ""));
			save("ipsec_profile_2", join(BASE2, NFLD, -1, ""));
			pre_ipsec_prof_set();
			save("ipsec_profile_2", v);
			log_clear();
			rc = pre_ipsec_prof_set();
			ck(ipsec_profile_shape_ok(v) == 0, "B: %d separators must not pass the shape check", nsep[k]);
			ck(rc == 1 && slot_zero(&prof[PROF_SVR][1]) && g_logs == 1 && !strcmp(g_log, "server profile 2 skipped: malformed saved value\n")
			   && prof[PROF_SVR][0].ipsec_conn_en == IPSEC_CONN_EN_UP, "B: %d separators: rc=%d log=[%s]", nsep[k], rc, show(g_log));
		}
		boot(); save("ipsec_profile_1", "4"); rc = pre_ipsec_prof_set();
		ck(rc == 1 && slot_zero(&prof[PROF_SVR][0]) && !strcmp(g_log, "server profile 1 skipped: malformed saved value\n"), "B: ipsec_profile_1=4: log=[%s]", show(g_log));
		/* 37 separators = the short form, 42 = the long form, more = extra fields the parser never reaches */
		ck(ipsec_profile_shape_ok(join(BASE1, 38, -1, "")) == 1 && ipsec_profile_shape_ok(join(BASE2, NFLD, -1, "")) == 1, "B: both templates pass the shape check");
		{ char v[1100]; snprintf(v, sizeof(v), "%s>more>and>more", join(BASE2, NFLD, -1, "")); ck(ipsec_profile_shape_ok(v) == 1, "B: extra fields pass the shape check"); }
		/* an empty subnet field makes the parser's one-character step eat a separator: one more is needed then */
		ck(ipsec_profile_shape_ok(join(BASE1, 38, 8, "")) == 0 && ipsec_profile_shape_ok(join(BASE1, 38, 10, "")) == 0, "B: an empty subnet field in the short form is one separator short");
		ck(ipsec_profile_ext_shape_ok("0>0>0>0>0>0") == 1 && ipsec_profile_ext_shape_ok("6>6>255>6>6>255") == 1 && ipsec_profile_ext_shape_ok("0>0>0>0>0") == 0
		   && ipsec_profile_ext_shape_ok("") == 0, "B: the _ext shape check");
	}
}

static int charset_ok(const char *s)
{
	for (; *s; s++) if (!((*s >= '0' && *s <= '9') || *s == '.')) return 0;
	return 1;
}
/* field 14 of the raw profile, in the forms both raw readers must take or turn down */
static const struct { const char *field; int ok; } SUBNET3[] = {
	{ "10.10.10", 1 }, { "10.10.11", 1 }, { "192.168.77", 1 }, { "0.0.0", 1 }, { "255.255.255", 1 }, { "1.2.3", 1 },
	{ "", 0 }, { "10.10.10.0/24", 0 }, { "10.10.10,1", 0 }, { "999.1.1", 0 }, { "256.1.1", 0 }, { "1234.1.1", 0 }, { "10.10", 0 }, { "10.10.10.10", 0 },
	{ "10.10.10.", 0 }, { ".10.10", 0 }, { "10..10", 0 }, { "a.b.c", 0 }, { "10.10.10\n-A INPUT -j ACCEPT", 0 }, { "10.10.10\n", 0 },
	{ "10.10.10;reboot", 0 }, { "10.10.10 -j ACCEPT", 0 }, { "$(reboot)", 0 }, { "`reboot`", 0 }, { "null", 0 }, { "10.10.10/24", 0 },
	{ "10.10.10|nc", 0 }, { "10.10.10&", 0 }, { " 10.10.10", 0 }, { "10.10.-1", 0 }, { "+1.2.3", 0 }, { "0x0a.1.1", 0 },
};
#define NSUB ((int)(sizeof(SUBNET3) / sizeof(SUBNET3[0])))

static void part_c(void)
{
	static const struct { const char *v; int ok; } wan[] = {
		{ "8.8.8.8", 1 }, { "203.0.113.7", 1 }, { "192.168.1.2", 1 }, { "10.0.0.2", 1 }, { "172.16.5.4", 1 }, { "100.64.0.1", 1 },
		{ "255.255.255.254", 1 }, { "0.0.0.0", 0 }, { "", 0 }, { "999.1.1.1", 0 }, { "1.2.3", 0 }, { "1.2.3.4.5", 0 }, { "abc", 0 },
		{ "1.2.3.4;reboot", 0 }, { "1.2.3.4\nreboot", 0 }, { "1.2.3.4 ", 0 }, { " 1.2.3.4", 0 }, { "$(id)", 0 }, { "1.2.3.4`id`", 0 },
		{ "2001:db8::1", 0 }, { "vpn.example.com", 0 },
	};
	char out[64], wantv[64];
	size_t k;
	int i;

	for (k = 0; k < sizeof(wan) / sizeof(wan[0]); k++)
		ck(ipsec_wan_addr_ok(wan[k].v) == wan[k].ok, "C: WAN address \"%s\" must be %s", show(wan[k].v), wan[k].ok ? "accepted" : "refused");
	ck(ipsec_wan_addr_ok(NULL) == 0, "C: a NULL WAN address is refused");

	for (i = 0; i < NSUB; i++) {
		ck(ipsec_subnet3_ok(SUBNET3[i].field) == SUBNET3[i].ok, "C: ipsec_subnet3_ok(\"%s\") must be %d", show(SUBNET3[i].field), SUBNET3[i].ok);
		boot();
		save("ipsec_profile_1", join(BASE1, 38, 14, SUBNET3[i].field));
		memset(out, 'x', sizeof(out));
		get_virtual_subnet("ipsec_profile_1", out, sizeof(out));
		snprintf(wantv, sizeof(wantv), "%s", SUBNET3[i].ok ? SUBNET3[i].field : "10.10.10");
		ck(!strcmp(out, wantv) && charset_ok(out), "C: get_virtual_subnet(field \"%s\") must be \"%s\", is \"%s\"", show(SUBNET3[i].field), wantv, show(out));
	}
	boot();
	get_virtual_subnet("ipsec_profile_1", out, sizeof(out));
	ck(!strcmp(out, "10.10.10"), "C: get_virtual_subnet() with nothing saved is the default, is \"%s\"", out);
}

static char *slurp(void)
{
	static char b[16384];
	FILE *fp = fopen(g_out, "r");
	size_t n = fp ? fread(b, 1, sizeof(b) - 1, fp) : 0;
	if (fp) fclose(fp);
	b[n] = 0;
	return b;
}
static void part_d(void)
{
	char *s;

	boot();
	save("ipsec_profile_1", join(BASE1, 38, -1, ""));
	save("ipsec_profile_2", join(BASE2, NFLD, -1, ""));
	nv_set("ipsec_server_enable", "1");
	nv_set("ipsec_ig_enable", "1");
	nv_set("ipsec_client_list_1", "<bob>bobpw<carol>carolpw");
	/* name>password>description>time>active */
	nv_set("ig_client_list", "<alice>alicepw>d>0>1<bad name>BADPW1>d>0>1<dave;x>DAVEPW>d>0>0<include /tmp/x>BADPW2>d>0>1<erin>erinpw>d>0>1");
	/* name>password>description>time>active>lan_access */
	nv_set("ig_guest_client_list", "<guest1>g1pw>d>0>1>0<g-2>BADPW3>d>0>1>0<okguest>g3pw>d>0>1>1<x y>BADPW4>d>0>1>1<off#1>OFFPW>d>0>0>0"
		"<thisnameiswaytoolongforaninstantguardclient>BADPW5>d>0>1>0");
	ck(pre_ipsec_prof_set() == 1 && g_logs == 0, "D: both templates applied (logs [%s])", show(g_log));
	remove(g_out);
	rc_ipsec_secrets_set();
	s = slurp();
	ck(strstr(s, " : PSK \"12345678\"") != NULL, "D: the secrets file was written (the PSK line is there)");
	ck(strstr(s, "\nbob : XAUTH \"bobpw\"") != NULL && strstr(s, "\ncarol : XAUTH \"carolpw\"") != NULL, "D: the plain client list is written as before");
	ck(strstr(s, "\nalice : ") != NULL && strstr(s, "\nerin : ") != NULL && strstr(s, "\nguest1 : ") != NULL && strstr(s, "\nokguest : ") != NULL,
	   "D: Instant Guard clients and guests with a good name keep their credential");
	ck(strstr(s, "BADPW") == NULL && strstr(s, "bad name") == NULL && strstr(s, "include") == NULL && strstr(s, "g-2") == NULL && strstr(s, "x y") == NULL
	   && strstr(s, "thisnameiswaytoolong") == NULL, "D: a client or guest whose name is refused gets no line in ipsec.secrets");
	ck(strstr(s, "DAVEPW") == NULL && strstr(s, "OFFPW") == NULL, "D: inactive entries are not written (as before)");
	ck(!strcmp(g_log, "Instant Guard client 2 skipped: unsafe name\nInstant Guard client 4 skipped: unsafe name\n"
	                  "Instant Guard guest 2 skipped: unsafe name\nInstant Guard guest 4 skipped: unsafe name\nInstant Guard guest 6 skipped: unsafe name\n")
	   && g_logs == 5, "D: one log line per refused entry and pass, by list position, never the name: [%s] x%d", show(g_log), g_logs);
	ck(g_sets == 0, "D: no setting is written");
	remove(g_out);
}

static void part_e(void)
{
	char buf[64], wantv[64], *r;
	int i;

	nv_clear();
	nv_set("vpns_rl", "<OpenVPN>OpenVPN>1>1>4<IPsec VPN>IPSec>1>1>5");
	for (i = 0; i < NSUB; i++) {
		ck(vpns_subnet3_ok(SUBNET3[i].field) == SUBNET3[i].ok, "E: vpns_subnet3_ok(\"%s\") must be %d", show(SUBNET3[i].field), SUBNET3[i].ok);
		nv_set("ipsec_profile_1", join(BASE1, 38, 14, SUBNET3[i].field));
		memset(buf, 'x', sizeof(buf)); buf[sizeof(buf) - 1] = 0;
		r = get_vpns_iprange_by_vpns_idx(5, buf, sizeof(buf));
		if (SUBNET3[i].ok) {
			snprintf(wantv, sizeof(wantv), "%s.1-%s.254", SUBNET3[i].field, SUBNET3[i].field);
			ck(r == buf && !strcmp(buf, wantv), "E: range for field \"%s\" must be \"%s\", is \"%s\"", SUBNET3[i].field, wantv, r ? show(r) : "(none)");
		} else
			ck(r == NULL, "E: field \"%s\" must give no range, gave \"%s\"", show(SUBNET3[i].field), r ? show(r) : "(none)");
	}
	nv_set("ipsec_profile_1", "");
	ck(get_vpns_iprange_by_vpns_idx(5, buf, sizeof(buf)) == NULL, "E: no saved profile: no range (as before)");
	nv_set("ipsec_profile_1", "4>x");
	ck(get_vpns_iprange_by_vpns_idx(5, buf, sizeof(buf)) == NULL, "E: a short profile: no range (as before)");
	nv_set("ipsec_profile_1", join(BASE1, 38, -1, ""));
	ck(get_vpns_iprange_by_vpns_idx(4, buf, sizeof(buf)) == NULL, "E: another VPN server's index: no range");
}

/* the parser straight on exact-size heap copies: a read or write outside the value is what the sanitizer build
 * stops on. Every prefix of the long template, and the helpers on their own. */
static void part_f(void)
{
	char full[1024], *h;
	size_t len, L;
	int i, n, c, sh;

	snprintf(full, sizeof(full), "%s", join(BASE2, NFLD, -1, ""));
	len = strlen(full);
	for (L = 0; L <= len; L++) {
		for (c = 0, i = 0; i < (int)L; i++) if (full[i] == '>') c++;
		h = malloc(L + 1); memcpy(h, full, L); h[L] = 0;
		sh = ipsec_profile_shape_ok(h);
		ck(sh == (c == 37 || c >= 42), "F: prefix of %d bytes (%d separators): shape check says %d", (int)L, c, sh);
		memset(prof, 0, sizeof(prof));
		ipsec_prof_fill(0, h, PROF_SVR);		/* must stay inside h whatever the shape */
		free(h);
	}
	for (L = 0; L <= strlen("6>6>255>6>6>255"); L++) {
		h = malloc(L + 1); memcpy(h, "6>6>255>6>6>255", L); h[L] = 0;
		memset(prof, 0, sizeof(prof));
		ipsec_prof_fill_ext(0, h, PROF_SVR);
		free(h);
	}
	{
		static const char *const odd[] = { "", ">", ">>", "4", "4>", ">>>>>>>>", ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", "4>a>b>c>d>e>1>k", "4>a>b>c>d>e>1>k>",
			"4>a>b>c>d>e>1>k>>", "4>a>b>c>d>e>1>k>x>0", "4>a>b>c>d>e>1>k>x>0>", "<<<<", "n", "nu", "auto" };
		size_t k;
		for (k = 0; k < sizeof(odd) / sizeof(odd[0]); k++) {
			h = strdup(odd[k]); memset(prof, 0, sizeof(prof)); ipsec_prof_fill(0, h, PROF_SVR); free(h);
			h = strdup(odd[k]); ipsec_prof_fill_ext(0, h, PROF_SVR); free(h);
			if (odd[k][0]) { h = strdup(odd[k]); ipsec_samba_prof_fill(h); free(h); }	/* its caller never passes an empty list */
		}
	}
	/* the helpers: at the end of the value the shift keeps the caller on the terminator */
	h = strdup("12"); n = ipsec_profile_int_parse(FLAG_NONE, h, &i);
	ck(n == 12 && i == 2 && h[2] == 0, "F: int parse of \"12\" (no separator): value %d, shift %d", n, i); free(h);
	h = strdup("12>x"); n = ipsec_profile_int_parse(FLAG_NONE, h, &i);
	ck(n == 12 && i == 3 && h[2] == 0 && h[3] == 'x', "F: int parse of \"12>x\": value %d, shift %d", n, i); free(h);
	h = strdup(""); n = ipsec_profile_int_parse(FLAG_NONE, h, &i);
	ck(i == 0, "F: int parse of an empty value: shift %d", i); free(h);
	{
		char out[8];
		h = strdup("abc"); i = 99;
		ipsec_profile_str_parse(h, out, __STRARGS__);
		ck(!strcmp(out, "abc") && i == 3, "F: string parse of \"abc\" (no separator): \"%s\", shift %d", out, i); free(h);
		h = strdup("abc>d"); i = 99;
		ipsec_profile_str_parse(h, out, __STRARGS__);
		ck(!strcmp(out, "abc") && i == 4 && h[3] == 0, "F: string parse of \"abc>d\": \"%s\", shift %d", out, i); free(h);
		h = strdup("abcdefghijklmnop>z"); i = 99;
		ipsec_profile_str_parse(h, out, __STRARGS__);
		ck(!strcmp(out, "abcdefg") && i == 17, "F: string parse longer than the field: \"%s\", shift %d", out, i); free(h);
	}
}

int main(int argc, char **argv)
{
	int n0, f0;
	if (argc < 2) return 2;
	g_out = argv[1];
#define PART(fn, title) n0 = g_n; f0 = g_fail; fn(); printf("%s %s: %d checks\n", g_fail > f0 ? "FAIL" : "ok  ", title, g_n - n0)
	PART(part_a, "A. gate table");
	PART(part_b, "B. real parser + gate");
	PART(part_c, "C. WAN address + get_virtual_subnet");
	PART(part_d, "D. ipsec.secrets + Instant Guard names");
	PART(part_e, "E. get_vpns_iprange_by_vpns_idx");
	PART(part_f, "F. short values, the parser stays inside");
	printf("CHECKS %d FAILED %d\n", g_n, g_fail);
	return g_fail ? 1 : 0;
}
'''

# the string parser's last two arguments are (shift, size) on one line and (size, shift) on the other
m = re.search(r"void ipsec_profile_str_parse\(char \*p_end, char \*p_tmp, ([^)]*)\)", code)
STRARGS = "&i, sizeof(out)" if m and m.group(1).strip().startswith("int") else "sizeof(out), &i"

prog = (HARNESS.replace("__G62__", g62).replace("__VSS__", vss).replace("__F60__", f60).replace("__IGS__", igs)
        .replace("__SLICE__", raw[S0:S1]).replace("__EXTRA__", "\n\n".join(extra)).replace("__FIELDS__", FIELDS)
        .replace("__STRARGS__", STRARGS))

def run_capped(cmd, timeout, cap, env=None):
    """Run cmd; keep at most `cap` bytes of its output and kill it at the cap or the time limit. (A sanitizer
    runtime that faults in its own signal handler prints without end - this must never be left unbounded.)"""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    timer = threading.Timer(timeout, p.kill)
    timer.start()
    try:
        out = p.stdout.read(cap + 1)
        over = len(out) > cap
        if over:
            p.kill()
        p.stdout.close()
        rc = p.wait()
    finally:
        timer.cancel()
    return rc, out[:cap].decode("utf-8", "replace"), over

work = tempfile.mkdtemp(prefix="ipsecgate_")
try:
    c_file, exe, out_file = os.path.join(work, "gate.c"), os.path.join(work, "gate"), os.path.join(work, "writer.out")
    with open(c_file, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as f:
        f.write(prog)
    # sanitizers, when a one-line probe built with them runs clean here (with address randomisation off if needed)
    SAN = ["-fsanitize=address,undefined", "-fno-sanitize-recover=undefined", "-fno-omit-frame-pointer", "-g"]
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:handle_segv=0:abort_on_error=0", UBSAN_OPTIONS="print_stacktrace=1")
    san, wrap = [], []
    if os.environ.get("IPSEC_GATE_NO_SANITIZER", "") == "":
        probe_c, probe = os.path.join(work, "probe.c"), os.path.join(work, "probe")
        with open(probe_c, "w") as f:
            f.write("#include <stdlib.h>\nint main(void){ char *p = malloc(8); p[7] = 0; free(p); return 0; }\n")
        if subprocess.run([CC] + SAN + ["-o", probe, probe_c], capture_output=True).returncode == 0:
            setarch = shutil.which("setarch")
            for w in ([[setarch, platform.machine(), "-R"]] if setarch else []) + [[]]:
                try:
                    rc, out, over = run_capped(w + [probe], 20, 65536, env)
                except OSError:
                    continue
                if rc == 0 and not over:
                    san, wrap = SAN, w
                    break
    print("note: " + ("built with AddressSanitizer + UBSan" if san else "no usable sanitizer runtime here - plain build"))
    r = subprocess.run([CC, "-O0", "-w"] + san + ["-I", os.path.join(SRC, "rc"), "-o", exe, c_file], capture_output=True, text=True)
    check("the real source compiles on the host", r.returncode == 0, r.stderr[-1500:])
    if r.returncode == 0:
        rc, out, over = run_capped(wrap + [exe, out_file], 120, 1 << 20, env)
        sys.stdout.write(out if len(out) < 6000 else out[:3000] + "\n[...]\n" + out[-3000:])
        tail = out.strip().splitlines()[-1] if out.strip() else ""
        check("compiled run: every check passed, nothing read or written outside a value (%s)" % tail[:60],
              rc == 0 and not over and re.match(r"CHECKS \d{4,} FAILED 0$", tail) is not None, "exit %s%s" % (rc, ", output over the cap" if over else ""))
finally:
    shutil.rmtree(work, ignore_errors=True)

if fails:
    print("\n%d FAILED: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("\nPASS: IPsec profile gate, parser bounds, Instant Guard names, WAN address check, the two raw subnet readers, 102.8 parity")
