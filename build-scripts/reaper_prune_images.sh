#!/bin/bash
# reaper_prune_images.sh -- keep the disk that holds the WSL build environment healthy (local builds only).
#
# WHY (2026-11-25, owner). Every local build writes a versioned <MODEL>_<serial>_Reaper_v<ver>[_noMCP]_*.pkgtb pair into
# targets/<platform>/ and nothing ever removed them. On 2026-11-25 the trees held 882 such images (65 GB, back to July)
# and the Windows drive holding the WSL disk file was down to 42 GB free - while `df /` inside WSL still showed 557 GB,
# because the guest sees the virtual disk's 1 TB ceiling, not the real drive.
#
# WHAT IT DOES.
#   1. Every worktree of the repo: named images older than REAPER_KEEP_DAYS move to the Windows-side archive
#      ($WIN_ASUS_ROOT/old-local-builds/<tree>/): copy, byte-compare, then delete the original. A failed copy or
#      compare leaves the original in place. The REAPER_KEEP_NEWEST newest images of each tree always stay. A name
#      already in the archive with different bytes is archived beside it with its date added, never overwritten.
#   2. Reports the free space of the Windows drive that holds the WSL disk file and warns below REAPER_HOST_MIN_GB.
#      Space freed inside WSL only reaches that drive after `fstrim` + a compact of the disk file (see the warning).
#
# SAFE BY DEFAULT. A no-op on CI and anywhere the Windows-side project folder is absent. Always exits 0 (2 on a bad
# argument), so it can never fail a build.
#
# Usage:  reaper_prune_images.sh [--dry]
# Env:    REAPER_TREE         any worktree of the repo          (default /home/reaper/asuswrt-be96u)
#         REAPER_KEEP_DAYS    keep images younger than this     (default 14)
#         REAPER_KEEP_NEWEST  always keep this many per tree    (default 4 = one build's two variants x image+loader)
#         REAPER_HOST_MIN_GB  warn below this much host free    (default 60)
#         REAPER_IMAGE_ARCHIVE archive root                     (default $WIN_ASUS_ROOT/old-local-builds)
#         REAPER_HOST_DRIVE   mount of the host drive, e.g. /mnt/f (default: found from the WSL registry entry)

DRY=0
case "${1:-}" in --dry|-n) DRY=1 ;; "") ;; *) echo "usage: $0 [--dry]"; exit 2 ;; esac
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TREE="${REAPER_TREE:-/home/reaper/asuswrt-be96u}"
KEEP_DAYS="${REAPER_KEEP_DAYS:-14}"
KEEP_NEWEST="${REAPER_KEEP_NEWEST:-4}"
MIN_GB="${REAPER_HOST_MIN_GB:-60}"

