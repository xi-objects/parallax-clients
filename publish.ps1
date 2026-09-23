<#
.SYNOPSIS
    Pack and publish the Xio.Parallax.Client NuGet package to the XI Objects ADO Artifacts feed.

.DESCRIPTION
    1. Restores, builds, and packs the solution (tests and examples are IsPackable=false, so only
       Xio.Parallax.Client is packed).
    2. Pushes every .nupkg/.snupkg in the output directory, skipping duplicates.

    Authentication priority:
      1. Active 'az login' session  — token fetched automatically via Azure CLI.
      2. $env:NUGET_PAT              — fallback for headless/CI use.

    If neither is available the script will prompt you to run 'az login'.

.PARAMETER Version
    SemVer to stamp on the package. Defaults to the value in the csproj.
    Override when publishing a new version: .\publish.ps1 -Version 1.0.0

.PARAMETER Configuration
    Build configuration (Release/Debug). Default: Release.

.PARAMETER OutputDir
    Directory that receives the packed .nupkg files. Default: .\artifacts\packages.

.PARAMETER SkipBuild
    Skip restore/build and pack only (useful if you just ran a build).

.EXAMPLE
    # Sign in once, then publish:
    az login
    .\publish.ps1

.EXAMPLE
    # Publish a specific version:
    az login
    .\publish.ps1 -Version 1.0.0

.EXAMPLE
    # Headless/CI — supply a PAT instead:
    $env:NUGET_PAT = "<ADO PAT with Packaging Read+Write>"
    .\publish.ps1
#>
[CmdletBinding()]
param(
    [string] $Version       = "",                               # empty = use csproj value
    [string] $Configuration = "Release",
    [string] $OutputDir     = "$PSScriptRoot\artifacts\packages",
    [switch] $SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Constants ─────────────────────────────────────────────────────────────────
$FeedName  = "xiobjects"
$FeedUrl   = "<feed-url>"
$Slnx      = Join-Path $PSScriptRoot "Xio.Parallax.Client.slnx"
$AzdoScope = "499b84ac-1321-427f-aa17-267ca6975798"   # Azure DevOps resource ID

# ── Resolve credentials ───────────────────────────────────────────────────────
# Try az login session first; fall back to $env:NUGET_PAT.
function Get-FeedToken {
    # 1. Azure CLI
    if (Get-Command az -ErrorAction SilentlyContinue) {
        $tokenJson = az account get-access-token --resource $AzdoScope 2>$null
        if ($LASTEXITCODE -eq 0 -and $tokenJson) {
            $token = ($tokenJson | ConvertFrom-Json).accessToken
            Write-Host "  Using Azure CLI token (az login session)." -ForegroundColor DarkGray
            return $token
        }
    }

    # 2. NUGET_PAT env var
    if ($env:NUGET_PAT) {
        Write-Host "  Using NUGET_PAT environment variable." -ForegroundColor DarkGray
        return $env:NUGET_PAT
    }

    # 3. Neither — guide the user
    Write-Error @"

No credentials found. Either:

  a) Sign in with the Azure CLI (recommended):
       az login
       .\publish.ps1

  b) Set a PAT with 'Packaging (Read & Write)' scope:
       `$env:NUGET_PAT = '<token>'
       .\publish.ps1

Create a PAT at: <azure-devops-pat-page>
"@
    exit 1
}

$token = Get-FeedToken

# ── Clean output directory ────────────────────────────────────────────────────
if (Test-Path $OutputDir) {
    Remove-Item $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputDir | Out-Null

# ── Restore + Build ───────────────────────────────────────────────────────────
if (-not $SkipBuild) {
    Write-Host "`n==> Restoring..." -ForegroundColor Cyan
    dotnet restore $Slnx
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "`n==> Building ($Configuration)..." -ForegroundColor Cyan
    dotnet build $Slnx --configuration $Configuration --no-restore
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# ── Pack ──────────────────────────────────────────────────────────────────────
$packArgs = @(
    "pack", $Slnx,
    "--configuration", $Configuration,
    "--no-build",
    "--output", $OutputDir
)
if ($Version -ne "") {
    $packArgs += "/p:Version=$Version"
}

$versionLabel = if ($Version) { " (version $Version)" } else { "" }
Write-Host "`n==> Packing$versionLabel..." -ForegroundColor Cyan
dotnet @packArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$packages = @(Get-ChildItem -Path $OutputDir -Filter "*.nupkg")
if ($packages.Count -eq 0) {
    Write-Error "No .nupkg files found in $OutputDir after pack."
    exit 1
}
Write-Host "  Packed $($packages.Count) package(s)." -ForegroundColor Green

# ── Push ──────────────────────────────────────────────────────────────────────
# The Azure Artifacts Credential Provider reads VSS_NUGET_EXTERNAL_FEED_ENDPOINTS
# to obtain credentials non-interactively.
$env:VSS_NUGET_EXTERNAL_FEED_ENDPOINTS =
    "{`"endpointCredentials`":[{`"endpoint`":`"$FeedUrl`",`"username`":`"az`",`"password`":`"$token`"}]}"

try {
    Write-Host "`n==> Pushing packages to $FeedName..." -ForegroundColor Cyan
    foreach ($pkg in $packages) {
        Write-Host "    $($pkg.Name)"
        dotnet nuget push $pkg.FullName `
            --source $FeedUrl `
            --api-key az `
            --skip-duplicate
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} finally {
    $env:VSS_NUGET_EXTERNAL_FEED_ENDPOINTS = $null
}

Write-Host "`nDone. $($packages.Count) package(s) published to $FeedName.`n" -ForegroundColor Green
