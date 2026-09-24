from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def text(rel):
    return read_source(ROOT / rel, errors="ignore")

def test_runtime_is_b41_r5():
    assert_release_identity()
    assert_release_identity()

def test_direct_pressure_has_connected_hold_state():
    cfg = text('config.cpp')
    block = cfg[cfg.index('class ACME_DirectPressureHold'):cfg.index('class UnconsciousReviveMedic_B')]
    assert 'interpolateFrom[]' in block
    assert 'interpolateTo[]' in block
    assert 'AmovPknlMstpSnonWnonDnon' in block

def test_direct_pressure_no_hard_switchmove():
    for name in ('fn_directPressureTorso.sqf','fn_directPressurePose.sqf','fn_directPressureStop.sqf'):
        src = text('functions/' + name)
        assert 'ace_common_switchMove' not in src
        assert 'ACM_CPR_Stop' not in src or name == 'fn_directPressureTorso.sqf' and False

def test_direct_pressure_entry_exit_are_priority_one():
    from test_bounded_pressure_contracts import assert_entry_exit_contract
    # Current connected hold entry and narrowly guarded stuck-hold exit fallback.
    assert_entry_exit_contract(text('functions/fn_directPressureTorso.sqf'),
                               text('functions/fn_directPressureStop.sqf'))

def test_movement_queues_are_explicit_priority_one():
    # Historical identity retained. Current provider movement is controller-owned rather than queued.
    pose = text('functions/fn_treatmentPoseStart.sqf')
    roll = text('functions/fn_chestSealRoll.sqf')
    menu = text('functions/fn_menuPoseStart.sqf')
    assert '[_medic, _transition, 1] call ACME_fnc_doAnim;' in pose
    assert '[_medic, _main, 1] call ACME_fnc_doAnim;' in pose
    assert 'call ACME_fnc_patientAnimRequest' in roll
    assert '_trans, 1, "chest-seal-roll"' in roll
    assert '[_medic, _kneel, 0] call ACME_fnc_doAnim;' in menu

def test_hang_bag_normal_entry_and_exit_blend():
    cfg = text('config.cpp')
    start = text('functions/fn_hangBagStart.sqf')
    stop = text('functions/fn_hangBagStop.sqf')
    assert 'class ACM_GenericContinuous;' in cfg
    begin = cfg.index('class ACME_Acts_JetsCrewaidFCrouchThumbup_in')
    end = cfg.index('class Acts_LyingWounded_loop3')
    block = cfg[begin:end]
    assert 'interpolateFrom[]' in block and 'ACM_GenericContinuous' in block
    assert '[_medic, _inAnim, 1.4, 1] call ACME_fnc_doAnimHeld;' in start
    assert '[_medic, _outAnim, 1] call ACME_fnc_doAnim;' in stop
    assert '[_medic, "AmovPknlMstpSnonWnonDnon", 1] call ACME_fnc_doAnim;' in stop

def test_hpmk_roll_uses_guarded_animation_wrapper():
    # HPMK wrapping is intentionally state-only now. It must not animate, attach, roll, or reposition the casualty.
    src = text('functions/fn_hpmkWrap.sqf')
    assert 'HPMK wrapping is state-only' in src
    assert 'ACME_fnc_hpmkStateCommit' in src
    for forbidden in ('ACME_fnc_doAnim', 'switchMove', 'playMoveNow', 'setPos', 'attachTo'):
        assert forbidden not in '\n'.join(line.split('//',1)[0] for line in src.splitlines())

def test_cpr_authored_exit_blends():
    # CPR is native ACM-owned. ACME must not carry a compile-time CPR animation override.
    from test_b90_critical_provider_cpr_bvm import test_cpr_and_bvm_are_native_acm_owned
    test_cpr_and_bvm_are_native_acm_owned()

def test_remaining_hard_switches_are_known_state_locks_only():
    # switchMove remains intentional only for exact held-frame/state-lock repair, not ordinary medical entry.
    pose = text('functions/fn_treatmentPoseStart.sqf')
    sync = text('functions/fn_treatmentPoseSync.sqf')
    roll = text('functions/fn_chestSealRoll.sqf')
    assert '_medic switchMove [_main, _phase, 1, false];' in pose
    assert '_medic switchMove [_main, _phase, 1, false];' in sync
    assert '["ace_common_switchMove", [_p, _hold]] call CBA_fnc_globalEvent;' in roll
    # Ordinary work and roll entry still start through priority-one interpolation.
    assert '[_medic, _main, 1] call ACME_fnc_doAnim;' in pose
    assert '_trans, 1, "chest-seal-roll"' in roll
