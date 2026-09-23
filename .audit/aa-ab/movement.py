"""Full provider/cancel execution with explicit input and display fixtures.
No real keyboard events, display lifetime, animation or network scheduling is simulated.
Only the originating medical display is tracked; menu-less chest exits remain valid.
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
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"movement/menu exit did not cancel provider"] call _check;
        [_removed isEqualTo [100],"cancel did not retire exact controller"] call _check;
        [_moves isEqualTo [[_medic,"{REST}",2]],"cancel lost existing crouch recovery"] call _check;
        [_stances isEqualTo ["MIDDLE"],"cancel changed stance sequence"] call _check;
        [count _waits==1 && {{(_waits select 0 select 2)==0.25}},"cancel changed release delay"] call _check;
        [!(_medic getVariable ["ACME_DP_Paused",true]) && {{!(_medic getVariable ["ACME_DP_TreatmentBusy",true])}},"pressure pause left busy"] call _check;
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
def test_movement_retires_every_stage_without_lowering_casualty(mode,stage):
    execute(setup()+begin(mode)+reset(stage)+'''
        _input setVariable ["MoveForward",1];
        [_job] call _tick;
    '''+stopped())


@pytest.mark.parametrize('action',ACTIONS)
def test_each_remappable_movement_action_can_cancel(action):
    execute(setup()+begin()+reset(1)+f'''
        _input setVariable ["{action}",0.1];
        [_job] call _tick;
    '''+stopped())


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('stage',[-1,0,1,2])
@pytest.mark.parametrize('replacement',['objNull','profileNamespace'])
def test_originating_menu_close_or_replacement_cancels_without_patient_writes(mode,stage,replacement):
    execute(setup()+'''
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
    '''+begin(mode)+reset(stage)+f'''
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",{replacement}];
        [_job] call _tick;
    '''+stopped())


@pytest.mark.parametrize('mode',['elevate','lower'])
@pytest.mark.parametrize('menu',['objNull','missionNamespace'])
def test_stationary_current_context_keeps_full_choreography(mode,menu):
    execute(setup()+f'''
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",{menu}];
        _input setVariable ["MoveForward",0.05];
    '''+begin(mode)+finish()+'''
        [count _moves==4 && {_removed isEqualTo [100]},"idle/dead-zone changed choreography"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('owner',['ai','headless'])
def test_other_local_provider_does_not_read_players_input_or_menu(owner):
    extra='ACE_player=profileNamespace;' if owner=='ai' else '_interfacePresent=false;'
    execute(setup()+extra+'''
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
        _input setVariable ["MoveForward",1];
    '''+begin()+'''
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",objNull];
    '''+finish()+'''
        [count _moves==4 && {_removed isEqualTo [100]},"player input cancelled other local provider"] call _check;
        call _patientUntouched;
    ''')


def test_no_originating_menu_does_not_bind_to_later_unrelated_menu():
    execute(setup()+begin()+'''
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
        _anim=toLower "'''+REST+'''";
        [_job] call _tick;
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",objNull];
    '''+finish()+'''
        [count _moves==4 && {_removed isEqualTo [100]},"menu-less exit adopted unrelated menu"] call _check;
        call _patientUntouched;
    ''')


def test_superseded_controller_cannot_cancel_new_sequence_even_with_input_and_closed_menu():
    execute(setup()+'''
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
    '''+begin()+reset(1)+'''
        _medic setVariable ["ACME_headElev_medicAnimToken",99];
        _input setVariable ["MoveForward",1];
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",objNull];
        [_job] call _tick;
        [_medic getVariable ["ACME_headElev_seqActive",false],"old input cancelled new sequence"] call _check;
        [count _moves==0 && {count _stances==0} && {count _waits==0} && {count _events==0},"old input requested cleanup"] call _check;
        [_removed isEqualTo [100],"old handle not retired"] call _check;
        call _patientUntouched;
    ''')


def movement_menu_contract(text=None):
    s=source('headElevMedicSeq') if text is None else text
    for part in (
        'private _watchMenu = !isNull _menu;',
        'hasInterface && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player}',
        'if (hasInterface && {!isNil "ACE_player"} && {_u isEqualTo ACE_player}) then {',
        '(inputAction _x) > 0.05',
        '_watchMenu && {isNull _menu || {!(_menu isEqualTo (uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull]))}}',
        'if (_cancel) exitWith {',
        'call ACME_fnc_headElevateCancelSeq;',
        '[_pfh] call CBA_fnc_removePerFrameHandler;',
    ):
        assert contains(s,part),part
    for action in ACTIONS:assert contains(s,'"'+action+'"')
    assert s.index('if ((_u getVariable ["ACME_headElev_medicAnimToken", -1]) != _token) exitWith {') < s.index('private _cancel = false;')
    assert not contains(source('headElevateCancelSeq'),'call ACME_fnc_headElevateStop')
    assert contains(source('headElevateCancelSeq'),'_m setUnitPos "AUTO";')


@pytest.mark.parametrize('old,new',[
    ('(inputAction _x) > 0.05','false'),
    ('private _watchMenu = !isNull _menu;','private _watchMenu = false;'),
    ('&& {_u isEqualTo ACE_player}','&& {true}'),
    ('call ACME_fnc_headElevateCancelSeq;',''),
])
def test_contract_rejects_removed_cancellation_guards_despite_comment_decoy(old,new):
    s=source('headElevMedicSeq');assert old in s
    with pytest.raises(AssertionError):movement_menu_contract(s.replace(old,new)+'\n/* '+old+' */')
