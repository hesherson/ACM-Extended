from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "addons/acm_extended/functions"

def read(name):
    return (F / name).read_text(encoding="utf-8", errors="replace")

def test_direct_pressure_uses_mmb_only_and_keeps_keyboard_free():
    guard = read("fn_installRmbCancelGuard.sqf")
    assert "(_button isEqualTo 1) && {_hang}" in guard
    assert "(_button isEqualTo 2) && {_dp}" in guard
    assert "MMB" in guard
    for name in ("fn_directPressureTorso.sqf","fn_directPressureLimb.sqf","fn_directPressureSelf.sqf"):
        src = read(name)
        assert '["", "Stop Direct Pressure", ""] call ace_interaction_fnc_showMouseHint;' in src
        assert "0x01" not in src
        assert "0x23" not in src

def test_direct_pressure_site_claim_is_patient_owner_atomic():
    start = read("fn_directPressureStart.sqf")
    claim = read("fn_directPressureClaimLocal.sqf")
    ack = read("fn_directPressureClaimAck.sqf")
    stop = read("fn_directPressureStop.sqf")
    owner = read("fn_ownerDispatch.sqf")
    reconcile = read("fn_transientStateReconcile.sqf")
    provider = read("fn_providerStateReconcile.sqf")
    runtime = read("fn_registerProviderStanceReleaseRuntime.sqf")
    cfg = (ROOT / "addons/acm_extended/config.cpp").read_text(encoding="utf-8", errors="replace")

    assert '"directPressureClaim"' in start
    assert "ACME_DP_ClaimPending" in start
    assert 'case "directPressureClaim"' in owner
    assert "ACME_DP_claim_%1" in claim
    assert "ACME_directPressureClaimAck" in claim
    assert "ACME_DP_ClaimToken" in ack
    assert '"release"' in stop and "ACME_DP_ClaimToken" in stop
    assert "ACME_reconcileInvalidDPClaim_%1" in reconcile
    assert "Cleared stale Direct Pressure claim request" in provider
    assert '["ACME_directPressureClaimAck"' in runtime
    assert "class directPressureClaimLocal {};" in cfg
    assert "class directPressureClaimAck {};" in cfg
    assert "ACME_DP_ClaimPending" in cfg

def test_minigame_input_recovers_from_lost_keyup_and_fallback_mode_is_truthful():
    inp = read("fn_minigameInput.sqf")
    install = read("fn_minigameInputInstall.sqf")
    open_src = read("fn_minigameOpen.sqf")
    assert "ACME_InputLastAt" in inp
    assert "(diag_tickTime - _lastInputAt) > 1.5" in inp
    assert '_held = createHashMap;' in inp
    assert 'ACME_InputLastAt", diag_tickTime' in install
    parent_fallback = open_src.split("private _parent = findDisplay 46;",1)[1].split("// close every open dialog first.",1)[0]
    assert 'ACME_minigame_openedAsDisplay", false' in parent_fallback
    assert "createDialog _dialogClass" in parent_fallback

def test_owner_recovery_sweep_is_throttled_without_slowing_provider_repair():
    owner_init = read("fn_ownerInit.sqf")
    assert 'ACME_ownerRecoveryNextAt' in owner_init
    assert 'CBA_missionTime + 4' in owner_init
    assert '[] call ACME_fnc_providerStateReconcile;' in owner_init
    assert '}, 1, []] call CBA_fnc_addPerFrameHandler;' in owner_init

def test_release_identity_regressions_match_current_124_branch():
    version = (ROOT / "tools/test_fork_phase105_public_version_gate.py").read_text(encoding="utf-8")
    perf = (ROOT / "tools/test_fork_phase161_medical_ui_performance.py").read_text(encoding="utf-8")
    assert "EXPECTED = '1.2.4'" in version
    assert "ACME_buildBatch" in perf and "ACME_debugRevision" in perf
    assert '"B134"' not in perf and '"rc18"' not in perf

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("player grievance fixes: PASS")
