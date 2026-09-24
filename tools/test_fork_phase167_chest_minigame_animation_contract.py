#!/usr/bin/env python3
"""RC24: chest-seal/auscultation animation handoff + supine-exit contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_every_chest_start_normalizes_posterior_patient_first():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    treatment = read("addons/core/overrides/fnc_treatment.sqf")
    before_carrier = acquire.index("// Existing custody belongs")
    front = acquire.index("// Every chest procedure starts anterior-up")
    assert front < before_carrier
    assert '[_patient,"front",false,_medic,_preserveHead] call ACME_fnc_chestSealRoll' in acquire
    assert '"chestAccessFrontRoll"' in acquire
    assert "private _frontRollPending = false;" in acquire
    assert "if (_frontRollPending) exitWith {true};" in acquire
    assert "private _needsFrontNormalize" in treatment
    assert '_actualChestSide == "back"' in treatment

def test_chestseal_opens_on_frozen_medic4_to_workspace_handoff():
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    open_fn = read("addons/acm_extended/functions/fn_chestSealOpen.sqf")
    hold = read("addons/acm_extended/functions/fn_chestSealProviderHoldStart.sqf")
    assert '{_ctx != "chestseal"}' in acquire
    assert '_mode == "chestAccess" && {_stage >= 3}' in open_fn
    assert open_fn.index("ACME_fnc_chestSealProviderHoldStart") < open_fn.index('"ACME_ChestSeal_Dialog"')
    assert '[_medic, "chestAccess", _accessEpoch, true] call ACME_fnc_treatmentPoseStop' in hold

def test_workspace_is_hands_on_chest_without_medic3():
    cfg = read("addons/acm_extended/config.cpp")
    init = read("addons/acm_extended/functions/fn_initChestSealProcedureRuntime.sqf")
    assert "class ACME_ChestSealWorkspace: ACM_CPR_Stop" in cfg
    assert "class ACME_ChestSealWorkspace: AinvPknlMstpSnonWnonDnon_medic3" not in cfg
    assert '["chestSealWorkspace"' not in init

def test_medic3_is_reserved_for_actual_seal_placement():
    pose = read("addons/acm_extended/functions/fn_treatmentPoseStart.sqf")
    apply = read("addons/acm_extended/functions/fn_chestSealApply.sqf")
    burp = read("addons/acm_extended/functions/fn_chestSealBurp.sqf")
    thora = read("addons/acm_extended/functions/fn_thoraAftercareLocal.sqf")
    dispatch = read("addons/acm_extended/functions/fn_ownerDispatch.sqf")
    assert 'case "chestSeal": {"AinvPknlMstpSnonWrflDnon_medic3"};' in pose
    assert '[_medic,"chestSeal",2.0,_patient] call ACME_fnc_treatmentPoseStart' in apply
    assert "ACME_fnc_chestSealProviderHoldStart" in apply
    assert "chestSealBurpGesture" not in burp
    assert "chestSealBurpGesture" not in thora
    assert 'case "chestSealBurpGesture"' not in dispatch

def test_flip_never_turns_provider_failure_into_patient_noop():
    # Provider acquisition failure now aborts the physical Flip instead of bypassing medic4.
    # The workspace is restored and the user can retry without moving the casualty out of sequence.
    flip = read("addons/acm_extended/functions/fn_chestSealFlip.sqf")
    assert "if (!_started) exitWith" in flip
    fallback = flip.split("if (!_started) exitWith", 1)[1].split("private _args =",1)[0]
    assert 'call ACME_fnc_chestSealRoll' not in fallback
    assert '["ACME_CS_FlipPendingToken",""]' in fallback
    assert '["ACME_CS_FlipLockedUntil",0]' in fallback
    assert '["ACME_CS_FlipTarget",""]' in fallback
    assert "ACME_fnc_chestSealProviderHoldStart" in fallback
    assert 'ACME_DP_PauseTreatmentClass' in fallback
    assert 'ACME_DP_Paused",false' in fallback
    assert "ACME_CS_ApplyGestureUntil" in flip

def test_workspace_handoff_is_valid_empty_hands_source():
    prep = read("addons/acm_extended/functions/fn_medicAnimationPrep.sqf")
    assert '"acme_chestsealworkspace"' in prep
    assert "private _ownedEmptyState" in prep

def test_chestseal_and_stethoscope_use_semifowler_putdown_exit():
    chest = read("addons/acm_extended/functions/fn_chestSealClose.sqf")
    steth = read("addons/acm_extended/functions/fn_stethoscopeClose.sqf")
    steth_controller = read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    restore = read("addons/acm_extended/functions/fn_chestAccessVestRestore.sqf")
    head = read("addons/acm_extended/functions/fn_headElevMedicSeq.sqf")

    assert '[_flipMedic,"lower"] call ACME_fnc_headElevMedicSeq' in chest
    assert '[_medic,"lower"] call ACME_fnc_headElevMedicSeq' in steth
    assert '[_flipMedic,_poseMode,_poseEpoch,true] call ACME_fnc_treatmentPoseStop' in chest
    assert '[_medic,"stethoscope",_poseEpoch,true] call ACME_fnc_treatmentPoseStop' in steth
    assert steth_controller.count('"stethoscope", _poseEpoch, true') >= 2
    assert '"chestAccessVestProvider", [_medic, _patient, "start"' not in restore

    # Verify this really is the requested Semi-Fowler Putdown/inventory sequence.
    assert '"AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown"' in head
    assert '"AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon"' in head
    assert 'private _rest = "AmovPknlMstpSnonWnonDnon";' in head


def test_chest_minigame_exits_always_leave_patient_supine():
    chest_end = read("addons/acm_extended/functions/fn_chestSealPatientEnd.sqf")
    steth_close = read("addons/acm_extended/functions/fn_stethoscopeClose.sqf")
    restore = read("addons/acm_extended/functions/fn_chestAccessVestRestore.sqf")

    assert "_preSide" not in chest_end
    assert "ACM_airway_fnc_setRecoveryPosition" not in chest_end
    assert '[_patient, "front"] call ACME_fnc_patientRollCancel;' in chest_end
    assert '[_patient,"front"] call ACME_fnc_patientRollCancel;' in steth_close
    assert "// Every chest-access exit normalizes anterior-up" in restore
    assert restore.index("// Every chest-access exit normalizes anterior-up") < restore.index("// Nothing is in custody.")

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc24: chest minigame animation + supine-exit contract")
