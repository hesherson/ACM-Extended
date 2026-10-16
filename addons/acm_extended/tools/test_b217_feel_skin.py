"""Execute the tactile-exam lifecycle; display/RTM rendering are explicit engine boundaries."""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, read, ROOT


def source(name):
    s=read(name)
    for a,b in {
        'local _medic':'_localMedic', 'objectParent _medic':'_vehicle',
        'objectParent _patient':'_patientVehicle', 'animationState _medic':'_animation',
        'inputAction _x':'([_x] call _input)',
        '_menu displayAddEventHandler [':'[',
        '_display displayRemoveEventHandler _x;':'_removedDisplay pushBack _x;',
    }.items(): s=s.replace(a,b)
    if name=='feelSkinStart':
        s=s.replace('    }];','    }] call _addDisplay;')
    return 'ACME_fnc_'+name+'={'+adapt(s)+'};'


def setup():
    return '''
        private _localMedic=true; private _vehicle=objNull; private _patientVehicle=objNull;
        private _animation="prep"; private _clinicalEpoch=0; private _blocked=false; private _allowed=true;
        private _interactive=true; private _inputActions=[]; private _results=[]; private _poseStops=[];
        private _addedDisplay=[]; private _removedDisplay=[]; private _poseStarts=[]; private _prone=false;
        private _menuSource=parsingNamespace;
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",_menuSource];
        missionNamespace setVariable ["ace_medical_gui_target",_patient];
        private _input={if ((_this select 0) in _inputActions) then {1} else {0}};
        private _addDisplay={_addedDisplay pushBack _this; count _addedDisplay-1};
        ACME_fnc_clinicalEpoch={_clinicalEpoch};
        ACME_fnc_animBlocked={_blocked}; ACME_fnc_procedureActionAllowed={_allowed};
        ACME_fnc_patientInteractionDistance={_distance};
        ace_common_fnc_canInteractWith={_interactive};
        ace_medical_treatment_fnc_canTreatCached={_allowed};
        ace_common_fnc_isAwake={!_unconscious};
        ACME_fnc_feelSkin={_results pushBack _this;};
        ACME_fnc_treatmentPoseStart={
            params ["_m","_mode"];
            _poseStarts pushBack _this;
            private _epoch=(_m getVariable ["ACME_treatmentPoseEpoch",0])+1;
            _m setVariable ["ACME_treatmentPoseEpoch",_epoch];
            _m setVariable ["ACME_treatmentPoseState",[_epoch,_mode,"work",1,10,-1,7,"",10,-1,10,0.55,-1,-1,-1,-1,false,1.5,false,false,_prone]];
            _testAnimationSpeed=1.5; _epoch
        };
        ACME_fnc_treatmentPoseStop={
            _poseStops pushBack _this;
            params ["_m","", "_epoch"];
            if (((_m getVariable ["ACME_treatmentPoseState",[]]) param [0,-1])==_epoch) then {
                _m setVariable ["ACME_treatmentPoseState",[]]; _testAnimationSpeed=1;
            };
        };
        private _request=[_medic,_patient,"Head","ACME_FeelSkin"];
        private _frame={
            private _record=_medic getVariable ["ACME_feelSkinAction",[]];
            if (_record isEqualTo []) exitWith {};
            private _id=_record select 6;
            private _h=_handlers select _id;
            if (_h select 2) then {[_h select 1,_id] call (_h select 0);};
        };
        private _hold={
            if ((_medic getVariable "ACME_feelSkinAction" select 3)==-1) then {
                (_medic getVariable "ACME_treatmentPoseState") set [3,2]; call _frame;
            };
            private _pose=_medic getVariable "ACME_treatmentPoseState";
            _pose set [3,3]; _pose set [14,CBA_missionTime]; _testAnimationSpeed=0; call _frame;
        };
        private _return={
            _animation="ainvpknlmstpsnonwnondnon_putdown_amovpknlmstpsnonwnondnon"; call _frame;
            _animation="amovpknlmstpsnonwnondnon"; call _frame;
        };
    '''+''.join(source(n) for n in ['feelSkinStart','feelSkinTick','feelSkinStop'])


