[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is not available on PATH.' }
    if (-not (Get-Command hemtt -ErrorAction SilentlyContinue)) { throw 'HEMTT is not available on PATH.' }
    git diff --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Tracked files have local changes. Save them before building.' }
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) { throw 'The index contains local changes. Save them before building.' }
    $startup = Get-Content -LiteralPath (Join-Path $repo 'addons\acm_extended\functions\fn_initForkStartupRuntime.sqf') -Raw
    if (-not $startup.Contains('ACME_buildBatch = "B222";') -or
        -not $startup.Contains('ACME_networkAuditRevision = "NA8-B222-1.2.4.1-candidate";')) {
        throw 'This checkout is not the B222 development candidate.'
    }
    hemtt check
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT check failed. Nothing was deployed.' }
    # Package a signed test copy, but never install it into the working mod/server/Workshop folders.
    hemtt release
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT packaging failed. Nothing was deployed.' }
    $output = Join-Path $repo '.hemttout\release'
    $pbos = @(Get-ChildItem -LiteralPath (Join-Path $output 'addons') -Filter '*.pbo' -File)
    $keys = @(Get-ChildItem -LiteralPath (Join-Path $output 'keys') -Filter '*.bikey' -File)
    if ($pbos.Count -ne 14 -or $keys.Count -ne 1) { throw 'Expected 14 PBOs and one signing key.' }
    foreach ($pbo in $pbos) {
        $signature = $pbo.FullName + '.' + $keys[0].BaseName + '.bisign'
        if (-not (Test-Path -LiteralPath $signature -PathType Leaf)) { throw "Missing signature: $signature" }
    }
    Write-Host "B222 candidate packaged at $output"
    Write-Host 'Nothing was copied to production or published. Test clients/server must load only this candidate, not both B201 and B222.'
} finally {
    Pop-Location
}
