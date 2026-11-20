/* nvshim - an in-memory nvram for running router programs under qemu-user (reaper_httpd_smoke.sh).
   Replaces libnvram.so's nvram_get/set/unset/getall/commit and the bit-flag helpers via LD_PRELOAD.
   Seed: NVRAM_SEED=<file> with "name=value" lines. Nothing is written back. Test-only; never shipped. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct kv { char *k, *v; struct kv *next; };
static struct kv *head;
static int seeded;

static struct kv *find(const char *k)
{
	struct kv *e;

	for (e = head; e; e = e->next)
		if (!strcmp(e->k, k))
			return e;
	return NULL;
}

int nvram_set(const char *k, const char *v);

static void seed(void)
{
	FILE *f;
	char ln[4096], *eq;
	const char *p = getenv("NVRAM_SEED");

	seeded = 1;
	if (!p || !(f = fopen(p, "r")))
		return;
	while (fgets(ln, sizeof(ln), f)) {
		ln[strcspn(ln, "\r\n")] = 0;
		if (ln[0] == '#' || !(eq = strchr(ln, '=')))
			continue;
		*eq = 0;
		nvram_set(ln, eq + 1);
	}
	fclose(f);
}

char *nvram_get(const char *k)
{
	struct kv *e;

	if (!seeded)
		seed();
	if (!k)
		return NULL;
	e = find(k);
	return e ? e->v : NULL;
}

int nvram_set(const char *k, const char *v)
{
	struct kv *e;

	if (!seeded)
		seed();
	if (!k)
		return -1;
	if (!v)
		v = "";
	if ((e = find(k))) {
		char *n = strdup(v);
		if (!n)
			return -1;
		e->v = n;	/* the old value is kept alive on purpose: callers may still hold its pointer */
		return 0;
	}
	if (!(e = calloc(1, sizeof(*e))) || !(e->k = strdup(k)) || !(e->v = strdup(v)))
		return -1;
	e->next = head;
	head = e;
	return 0;
}

int nvram_unset(const char *k)
{
	struct kv *e = k ? find(k) : NULL;

	if (e)
		e->v = "";	/* keep the node: a removed name reads as unset below */
	return 0;
}

int nvram_getall(char *buf, int count)
{
	struct kv *e;
	int n = 0, l;

	if (!seeded)
		seed();
	if (!buf || count < 2)
		return -1;
	memset(buf, 0, count);
	for (e = head; e; e = e->next) {
		if (!*e->v)
			continue;
		l = strlen(e->k) + 1 + strlen(e->v) + 1;
		if (n + l >= count - 1)
			break;
		n += sprintf(buf + n, "%s=%s", e->k, e->v) + 1;
	}
	return 0;
}

int nvram_commit(void) { return 0; }
int nvram_kcommit(void) { return 0; }
int nvram_kset(const char *k, const char *v) { return nvram_set(k, v); }
int nvram_get_bitflag(const char *k, int bit)
{
	char *v = nvram_get(k);

	return v ? (int)((strtoul(v, NULL, 0) >> bit) & 1) : 0;
}
int nvram_set_bitflag(const char *k, int bit, int val)
{
	char b[32];
	char *v = nvram_get(k);
	unsigned long x = v ? strtoul(v, NULL, 0) : 0;

	x = val ? (x | (1UL << bit)) : (x & ~(1UL << bit));
	snprintf(b, sizeof(b), "%lu", x);
	return nvram_set(k, b);
}
