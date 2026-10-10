#!/usr/bin/env python3
"""Current chest choreography rollback guard."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8",errors="replace")
def test_chest_prep_wraps_native_treatment_without_owning_a_continuous_session():
    treatment=read("addons/core/overrides/fnc_treatment.sqf")
    start=treatment.index("// Chest-access preparation is a physical gear transaction")
    end=treatment.index("// Auscultation owns its own modal display",start)
    block=treatment[start:end]
    assert "ACME_chestAccessPreflightActive" in block and "ACME_chestAccess_readyLease" in block
    assert "ACM_core_fnc_treatmentNative" in block and "ace_medical_treatment_fnc_treatment;" not in block
    assert "ACM_core_fnc_beginContinuousAction" not in block
    assert "ACM_core_ContinuousAction_Session" not in block
    assert "ACM_core_ContinuousAction_Kind" not in block
def test_patient_readiness_and_stethoscope_lifecycle_remain_separate():
    acquire=read("addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf")
    provider=read("addons/acm_extended/functions/fn_chestAccessVestProvider.sqf")
    use=read("addons/breathing/functions/fnc_useStethoscope.sqf")
    begin=read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    config=read("addons/acm_extended/config.cpp")
    assert '"ACME_HeadElevPatientGrab"' in acquire
    assert "ACME_chestAccessProviderReady" in acquire and "ACME_chestAccessProviderReady" in provider and "4.75" in acquire
    assert "_entryEpoch" not in use and "ACME_fnc_beginStethoscopeAction" in use
    assert 'getVariable ["ACM_core_ContinuousAction_Session", []]) isEqualTo [_patient, _epoch]' in begin
    assert begin.index("_args call _onStart;") < begin.index('call ACME_fnc_treatmentPoseStart;')
    assert "class ACME_ChestSealWorkspace:" in config
