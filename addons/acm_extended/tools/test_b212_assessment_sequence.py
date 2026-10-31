"""Execute production assessment duration, preparation, sequence, and callback ownership in SQF-VM.

RTM rendering/engine phase values are explicit boundaries. These tests do not claim an Arma visual run.
"""
import re
from functools import lru_cache
import pytest
from test_menu_death_lifecycle import adapt, execute, read, ROOT


def function(name):
    s = read(name)
    s = s.replace('local _medic', '_localMedic')
    s = s.replace('objectParent _medic', '_vehicle').replace('objectParent _patient', '_patientVehicle')
    s = re.sub(r'\bobjectParent _m\b', '_vehicle', s)
    s = re.sub(r'\bstance _m\b', '(["CROUCH","PRONE"] select _prone)', s)
    s = s.replace('stance _medic', '(["CROUCH","PRONE"] select _prone)')
    s = s.replace('_medic setUnitPos "MIDDLE";', '_stanceFreed=false;')
    s = s.replace('animationState _medic', '_animation')
    s = s.replace('_medic getUnitMovesInfo 1', '_nativeElapsed').replace('_medic getUnitMovesInfo 2', '_nativeDuration')
    s = s.replace('netId _medic', '"provider"')
    s = re.sub(r'getNumber \(configFile >> "CfgMovesMaleSdr" >> "States" >> "AinvPknlMstpSnonWnonDr_medic4" >> "speed"\)', '_configuredSpeed', s)
    s = s.replace('getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _main >> "speed")', '_configuredSpeed5')
    s = re.sub(r'finite (_\w+)', r'true', s)
    s = re.sub(r'_medic switchMove (\[[^;]+);', r'_seeks pushBack \1;', s)
    return f'ACME_fnc_{name}={{' + adapt(s) + '};\n'


@lru_cache(maxsize=1)
def setup():
    return r'''
        private _localMedic=true; private _vehicle=objNull; private _patientVehicle=objNull;
        private _animation="ainvpknlmstpsnonwnondr_medic5";
        private _nativeElapsed=0; private _nativeDuration=4; private _configuredSpeed=-4; private _configuredSpeed5=-4;
        private _nativeCalls=[]; private _seeks=[]; private _poseStops=[]; private _banners=[];
        private _permitted=true; private _interactive=true; private _nativeAccepted=true;
        private _poseEpoch=0; private _prone=false; private _leases=[];
        private _request=[_medic,_patient,"Head","CheckAirway"];
        private _nativeArgs=[]; private _added=[]; private _newOwner=false; private _reopened=0;
        ACME_fnc_providerStanceOwned={_newOwner || {(_medic getVariable ["ACME_treatmentPoseState",[]]) isNotEqualTo []}};
        CBA_fnc_execNextFrame={_waits pushBack [_this select 0,_this select 1];};
        CBA_fnc_localEvent={if ((_this select 0)=="ACM_core_openMedicalMenu") then {_reopened=_reopened+1;};};
        CBA_fnc_addKeyHandler={private _id=format ["key%1",count _added]; _added pushBack _this; _id};
        ACME_fnc_chestAccessPreparing={_banners pushBack _this;};
        ACME_fnc_chestAccessVestEvent={_leases pushBack _this;};
        ACME_fnc_patientInteractionDistance={_distance};
        ace_medical_treatment_fnc_canTreatCached={_permitted};
        ace_common_fnc_canInteractWith={_interactive};
        ace_common_fnc_isPlayer={true};
        ACME_fnc_doAnim={_moves pushBack _this;};
        ACME_fnc_treatmentPoseStart={
            params ["_m","_mode"];
            _poseEpoch=_poseEpoch+1;
            private _main=["AinvPknlMstpSnonWnonDr_medic5","AinvPknlMstpSnonWnonDr_medic4"] select (_mode=="assessmentBreathing");
            if (_prone) then {_main="ACM_ProneContinuous";};
            _m setVariable ["ACME_treatmentPoseState",[_poseEpoch,_mode,_main,1,10,-1,7,"",10,-1,10,-1,-1,-1,-1,-1,false,1.5,false,false,_prone]];
            _animation=toLower _main;
            _poseEpoch
        };
        ACME_fnc_treatmentPoseStop={
            _poseStops pushBack _this;
            if (((_medic getVariable ["ACME_treatmentPoseState",[]]) param [0,-1]) == (_this select 2)) then {
                _medic setVariable ["ACME_treatmentPoseState",[]];
            };
        };
        ACM_core_fnc_treatmentNative={
            _nativeCalls pushBack _this;
            _nativeArgs=_this + [objNull,"",false,((_medic getVariable ["ACME_assessment",[]]) param [0,-1])];
            private _seated=_medic getVariable ["ACME_assessmentSeated",[]];
            if ((_nativeArgs select 7)==-1 && {_seated isNotEqualTo []}) then {_nativeArgs pushBack (_seated select 0);};
            _nativeAccepted
        };
        private _frame={
            private _record=_medic getVariable ["ACME_assessment",[]];
            if (_record isEqualTo []) exitWith {};
            private _id=_record select 3;
            private _handler=_handlers select _id;
            [_handler select 1,_id] call (_handler select 0);
        };
        private _ready={(_medic getVariable ["ACME_treatmentPoseState",[]]) set [3,2]; call _frame;};
    ''' + ''.join(function(name) for name in ['assessmentReopen','assessmentTime','assessmentStop','assessmentStart','assessmentTick','assessmentFinish','assessmentProgress','assessmentAdvance','assessmentCompletion'])


