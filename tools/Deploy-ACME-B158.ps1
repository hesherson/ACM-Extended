[CmdletBinding()]
param(
    [string]$ModPath,
    [string]$ServerKeysPath
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    git diff --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Tracked files have local changes. Save them before deploying this build.' }
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) { throw 'The index contains local changes. Save them before deploying this build.' }
    $startup = Get-Content -LiteralPath (Join-Path $repo 'addons\acm_extended\functions\fn_initForkStartupRuntime.sqf') -Raw
    if (-not $startup.Contains('ACME_buildBatch = "B158";')) { throw 'This checkout is not B158.' }
    if (-not (Get-Command hemtt -ErrorAction SilentlyContinue)) { throw 'HEMTT is not available on PATH.' }
    hemtt release
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT release failed. Nothing was deployed.' }

    $release = Join-Path $repo '.hemttout\release'
    $pbos = @(Get-ChildItem -LiteralPath (Join-Path $release 'addons') -Filter '*.pbo' -File)
    $keys = @(Get-ChildItem -LiteralPath (Join-Path $release 'keys') -Filter '*.bikey' -File)
    if ($pbos.Count -ne 14 -or $keys.Count -ne 1) { throw 'Incomplete release: expected 14 PBOs and one signing key.' }
    foreach ($pbo in $pbos) {
        $signature = $pbo.FullName + '.' + $keys[0].BaseName + '.bisign'
        if (-not (Test-Path -LiteralPath $signature -PathType Leaf)) { throw "Missing signature for $($pbo.Name)." }
    }
    if ([string]::IsNullOrWhiteSpace($ModPath)) {
        $ModPath = Read-Host 'Full path to the existing ACM Extended mod folder to update (outside F:\ACM-Extended)'
    }
    $target = (Resolve-Path -LiteralPath $ModPath).ProviderPath.TrimEnd('\', '/')
    if (-not (Test-Path -LiteralPath $target -PathType Container)) { throw 'The destination must be an existing mod folder.' }
    $repoPrefix = $repo.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if ($target -eq $repo -or $target.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Choose the installed mod folder outside this source checkout.'
    }
    if ($target -eq [IO.Path]::GetPathRoot($target).TrimEnd('\', '/')) { throw 'Choose a mod folder, not a drive root.' }
    if ($ServerKeysPath -and -not (Test-Path -LiteralPath $ServerKeysPath -PathType Container)) {
        throw 'The server keys folder does not exist.'
    }
    foreach ($item in Get-ChildItem -LiteralPath $release -Force) {
        Copy-Item -LiteralPath $item.FullName -Destination $target -Recurse -Force
    }
    if ($ServerKeysPath) { Copy-Item -LiteralPath $keys[0].FullName -Destination $ServerKeysPath -Force }
    Write-Host "B158 deployed to $target. Restart Arma/server and check the B158 debug marker."
} finally {
    Pop-Location
}