if [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${CI:-}" ]; then echo "prune-images: CI run - skipped"; exit 0; fi
if [ -z "${WIN_ASUS_ROOT:-}" ] && [ -f "$HERE/_reaper_env.sh" ]; then . "$HERE/_reaper_env.sh" 2>/dev/null; fi
if [ -z "${WIN_ASUS_ROOT:-}" ] || [ ! -d "$WIN_ASUS_ROOT" ]; then
	echo "prune-images: no Windows-side project folder (WIN_ASUS_ROOT) - skipped"; exit 0
fi
ARCH="${REAPER_IMAGE_ARCHIVE:-$WIN_ASUS_ROOT/old-local-builds}"
git -C "$TREE" rev-parse --git-dir > /dev/null 2>&1 || { echo "prune-images: $TREE is not a git tree - skipped"; exit 0; }

cutoff=$(( $(date +%s) - KEEP_DAYS * 86400 ))
moved=0; mbytes=0; kept=0; failed=0
echo "== prune-images: images older than $KEEP_DAYS days -> $ARCH$( [ $DRY = 1 ] && echo '  (dry run)')"
while read -r w; do
	[ -d "$w" ] || continue
	t=$(basename "$w"); i=0
	# newest first; only the versioned named images - the platform's own bcm*/rootfs outputs are rewritten each build
	while read -r mt f; do
		[ -n "$f" ] || continue
		i=$((i + 1)); mt=${mt%.*}
		if [ "$i" -le "$KEEP_NEWEST" ] || [ "$mt" -ge "$cutoff" ]; then kept=$((kept + 1)); continue; fi
		sz=$(stat -c %s "$f")
		if [ $DRY = 1 ]; then echo "  would move $t/$(basename "$f")"; moved=$((moved + 1)); mbytes=$((mbytes + sz / 1048576)); continue; fi
		mkdir -p "$ARCH/$t" || { failed=$((failed + 1)); continue; }
		o="$ARCH/$t/$(basename "$f")"
		if [ -e "$o" ] && cmp -s "$f" "$o"; then rm -f "$f"; moved=$((moved + 1)); mbytes=$((mbytes + sz / 1048576)); continue; fi
		[ -e "$o" ] && o="$ARCH/$t/$(basename "$f" .pkgtb).$(date -d "@$mt" +%Y%m%d-%H%M).pkgtb"
		# plain cp: --preserve=timestamps is refused on /mnt/c ("Operation not permitted"); the date goes on after, if allowed
		if cp "$f" "$o" 2>/dev/null && cmp -s "$f" "$o"; then
			touch -r "$f" "$o" 2>/dev/null
			rm -f "$f"; moved=$((moved + 1)); mbytes=$((mbytes + sz / 1048576))
		else
			rm -f "$o"; failed=$((failed + 1)); echo "  [kept, copy failed] $f"
		fi
	done < <(find "$w"/release/src-rt-*/targets/*/ -maxdepth 1 -type f -name '*_Reaper_*' \
		\( -name '*.pkgtb' -o -name '*.trx' -o -name '*.w' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn)
done < <(git -C "$TREE" worktree list --porcelain | sed -n 's/^worktree //p')
awk -v w="$([ $DRY = 1 ] && echo 'would move' || echo moved)" -v n="$moved" -v mb="$mbytes" -v k="$kept" -v f="$failed" \
	'BEGIN { printf "   %s %d images (%.1f GB), kept %d, failed %d\n", w, n, mb / 1024, k, f }'

# the Windows drive that holds the WSL disk file - guest df cannot show it
drv="${REAPER_HOST_DRIVE:-}"
if [ -z "$drv" ] && [ -n "${WSL_DISTRO_NAME:-}" ]; then
	PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
	if [ -x "$PS" ]; then
		bp=$(timeout 20 "$PS" -NoProfile -NonInteractive -Command "Get-ChildItem HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Lxss | ForEach-Object { Get-ItemProperty \$_.PSPath } | Where-Object { \$_.DistributionName -eq '$WSL_DISTRO_NAME' } | ForEach-Object { [Console]::Write(\$_.BasePath) }" 2>/dev/null | tr -d '\r')
		l=$(echo "$bp" | sed -nE 's#^(\\\\\?\\)?([A-Za-z]):.*#\2#p' | tr 'A-Z' 'a-z')
		[ -n "$l" ] && drv="/mnt/$l"
	fi
fi
if [ -n "$drv" ] && [ -d "$drv" ]; then
	free=$(df -BG --output=avail "$drv" 2>/dev/null | tail -1 | tr -dc '0-9')
	if [ -n "$free" ] && [ "$free" -lt "$MIN_GB" ]; then
		echo "   [LOW DISK] $drv (holds the WSL disk file) has ${free} GB free, under ${MIN_GB} GB."
		echo "              Free space inside WSL, then as root 'fstrim -v /', 'wsl --shutdown', and compact the disk file"
		echo "              (admin diskpart: select vdisk file=<ext4.vhdx>; attach vdisk readonly; compact vdisk; detach vdisk)."
	else
		echo "   host drive $drv (holds the WSL disk file): ${free:-?} GB free"
	fi
fi
exit 0