# Retain the B212 case identity while testing the longer B213 first-stage duration.
# B218: exact normal-speed duration, retaining historical pytest IDs for baseline comparisons.
@pytest.mark.parametrize('speed,expected',[
    pytest.param(-4,5.75,id='-4-4'), pytest.param(-4.25,6,id='-4.25-4'),
    pytest.param(-4.251,6.001,id='-4.251-5'), pytest.param(-6.125,7.875,id='-6.125-5'),
    pytest.param(.25,5.75,id='0.25-4'), pytest.param(0,0,id='0-0')])
def test_airway_time_uses_runtime_full_medic4_duration_and_ceil(speed,expected):
    execute(setup()+f'_configuredSpeed={speed};'+f'[["CheckAirway"] call ACME_fnc_assessmentTime == {expected},"wrong timer"] call _check;'+'''
        [["CheckBreathing"] call ACME_fnc_assessmentTime == (if (_configuredSpeed==0) then {0} else {if (_configuredSpeed<0) then {-_configuredSpeed} else {1/_configuredSpeed}}),"breathing not full RTM duration"] call _check;
    ''')


@pytest.mark.parametrize('action',['CheckAirway','CheckBreathing'])
def test_preparation_waits_for_actual_work_entry_and_native_timer_starts_once(action):
    execute(setup()+f'_request set [3,"{action}"];'+r'''
        [_request call ACME_fnc_assessmentStart,"start denied"] call _check;
        call _frame; call _frame;
        [count _nativeCalls==1,"entry was not included in the clinical timer"] call _check;
        call _ready; call _frame;
        [count _nativeCalls==1,"native timer missing or duplicated"] call _check;
        [count _added==0,"redundant preflight cancel keys installed"] call _check;
        [[_nativeArgs] call ACME_fnc_assessmentProgress,"current clinical work rejected"] call _check;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"completion retained sequence"] call _check;
        [count _poseStops==1,"completion did not retire pose once"] call _check;
    ''')


@pytest.mark.parametrize('elapsed',[0,1.374,1.375,1.49,1.749,1.75,3.8])
def test_airway_freezes_exact_source_sample_then_interpolates_once(elapsed):
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
    '''+f'_nativeElapsed={elapsed}; call _frame;'+(r'''
        [count _seeks==0 && {count _moves==0},"airway transitioned too early"] call _check;
    ''' if elapsed < 1.75 else r'''
        [count _seeks==1 && {abs (((_seeks select 0) select 1)-1.75/4)<0.00001},"not exact native sample"] call _check;
        [(_moves select 0) isEqualTo [_medic,"AinvPknlMstpSnonWnonDr_medic4",1],"not interpolated medic4"] call _check;
        [_testAnimationSpeed==1,"second animation was accelerated"] call _check;
        call _frame;
        [count _seeks==1 && {count _moves==1},"second stage restarted"] call _check;
        [((_medic getVariable ["ACME_treatmentPoseState",[]]) select 11)==-1,"medic4 inherited freeze"] call _check;
    '''))


@pytest.mark.parametrize('invalidation',[
    '_localMedic=false;', '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_distance=10;', '_interactive=false;', '_permitted=false;', 'CBA_missionTime=16;',
])
def test_invalid_or_timed_out_preparation_never_launches(invalidation):
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
    '''+invalidation+r'''
        call _ready;
        [count _nativeCalls==1,"entry cancellation relaunched treatment"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"invalid prep retained sequence"] call _check;
        [count _added==0,"redundant input handlers leaked"] call _check;
    ''')


