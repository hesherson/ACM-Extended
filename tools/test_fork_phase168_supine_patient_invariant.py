#!/usr/bin/env python3
"""RC24: chest work and Semi-Fowler must always start/end anterior-up (patient lying on back)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_chest_start_rolls_front_before_any_carrier_theatre():
    s = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    assert s.index("// Every chest procedure starts anterior-up") < s.index("// Existing custody belongs")
    assert '[_patient,"front",false,_medic,_preserveHead] call ACME_fnc_chestSealRoll' in s
    assert "if (_frontRollPending) exitWith {true};" in s

def test_chest_restore_normalizes_front_even_with_no_carrier():
    s = read("addons/acm_extended/functions/fn_chestAccessVestRestore.sqf")
    normalize = s.index("// Every chest-access exit normalizes anterior-up")
    no_custody = s.index("// Nothing is in custody.")
    assert normalize < no_custody
    assert '[_patient,"front"] call ACME_fnc_patientRollCancel;' in s
    assert '[_patient,"front",false,objNull,true] call ACME_fnc_chestSealRoll;' in s
    assert 'private _actualBeforeRestore = [_patient, _patient getVariable ["ACME_CS_facing","front"]]' in s
    assert 'private _needFrontNormalize = !_frontNormalized' in s
    assert 'private _canRollFront = [_patient] call ACME_fnc_chestSealCanPhysicalRoll;' in s
    assert '[_patient,"front",false,objNull,true] call ACME_fnc_chestSealRoll;' in s
    # B267 preserves the original kit generation across BOTH deferred
    # front-normalization paths; a newer kit must not inherit this return.
    assert s.count('[_p,_force,_medic,_ctx,true,_kitEpoch] call ACME_fnc_chestAccessVestRestore;') == 2
    # A denied physical roll defers restoration; it does not force a rest animation.
    normalize_block = s[s.index('if (_needFrontNormalize) exitWith {'):s.index('_patient setVariable ["ACME_CS_facing","front",true];', s.index('if (_needFrontNormalize) exitWith {'))]
    assert 'ace_common_switchMove' not in normalize_block
    assert normalize_block.count('(_p getVariable ["ACME_equipmentKitEpoch", 0]) == _kitEpoch') == 2
    assert '["_frontNormalized", false, [false]]' in s

def test_chest_seal_never_restores_original_posterior_or_recovery_pose():
    s = read("addons/acm_extended/functions/fn_chestSealPatientEnd.sqf")
    assert "_preSide" not in s
    assert "_preRecovery" not in s
    assert "_preAnim" not in s
    assert '[_patient, "front"] call ACME_fnc_patientRollCancel;' in s
    assert '[_p, "front", false, objNull, true] call ACME_fnc_chestSealRoll;' in s
    assert 'setVariable ["ACME_CS_facing", "front", true]' in s
    assert "ACM_airway_fnc_setRecoveryPosition" not in s
    assert '"back", false' not in s

def test_auscultation_close_always_routes_to_supine_restore():
    s = read("addons/acm_extended/functions/fn_stethoscopeClose.sqf")
    assert '[_patient,"front"] call ACME_fnc_patientRollCancel;' in s
    assert "private _restoreDispatched = false;" in s
    assert '[_patient,false,_medic,"access",false] call ACME_fnc_chestAccessVestRestore;' in s

def test_semifowler_start_rolls_front_before_grab():
    s = read("addons/acm_extended/functions/fn_headElevateStart.sqf")
    roll = s.index('[_patient,"front",false,_medic,true] call ACME_fnc_chestSealRoll;')
    elevate = s.index('[_patient] call ACME_fnc_headElevApplyTilt;')
    assert roll < elevate
    assert "private _needFrontFirst" in s
    assert 'setVariable ["ACME_CS_facing","front",true]' in s

def test_semifowler_suspend_resume_and_lower_all_normalize_front_first():
    suspend = read("addons/acm_extended/functions/fn_headElevSuspend.sqf")
    resume = read("addons/acm_extended/functions/fn_headElevResume.sqf")
    lower = read("addons/acm_extended/functions/fn_headElevateStop.sqf")

    # A live Semi-Fowler episode is constructed face-up. These transitions must not
    # reclassify transient authored geometry and inject a redundant body roll.
    assert "// A live Semi-Fowler placement is already face-up." in suspend
    assert 'setVariable ["ACME_CS_facing","front",true]' in suspend
    assert 'call ACME_fnc_chestSealRoll' not in suspend

    assert "// Suspension ends in the stable face-up rest by construction." in resume
    assert 'setVariable ["ACME_CS_facing","front",true]' in resume
    assert 'call ACME_fnc_chestSealRoll' not in resume
    assert resume.index('setVariable ["ACME_CS_facing","front",true]') < resume.index("ACME_fnc_headElevApplyTilt")

    assert "// An active Semi-Fowler placement is already anterior-up by construction." in lower
    assert 'setVariable ["ACME_CS_facing","front",true]' in lower
    assert 'call ACME_fnc_chestSealRoll' not in lower
    assert lower.index('setVariable ["ACME_CS_facing","front",true]') < lower.index('"ACME_HeadElevPatientRelease"')


def test_semifowler_rest_animation_can_never_replay_face_down_base_pose():
    s = read("addons/acm_extended/functions/fn_headElevRestAnim.sqf")
    assert "ACME_headElev_baseAnim" not in s
    assert 'ACME_uncon_faceUp' in s
    assert "face-down" in s.lower()
    assert "_base" not in s

def test_front_semantics_still_mean_anterior_chest_up():
    s = read("addons/acm_extended/functions/fn_chestSealActualSide.sqf")
    assert '"front" means the casualty is supine / anterior chest up.' in s
    assert '"back"  means the casualty is prone / posterior chest up.' in s

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc24: absolute supine patient invariant")
