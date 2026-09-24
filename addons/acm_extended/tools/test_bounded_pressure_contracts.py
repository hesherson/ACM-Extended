"""Current Direct Pressure contracts; actual SQF with explicit engine stand-ins.

Uses the existing BVM/DP execution harness. It does not render poses or certify
network transport. Input bindings and gameplay tuning are deliberately unchanged.
"""
import pytest
from source_scan import lex
from test_menu_death_lifecycle import execute, read
from test_native_bvm_dp import setup as existing_setup, pressure_source


def has(source, fragment):
    tokens = [(t.kind, t.value) for t in lex(source)]
    wanted = [(t.kind, t.value) for t in lex(fragment)]
    assert any(tokens[i:i + len(wanted)] == wanted for i in range(len(tokens))), fragment


def assert_entry_exit_contract(start, stop):
    has(start, '[_medic,"ACME_DirectPressureHold",1.1,1] call ACME_fnc_doAnimHeld;')
    has(stop, 'private _exitPriority = [1,2] select (_stateBefore == "acme_directpressurehold");')
    has(stop, '[_medic,"AmovPknlMstpSnonWnonDnon",_exitPriority] call ACME_fnc_doAnim;')
    has(stop, 'if (!_otherManeuver && {local _medic} && {alive _medic} && {isNull objectParent _medic} && {_ownsHold}) then')


def assert_nonexclusive_contract(start, regions):
    has(start, 'private _providerManeuver = (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])')
    has(start, '_medic getVariable ["ACM_circulation_isPerformingCPR", false]')
    has(start, '_medic getVariable ["ACM_breathing_isUsingBVM", false]')
    has(start, '[_patient] call ACM_core_fnc_cprActive')
    has(start, '[_patient] call ACM_core_fnc_bvmActive')
    has(start, 'if (_providerManeuver) exitWith')
    has(start, 'if (_bodyPart == "body") then')
    for name in ('directPressureTorso', 'directPressureSelf', 'directPressureLimb'):
        has(start, 'call ACME_fnc_' + name)
    for source in regions:
        has(source, '_medic setVariable ["ACME_DP_OwnsContinuous",false];')
        # The controller variable may be READ, but not assigned/acquired by DP.
        ident = [t.value for t in lex(source) if t.kind == 'ident']
        assert 'ACM_core_ContinuousAction_Active' not in ident
        assert 'ACM_core_fnc_beginContinuousAction' not in ident
        has(source, '[_patient,"directPressureMarker"' if '"torso"' in source or '"limb"' in source else '[_medic,"directPressureMarker"')


def assert_compatible_work_contract(tick, hang, bp):
    has(tick, 'private _nativeCpr = [_patient] call ACM_core_fnc_cprActive;')
    has(tick, 'private _nativeBvm = [_patient] call ACM_core_fnc_bvmActive;')
    has(tick, 'private _mustYieldClinical = _maneuverActive || {_manualPause} || {_chestPrep} || {_headProvider} || {_treatmentBusy};')
    has(tick, 'if (_mustYieldClinical) exitWith')
    # Higher-priority work must yield before the decorative pressure pose can run.
    assert tick.index('if (_mustYieldClinical) exitWith') < tick.index('call ACME_fnc_directPressurePose')
    has(tick, 'private _yieldDuration = (CBA_missionTime - _yieldStart) max 0;')
    for key in ('ACME_DP_Start', 'ACME_DP_NextClot'):
        has(tick, f'_medic setVariable ["{key}", (_medic getVariable ["{key}", CBA_missionTime]) + _yieldDuration];')
    has(bp, '[_medic,_patient,_bodyPart,_stethoscope] call ACM_circulation_fnc_measureBP;')
    for source in (hang, bp):
        tokens = lex(source)
        assert not any(t.kind == 'ident' and t.value == 'ACME_fnc_directPressureStop' for t in tokens)
        assert not any(t.kind == 'string' and t.value == 'ACME_DP_Mode' for t in tokens)


def setup():
    return existing_setup() + 'ACME_fnc_directPressureSelf = {' + pressure_source('directPressureSelf') + '};' + '''
        private _markerEvents = [];
        private _dispatch = ACME_fnc_ownerDispatch;
        ACME_fnc_ownerDispatch = {
            if ((_this select 1) == "directPressureMarker") then {_markerEvents pushBack _this;};
            _this call _dispatch;
        };
        private _animCalls = [];
        ACME_fnc_doAnim = {_animCalls pushBack _this;};
        private _begin = {
            private _p = if (_this == "self") then {_medic} else {_patient};
            private _part = if (_this == "self") then {"leftarm"} else {_this};
            [_medic,_p,_part] call ACME_fnc_directPressureStart;
            [_p,_part]
        };
    '''


