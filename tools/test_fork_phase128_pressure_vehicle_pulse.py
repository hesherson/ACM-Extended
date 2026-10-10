"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase128_pressure_vehicle_pulse():
    #!/usr/bin/env python3
    """Phase 128: direct pressure keeps manual Stop plus AED-style leash; pulse checks work inside shared vehicles."""
    from pathlib import Path
    R=Path(__file__).resolve().parents[1]
    F=R/'addons/acm_extended/functions'
    tick=(F/'fn_directPressureTick.sqf').read_text()
    cfg=(R/'addons/acm_extended/config.cpp').read_text()
    pulse=(R/'addons/circulation/functions/fnc_feelPulse.sqf').read_text()
    assert 'class ACME_StopDirectPressure: CheckPulse' in cfg
    assert 'objectParent _medic' in tick and 'objectParent _patient' in tick
    assert '_medicVehicle isNotEqualTo _patientVehicle' in tick
    assert '([_medic, _patient] call ACME_fnc_patientInteractionDistance) > _leash' in tick
    proximity=(F/'fn_patientInteractionDistance.sqf').read_text()
    assert '!isNull _medicVehicle && {_medicVehicle isEqualTo _patientVehicle}) exitWith {0}' in proximity
    assert 'private _distance = _medic distance _patient;' in proximity
    assert 'private _medicVehicle = objectParent _medic' in pulse
    assert '_medicVehicle isNotEqualTo _patientVehicle' in pulse
    vehicle_branch=pulse[pulse.index('// Vehicle-safe path.'):pulse.index('ace_medical_gui_pendingReopen')]
    assert 'ace_medical_treatment_fnc_checkPulseLocal' in vehicle_branch
    assert 'closeDialog' not in vehicle_branch
    print('PASS phase128: pressure has manual stop + AED-style leash and pulse palpation is vehicle-safe')


if __name__ == "__main__":
    test_current_phase128_pressure_vehicle_pulse()
