<#
.SYNOPSIS
  Stage locally built Reaper firmware into releases/ for a GitHub release.

.DESCRIPTION
  Copies the built .pkgtb images for a version from the local firmware ladder
  (asuswrt-merlin.ng\reaper-firmware\) into releases/<Model>/<MODEL>-REAPER-<ver>/,
  writes per-model SHA256SUMS files, verifies every copy hash-for-hash,
  refreshes releases/latest.json, and commits the result locally.

  It NEVER pushes. Publishing is: git push, then push the version tag —
  .github/workflows/release.yml builds the GitHub Release from what was staged.

.EXAMPLE
  .\stage_release.ps1 -Version v2.2.0
  .\stage_release.ps1 -Version v2.2.0 -Models BE96U,BE98 -AllowPartial
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^v\d+\.\d+\.\d+[0-9a-z._-]*$')]
    [string]$Version,

    [ValidateSet('BE96U', 'BE86U', 'BE88U', 'BE98', 'BE98Pro')]
    [string[]]$Models = @('BE96U', 'BE86U', 'BE88U', 'BE98', 'BE98Pro'),

    # Local firmware ladder holding the built images (default: sibling asuswrt-merlin.ng mirror)
    [string]$LadderDir,

    # Stage whatever images exist instead of requiring the full model matrix
    [switch]$AllowPartial,

    # Stage + write files but skip the git commit
    [switch]$NoCommit
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $LadderDir) {
    $LadderDir = Join-Path (Split-Path -Parent $RepoRoot) 'asuswrt-merlin.ng\reaper-firmware'
}
if (-not (Test-Path $LadderDir)) { throw "Firmware ladder not found: $LadderDir (pass -LadderDir)" }

$PrefixMap = @{
    BE96U   = 'RT-BE96U'
    BE86U   = 'RT-BE86U'
    BE88U   = 'RT-BE88U'
    BE98    = 'GT-BE98'
    BE98Pro = 'GT-BE98_PRO'
}

# --- 1. Plan: confirm every expected image exists before touching anything ---
$plan = @(); $missing = @()
foreach ($m in $Models) {
    $prefix = $PrefixMap[$m]
    foreach ($variant in @('', '_noMCP')) {
        $file = "${prefix}_3006_102.8_Reaper_${Version}${variant}_nand_squashfs.pkgtb"
        $src = Join-Path $LadderDir $file
        if (Test-Path $src) {
            $plan += [pscustomobject]@{ Model = $m; Prefix = $prefix; File = $file; Src = $src }
        }
        else { $missing += $file }
    }
}
if ($missing.Count -gt 0) {
    $missing | ForEach-Object { Write-Host "MISSING: $_" -ForegroundColor Red }
    if (-not $AllowPartial) {
        throw "Not all images for $Version are in the ladder. Build them first, narrow -Models, or pass -AllowPartial."
    }
    Write-Host "continuing without the missing images (-AllowPartial)" -ForegroundColor Yellow
}
if ($plan.Count -eq 0) { throw "Nothing to stage for $Version." }

# --- 2. Copy, hash, verify, write per-model SHA256SUMS ---
$staged = @()
foreach ($group in ($plan | Group-Object Model)) {
    $m = $group.Name
    $prefix = $PrefixMap[$m]
    $destDir = Join-Path $RepoRoot "releases\$m\$($m.ToUpper())-REAPER-$Version"
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    $sums = @()
    foreach ($item in $group.Group) {
        $dest = Join-Path $destDir $item.File
        Copy-Item $item.Src $dest -Force
        $srcHash = (Get-FileHash $item.Src -Algorithm SHA256).Hash.ToLower()
        $dstHash = (Get-FileHash $dest -Algorithm SHA256).Hash.ToLower()
        if ($srcHash -ne $dstHash) { throw "COPY VERIFICATION FAILED for $($item.File) — staged file does not match the built image" }
        $sums += "$dstHash  $($item.File)"
        $staged += [pscustomobject]@{ Model = $m; File = $item.File; Sha256 = $dstHash; Size = (Get-Item $dest).Length }
        Write-Host ("staged  {0,-8} {1}" -f $m, $item.File)
    }
    # LF line endings so sha256sum -c works in CI
    $sumsPath = Join-Path $destDir "SHA256SUMS-$prefix-Reaper_$Version.txt"
    [System.IO.File]::WriteAllText($sumsPath, (($sums -join "`n") + "`n"))
}

# --- 3. Update the machine-readable manifest (future in-firmware update checks) ---
$manifest = [ordered]@{ version = $Version; date = (Get-Date -Format 'yyyy-MM-dd'); models = [ordered]@{} }
foreach ($group in ($staged | Group-Object Model | Sort-Object Name)) {
    $manifest.models[$group.Name] = @(
        foreach ($s in $group.Group) {
            [ordered]@{
                file   = $s.File
                sha256 = $s.Sha256
                size   = $s.Size
                url    = "https://github.com/TheUnboundDeveloper/AM-Reaper/releases/download/$Version/$($s.File)"
            }
        }
    )
}
$manifestPath = Join-Path $RepoRoot 'releases\latest.json'
[System.IO.File]::WriteAllText($manifestPath, (($manifest | ConvertTo-Json -Depth 6) -replace "`r`n", "`n") + "`n")
Write-Host "wrote releases/latest.json"

# --- 4. Commit locally (never push) ---
if (-not $NoCommit) {
    git -C $RepoRoot add -- releases
    git -C $RepoRoot commit -m "releases: stage firmware $Version"
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
}

Write-Host ""
Write-Host "Staged $($staged.Count) images for $Version." -ForegroundColor Green
Write-Host "Next steps (run when ready to publish):" -ForegroundColor Cyan
Write-Host "  git -C `"$RepoRoot`" push origin main"
Write-Host "  git -C `"$RepoRoot`" tag $Version"
Write-Host "  git -C `"$RepoRoot`" push origin $Version   # <- this triggers the 'Publish release' workflow"
