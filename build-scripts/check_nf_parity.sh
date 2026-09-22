#!/bin/bash
# ============================================================================
# check_nf_parity.sh -- every netfilter match/target the shipped firewall can
# name, the shipped kernel must provide (built in, or a staged module).
# ----------------------------------------------------------------------------
# Usage:  check_nf_parity.sh FS KCONFIG KSRC
#   FS       staged rootfs (targets/96813GW/fs)
#   KCONFIG  the kernel .config the image was built from (kernel/linux-4.19/.config)
#   KSRC     the kernel source dir (for its netfilter Kconfig files)
#
# WHY. RT-BE88U field report, 2026-09-14: iptables-restore refused the whole
# filter table at COMMIT because of `-m string` / `-m u32` rules the closed
# blob emits. The reporter concluded the kernel lacked those matches; it did
# not (IKCONFIG of the CI image says =y for both), so the cause was elsewhere -
# but the class is real and this is the gate for it: a kernel-config drift that
# drops a match the firewall emits would refuse the table on every box and
# nothing in the build would say so. This reads the NAMES out of the staged
# binaries and scripts (so the closed blob is covered - it is linked into rc),
# resolves each to its Kconfig symbol(s) from the kernel's own Kconfig, and
# requires =y or a staged .ko. A name with no Kconfig symbol is a user chain
# (or a match this kernel never had) and is listed, not judged.
#
# Exit 0 = every judged name is provided (unknowns printed as notes), 1 = at
# least one is not, 2 = bad usage.
# ============================================================================
set -u
FS="${1:?FS}"; KCONF="${2:?KCONFIG}"; KSRC="${3:?KSRC}"
[ -d "$FS" ] || { echo "no staged fs at $FS"; exit 2; }
[ -f "$KCONF" ] || { echo "no kernel config at $KCONF"; exit 2; }
KC="$KSRC/net/netfilter/Kconfig $KSRC/net/netfilter/ipset/Kconfig $KSRC/net/ipv4/netfilter/Kconfig $KSRC/net/ipv6/netfilter/Kconfig"
for f in $KC; do [ -f "$f" ] || { echo "no Kconfig at $f"; exit 2; }; done

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# --- 1. the names: -m <match> and -j <TARGET> literals in everything staged ---
# ELF binaries and shared objects via strings (rc carries the blob), shell
# scripts and other text via grep. `-m %s` / `-j %s` format holes cannot match
# the name classes and drop out on their own.
find "$FS/sbin" "$FS/bin" "$FS/usr/sbin" "$FS/usr/bin" "$FS/lib" "$FS/usr/lib" -type f 2>/dev/null \
  | while read -r f; do
      if head -c 4 "$f" 2>/dev/null | grep -q 'ELF'; then strings -n 4 "$f"; else cat "$f"; fi
    done > "$TMP/text" 2>/dev/null
grep -rh --include='*.sh' --include='*.asp' --include='*.js' -e '-m ' -e '-j ' "$FS/rom" "$FS/www" "$FS/etc" 2>/dev/null >> "$TMP/text" || true
grep -oE -- '(^|[^A-Za-z0-9_-])-m [a-z][a-z0-9_]*' "$TMP/text" | awk '{print $2}' | sort -u > "$TMP/matches"
grep -oE -- '(^|[^A-Za-z0-9_-])-j [A-Z][A-Z0-9_]*' "$TMP/text" | awk '{print $2}' | sort -u > "$TMP/targets"

kcfg() { grep -E "^CONFIG_$1=" "$KCONF" | head -1 | sed 's/^[^=]*=//'; }
ksym_exists() { grep -qE "^config $1\$" $KC; }
staged_ko() {  # $1 = module base name(s), space separated
  local m
  for m in $1; do find "$FS/lib/modules" -name "$m.ko" 2>/dev/null | grep -q . && return 0; done
  return 1
}

fail=0; judged=0; unknown=""
judge() {  # $1 kind (match|target)  $2 name  $3 candidate symbols  $4 module basenames
  local kind="$1" name="$2" syms="$3" mods="$4" s v any=0 built=0 modv=0
  for s in $syms; do
    ksym_exists "$s" || continue
    any=1; v="$(kcfg "$s")"
    [ "$v" = y ] && built=1
    [ "$v" = m ] && modv=1
  done
  if [ "$any" = 0 ]; then unknown="$unknown $kind:$name"; return; fi
  judged=$((judged+1))
  if [ "$built" = 1 ]; then return; fi
  if [ "$modv" = 1 ]; then
    staged_ko "$mods" && return
    echo "  FAIL $kind '$name': built as a module but no $(echo $mods | sed 's/ /.ko|/g').ko is staged under lib/modules"; fail=$((fail+1)); return
  fi
  echo "  FAIL $kind '$name': the firewall can emit it but the kernel config has $(for s in $syms; do ksym_exists "$s" && echo -n "$s "; done)unset"; fail=$((fail+1))
}

while read -r m; do
  [ -n "$m" ] || continue
  case "$m" in tcp|udp|udplite|icmp|icmp6|icmpv6) continue;; esac   # protocol matches: ip_tables itself
  U=$(echo "$m" | tr 'a-z' 'A-Z')
  case "$m" in
    set)   judge match "$m" "NETFILTER_XT_SET" "xt_set" ;;
    *)     judge match "$m" "NETFILTER_XT_MATCH_$U IP_NF_MATCH_$U IP6_NF_MATCH_$U" "xt_$m ipt_$m ip6t_$m" ;;
  esac
  if [ "$m" = string ]; then
    judged=$((judged+1))
    if [ "$(kcfg TEXTSEARCH_BM)" != y ] && ! staged_ko "ts_bm"; then
      echo "  FAIL match 'string': its --algo bm needs CONFIG_TEXTSEARCH_BM, which is neither built in nor staged"; fail=$((fail+1))
    fi
  fi
done < "$TMP/matches"

while read -r t; do
  [ -n "$t" ] || continue
  case "$t" in ACCEPT|DROP|RETURN|QUEUE) continue;; esac
  case "$t" in
    DNAT|SNAT)  judge target "$t" "NETFILTER_XT_NAT IP_NF_NAT" "xt_nat" ;;
    *)          judge target "$t" "NETFILTER_XT_TARGET_$t IP_NF_TARGET_$t IP6_NF_TARGET_$t" "xt_$t ipt_$t ip6t_$t" ;;
  esac
done < "$TMP/targets"

nm=$(wc -l < "$TMP/matches"); nt=$(wc -l < "$TMP/targets")
[ -n "$unknown" ] && echo "  note: no Kconfig symbol for (user chains or names this kernel never had):$unknown"
if [ "$fail" -gt 0 ]; then
  echo "$fail netfilter match/target(s) the firewall can emit are NOT provided by the shipped kernel ($judged judged from $nm match / $nt target names)"
  exit 1
fi
echo "$judged netfilter match/target names judged (from $nm match / $nt target literals in the staged fs), all provided by the shipped kernel"
exit 0
