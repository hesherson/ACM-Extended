"""Execute DP weapon preflight, finite exits, and successor ownership in SQF-VM.

Native weapon/animation/config/input are explicit boundaries, not an Arma renderer.
The production claim handshake, held worker, DP tick, enter/exit, and cleanup execute.
"""
import pytest

from test_b211_direct_pressure_inputs import setup as pressure_setup
from test_b209_direct_pressure_locality import source
from test_menu_death_lifecycle import execute, read


def setup():
    return pressure_setup() + '''
        private _holsters=0;
        ace_common_fnc_isPlayer={true};
        ace_weaponselect_fnc_putWeaponAway={_holsters=_holsters+1;};
    ''' + 'ACME_fnc_medicAnimationPrep={' + source('medicAnimationPrep').replace('handgunWeapon _medic', '"pistol"') + '};'


@pytest.mark.parametrize('weapon,delay', [('rifle', 0.70), ('pistol', 0.95)])
def test_real_holster_finishes_before_first_hold_and_is_never_replayed_on_resume(weapon, delay):
    execute(setup() + f'''
        _dpWeapon="{weapon}"; _animation="amovpknlmstpsraswrfldnon";
        ["leftarm"] call _start;
        [_holsters==1,"first hold did not issue exactly one real holster"] call _check;
        [!(_medic getVariable ["ACME_DP_InPose",false]),"hold started under selected weapon"] call _check;
        CBA_missionTime=CBA_missionTime+0.1; call _pressTick;
        [_holsters==1,"pending holster replayed"] call _check;
        _dpWeapon=""; CBA_missionTime=CBA_missionTime+{delay}; call _pressTick;
        [!(_medic getVariable ["ACME_DP_InPose",false]),"logical empty hands skipped visible holster"] call _check;
        _animation="amovpknlmstpsnonwnondnon"; call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"completed weapon preflight did not enter hold"] call _check;
        private _holdId=count _handlers-1; _holdId call _tick;
        _animation="acme_directpressurehold"; _inputActions=["MoveForward"]; call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"movement stopped clinical pressure"] call _check;
        call _finishPressureExit;
        _animation="amovpknlmstpsnonwnondnon"; _inputActions=[]; call _pressTick;
        [!(_medic getVariable ["ACME_DP_InPose",false]),"pressure skipped two-second quiet interval"] call _check;
        CBA_missionTime=(_medic getVariable "ACME_DP_IdleStart")+2; call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"pressure did not resume after full exit and quiet interval"] call _check;
        [_holsters==1 && {{_dpWeapon==""}},"resume replayed holster or restored selected weapon"] call _check;
    ''')


@pytest.mark.parametrize('busy', [
    '_medic setVariable ["ACME_DP_TreatmentBusy",true];',
    '_medic setVariable ["ACME_treatmentPoseState",[99,"auscultate"]];',
    '_medic setVariable ["ACME_chestAccessProvider",[_patient,"lease"]];',
    '_medic setVariable ["ACME_nativeTreatmentRate",[99]];',
    'ACM_core_ContinuousAction_Active=true;',
])
def test_first_entry_grace_and_repeated_pressure_ticks_never_cancel_successor_worker(busy):
    execute(setup() + '''
        ["body"] call _start;
        private _ownGen=_medic getVariable "ACME_DP_HeldGeneration";
    ''' + busy + '''
        [_medic,"ACME_StethoscopeWork",1.1,1,true] call ACME_fnc_doAnimHeld;
        private _scopeId=count _handlers-1;
        private _scopeGen=_medic getVariable "ACME_dah_gen";
        [_scopeGen>_ownGen,"successor never reserved its generation"] call _check;
        for "_i" from 1 to 3 do {call _pressTick; CBA_missionTime=CBA_missionTime+0.01;};
        [(_medic getVariable "ACME_dah_gen")==_scopeGen,"DP busy frames cancelled newer scope animation"] call _check;
        [!(_medic getVariable ["ACME_DP_InPose",true]),"entry grace masked a real successor"] call _check;
        _moves=[]; _scopeId call _tick;
        [count _moves==1 && {((_moves select 0) select 1)=="ACME_StethoscopeWork"},"scope provider animation was blocked"] call _check;
    ''')


