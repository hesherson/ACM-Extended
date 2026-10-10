[CmdletBinding()]
param([string]$ServerKeysPath, [switch]$Recover)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).ProviderPath.TrimEnd([char[]]'\/')
Push-Location $Repo
try {
    Get-Command git, hemtt -ErrorAction Stop | Out-Null
    if (Get-Process -Name arma3,arma3_x64,arma3server,arma3server_x64 -ErrorAction SilentlyContinue) {
        throw 'Close Arma and local Arma servers before deployment or recovery.'
    }
    $PythonPrefix = @()
    $Python = Get-Command py -ErrorAction SilentlyContinue
    if ($Python) { $PythonPrefix = @('-3') } else { $Python = Get-Command python -ErrorAction Stop }
    $PythonExe = $Python.Source
    & $PythonExe @PythonPrefix -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.9 or newer is required for journalled deployment.' }
    $Tool = Join-Path $Repo 'tools\deploy_acme_release.py'
    if ($Recover) {
        & $PythonExe @PythonPrefix $Tool recover --repo $Repo
        if ($LASTEXITCODE -ne 0) { throw 'Recovery failed. Do not launch Arma. Preserve the journal and backups.' }
        return
    }
    $Status = @(git status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the source checkout.' }
    $Generated = '^\?\? (addons/ACM_[^/]+\.pbo(?:\.[^/]+\.bisign)?|keys/[^/]+\.bikey)$'
    $Edits = @($Status | Where-Object { $_ -notmatch $Generated })
    if ($Edits.Count -gt 0) {
        $Edits | ForEach-Object { Write-Host $_ }
        throw 'Source changes or unrelated untracked files found. Nothing was discarded.'
    }
    $Startup = Get-Content -LiteralPath 'addons\acm_extended\functions\fn_initForkStartupRuntime.sqf' -Raw
    if (-not $Startup.Contains('ACME_buildBatch = "B245";') -or
        -not $Startup.Contains('ACME_networkAuditRevision = "NA8-B245-1.2.4.1-candidate";')) {
        throw 'This checkout is not B245.'
    }
    if ($ServerKeysPath -and -not (Test-Path -LiteralPath $ServerKeysPath -PathType Container)) {
        throw 'The optional server keys folder does not exist.'
    }
    & $PythonExe @PythonPrefix $Tool preflight --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw 'Destination preflight failed. No build/deployment attempted.' }
    & $PythonExe @PythonPrefix (Join-Path $Repo 'tools\build_contract.py')
    if ($LASTEXITCODE -ne 0) { throw 'Current build identity contract failed. Nothing was deployed.' }
    hemtt check --error-on-all
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT check failed. Nothing was deployed.' }
    hemtt release
    if ($LASTEXITCODE -ne 0) { throw 'HEMTT release failed. Nothing was deployed.' }
    # Arma may have been launched during the build. Recheck before touching targets.
    if (Get-Process -Name arma3,arma3_x64,arma3server,arma3server_x64 -ErrorAction SilentlyContinue) {
        throw 'Arma started during the build. Close it and rerun; no installation files replaced.'
    }
    $DeployArgs = @('deploy', '--repo', $Repo)
    if ($ServerKeysPath) { $DeployArgs += @('--server-keys', $ServerKeysPath) }
    & $PythonExe @PythonPrefix $Tool @DeployArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'Deployment did not succeed. Read the error; an unfinished journal requires -Recover. Do not launch an unverified installation.'
    }
    Write-Host "B245 deployed and verified in $Repo and its existing .hemttout\build path."
    Write-Host 'Confirm 1.2.4.1 / B245 in-game. Server and all clients/HCs must use the same complete build.'
    Write-Host 'Nothing was pushed or published by this helper.'
} finally { Pop-Location }
