#!/usr/bin/env python3
"""Current minigame flip-cancellation regression."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; FUN=ROOT/"addons"/"acm_extended"/"functions"
def read(p): return p.read_text(encoding="utf-8",errors="replace")
def test_flip_cancel_releases_current_provider_and_patient_ownership():
    provider=read(FUN/"fn_rollProviderCancel.sqf"); patient=read(FUN/"fn_patientRollCancel.sqf")
    chest_close=read(FUN/"fn_chestSealClose.sqf"); chest_flip=read(FUN/"fn_chestSealFlip.sqf"); chest_tick=read(FUN/"fn_chestSealFlipTick.sqf")
    patient_end=read(FUN/"fn_chestSealPatientEnd.sqf"); steth_close=read(FUN/"fn_stethoscopeClose.sqf"); steth_flip=read(FUN/"fn_stethoscopeFlip.sqf"); steth_tick=read(FUN/"fn_stethoscopeFlipTick.sqf")
    owner=read(FUN/"fn_ownerDispatch.sqf"); cfg=read(ROOT/"addons"/"acm_extended"/"config.cpp")
    assert 'ACME_rollProviderPFH' in provider
    assert '[_medic, "roll", _epoch, true] call ACME_fnc_treatmentPoseStop;' in provider
    assert '_medic switchMove "";' in provider and 'setUnitPos "AUTO"' in provider
    assert 'setVariable ["ACME_CS_rollToken", "", false]' in patient and 'setVariable ["ACME_CS_rollUntil", -1, false]' in patient
    assert 'ACME_fnc_patientAnimRelease' in patient and 'ACME_CS_facing' in patient
    assert 'ACME_CS_FlipPFH' in chest_flip and 'ACME_CS_FlipPFH' in chest_tick and 'ACME_CS_FlipPFH' in chest_close
    assert '[_flipMedic,"chestSealFlip"] call ACME_fnc_rollProviderCancel;' in chest_close
    assert 'ACME_stethFlipPFH' in steth_flip and 'ACME_stethFlipPFH' in steth_tick and 'ACME_stethFlipPFH' in steth_close
    assert '[_medic,"stethoscopeFlip"] call ACME_fnc_rollProviderCancel;' in steth_close
    assert '[_patient,"front"] call ACME_fnc_patientRollCancel;' in steth_close
    assert 'private _rollActive' in patient_end and '[_patient, "front"] call ACME_fnc_patientRollCancel;' in patient_end
    assert '(_rollUntil - CBA_missionTime) + 0.08' not in patient_end
    assert 'case "patientRollCancel": {_args call ACME_fnc_patientRollCancel;};' in owner
    assert 'class rollProviderCancel {};' in cfg and 'class patientRollCancel {};' in cfg
