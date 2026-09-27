from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUN = ROOT / "functions"

def read(name):
    return (FUN / name).read_text(encoding="utf-8", errors="replace")

def test_single_authority_excludes_manual_prone_obtunded_and_stale_procedure_state():
    src = read("fn_chestSealCanPhysicalRoll.sqf")
    assert 'ACE_isUnconscious' in src
    assert 'ace_medical_unconscious' in src
    assert 'ACM_core_Lying_State' in src
    assert 'ACM_LyingState' in src
    assert 'stance _patient' not in src
    assert 'ACME_obtunded' not in src
    assert 'ACME_CS_ProcedureGrounded' in src  # documentation only
    # It must require actual lying/rest animation after wake, not just a possibly stale logical flag.
    assert 'animationState _patient' in src
    assert 'ace_medical_engine_uncon_anim_faceup' in src
    assert 'ace_medical_engine_uncon_anim_facedown' in src

def test_flip_button_uses_only_authoritative_roll_eligibility():
    src = read("fn_chestSealFlip.sqf")
    assert 'ACME_fnc_chestSealCanPhysicalRoll' in src
    assert 'stance _patient' not in src
    assert 'ACME_obtunded' not in src
    assert 'ACME_CS_ProcedureGrounded' not in src
    assert 'ACME_CS_VirtualFlip", true' in src

def test_flip_waits_for_exact_medic4_then_patient_owner_rechecks_authority():
    click = read("fn_chestSealFlip.sqf")
    tick = read("fn_chestSealFlipTick.sqf")
    roll = read("fn_chestSealRoll.sqf")
    assert '[_provider, "chestSealFlip", _patient] call ACME_fnc_rollProviderStart' in click
    assert '[_provider, "chestSealFlip", _patient, true] call ACME_fnc_rollProviderStart' not in click
    assert 'call ACME_fnc_chestSealRoll' not in click
    dispatch = tick.index('call ACME_fnc_chestSealRoll')
    assert '_work == "ainvpknlmstpsnonwnondnon_medic4"' in tick[:dispatch]
    assert '(toLowerANSI animationState _provider) == _work' in tick[:dispatch]
    assert '[_patient,_side,false,_provider,false] call ACME_fnc_chestSealRoll;' in tick
    assert '[_patient,_side,false,_provider,false,true] call ACME_fnc_chestSealRoll;' not in tick
    gate = roll.index('if !([_patient] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {};')
    anim = roll.index('call ACME_fnc_patientAnimRequest')
    assert gate < anim
    assert 'private _animPriority = [1, 2] select _immediate;' in roll

def test_patient_owner_rejects_stale_or_remote_roll_before_side_effects():
    src = read("fn_chestSealRoll.sqf")
    gate = src.index('if !([_patient] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {};')
    head = src.index('call ACME_fnc_headElevYieldForRoll')
    anim = src.index('call ACME_fnc_patientAnimRequest')
    assert gate < head < anim
    assert 'stance _patient' not in src
    assert 'ACME_obtunded' not in src
    assert 'ACME_CS_ProcedureGrounded' not in src
    # Both delayed animation callbacks must re-check live eligibility.
    assert src.count('call ACME_fnc_chestSealCanPhysicalRoll') >= 3

def test_workspace_open_and_close_cannot_convert_conscious_prone_into_roll_permission():
    begin=read("fn_chestSealPatientBegin.sqf")
    assert 'private _preGrounded = [_patient] call ACME_fnc_chestSealCanPhysicalRoll;' in begin
    assert 'stance _patient) == "PRONE"' not in begin
    from test_historical_chest_workspace import (
        test_workspace_close_never_forces_conscious_mobile_prone_into_unconscious_pose,
        test_common_carrier_restore_does_not_override_a_denied_roll,
    )
    for carrier in (False,True):
        for state in ('', '_patient setVariable ["ACME_CS_ProcedureGrounded",true];',
                      '_patient setVariable ["ACM_core_Lying_State",true];'):
            test_workspace_close_never_forces_conscious_mobile_prone_into_unconscious_pose(state,carrier)
        for context in ('access','chestseal'):
            test_common_carrier_restore_does_not_override_a_denied_roll(context,carrier)
