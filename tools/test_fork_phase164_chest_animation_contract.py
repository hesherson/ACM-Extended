#!/usr/bin/env python3
"""RC20: chest-access animation choreography and clinical-lifetime regression guard."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_release_animation_finishes_supine():
    s = read("addons/acm_extended/config.cpp")
    block = s.split("class ACME_HeadElevPatientRelease:", 1)[1][:500]
    assert 'ConnectTo[] = {"ACM_LyingState", 0.1};' in block

def test_chest_workspace_move_exists():
    s = read("addons/acm_extended/config.cpp")
    assert "class ACME_ChestSealWorkspace:" in s
    assert "class ACME_ChestSealWorkspace: ACM_CPR_Stop" in s
    assert '"AinvPknlMstpSnonWnonDnon_medic4", 0.08' in s

def test_carrier_provider_uses_medic4_and_exact_ready_handshake():
    s = read("addons/acm_extended/functions/fn_chestAccessVestProvider.sqf")
    assert '[_medic, "chestAccess", -1, _patient] call ACME_fnc_treatmentPoseStart' in s
    assert '"ainvpknlmstpsnonwnondnon_medic4"' in s
    assert 'ACME_chestAccessProviderReady' in s
    assert '["stethoscope","inspect","chestSealWorkspace","roll"]' in s

def test_patient_lift_waits_for_provider_entry_but_fails_open():
    s = read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    wait = s.split("// After any Semi-Fowler lay-flat finishes", 1)[1]
    assert "ACME_chestAccessProviderReady" in wait
    assert "4.75" in wait
    assert '_patient setVariable [_readyVar, -1, true];' in s

def test_carrier_is_parked_at_one_world_target():
    access = read("addons/acm_extended/functions/fn_chestAccessVestPark.sqf")
    seal = read("addons/acm_extended/functions/fn_chestSealParkCarrier.sqf")
    assert "ACME_chestFixedPark" in access
    assert "ACME_chestFixedPark" in seal
    assert 'getVariable ["ACME_chestFixedPark", []]' in access
    assert 'getVariable ["ACME_chestFixedPark", []]' in seal

def test_restore_is_visible_reverse_sequence():
    s = read("addons/acm_extended/functions/fn_chestAccessVestRestore.sqf")
    begin = s.split("private _beginRestore = {", 1)[1]
    grab = begin.index('"ACME_HeadElevPatientGrab"')
    loadout = begin.index("call ACME_fnc_carrierInventoryRestore")
    release = begin.index('"ACME_HeadElevPatientRelease"')
    # B218 delegates exact carrier/cargo custody; do not restore the unsafe whole loadout.
    assert grab < loadout < release
    assert '"chestAccessVestProvider", [_medic, _patient, "start"' not in s

def test_chest_prep_launches_native_action_once():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    start = s.index("// Chest-access preparation is a physical gear transaction")
    end = s.index("// Auscultation owns its own modal display", start)
    block = s[start:end]
    assert "ACM_core_fnc_treatmentNative" in block
    assert "ace_medical_treatment_fnc_treatment" not in block
    assert "ACM_core_fnc_beginContinuousAction" not in block
    assert "ACM_core_ContinuousAction_Session" not in block
    assert "ACM_core_ContinuousAction_Kind" not in block
    assert "ACME_chestAccess_readyLease" in block

def test_chest_seal_workspace_hold_and_flip_handoff():
    start = read("addons/acm_extended/functions/fn_chestSealOpen.sqf")
    flip = read("addons/acm_extended/functions/fn_chestSealFlip.sqf")
    tick = read("addons/acm_extended/functions/fn_chestSealFlipTick.sqf")
    cfg = read("addons/acm_extended/functions/fn_initChestSealProcedureRuntime.sqf")
    assert "ACME_fnc_chestSealProviderHoldStart" in start
    assert '["chestSealWorkspace", "AinvPknlMstpSnonWnonDnon_medicUp4"]' in cfg
    assert '[_provider, _oldMode, _oldEpoch, true] call ACME_fnc_treatmentPoseStop;' in flip
    assert '[_provider,"roll",_epoch] call ACME_fnc_treatmentPoseStop;' in tick
    assert "ACME_fnc_chestSealProviderHoldStart" in tick

def test_workspace_close_uses_semifowler_provider_exit():
    s = read("addons/acm_extended/functions/fn_chestSealClose.sqf")
    assert '[_flipMedic,_poseMode,_poseEpoch,true] call ACME_fnc_treatmentPoseStop' in s
    assert '[_flipMedic,"chestsealexit",uiNamespace getVariable ["ACME_CS_SessionToken", ""]] call ACME_fnc_headElevMedicSeq' in s

def test_semi_fowler_waits_for_reverse_carrier_restore():
    s = read("addons/acm_extended/functions/fn_headElevTryResume.sqf")
    assert "ACME_chestAccess_vestBusy" in s
    assert "ACME_chestAccess_leases" in s

def test_auscultation_and_cric_lifetime_fixes_remain_intact():
    steth = read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    cric = read("addons/airway/functions/fnc_establishSurgicalAirway.sqf")
    reconcile = read("addons/acm_extended/functions/fn_transientStateReconcile.sqf")
    assert 'getVariable ["ACM_core_ContinuousAction_Session", []]) isEqualTo [_patient, _epoch]' in steth
    assert "_medic isNotEqualTo ACE_player" not in steth
    assert "SurgicalAirway_InProgress_Session" not in cric
    assert "ACME_reconcileInvalidSurgicalAirwayAt" not in reconcile

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc20: chest animation choreography contracts")
