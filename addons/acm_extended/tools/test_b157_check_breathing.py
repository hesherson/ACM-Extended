"""Current Check Breathing preparation, timed work, and exact completion gates.

Historical test identities are retained. B218 starts native progress with provider
entry and uses the configured full Dr_medic4 duration (prone equivalent when needed).
Engine rendering is a boundary; production sequence and carrier/event cleanup execute.
"""
import pytest
from test_menu_death_lifecycle import adapt, execute, read
from test_b212_assessment_sequence import setup as assessment_setup
from test_chestseal_preparation_progress import setup as patient_setup, function
from test_chest_entry_timing import setup as pose_setup


def setup():
    return assessment_setup() + r'''
        _request set [3,"CheckBreathing"];
        private _eventHandlers=[];
        CBA_fnc_addEventHandler={_eventHandlers pushBack _this;};
        private _emit={params ["_name","_eventArgs"]; {if ((_x select 0)==_name) then {_eventArgs call (_x select 1);};} forEach _eventHandlers;};
        CBA_fnc_localEvent={_this call _emit;};
        ACM_core_fnc_treatmentNative={
            _nativeCalls pushBack _this;
            _nativeArgs=_this+[objNull,"",false,((_medic getVariable ["ACME_assessment",[]]) param [0,-1])];
            if (_nativeAccepted) then {["ace_treatmentStarted",_nativeArgs] call _emit;};
            _nativeAccepted
        };
    ''' + adapt(read('registerChestAccessVestRuntime').replace('netId _medic', '"provider"')).replace(') != _patient', ') isNotEqualTo _patient')


def test_no_carrier_timer_waits_for_freeze_and_does_not_end_pose_at_launch():
    # Name retained: the old freeze requirement is deliberately replaced by actual Dr_medic4 entry.
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
        call _frame; call _frame;
        [count _nativeCalls==1,"entry did not share the single clinical timer"] call _check;
        [((_medic getVariable ["ACME_treatmentPoseState",[]]) select 2)=="AinvPknlMstpSnonWnonDr_medic4","wrong clinical animation"] call _check;
        call _ready;
        [count _nativeCalls==1 && {count _poseStops==0},"clinical launch retired its own work"] call _check;
        [["CheckBreathing"] call ACME_fnc_assessmentTime==-_configuredSpeed,"wrong breathing duration"] call _check;
        [((_medic getVariable ["ACME_treatmentPoseState",[]]) select 11)==-1,"assessment inherited carrier freeze"] call _check;
    ''')


@pytest.mark.parametrize('event',['ace_treatmentSucceded','ace_treatmentFailed'])
def test_breathing_timer_completion_or_cancel_releases_exact_hold_and_custody(event):
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        [count _poseStops==0 && {count _leases==1},"clinical work or carrier lease missing"] call _check;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
    '''+f'["{event}",_nativeArgs] call _emit;'+r'''
        [count _poseStops==1,"completion did not retire exact work"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"completion retained assessment worker"] call _check;
        [count _leases==2 && {!((_leases select 1) select 3)},"completion retained carrier custody"] call _check;
    ''')


@pytest.mark.parametrize('invalidation',[
    '_medic setVariable ["ACME_chestAccessPreflightCancel",true];',
    '_distance=9;', '_alive=false;', '_patientAlive=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_interactable=false;',
])
def test_preparation_invalidation_does_not_start_breathing_timer(invalidation):
    # Preserve old parametrized IDs while explicitly mapping the renamed preflight inputs to the current owner.
    source={'_medic setVariable ["ACME_chestAccessPreflightCancel",true];':'[_medic,1,true] call ACME_fnc_assessmentStop;',
            '_interactable=false;':'_interactive=false;'}.get(invalidation,invalidation)
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
    '''+source+(r'''
        call _ready;
        [count _nativeCalls==1 && {count _poseStops==0},"death blocked otherwise eligible assessment"] call _check;
    ''' if invalidation=='_patientAlive=false;' else r'''
        call _frame;
        [count _nativeCalls==1 && {count _poseStops==1},"invalid prep relaunched timer or retained work"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"invalid prep retained lock"] call _check;
    '''))


def test_missing_pose_bounded_timeout_aborts_without_unfrozen_timer():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
        CBA_missionTime=16; call _frame;
        [count _nativeCalls==1 && {count _poseStops==1},"missing work relaunched timer or retained sequence"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"timeout retained lock"] call _check;
    ''')