@pytest.mark.parametrize('action',['CheckAirway','CheckBreathing'])
def test_prone_sequence_never_seeks_or_starts_kneeling_stage(action):
    execute(setup()+f'_request set [3,"{action}"];'+r'''
        _prone=true; _request call ACME_fnc_assessmentStart; call _ready;
        _nativeElapsed=3; call _frame;
        [count _seeks==0 && {count _moves==0},"prone assessment sought kneeling RTM"] call _check;
        [count _nativeCalls==1,"prone clinical timer blocked"] call _check;
    ''')


def test_old_finish_and_worker_do_not_touch_new_same_class_assessment():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        private _oldArgs=+_nativeArgs; private _old=+(_handlers select 0);
        [_medic,1] call ACME_fnc_assessmentStop;
        _request call ACME_fnc_assessmentStart; call _ready;
        [_oldArgs] call ACME_fnc_assessmentFinish;
        [_old select 1,0] call (_old select 0);
        [((_medic getVariable ["ACME_assessment",[]]) select 0)==2,"old callback released new same-class action"] call _check;
        [!([_oldArgs] call ACME_fnc_assessmentProgress),"old clinical callback accepted successor"] call _check;
    ''')


def test_preflight_rejection_releases_dp_pause_and_own_carrier_lease():
    execute(setup()+r'''
        _request set [3,"CheckBreathing"];
        _medic setVariable ["ACME_chestAccess_treatment",[_patient,"checkbreathing","lease"]];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","checkbreathing"];
        _medic setVariable ["ACME_DP_Paused",true];
        _nativeAccepted=false; _request call ACME_fnc_assessmentStart;
        [!(_medic getVariable ["ACME_DP_Paused",true]),"failed startup stranded DP"] call _check;
        [count _leases==1 && {!((_leases select 0) select 3)},"failed startup retained carrier lease"] call _check;
    ''')


def test_cancel_key_uses_direct_local_provider_even_without_network_identity():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
        // Native progress owns ESC/RMB from the first frame; its failure callback retires this exact episode.
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"RMB failed to cancel local prep"] call _check;
        [count _nativeCalls==1 && {count _added==0},"native cancellation leaked preflight handlers"] call _check;
    ''')


@pytest.mark.parametrize('elapsed,expected',[(3.999,4),(4,5),(4.35,5),(5,6),(9,-1)])
def test_active_final_rtm_never_completes_at_nominal_deadline(elapsed,expected):
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        _nativeElapsed=1.75; call _frame;
    '''+f'''private _result=[_nativeArgs,{elapsed},4,4] call ACME_fnc_assessmentCompletion;
        [_result=={expected},"final RTM clipped or deadline not rounded/bounded"] call _check;
    ''')


@pytest.mark.parametrize('natural_exit',[False,True])
def test_final_animation_must_run_all_native_seconds_before_completion(natural_exit):
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        _nativeElapsed=1.75; call _frame;
        _animation="ainvpknlmstpsnonwnondr_medic4";
        CBA_missionTime=11.5; _nativeElapsed=0; _nativeDuration=4; call _frame;
        CBA_missionTime=13; _nativeElapsed=2.25; call _frame;
        [(_medic getVariable ["ACME_assessment",[]]) select 2 == 2,"incomplete final animation marked complete"] call _check;
        CBA_missionTime=15.5; _nativeElapsed=4;
    '''+('_animation="amovpknlmstpsnonwnondnon";' if natural_exit else '')+r'''
        call _frame;
        [(_medic getVariable ["ACME_assessment",[]]) select 2 == 3,"complete final animation not recognized"] call _check;
        [[_nativeArgs,5,5,4] call ACME_fnc_assessmentCompletion == 5,"finished animation extended unnecessarily"] call _check;
    ''')


