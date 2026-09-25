"""Head-start routing contracts and actual SQF execution with explicit engine fixtures.

Actual-side detection, physical rolling, gear writes and animations are boundary
stand-ins here. These tests do not render a body, simulate PhysX or validate NaN.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute
from test_bounded_head_completion import setup, source
from test_bounded_head_pose_contracts import contains


def start_contract(text=None):
    s=source('headElevateStart') if text is None else text
    for fragment in (
        'if !([_patient, _medic] call ACME_fnc_headElevateCanStart) exitWith {};',
        'private _actualBeforeElevate = [_patient, _patient getVariable ["ACME_CS_facing","front"]] call ACME_fnc_chestSealActualSide;',
        'private _needFrontFirst = !_afterProneRoll && {_actualBeforeElevate != "front"};',
        'if (_needFrontFirst) exitWith {',
        'if ([_patient] call ACME_fnc_chestSealCanPhysicalRoll) then {',
        '[_medic,"chestAccessFrontRoll",[_medic,_patient]] call ACME_fnc_ownerDispatch;',
        '[_patient,"front",false,_medic,true] call ACME_fnc_chestSealRoll;',
        '[_m,_p,_body,_auto,true] call ACME_fnc_headElevateStart;',
        '_patient setVariable ["ACME_headElevated", true, true];',
        '[_patient] call ACME_fnc_headElevApplyTilt;',
    ):
        assert contains(s,fragment),fragment


def start_setup():
    s=source('headElevateStart')
    for old,new in (
        ('canSuspend','false'), ('local _patient','_patientLocal'),
        ('local _p','_patientLocal'), ('objectParent _patient','_parent'),
        ('backpack _patient','"backpack"'), ('vest _patient','""'),
        ('getPosASL _patient','[1,2,3]'), ('getDir _patient','0'),
        ('animationState _patient','_animation'),
        ('finite _patientRoll','true'), ('finite _providerRoll','true'),
    ):
        s=re.sub(re.escape(old)+r'\b',lambda _:new,s)
    return setup() + r'''
        private _canStart=true; private _canRoll=true;
        private _tilts=[]; private _starts=[]; private _watches=[];
        ACME_fnc_headElevateCanStart={_canStart};
        ACME_fnc_chestSealCanPhysicalRoll={_canRoll};
        private _providerRolls=[];
        // Generic chestAccessFrontRoll is presentation-only in B164. The patient roll is a separate owner request.
        ACME_fnc_ownerDispatch={
            params ["_owner","_op","_args"];
            if (_op=="chestAccessFrontRoll") then {_providerRolls pushBack _args;};
        };
        ACME_fnc_headElevApplyTilt={_tilts pushBack _this;};
        // This older normalization fixture immediately acknowledges the provider reach.
        ACME_fnc_headElevMedicStart={
            _starts pushBack _this;
            if ((_patient getVariable ["ACME_headElev_pendingLift",[]]) isNotEqualTo []) then {[_patient] call ACME_fnc_headElevApplyTilt;};
        };
        ACME_fnc_headElevWatch={_watches pushBack _this;};
        _patient setVariable ["ACME_headElevated",false];
        _patient setVariable ["ACME_headElev_poseToken",""];
    ''' + 'ACME_fnc_headElevateStart={' + adapt(s) + '};\n'


@pytest.mark.parametrize('actual',['front','back'])
@pytest.mark.parametrize('cached',['front','back'])
@pytest.mark.parametrize('rollable',[False,True])
def test_actual_side_not_cached_label_decides_initial_normalization(actual,cached,rollable):
    execute(start_setup()+f'''
        _actualSide="{actual}"; _canRoll={str(rollable).lower()};
        _patient setVariable ["ACME_CS_facing","{cached}"];
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        [count _waits=={int(actual=='back')},"cached side incorrectly scheduled normalization"] call _check;
        [count _rolls=={int(actual=='back' and rollable)},"incorrect physical roll count"] call _check;
    ''' + (f'''
        [count _tilts==0 && {{count _starts==0}},"lift started before normalization retry"] call _check;
        private _retry=_waits select 0; _waits=[];
        [abs ((_retry select 2)-{2.45 if rollable else .08})<0.0001,"normalization delay changed"] call _check;
        _actualSide="front";
        [_retry] call _deliver;
        [count _waits==0,"retry queued another normalization"] call _check;
    ''' if actual=='back' else '') + '''
        [_patient getVariable ["ACME_headElevated",false],"accepted startup lost logical elevation"] call _check;
        [count _tilts==1 && {count _starts==1} && {count _watches==1},"accepted startup lost authored dispatch"] call _check;
        [(_patient getVariable ["ACME_CS_facing",""])=="front","accepted startup lost front cache"] call _check;
        [_restores isEqualTo [["access",[_patient]]],"backpack startup altered recovery handoff"] call _check;
    ''')


@pytest.mark.parametrize('actual',['front','back'])
def test_owner_revalidation_denies_start_before_roll_gear_or_state_writes(actual):
    execute(start_setup()+f'''
        _actualSide="{actual}"; _canStart=false;
        _patient setVariable ["ACME_CS_facing","sentinel"];
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        [count _waits==0 && {{count _rolls==0}} && {{count _tilts==0}} && {{count _restores==0}},"denied start changed presentation"] call _check;
        [(_patient getVariable ["ACME_CS_facing",""])=="sentinel","denied start rewrote facing"] call _check;
        [!(_patient getVariable ["ACME_headElevated",false]),"denied start wrote elevation"] call _check;
    ''')


@pytest.mark.parametrize('change',['_patientLocal=false;','_patientAlive=false;','_canStart=false;'])
def test_start_retry_retains_existing_owner_life_and_eligibility_checks(change):
    execute(start_setup()+'''
        _actualSide="back";
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        private _retry=_waits select 0; _waits=[];
    '''+change+'''
        [_retry] call _deliver;
        [count _tilts==0 && {count _starts==0} && {count _restores==0},"invalid retry started elevation"] call _check;
    ''')


@pytest.mark.parametrize('patient,provider,expected',[
    ('1.85','2.2',2.45), ('4','2.2',4.10), ('1.85','5',5.25),
    ('"bad"','"bad"',2.45),
])
def test_normalization_waits_for_the_longer_patient_or_provider_move(patient,provider,expected):
    execute(start_setup()+f'''
        _actualSide="back";
        missionNamespace setVariable ["ACME_CS_rollTime",{patient}];
        missionNamespace setVariable ["ACME_rollProviderDuration",{provider}];
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        [count _waits==1 && {{abs (((_waits select 0) select 2)-{expected})<0.0001}},"patient/provider delay contract changed"] call _check;
    ''')


def test_provider_theatre_and_patient_normalization_remain_separate_single_requests():
    s=source('headElevateStart')
    start=s.index('if ([_patient] call ACME_fnc_chestSealCanPhysicalRoll) then {')
    end=s.index('} else {',start)
    physical=s[start:end]
    assert physical.count('chestAccessFrontRoll') == 1
    assert physical.count('call ACME_fnc_chestSealRoll') == 1


@pytest.mark.parametrize('old,new',[
    ('_actualBeforeElevate != "front"','_actualBeforeElevate == "front"'),
    ('!_afterProneRoll &&','_afterProneRoll &&'),
    ('[_patient,"front",false,_medic,true]','[_patient,"back",false,_medic,true]'),
    ('if !([_patient, _medic] call ACME_fnc_headElevateCanStart) exitWith {};',''),
])
def test_start_contract_rejects_reversed_or_missing_guards_despite_comment_decoys(old,new):
    s=source('headElevateStart');assert old in s
    with pytest.raises(AssertionError):start_contract(s.replace(old,new,1)+'\n/* '+old+' */\n')