def test_menu_stays_open_and_contact_clock_excludes_bend_down():
    execute(setup()+'''
        _dialog=true;
        [_request call ACME_fnc_feelSkinStart,"start rejected"] call _check;
        CBA_missionTime=11.5; call _frame;
        [(_medic getVariable "ACME_feelSkinAction" select 4)==-1,"entry consumed contact time"] call _check;
        [_dialog && {count _addedDisplay==2},"menu closed or cancellation not hooked"] call _check;
        call _hold;
        [(_poseStarts select 0 select 1)=="chestSealWorkspace" && {(_poseStarts select 1 select 1)=="feelSkin"},"wrong workspace handoff"] call _check;
        CBA_missionTime=12.999; call _frame;
        [count _poseStarts==2 && {count _results==0} && {_testAnimationSpeed==0},"hold finished early"] call _check;
        CBA_missionTime=13; call _frame;
        [_results isEqualTo [_request],"missing or repeated result"] call _check;
        [_dialog && {_testAnimationSpeed==1} && {count _poseStarts==2},"menu closed, extra return or animation speed stuck"] call _check;
        [count _removedDisplay==2 && {(_medic getVariable ["ACME_feelSkinAction",[]]) isEqualTo []},"input/worker leaked"] call _check;
        call _frame; [_medic,1,true] call ACME_fnc_feelSkinStop;
        [count _results==1,"late success repeated result"] call _check;
    ''')


@pytest.mark.parametrize('elapsed',[0,0.5,1.49,1.499,1.5,1.51,2.5])
def test_one_and_half_seconds_from_observed_hand_hold(elapsed):
    execute(setup()+'''_request call ACME_fnc_feelSkinStart; call _hold;'''+f'''
        CBA_missionTime=10+{elapsed}; call _frame;
        [count _poseStarts==2 && {{count _results=={int(elapsed>=1.5)}}},"incorrect contact boundary"] call _check;
    ''')


@pytest.mark.parametrize('phase',['entry','hold','latehold'])
@pytest.mark.parametrize('cause',[
    '_inputActions=["MoveForward"];', '_distance=4;', '_unconscious=true;', '_alive=false;',
    '_localMedic=false;', '_clinicalEpoch=1;', '_vehicle=missionNamespace;',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];', '_interactive=false;',
    'missionNamespace setVariable ["ace_medical_gui_target",missionNamespace];',
])
def test_cancellation_never_reports_or_retains_owned_frame(phase,cause):
    prep='' if phase=='entry' else 'call _hold;'
    if phase=='latehold': prep+='CBA_missionTime=11.49; call _frame;'
    execute(setup()+'_request call ACME_fnc_feelSkinStart;'+prep+cause+'''
        call _frame;
        [(_medic getVariable ["ACME_feelSkinAction",[]]) isEqualTo [],"cancel retained episode"] call _check;
        [count _results==0 && {count _removedDisplay==2},"cancel credited result or retained input"] call _check;
        [!((_handlers select 0) select 2),"cancel retained PFH"] call _check;
    ''')


@pytest.mark.parametrize('handler,event',[(0,'[_menuSource,1]'),(0,'[_menuSource,240]'),(1,'[_menuSource,1]')])
def test_escape_right_mouse_and_ace_cancel_work_with_source_menu(handler,event):
    execute(setup()+f'''
        _request call ACME_fnc_feelSkinStart; call _hold;
        {event} call (_addedDisplay select {handler} select 1);
        [(_medic getVariable ["ACME_feelSkinAction",[]]) isEqualTo [],"input did not cancel"] call _check;
        [_testAnimationSpeed==1 && {{count _results==0}},"cancel left freeze or reported result"] call _check;
    ''')


def test_old_stop_or_tick_cannot_release_new_action():
    execute(setup()+'''
        _request call ACME_fnc_feelSkinStart; call _hold;
        private _old=+(_handlers select 0);
        [_medic,1] call ACME_fnc_feelSkinStop;
        _request call ACME_fnc_feelSkinStart; call _hold;
        [_medic,1,true] call ACME_fnc_feelSkinStop;
        [_old select 1,0] call (_old select 0);
        [(_medic getVariable "ACME_feelSkinAction" select 0)==2,"old action retired replacement"] call _check;
        [_testAnimationSpeed==0 && {count _poseStops==1},"old action unfroze replacement"] call _check;
    ''')


def test_repeated_click_does_not_create_second_worker():
    execute(setup()+'''
        _request call ACME_fnc_feelSkinStart;
        [!(_request call ACME_fnc_feelSkinStart),"repeat accepted"] call _check;
        [count _handlers==1 && {count _poseStarts==1} && {count _addedDisplay==2},"repeat leaked handlers"] call _check;
    ''')


def test_seated_check_keeps_menu_and_does_not_force_kneeling():
    execute(setup()+'''
        _vehicle=missionNamespace; _patientVehicle=_vehicle; _blocked=true;
        _dialog=true; _request call ACME_fnc_feelSkinStart;
        CBA_missionTime=11.499; call _frame;
        [count _results==0 && {count _poseStarts==0},"seated check early/forced pose"] call _check;
        CBA_missionTime=11.5; call _frame;
        [count _results==1 && {_dialog} && {count _poseStarts==0},"seated completion missing/closed menu"] call _check;
    ''')


