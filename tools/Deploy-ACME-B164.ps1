[CmdletBinding()]
param(
    [string]$ModPath,
    [string]$ServerKeysPath
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ModPath)) { $ModPath = $repo }
$target = (Resolve-Path -LiteralPath $ModPath).ProviderPath.TrimEnd([char[]]'\/')
if (-not (Test-Path -LiteralPath $target -PathType Container)) { throw 'The destination must be an existing mod folder.' }
if ($target -eq [IO.Path]::GetPathRoot($target).TrimEnd([char[]]'\/')) { throw 'Choose a mod folder, not a drive root.' }
if ($ServerKeysPath -and -not (Test-Path -LiteralPath $ServerKeysPath -PathType Container)) {
    throw 'The server keys folder does not exist.'
}
Push-Location $repo
try {
    git diff --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Tracked files have local changes. Save them before deploying this build.' }
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) { throw 'The index contains local changes. Save them before deploying this build.' }
    $startup = Get-Content -LiteralPath (Join-Path $repo 'addons\acm_extended\functions\fn_initForkStartupRuntime.sqf') -Raw
    if (-not $startup.Contains('ACME_buildBatch = "B164";')) { throw 'This checkout is not B164.' }
    if (-not (Get-Command hemtt -ErrorAction SilentlyContinue)) { throw 'HEMTT is not available on PATH.' }
    hemtt release
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT release failed. Nothing was deployed.' }

    $release = Join-Path $repo '.hemttout\release'
    $releasePath = (Resolve-Path -LiteralPath $release).ProviderPath.TrimEnd([char[]]'\/')
    if ($target -eq $releasePath -or $target.StartsWith($releasePath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'The destination must be outside the generated release folder.'
    }
    $pbos = @(Get-ChildItem -LiteralPath (Join-Path $release 'addons') -Filter '*.pbo' -File)
    $keys = @(Get-ChildItem -LiteralPath (Join-Path $release 'keys') -Filter '*.bikey' -File)
    if ($pbos.Count -ne 14 -or $keys.Count -ne 1) { throw 'Incomplete release: expected 14 PBOs and one signing key.' }
    $signatures = @()
    foreach ($pbo in $pbos) {
        $signature = $pbo.FullName + '.' + $keys[0].BaseName + '.bisign'
        if (-not (Test-Path -LiteralPath $signature -PathType Leaf)) { throw "Missing signature for $($pbo.Name)." }
        $signatures += Get-Item -LiteralPath $signature
    }

    # The source checkout is also the installed mod at F:\ACM-Extended.
    # Copy individual release files into its existing folders, preserving addon source subdirectories.
    $targetAddons = Join-Path $target 'addons'
    $targetKeys = Join-Path $target 'keys'
    New-Item -ItemType Directory -Path $targetAddons -Force | Out-Null
    New-Item -ItemType Directory -Path $targetKeys -Force | Out-Null
    foreach ($file in ($pbos + $signatures)) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $targetAddons $file.Name) -Force
    }
    Copy-Item -LiteralPath $keys[0].FullName -Destination (Join-Path $targetKeys $keys[0].Name) -Force
    foreach ($file in Get-ChildItem -LiteralPath $release -File) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $target $file.Name) -Force
    }
    if ($ServerKeysPath) { Copy-Item -LiteralPath $keys[0].FullName -Destination $ServerKeysPath -Force }
    Write-Host "B164 deployed to $target. Restart Arma/server and check the B164 debug marker."
} finally {
    Pop-Location
}
