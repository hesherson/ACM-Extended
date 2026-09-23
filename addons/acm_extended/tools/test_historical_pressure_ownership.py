"""Current persistent-pressure contracts behind superseded B40/B75 assertions.

Execute the real DP entry, marker, tick and stop bodies in SQF-VM. The retained
BVM fixture supplies engine object, input, animation and networking primitives;
this does not claim live multiplayer animation or hemorrhage validation.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_native_bvm_dp import setup as native_setup, pressure_source

CASES = [('body', False, 'torso'), ('head', False, 'limb'),
         ('leftarm', False, 'limb'), ('rightarm', False, 'limb'),
         ('leftleg', False, 'limb'), ('rightleg', False, 'limb'),
         ('head', True, 'self'), ('leftarm', True, 'self'),
         ('rightarm', True, 'self'), ('leftleg', True, 'self'),
         ('rightleg', True, 'self')]


def setup():
    return native_setup() + 'ACME_fnc_directPressureSelf={' + pressure_source('directPressureSelf') + '};' + '''
        private _ownerOps=[]; _animation="neutral";
        // Engine wound-loss integration is outside these marker ownership checks.
        ace_medical_status_fnc_updateWoundBloodLoss={};
        private _pressureOwner=ACME_fnc_ownerDispatch;
        ACME_fnc_ownerDispatch={_ownerOps pushBack _this; _this call _pressureOwner;};
        ACME_fnc_doAnim={_moves pushBack _this;};
    '''


def start(part, own):
    return ('private _target=' + ('_medic' if own else '_patient') + ';' +
            f'private _part="{part}"; [_medic,_target,_part] call ACME_fnc_directPressureStart;')


@pytest.mark.parametrize('part,own,mode', CASES)
def test_every_region_is_persistent_without_claiming_the_native_continuous_controller(part, own, mode):
    execute(setup() + '''
        ACM_core_ContinuousAction_PFH=777;
        ACM_core_ContinuousAction_IsDialog=true;
        ACM_core_ContinuousAction_Epoch=31;
    ''' + start(part, own) + f'''
        [_medic getVariable ["ACME_DP_Active",false],"pressure did not start"] call _check;
        [(_medic getVariable ["ACME_DP_Mode",""])=="{mode}","wrong region controller"] call _check;
        [(_target getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo _medic,"missing owner marker"] call _check;
        [!ACM_core_ContinuousAction_Active && {{ACM_core_ContinuousAction_PFH==777}}
            && {{ACM_core_ContinuousAction_Epoch==31}} && {{ACM_core_ContinuousAction_IsDialog}},"pressure acquired native globals"] call _check;
        [!(_medic getVariable ["ACME_DP_OwnsContinuous",true]),"pressure claimed exclusive controller"] call _check;
        [(_medic getVariable ["ACME_DP_PFH",-1])>=0,"missing pressure worker"] call _check;
        [true,_medic] call ACME_fnc_directPressureStop;
        [!ACM_core_ContinuousAction_Active && {{ACM_core_ContinuousAction_PFH==777}}
            && {{ACM_core_ContinuousAction_Epoch==31}} && {{ACM_core_ContinuousAction_IsDialog}},"pressure teardown changed native globals"] call _check;
        [(_target getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo objNull,"pressure marker survived stop"] call _check;
    ''')


@pytest.mark.parametrize('part,own,mode', CASES)
def test_an_incompatible_maneuver_yields_marker_once_and_excludes_paused_time(part, own, mode):
    execute(setup() + start(part, own) + '''
        CBA_missionTime=13;
        ACM_core_ContinuousAction_Active=true;
        call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"temporary yield cancelled persistent episode"] call _check;
        [_medic getVariable ["ACME_DP_ClinicalYield",false],"incompatible maneuver did not yield"] call _check;
        [(_target getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo objNull,"yield retained clinical pressure"] call _check;
        private _messages=count _ownerOps;
        CBA_missionTime=17; call _pressTick;
        [count _ownerOps==_messages,"repeated yield spammed owner marker"] call _check;
        ACM_core_ContinuousAction_Active=false;
        CBA_missionTime=20; call _pressTick;
        [!(_medic getVariable ["ACME_DP_ClinicalYield",true]),"pressure did not resume"] call _check;
        [(_target getVariable [format ["ACME_DP_press_%1",_part],objNull]) isEqualTo _medic,"resume did not republish marker"] call _check;
        [(_medic getVariable ["ACME_DP_Start",0])==17,"paused time counted as pressure time"] call _check;
        [(_medic getVariable ["ACME_DP_NextClot",0])==32,"clot deadline ignored pause duration"] call _check;
        [count _ownerOps==_messages+1,"resume did not issue exactly one owner marker"] call _check;
    ''')


@pytest.mark.parametrize('part',['body','leftarm','head'])
@pytest.mark.parametrize('animation,expected',[('acme_directpressurehold',2),('other-medical-pose',1)])
def test_priority_two_is_only_the_observed_loop_escape_not_normal_entry(part, animation, expected):
    execute(setup()+start(part,False)+'''
        // doAnimHeld registers its bounded worker; replay its first unentered frame.
        private _heldId=(_medic getVariable "ACME_DP_PFH")-1;
        private _held=_handlers select _heldId;
        _animation="not-entered";
        [_held select 1,_heldId] call (_held select 0);
        [count _moves==1 && {((_moves select 0) select 1)=="ACME_DirectPressureHold"}
            && {((_moves select 0) select 2)==1},"normal hold entry was not priority one"] call _check;
        _moves=[];
    '''+f'_animation="{animation}";'+'''
        [true,_medic] call ACME_fnc_directPressureStop;
    '''+f'''
        [count _moves==1 && {{((_moves select 0) select 1)=="AmovPknlMstpSnonWnonDnon"}}
            && {{((_moves select 0) select 2)=={expected}}},"wrong scoped exit priority"] call _check;
    ''')


@pytest.mark.parametrize('part',['body','leftarm','head'])
def test_retired_pressure_tick_cannot_operate_on_a_replacement_episode(part):
    execute(setup()+start(part,False)+'''
        private _oldId=_medic getVariable "ACME_DP_PFH";
        private _old=+(_handlers select _oldId);
        [true,_medic] call ACME_fnc_directPressureStop;
        [_medic,_patient,"rightleg"] call ACME_fnc_directPressureStart;
        private _newId=_medic getVariable "ACME_DP_PFH";
        private _messages=count _ownerOps; private _animations=count _moves;
        [_old select 1,_oldId] call (_old select 0);
        [(_medic getVariable "ACME_DP_PFH")==_newId && {(_handlers select _newId) select 2},"old tick retired replacement"] call _check;
        [count _ownerOps==_messages && {count _moves==_animations},"old tick wrote clinical or animation state"] call _check;
        [(_patient getVariable ["ACME_DP_press_rightleg",objNull]) isEqualTo _medic,"replacement marker was lost"] call _check;
    ''')
