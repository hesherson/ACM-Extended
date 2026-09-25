"""Exercise the real Check Breathing preparation, timed hold, and completion gates.

Engine inventory/RTM rendering are boundaries. Clinical startup and event callbacks
run from current SQF; separate pose tests exercise the actual freeze controller.
"""
import pytest
from test_menu_death_lifecycle import adapt, execute, read
from test_historical_weapon_preflight import setup as bridge_setup
from test_chestseal_preparation_progress import setup as patient_setup, function
from test_chest_entry_timing import setup as pose_setup


def setup():
    return bridge_setup().replace('serverTime', '_clock').replace('_m distance _p', '_distance') + r'''
        private _stops=[]; private _prep=[]; private _leases=[]; private _starts=[];
        private _patientReady=true; private _heldAtStart=[]; private _eventHandlers=[];
        _weaponNow=""; _animNowFixture="AmovPknlMstpSnonWnonDnon"; _stanceNow="CROUCH";
        ACME_chestAccess_classes=["checkbreathing","cpr"];
        ace_medical_treatment_fnc_canTreat={_permitted};
        ACME_fnc_chestAccessPreparing={_prep pushBack _this;};
        CBA_fnc_addEventHandler={_eventHandlers pushBack _this;};
        ACME_fnc_chestAccessVestEvent={
            params ["_p","_m","_id","_start"];
            _leases pushBack _this;
            if (_start) then {
                _p setVariable ["ACME_chestAccess_readyLease",_id];
                _p setVariable ["ACME_chestAccess_readyServer",[-1,_clock] select _patientReady];
            };
        };
        ACME_fnc_chestAccessVestProvider={
            params ["_m","_p","_op",["_handoff",false],["_token",""]];
            if (_op=="start") then {
                _starts pushBack _this;
                _m setVariable ["ACME_chestAccessProvider",[_p,7,_token]];
                _m setVariable ["ACME_treatmentPoseState",[7,"chestAccess","medic4",1]];
            } else {
                _stops pushBack _this;
                _m setVariable ["ACME_chestAccessProvider",[]];
                _m setVariable ["ACME_treatmentPoseState",[]];
            };
            7
        };
        ACM_core_fnc_treatmentNative={
            _nativeCalls pushBack _this;
            _heldAtStart pushBack [(_medic getVariable ["ACME_treatmentPoseState",[]]) param [3,-1],
                _medic getVariable ["ACME_suppressNativeTreatmentAnim",false]];
            _nativeAccepted
        };
        private _freeze={(_medic getVariable ["ACME_treatmentPoseState",[]]) set [3,3];};
        private _emit={params ["_name","_args"]; {if ((_x select 0)==_name) then {_args call (_x select 1);};} forEach _eventHandlers;};
    ''' + adapt(read('registerChestAccessVestRuntime')).replace(') != _patient', ') isNotEqualTo _patient')


def test_no_carrier_timer_waits_for_freeze_and_does_not_end_pose_at_launch():
    execute(setup()+r'''
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        [count _nativeCalls==0 && {count _timers==1},"no-carrier timer skipped preparation"] call _check;
        [!(0 call _condition) && {count _starts==1},"no-carrier pose was not requested"] call _check;
        [!(0 call _condition) && {count _starts==1},"pending pose was requested repeatedly"] call _check;
        call _freeze; 0 call _deliver;
        [_heldAtStart isEqualTo [[3,true]] && {count _stops==0},"native launch thawed/replaced held animation"] call _check;
        [!(_medic getVariable ["ACME_suppressNativeTreatmentAnim",true]),"suppression leaked into other treatments"] call _check;
        [!(_medic getVariable ["ACME_chestAccessPreflightActive",true]),"preflight lock leaked into timer"] call _check;
    ''')


@pytest.mark.parametrize('event',['ace_treatmentSucceded','ace_treatmentFailed'])
def test_breathing_timer_completion_or_cancel_releases_exact_hold_and_custody(event):
    execute(setup()+r'''
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        0 call _condition; call _freeze; 0 call _deliver;
        [count _stops==0,"hold ended before timer completion"] call _check;
    '''+f'["{event}",[_medic,_patient,"Head","CheckBreathing"]] call _emit;'+r'''
        [count _stops==1 && {!((_stops select 0) select 3)},"timer did not exit assessment hold"] call _check;
        [(_medic getVariable ["ACME_checkBreathingPose",[]]) isEqualTo [],"timer retained hold ownership"] call _check;
        [count _leases==2 && {!((_leases select 1) select 3)},"timer failed to release carrier custody"] call _check;
    ''')


@pytest.mark.parametrize('invalidation',[
    '_medic setVariable ["ACME_chestAccessPreflightCancel",true];',
    '_distance=9;', '_alive=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_interactable=false;',
])
def test_preparation_invalidation_does_not_start_breathing_timer(invalidation):
    execute(setup()+r'''
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        0 call _condition;
    '''+invalidation+r'''
        0 call _deliver;
        [count _nativeCalls==0 && {count _stops==1},"cancelled preparation started or retained hold"] call _check;
        [!(_medic getVariable ["ACME_chestAccessPreflightActive",true]),"cancel retained preparation lock"] call _check;
    ''')


def test_missing_pose_bounded_timeout_aborts_without_unfrozen_timer():
    execute(setup()+r'''
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        0 call _condition; 0 call _timeout;
        [count _nativeCalls==0 && {count _stops==1},"failed pose timed out into an unheld assessment"] call _check;
        [!(_medic getVariable ["ACME_chestAccessPreflightActive",true]),"timeout retained preflight lock"] call _check;
    ''')


def test_second_click_cannot_launch_while_first_check_is_preparing():
    execute(setup()+r'''
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        private _second=[_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        [!_second && {count _nativeCalls==0} && {count _timers==1},"second click bypassed pending chest lease"] call _check;
    ''')


def test_native_rejection_releases_frozen_episode():
    execute(setup()+r'''
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        0 call _condition; call _freeze; _nativeAccepted=false; 0 call _deliver;
        [count _stops==1 && {(_medic getVariable ["ACME_checkBreathingPose",[]]) isEqualTo []},"native rejection retained frozen pose"] call _check;
    ''')


def test_old_completion_does_not_stop_newer_pose():
    execute(setup()+r'''
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        0 call _condition; call _freeze; 0 call _deliver;
        _medic setVariable ["ACME_chestAccessProvider",[_patient,8,"new"]];
        _medic setVariable ["ACME_treatmentPoseState",[8,"chestAccess","medic4",3]];
        ["ace_treatmentFailed",[_medic,_patient,"Head","CheckBreathing"]] call _emit;
        [count _stops==0,"old completion stopped newer provider episode"] call _check;
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
        [_medic,_patient,"Head","CheckBreathing"] call ace_medical_treatment_fnc_treatment;
        0 call _condition;
        // Model Arma's deleted-object references becoming objNull at every object boundary.
        ((_timers select 0) select 2) set [1,objNull];
        (_medic getVariable ["ACME_chestAccessProvider",[]]) set [0,objNull];
        (_medic getVariable ["ACME_chestAccess_treatment",[]]) set [0,objNull];
        0 call _deliver;
        [count _nativeCalls==0 && {count _stops==1},"deleted patient leaked frozen preparation"] call _check;
        [!(_medic getVariable ["ACME_chestAccessPreflightActive",true]),"deleted patient retained prep lock"] call _check;
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
