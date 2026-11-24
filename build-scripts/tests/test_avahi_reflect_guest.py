#!/usr/bin/env python3
"""mDNS discovery between the main network and chosen guest networks: avahi reflect-guest (owner, 2026-11-19).

WHY. Guest isolation keeps guest / IoT networks off the main LAN, and since 2026-11-14 the reflector joins only the main
LAN and the networks with Access Intranet on (`reflect-interfaces`). A phone on a guest network therefore cannot find
the main network's printer, AirPlay speaker or Chromecast. The owner chose a narrow, per-network switch: discovery as a
STAR (main <-> each chosen guest network, never guest <-> guest), only the service types picked for that network, and
never the router's own records on a guest network.

HOW. A Reaper avahi patch adds `reflect-guest=<ifname>:<type>:<type>...,<ifname>:...` in [reflector]
(avahi-daemon/main.c, normalised by reaper_rg_entry; AvahiServerConfig.reflect_guest, appended LAST; copied and freed
with the rest). avahi-core/server.c (block REAPER-RGUEST) decides each pair with reflect_pair_ok(): core <-> core = the
2026-11-14 reflect-interfaces rule, core <-> guest = through that guest's types, guest <-> guest and an interface in
neither list = never. The filter passes PTR / SRV / TXT records of an allowed type (anchored, so _ipp._tcp never matches
_ipps._tcp; the type-enumeration PTR by its target) and A / AAAA only for a host an allowed SRV in the sending
network's cache points at; a guest's SRV / TXT / A / AAAA never crosses for a name and type a main-network device
already holds in a core cache, nor for any name this router publishes itself (host name, findasus.local and the
other aliases, its services; as the owner or as an SRV / PTR target), and it reaches the main network without the
cache-flush bit (2026-11-19 review: no name takeover, no router-login phishing). Rev 4 (review R1 / R2): a guest
goodbye (TTL 0) crosses only for a record in that guest's own cache; a guest PTR never names an instance a main cache
holds; a bounded set (RG_SEEN_MAX, FIFO) of names seen on the main network during the daemon's life is refused too, so
a main name that left the router's cache cannot be taken while main clients still hold it; queries cross only for such names; the reflected-query cache walk is
filtered too; legacy
unicast never crosses a guest boundary (relayed untouched, so it cannot be filtered). announce.c new_announcer() gives
a guest interface no announcer, so the router's own records are neither announced nor answered there. The config
reader (avahi-daemon/ini-file-parser.c) read lines into char ln[256]: a longer reflect-guest= line was split, the rest
had no '=' and avahi refused its whole config (did not start); the buffer is 4096 now (rc caps the line below that).

WHAT IT DOES. Pins the option, the field, copy / free, the four reflect paths and the announcer skip; compiles on the
host, against small stand-ins, the REAL patched code (the REAPER-RGUEST block, reflect_iface_ok, reflect_response,
reflect_query with both cache-walk callbacks, reflect_probe, announce.c new_announcer and main.c's entry normaliser)
and runs: the pair matrix, the record and query filters, whole reflect flows, the announcer skip, the normaliser, and
the unset option = the old behaviour. Exit 0 pass, 1 fail, 77 skipped (no gcc, or no router tree - argv[1] or
REAPER_ROUTER_SRC = .../release/src/router). Only an image on a router proves real phones / AirPlay / Cast discovery."""
import os, re, shutil, subprocess, sys, tempfile

def skip(msg):
    print("SKIP: " + msg); sys.exit(77)

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REAPER_ROUTER_SRC", "")
if not SRC or not os.path.isfile(os.path.join(SRC, "avahi", "avahi-core", "server.c")):
    skip("no router tree with avahi/avahi-core/server.c (argv[1] or REAPER_ROUTER_SRC)")
CC = shutil.which("gcc") or shutil.which("cc")
if not CC:
    skip("no host C compiler")

fails = []
def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name + (" - " + str(detail)[:900] if detail else ""))

def read(rel):
    return open(os.path.join(SRC, rel), encoding="utf-8", errors="surrogateescape").read()

def cfunc(src, head):
    """the text of the C function whose definition starts with head, up to its closing brace at column 0"""
    i = src.find(head)
    if i < 0:
        return None
    j = src.find("\n}\n", i)
    return src[i:j + 3] if j > 0 else None

asrc = read("avahi/avahi-core/server.c")
ann = read("avahi/avahi-core/announce.c")
core = read("avahi/avahi-core/core.h")
inth = read("avahi/avahi-core/internal.h")
msrc = read("avahi/avahi-daemon/main.c")
isrc = read("avahi/avahi-daemon/ini-file-parser.c")

# ---------------------------------------------------------------- pins
check("server.c: one REAPER-RGUEST block", asrc.count("/* REAPER-RGUEST-BEGIN") == 1 and asrc.count("/* REAPER-RGUEST-END */") == 1)
check("core.h: reflect_guest right after reflect_interfaces, then reflect_core_types (2026-11-20) as the LAST member "
      "(nothing before them moves)",
      re.search(r"AvahiStringList \*reflect_interfaces;[^\n]*\n    AvahiStringList \*reflect_guest;[^\n]*\n"
                r"    char \*reflect_core_types;[^\n]*\n\} AvahiServerConfig;", core) is not None)
# ---- reaper 2026-11-20 (REAPER-MDNS-CORETYPES): the main side's own service-type list ----
check("server.c config: reflect_core_types initialised, freed, copied (with the unwind on failure) and set",
      "c->reflect_core_types = NULL;" in asrc and "avahi_free(c->reflect_core_types);" in asrc
      and "if (c->reflect_core_types && !(rct = avahi_strdup(c->reflect_core_types))) {" in asrc
      and "        avahi_string_list_free(rguest);\n        avahi_string_list_free(rifs);" in asrc
      and "ret->reflect_core_types = rct;" in asrc)
check("avahi-daemon: [reflector] reflect-core-types is parsed through reaper_core_types and logged at start",
      'strcasecmp(p->key, "reflect-core-types") == 0' in msrc
      and "c->server_config.reflect_core_types = reaper_core_types(p->value);" in msrc
      and "avahi_free(c->server_config.reflect_core_types);" in msrc
      and "config.server_config.enable_reflector && config.server_config.reflect_core_types" in msrc)
_rp = cfunc(asrc, "static int reflect_pair_ok(") or ""
check("server.c reflect_pair_ok: core<->core hands back reflect_core_types (NULL = unfiltered, as before)",
      "*types = s->config.reflect_core_types;" in _rp and _rp.count("*types = NULL;") == 1)
check("server.c config: reflect_guest initialised, freed, deep-copied (with the unwind on failure) and set",
      "c->reflect_guest = NULL;" in asrc and "avahi_string_list_free(c->reflect_guest);" in asrc
      and "if (!(rguest = avahi_string_list_copy(c->reflect_guest)) && c->reflect_guest) {" in asrc
      and "        avahi_string_list_free(rifs);\n        avahi_string_list_free(reflect);" in asrc
      and "ret->reflect_guest = rguest;" in asrc)
check("internal.h: avahi_reflect_guest_types() prototype (announce.c uses it)",
      "const char *avahi_reflect_guest_types(AvahiServer *s, AvahiInterface *i);" in inth)
check("avahi-daemon: [reflector] reflect-guest is parsed through reaper_rg_entry and logged at start (syslog)",
      'strcasecmp(p->key, "reflect-guest") == 0' in msrc and "char *ge = reaper_rg_entry(*t);" in msrc
      and "avahi_string_list_free(c->server_config.reflect_guest);" in msrc
      and "for (l = config.server_config.reflect_guest; l; l = l->next)" in msrc)
check("avahi-daemon: stock reflect-filters and reflect-interfaces are still parsed",
      'strcasecmp(p->key, "reflect-filters") == 0' in msrc and 'strcasecmp(p->key, "reflect-interfaces") == 0' in msrc)
check("server.c: stock reflect-filters (cache-time strstr in handle_response_packet) is untouched",
      "if (!from_local_iface && s->config.enable_reflector && s->config.reflect_filters != NULL) {" in asrc
      and "if (strstr(record->data.ptr.name, (char*) l->text) != NULL) {" in asrc
      and "if (strstr(record->key->name, (char*) l->text) != NULL) {" in asrc)
for fn in ("static void reflect_response(", "static void reflect_query(", "static void reflect_probe(",
           "static void reflect_legacy_unicast_query_packet("):
    body = cfunc(asrc, fn) or ""
    name = fn.split()[2].split("(")[0]
    check("server.c %s: no bare reflect_iface_ok pair left; reflect_pair_ok decides, j != i kept" % name,
          "reflect_iface_ok(" not in body and "reflect_pair_ok(s, i, j, &gt)" in body and "j != i" in body)
rb = cfunc(asrc, "static void reflect_response(") or ""
check("server.c reflect_response: the receiving end must take part; a guest pair goes through the record filter "
      "(source = the arrival cache); a guest's record goes out without the cache-flush bit",
      "!s->config.enable_reflector || !reflect_side_ok(s, i)" in rb
      and "gi = avahi_reflect_guest_types(s, i) != NULL;" in rb and "(!gt || rg_cross_ok(s, gt, r, i->cache, gi))" in rb
      and "avahi_interface_post_response(j, r, gi ? 0 : flush_cache, NULL, 1);" in rb)
