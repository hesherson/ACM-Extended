#!/usr/bin/env python3
"""Current junctional/chest-workspace source contracts."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; FUN=ROOT/"addons"/"acm_extended"/"functions"
def read(p): return p.read_text(encoding="utf-8",errors="replace")
def test_junctional_layers_keep_xstat_on_base_and_gauze_on_overlay():
    s=read(FUN/"fn_updateJunctionalImage.sqf")
    assert '_woundC ctrlShow (_state in ["open", "packed", "xstat"]);' in s
    assert '_packedC ctrlShow (_state == "packed");' in s
    assert 'if (_state == "xstat") then {_xstatTex} else {_openTex}' in s
    assert 'junctionalwound_packed_leftarm_ca.paa' in s and 'junctionalwound_xstat_leftarm_ca.paa' in s
    assert 'ctrlSetFade 0' in s
    for f in ("ACME_JuncVisualFadeStart","ACME_junctionalImageFadeInSec","ctrlCommit _left"): assert f not in s
def test_chest_access_and_workspace_choreography_is_current():
    acquire=read(FUN/"fn_chestAccessVestAcquire.sqf"); provider=read(FUN/"fn_chestAccessVestProvider.sqf")
    begin=read(FUN/"fn_chestSealPatientBegin.sqf"); openf=read(FUN/"fn_chestSealOpen.sqf"); tick=read(FUN/"fn_chestSealFlipTick.sqf"); close=read(FUN/"fn_chestSealClose.sqf")
    pose_start=read(FUN/"fn_treatmentPoseStart.sqf"); pose_stop=read(FUN/"fn_treatmentPoseStop.sqf"); runtime=read(FUN/"fn_initChestSealProcedureRuntime.sqf")
    cfg=read(ROOT/"addons"/"acm_extended"/"config.cpp"); treatment=read(ROOT/"addons"/"core"/"overrides"/"fnc_treatment.sqf")
    for t in ('"ACME_HeadElevPatientGrab"','"ACME_HeadElevPatientRelease"','removeVest _p;','ACME_fnc_headElevPinPose'): assert t in acquire
    assert 'ACME_chestAccessProviderReady' in provider
    assert 'case "chestAccess": {"AinvPknlMstpSnonWnonDnon_medic4"};' in pose_start
    assert '[_patient, _medic, "chestseal", false, "", "", _authority] call ACME_fnc_chestAccessVestAcquire;' in begin
    assert '[_p, _medic, "chestseal", false, "", "", _authority] call ACME_fnc_chestAccessVestAcquire;' in begin
    assert '(_p getVariable ["ACME_equipmentKitEpoch", 0]) != (_authority select 0)' in begin
    assert '(_p getVariable ["ACME_providerLocalityEpoch", 0]) != (_authority select 1)' in begin
    start=treatment.index("// Chest-access preparation is a physical gear transaction"); end=treatment.index("// Auscultation owns its own modal display",start); chest=treatment[start:end]
    assert "ACME_chestAccessPreflightActive" in chest and "ACME_chestAccess_readyServer" in chest and "ACME_chestAccess_readyLease" in chest
    assert "ACM_core_fnc_treatmentNative" in chest and "ace_medical_treatment_fnc_treatment;" not in chest
    assert 'class ACME_ChestSealWorkspace' in cfg and 'class chestSealProviderHoldStart {};' in cfg
    assert 'case "chestSealWorkspace": {"ACME_ChestSealWorkspace"};' in pose_start
    assert 'class ACME_ChestSealWorkspace: ACM_CPR_Stop' in cfg
    assert '["chestSealWorkspace", "AinvPknlMstpSnonWnonDnon_medicUp4"]' in runtime and '["_handoff", false' in pose_stop
    assert 'ACME_fnc_chestSealProviderHoldStart' in openf and 'ACME_fnc_chestSealProviderHoldStart' in tick and '"chestSealWorkspace"' in close
