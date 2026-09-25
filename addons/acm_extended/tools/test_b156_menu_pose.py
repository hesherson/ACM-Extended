"""Execute menu-provider ownership using real start, stop and Unload callbacks."""
import pytest

from test_menu_death_lifecycle import adapt, execute, read


def menu_code(name):
    source = read(name)
    # Display/object commands are the only substituted boundaries. All episode,
    # provider-ownership and callback logic remains the checked-out SQF source.
    source = source.replace('stance _medic', '_menuStance')
    source = source.replace('animationState _medic', '_menuAnimation')
    for command in ('primaryWeapon', 'secondaryWeapon', 'handgunWeapon', 'binocular', 'currentWeapon'):
        source = source.replace(command + ' _medic', '_' + command)
    source = source.replace('_patient isKindOf "CAManBase"', 'true')
    source = source.replace('_medic setUnitPos "MIDDLE";', '_stanceMiddle=true;')
    source = source.replace('_display displayAddEventHandler', '_display setVariable')
    source = source.replace('_medic getUnitMovesInfo 0', '0')
    source = source.replace('_medic switchMove [_main, _phase, 1, false];', '_moves pushBack _main;')
    return adapt(source)


def setup():
    return """
        private _menuStance="CROUCH";
        private _menuAnimation="amovpknlmstpsnonwnondnon";
        private _primaryWeapon=""; private _secondaryWeapon="";
        private _handgunWeapon=""; private _binocular=""; private _currentWeapon="";
        _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        private _stanceMiddle=false;
        private _display=missionNamespace;
        private _prepDelay=.2;
        private _runtimeHandlers=createHashMap;
        ACME_fnc_animBlocked={false};
        ace_common_fnc_isSwimming={false};
        ACME_fnc_medicAnimationPrep={_prepDelay};
        private _priorities=[];
        ACME_fnc_doAnim={_moves pushBack (_this select 1); _priorities pushBack (_this select 2);};
        ACME_fnc_syncPremixedBags={};
        CBA_fnc_waitAndExecute={_waits pushBack _this;};
        CBA_fnc_globalEvent={_events pushBack _this;};
        CBA_fnc_addEventHandler={_runtimeHandlers set [_this select 0,_this select 1];};
        private _runWait={private _w=_waits select _this; (_w select 1) call (_w select 0);};
    """ + ''.join(
        f'ACME_fnc_{name}={{' + menu_code(name) + '};'
        for name in ('providerStanceOwned', 'treatmentPoseSync', 'treatmentPoseStop', 'menuPoseStop', 'menuPoseStart')
    ) + menu_code('registerMedicalMenuOpenRuntime')


@pytest.mark.parametrize('stance, transition, delay', [
    ('CROUCH', '', 0),
    ('STAND', 'AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon', .65 / 1.5),
    ('PRONE', 'AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon', 1.116 / 1.5),
])
def test_menu_uses_native_generic_after_preparation_and_correct_transition(stance, transition, delay):
    expected = f'["{transition}"]' if transition else '[]'
    execute(setup() + f'''
        _menuStance="{stance}";
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        [count _moves==0 && {{count _waits==1}},"menu skipped weapon preparation"] call _check;
        [_stanceMiddle && {{_testAnimationSpeed==1.5}},"menu did not acquire its stance and choreography speed"] call _check;
        [abs (((_waits select 0) select 2)-.2)<.000001,"preparation delay changed"] call _check;
        0 call _runWait;
        [_moves isEqualTo {expected},"wrong stance transition"] call _check;
        [abs (((_waits select 1) select 2)-{delay})<.000001,"stance transition timing changed"] call _check;
        1 call _runWait;
        [(_moves select ((count _moves)-1))=="ACM_GenericContinuous","menu failed to enter native continuous pose"] call _check;
    ''')


def test_old_display_unload_and_callbacks_cannot_retire_reopened_menu():
    execute(setup() + '''
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        private _oldDisplay=_display;
        private _oldState=+(_medic getVariable "ACME_menuPose");
        _display=profileNamespace;
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        private _newState=+(_medic getVariable "ACME_menuPose");
        [_oldDisplay] call (_oldDisplay getVariable "Unload");
        0 call _runWait;
        [(_medic getVariable "ACME_menuPose") isEqualTo _newState,"old display retired new menu"] call _check;
        [count _moves==0 && {count _waits==2},"old preparation callback animated new menu"] call _check;
        [!_stanceFreed && {_testAnimationSpeed==1.5},"old unload released the new stance or speed"] call _check;
        1 call _runWait;
        2 call _runWait;
        [_moves isEqualTo ["ACM_GenericContinuous"],"replacement menu lost its entry"] call _check;
    ''')


