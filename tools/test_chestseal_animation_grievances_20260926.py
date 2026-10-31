from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "addons/acm_extended/functions"

def read(name):
    return (F / name).read_text(encoding="utf-8", errors="replace")

def test_seal_placement_is_exact_unarmed_medic3_for_265_seconds():
    init = read("fn_initChestSealProcedureRuntime.sqf")
    pose = read("fn_treatmentPoseStart.sqf")
    apply = read("fn_chestSealApply.sqf")
    assert "ACME_CS_applyAnimSeconds = 2.65;" in init
    assert 'case "chestSeal": {"AinvPknlMstpSnonWnonDnon_medic3"};' in pose
    assert '[_medic, "chestSeal", _duration, _patient] call ACME_fnc_treatmentPoseStart' in apply
    assert 'private _endsAt = diag_tickTime + _duration;' in apply
    assert 'call ACME_fnc_doAnim' not in apply
    assert 'uiNamespace setVariable ["ACME_CS_ApplyPFH", -1];' in apply
    assert '[_m, "chestSeal", _epoch, _restoreWorkspace] call ACME_fnc_treatmentPoseStop;' in apply
    assert '}, [_medic, _patient, _placeEpoch, _serial], _duration] call CBA_fnc_waitAndExecute;' in apply
    assert '[_m, _p] call ACME_fnc_chestSealProviderHoldStart' in apply

def test_medic1_is_ncd_only_not_chest_seal_apply():
    pose = read("fn_treatmentPoseStart.sqf")
    apply = read("fn_chestSealApply.sqf")
    ncd = read("fn_chestSealApplyNCD.sqf")
    assert 'case "ncdSeat": {"AinvPknlMstpSnonWnonDnon_medic1"};' in pose
    assert '[_medic,"ncdSeat",2.0,_patient] call ACME_fnc_treatmentGesture' in ncd
    assert 'call ACME_fnc_treatmentGesture' not in apply
    assert '[_medic,"ncdSeat"' not in apply
    assert '[_medic, "ncdSeat"' not in apply
    assert '"ncdSeat"' in apply  # cancellation-only: an old NCD pose must be retired before medic3 starts
    assert apply.index('call ACME_fnc_treatmentPoseStop') < apply.index('"chestSeal", _duration, _patient] call ACME_fnc_treatmentPoseStart')

def test_flip_preempts_apply_then_uses_standard_medic4_provider_path():
    flip = read("fn_chestSealFlip.sqf")
    tick = read("fn_chestSealFlipTick.sqf")
    assert 'if ((uiNamespace getVariable ["ACME_CS_ApplyGestureUntil",0]) > _now) exitWith {};' not in flip
    assert 'ACME_CS_ApplyPFH' in flip and 'ACME_CS_ApplyAnimSerial' in flip
    assert '[_provider, _oldMode, _oldEpoch, true] call ACME_fnc_treatmentPoseStop;' in flip
    assert 'selectWeapon' not in flip
    assert 'ACME_medicAnimationPrep' not in flip
    assert '[_provider, "chestSealFlip", _patient] call ACME_fnc_rollProviderStart' in flip
    assert '[_provider, "chestSealFlip", _patient, true] call ACME_fnc_rollProviderStart' not in flip
    assert 'call ACME_fnc_chestSealRoll' not in flip
    assert flip.index("ACME_CS_ApplyAnimSerial") < flip.index("call ACME_fnc_rollProviderStart")
    assert flip.index("call ACME_fnc_treatmentPoseStop") < flip.index("call ACME_fnc_rollProviderStart")
    assert '[_patient,_side,false,_provider,false] call ACME_fnc_chestSealRoll;' in tick

def test_flip_waits_only_for_exact_medic4_state_before_patient_roll():
    tick = read("fn_chestSealFlipTick.sqf")
    assert tick.count("call ACME_fnc_chestSealRoll") == 1
    dispatch = tick.index("call ACME_fnc_chestSealRoll")
    assert '_work == "ainvpknlmstpsnonwnondnon_medic4"' in tick[:dispatch]
    assert '(toLowerANSI animationState _provider) == _work' in tick[:dispatch]
    assert '(_pose param [3,-2]) >= 1' in tick[:dispatch]
    assert '_args set [9,diag_tickTime]' in tick[:dispatch]
    assert "_providerDone" in tick
    assert "min 3.0" in read("fn_chestSealFlip.sqf")

def test_provider_and_patient_both_use_normal_interpolated_flip_paths():
    pose = read("fn_treatmentPoseStart.sqf")
    provider = read("fn_rollProviderStart.sqf")
    patient = read("fn_chestSealRoll.sqf")
    flip = read("fn_chestSealFlip.sqf")
    tick = read("fn_chestSealFlipTick.sqf")
    assert 'case "roll": {"AinvPknlMstpSnonWnonDnon_medic4"};' in pose
    assert '[_medic, "roll", _duration, _patient, _forceImmediate] call ACME_fnc_treatmentPoseStart' in provider
    assert '[_provider, "chestSealFlip", _patient] call ACME_fnc_rollProviderStart' in flip
    assert '[_patient,_side,false,_provider,false] call ACME_fnc_chestSealRoll;' in tick
    assert '[_provider,"roll",_epoch] call ACME_fnc_treatmentPoseStop;' in tick
    assert '[_provider,"roll",_epoch,true] call ACME_fnc_treatmentPoseStop;' not in tick
    assert 'private _animPriority = [1, 2] select _immediate;' in patient
    assert 'private _lockPriority = [3, 100] select _immediate;' in patient

def test_apply_generation_is_retired_on_flip_close_and_reopen():
    flip = read("fn_chestSealFlip.sqf")
    close = read("fn_chestSealClose.sqf")
    init = read("fn_chestSealInit.sqf")
    for src in (flip, close, init):
        assert "ACME_CS_ApplyPFH" in src
        assert "ACME_CS_ApplyAnimSerial" in src
        assert "ACME_CS_ApplyGestureUntil" in src

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("chest-seal animation grievance fixes: PASS")
