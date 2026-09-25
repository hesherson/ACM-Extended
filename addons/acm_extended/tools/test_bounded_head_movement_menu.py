"""Provider movement cancellation without medical-menu lifetime coupling.

The B166 provider theatre is presentation-only. Movement may cancel that theatre, but closing/recreating ACE's
medical menu must never cancel patient Semi-Fowler state or gate its animation.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_bounded_head_cancel_generation import setup
from test_bounded_head_provider_sequence import begin, finish, REST
from test_bounded_head_completion import source
from test_bounded_head_pose_contracts import contains

ACTIONS=['MoveForward','MoveBack','TurnLeft','TurnRight','MoveLeft','MoveRight','MoveFastForward','MoveSlowForward']


def stopped():
    return f'''
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"movement did not cancel provider theatre"] call _check;
        [_removed isEqualTo [100],"cancel did not retire exact controller"] call _check;
        [_moves isEqualTo [[_medic,"{REST}",2]],"cancel lost crouch recovery"] call _check;
        [_stances isEqualTo ["MIDDLE"],"cancel changed stance sequence"] call _check;
        [count _waits==1 && {{(_waits select 0 select 2)==0.25}},"cancel changed release delay"] call _check;
        if (count _waits==1) then {{[_waits select 0] call _deliver;}};
        [_stances isEqualTo ["MIDDLE","AUTO"],"cancel left stance locked"] call _check;
        call _patientUntouched;
    '''


def reset(stage):
    return f'''
        (_job select 2) set [7,{stage}];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Paused",true];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","acme_elevatehead"];
        _moves=[];_stances=[];_events=[];_waits=[];_removed=[];
    '''


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('stage',[-1,0,1,2])
def test_movement_retires_every_stage_without_touching_casualty(mode,stage):
    execute(setup()+begin(mode)+reset(stage)+'''
        _input setVariable ["MoveForward",1];
        [_job] call _tick;
    '''+stopped())


@pytest.mark.parametrize('action',ACTIONS)
def test_each_remappable_movement_action_can_cancel_provider_theatre(action):
    execute(setup()+begin()+reset(1)+f'''
        _input setVariable ["{action}",0.1];
        [_job] call _tick;
    '''+stopped())


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_stationary_provider_keeps_full_choreography(mode):
    execute(setup()+'''
        _input setVariable ["MoveForward",0.05];
    '''+begin(mode)+finish()+'''
        [count _moves==4 && {_removed isEqualTo [100]},"idle/dead-zone changed choreography"] call _check;
        call _patientUntouched;
    ''')


def test_superseded_controller_cannot_cancel_new_sequence_even_with_input():
    execute(setup()+begin()+reset(1)+'''
        _medic setVariable ["ACME_headElev_medicAnimToken",99];
        _input setVariable ["MoveForward",1];
        [_job] call _tick;
        [_medic getVariable ["ACME_headElev_seqActive",false],"old input cancelled new sequence"] call _check;
        [count _moves==0 && {count _stances==0} && {count _waits==0} && {count _events==0},"old input requested cleanup"] call _check;
        [_removed isEqualTo [100],"old handle not retired"] call _check;
        call _patientUntouched;
    ''')


def movement_contract(text=None):
    s=source('headElevMedicSeq') if text is None else text
    for part in (
        'hasInterface && {!isNil "ACE_player"} && {_u isEqualTo ACE_player}',
        '(inputAction _x) > 0.05',
        'if (_cancel) exitWith {',
        'call ACME_fnc_headElevateCancelSeq;',
        '[_pfh] call CBA_fnc_removePerFrameHandler;',
        'private _hardDeadline = CBA_missionTime + 6.0;',
    ):
        assert contains(s,part),part
    for action in ACTIONS:
        assert contains(s,'"'+action+'"')
    assert 'ace_medical_gui_menuDisplay' not in s
    assert '_watchMenu' not in s
    assert 'headElevMedicReady' not in s
    assert 'ACME_headElev_pendingMove' not in s
    assert s.index('if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {') < s.index('private _cancel = false;')
    assert not contains(source('headElevateCancelSeq'),'call ACME_fnc_headElevateStop')
    assert contains(source('headElevateCancelSeq'),'_m setUnitPos "AUTO";')


@pytest.mark.parametrize('old,new',[
    ('(inputAction _x) > 0.05','false'),
    ('call ACME_fnc_headElevateCancelSeq;',''),
    ('private _hardDeadline = CBA_missionTime + 6.0;','private _hardDeadline = CBA_missionTime + 60.0;'),
])
def test_contract_rejects_removed_cancellation_guards(old,new):
    s=source('headElevMedicSeq'); assert old in s
    with pytest.raises(AssertionError):
        movement_contract(s.replace(old,new)+'\n/* '+old+' */')