@pytest.mark.parametrize('operation', ['move', 'cancel', 'look-away'])
def test_exit_runs_exact_medic_end_at_one_point_five_with_no_early_resume(operation):
    trigger = {
        'move': '_inputActions=["MoveForward"]; call _pressTick;',
        'cancel': '[false,_medic] call ACME_fnc_directPressureStop;',
        'look-away': '_look=[0,-1,0]; call _pressTick;',
    }[operation]
    execute(setup() + '''
        ["body"] call _start; _animation="acme_directpressurehold"; CBA_missionTime=CBA_missionTime+0.2;
        _moves=[];
    ''' + trigger + f'''
        [count _moves==1 && {{((_moves select 0) select 1)=="AinvPknlMstpSnonWnonDnon_medicEnd"}},"wrong pressure exit animation"] call _check;
        [_testAnimationSpeed==1,"pending exit accelerated movement before its RTM"] call _check;
        private _exitId=count _handlers-1;
        _inputActions=[]; _look=[0,1,0];
        _animation="ainvpknlmstpsnonwnondnon_medicend";
        _testAnimationSpeed=1; _exitId call _tick;
        [_testAnimationSpeed==1.5,"Animate walk reset was not repaired during owned exit"] call _check;
        CBA_missionTime=CBA_missionTime+0.5;
        if (_medic getVariable ["ACME_DP_Active",false]) then {{call _pressTick;}};
        [!(_medic getVariable ["ACME_DP_InPose",true]),"stationary pressure clipped finite exit"] call _check;
        _exitId call _tick;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isNotEqualTo [],"exit ended before native RTM duration"] call _check;
        CBA_missionTime=CBA_missionTime+0.71; _exitId call _tick;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isEqualTo [],"completed exit never released"] call _check;
        [_testAnimationSpeed==1,"exit left movement accelerated"] call _check;
        [(_medic getVariable ["ACME_DP_Active",false]) isEqualTo {str(operation != 'cancel').lower()},"exit changed wrong clinical episode"] call _check;
    ''')


@pytest.mark.parametrize('replacement', [
    '_medic setVariable ["ACME_treatmentPoseEpoch",10]; _medic setVariable ["TEST_speedOwner",true]; _testAnimationSpeed=0;',
    '_medic setVariable ["ACME_nativeTreatmentRate",[10]]; _medic setVariable ["TEST_speedOwner",true]; _testAnimationSpeed=1.7;',
    '_medic setVariable ["ACME_DP_PoseToken",99];',
    '_medic setVariable ["ACME_providerLocalityEpoch",99];',
    '_medic setVariable ["TEST_owner",8];',
])
def test_exit_callback_does_not_reanimate_or_change_successor_rate(replacement):
    execute(setup() + '''
        ["body"] call _start; _animation="acme_directpressurehold";
        _inputActions=["MoveForward"]; CBA_missionTime=CBA_missionTime+0.2; call _pressTick;
        private _exitId=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _exitId call _tick;
    ''' + replacement + '''
        private _expectedRate=_testAnimationSpeed;
        _moves=[]; CBA_missionTime=CBA_missionTime+3; _exitId call _tick;
        [count _moves==0,"old pressure exit reanimated successor"] call _check;
        if (_medic getVariable ["TEST_speedOwner",false]) then {
            [_testAnimationSpeed==_expectedRate,"old pressure exit changed successor-owned speed"] call _check;
        };
        [_exitId in _removed,"stale exit worker did not retire"] call _check;
    ''')


def test_cancel_while_moving_finishes_existing_exit_once_without_restarting_it():
    execute(setup() + '''
        ["body"] call _start; _animation="acme_directpressurehold";
        _inputActions=["MoveForward"]; CBA_missionTime=CBA_missionTime+0.2; call _pressTick;
        private _exitId=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _exitId call _tick;
        private _count=count _moves;
        [false,_medic] call ACME_fnc_directPressureStop;
        [count _moves==_count,"cancel restarted ongoing movement exit"] call _check;
        CBA_missionTime=CBA_missionTime+0.2; _exitId call _tick;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isNotEqualTo [],"cancel retired ongoing medicEnd early"] call _check;
        CBA_missionTime=CBA_missionTime+1.01; _exitId call _tick;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isEqualTo [],"cancelled exit remained active"] call _check;
        [_testAnimationSpeed==1,"cancelled exit kept1.5 movement rate"] call _check;
    ''')