@pytest.mark.parametrize('gap,advance',[(.2,False),pytest.param(2.8,False,id='2.8-True'),(5,True)])
def test_sparse_frame_past_full_medic5_recovers_exact_sample_but_early_interrupt_cancels(gap,advance):
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        _animation="amovpknlmstpsnonwnondnon";
    '''+f'CBA_missionTime=10+{gap}; call _frame;'+(r'''
        [count _seeks==1 && {abs (((_seeks select 0) select 1)-1.75/4)<0.00001},"sparse frame lost exact first sample"] call _check;
        [count _moves==1,"sparse frame did not interpolate once"] call _check;
    ''' if advance else r'''
        [count _seeks==0 && {count _moves==0},"interrupt replayed first animation"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"interrupted medic5 retained action"] call _check;
    '''))


def progress_worker():
    source=read('assessmentProgressBar')
    start=source.index('[{')+1
    end=source.rindex('}, 0,')+1
    source=source[start:end].replace('ACE_player != _player','ACE_player isNotEqualTo _player')
    source=re.sub(r'\(uiNamespace getVariable [^\n]+\) (?:progressSetPosition|ctrlSetText) [^\n]+;', '', source)
    source=source.replace('alive _player','_alive')
    source=source.replace('params ["_args", "_onFinish"','params ["_args", "_onFinish"')
    return adapt(source)


def test_real_progress_worker_retains_same_display_until_completed_rounded_deadline():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        _nativeElapsed=1.75; call _frame;
        private _finished=0; private _failed=0;
        uiNamespace setVariable ["ace_common_ctrlProgressBar",profileNamespace];
        ace_common_settingProgressBarLocation=0; ace_common_progressBarInfo=0;
        private _payload=[_nativeArgs,{_finished=_finished+1;},{_failed=_failed+1;},
            ACME_fnc_assessmentProgress,_medic,10,4,[],"Check Airway",true,4];
        private _id=count _handlers;
        _handlers pushBack [{},[],true];
    '''+'private _barWorker='+progress_worker()+';'+r'''
        CBA_missionTime=14.1; [_payload,_id] call _barWorker;
        [_finished==0 && {_failed==0} && {(_payload select 6)==5},"nominal timer closed/reset live progress"] call _check;
        (_medic getVariable ["ACME_assessment",[]]) set [2,3];
        CBA_missionTime=14.3; [_payload,_id] call _barWorker;
        [_finished==1 && {_failed==0} && {!((_handlers select _id) select 2)},"completed RTM waited for an arbitrary rounded second"] call _check;
    ''')


def test_missing_final_rtm_times_out_through_native_failure_and_no_success():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        _nativeElapsed=1.75; call _frame;
        private _finished=0; private _failed=0;
        uiNamespace setVariable ["ace_common_ctrlProgressBar",profileNamespace];
        ace_common_progressBarInfo=0;
        private _payload=[_nativeArgs,{_finished=_finished+1;},{_failed=_failed+1;},
            ACME_fnc_assessmentProgress,_medic,10,4,[],"Check Airway",true,4];
        private _id=count _handlers; _handlers pushBack [{},[],true];
    '''+'private _barWorker='+progress_worker()+';'+r'''
        CBA_missionTime=19; [_payload,_id] call _barWorker;
        [_finished==0 && {_failed==1},"unavailable final RTM reported success or stuck indefinitely"] call _check;
    ''')


@pytest.mark.parametrize('action',['CheckAirway','CheckBreathing'])
def test_onfoot_assessment_cannot_resume_as_seated_after_vehicle_cancellation(action):
    execute(setup()+f'_request set [3,"{action}"];'+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        _vehicle=missionNamespace; _patientVehicle=missionNamespace;
        call _frame;
        [!([_nativeArgs] call ACME_fnc_assessmentProgress),"on-foot episode revived in shared vehicle"] call _check;
        [[_nativeArgs,4,4,4] call ACME_fnc_assessmentCompletion == -1,"cancelled on-foot action reported seated completion"] call _check;
    ''')


