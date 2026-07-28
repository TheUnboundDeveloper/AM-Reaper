#!/bin/bash
# _reaper_env.sh -- resolve the Windows-side paths generically so the build
# scripts are not pinned to one developer's Windows profile folder.
#
# Exports:
#   WINUSER        Windows PROFILE-FOLDER name under /mnt/c/Users
#   WIN_ASUS_ROOT  the ASUS project root as seen from WSL
#                  (/mnt/c/Users/<WINUSER>/AppData/Roaming/VSC/ASUS)
#
# Override by exporting WINUSER before invoking a build script, e.g.
#   WINUSER=alice build_gtbe98.sh
#
# NB: we resolve the PROFILE FOLDER, not the login name. On Windows the two can
# differ (e.g. account "Nathan" but folder C:\Users\natha), so %USERNAME% is
# unreliable -- we validate each candidate by checking the ASUS mirror exists.

# true if /mnt/c/Users/$1/AppData/Roaming/VSC/ASUS is a real directory
_rw_has_asus() { [ -n "${1:-}" ] && [ -d "/mnt/c/Users/$1/AppData/Roaming/VSC/ASUS" ]; }

if [ -z "${WINUSER:-}" ]; then   # honor an explicit override unconditionally
	# 1) the actual profile FOLDER from %USERPROFILE% (basename), validated.
	_up="$(powershell.exe -NoProfile -NonInteractive -Command '[Console]::Write($env:USERPROFILE)' 2>/dev/null | tr -d '\r')"
	_cand="${_up##*\\}"
	_rw_has_asus "$_cand" && WINUSER="$_cand"
	# 2) scan every profile dir for the ASUS mirror (most reliable, generic).
	if [ -z "$WINUSER" ]; then
		for _d in /mnt/c/Users/*/AppData/Roaming/VSC/ASUS; do
			[ -d "$_d" ] || continue
			WINUSER="$(echo "$_d" | sed -E 's#^/mnt/c/Users/([^/]+)/.*#\1#')"; break
		done
	fi
	# 3) last resort: the profile-folder guess if we had one, else the build box.
	[ -z "$WINUSER" ] && WINUSER="${_cand:-natha}"
fi

WIN_ASUS_ROOT="/mnt/c/Users/${WINUSER}/AppData/Roaming/VSC/ASUS"
export WINUSER WIN_ASUS_ROOT