def test_movement_superseding_exit_keeps_move_and_restores_rate_without_snap():
    execute(setup() + '''
        ["body"] call _start; _animation="acme_directpressurehold";
        _inputActions=["MoveForward"]; CBA_missionTime=CBA_missionTime+0.2; call _pressTick;
        private _exitId=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _exitId call _tick;
        _animation="amovpknlmwlksnonwnondf"; _moves=[]; _exitId call _tick;
        [count _moves==0,"finished exit overwrote actual movement"] call _check;
        [_testAnimationSpeed==1,"movement inherited exit acceleration"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"actual movement cancelled pressure"] call _check;
    ''')


def test_preflight_cancel_has_no_delayed_animation_worker_or_weapon_restore():
    execute(setup() + '''
        _dpWeapon="rifle"; _animation="amovpknlmstpsraswrfldnon";
        ["body"] call _start;
        [false,_medic] call ACME_fnc_directPressureStop;
        _moves=[]; _dpWeapon=""; _animation="amovpknlmstpsnonwnondnon";
        CBA_missionTime=CBA_missionTime+3;
        [_medic,_patient] call ACME_fnc_directPressurePoseEnter;
        [count _moves==0 && {!(_medic getVariable ["ACME_DP_InPose",false])},"cancelled preflight revived pressure"] call _check;
        [_holsters==1 && {_dpWeapon==""},"cancel restored weapon or repeated holster"] call _check;
    ''')


@pytest.mark.parametrize('when', ['before-entry', 'during-exit'])
def test_unconscious_provider_never_gets_medical_exit_or_neutral_pose(when):
    execute(setup() + '''
        ["body"] call _start; _animation="acme_directpressurehold";
        _inputActions=["MoveForward"]; CBA_missionTime=CBA_missionTime+0.2;
    ''' + ('''
        _medic setVariable ["ACE_isUnconscious",true];
        _moves=[]; call _pressTick;
        [count _moves==0,"downed provider entered medical exit"] call _check;
    ''' if when == 'before-entry' else '''
        call _pressTick; private _exitId=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _exitId call _tick;
        _medic setVariable ["ACE_isUnconscious",true];
        _animation="unconscious"; _moves=[]; _exitId call _tick;
        [count _moves==0,"exit cleanup replaced unconscious animation"] call _check;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isEqualTo [],"unconscious exit never retired"] call _check;
    '''))


def test_starting_during_movement_waits_for_idle_and_repeated_move_does_not_replay_exit():
    execute(setup() + '''
        _inputActions=["MoveForward"]; ["body"] call _start;
        [!(_medic getVariable ["ACME_DP_InPose",false]),"pressure forced hold while moving at start"] call _check;
        _inputActions=[]; call _pressTick;
        [!(_medic getVariable ["ACME_DP_InPose",false]),"first quiet frame entered pressure"] call _check;
        CBA_missionTime=(_medic getVariable "ACME_DP_IdleStart")+2; call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"two quiet seconds did not enter pressure"] call _check;
        _animation="acme_directpressurehold"; _inputActions=["MoveForward"]; CBA_missionTime=CBA_missionTime+0.2;
        call _pressTick; private _movesBefore=count _moves; private _handlersBefore=count _handlers;
        for "_i" from 1 to 5 do {CBA_missionTime=CBA_missionTime+0.016; call _pressTick;};
        [count _moves==_movesBefore && {count _handlers==_handlersBefore},"movement replayed medicEnd each tick"] call _check;
    ''')