def test_new_treatment_handoff_retires_pending_menu_without_exit_or_speed_reset():
    execute(setup() + '''
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        // This is the actual ownership handoff used by treatmentPoseStart.
        [_medic,true] call ACME_fnc_menuPoseStop;
        _medic setVariable ["ACME_treatmentPoseEpoch",1];
        _medic setVariable ["ACME_treatmentPoseState",[1,"inspect"]];
        _testAnimationSpeed=0;
        [_display] call (_display getVariable "Unload");
        0 call _runWait;
        [count _moves==0 && {count _waits==1},"retired menu callback animated the treatment"] call _check;
        [!_stanceFreed && {_testAnimationSpeed==0},"old menu unfreezed treatment or released its stance"] call _check;
    ''')


def test_normal_unload_exits_once_then_restores_local_speed():
    execute(setup() + '''
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        0 call _runWait; 1 call _runWait;
        [_display] call (_display getVariable "Unload");
        [(_medic getVariable "ACME_menuPose") isEqualTo [],"unload retained menu owner"] call _check;
        [_stanceFreed,"unload retained forced stance"] call _check;
        [_moves isEqualTo ["ACM_GenericContinuous","AmovPknlMstpSnonWnonDnon"],"unload omitted or replayed its neutral exit"] call _check;
        [count _waits==3 && {_testAnimationSpeed==1.5},"exit did not retain accelerated blend"] call _check;
        2 call _runWait;
        [_testAnimationSpeed==1,"normal menu exit leaked local animation speed"] call _check;
        [(_events select ((count _events)-1)) isEqualTo ["ace_common_setAnimSpeedCoef",[_medic,1]],"normal exit omitted observer speed reset"] call _check;
    ''')


@pytest.mark.parametrize('handoff', ['menu', 'treatment', 'continuous'])
def test_delayed_menu_exit_cannot_reset_new_controller_speed(handoff):
    change = {
        'menu': '[_medic,_patient,profileNamespace] call ACME_fnc_menuPoseStart;',
        'treatment': '_medic setVariable ["ACME_treatmentPoseEpoch",1];',
        'continuous': 'ACM_core_ContinuousAction_Epoch=1;',
    }[handoff]
    execute(setup() + '''
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        [_display] call (_display getVariable "Unload");
    ''' + change + '''
        _testAnimationSpeed=0;
        private _eventCount=count _events;
        1 call _runWait;
        [_testAnimationSpeed==0 && {count _events==_eventCount},"old exit reset a newer controller's speed"] call _check;
    ''')


def test_menu_retires_previous_treatment_exit_before_acquiring_speed():
    execute(setup() + '''
        _medic setVariable ["ACME_treatmentPoseEpisode",[1,false]];
        [_medic,1,"exit","",-1,7,1.5] call ACME_fnc_treatmentPoseSync;
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        [(_medic getVariable "ACME_treatmentPoseRemote") isEqualTo [1,"release",-1],"menu did not retire previous treatment exit"] call _check;
        [_testAnimationSpeed==1.5,"menu did not acquire its own speed"] call _check;
        0 call _runWait;
        [_testAnimationSpeed==1.5,"old treatment exit reset new menu speed"] call _check;
        [("ACME_treatmentPoseSync" in (_events apply {_x select 0})),"retired exit was not released for observers"] call _check;
    ''')


def test_stale_treatment_stop_does_not_retire_newer_exit_when_work_state_is_empty():
    execute(setup() + '''
        _medic setVariable ["ACME_treatmentPoseEpisode",[2,false]];
        [_medic,2,"exit","",-1,7,1.5] call ACME_fnc_treatmentPoseSync;
        [_medic,"",1,true] call ACME_fnc_treatmentPoseStop;
        [(_medic getVariable "ACME_treatmentPoseRemote") isEqualTo [2,"exit",-1],"stale stop retired a newer exit"] call _check;
        [_testAnimationSpeed==1.5,"stale stop reset a newer exit speed"] call _check;
        0 call _runWait;
        [_testAnimationSpeed==1,"matching exit no longer restores normal speed"] call _check;
    ''')