pb = cfunc(asrc, "static void reflect_probe(") or ""
check("server.c reflect_probe: the receiving end must take part; a guest pair goes through the record filter",
      "!s->config.enable_reflector || !reflect_side_ok(s, i)" in pb
      and "(!gt || rg_cross_ok(s, gt, r, i->cache, avahi_reflect_guest_types(s, i) != NULL))" in pb)
qb = cfunc(asrc, "static void reflect_query(") or ""
check("server.c reflect_query: a guest pair checks the question first, then posts it and walks the cache through the filter",
      "!s->config.enable_reflector || !reflect_side_ok(s, i)" in qb
      and 0 <= qb.find("if (gt && !rg_key_ok(gt, k, j->cache))") < qb.find("avahi_interface_post_query(j, k, 1, NULL);")
      and "avahi_cache_walk(j->cache, k, rg_cache_walk_callback, &w);" in qb
      and "avahi_cache_walk(j->cache, k, reflect_cache_walk_callback, s);" in qb
      and "w.from_guest = avahi_reflect_guest_types(s, j) != NULL;" in qb)
cx = cfunc(asrc, "static int rg_cross_ok(") or ""
check("server.c rg_cross_ok (review R1): from a guest a goodbye only for a record in that guest's own cache, checked first",
      0 <= cx.find("if (r->ttl == 0 && !(from && avahi_cache_walk(from, r->key, rg_same_callback, r)))") < cx.find("AVAHI_DNS_TYPE_PTR")
      and "return avahi_record_equal_no_ttl(e->record, userdata) ? e : NULL;" in asrc)
hp = cfunc(asrc, "static void handle_response_packet(") or ""
check("server.c (review R2): names seen on the main network - fixed set of RG_SEEN_MAX 512 strdup'd names, FIFO, "
      "noted for core interfaces before reflecting, initialised in avahi_server_new, freed in avahi_server_free; "
      "the field is the last member of AvahiServer",
      "#define RG_SEEN_MAX 512" in asrc and "char *name[RG_SEEN_MAX];" in asrc
      and "t->next = (t->next + 1) % RG_SEEN_MAX;" in asrc and "avahi_free(t->name[t->next]);" in asrc
      and 0 <= hp.find("rg_seen_note(s, i, record);") < hp.find("reflect_response(s, i, record, cache_flush);")
      and "    s->legacy_unicast_reflect_id = 0;\n    s->reaper_rg_seen = NULL;\n" in asrc
      and 0 <= (cfunc(asrc, "void avahi_server_free(") or "").find("rg_seen_free(s);")
      and re.search(r"struct RgSeen \*reaper_rg_seen;\n\};", inth) is not None)
check("server.c rg_cross_ok: from a guest never a router-published name (any local entry; owner, SRV or PTR target) "
      "nor a name a core cache holds; also in the cache walk, which pushes a guest's records without the flush bit",
      "for (e = s->entries; e; e = e->entries_next)" in (cfunc(asrc, "static int rg_local_name(") or "")
      and "return strcasecmp(r->key->name, RG_ENUM_NAME) == 0 ||" in cx
      and "(!rg_local_name(s, r->data.ptr.name) && !rg_seen_has(s, r->data.ptr.name) &&" in cx
      and "!rg_core_holds_instance(s, r->data.ptr.name));" in cx
      and "if (r->key->type == AVAHI_DNS_TYPE_SRV && (rg_local_name(s, r->data.srv.name) || rg_seen_has(s, r->data.srv.name)))" in cx
      and "return !rg_local_name(s, r->key->name) && !rg_seen_has(s, r->key->name) && !rg_core_claims(s, r->key);" in cx
      and "if (!rg_cross_ok(w->server, w->types, e->record, c, w->from_guest))" in asrc
      and "avahi_record_list_push(w->server->record_list, r, 0, 0, 0);" in asrc)
lb = cfunc(asrc, "static void reflect_legacy_unicast_query_packet(") or ""
check("server.c legacy unicast: a guest interface is refused before a reflect slot is taken; only unfiltered (core) pairs relay",
      0 <= lb.find("if (avahi_reflect_guest_types(s, i)) {") < lb.find("allocate_slot(")
      and "reflect_pair_ok(s, i, j, &gt) && !gt &&" in lb)
na = cfunc(ann, "static void new_announcer(") or ""
check("announce.c new_announcer: a guest interface gets no announcer (after the stock match test, before the duplicate test)",
      0 <= na.find("!avahi_entry_is_commited(e))\n        return;") < na.find("if (avahi_reflect_guest_types(s, i))\n        return;")
      < na.find("if (get_announcer(s, e, i))"))
check("server.c: reflect_iface_ok itself is unchanged (test_mdns_reflector compiles it alone)",
      (cfunc(asrc, "static int reflect_iface_ok(") or "").count("s->config.") == 2)
check("ini-file-parser.c: config lines up to 4095 bytes (was 256); fgets takes the buffer size, no other fixed-size copy",
      isrc.count("char ln[4096], *s, *e;") == 1 and "char ln[256]" not in isrc
      and "if (!(fgets(ln, sizeof(ln), fo)))" in isrc
      and "pair->key = avahi_strdup(s);" in isrc and "pair->value = avahi_strdup(e);" in isrc
      and not re.search(r"\[(?:64|128|256|512|1024)\]", isrc))
for f, t in (("server.c", asrc), ("announce.c", ann), ("main.c", msrc), ("core.h", core), ("internal.h", inth),
             ("ini-file-parser.c", isrc)):
    check("avahi %s: ASCII only" % f, all(ord(ch) < 128 for ch in t))

# ---------------------------------------------------------------- host-compiled real code
_bm = re.search(r"(/\* REAPER-RGUEST-BEGIN.*?/\* REAPER-RGUEST-END \*/)", asrc, re.S)
_wm = re.search(r"(/\* reaper 2026-11-19: reflect-guest - a cache answer.*?)static void reflect_query\(", asrc, re.S)
parts = {
    "IFACE_OK": cfunc(asrc, "static int reflect_iface_ok("),
    "BLOCK": _bm.group(1) if _bm else None,
    "RESP": cfunc(asrc, "static void reflect_response("),
    "CWALK": cfunc(asrc, "static void* reflect_cache_walk_callback("),
    "RGWALK": _wm.group(1) if _wm else None,
    "QUERY": qb or None,
    "PROBE": cfunc(asrc, "static void reflect_probe("),
    "ANN": na or None,
    "NTYPE": cfunc(msrc, "static int reaper_rg_type_ok("),
    "NENTRY": cfunc(msrc, "static char *reaper_rg_entry("),
    "NCORE": cfunc(msrc, "static char *reaper_core_types("),
}
missing = [k for k, v in parts.items() if not v]
check("the patched functions are all there to compile", not missing, missing)

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#include <stdint.h>
#include <assert.h>
#define AVAHI_DNS_TYPE_A 0x01
#define AVAHI_DNS_TYPE_CNAME 0x05
#define AVAHI_DNS_TYPE_PTR 0x0C
#define AVAHI_DNS_TYPE_HINFO 0x0D
#define AVAHI_DNS_TYPE_TXT 0x10
#define AVAHI_DNS_TYPE_AAAA 0x1C
#define AVAHI_DNS_TYPE_SRV 0x21
#define AVAHI_DNS_TYPE_NSEC 0x2F
#define AVAHI_DNS_TYPE_ANY 0xFF
#define AVAHI_DNS_CLASS_IN 1
#define AVAHI_DNS_CLASS_ANY 0xFF
#define AVAHI_IF_UNSPEC (-1)
#define AVAHI_PROTO_UNSPEC (-1)
typedef struct AvahiStringList { struct AvahiStringList *next; size_t size; uint8_t text[96]; } AvahiStringList;
typedef struct { const char *name; uint16_t clazz, type; } AvahiKey;
typedef struct { AvahiKey *key; uint32_t ttl; struct { struct { const char *name; } ptr, cname; struct { uint16_t port; const char *name; } srv;
	struct { struct { uint8_t address[16]; } address; } aaaa; } data; } AvahiRecord;
typedef struct AvahiCacheEntry { AvahiRecord *record; int cache_flush; struct AvahiCacheEntry *entry_next; } AvahiCacheEntry;
typedef struct AvahiCache { AvahiCacheEntry *entries; } AvahiCache;
typedef struct { const char *name; int index; } AvahiHwInterface;
typedef struct AvahiAnnouncer AvahiAnnouncer;
typedef struct AvahiInterface { AvahiHwInterface *hardware; struct AvahiInterface *interface_next; int protocol, announcing;
	AvahiCache *cache; AvahiAnnouncer *announcers; } AvahiInterface;
typedef struct { AvahiInterface *interfaces; } AvahiInterfaceMonitor;
typedef struct AvahiEntry { int dead, interface, protocol; AvahiAnnouncer *announcers; AvahiRecord *record;
	struct AvahiEntry *entries_next; } AvahiEntry;
typedef struct AvahiServer { struct { int enable_reflector, reflect_ipv; AvahiStringList *reflect_interfaces, *reflect_guest; char *reflect_core_types; } config;
	AvahiInterfaceMonitor *monitor; const char *host_name_fqdn; void *record_list; AvahiEntry *entries;
	struct RgSeen *reaper_rg_seen; } AvahiServer;