@pytest.mark.parametrize('helper', ['providerStanceOwned', 'providerAnimSpeedOwned'])
@pytest.mark.parametrize('state,expected', [
    ('[1,0,0,0,CBA_missionTime,-1,1.2,1,"end","neutral"]', True),
    ('[1,0,1,0,CBA_missionTime,-1,1.2,1,"end","neutral"]', False),
    ('[1,0,0,0,CBA_missionTime-4,-1,1.2,1,"end","neutral"]', False),
])
def test_shared_ownership_recognizes_only_live_locality_matching_exit(helper,state,expected):
    execute(setup() + 'ACME_fnc_'+helper+'={'+source(helper)+'};'+f'''
        _medic setVariable ["ACME_DP_Exit",{state}];
        private _owned=[_medic] call ACME_fnc_{helper};
        [_owned isEqualTo {str(expected).lower()},"shared helper retained stale pressure exit ownership"] call _check;
    ''')


def observer_setup():
    return setup() + 'ACME_fnc_directPressurePoseExitSync={'+source('directPressurePoseExitSync')+'};'+'''
        _medic setVariable ["TEST_owner",8];
        private _episode=[_networkTime,1,8];
        _medic setVariable ["ACME_DP_ExitEpisode",_episode+[true]];
        private _sync={params [["_active",true]]; [_medic,_episode,0,1.2,_active] call ACME_fnc_directPressurePoseExitSync;};
    '''


def test_observer_waits_for_public_episode_and_actual_exit_before_setting_rate():
    execute(observer_setup() + '''
        _medic setVariable ["ACME_DP_ExitEpisode",[]];
        [] call _sync; private _id=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _id call _tick;
        [_testAnimationSpeed==1,"unknown public episode changed observer speed"] call _check;
        _medic setVariable ["ACME_DP_ExitEpisode",_episode+[true]];
        _animation="amovpknlmstpsnonwnondnon"; _id call _tick;
        [_testAnimationSpeed==1,"pending medicEnd changed ordinary movement speed"] call _check;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _id call _tick;
        [_testAnimationSpeed==1.5,"observed end never took1.5 rate"] call _check;
        [false] call _sync; _id call _tick;
        [_testAnimationSpeed==1,"matching observer release never restored rate"] call _check;
    ''')


