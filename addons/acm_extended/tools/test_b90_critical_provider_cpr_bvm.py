from historical_source import read_source, assert_release_identity
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8', errors='replace')


def test_examine_is_one_click_for_common_assessments():
    src = txt('functions/fn_menuExamineGroups.sqf')
    groups = json.loads(src[src.index('\n[') + 1:])
    assert [g[1] for g in groups] == ['Monitoring Equipment', 'Injuries & IV Sites', 'Debug']
    grouped = {name for _, _, names, _ in groups for name in names}
    for cls in [
        'checkresponse', 'slapawake', 'acme_assesspupils',
        'checkpulse', 'checkbloodpressure', 'checkcapillaryrefill',
        'acme_inspectchest', 'usestethoscope',
        'acme_feelskin', 'acme_checktemperature', 'acme_readcoretemp',
        'acme_elevatehead', 'acme_lowerhead',
    ]:
        assert cls not in grouped, cls


def test_elevated_death_uses_normal_patient_release_animation():
    death = txt('functions/fn_headElevDeathRelease.sqf')
    stop = txt('functions/fn_headElevateStop.sqf')
    release = '[_patient, "ACME_HeadElevPatientRelease", 2] call ACME_fnc_doAnim;'
    assert release in stop
    assert release in death
    assert '[_patient, false] call ACME_fnc_headElevCollision;' in death
    assert '[_p, true] call ACME_fnc_headElevCollision;' in death
    # Death cleanup must never start a provider animation.
    assert 'headElevMedicSeq' not in death


def test_head_position_provider_releases_stance_lock_after_crouched_finish():
    seq = txt('functions/fn_headElevMedicSeq.sqf')
    cancel = txt('functions/fn_headElevateCancelSeq.sqf')
    assert '[_u, _rest, 2] call ACME_fnc_doAnim;' in seq
    assert '_unit setUnitPos "AUTO";' in seq
    assert '_m setUnitPos "AUTO";' in cancel
    assert 'ACME_headElev_seqActive' in seq


def test_cpr_and_bvm_are_native_acm_owned():
    cfg = txt('config.cpp')
    treatment = read_source(ROOT.parent / 'core/overrides/fnc_treatment.sqf', encoding='utf-8', errors='replace')

    # No compile-time replacement of the ACM continuous-action functions.
    assert 'class beginCPR { file = "\\acm_extended\\overrides\\fn_beginCPR.sqf"; };' not in cfg
    assert 'class canUseBVM { file = "\\acm_extended\\overrides\\fn_canUseBVM.sqf"; };' not in cfg
    assert 'class useBVM { file = "\\acm_extended\\overrides\\fn_useBVM.sqf"; };' not in cfg
    assert not (ROOT / 'overrides/fn_beginCPR.sqf').exists()
    assert not (ROOT / 'overrides/fn_canUseBVM.sqf').exists()
    assert not (ROOT / 'overrides/fn_useBVM.sqf').exists()
    assert 'class CPR {' not in cfg

    # BVM and CPR are routed directly into ACM's native treatment function before generic provider preflight.
    guard = treatment.index('private _nativeContinuousClass')
    preflight = treatment.index('private _bypass')
    bridge = treatment[guard:preflight]
    for cls in ['"cpr"', '"usebvm"', '"usebvm_oxygen"', '"usebvm_vehicleoxygen"', '"usebvm_portableoxygen"']:
        assert cls in bridge
    bvm = bridge.split('if (_nativeContinuousClass in ["usebvm"',1)[1].split('// Preserve the existing Direct Pressure handoff for CPR.',1)[0]
    assert '_this call ACM_core_fnc_treatmentNative' in bvm
    cpr = bridge.split('if (_nativeContinuousClass == "cpr") exitWith {',1)[1]
    assert '_this call ACM_core_fnc_treatmentNative' in cpr
    assert 'ACME_fnc_doAnim' not in bvm and 'ACME_fnc_doAnim' not in cpr


def test_bvm_visual_cue_is_read_only_native_observer():
    tick = txt('functions/fn_bvmVentTick.sqf')
    assert 'ACM_breathing_BVM_NextBreath' in tick
    assert 'ACME_bvmVent_lastNativeNextBreath' in tick
    for forbidden in ['ACM_breathing_BVM_Medic", _', 'ACM_breathing_BVM_provider", _', 'setUnitPos', 'ACME_fnc_medicAnimationPrep']:
        assert forbidden not in tick


def test_release_stamp():
    assert_release_identity()
    assert_release_identity()


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for test in tests:
        test()
        print(f'{test.__name__}: PASS')
    print('B92 critical provider/CPR/BVM checks: PASS')
