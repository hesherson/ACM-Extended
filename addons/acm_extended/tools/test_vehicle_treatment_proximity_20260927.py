from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def test_same_vehicle_is_zero_effective_treatment_distance():
    s = read("addons/acm_extended/functions/fn_patientInteractionDistance.sqf")
    assert "private _medicVehicle = objectParent _medic;" in s
    assert "private _patientVehicle = objectParent _patient;" in s
    assert "if (!isNull _medicVehicle && {_medicVehicle isEqualTo _patientVehicle}) exitWith {0};" in s


def test_core_treatment_uses_vehicle_aware_proximity():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    assert "ACME_fnc_patientInteractionContact" in s
    contact = read("addons/acm_extended/functions/fn_patientInteractionContact.sqf")
    assert "ACME_fnc_patientInteractionDistance" in contact
    assert "_medicVehicle isEqualTo _patientVehicle" in contact
    assert "(_m distance _p) > ace_medical_gui_maxDistance" not in s


def test_chest_workspace_does_not_reject_vehicle_occupants():
    s = read("addons/acm_extended/functions/fn_chestSealOpen.sqf")
    assert "objectParent _m isNotEqualTo objectParent _p" in s
    assert "ACME_fnc_patientInteractionDistance" in s
    assert "|| {!isNull objectParent _m} || {!isNull objectParent _p}" not in s


def test_active_medication_push_uses_vehicle_aware_leash():
    start = read("addons/acm_extended/functions/fn_hardcorePushStart.sqf")
    tick = read("addons/acm_extended/functions/fn_hardcorePushTick.sqf")
    request = read("addons/acm_extended/functions/fn_medicationRequest.sqf")
    for s in (start, tick, request):
        assert "ACME_fnc_patientInteractionDistance" in s
    assert "ACE_player distance _patient > _leash" not in start
    assert "(_patient distance _medic) > _leash" not in tick


def test_direct_pressure_same_vehicle_does_not_fail_raw_seat_distance():
    s = read("addons/acm_extended/functions/fn_directPressureTick.sqf")
    assert "ACME_fnc_patientInteractionDistance" in s
    assert "(_medic distance _patient) > _leash" not in s


def test_continuous_actions_keep_same_vehicle_session_alive():
    core = read("addons/core/functions/fnc_beginContinuousAction.sqf")
    steth = read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    assert "ACME_fnc_patientInteractionContact" in core
    assert "objectParent _medic isNotEqualTo objectParent _patient" in steth
    for s in (core, steth):
        assert "(!_notInVehicle && _vehicleCondition)" in s


def test_timed_medical_progress_always_exempts_inside_vehicle_gate():
    treatment = read("addons/core/functions/fnc_treatmentNative.sqf")
    progress = read("addons/core/overrides/fnc_progressBar.sqf")

    # ACE progressBar validates general interaction against objNull. If a same-vehicle
    # branch removes isNotInside here, every timed treatment fails immediately in a vehicle.
    assert '["isNotInside", "isNotSwimming", "isNotInZeus"]' in treatment
    assert '_sameVehicleTreatment' not in treatment
    assert '[_player, objNull, _exceptions] call ACEFUNC(common,canInteractWith)' in progress