struct AvahiAnnouncer { AvahiServer *server; AvahiInterface *interface; AvahiEntry *entry; void *time_event;
	AvahiAnnouncer *by_interface_next, *by_interface_prev, *by_entry_next, *by_entry_prev; };
#define AVAHI_LLIST_PREPEND(t, name, head, item) do { (item)->name##_next = (head); (item)->name##_prev = NULL; (head) = (item); } while (0)
#define avahi_new(type, n) ((type*) calloc((n), sizeof(type)))
#define AVAHI_GCC_UNUSED __attribute__ ((unused))
#define avahi_new0(type, n) ((type*) calloc((n), sizeof(type)))
#define avahi_free free
#define avahi_strdup strdup
static AvahiKey *avahi_key_new(const char *n, uint16_t c, uint16_t t) { AvahiKey *k = calloc(1, sizeof(*k)); k->name = n; k->clazz = c; k->type = t; return k; }
static void avahi_key_unref(AvahiKey *k) { free(k); }
static int nz_eq(const char *a, const char *b) { return (!a && !b) || (a && b && !strcasecmp(a, b)); }
static int avahi_record_equal_no_ttl(const AvahiRecord *a, const AvahiRecord *b)
{ return !strcasecmp(a->key->name, b->key->name) && a->key->type == b->key->type && a->key->clazz == b->key->clazz
	&& nz_eq(a->data.ptr.name, b->data.ptr.name) && nz_eq(a->data.srv.name, b->data.srv.name); }
static char LOG[8192];
static void logf_(const char *fmt, ...) { va_list ap; size_t l = strlen(LOG); va_start(ap, fmt); vsnprintf(LOG + l, sizeof(LOG) - l, fmt, ap); va_end(ap); }
static void avahi_log_error(const char *fmt, ...) { (void) fmt; }
static void avahi_log_warn(const char *fmt, ...) { (void) fmt; logf_("warn "); }
static int avahi_domain_equal(const char *a, const char *b) { return strcasecmp(a, b) == 0; }
static void avahi_interface_post_response(AvahiInterface *j, AvahiRecord *r, int f, void *a, int im)
{ (void) a; (void) im; logf_("resp:%s:%s%s ", j->hardware->name, r->key->name, f ? "!" : ""); }
static void avahi_interface_post_probe(AvahiInterface *j, AvahiRecord *r, int im) { (void) im; logf_("probe:%s:%s ", j->hardware->name, r->key->name); }
static void avahi_interface_post_query(AvahiInterface *j, AvahiKey *k, int im, void *a) { (void) im; (void) a; logf_("query:%s:%s ", j->hardware->name, k->name); }
static void avahi_record_list_push(void *l, AvahiRecord *r, int f, int u, int a) { (void) l; (void) u; (void) a; logf_("ans:%s/%d%s ", r->key->name, r->key->type, f ? "!" : ""); }
typedef void *(*walk_cb)(AvahiCache *, AvahiKey *, AvahiCacheEntry *, void *);
static void *avahi_cache_walk(AvahiCache *c, AvahiKey *k, walk_cb cb, void *ud)
{ AvahiCacheEntry *e; void *ret; for (e = c->entries; e; e = e->entry_next)
	if (!strcasecmp(e->record->key->name, k->name) && (k->type == AVAHI_DNS_TYPE_ANY || k->type == e->record->key->type))
		if ((ret = cb(c, k, e, ud))) return ret;
  return NULL; }
static int avahi_interface_match(AvahiInterface *i, int idx, int proto) { (void) i; (void) idx; (void) proto; return 1; }
static int avahi_entry_is_commited(AvahiEntry *e) { (void) e; return 1; }
static AvahiAnnouncer *get_announcer(AvahiServer *s, AvahiEntry *e, AvahiInterface *i)
{ AvahiAnnouncer *a; (void) s; for (a = e->announcers; a; a = a->by_entry_next) if (a->interface == i) return a; return NULL; }
static void go_to_initial_state(AvahiAnnouncer *a) { (void) a; }

@@IFACE_OK@@
@@BLOCK@@
@@CWALK@@
@@RGWALK@@
@@RESP@@
@@QUERY@@
@@PROBE@@
@@ANN@@
@@NTYPE@@
@@NENTRY@@
@@NCORE@@

/* ---- fixtures ---- */
static AvahiStringList *sl(const char *t, AvahiStringList *next)
{ AvahiStringList *l = calloc(1, sizeof(*l)); l->next = next; l->size = strlen(t); memcpy(l->text, t, l->size); return l; }
static AvahiRecord *rec(const char *name, int type, const char *target)
{ AvahiRecord *r = calloc(1, sizeof(*r)); r->key = calloc(1, sizeof(AvahiKey)); r->key->name = name; r->key->clazz = AVAHI_DNS_CLASS_IN;
  r->key->type = type; r->ttl = 120; if (type == AVAHI_DNS_TYPE_SRV) r->data.srv.name = target; else r->data.ptr.name = target; return r; }
static AvahiKey *key(const char *name, int type) { AvahiKey *k = calloc(1, sizeof(*k)); k->name = name; k->clazz = AVAHI_DNS_CLASS_IN; k->type = type; return k; }
static void cput(AvahiCache *c, AvahiRecord *r) { AvahiCacheEntry *e = calloc(1, sizeof(*e)); AvahiCacheEntry **p = &c->entries;
  e->record = r; e->cache_flush = r->key->type != AVAHI_DNS_TYPE_PTR; while (*p) p = &(*p)->entry_next; *p = e; }
/* a record this router publishes itself */
static AvahiServer S;
static void local(const char *name, int type, const char *target)
{ AvahiEntry *e = calloc(1, sizeof(*e)); e->record = rec(name, type, target); if (type == AVAHI_DNS_TYPE_CNAME) e->record->data.cname.name = target;
  e->entries_next = S.entries; S.entries = e; }
