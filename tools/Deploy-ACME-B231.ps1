[CmdletBinding()]
param([string]$ServerKeysPath)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).ProviderPath.TrimEnd([char[]]'\/')
Push-Location $Repo
try {
    Get-Command git, hemtt -ErrorAction Stop | Out-Null
    if (Get-Process -Name arma3,arma3_x64,arma3server,arma3server_x64 -ErrorAction SilentlyContinue) {
        throw 'Close Arma and any local Arma server before replacing its PBOs.'
    }
    # Generated files coexist with the source subdirectories in this established install.
    $Status = @(git status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) { throw 'Could not check the source checkout.' }
    $Generated = '^\?\? (addons/ACM_[^/]+\.pbo(?:\.[^/]+\.bisign)?|keys/[^/]+\.bikey)$'
    $Edits = @($Status | Where-Object { $_ -notmatch $Generated })
    if ($Edits.Count -gt 0) {
        $Edits | ForEach-Object { Write-Host $_ }
        throw 'Source changes or other untracked files found. Nothing was discarded.'
    }
    $Startup = Get-Content -LiteralPath 'addons\acm_extended\functions\fn_initForkStartupRuntime.sqf' -Raw
    if (-not $Startup.Contains('ACME_buildBatch = "B231";') -or
        -not $Startup.Contains('ACME_networkAuditRevision = "NA8-B231-1.2.4.1-candidate";')) {
        throw 'This source checkout is not B231.'
    }
    if ($ServerKeysPath -and -not (Test-Path -LiteralPath $ServerKeysPath -PathType Container)) {
        throw 'The optional server keys folder does not exist.'
    }
    hemtt check
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT check failed. Nothing was deployed.' }
    hemtt release
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT release failed. Nothing was deployed.' }
    $Release = (Resolve-Path -LiteralPath '.hemttout\release').ProviderPath.TrimEnd([char[]]'\/')
    $Pbos = @(Get-ChildItem -LiteralPath "$Release\addons" -Filter '*.pbo' -File)
    $Keys = @(Get-ChildItem -LiteralPath "$Release\keys" -Filter '*.bikey' -File)
    if ($Pbos.Count -ne 14 -or $Keys.Count -ne 1) {
        throw 'Incomplete release: expected 14 PBOs and one public signing key.'
    }
    $Signatures = @(
        foreach ($Pbo in $Pbos) {
            $Signature = $Pbo.FullName + '.' + $Keys[0].BaseName + '.bisign'
            if (-not (Test-Path -LiteralPath $Signature -PathType Leaf)) {
                throw "Missing signature for $($Pbo.Name). Nothing was deployed."
            }
            Get-Item -LiteralPath $Signature
        }
    )
    $Files = @($Pbos + $Signatures + $Keys + @(Get-ChildItem -LiteralPath $Release -File))
    # Normal installed folder and the already-used launcher path receive the SAME signed release.
    # Never mirror, recursively remove, or overwrite addon source directories.
    $Targets = @($Repo, (Join-Path $Repo '.hemttout\build'))
    foreach ($File in $Files) {
        $Relative = $File.FullName.Substring($Release.Length).TrimStart([char[]]'\/')
        $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash
        foreach ($Target in $Targets) {
            $Destination = Join-Path $Target $Relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
            Copy-Item -LiteralPath $File.FullName -Destination $Destination -Force
            if ((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -ne $Hash) {
                throw "Copy verification failed: $Destination. Do not launch this installation."
            }
        }
    }
    if ($ServerKeysPath) {
        Copy-Item -LiteralPath $Keys[0].FullName -Destination $ServerKeysPath -Force
    }
    Write-Host "B231 deployed and copy-verified in $Repo"
    Write-Host "Existing launcher path refreshed: $(Join-Path $Repo '.hemttout\build')"
    Write-Host 'Restart Arma and confirm 1.2.4.1 / B231. Nothing was pushed or published.'
} finally {
    Pop-Location
}
