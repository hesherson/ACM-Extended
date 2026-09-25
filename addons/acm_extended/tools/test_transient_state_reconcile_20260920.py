from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

def acme(name):
    return read(ROOT / "functions" / name)

def test_owner_runs_central_reconciliation():
    assert "ACME_fnc_transientStateReconcile" in acme("fn_ownerRegister.sqf")
    assert "ACME_fnc_providerStateReconcile" in acme("fn_ownerInit.sqf")

def test_reconciler_covers_high_risk_transient_state():
    src = acme("fn_transientStateReconcile.sqf")
    for needle in [
        "ACM_breathing_BVM_session",
        "ACM_circulation_CPR_session",
        "ACME_hang_Medic",
        "ACME_DP_press_%1",
        "ACM_damage_BandageProgress",
        "ACME_Junc_Packing_%1",
        "ACME_Junc_AAJTApplying",
        "ACM_circulation_IV_Bags_Active",
        "ACM_circulation_FluidBagsFlow_IV",
        "ACME_IV_BandState_%1",
        "ACME_patientAnimLock",
    ]:
        assert needle in src

def test_bag_map_self_heals_active_flag():
    src = read(ADDONS / "circulation/functions/fnc_getBloodVolumeChange.sqf")
    assert "private _hasFluidBags" in src
    assert "IV_Bags_Active), _hasFluidBags, true" in src
    assert "if (_hasFluidBags) then {" in src

def test_networked_transient_deadlines_use_server_time():
    assert "private _now = serverTime;" in acme("fn_patientAnimRequest.sqf")
    assert "> serverTime" in acme("fn_treatmentPatientSettle.sqf")
    chest_begin = acme("fn_chestSealPatientBegin.sqf")
    # Readiness is acknowledged after actual roll/custody completion, never a nominal future finish time.
    assert 'serverTime + _rollTime + 0.08' not in chest_begin
    assert 'ACME_CS_rollToken' in chest_begin
    assert 'ACME_CS_ProcedureReadyAt", serverTime' in chest_begin
    assert "serverTime < _readyAt" in acme("fn_chestSealOpen.sqf")

def test_progressive_bandage_and_junctional_clocks_are_shared():
    start = read(ADDONS / "damage/functions/fnc_bandageProgressStart.sqf")
    wound = read(ADDONS / "core/overrides/fnc_updateWoundBloodLoss.sqf")
    junc = acme("fn_junctionalStartBleed.sqf")
    assert "serverTime, _duration, _classname" in start
    assert "serverTime - _started" in wound
    assert "serverTime - _startedAt" in wound
    assert "serverTime - _started" in junc
    assert "serverTime - _stamp < 25" in junc

def test_surgical_airway_reserves_only_after_controller_accepts():
    src = read(ADDONS / "airway/functions/fnc_establishSurgicalAirway.sqf")
    start_i = src.index("[[_medic, _patient, \"head\"], { // On Start")
    reserve_i = src.index("SurgicalAirway_InProgress), true, true")
    assert reserve_i > start_i
    # The live continuous-action controller owns the reservation lifetime. Replicated
    # session metadata was retired because UI clicks are not treatment-lifetime events.
    assert "SurgicalAirway_InProgress_Session" not in src


def test_reconciler_does_not_guess_surgical_airway_session_lifetime():
    src = acme("fn_transientStateReconcile.sqf")
    assert "Do not clear SurgicalAirway_InProgress" in src
    assert "SurgicalAirway_InProgress_Session" not in src

def test_direct_pressure_part_is_replicated():
    for name in ["fn_directPressureLimb.sqf","fn_directPressureTorso.sqf","fn_directPressureSelf.sqf"]:
        assert 'setVariable ["ACME_DP_Part", _bodyPart, true]' in acme(name)

def test_transfusion_menu_explains_real_flow_blocks():
    src = read(ADDONS / "circulation/functions/fnc_openTransfusionMenu.sqf")
    assert "IV placement band is still applied" in src
    assert "AAJT-S compression is physically occluding" in src
    assert "No forward perfusion during cardiac arrest" in src
    assert 'ctrlSetText "Flow physically blocked"' in src