@pytest.mark.parametrize('region', ['body', 'leftarm', 'head', 'self'])
def test_every_region_starts_without_acquiring_the_continuous_action_gate(region):
    execute(setup() + f'("{region}" call _begin) params ["_p","_part"];' + '''
        [_medic getVariable ["ACME_DP_Active",false],"pressure not active"] call _check;
        [!ACM_core_ContinuousAction_Active,"pressure acquired exclusive controller"] call _check;
        [!(_medic getVariable ["ACME_DP_OwnsContinuous",true]),"wrong ownership flag"] call _check;
        [(_p getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo _medic,"marker not committed"] call _check;
        [count _markerEvents == 1,"marker duplicated on entry"] call _check;
    ''')


@pytest.mark.parametrize('region', ['body', 'leftarm', 'head', 'self'])
@pytest.mark.parametrize('duration', [0, 4, 20])
def test_stationary_manual_pause_yields_once_and_does_not_credit_clot_time(region, duration):
    execute(setup() + f'("{region}" call _begin) params ["_p","_part"];' + '''
        private _start = _medic getVariable "ACME_DP_Start";
        private _clot = _medic getVariable "ACME_DP_NextClot";
        private _id = _medic getVariable "ACME_DP_PFH";
        CBA_missionTime = 11;
        _medic setVariable ["ACME_DP_Paused",true];
        call _pressTick; call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"pause cancelled episode"] call _check;
        [(_medic getVariable "ACME_DP_PFH") == _id,"pause replaced worker"] call _check;
        [(_p getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo objNull,"yield kept pressure marker"] call _check;
        [count _markerEvents == 2,"yield repeatedly published marker"] call _check;
    ''' + f'CBA_missionTime = 11 + {duration};' + '''
        _medic setVariable ["ACME_DP_Paused",false];
        call _pressTick; call _pressTick;
        [(_p getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo _medic,"pressure not resumed"] call _check;
        [count _markerEvents == 3,"resume repeatedly published marker"] call _check;
    ''' + f'''
        [(_medic getVariable "ACME_DP_Start") == _start + {duration},"paused time credited as hold time"] call _check;
        [(_medic getVariable "ACME_DP_NextClot") == _clot + {duration},"clot timer not shifted"] call _check;
    ''')


@pytest.mark.parametrize('animation,other,expected', [
    ('acme_directpressurehold',False,2), ('other_treatment',False,1),
    ('acme_directpressurehold',True,0), ('other_treatment',True,0),
])
def test_exit_fallback_is_limited_to_the_visible_hold_and_never_steals_a_maneuver(animation, other, expected):
    execute(setup() + '"body" call _begin;' + f'''
        _animation = "{animation}";
        ACM_core_ContinuousAction_Active = {str(other).lower()};
        _animCalls = [];
        [true,_medic] call ACME_fnc_directPressureStop;
        [count _animCalls == {int(expected != 0)},"incorrect exit request count"] call _check;
        [ACM_core_ContinuousAction_Active isEqualTo {str(other).lower()},"pressure stop changed another controller"] call _check;
    ''' + (f'[(_animCalls select 0) isEqualTo [_medic,"AmovPknlMstpSnonWnonDnon",{expected}],"wrong exit priority"] call _check;' if expected else ''))


@pytest.mark.parametrize('stethoscope',[False,True])
def test_bp_wrapper_delivers_native_callback_without_cancelling_pressure(stethoscope):
    execute(setup() + '"body" call _begin;' + '''
        private _bpCalls = [];
        ACM_circulation_fnc_measureBP = {_bpCalls pushBack _this;};
        private _bp = {
    ''' + pressure_source('measureBPWrap') + '};' + f'''
        [_medic,_patient,"leftarm",{str(stethoscope).lower()}] call _bp;
        [count _bpCalls == 0,"BP callback was not deferred"] call _check;
        private _jobs = +_waits; _waits = [];
        {{(_x select 1) call (_x select 0);}} forEach _jobs;
        [_bpCalls isEqualTo [[_medic,_patient,"leftarm",{str(stethoscope).lower()}]],"BP payload changed"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"BP wrapper cancelled pressure"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    lambda s: s.replace('1.1, 1] call ACME_fnc_doAnimHeld', '1.1, 2] call ACME_fnc_doAnimHeld'),
    lambda s: '// ' + s.replace('\n', '\n// '),
])
def test_entry_contract_rejects_wrong_priority_and_comment_only_decoys(change):
    with pytest.raises(AssertionError):
        assert_entry_exit_contract(change(read('directPressureTorso')),read('directPressureStop'))
