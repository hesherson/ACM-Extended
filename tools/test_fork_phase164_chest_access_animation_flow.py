#!/usr/bin/env python3
"""RC20: chest-access animation choreography must wrap, never own, clinical action lifetime."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_patient_release_finishes_supine_and_workspace_state_exists():
    s = read("addons/acm_extended/config.cpp")
    release = s.split("class ACME_HeadElevPatientRelease:", 1)[1][:500]
    assert 'ConnectTo[] = {"ACM_LyingState", 0.1};' in release
    assert "class ACME_ChestSealWorkspace:" in s

def test_carrier_provider_is_literal_medic4_and_freezes_at_22():
    pose = read("addons/acm_extended/functions/fn_treatmentPoseStart.sqf")
    init = read("addons/acm_extended/functions/fn_initChestSealProcedureRuntime.sqf")
    assert 'case "chestAccess": {"AinvPknlMstpSnonWnonDnon_medic4"};' in pose
    assert '["chestAccess", 2.2]' in init
    assert '["chestSealWorkspace"' not in init

def test_patient_lift_waits_for_real_provider_medic4():
    provider = read("addons/acm_extended/functions/fn_chestAccessVestProvider.sqf")
    acquire = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    assert 'animationState _m) == "ainvpknlmstpsnonwnondnon_medic4"' in provider
    assert "ACME_chestAccessProviderReady" in provider
    wait_block = acquire.split("// After any Semi-Fowler lay-flat finishes", 1)[1]
    assert "ACME_chestAccessProviderReady" in wait_block
    assert "_args call _begin;" in wait_block
    # Patient-owner completion deliberately does NOT send a late provider stop packet anymore.
    assert '"stop", true, _token' not in acquire
    treatment = read("addons/core/overrides/fnc_treatment.sqf")
    assert '[_m, _p, "stop", true, ((_m getVariable ["ACME_chestAccessProvider", []]) param [2, ""])] call ACME_fnc_chestAccessVestProvider;' in treatment

def test_removal_order_is_lift_remove_park_release():
    s = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    begin = s.split("private _beginPatient = {", 1)[1].split("// After any Semi-Fowler lay-flat finishes", 1)[0]
    grab = begin.index('"ACME_HeadElevPatientGrab"')
    lower_stage = begin.index("// Start the lower interval from the callback that actually removes the")
    commit = begin.index("private _removed = [_p,_ctx,_savedVar,_propVar,_pfhVar] call _commit;", lower_stage)
    release = begin.index('"ACME_HeadElevPatientRelease"', commit)
    assert grab < lower_stage < commit < release
    commit_fn = s.split("private _commitRemoval = {", 1)[1].split("// Animation is allowed", 1)[0]
    assert commit_fn.index("removeVest _p") < commit_fn.index("ACME_fnc_chestAccessVestPark")

def test_restoration_is_patient_lift_revest_release_without_extra_provider_medic4():
    s = read("addons/acm_extended/functions/fn_chestAccessVestRestore.sqf")
    begin = s.split("private _beginRestore = {", 1)[1]
    grab = begin.index('"ACME_HeadElevPatientGrab"')
    revest = begin.index("_loadout set [4,+_saved]")
    release = begin.index('"ACME_HeadElevPatientRelease"')
    assert grab < revest < release
    assert '"chestAccessVestProvider", [_medic, _patient, "start"' not in s

def test_removed_carrier_has_one_fixed_world_target():
    a = read("addons/acm_extended/functions/fn_chestAccessVestPark.sqf")
    b = read("addons/acm_extended/functions/fn_chestSealParkCarrier.sqf")
    assert "ACME_chestFixedPark" in a
    assert "ACME_chestFixedPark" in b

def test_clinical_launch_is_native_and_generation_scoped():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    start = s.index("// Chest-access preparation is a physical gear transaction")
    end = s.index("// Auscultation owns its own modal display", start)
    block = s[start:end]
    assert "ACME_chestAccess_readyLease" in block
    assert "ACME_chestAccess_readyServer" in block
    assert "ACM_core_fnc_treatmentNative" in block
    assert "ace_medical_treatment_fnc_treatment;" not in block
    # Chest prep does not acquire/edit the continuous-action controller. A read-only DP handoff guard is allowed.
    assert "ACM_core_fnc_beginContinuousAction" not in block
    assert 'missionNamespace setVariable ["ACM_core_ContinuousAction_Active"' not in block

def test_chest_seal_workspace_hands_directly_to_standard_medic4_flip_and_back():
    flip = read("addons/acm_extended/functions/fn_chestSealFlip.sqf")
    tick = read("addons/acm_extended/functions/fn_chestSealFlipTick.sqf")
    close = read("addons/acm_extended/functions/fn_chestSealClose.sqf")
    assert '"ACME_CS_providerHoldEpoch", -1' in flip
    assert '[_provider, _oldMode, _oldEpoch, true] call ACME_fnc_treatmentPoseStop;' in flip
    assert '[_provider, "chestSealFlip", _patient] call ACME_fnc_rollProviderStart' in flip
    assert '[_provider, "chestSealFlip", _patient, true] call ACME_fnc_rollProviderStart' not in flip
    assert 'call ACME_fnc_chestSealRoll' not in flip
    assert '[_patient,_side,false,_provider,false] call ACME_fnc_chestSealRoll;' in tick
    assert '[_provider,"roll",_epoch] call ACME_fnc_treatmentPoseStop;' in tick
    assert '[_provider,"roll",_epoch,true] call ACME_fnc_treatmentPoseStop;' not in tick
    assert "ACME_fnc_chestSealProviderHoldStart" in tick
    assert "_providerCompleted" in tick
    assert "_providerDone" in tick
    assert 'ACME_fnc_headElevMedicSeq' in close
    assert '[_flipMedic,_poseMode,_poseEpoch,true] call ACME_fnc_treatmentPoseStop;' in close

def test_stethoscope_rolls_wait_for_medic4_hold_without_touching_dialog_lifetime():
    entry = read("addons/acm_extended/functions/fn_stethoscopeEntryFlipTick.sqf")
    flip = read("addons/acm_extended/functions/fn_stethoscopeFlipTick.sqf")
    use = read("addons/breathing/functions/fnc_useStethoscope.sqf")
    assert "_providerAtHold" in entry
    assert "_providerAtHold" in flip
    assert use.index('createDialog "ACM_breathing_Stethoscope_Dialog";') < use.index("call ACME_fnc_patientAnimRequest;")

def test_thoracostomy_waits_for_same_chest_access_transaction():
    s = read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    assert "ACME_chestAccess_readyLease" in s
    assert "ACME_chestAccess_readyServer" in s
    wait = s.split("ACME_chestAccess_readyLease", 1)[1]
    assert "CBA_fnc_waitUntilAndExecute" in wait

def test_semi_fowler_resume_cannot_overlap_carrier_restore():
    s = read("addons/acm_extended/functions/fn_headElevTryResume.sqf")
    assert "ACME_chestAccess_leases" in s
    assert "ACME_chestAccess_vestBusy" in s

def test_cric_acm_lifetime_regression_remains_removed():
    s = read("addons/airway/functions/fnc_establishSurgicalAirway.sqf")
    assert "SurgicalAirway_InProgress_Session" not in s
    assert "ContinuousAction_Session" not in s

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc20: chest access choreography contracts")
