#!/usr/bin/env python3
"""RC19: preserve ACM dialog lifetimes for auscultation and surgical airway."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

def test_stethoscope_owns_a_real_continuous_session():
    s = read("addons/acm_extended/functions/fn_beginStethoscopeAction.sqf")
    assert '["session", [_patient, _epoch]]' in s
    assert '["lastSeen", CBA_missionTime]' in s
    assert 'call ACM_core_fnc_setContinuousActionState' in s
    assert "_medic isNotEqualTo ACE_player" not in s
    assert s.index("_args call _onStart;") < s.index('call ACME_fnc_treatmentPoseStart;')
    assert 'isNull _scopeDisplay' in s

def test_auscultation_ui_exists_before_presentation_work():
    s = read("addons/breathing/functions/fnc_useStethoscope.sqf")
    create = s.index('createDialog "ACM_breathing_Stethoscope_Dialog";')
    lung = s.index('call ACME_fnc_ownerDispatch;')
    patient_pose = s.index('call ACME_fnc_patientAnimRequest;')
    assert create < lung
    assert create < patient_pose

def test_auscultation_bypasses_generic_provider_preflight():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    direct = s.index('_nativeContinuousClass == "usestethoscope"')
    preflight = s.index("// Resolve ACME's provider-theatre policy BEFORE native treatment starts.")
    assert direct < preflight
    assert '_this call ACM_core_fnc_treatmentNative' in s[direct:direct + 400]

def test_core_continuous_action_does_not_depend_on_ace_player_identity():
    s = read("addons/core/functions/fnc_beginContinuousAction.sqf")
    assert "_medic isNotEqualTo ACE_player" not in s

def test_surgical_airway_uses_base_acm_dialog_lifetime():
    s = read("addons/airway/functions/fnc_establishSurgicalAirway.sqf")
    assert "SurgicalAirway_InProgress_Session" not in s
    assert "ContinuousAction_Session" not in s
    assert '_patient setVariable [QGVAR(SurgicalAirway_InProgress), true, true];' in s
    assert '_patient setVariable [QGVAR(SurgicalAirway_InProgress), false, true];' in s

def test_stethoscope_unload_only_aborts_an_active_flip_and_clears_its_session():
    s = read("addons/acm_extended/functions/fn_stethoscopeClose.sqf")
    assert 'private _flipWasActive = _display getVariable ["ACME_stethFlipActive", false];' in s
    assert "if (_flipWasActive) then" in s
    assert '["session", []]' in s
    assert 'call ACM_core_fnc_setContinuousActionState' in s

def test_transient_reconcile_does_not_own_cric_dialog_lifetime():
    s = read("addons/acm_extended/functions/fn_transientStateReconcile.sqf")
    assert "ACME_reconcileInvalidSurgicalAirwayAt" not in s
    assert "SurgicalAirway_InProgress_Session" not in s

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS rc19: ACM continuous-dialog lifetime regressions")
