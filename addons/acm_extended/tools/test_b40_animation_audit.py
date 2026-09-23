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
    expected = {
        'functions/fn_airwayMedicPose.sqf': [r'_steps pushBack \[_crouch,.*?, 1\]', r'_steps pushBack \[_anim, _animTime, 1\]'],
        'functions/fn_headElevMedicSeq.sqf': [r'_steps pushBack \[_liftAnim, _liftTime, 1\]', r'_steps pushBack \[_riseAnim, _riseTime, 1\]'],
        'functions/fn_chestSealRoll.sqf': [r'\[_trans, _rollT, 1\]'],
    }
    for rel, patterns in expected.items():
        src = text(rel)
        for pat in patterns:
            assert re.search(pat, src, re.S), (rel, pat)

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
    src = text('functions/fn_hpmkWrap.sqf')
    assert '[_patient, _anim, 1] call ACME_fnc_doAnim;' in src
    assert 'remoteExec ["playMoveNow"' not in src

def test_cpr_authored_exit_blends():
    src = text('overrides/fn_beginCPR.sqf')
    assert 'AinvPknlMstpSnonWnonDnon_medicEnd", 1] call ACME_fnc_doAnim;' in src

def test_remaining_hard_switches_are_known_state_locks_only():
    allowed = {
        'functions/fn_megacodeClosePanel.sqf',
        'functions/fn_obtundedApply.sqf',
        'functions/fn_megacodeStanceLock.sqf',
        'functions/fn_postInit.sqf',
        'functions/fn_obtundedTransition.sqf',
        'functions/fn_chestSealRoll.sqf',
        'functions/fn_treatmentPoseSync.sqf',
        'functions/fn_treatmentPoseStart.sqf',
        'overrides/fn_beginCPR.sqf',
    }
    found=set()
    for base in ('functions','overrides'):
        for p in (ROOT/base).glob('*.sqf'):
            s=read_source(p, errors='ignore')
            if 'ace_common_switchMove' in s or 'QACEGVAR(common,switchMove)' in s or re.search(r'(?<!_)\bswitchMove\s*\[', s):
                found.add(str(p.relative_to(ROOT)).replace('\\','/'))
    assert found <= allowed, sorted(found-allowed)