def test_observer_stop_before_start_rejects_reordered_old_start():
    execute(observer_setup() + '''
        [false] call _sync; [] call _sync;
        [count _handlers==1 && {!((_medic getVariable "ACME_DP_ExitRemote") select 1)},"late start revived stopped observer episode"] call _check;
        [_testAnimationSpeed==1,"reordered packets changed provider rate"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_medic setVariable ["ACME_treatmentPoseEpoch",1]; _testAnimationSpeed=0;',
    '_medic setVariable ["ACME_DP_ExitEpisode",[_networkTime+0.1,2,8,true]];',
    '_medic setVariable ["TEST_owner",7];',
    '_animation="acme_stethoscopework"; _testAnimationSpeed=0;',
])
def test_observer_late_stop_never_resets_replacement_or_new_owner(change):
    execute(observer_setup() + '''
        [] call _sync; private _id=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _id call _tick;
        [_testAnimationSpeed==1.5,"observer never acquired exit rate"] call _check;
    '''+change+'''
        // Local speed is not inherited from the old remote exit on owner transfer.
        private _expected=if ((_medic getVariable ["TEST_owner",8])==7) then {1} else {_testAnimationSpeed};
        [false] call _sync; _id call _tick;
        [_testAnimationSpeed==_expected,"old observer stop altered replacement rate"] call _check;
        if (((_medic getVariable ["ACME_DP_ExitEpisode",[]]) param [0,0]) > _networkTime) then {
            _animation="amovpknlmstpsnonwnondnon"; _id call _tick;
        };
        [_id in _removed,"old observer worker did not retire"] call _check;
    ''')


def test_observer_expired_start_and_duplicate_start_do_not_replay_or_leak():
    execute(observer_setup() + '''
        _networkTime=_networkTime+10; [] call _sync;
        [count _handlers==0,"expired start spawned observer work"] call _check;
        _networkTime=_networkTime-10; [] call _sync; [] call _sync;
        [count _handlers==1,"duplicate start spawned second rate worker"] call _check;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; 0 call _tick;
        _networkTime=_networkTime+5; 0 call _tick;
        [_testAnimationSpeed==1,"lost stop packet leaked observer rate"] call _check;
        [0 in _removed,"expired observer never retired"] call _check;
    ''')



def test_observer_newer_exit_wins_when_packets_share_same_timestamp():
    execute(observer_setup() + '''
        [] call _sync; private _oldId=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _oldId call _tick;
        private _newEpisode=[_networkTime,2,8];
        _medic setVariable ["ACME_DP_ExitEpisode",_newEpisode+[true]];
        [_medic,_newEpisode,0,1.2,true] call ACME_fnc_directPressurePoseExitSync;
        private _newId=count _handlers-1;
        [false] call _sync; [] call _sync;
        private _record=_medic getVariable "ACME_DP_ExitRemote";
        [(_record select 0) isEqualTo _newEpisode && {_record select 1},"same-timestamp old packet replaced newest exit"] call _check;
        _oldId call _tick; _newId call _tick;
        [_testAnimationSpeed==1.5,"old receiver reset replacement exit"] call _check;
        [_medic,_newEpisode,0,1.2,false] call ACME_fnc_directPressurePoseExitSync;
        _newId call _tick;
        [_testAnimationSpeed==1,"new receiver inherited stale1.5 prior rate"] call _check;
    ''')



def test_observer_newer_stop_before_start_retires_inherited_old_rate():
    execute(observer_setup() + '''
        [] call _sync; private _oldId=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _oldId call _tick;
        [_testAnimationSpeed==1.5,"old episode never acquired rate"] call _check;
        private _newEpisode=[_networkTime+0.1,2,8];
        _medic setVariable ["ACME_DP_ExitEpisode",_newEpisode+[false]];
        [_medic,_newEpisode,0,1.2,false] call ACME_fnc_directPressurePoseExitSync;
        private _cleanupId=count _handlers-1;
        [_medic,_newEpisode,0,1.2,true] call ACME_fnc_directPressurePoseExitSync;
        _animation="amovpknlmstpsnonwnondnon";
        _oldId call _tick; _cleanupId call _tick;
        [_testAnimationSpeed==1,"stop-first newer episode leaked old observer1.5 rate"] call _check;
        [!((_medic getVariable "ACME_DP_ExitRemote") select 1),"late start revived stop-first tombstone"] call _check;
    ''')



def test_exit_prefers_observed_native_rtm_completion_over_wall_clock_guess():
    execute(setup() + '''
        ["body"] call _start; _animation="acme_directpressurehold";
        [false,_medic] call ACME_fnc_directPressureStop;
        private _id=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend";
        _dpNativeElapsed=0; _dpNativeDuration=1.8; _id call _tick;
        CBA_missionTime=CBA_missionTime+1.3; _dpNativeElapsed=1.2; _id call _tick;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isNotEqualTo [],"wall clock clipped incomplete native medicEnd"] call _check;
        _dpNativeElapsed=1.8; _id call _tick;
        [(_medic getVariable ["ACME_DP_Exit",[]]) isEqualTo [],"native completed medicEnd never released"] call _check;
    ''')


@pytest.mark.parametrize('stop_arrives', [False, True])
def test_observer_public_successor_overtaking_packets_does_not_discard_owned_rate(stop_arrives):
    execute(observer_setup() + '''
        [] call _sync; private _oldId=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _oldId call _tick;
        private _newEpisode=[_networkTime+0.1,2,8];
        _medic setVariable ["ACME_DP_ExitEpisode",_newEpisode+[false]];
        _oldId call _tick;
        [_testAnimationSpeed==1.5,"old observer changed successor medicEnd rate"] call _check;
    '''+('''
        [_medic,_newEpisode,0,1.2,false] call ACME_fnc_directPressurePoseExitSync;
        private _cleanupId=count _handlers-1;
        _animation="amovpknlmstpsnonwnondnon";
        _oldId call _tick; _cleanupId call _tick;
    ''' if stop_arrives else '''
        _animation="amovpknlmstpsnonwnondnon"; _oldId call _tick;
    ''')+'''
        [_testAnimationSpeed==1,"public successor discarded rate ownership before packet/neutral cleanup"] call _check;
    ''')



def test_prone_selected_during_finite_exit_remains_prone_at_cleanup():
    execute(setup() + '''
        ["body"] call _start; _animation="acme_directpressurehold";
        [false,_medic] call ACME_fnc_directPressureStop;
        private _id=count _handlers-1;
        _animation="ainvpknlmstpsnonwnondnon_medicend"; _id call _tick;
        _providerStance="PRONE"; CBA_missionTime=CBA_missionTime+1.21;
        _moves=[]; _id call _tick;
        [count _moves==1 && {((_moves select 0) select 1)=="AmovPpneMstpSnonWnonDnon"},"exit cleanup raised newly prone provider"] call _check;
    ''')


@pytest.mark.parametrize('posture', ['kneeling', 'prone', 'moving-exit'])
def test_actual_medical_menu_bridge_stops_pressure_before_native_started_hook(posture):
    from test_menu_death_lifecycle import ROOT

    bridge = (ROOT / 'addons/core/overrides/fnc_treatment.sqf').read_text()
    # Execute the exact early treatment bridge, including its menu refresh and both DP actions.
    # The following generic procedure branch is unreachable for these two action classes.
    bridge = bridge.split('if !([_medic, _classname] call ACME_fnc_procedureActionAllowed)', 1)[0]
    hooks = source('registerProviderStanceReleaseRuntime')
    execute(setup() + '''
        private _registered=[]; private _nativeEvents=0; private _canTreatCalls=0; private _respStops=0;
        CBA_fnc_addEventHandler={_registered pushBack _this;};
        ACME_fnc_respirationStop={_respStops=_respStops+1;};
        ACME_fnc_feelSkinStop={};
        ace_medical_treatment_fnc_canTreatCached={_canTreatCalls=_canTreatCalls+1; true};
    ''' + hooks + '''
        CBA_fnc_localEvent={
            params ["_name","_args"];
            if (_name in ["ace_treatmentStarted","ace_treatmentSucceded","ace_treatmentFailed"]) then {
                _nativeEvents=_nativeEvents+1;
            };
            {if ((_x select 0)==_name) then {_args call (_x select 1);};} forEach _registered;
        };
        private _treatmentBridge={
    ''' + source('directPressureStart', bridge) + '};' +
        ('_providerStance="PRONE";' if posture == 'prone' else '') + '''
        [_medic,_patient,"Body","ACME_DirectPressure"] call _treatmentBridge;
        call _deliver; call _deliver;
        [_medic getVariable ["ACME_DP_Active",false],"menu bridge did not activate direct pressure"] call _check;
        _animation=toLower (_medic getVariable "ACME_DP_Pose");
        CBA_missionTime=CBA_missionTime+0.2;
    ''' + ('''
        _inputActions=["MoveForward"]; call _pressTick;
        _animation="ainvpknlmstpsnonwnondnon_medicend";
        (count _handlers-1) call _tick;
    ''' if posture == 'moving-exit' else '') + '''
        _moves=[];
        private _accepted=[_medic,_patient,"Body","ACME_StopDirectPressure"] call _treatmentBridge;
        [_accepted && {!(_medic getVariable ["ACME_DP_Active",true])},"menu stop bridge retained pressure"] call _check;
        [_nativeEvents==0 && {_respStops==0},"menu DP toggle entered native treatment lifecycle"] call _check;
        [_canTreatCalls==1,"menu stop depended on a new canTreat/preflight pass"] call _check;
        [!(_medic getVariable ["ACME_DP_TreatmentBusy",true]),"menu stop manufactured successor Busy"] call _check;
    ''' + ('''
        [count _moves==1 && {((_moves select 0) select 1)=="AinvPknlMstpSnonWnonDnon_medicEnd"},"menu stop skipped requested medicEnd"] call _check;
        [_testAnimationSpeed==1,"menu stop accelerated before visible exit"] call _check;
        _animation="ainvpknlmstpsnonwnondnon_medicend";(count _handlers-1) call _tick;
        [_testAnimationSpeed==1.5,"observed menu stop exit missed1.5 rate"] call _check;
    ''' if posture == 'kneeling' else '''
        [count _moves==1 && {((_moves select 0) select 1)=="AmovPpneMstpSnonWnonDnon"},"menu stop raised prone provider"] call _check;
    ''' if posture == 'prone' else '''
        [count _moves==0 && {(_medic getVariable ["ACME_DP_Exit",[]]) isNotEqualTo []},"menu stop restarted or discarded ongoing exit"] call _check;
    '''))
