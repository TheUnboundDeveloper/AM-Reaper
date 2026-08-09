<#
.SYNOPSIS
  Repo size report: what actually counts against GitHub's 10 GB repo limit,
  what's free (Release assets), and where the bytes live in your local clone.

.DESCRIPTION
  GitHub counts ONLY the server-side git object store (".git") against the
  repository size limit (docs: "On-disk size refers to the size of the .git
  folder"). Release assets are stored separately and are free (2 GiB/file cap,
  no total or bandwidth cap). This script shows both sides:

    1. GitHub API  : the official counted size + total (free) release-asset bytes
    2. Local clone : .git breakdown, raw tracked bytes at HEAD, biggest blobs
                     in history, and anything not pushed yet

  The interesting delta is usually [raw tracked bytes] vs [counted size]:
  git's delta compression can pack similar binaries (e.g. successive firmware
  images) far smaller than their raw size.

.EXAMPLE
  ./repo-size-report.ps1 -Repo TheUnboundDeveloper/AM-Reaper -LocalPath .

.EXAMPLE
  ./repo-size-report.ps1 -Repo owner/private-repo -Token ghp_xxx -TopBlobs 15

.NOTES
  -Token is only needed for private repos (a classic PAT or fine-grained token
  with repo read). Without -LocalPath, only the API section runs.
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[\w.-]+/[\w.-]+$')]
  [string]$Repo,                 # "owner/name"

  [string]$LocalPath = '',       # path to a local clone (optional)
  [string]$Token     = '',       # PAT for private repos (optional)
  [int]$TopBlobs     = 10        # how many largest history blobs to list
)

$ErrorActionPreference = 'Stop'

function Fmt([long]$bytes) {
  if ($bytes -ge 1GB) { return ('{0:N2} GB' -f ($bytes / 1GB)) }
  if ($bytes -ge 1MB) { return ('{0:N1} MB' -f ($bytes / 1MB)) }
  if ($bytes -ge 1KB) { return ('{0:N0} KB' -f ($bytes / 1KB)) }
  return "$bytes B"
}

# ---------- 1. GitHub API: the size that actually counts -----------------------
$headers = @{ 'User-Agent' = 'repo-size-report'; 'Accept' = 'application/vnd.github+json' }
if ($Token) { $headers['Authorization'] = "Bearer $Token" }

Write-Host "== GitHub ($Repo) ==" -ForegroundColor Cyan
$r = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo" -Headers $headers
$countedBytes = [long]$r.size * 1KB          # API reports KB
Write-Host ("counted repo size (the 10 GB budget) : {0}  ({1} KB raw)" -f (Fmt $countedBytes), $r.size)
Write-Host ("visibility / default branch          : {0} / {1}" -f ($(if ($r.private) {'private'} else {'public'})), $r.default_branch)
Write-Host ("last push (size field may lag this)  : {0}" -f $r.pushed_at)

# Release assets: free storage, listed for contrast
$assetBytes = [long]0; $assetCount = 0; $page = 1
do {
  $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases?per_page=100&page=$page" -Headers $headers
  foreach ($rr in $rel) { foreach ($a in $rr.assets) { $assetBytes += [long]$a.size; $assetCount++ } }
  $page++
} while ($rel.Count -eq 100)
Write-Host ("release assets (FREE, not counted)   : {0} across {1} files" -f (Fmt $assetBytes), $assetCount)

# ---------- 2. Local clone (optional) ------------------------------------------
if (-not $LocalPath) {
  Write-Host "`n(no -LocalPath given; skipping local analysis)" -ForegroundColor DarkGray
  return
}
$LocalPath = (Resolve-Path $LocalPath).Path
if (-not (Test-Path (Join-Path $LocalPath '.git'))) { throw "$LocalPath is not a git clone" }
Push-Location $LocalPath
try {
  Write-Host "`n== Local clone ($LocalPath) ==" -ForegroundColor Cyan

  $gitDirBytes = (Get-ChildItem .git -Recurse -Force -ErrorAction SilentlyContinue |
                  Measure-Object Length -Sum).Sum
  Write-Host ("local .git size                      : {0}" -f (Fmt $gitDirBytes))
  git count-objects -vH | ForEach-Object { Write-Host ("  {0}" -f $_) }

  # raw (uncompressed) bytes referenced by HEAD, and the biggest paths
  Write-Host "`n-- raw tracked bytes at HEAD (uncompressed blob sizes) --"
  $headSum = [long]0
  $byDir = @{}
  git ls-tree -r -l HEAD | ForEach-Object {
    $f = ($_ -split "`t")[0] -split '\s+'      # mode type sha size
    $path = ($_ -split "`t")[1]
    $sz = [long]$f[3]
    $headSum += $sz
    $top = ($path -split '/')[0]
    $byDir[$top] = [long]($byDir[$top]) + $sz
  }
  Write-Host ("total at HEAD                        : {0}" -f (Fmt $headSum))
  $byDir.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 8 | ForEach-Object {
    Write-Host ("  {0,-30} {1}" -f $_.Key, (Fmt $_.Value))
  }
  if ($countedBytes -gt 0 -and $headSum -gt 0) {
    Write-Host ("compression on GitHub                : {0:N1} : 1  (raw HEAD vs counted size; history adds more raw)" -f ($headSum / $countedBytes))
  }

  # biggest blobs in ALL history (what a history rewrite would reclaim)
  Write-Host "`n-- top $TopBlobs largest blobs anywhere in history --"
  $sizes = git rev-list --objects --all |
    git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
    Where-Object { $_ -like 'blob *' } |
    ForEach-Object { $p = $_ -split ' ', 4; [pscustomobject]@{ Size = [long]$p[2]; Path = $p[3] } } |
    Sort-Object Size -Descending
  $sizes | Select-Object -First $TopBlobs | ForEach-Object {
    Write-Host ("  {0,10}  {1}" -f (Fmt $_.Size), $_.Path)
  }
  $histSum = ($sizes | Measure-Object Size -Sum).Sum
  Write-Host ("raw bytes across ALL history         : {0} (packs down to the counted size above)" -f (Fmt $histSum))

  # anything not on the remote yet
  Write-Host "`n-- not pushed yet --"
  $branch = git rev-parse --abbrev-ref HEAD
  $upstream = git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null
  if (-not $upstream) {
    # no tracking ref configured; fall back to origin/<branch> if it exists
    git show-ref --verify --quiet "refs/remotes/origin/$branch" 2>$null
    if ($LASTEXITCODE -eq 0) { $upstream = "origin/$branch" }
  }
  if ($upstream) {
    $ahead = @(git log --oneline "$upstream..HEAD")
    if ($ahead.Count) { $ahead | ForEach-Object { Write-Host "  $_" } }
    else { Write-Host "  (none - local matches $upstream)" }
  } else { Write-Host "  (no upstream or origin/$branch ref to compare against)" }
}
finally {
  Pop-Location
  $global:LASTEXITCODE = 0     # informational tool: never bubble a git probe's exit code
}