static void locals(void)
{ local("RT-BE96U.local", AVAHI_DNS_TYPE_A, NULL);
  local("findasus.local", AVAHI_DNS_TYPE_CNAME, "RT-BE96U.local");			/* static-aliases / rc aliases */
  local("Router Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "RT-BE96U.local");	/* a service the router publishes */
  local("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Router Printer._ipp._tcp.local");
  local("_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR, "_ipp._tcp.local"); }
#define NI 5
static const char *NAMES[NI] = { "br0", "br53", "br52", "br54", "br55" };	/* core, core (intranet), guest A, guest B, neither */
static AvahiInterface IF[NI]; static AvahiHwInterface HW[NI]; static AvahiCache CA[NI]; static AvahiInterfaceMonitor MON;
static AvahiServer S;
static void setup(int core, int guest)
{ int n; memset(&S, 0, sizeof(S)); S.monitor = &MON; S.host_name_fqdn = "RT-BE96U.local"; S.config.enable_reflector = 1;
  for (n = 0; n < NI; n++) { HW[n].name = NAMES[n]; HW[n].index = n + 1; IF[n].hardware = &HW[n]; IF[n].cache = &CA[n];
	IF[n].protocol = 0; IF[n].announcing = 1; IF[n].announcers = NULL; IF[n].interface_next = n + 1 < NI ? &IF[n + 1] : NULL; }
  MON.interfaces = &IF[0];
  if (core) S.config.reflect_interfaces = sl("BR0", sl("br53", NULL));
  if (guest) S.config.reflect_guest = sl("br52:_ipp._tcp:_airplay._tcp", sl("br54:_googlecast._tcp", NULL)); }
static void fill_caches(void)
{ memset(CA, 0, sizeof(CA));
  /* main LAN: an office printer (ipp), a box that only does ipps, and an HINFO for the printer */
  cput(&CA[0], rec("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "office.local"));
  cput(&CA[0], rec("Box._ipps._tcp.local", AVAHI_DNS_TYPE_SRV, "box.local"));
  cput(&CA[0], rec("office.local", AVAHI_DNS_TYPE_A, NULL));
  cput(&CA[0], rec("office.local", AVAHI_DNS_TYPE_HINFO, NULL));
  cput(&CA[0], rec("box.local", AVAHI_DNS_TYPE_A, NULL));
  cput(&CA[0], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"));
  /* guest A: a printer, a speaker, a box pretending to be the router */
  cput(&CA[2], rec("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local"));
  cput(&CA[2], rec("Other._ipps._tcp.local", AVAHI_DNS_TYPE_SRV, "other.local"));
  cput(&CA[2], rec("TV._airplay._tcp.local", AVAHI_DNS_TYPE_SRV, "tv.local"));
  cput(&CA[2], rec("Evil._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "RT-BE96U.local"));
  cput(&CA[2], rec("Fake._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "office.local"));
  cput(&CA[2], rec("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "evil.local"));
  cput(&CA[2], rec("x._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "findasus.local"));		/* review 2026-11-19: login phishing */
  cput(&CA[2], rec("Office2._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "office2.local"));	/* a main name aged out of br0's cache */
  cput(&CA[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"));	/* the guest printer's own PTR */
  /* guest B: a Chromecast */
  cput(&CA[3], rec("_googlecast._tcp.local", AVAHI_DNS_TYPE_PTR, "Cast._googlecast._tcp.local")); }
#define OUT(label, v) printf("%s=%d\n", label, (int) (v))
#define FLOW(label, stmt) do { LOG[0] = 0; stmt; printf("%s=%s\n", label, LOG); } while (0)
static int rr(const char *types, const char *name, int type, const char *target, AvahiCache *c)
{ return rg_record_ok(types, rec(name, type, target), c, S.host_name_fqdn); }

int main(void)
{
	const char *T = "_ipp._tcp:_airplay._tcp", *gt;
	AvahiCache *G = &CA[2];
	int a, b, n;
	AvahiRecord *r;
	AvahiEntry e;

	/* ---- pair matrix: reflect-interfaces br0,br53 + reflect-guest br52, br54 ---- */
	setup(1, 1); fill_caches(); locals();
	for (a = 0; a < NI; a++) for (b = 0; b < NI; b++) if (a != b) {
		char l[64]; n = reflect_pair_ok(&S, &IF[a], &IF[b], &gt);
		snprintf(l, sizeof(l), "pair.%s.%s", NAMES[a], NAMES[b]); printf("%s=%d:%s\n", l, n, gt ? gt : "-"); }
	for (a = 0; a < NI; a++) { char l[64]; snprintf(l, sizeof(l), "side.%s", NAMES[a]); OUT(l, reflect_side_ok(&S, &IF[a])); }

	/* ---- record filter (source = guest A cache) ---- */
	OUT("r.ptr.ipp", rr(T, "_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local", G));
	OUT("r.ptr.ipps", rr(T, "_ipps._tcp.local", AVAHI_DNS_TYPE_PTR, "Other._ipps._tcp.local", G));
	OUT("r.ptr.ipp_to_ipps", rr(T, "_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Other._ipps._tcp.local", G));
	OUT("r.ptr.enum.ipp", rr(T, "_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR, "_ipp._tcp.local", G));
	OUT("r.ptr.enum.ipps", rr(T, "_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR, "_ipps._tcp.local", G));
	OUT("r.ptr.enum.instance", rr(T, "_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local", G));
	OUT("r.ptr.subtype", rr(T, "_universal._sub._ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local", G));
	OUT("r.ptr.reverse", rr(T, "7.1.168.192.in-addr.arpa", AVAHI_DNS_TYPE_PTR, "printer.local", G));
	OUT("r.srv.ipp", rr(T, "Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.srv.ipps", rr(T, "Other._ipps._tcp.local", AVAHI_DNS_TYPE_SRV, "other.local", G));
	OUT("r.srv.bare_type", rr(T, "_ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.srv.case", rr(T, "PRINTER._IPP._TCP.LOCAL", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.srv.nodot", rr(T, "x_ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.srv.emptylabel", rr(T, "._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.srv.escaped_dot", rr(T, "Evil\\._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.srv.escaped_backslash", rr(T, "Evil\\\\._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.srv.notlocal", rr(T, "Printer._ipp._tcp.example.com", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	OUT("r.txt.ipp", rr(T, "Printer._ipp._tcp.local", AVAHI_DNS_TYPE_TXT, NULL, G));
	OUT("r.txt.airplay", rr(T, "TV._airplay._tcp.local", AVAHI_DNS_TYPE_TXT, NULL, G));
	OUT("r.txt.raop", rr(T, "TV._raop._tcp.local", AVAHI_DNS_TYPE_TXT, NULL, G));
	OUT("r.a.allowed_host", rr(T, "printer.local", AVAHI_DNS_TYPE_A, NULL, G));
	OUT("r.aaaa.allowed_host", rr(T, "printer.local", AVAHI_DNS_TYPE_AAAA, NULL, G));
	OUT("r.a.tv", rr(T, "tv.local", AVAHI_DNS_TYPE_A, NULL, G));
	OUT("r.a.ipps_host", rr(T, "other.local", AVAHI_DNS_TYPE_A, NULL, G));
	OUT("r.a.stranger", rr(T, "stranger.local", AVAHI_DNS_TYPE_A, NULL, G));
	OUT("r.a.other_cache", rr(T, "printer.local", AVAHI_DNS_TYPE_A, NULL, &CA[0]));
	OUT("r.a.router_name", rr(T, "rt-be96u.local", AVAHI_DNS_TYPE_A, NULL, G));
	OUT("r.hinfo", rr(T, "printer.local", AVAHI_DNS_TYPE_HINFO, NULL, G));
	OUT("r.nsec", rr(T, "Printer._ipp._tcp.local", AVAHI_DNS_TYPE_NSEC, NULL, G));
	OUT("r.cname", rr(T, "Printer._ipp._tcp.local", AVAHI_DNS_TYPE_CNAME, NULL, G));
	r = rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"); r->key->clazz = AVAHI_DNS_CLASS_ANY;
	OUT("r.class_any", rg_record_ok(T, r, G, S.host_name_fqdn));
	OUT("r.empty_types", rr("", "Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));

	/* ---- query filter (answering = guest A cache) ---- */
	OUT("k.ptr.ipp", rg_key_ok(T, key("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR), G));
	OUT("k.ptr.ipps", rg_key_ok(T, key("_ipps._tcp.local", AVAHI_DNS_TYPE_PTR), G));
	OUT("k.ptr.enum", rg_key_ok(T, key("_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR), G));
	OUT("k.any.enum", rg_key_ok(T, key("_services._dns-sd._udp.local", AVAHI_DNS_TYPE_ANY), G));
	OUT("k.srv.enum", rg_key_ok(T, key("_services._dns-sd._udp.local", AVAHI_DNS_TYPE_SRV), G));
	OUT("k.srv.instance", rg_key_ok(T, key("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV), G));
	OUT("k.any.instance", rg_key_ok(T, key("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_ANY), G));
	OUT("k.a.host", rg_key_ok(T, key("printer.local", AVAHI_DNS_TYPE_A), G));
	OUT("k.aaaa.host", rg_key_ok(T, key("printer.local", AVAHI_DNS_TYPE_AAAA), G));
	OUT("k.any.host", rg_key_ok(T, key("printer.local", AVAHI_DNS_TYPE_ANY), G));
	OUT("k.hinfo.host", rg_key_ok(T, key("printer.local", AVAHI_DNS_TYPE_HINFO), G));
	OUT("k.a.ipps_host", rg_key_ok(T, key("other.local", AVAHI_DNS_TYPE_A), G));
	OUT("k.a.stranger", rg_key_ok(T, key("stranger.local", AVAHI_DNS_TYPE_A), G));
	OUT("k.ptr.reverse", rg_key_ok(T, key("7.1.168.192.in-addr.arpa", AVAHI_DNS_TYPE_PTR), G));

	/* ---- whole reflect paths ---- */
	FLOW("f.resp.guest_ipp", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"), 0));
	FLOW("f.resp.guest_ipps", reflect_response(&S, &IF[2], rec("_ipps._tcp.local", AVAHI_DNS_TYPE_PTR, "Other._ipps._tcp.local"), 0));
	FLOW("f.resp.guest_a", reflect_response(&S, &IF[2], rec("printer.local", AVAHI_DNS_TYPE_A, NULL), 0));
	FLOW("f.resp.guest_a_other", reflect_response(&S, &IF[2], rec("other.local", AVAHI_DNS_TYPE_A, NULL), 0));
	FLOW("f.resp.guest_hinfo", reflect_response(&S, &IF[2], rec("printer.local", AVAHI_DNS_TYPE_HINFO, NULL), 0));
	FLOW("f.resp.core_ipp", reflect_response(&S, &IF[0], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"), 0));
	FLOW("f.resp.core_hinfo", reflect_response(&S, &IF[0], rec("office.local", AVAHI_DNS_TYPE_HINFO, NULL), 0));
	FLOW("f.resp.core_cast", reflect_response(&S, &IF[0], rec("_googlecast._tcp.local", AVAHI_DNS_TYPE_PTR, "Cast._googlecast._tcp.local"), 0));
	FLOW("f.resp.neither", reflect_response(&S, &IF[4], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "X._ipp._tcp.local"), 0));
	FLOW("f.query.guest_ipp", reflect_query(&S, &IF[2], key("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR)));
	FLOW("f.query.guest_ipps", reflect_query(&S, &IF[2], key("_ipps._tcp.local", AVAHI_DNS_TYPE_PTR)));
	FLOW("f.query.guest_any_host", reflect_query(&S, &IF[2], key("office.local", AVAHI_DNS_TYPE_ANY)));
	FLOW("f.query.guest_a_box", reflect_query(&S, &IF[2], key("box.local", AVAHI_DNS_TYPE_A)));
	FLOW("f.query.core_cast", reflect_query(&S, &IF[0], key("_googlecast._tcp.local", AVAHI_DNS_TYPE_PTR)));
	FLOW("f.query.guestB_ipp", reflect_query(&S, &IF[3], key("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR)));
	FLOW("f.probe.guest_srv", reflect_probe(&S, &IF[2], rec("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local")));
	FLOW("f.probe.guest_a_new", reflect_probe(&S, &IF[2], rec("newhost.local", AVAHI_DNS_TYPE_A, NULL)));
	/* name takeover: a guest's A for the office printer's host, its SRV for the printer's instance name */
	FLOW("f.claim.a", reflect_response(&S, &IF[2], rec("office.local", AVAHI_DNS_TYPE_A, NULL), 1));
	FLOW("f.claim.srv", reflect_response(&S, &IF[2], rec("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "evil.local"), 1));
	FLOW("f.claim.probe", reflect_probe(&S, &IF[2], rec("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "evil.local")));
	FLOW("f.claim.ptr", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Fake._ipp._tcp.local"), 0));
	FLOW("f.claim.walk", reflect_query(&S, &IF[0], key("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV)));
	FLOW("f.claim.core_to_guest", reflect_response(&S, &IF[0], rec("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "office.local"), 1));
	/* review 2026-11-19: router-published names and the cache-flush bit */
	FLOW("f.local.findasus_srv", reflect_response(&S, &IF[2], rec("x._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "findasus.local"), 1));
	FLOW("f.local.findasus_a", reflect_response(&S, &IF[2], rec("FINDASUS.local", AVAHI_DNS_TYPE_A, NULL), 1));
	FLOW("f.local.service_srv", reflect_response(&S, &IF[2], rec("Router Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "evil.local"), 1));
	FLOW("f.local.service_txt", reflect_response(&S, &IF[2], rec("Router Printer._ipp._tcp.local", AVAHI_DNS_TYPE_TXT, NULL), 1));
	FLOW("f.local.ptr_target", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Router Printer._ipp._tcp.local"), 0));
	FLOW("f.local.probe", reflect_probe(&S, &IF[2], rec("x._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "findasus.local")));
	FLOW("f.local.walk", reflect_query(&S, &IF[0], key("x._ipp._tcp.local", AVAHI_DNS_TYPE_SRV)));
	FLOW("f.local.enum", reflect_response(&S, &IF[2], rec("_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR, "_ipp._tcp.local"), 0));
	FLOW("f.flush.aged_a", reflect_response(&S, &IF[2], rec("office2.local", AVAHI_DNS_TYPE_A, NULL), 1));
	FLOW("f.flush.guest_srv", reflect_response(&S, &IF[2], rec("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local"), 1));
	FLOW("f.flush.walk", reflect_query(&S, &IF[0], key("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV)));
	/* review R1: goodbyes from a guest */
	r = rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"); r->ttl = 0;
	FLOW("g.main_printer_goodbye", reflect_response(&S, &IF[2], r, 0));
	FLOW("g.main_printer_ptr", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"), 0));
	r = rec("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local"); r->ttl = 0;
	FLOW("g.own_srv_goodbye", reflect_response(&S, &IF[2], r, 1));
	r = rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"); r->ttl = 0;
	FLOW("g.own_ptr_goodbye", reflect_response(&S, &IF[2], r, 0));
	r = rec("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "elsewhere.local"); r->ttl = 0;
	FLOW("g.goodbye_not_identical", reflect_response(&S, &IF[2], r, 1));
	r = rec("office2.local", AVAHI_DNS_TYPE_A, NULL); r->ttl = 0;
	FLOW("g.expired_main_a_goodbye", reflect_response(&S, &IF[2], r, 1));
	/* review R2: a main name that left the router's cache (seen-set) */
	cput(&CA[2], rec("NAS._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "nas.local"));
	FLOW("s.before", reflect_response(&S, &IF[2], rec("nas.local", AVAHI_DNS_TYPE_A, NULL), 1));
	rg_seen_note(&S, &IF[0], rec("NAS.local", AVAHI_DNS_TYPE_A, NULL));	/* seen on br0 earlier, no longer cached there */
	FLOW("s.after_a", reflect_response(&S, &IF[2], rec("nas.local", AVAHI_DNS_TYPE_A, NULL), 1));
	FLOW("s.after_srv_target", reflect_response(&S, &IF[2], rec("NAS._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "nas.local"), 1));
	rg_seen_note(&S, &IF[1], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Lobby._ipp._tcp.local"));
	FLOW("s.ptr_target", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Lobby._ipp._tcp.local"), 0));
	rg_seen_note(&S, &IF[1], rec("Desk._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "desk.local"));
	OUT("s.srv_both_names", rg_seen_has(&S, "desk._ipp._tcp.local") && rg_seen_has(&S, "DESK.local"));
	rg_seen_note(&S, &IF[2], rec("guestbox.local", AVAHI_DNS_TYPE_A, NULL));
	OUT("s.guest_not_noted", rg_seen_has(&S, "guestbox.local"));
	FLOW("s.allowed_still", reflect_response(&S, &IF[2], rec("Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local"), 1));
	/* the set: bounded, FIFO, case-insensitive, freed; nothing without reflect-guest or from a non-core interface */
	setup(1, 1);
	for (n = 0; n < 600; n++) { char *h = malloc(32); snprintf(h, 32, "H%d.local", n); rg_seen_note(&S, &IF[1], rec(h, AVAHI_DNS_TYPE_A, NULL)); }
	{ unsigned k, used = 0; for (k = 0; k < RG_SEEN_MAX; k++) used += S.reaper_rg_seen->name[k] != NULL; printf("cap.used=%u\n", used); }
	OUT("cap.h0", rg_seen_has(&S, "h0.local")); OUT("cap.h87", rg_seen_has(&S, "h87.local"));
	OUT("cap.h88", rg_seen_has(&S, "h88.local")); OUT("cap.h599", rg_seen_has(&S, "H599.LOCAL"));
	a = (int) S.reaper_rg_seen->next; rg_seen_note(&S, &IF[1], rec("h599.local", AVAHI_DNS_TYPE_A, NULL));
	OUT("cap.dup_kept_once", S.reaper_rg_seen->next == (unsigned) a);
	printf("cap.newest=%s\n", S.reaper_rg_seen->name[(S.reaper_rg_seen->next + RG_SEEN_MAX - 1) % RG_SEEN_MAX]);
	rg_seen_free(&S); OUT("cap.freed", S.reaper_rg_seen == NULL);
	rg_seen_note(&S, &IF[4], rec("x.local", AVAHI_DNS_TYPE_A, NULL)); OUT("cap.neither_no_alloc", S.reaper_rg_seen == NULL);
	setup(1, 0); rg_seen_note(&S, &IF[0], rec("x.local", AVAHI_DNS_TYPE_A, NULL)); OUT("cap.unset_no_alloc", S.reaper_rg_seen == NULL);
	setup(1, 1); fill_caches(); locals();
	S.config.reflect_ipv = 0; IF[1].protocol = 1;
	FLOW("f.resp.other_protocol", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"), 0));
	IF[1].protocol = 0;
	S.config.enable_reflector = 0;
	FLOW("f.resp.reflector_off", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"), 0));
	S.config.enable_reflector = 1;

	/* ---- the router's own records: announcers per interface ---- */
	memset(&e, 0, sizeof(e)); e.interface = AVAHI_IF_UNSPEC; e.protocol = AVAHI_PROTO_UNSPEC;
	for (a = 0; a < NI; a++) new_announcer(&S, &IF[a], &e);
	LOG[0] = 0; for (a = 0; a < NI; a++) if (IF[a].announcers) logf_("%s ", NAMES[a]); printf("ann.guest_set=%s\n", LOG);
	setup(1, 0);
	memset(&e, 0, sizeof(e)); e.interface = AVAHI_IF_UNSPEC; e.protocol = AVAHI_PROTO_UNSPEC;
	for (a = 0; a < NI; a++) new_announcer(&S, &IF[a], &e);
	LOG[0] = 0; for (a = 0; a < NI; a++) if (IF[a].announcers) logf_("%s ", NAMES[a]); printf("ann.guest_unset=%s\n", LOG);

	/* ---- unset = old behaviour: pair == reflect_iface_ok on both ends, unfiltered; side == reflect_iface_ok ---- */
	for (n = 0; n < 2; n++) {
		int bad = 0; setup(n, 0); fill_caches();
		for (a = 0; a < NI; a++) {
			if (reflect_side_ok(&S, &IF[a]) != reflect_iface_ok(&S, &IF[a])) bad++;
			for (b = 0; b < NI; b++) if (a != b) {
				int p = reflect_pair_ok(&S, &IF[a], &IF[b], &gt);
				if (p != (reflect_iface_ok(&S, &IF[a]) && reflect_iface_ok(&S, &IF[b])) || gt) bad++; } }
		printf("unset.equiv%d=%d\n", n, bad);
	}
	setup(1, 0); fill_caches();
	FLOW("unset.resp.core_hinfo", reflect_response(&S, &IF[0], rec("office.local", AVAHI_DNS_TYPE_HINFO, NULL), 0));
	FLOW("unset.resp.br52", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"), 0));
	FLOW("unset.query.core_any", reflect_query(&S, &IF[1], key("office.local", AVAHI_DNS_TYPE_ANY)));
	setup(0, 0); fill_caches();
	FLOW("unset.stock.resp", reflect_response(&S, &IF[0], rec("office.local", AVAHI_DNS_TYPE_HINFO, NULL), 0));
	/* reflect-guest set, reflect-interfaces empty: no core, nothing crosses */
	setup(0, 1); fill_caches();
	FLOW("nocore.resp.br0", reflect_response(&S, &IF[0], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"), 0));
	FLOW("nocore.resp.br52", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"), 0));
	/* a name in both lists is a guest */
	setup(1, 0); S.config.reflect_guest = sl("br53:_ipp._tcp", NULL);
	n = reflect_pair_ok(&S, &IF[0], &IF[1], &gt); printf("both.pair=%d:%s\n", n, gt ? gt : "-");
	/* entry without types: a guest with nothing allowed */
	setup(1, 0); S.config.reflect_guest = sl("br52", NULL);
	n = reflect_pair_ok(&S, &IF[0], &IF[2], &gt); printf("notypes.pair=%d:[%s]\n", n, gt ? gt : "-");
	OUT("notypes.rec", rr(gt ? gt : "", "Printer._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "printer.local", G));
	/* br5 must not match the br52 entry (prefix) */
	setup(1, 1); HW[4].name = "br5";
	printf("prefix.guest=%s\n", avahi_reflect_guest_types(&S, &IF[4]) ? "yes" : "no");

	/* ---- reaper 2026-11-20: reflect-core-types - the main side relays only these types (guest lists unchanged) ---- */
	setup(1, 1); fill_caches(); locals(); S.config.reflect_core_types = (char *) "_ipp._tcp";
	n = reflect_pair_ok(&S, &IF[0], &IF[1], &gt); printf("ct.pair.core=%d:%s\n", n, gt ? gt : "-");
	n = reflect_pair_ok(&S, &IF[0], &IF[2], &gt); printf("ct.pair.guest=%d:%s\n", n, gt ? gt : "-");
	n = reflect_pair_ok(&S, &IF[2], &IF[3], &gt); printf("ct.pair.gg=%d:%s\n", n, gt ? gt : "-");
	FLOW("ct.resp.ipp", reflect_response(&S, &IF[0], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"), 0));
	FLOW("ct.resp.ipps", reflect_response(&S, &IF[0], rec("_ipps._tcp.local", AVAHI_DNS_TYPE_PTR, "Box._ipps._tcp.local"), 0));
	FLOW("ct.resp.cast", reflect_response(&S, &IF[0], rec("_googlecast._tcp.local", AVAHI_DNS_TYPE_PTR, "Cast._googlecast._tcp.local"), 0));
	FLOW("ct.resp.srv", reflect_response(&S, &IF[0], rec("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "office.local"), 1));
	FLOW("ct.resp.a_allowed", reflect_response(&S, &IF[0], rec("office.local", AVAHI_DNS_TYPE_A, NULL), 1));
	FLOW("ct.resp.aaaa_allowed", reflect_response(&S, &IF[0], rec("office.local", AVAHI_DNS_TYPE_AAAA, NULL), 1));
	FLOW("ct.resp.a_other", reflect_response(&S, &IF[0], rec("box.local", AVAHI_DNS_TYPE_A, NULL), 1));
	FLOW("ct.resp.hinfo", reflect_response(&S, &IF[0], rec("office.local", AVAHI_DNS_TYPE_HINFO, NULL), 0));
	FLOW("ct.resp.enum_ipp", reflect_response(&S, &IF[0], rec("_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR, "_ipp._tcp.local"), 0));
	FLOW("ct.resp.enum_cast", reflect_response(&S, &IF[0], rec("_services._dns-sd._udp.local", AVAHI_DNS_TYPE_PTR, "_googlecast._tcp.local"), 0));
	FLOW("ct.query.ipp", reflect_query(&S, &IF[1], key("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR)));
	FLOW("ct.query.ipps", reflect_query(&S, &IF[1], key("_ipps._tcp.local", AVAHI_DNS_TYPE_PTR)));
	FLOW("ct.query.any_office", reflect_query(&S, &IF[1], key("office.local", AVAHI_DNS_TYPE_ANY)));
	FLOW("ct.query.a_box", reflect_query(&S, &IF[1], key("box.local", AVAHI_DNS_TYPE_A)));
	FLOW("ct.probe.other", reflect_probe(&S, &IF[0], rec("Box._ipps._tcp.local", AVAHI_DNS_TYPE_SRV, "box.local")));
	FLOW("ct.probe.ipp", reflect_probe(&S, &IF[0], rec("Office._ipp._tcp.local", AVAHI_DNS_TYPE_SRV, "office.local")));
	FLOW("ct.guest.ipp", reflect_response(&S, &IF[2], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Printer._ipp._tcp.local"), 0));
	FLOW("ct.guest.airplay", reflect_response(&S, &IF[2], rec("TV._airplay._tcp.local", AVAHI_DNS_TYPE_SRV, "tv.local"), 1));
	memset(&e, 0, sizeof(e)); e.interface = AVAHI_IF_UNSPEC; e.protocol = AVAHI_PROTO_UNSPEC;
	for (a = 0; a < NI; a++) new_announcer(&S, &IF[a], &e);
	LOG[0] = 0; for (a = 0; a < NI; a++) if (IF[a].announcers) logf_("%s ", NAMES[a]); printf("ct.ann=%s\n", LOG);
	/* without guests too, and an empty list (a value with no valid type) relays nothing between the core */
	setup(1, 0); fill_caches(); S.config.reflect_core_types = (char *) "_ipp._tcp";
	FLOW("ct.noguest.ipp", reflect_response(&S, &IF[0], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"), 0));
	FLOW("ct.noguest.hinfo", reflect_response(&S, &IF[0], rec("office.local", AVAHI_DNS_TYPE_HINFO, NULL), 0));
	S.config.reflect_core_types = (char *) "";
	FLOW("ct.empty.ipp", reflect_response(&S, &IF[0], rec("_ipp._tcp.local", AVAHI_DNS_TYPE_PTR, "Office._ipp._tcp.local"), 0));
	{
		static const char *cin[] = { "_ipp._tcp:_IPPS._tcp", "", "junk", ":_ipp._tcp::_x._sctp:", "_airplay._tcp", NULL };
		char many[2048]; int k;
		for (k = 0; cin[k]; k++) { char *o; LOG[0] = 0; o = reaper_core_types(cin[k]); printf("cnorm%d=%s|%s\n", k, o ? o : "(null)", LOG); free(o); }
		many[0] = 0;
		for (k = 0; k < 40; k++) sprintf(many + strlen(many), "%s_t%d._tcp", k ? ":" : "", k);
		{ char *o = reaper_core_types(many); int c = 0; const char *q; for (q = o; q && *q; q++) c += *q == ':'; printf("cnorm.cap=%d\n", c + 1); free(o); }
	}

	/* ---- main.c normaliser ---- */
	{
		static const char *in[] = { "br52:_ipp._tcp:_IPPS._tcp", "br52:_ipp._tcp:junk:_x._sctp:_a b._tcp:", "br52", "", ":_ipp._tcp",
			"br 5:_ipp._tcp", "br0123456789abcd:_ipp._tcp", "br0123456789abc:_hap._udp", "br52:_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa._tcp",
			"br52:_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa._tcp", "br52:ipp._tcp:_._tcp:_ipp._tcpx", NULL };
		char many[2048]; int k;
		for (k = 0; in[k]; k++) { char *o; LOG[0] = 0; o = reaper_rg_entry(in[k]); printf("norm%d=%s|%s\n", k, o ? o : "(null)", LOG); free(o); }
		strcpy(many, "br52");
		for (k = 0; k < 40; k++) sprintf(many + strlen(many), ":_t%d._tcp", k);
		{ char *o = reaper_rg_entry(many); int c = 0; const char *p; for (p = o; p && *p; p++) c += *p == ':'; printf("norm.cap=%d\n", c); free(o); }
	}
	return 0;
}
'''

with tempfile.TemporaryDirectory() as td:
    if not missing:
        src = HARNESS
        for k, v in parts.items():
            src = src.replace("@@%s@@" % k, v)
        c, exe = os.path.join(td, "g.c"), os.path.join(td, "g")
        open(c, "w").write(src)
        rr = subprocess.run([CC, "-std=gnu99", "-Wall", "-Wextra", "-Wshadow", "-Werror", "-Wno-unused-function",
                             "-Wno-unused-parameter", "-o", exe, c], capture_output=True, text=True)
        check("the patched avahi code compiles on the host (-Wall -Wextra -Wshadow -Werror)", rr.returncode == 0, rr.stderr)
        if rr.returncode == 0:
            pr = subprocess.run([exe], capture_output=True, text=True)
            check("the harness ran", pr.returncode == 0, pr.stderr)
            o = dict(l.split("=", 1) for l in pr.stdout.strip().split("\n") if "=" in l)
            T, C = "_ipp._tcp:_airplay._tcp", "_googlecast._tcp"
            # pair matrix
            exp = {("br0", "br53"): "1:-", ("br53", "br0"): "1:-",
                   ("br0", "br52"): "1:" + T, ("br52", "br0"): "1:" + T, ("br53", "br52"): "1:" + T, ("br52", "br53"): "1:" + T,
                   ("br0", "br54"): "1:" + C, ("br54", "br0"): "1:" + C, ("br53", "br54"): "1:" + C, ("br54", "br53"): "1:" + C}
            bad = []
            names = ["br0", "br53", "br52", "br54", "br55"]
            for a in names:
                for b in names:
                    if a != b and o.get("pair.%s.%s" % (a, b)) != exp.get((a, b), "0:-"):
                        bad.append("%s->%s=%s" % (a, b, o.get("pair.%s.%s" % (a, b))))
            check("pairs: core<->core unfiltered (names case-insensitive), core<->guest with THAT guest's types, guest<->guest and "
                  "an interface in neither list never", not bad, bad)
            check("the receiving end: core and guest take part, an interface in neither list does not",
                  [o.get("side." + n) for n in names] == ["1", "1", "1", "1", "0"], [o.get("side." + n) for n in names])
            want = {"r.ptr.ipp": "1", "r.ptr.ipps": "0", "r.ptr.ipp_to_ipps": "0", "r.ptr.enum.ipp": "1", "r.ptr.enum.ipps": "0",
                    "r.ptr.enum.instance": "0", "r.ptr.subtype": "1", "r.ptr.reverse": "0"}
            check("PTR: an allowed type's instance passes; _ipp never matches _ipps; the enumeration PTR by its target type; "
                  "a subtype PTR passes; a reverse PTR does not", all(o.get(k) == v for k, v in want.items()),
                  {k: o.get(k) for k in want})
            want = {"r.srv.ipp": "1", "r.srv.ipps": "0", "r.srv.bare_type": "0", "r.srv.case": "1", "r.srv.nodot": "0",
                    "r.srv.emptylabel": "0", "r.srv.escaped_dot": "0", "r.srv.escaped_backslash": "1", "r.srv.notlocal": "0",
                    "r.txt.ipp": "1", "r.txt.airplay": "1", "r.txt.raop": "0"}
            check("SRV / TXT: an instance of an allowed type, anchored at an unescaped dot, case-insensitive, .local only",
                  all(o.get(k) == v for k, v in want.items()), {k: o.get(k) for k in want})
            want = {"r.a.allowed_host": "1", "r.aaaa.allowed_host": "1", "r.a.tv": "1", "r.a.ipps_host": "0", "r.a.stranger": "0",
                    "r.a.other_cache": "0", "r.a.router_name": "0"}
            check("A / AAAA: only a host an allowed SRV in the SOURCE cache points at; never the router's own name",
                  all(o.get(k) == v for k, v in want.items()), {k: o.get(k) for k in want})
            want = {"r.hinfo": "0", "r.nsec": "0", "r.cname": "0", "r.class_any": "0", "r.empty_types": "0"}
            check("everything else (HINFO, NSEC, CNAME, a non-IN class, a guest with no types) does not cross",
                  all(o.get(k) == v for k, v in want.items()), {k: o.get(k) for k in want})
            want = {"k.ptr.ipp": "1", "k.ptr.ipps": "0", "k.ptr.enum": "1", "k.any.enum": "1", "k.srv.enum": "0",
                    "k.srv.instance": "1", "k.any.instance": "1", "k.a.host": "1", "k.aaaa.host": "1", "k.any.host": "1",
                    "k.hinfo.host": "0", "k.a.ipps_host": "0", "k.a.stranger": "0", "k.ptr.reverse": "0"}
            check("queries: an allowed type / instance / enumeration, A / AAAA / ANY for an allowed host only",
                  all(o.get(k) == v for k, v in want.items()), {k: o.get(k) for k in want})
            fl = {
                "f.resp.guest_ipp": "resp:br0:_ipp._tcp.local resp:br53:_ipp._tcp.local ",
                "f.resp.guest_ipps": "",
                "f.resp.guest_a": "resp:br0:printer.local resp:br53:printer.local ",
                "f.resp.guest_a_other": "",
                "f.resp.guest_hinfo": "",
                "f.resp.core_ipp": "resp:br53:_ipp._tcp.local resp:br52:_ipp._tcp.local ",
                "f.resp.core_hinfo": "resp:br53:office.local ",
                "f.resp.core_cast": "resp:br53:_googlecast._tcp.local resp:br54:_googlecast._tcp.local ",
                "f.resp.neither": "",
            }
            check("reflect_response: a guest's allowed records reach the core only (never back, never guest B, never br55); "
                  "core records reach a guest only through its types; core<->core unfiltered",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {
                "f.query.guest_ipp": "query:br0:_ipp._tcp.local ans:_ipp._tcp.local/12 query:br53:_ipp._tcp.local ",
                "f.query.guest_ipps": "",
                "f.query.guest_any_host": "query:br0:office.local ans:office.local/1! ",
                "f.query.guest_a_box": "",
                "f.query.core_cast": "query:br53:_googlecast._tcp.local query:br54:_googlecast._tcp.local ans:_googlecast._tcp.local/12 ",
                "f.query.guestB_ipp": "",
            }
            check("reflect_query: a guest's allowed question goes to the core; the cache answer is filtered (A yes, HINFO no); "
                  "a host question only where an allowed SRV points at it; guest B never reaches guest A",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"f.probe.guest_srv": "probe:br0:Printer._ipp._tcp.local probe:br53:Printer._ipp._tcp.local ",
                  "f.probe.guest_a_new": "", "f.resp.other_protocol": "resp:br0:_ipp._tcp.local ", "f.resp.reflector_off": ""}
            fl = {"f.claim.a": "", "f.claim.srv": "", "f.claim.probe": "",
                  "f.claim.ptr": "resp:br0:_ipp._tcp.local resp:br53:_ipp._tcp.local ",
                  "f.claim.walk": "query:br53:Office._ipp._tcp.local query:br52:Office._ipp._tcp.local ",
                  "f.claim.core_to_guest": "resp:br53:Office._ipp._tcp.local! resp:br52:Office._ipp._tcp.local! "}
            check("no name takeover: a guest's A / SRV (announce, probe or cache answer) for a name a main-network device holds "
                  "stays on the guest side; shared PTRs and core -> guest are not affected",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"f.local.findasus_srv": "", "f.local.findasus_a": "", "f.local.service_srv": "", "f.local.service_txt": "",
                  "f.local.ptr_target": "", "f.local.probe": "",
                  "f.local.walk": "query:br53:x._ipp._tcp.local query:br52:x._ipp._tcp.local ",
                  "f.local.enum": "resp:br0:_services._dns-sd._udp.local resp:br53:_services._dns-sd._udp.local "}
            check("review 2026-11-19: from a guest, no record for a name the router publishes - findasus.local (SRV target "
                  "and A, any case), the router's own service instance (SRV / TXT / PTR target), not by probe nor from the "
                  "guest cache; a shared enumeration PTR still crosses", all(o.get(k) == v for k, v in fl.items()),
                  {k: o.get(k) for k in fl})
            fl = {"f.flush.aged_a": "resp:br0:office2.local resp:br53:office2.local ",
                  "f.flush.guest_srv": "resp:br0:Printer._ipp._tcp.local resp:br53:Printer._ipp._tcp.local ",
                  "f.flush.walk": "query:br53:Printer._ipp._tcp.local query:br52:Printer._ipp._tcp.local ans:Printer._ipp._tcp.local/33 "}
            check("review 2026-11-19: a guest's records reach the main network WITHOUT the cache-flush bit (an aged-out main "
                  "name cannot evict the real owner); allowed guest services still cross; main -> guest keeps the bit",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            ipp = "resp:br0:Printer._ipp._tcp.local resp:br53:Printer._ipp._tcp.local "
            fl = {"g.main_printer_goodbye": "", "g.main_printer_ptr": "", "g.own_srv_goodbye": ipp,
                  "g.own_ptr_goodbye": "resp:br0:_ipp._tcp.local resp:br53:_ipp._tcp.local ",
                  "g.goodbye_not_identical": "", "g.expired_main_a_goodbye": ""}
            check("review R1: a guest goodbye for a main printer (or a main name gone from the cache) does not cross, nor a "
                  "guest PTR naming a main instance; a guest's goodbye for its own cached record does",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"s.before": "resp:br0:nas.local resp:br53:nas.local ", "s.after_a": "", "s.after_srv_target": "",
                  "s.ptr_target": "", "s.srv_both_names": "1", "s.guest_not_noted": "0", "s.allowed_still": ipp}
            check("review R2: once nas.local was seen on the main network, a guest A for it or an SRV pointing at it does not "
                  "cross although it left the cache; seen PTR targets and SRV names / targets count; guest names are not noted",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"cap.used": "512", "cap.h0": "0", "cap.h87": "0", "cap.h88": "1", "cap.h599": "1", "cap.dup_kept_once": "1",
                  "cap.newest": "h599.local", "cap.freed": "1", "cap.neither_no_alloc": "1", "cap.unset_no_alloc": "1"}
            check("review R2: the seen-set holds at most 512 names, oldest replaced first (FIFO), stored lower-case, matched "
                  "case-insensitively, a repeat not stored twice, freed; nothing allocated without reflect-guest or from a "
                  "non-core interface", all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            check("reflect_probe filtered the same way; reflect-ipv and enable-reflector still apply",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            check("the router's own records: no announcer on a guest interface (so no announcement, no answer); every other "
                  "interface as before; with reflect-guest unset every interface",
                  o.get("ann.guest_set") == "br0 br53 br55 " and o.get("ann.guest_unset") == "br0 br53 br52 br54 br55 ",
                  (o.get("ann.guest_set"), o.get("ann.guest_unset")))
            check("reflect-guest unset = the old rule exactly: pair == reflect_iface_ok on both ends, never filtered, with and "
                  "without reflect-interfaces", o.get("unset.equiv0") == "0" and o.get("unset.equiv1") == "0",
                  (o.get("unset.equiv0"), o.get("unset.equiv1")))
            fl = {"unset.resp.core_hinfo": "resp:br53:office.local ", "unset.resp.br52": "",
                  "unset.query.core_any": "query:br0:office.local ans:office.local/1! ans:office.local/13! ",
                  "unset.stock.resp": "resp:br53:office.local resp:br52:office.local resp:br54:office.local resp:br55:office.local "}
            check("reflect-guest unset: the 2026-11-14 flows (core<->core everything, a non-listed network nothing; no lists = stock, every interface)",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            check("reflect-guest set with no reflect-interfaces: no core, nothing crosses",
                  o.get("nocore.resp.br0") == "" and o.get("nocore.resp.br52") == "", (o.get("nocore.resp.br0"), o.get("nocore.resp.br52")))
            check("an interface in both lists is a guest; an entry without types allows nothing; br5 is not br52",
                  o.get("both.pair") == "1:_ipp._tcp" and o.get("notypes.pair") == "1:[]" and o.get("notypes.rec") == "0"
                  and o.get("prefix.guest") == "no", (o.get("both.pair"), o.get("notypes.pair"), o.get("notypes.rec"), o.get("prefix.guest")))
            I, C2 = "_ipp._tcp", "_googlecast._tcp"
            fl = {"ct.pair.core": "1:" + I, "ct.pair.guest": "1:" + T, "ct.pair.gg": "0:-"}
            check("reflect-core-types: core<->core through the main list; core<->guest still THAT guest's list; guest<->guest never",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"ct.resp.ipp": "resp:br53:_ipp._tcp.local resp:br52:_ipp._tcp.local ",
                  "ct.resp.ipps": "",
                  "ct.resp.cast": "resp:br54:_googlecast._tcp.local ",
                  "ct.resp.srv": "resp:br53:Office._ipp._tcp.local! resp:br52:Office._ipp._tcp.local! ",
                  "ct.resp.a_allowed": "resp:br53:office.local! resp:br52:office.local! ",
                  "ct.resp.aaaa_allowed": "resp:br53:office.local! resp:br52:office.local! ",
                  "ct.resp.a_other": "", "ct.resp.hinfo": "",
                  "ct.resp.enum_ipp": "resp:br53:_services._dns-sd._udp.local resp:br52:_services._dns-sd._udp.local ",
                  "ct.resp.enum_cast": "resp:br54:_services._dns-sd._udp.local "}
            check("reflect-core-types _ipp._tcp: an allowed type's PTR / SRV / enumeration and the A / AAAA of the host its SRV "
                  "names cross core<->core (cache-flush kept); another type (_ipps never matches), another host's address, "
                  "HINFO do not; a guest still gets its own types (Cast for br54)",
                  all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"ct.query.ipp": "query:br0:_ipp._tcp.local ans:_ipp._tcp.local/12 query:br52:_ipp._tcp.local ans:_ipp._tcp.local/12 ",
                  "ct.query.ipps": "",
                  "ct.query.any_office": "query:br0:office.local ans:office.local/1! query:br52:office.local ",
                  "ct.query.a_box": "",
                  "ct.probe.other": "", "ct.probe.ipp": "probe:br53:Office._ipp._tcp.local probe:br52:Office._ipp._tcp.local "}
            check("reflect-core-types: questions and cache answers through the same list (ANY for an allowed host answers A, "
                  "not HINFO); probes too", all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"ct.guest.ipp": "resp:br0:_ipp._tcp.local resp:br53:_ipp._tcp.local ",
                  "ct.guest.airplay": "resp:br0:TV._airplay._tcp.local resp:br53:TV._airplay._tcp.local ",
                  "ct.ann": "br0 br53 br55 "}
            check("reflect-core-types leaves the guest lists alone (a guest's airplay still reaches the core) and the router's "
                  "own announcers as they were", all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            fl = {"ct.noguest.ipp": "resp:br53:_ipp._tcp.local ", "ct.noguest.hinfo": "", "ct.empty.ipp": ""}
            check("reflect-core-types without guest networks filters the core the same way; an empty list relays nothing "
                  "(never unfiltered by mistake)", all(o.get(k) == v for k, v in fl.items()), {k: o.get(k) for k in fl})
            want = {"cnorm0": "_ipp._tcp:_IPPS._tcp|", "cnorm1": "(null)|", "cnorm2": "|warn ", "cnorm3": "_ipp._tcp|warn ",
                    "cnorm4": "_airplay._tcp|", "cnorm.cap": "32"}
            check("avahi-daemon reaper_core_types: well-formed types kept, others dropped with a warning, empty value = unset "
                  "(NULL), no valid type = an empty list, at most 32", all(o.get(k) == v for k, v in want.items()),
                  {k: o.get(k) for k in want})
            want = {"norm0": "br52:_ipp._tcp:_IPPS._tcp|", "norm1": "br52:_ipp._tcp|warn warn warn ",
                    "norm2": "br52|", "norm3": "(null)|", "norm4": "(null)|", "norm5": "(null)|", "norm6": "(null)|",
                    "norm7": "br0123456789abc:_hap._udp|", "norm8": "br52|warn ",
                    "norm9": "br52:_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa._tcp|", "norm10": "br52|warn warn warn ", "norm.cap": "32"}
            check("avahi-daemon reaper_rg_entry: keeps the interface (1-15 safe chars) and well-formed _name._tcp/_udp types "
                  "(name 1-32), drops the rest with a warning, at most 32 types",
                  all(o.get(k) == v for k, v in want.items()), {k: o.get(k) for k in want})

INI_MAIN = r"""
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "avahi-daemon/ini-file-parser.h"
void avahi_log_error(const char *f, ...) { va_list ap; va_start(ap, f); fputs("ERR ", stdout); vprintf(f, ap); fputc(10, stdout); va_end(ap); }
int main(int argc, char **argv)
{
	AvahiIniFile *f; AvahiIniFileGroup *g; AvahiIniFilePair *p;
	(void) argc;
	if (!(f = avahi_ini_file_load(argv[1]))) { printf("load=fail\n"); return 0; }
	printf("load=ok\n");
	for (g = f->groups; g; g = g->groups_next)
		for (p = g->pairs; p; p = p->pairs_next) {
			if (!strcmp(p->key, "reflect-guest")) {
				char **e = avahi_split_csv(p->value), **t; int n = 0;
				for (t = e; *t; t++) n++;
				printf("len=%u\nentries=%d\nlast=%s\n", (unsigned) strlen(p->value), n, n ? e[n - 1] : "");
				avahi_strfreev(e);
			}
			if (!strcmp(p->key, "enable-reflector")) printf("reflector=%s\n", p->value);
		}
	avahi_ini_file_free(f);
	return 0;
}
"""
# ---------------------------------------------------------------- the real config reader, host-compiled
with tempfile.TemporaryDirectory() as td:
    av = os.path.join(SRC, "avahi")
    c, exe = os.path.join(td, "ini.c"), os.path.join(td, "ini")
    open(c, "w").write(INI_MAIN)
    rr = subprocess.run([CC, "-std=gnu99", "-Wall", "-Werror", "-Wno-unused-function", "-I" + av, "-o", exe,
                         os.path.join(av, "avahi-daemon", "ini-file-parser.c"), os.path.join(av, "avahi-common", "malloc.c"), c],
                        capture_output=True, text=True)
    check("avahi-daemon ini-file-parser.c (with avahi-common/malloc.c) compiles on the host", rr.returncode == 0, rr.stderr)
    if rr.returncode == 0:
        types = ":".join("_svc%d._tcp" % k for k in range(16))
        entries = ["br%d:%s" % (50 + k, types) for k in range(6)]
        line = "reflect-guest=" + ",".join(entries)
        cfg = os.path.join(td, "avahi-daemon.conf")
        def load(guest_line):
            open(cfg, "w").write("[server]\nuse-ipv4=yes\nuse-ipv6=no\n[reflector]\nenable-reflector=yes\n"
                                 "reflect-interfaces=br0,br53\n" + guest_line + "\n[rlimits]\n")
            out = subprocess.run([exe, cfg], capture_output=True, text=True).stdout
            return dict(l.split("=", 1) for l in out.strip().split("\n") if "=" in l and not l.startswith("ERR"))
        o = load(line)
        check("a %d-byte reflect-guest line (6 networks x 16 types) parses whole: config loads, one value, 6 entries"
              % len(line), len(line) >= 1000 and o.get("load") == "ok" and o.get("len") == str(len(line) - 14)
              and o.get("entries") == "6" and o.get("last") == entries[-1] and o.get("reflector") == "yes", (len(line), o))
        big = "reflect-guest=" + "br52:" + ":".join("_t%d._tcp" % k for k in range(800))
        big = big[:4094]
        o = load(big)
        check("a 4094-byte line still parses whole (the new limit is 4095 bytes plus the newline)",
              o.get("load") == "ok" and o.get("len") == str(len(big) - 14), (len(big), o))

if fails:
    print("\n%d check(s) failed:" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("\nall checks passed")
