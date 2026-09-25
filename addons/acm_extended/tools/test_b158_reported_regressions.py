"""Execute the reported pause/swap and provider-before-patient order failures.

Animation state, UI metrics and network delivery are explicit fixtures; this does
not replace a live Arma/Animate playback check.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_bounded_head_provider_sequence import setup as provider_setup, begin, FIRST, REST
from test_bounded_head_completion import setup as patient_setup, code as patient_code
from test_bounded_head_start_contracts import start_setup
from test_historical_weapon_preflight import setup as treatment_setup
from test_historical_chest_workspace import setup as chest_setup


def maneuver_setup():
    return r'''
        private _cprReserved=false;private _bvmReserved=false;
        ACM_core_fnc_cprActive={false};ACM_core_fnc_bvmActive={false};
        ACM_circulation_fnc_cprSessionValid={_cprReserved};
        ACM_breathing_fnc_bvmSessionValid={_bvmReserved};
    '''+'ACME_fnc_chestAccessManeuverActive={'+adapt(read('chestAccessManeuverActive'))+'};'


def watcher_setup():
    s=read('registerChestAccessVestRuntime').replace('serverTime','_serverClock').replace('!= _patient','isNotEqualTo _patient')
    return maneuver_setup()+r'''
        private _serverClock=1000;private _listeners=[];private _conditions=[];private _leases=[];
        CBA_fnc_addEventHandler={_listeners pushBack _this;};
        CBA_fnc_waitUntilAndExecute={_conditions pushBack _this;};
        ACME_fnc_chestAccessVestEvent={_leases pushBack _this;};
    '''+adapt(s)+r'''
        private _fire={params ["_event","_class"];{if ((_x select 0)==_event) then {[_medic,_patient,"body",_class] call (_x select 1);};} forEach _listeners;};
        _medic setVariable ["ACME_chestAccess_treatment",[_patient,"cpr","stable-lease"]];
        _cprReserved=true;
        ["ace_treatmentSucceded","CPR"] call _fire;
        private _watch=_conditions select 0;
        private _finished={(_watch select 2) call (_watch select 0)};
    '''


def test_paused_cpr_bvm_round_trips_preserve_same_lease_until_real_stop():
    execute(watcher_setup()+r'''
        [!(call _finished),"paused CPR restored carrier before swap became available"] call _check;
        for "_i" from 1 to 6 do {
            CBA_missionTime=1000*_i;
            _medic setVariable ["ACME_chestAccessManeuverHandoff",[_patient,CBA_missionTime+1]];
            _cprReserved=false;
            [!(call _finished),"carrier restored in CPR-to-BVM gap"] call _check;
            _bvmReserved=true;
            _medic setVariable ["ACME_chestAccessManeuverHandoff",[]];
            ["ace_treatmentStarted","UseBVM"] call _fire;
            [!(call _finished),"paused BVM lost open chest"] call _check;
            ["ace_treatmentFailed","UseBVM"] call _fire;
            [count _leases==0,"failure handler escaped only inner block and released watched lease"] call _check;
            _medic setVariable ["ACME_chestAccessManeuverHandoff",[_patient,CBA_missionTime+1]];
            _bvmReserved=false;
            [!(call _finished),"carrier restored in BVM-to-CPR gap"] call _check;
            _cprReserved=true;
            _medic setVariable ["ACME_chestAccessManeuverHandoff",[]];
            ["ace_treatmentStarted","CPR"] call _fire;
            [!(call _finished),"CPR entry lost carrier custody"] call _check;
            [((_medic getVariable ["ACME_chestAccess_treatment",[]]) select 2)=="stable-lease","swap replaced lease"] call _check;
        };
        [count _watch==3,"arbitrary watcher timeout can restore carrier during long session"] call _check;
        _cprReserved=false;
        [call _finished,"stopped session failed to release"] call _check;
        (_watch select 2) call (_watch select 1);
        [count _leases==1 && {!((_leases select 0) select 3)},"final stop did not release exactly once"] call _check;
    ''')


@pytest.mark.parametrize('role',['cpr','bvm'])
def test_patient_owner_refuses_carrier_return_while_maneuver_is_paused(role):
    execute(chest_setup()+maneuver_setup()+f'_{role}Reserved=true;'+r'''
        _actualSide="front";
        _patient setVariable ["ACME_chestAccess_vestLoadout",["plate-carrier",[]]];
        private _restored=[_patient,false,_medic,"access",true] call ACME_fnc_chestAccessVestRestore;
        [!_restored && {count _loadouts==0} && {count _animRequests==0},"pause started carrier restoration"] call _check;
        [count _waits==1,"owner did not defer until session release"] call _check;
    ''')


@pytest.mark.parametrize('mode',['elevate','lower'])
def test_patient_move_is_sent_once_only_after_provider_reach_is_observed(mode):
    execute(provider_setup()+f'''
        [_medic,"{mode}",_patient,"pose-1"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0;_events=[];
        [_job] call _tick;
        [count _events==0,"patient moved during weapon preparation"] call _check;
        CBA_missionTime=10.2;[_job] call _tick;
        _anim=toLower "{REST}";[_job] call _tick;
        [count _events==0,"patient moved when reach was only queued"] call _check;
        _anim=toLower "{FIRST}";
        for "_i" from 0 to 3 do {{[_job] call _tick;}};
        [count _events==1,"patient move missing/repeated"] call _check;
        [(_events select 0) isEqualTo [_patient,"headElevMedicReady",[_medic,_patient,"{mode}","pose-1"]],"wrong placement notified"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACME_headElev_poseToken","new-placement"];',
    '_patient setVariable ["ACME_headElevated",false];',
    '_patient setVariable ["ACME_headElev_Suspended",true];',
])
def test_delayed_provider_ready_cannot_lift_retired_or_suspended_patient(change):
    execute(patient_setup()+'ACME_fnc_headElevMedicReady={'+patient_code('headElevMedicReady')+'};'+r'''
        _patient setVariable ["ACME_headElev_pendingLift",[_medic,"placement:one"]];
    '''+change+r'''
        [_medic,_patient,"elevate","placement:one"] call ACME_fnc_headElevMedicReady;
        [count _moves==0 && {count _pins==0},"late reach moved newer patient state"] call _check;
    ''')


def test_explicit_lower_waits_for_reach_then_starts_release_without_restarting_provider():
    execute(patient_setup()+r'''
        ACME_fnc_headElevMedicSeq={_provider pushBack _this;};
    '''+'ACME_fnc_headElevMedicReady={'+patient_code('headElevMedicReady')+'};'+r'''
        [_medic,_patient] call ACME_fnc_headElevateStop;
        [count _provider==1 && {count _moves==0} && {count _restores==0},"patient lowered before provider reached"] call _check;
        [_patient getVariable ["ACME_headElevated",false],"placement retired before provider reached"] call _check;
        [_medic,_patient,"lower","placement:one"] call ACME_fnc_headElevMedicReady;
        [count _provider==1 && {count _moves==1},"lower replayed provider or skipped patient release"] call _check;
        [!(_patient getVariable ["ACME_headElevated",true]),"lower did not finish logical placement"] call _check;
    ''')


def test_cancel_before_reach_restores_pending_lift_without_fake_lower_animation():
    execute(patient_setup()+'ACME_fnc_headElevMedicReady={'+patient_code('headElevMedicReady')+'};'+r'''
        _patient setVariable ["ACME_headElev_pendingLift",[_medic,"placement:one"]];
        _patient setVariable ["ACME_headElev_visualActive",false];
        [_medic,_patient,"elevate","placement:one",true] call ACME_fnc_headElevMedicReady;
        [!(_patient getVariable ["ACME_headElevated",true]),"cancel stranded pending elevation"] call _check;
        [count _moves==0 && {count _provider==0},"cancel played lowering for a patient never lifted"] call _check;
    ''')


def test_initial_supported_lift_waits_for_provider_ready_and_ignores_duplicate_packet():
    execute(start_setup()+r'''
        ACME_fnc_headElevMedicStart={_starts pushBack _this;};
    '''+'ACME_fnc_headElevMedicReady={'+patient_code('headElevMedicReady')+'};'+r'''
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        [count _starts==1 && {count _tilts==0},"patient lifted before provider reach"] call _check;
        private _token=_patient getVariable ["ACME_headElev_poseToken",""];
        [_medic,_patient,"elevate",_token] call ACME_fnc_headElevMedicReady;
        [_medic,_patient,"elevate",_token] call ACME_fnc_headElevMedicReady;
        [count _tilts==1,"reach packet did not produce exactly one lift"] call _check;
    ''')


def test_provider_leaving_before_ready_cancels_pending_lift_without_moving_patient():
    execute(patient_setup()+'ACME_fnc_headElevMedicReady={'+patient_code('headElevMedicReady')+'};'+r'''
        _patient setVariable ["ACME_headElev_pendingLift",[_medic,"placement:one"]];
        _patient setVariable ["ACME_headElev_visualActive",false];
        _distance=10;
        [_medic,_patient,"elevate","placement:one"] call ACME_fnc_headElevMedicReady;
        [count _moves==0 && {!(_patient getVariable ["ACME_headElevated",true])},"late packet lifted abandoned patient"] call _check;
    ''')


def test_new_head_action_retires_old_finite_rate_before_sequence_starts():
    execute(treatment_setup()+r'''
        _categoryFixture="examine";
        _medic setVariable ["ACME_nativeTreatmentRate",[4,_patient,"head","InsertOPA",7]];
        [_medic,_patient,"head","ACME_ElevateHead"] call ace_medical_treatment_fnc_treatment;
        [count _nativeCalls==1,"head action did not reach native treatment"] call _check;
        [(_medic getVariable ["ACME_nativeTreatmentRate",[]]) isEqualTo [],"stale treatment rate would cancel head sequence"] call _check;
    ''')