@pytest.mark.parametrize('action',['CheckAirway','CheckBreathing'])
def test_genuine_seated_assessment_uses_no_pose_but_keeps_native_duration(action):
    execute(setup()+f'_request set [3,"{action}"];'+r'''
        _vehicle=missionNamespace; _patientVehicle=missionNamespace;
        [_request call ACME_fnc_assessmentStart,"seated assessment denied"] call _check;
        [count _nativeCalls==1 && {count _handlers==0} && {count _moves==0},"seated action tried on-foot theatre"] call _check;
        [[_nativeArgs] call ACME_fnc_assessmentProgress,"seated native callback rejected"] call _check;
        [[_nativeArgs,4,4,4] call ACME_fnc_assessmentCompletion == 4,"seated assessment waited for absent RTM"] call _check;
    ''')


def test_observed_final_rtm_interruption_fails_immediately_and_cannot_become_natural_exit():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        _nativeElapsed=1.75; call _frame;
        _animation="ainvpknlmstpsnonwnondr_medic4";
        CBA_missionTime=11; _nativeElapsed=0; _nativeDuration=4; call _frame;
        _animation="amovpknlmstpsnonwnondnon";
        CBA_missionTime=11.1; call _frame;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"early observed medic4 exit was tolerated"] call _check;
        CBA_missionTime=16;
        [[_nativeArgs,6,6,4] call ACME_fnc_assessmentCompletion == -1,"interrupted final RTM later passed by clock alone"] call _check;
    ''')


@pytest.mark.parametrize('stance',['STAND','CROUCH','PRONE'])
def test_actual_shared_pose_controller_and_assessment_worker_complete_one_owned_episode(stance):
    from test_historical_pose_lifecycle import setup as shared_setup
    code=setup()+shared_setup()
    # All ownership/start/stop/receiver functions above now execute their production implementations.
    # Keep one shared stand-in for the engine animation rate across both sets of engine adapters.
    for name in ['assessmentStop','assessmentStart','assessmentTick','assessmentAdvance']:
        code+=function(name).replace('_testAnimationSpeed','_speed')
    execute(code+f'_stance="{stance}";'+r'''
        _request call ACME_fnc_assessmentStart;
        private _pose=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _poseId=_pose select 5;
        CBA_missionTime=12; [_poseId] call _poseTick;
        _animation=toLower (_pose select 2); _nativeElapsed=0; _duration=4;
        [_poseId] call _poseTick; call _frame;
        [count _nativeCalls==1 && {(_pose select 3)==2},"actual shared controller never launched clinical work"] call _check;
    '''+(r'''
        CBA_missionTime=13.166667; _nativeElapsed=1.75; _nativeDuration=4; call _frame;
        [(_pose select 2)=="AinvPknlMstpSnonWnonDr_medic4" && {(_pose select 3)==1},"handoff did not update shared pose"] call _check;
        _animation="ainvpknlmstpsnonwnondr_medic4"; _nativeElapsed=0;
        [_poseId] call _poseTick; call _frame;
        CBA_missionTime=15.85; _nativeElapsed=4; call _frame;
        [(_medic getVariable ["ACME_assessment",[]]) select 2==3,"shared second RTM failed full completion"] call _check;
    ''' if stance!='PRONE' else r'''
        [(_pose select 20) && {(_positions find "MIDDLE")==-1},"actual prone work crouched"] call _check;
    ''')+r'''
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo [],"actual pose cleanup retained state"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"assessment completion retained worker"] call _check;
        [_poseId in _removed,"actual pose PFH not removed"] call _check;
        {[_x] call _deliver;} forEach +_speedWaits;
        [_speed==1,"actual cleanup left provider accelerated or frozen"] call _check;
    ''')


@pytest.mark.parametrize('successor',['pose','native'])
def test_retired_preflight_does_not_reopen_menu_over_successor_treatment(successor):
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
    '''+('''_medic setVariable ["ACME_treatmentPoseState",[99,"replacement"]];''' if successor=='pose' else '''
        _medic setVariable ["ACME_treatmentPoseState",[]]; _newOwner=true;
    ''')+r'''
        call _frame;
        [_reopened==0,"old preflight reopened menu over replacement intervention"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"retired preflight retained its worker"] call _check;
    ''')
