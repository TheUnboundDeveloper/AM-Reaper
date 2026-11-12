#!/bin/bash
# reaper_httpd_smoke.sh - run the IMAGE's own httpd under qemu-user and prove it serves and survives connections.
#
# Why: test image _r14 shipped an httpd that exited on its first connection (a libc name answered by libshared);
# every host test passed because host tests link the real C library. This runs the staged binary with the staged
# libraries, in a private user+mount+pid namespace with the staged fs as its root (bind-mounted read-only view,
# tmpfs on /tmp), an in-memory nvram (nvshim.so via LD_PRELOAD), plain HTTP on 127.0.0.1:<port>.
#
# Usage: reaper_httpd_smoke.sh <staged fs> [port]      env: REAPER_CC (ARM gcc for the shim), SMOKE_KEEP=1
# Checks: httpd starts and listens; GET /Main_Login.asp answers HTTP 200 with a page; the process is the same and
# alive after it; it survives a connection that sends nothing and closes, and 5 requests in a row.
# Exit: 0 pass, 1 fail, 77 skipped (no qemu-arm binfmt / no namespaces / no ARM compiler).
set -u
FS=${1:?staged fs}; PORT=${2:-18080}
HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
CC=${REAPER_CC:-/opt/toolchains/crosstools-arm_softfp-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1/usr/bin/arm-buildroot-linux-gnueabi-gcc}
skip(){ echo "SKIP: $*"; exit 77; }
[ -x "$FS/usr/sbin/httpd" ] || { echo "FAIL: no $FS/usr/sbin/httpd"; exit 1; }
grep -qs enabled /proc/sys/fs/binfmt_misc/qemu-arm || skip "qemu-arm binfmt not registered"
grep -qs 'flags: .*F' /proc/sys/fs/binfmt_misc/qemu-arm || skip "qemu-arm binfmt lacks the F flag (needed inside a chroot)"
unshare -Urmpf true 2>/dev/null || skip "user/mount/pid namespaces not available"
[ -x "$CC" ] || skip "ARM compiler $CC missing"
command -v curl >/dev/null || skip "curl missing"

W=$(mktemp -d /tmp/httpd_smoke.XXXXXX)
trap '[ -n "${SMOKE_KEEP:-}" ] || rm -rf "$W"' EXIT
"$CC" -shared -fPIC -O2 -o "$W/nvshim.so" "$HERE/reaper_smoke_nvshim.c" || { echo "FAIL: shim build"; exit 1; }
sed "s/^http_lanport=.*/http_lanport=$PORT/" "$HERE/reaper_smoke_httpd.seed" > "$W/seed"

cat > "$W/inner.sh" <<'INNER'
set -u
FS=$1; W=$2; PORT=$3
R=$W/root; mkdir -p $R
mount --rbind "$FS" $R || exit 3
mount -o remount,bind,ro $R 2>/dev/null
mount -t tmpfs tmpfs $R/tmp || exit 3
mount -t tmpfs tmpfs $R/var || exit 3	# the router's init mounts a tmpfs on /var at boot
mkdir -p $R/var/run $R/var/lock $R/var/tmp $R/tmp/var/run $R/tmp/etc $R/tmp/reaper $R/tmp/smoke
cp $W/nvshim.so $W/seed $R/tmp/smoke/
mount -t proc proc $R/proc 2>/dev/null
for d in null zero urandom random; do [ -e $R/dev/$d ] || continue; mount --bind /dev/$d $R/dev/$d 2>/dev/null; done
# SMOKE_HTTPD=<file>: test another httpd binary (e.g. one taken out of an older image) in this image's root
[ -n "${SMOKE_HTTPD:-}" ] && { mount --bind "$SMOKE_HTTPD" $R/usr/sbin/httpd || exit 3; echo "     testing $SMOKE_HTTPD in place of the staged httpd"; }
( cd / && exec chroot $R /bin/sh -c "cd /www && LD_PRELOAD=/tmp/smoke/nvshim.so NVRAM_SEED=/tmp/smoke/seed exec /usr/sbin/httpd -i lo -p $PORT" ) >$W/httpd.out 2>&1 &
HP=$!
ok=0; fails=""
i=0; while [ $i -lt 40 ]; do
  curl -s -o /dev/null --max-time 2 http://127.0.0.1:$PORT/ 2>/dev/null; rc=$?
  [ $rc -ne 7 ] && break
  kill -0 $HP 2>/dev/null || break
  sleep 0.5; i=$((i+1))
done
# (the probe above is itself a first connection; the checks below say whether httpd survived it)
alive(){ kill -0 $HP 2>/dev/null; }
alive && echo "ok   httpd started and listens on 127.0.0.1:$PORT (pid $HP)" || { echo "FAIL httpd is not running after its first connection"; fails=1; }
if alive; then
  code=$(curl -s -o $W/page --max-time 15 -w '%{http_code}' http://127.0.0.1:$PORT/Main_Login.asp)
  if [ "$code" = 200 ] && grep -qi '<html' $W/page; then echo "ok   GET /Main_Login.asp -> 200, $(wc -c < $W/page) bytes"; else echo "FAIL GET /Main_Login.asp -> '$code'"; fails=1; fi
  alive && echo "ok   same process alive after the request" || { echo "FAIL httpd exited after a request"; fails=1; }
  # a connection that sends nothing and closes (the _r14 killer was ANY accepted connection)
  exec 9<>/dev/tcp/127.0.0.1/$PORT && sleep 1 && exec 9>&-
  sleep 1
  alive && echo "ok   survives a connection that sends nothing" || { echo "FAIL httpd exited after an empty connection"; fails=1; }
  n=0; for k in 1 2 3 4 5; do c=$(curl -s -o /dev/null --max-time 15 -w '%{http_code}' http://127.0.0.1:$PORT/Main_Login.asp); [ "$c" = 200 ] && n=$((n+1)); done
  [ $n = 5 ] && alive && echo "ok   5 requests in a row answered, still the same process" || { echo "FAIL $n of 5 requests answered (alive: $(alive && echo yes || echo no))"; fails=1; }
fi
if ! alive; then wait $HP 2>/dev/null; echo "     httpd exit status: $?"; fi
kill $HP 2>/dev/null; wait $HP 2>/dev/null
[ -s $W/httpd.out ] && { echo "---- httpd output (tail)"; tail -15 $W/httpd.out; }
[ -z "$fails" ]
INNER
SMOKE_HTTPD="${SMOKE_HTTPD:-}" unshare -Urmpf --mount-proc=/proc bash "$W/inner.sh" "$FS" "$W" "$PORT"
rc=$?
if [ $rc = 0 ]; then echo "httpd smoke: PASS"; exit 0; fi
[ $rc = 3 ] && skip "could not set up the private root (mount refused)"
echo "httpd smoke: FAIL"; exit 1
