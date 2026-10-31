#!/usr/bin/env python3
"""Stable B190: exposed-HPMK CPR and one-shot IO fluid syncope."""
from build_contract import assert_current_build as _assert_current_build
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_fully_wrapped_hpmk_still_blocks_body_cpr():
    s = read("addons/core/overrides/fnc_canTreatCached.sqf")
    wrapped = s.split("// fully wrapped:", 1)[1].split("// the dead-casualty override", 1)[0]
    assert '_state == "wrapped"' in wrapped
    assert '_part != "head"' in wrapped
    assert "_hpmkActions" in wrapped
    assert '"CPR"' not in s.split("private _hpmkActions =", 1)[1].split(";", 1)[0]


def test_exposed_hpmk_cpr_is_explicitly_body_targeted():
    cached = read("addons/core/overrides/fnc_canTreatCached.sqf")
    treatment = read("addons/core/overrides/fnc_treatment.sqf")

    assert '_state == "exposed"' in cached
    assert '(toLowerANSI _className) == "cpr"' in cached
    # Normalize the body selection before common eligibility; do not bypass provider checks.
    assert '_bodyPart = "body";' in cached
    assert '_part = "body";' in cached
    assert '[_caller, _target, toLowerANSI _bodyPart, _className] call ace_medical_treatment_fnc_canTreat' in cached
    assert cached.index('_bodyPart = "body";') < cached.index('private _allowed =') < cached.rindex('call ace_medical_treatment_fnc_canTreat')

    marker = treatment.index("// B190: the exposed HPMK overlay represents a physically open chest.")
    block = treatment[marker:treatment.index("private _medicVehicle", marker)]
    assert '(toLowerANSI _classname) == "cpr"' in block
    assert 'getVariable ["ACME_hpmk_state", ""]) == "exposed"' in block
    assert '_bodyPart = "Body";' in block
    assert '_this set [2, _bodyPart];' in block


def test_io_medication_never_uses_fluid_syncope_path_or_max_pain():
    s = read("addons/acm_extended/functions/fn_ioPainResponse.sqf")
    med = s.split('if (_mode == "medication") exitWith {', 1)[1].split('if (_mode != "fluid") exitWith {};', 1)[0]

    assert 'ACME_ioMedicationPainFloor' in med
    assert "ACME_ioFluidSyncopeEpisode_" not in med
    assert "setUnconscious" not in med
    assert '[["pain", 1, true]]' not in med


def test_io_fluid_eligibility_is_latched_from_first_fluid_on_line_generation():
    s = read("addons/acm_extended/functions/fn_ioPainResponse.sqf")

    assert 'ACME_medicationLineGenerations' in s
    assert 'private _generationKey = format ["%1:-1", _bodyPart];' in s
    assert 'private _episodeVar = format ["ACME_ioFluidSyncopeEpisode_%1", _bodyPart];' in s
    assert '_episode = [_lineGeneration, !_isUncon, false];' in s
    assert '_patient setVariable [_episodeVar, _episode, true];' in s

    # Once first-flow eligibility is false, waking later on the same IO cannot re-arm.
    assert 'private _eligible = _episode param [1, false];' in s
    assert 'if (!_eligible || {_consumed}) exitWith {};' in s


def test_io_fluid_syncope_is_consumed_before_delay_and_can_fire_only_once():
    s = read("addons/acm_extended/functions/fn_ioPainResponse.sqf")
    consume = s.index("_episode set [2, true];")
    schedule = s.index("CBA_fnc_waitAndExecute;", consume)
    assert consume < schedule

    callback = s[consume:schedule]
    assert 'ACME_ioFluidSyncopeDelay' in callback
    assert 'ACME_ioFluidSyncopeSeconds' in callback
    assert '[_patient, true, _transient, true] call ace_medical_fnc_setUnconscious;' in callback


def test_io_syncope_callback_validates_same_physical_io_generation():
    s = read("addons/acm_extended/functions/fn_ioPainResponse.sqf")
    callback = s.split('[{', 1)[1]

    assert 'ACME_medicationLineGenerations' in callback
    assert '(_generations getOrDefault [_generationKey, -1]) != _lineGeneration' in callback
    assert '([_patient] call ACME_fnc_clinicalEpoch) != _epoch' in callback


def test_io_line_generation_changes_on_every_io_placement_or_removal():
    s = read("addons/circulation/functions/fnc_setIVLocal.sqf")
    assert 'private _generationKey = format ["%1:%2",_bodyPart,if (_iv) then {_accessSite} else {-1}];' in s
    assert '_generations set [_generationKey,(_generations getOrDefault [_generationKey,0]) + 1];' in s


def test_build_identity_is_b190_stable():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    _assert_current_build()
    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B190 HPMK CPR / IO syncope regression: PASS")