def test_second_click_cannot_launch_while_first_check_is_preparing():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
        private _second=_request call ACME_fnc_assessmentStart;
        [!_second && {count _nativeCalls==1} && {count _handlers==1},"second click replaced pending assessment"] call _check;
    ''')


def test_native_rejection_releases_frozen_episode():
    execute(setup()+r'''
        _nativeAccepted=false;
        _request call ACME_fnc_assessmentStart; call _frame;
        [count _poseStops==1 && {(_medic getVariable ["ACME_assessment",[]]) isEqualTo []},"native rejection retained work"] call _check;
        [count _removed==0 && {count _added==0} && {!((_handlers select 0) select 2)},"native rejection retained PFH or redundant inputs"] call _check;
    ''')


def test_old_completion_does_not_stop_newer_pose():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        private _oldArgs=+_nativeArgs;
        [_medic,1] call ACME_fnc_assessmentStop;
        _request call ACME_fnc_assessmentStart; call _ready;
        [_oldArgs] call ACME_fnc_assessmentFinish;
        [((_medic getVariable ["ACME_assessment",[]]) select 0)==2,"old completion stopped newer same-class assessment"] call _check;
        [count _poseStops==1,"old completion retired replacement pose"] call _check;
    ''')


def test_carrier_readiness_publishes_at_removal_while_lowering_completes_later():
    execute(patient_setup()+function('chestAccessVestAcquire')+r'''
        _vest="Vest_A"; _loadout set [4,["Vest_A",[]]];
        [_patient,objNull,"access",true,"checkbreathing"] call ACME_fnc_chestAccessVestAcquire;
        private _start=call _take; [_start] call _deliver;
        [count _waits==1,"breathing lower completion scheduled before actual removal"] call _check;
        private _lift=call _take; _serverClock=1200; [_lift] call _deliver;
        [count _commits==1 && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==1200},"removed carrier did not release assessment timer"] call _check;
        [(_patient getVariable ["ACME_chestAccess_vestBusy",""])!="" && {count _waits==1},"readiness skipped patient lowering"] call _check;
        private _lower=call _take; _serverClock=1201; [_lower] call _deliver;
        [(_patient getVariable ["ACME_chestAccess_vestBusy","bad"])=="","lowering never finished"] call _check;
    ''')


def test_breathing_provider_ack_waits_for_actual_freeze():
    execute(pose_setup()+r'''
        _medic setVariable ["ACME_chestAccess_treatment",[_patient,"checkbreathing","lease"]];
        [_medic,_patient,"start",false,"vest:access:test"] call ACME_fnc_chestAccessVestProvider;
        private _probe=_probes select 0;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        _animation="ainvpknlmstpsnonwnondnon_medic4";
        [!((_probe select 2) call (_probe select 0)),"entering medic4 declared breathing ready before hold"] call _check;
        private _id=_state select 5;
        _nativeElapsed=2.2; CBA_missionTime=11.5; [_id] call _poseTick; [_id] call _poseTick;
        [(_state select 3)==3 && {_speed==0},"real pose failed to freeze"] call _check;
        [(_probe select 2) call (_probe select 0),"frozen provider never acknowledged readiness"] call _check;
        (_probe select 2) call (_probe select 1);
        [((_medic getVariable ["ACME_chestAccessProviderReady",[]]) select 1)==_serverTime,"held readiness missing"] call _check;
    ''')


def test_deleted_patient_releases_pending_provider_and_preparation_lock():
    execute(setup()+r'''
        _request call ACME_fnc_assessmentStart;
        // Model deleted object references becoming objNull while preparation is pending.
        ((_medic getVariable ["ACME_assessment",[]]) select 1) set [1,objNull];
        call _frame;
        [count _nativeCalls==1 && {count _poseStops==1},"deleted patient leaked prepared provider"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [],"deleted patient retained pending lock"] call _check;
    ''')


def test_cancelled_front_roll_cannot_restart_carrier_removal():
    execute(patient_setup()+function('chestAccessVestAcquire')+function('chestAccessVestEvent')+r'''
        private _restores=0; ACME_fnc_chestAccessVestRestore={_restores=_restores+1;};
        _actualSide="back"; _vest="Vest_A"; _loadout set [4,["Vest_A",[]]];
        _patient setVariable ["ACME_chestAccess_leases",createHashMapFromArray [["lease",[objNull,10,"checkbreathing"]]]];
        [_patient,objNull,"access",false,"checkbreathing","prep"] call ACME_fnc_chestAccessVestAcquire;
        private _roll=call _take;
        [(_patient getVariable ["ACME_chestAccess_frontBusy",""])!="","front roll not scheduled"] call _check;
        [_patient,objNull,"lease",false,"checkbreathing"] call ACME_fnc_chestAccessVestEvent;
        [_roll] call _deliver;
        [count _waits==0 && {count _commits==0} && {_restores==1},"cancelled front roll re-entered removal"] call _check;
    ''')