def test_prone_check_releases_to_supported_posture_without_return_kneel():
    execute(setup()+'''
        _prone=true; _request call ACME_fnc_feelSkinStart; call _hold;
        CBA_missionTime=11.5; call _frame;
        [count _results==1 && {count _poseStarts==2},"prone check forced additional return"] call _check;
        [count _poseStops==1 && {!((_poseStops select 0) param [3,false])},"prone hold was handed off without exit"] call _check;
    ''')


def test_missing_workspace_or_hand_contact_fails_boundedly():
    execute(setup()+'''
        _request call ACME_fnc_feelSkinStart;
        CBA_missionTime=22.1; call _frame;
        [(_medic getVariable ["ACME_feelSkinAction",[]]) isEqualTo [],"workspace timeout stuck"] call _check;
        _request call ACME_fnc_feelSkinStart;
        (_medic getVariable "ACME_treatmentPoseState") set [3,2]; call _frame;
        CBA_missionTime=34.2; call _frame;
        [(_medic getVariable ["ACME_feelSkinAction",[]]) isEqualTo [] && {count _results==0},"missing hand contact passed/stuck"] call _check;
    ''')


def test_exact_class_launcher_and_workspace_to_medic3_contract():
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    block=cfg.split('class ACME_FeelSkin: CheckPulse {',1)[1].split('\n    };',1)[0]
    assert 'treatmentTime = 0;' in block
    for name in ('feelSkinStart','feelSkinTick','feelSkinStop'):
        src=read(name)
        assert 'closeDialog' not in src and 'progressBar' not in src
    start=read('treatmentPoseStart')
    assert 'case "feelSkin": {"AinvPknlMstpSnonWnonDr_medic3"};' in start
    assert '_holdAt = 1.5;' in start
    assert '"chestSealWorkspace"' in read('feelSkinStart')
    assert 'feelSkinReturn' not in read('feelSkinTick')
    bridge=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    assert 'if (_classname == "ACME_FeelSkin") exitWith {_this call ACME_fnc_feelSkinStart;};' in bridge
    assert bridge.index('call ACME_fnc_feelSkinStop') < bridge.index('call ACM_core_fnc_treatmentNative')


@pytest.mark.parametrize('cancel',[False,True])
@pytest.mark.parametrize('stance',['CROUCH','PRONE'])
def test_real_shared_pose_controller_freezes_unfreezes_and_rejects_old_packets(stance,cancel):
    from test_historical_pose_lifecycle import setup as real_pose_setup
    execute(setup()+real_pose_setup()+f'_stance="{stance}";'+'''
        _prone=(_stance=="PRONE");
        [_request call ACME_fnc_feelSkinStart,"actual pose start denied"] call _check;
        private _workspace=_medic getVariable "ACME_treatmentPoseState";
        private _workspaceId=_workspace select 5;
        CBA_missionTime=12; [_workspaceId] call _poseTick;
        _animation=toLower (_workspace select 2); _nativeElapsed=0; _duration=4;
        [_workspaceId] call _poseTick;call _frame;
        private _pose=_medic getVariable "ACME_treatmentPoseState";
        [(_pose select 1)=="feelSkin" && {(_pose select 0)!=(_workspace select 0)},"workspace not handed off"] call _check;
        private _poseId=_pose select 5;
        _animation=toLower (_pose select 2); _nativeElapsed=0;
        [_poseId] call _poseTick;
        _nativeElapsed=1.5; [_poseId] call _poseTick; call _frame;
        [(_pose select 3)==3 && {_speed==0},"actual controller did not freeze contact"] call _check;
    '''+('''
        [_medic,1] call ACME_fnc_feelSkinStop;
        [count _results==0,"cancel produced result"] call _check;
    ''' if cancel else '''
        CBA_missionTime=13.499;call _frame;
        [count _results==0,"actual hold finished early"] call _check;
        CBA_missionTime=13.5; call _frame;
        [count _results==1,"actual controller did not finish tactile exam"] call _check;
    ''')+'''
        [(_medic getVariable ["ACME_feelSkinAction",[]]) isEqualTo [],"tactile worker retained"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo [],"pose retained after finish"] call _check;
        {[_x] call _deliver;} forEach +_speedWaits;
        [_speed==1,"actual cleanup left provider frozen/accelerated"] call _check;
        [_medic,_pose select 0,"hold","AinvPknlMstpSnonWnonDr_medic3",0.375,7] call ACME_fnc_treatmentPoseSync;
        [_speed==1,"late hold packet revived retired freeze"] call _check;
        [_poseId in _removed && {_workspaceId in _removed},"actual shared pose worker not removed"] call _check;
    ''')
