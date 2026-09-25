"""Run patient preparation with delayed owner callbacks in SQF-VM.

Actual begin/end/acquire scheduling and lease checks run. Inventory removal and
visual prop creation are one recorded engine boundary; animations are recorded
requests, not rendered Arma RTMs. Mission and server clocks remain independent.
"""
import re
import pytest
from test_menu_death_lifecycle import execute
from test_historical_chest_workspace import setup as workspace_setup, code
from test_bounded_head_completion import setup as head_setup, begin as head_begin


def function(name):
    text = code(name, server_clock='_serverClock')
    text = re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', text)
    if name == 'chestAccessVestAcquire':
        start = text.index('private _commitRemoval = {')
        end = text.index('// Animation is allowed only', start)
        text = text[:start] + r'''
            private _commitRemoval = {
                params ["_p","_ctx","_savedVar"];
                _commits pushBack _serverClock;
                _p setVariable [_savedVar,["Vest_A",[]]];
                _vest=""; _loadout set [4,[]]; true
            };
        ''' + text[end:]
    return 'ACME_fnc_' + name + '={' + text + '};\n'


def setup():
    return workspace_setup() + r'''
        private _serverClock=1000; private _commits=[]; private _pins=[];
        _actualSide="front"; _animation="ACM_LyingState";
        _patient setVariable ["ACE_isUnconscious",true];
        ACME_fnc_headElevPinPose={_pins pushBack _this;};
        private _take={private _job=_waits deleteAt 0; _job};
        private _ready={params ["_job"]; (_job select 2) call (_job select 4)};
    ''' + function('chestSealPatientBegin') + function('chestSealPatientEnd')


def worn_acquire(context='chestseal'):
    return function('chestAccessVestAcquire') + r'''
        _vest="Vest_A"; _loadout set [4,["Vest_A",[]]];
        _patient setVariable ["ACME_CS_PreparationToken","viewer"];
        _patient setVariable ["ACME_CS_ProcedureTokens",["viewer"]];
    ''' + f'[_patient,objNull,"{context}",true] call ACME_fnc_chestAccessVestAcquire;'


def test_late_lift_does_not_publish_future_readiness_or_finish_on_same_frame():
    execute(setup() + worn_acquire() + r'''
        private _start=call _take; [_start] call _deliver;
        [count _waits==1,"chestseal scheduled finish independently of removal"] call _check;
        [(_patient getVariable ["ACME_CS_vestReadyServer",0]) == -1,"future estimate published before removal"] call _check;
        private _lift=call _take;
        CBA_missionTime=80; _serverClock=1200;
        [_lift] call _deliver;
        [count _commits==1 && {count _waits==1},"late lift failed to schedule actual lower interval"] call _check;
        [(_patient getVariable ["ACME_CS_vestReadyServer",0]) == -1,"late removal declared unfinished lower ready"] call _check;
        private _lower=call _take;
        [abs ((_lower select 3)-(1.4/1.5))<0.0001,"lower duration was measured from stale lift start"] call _check;
        _serverClock=1205; [_lower] call _deliver;
        [(_patient getVariable ["ACME_CS_vestReadyServer",0])==1205,"ready clock is not actual server completion"] call _check;
        [(_patient getVariable ["ACME_CS_vestBusy","bad"])=="","completion retained transaction"] call _check;
    ''')


def test_generic_access_callback_intervals_follow_shared_rate():
    execute(setup() + worn_acquire('access') + r'''
        private _start=call _take; [_start] call _deliver;
        private _times=_waits apply {_x select 3};
        [abs ((_times select 0)-(1.2/1.5+0.04))<0.0001 && {abs ((_times select 1)-(2.6/1.5+0.04))<0.0001} && {abs ((_times select 2)-(2.6/1.5+0.04+0.25))<0.0001},"generic access choreography timing changed"] call _check;
        call _drain;
        [count _commits==1 && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==1000},"generic access lost completion"] call _check;
    ''')


def test_saved_carrier_does_not_bypass_inflight_body_transaction():
    execute(setup() + worn_acquire() + r'''
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[]]];
        _patient setVariable ["ACME_CS_vestReadyServer",-1];
        [_patient,objNull,"chestseal",true] call ACME_fnc_chestAccessVestAcquire;
        [(_patient getVariable ["ACME_CS_vestReadyServer",0])==-1,"custody shortcut bypassed unfinished body work"] call _check;
        [count _waits==1,"join started duplicate preparation"] call _check;
    ''')


def test_denied_patient_lift_waits_foreign_lease_then_resumes():
    execute(setup() + worn_acquire() + r'''
        _leaseAllowed=false;
        private _foreign=["other","other-procedure","provider",8,1100];
        _patient setVariable ["ACME_patientAnimLock",_foreign];
        private _start=call _take; [_start] call _deliver;
        [count _pins==0 && {count _events==0} && {count _commits==0},"denied lift still changed body"] call _check;
        private _leaseWait=call _take;
        [!([_leaseWait] call _ready),"valid foreign lease treated as retired"] call _check;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo _foreign,"valid lock overwritten"] call _check;
        _serverClock=1101; _leaseAllowed=true; [_leaseWait] call _deliver;
        [count _pins==1 && {count _waits==1},"retired lease never resumed patient preparation"] call _check;
    ''')


def test_intervening_lease_blocks_lower_pin_and_final_rest_until_release():
    execute(setup() + worn_acquire() + r'''
        private _start=call _take; [_start] call _deliver;
        private _lift=call _take;
        _leaseAllowed=false; _pins=[]; _events=[];
        private _foreign=["other","other-procedure","provider",8,1100];
        _patient setVariable ["ACME_patientAnimLock",_foreign];
        [_lift] call _deliver;
        [count _pins==0,"rejected Release still pinned foreign body owner"] call _check;
        private _lower=call _take; [_lower] call _deliver;
        [count _events==0 && {(_patient getVariable ["ACME_CS_vestReadyServer",0])==-1},"foreign lease did not block forced rest/readiness"] call _check;
        private _wait=call _take; [!([_wait] call _ready),"foreign lease bypassed"] call _check;
        _serverClock=1101; [_wait] call _deliver;
        [(_patient getVariable ["ACME_CS_vestReadyServer",0])==1101,"released foreign lease left preparation stranded"] call _check;
    ''')


def test_owner_preparation_survives_long_delay_and_first_viewer_departure():
    execute(setup() + r'''
        [_patient,"first",_medic] call ACME_fnc_chestSealPatientBegin;
        private _prep=call _take;
        [(_prep select 3)==-1,"owner readiness has a fixed abort deadline"] call _check;
        [_patient,"second",_medic] call ACME_fnc_chestSealPatientBegin;
        [_patient,"first",_medic] call ACME_fnc_chestSealPatientEnd;
        CBA_missionTime=100; _serverClock=1300;
        [!([_prep] call _ready),"late unfinished preparation became ready"] call _check;
        [(_patient getVariable ["ACME_CS_PreparationToken",""])=="first","first viewer departure invalidated shared preparation"] call _check;
        _patient setVariable ["ACME_CS_vestReadyServer",1299];
        [_prep] call _deliver;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==1300,"late completed preparation lost workspace readiness"] call _check;
    ''')


def test_old_preparation_cannot_publish_readiness_for_reopened_workspace():
    execute(setup() + r'''
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientBegin;
        private _old=call _take;
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientEnd;
        [_patient,"new",_medic] call ACME_fnc_chestSealPatientBegin;
        _patient setVariable ["ACME_CS_ProcedureReadyAt",222];
        _patient setVariable ["ACME_CS_vestReadyServer",999];
        private _pending=+_waits; [_old] call _deliver;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==222,"old preparation overwrote new readiness"] call _check;
        [_waits isEqualTo _pending,"old preparation started work in new generation"] call _check;
    ''')


def test_normalization_retries_only_after_foreign_lease_and_finishes_actual_roll():
    execute(setup() + r'''
        _actualSide="back";
        [_patient,"viewer",_medic] call ACME_fnc_chestSealPatientBegin;
        private _prep=call _take;
        _patient setVariable ["ACME_CS_vestReadyServer",1000];
        _patient setVariable ["ACME_patientAnimLock",["other","procedure","provider",8,1100]];
        [_prep] call _deliver; private _roll=call _take;
        CBA_missionTime=40;
        [!([_roll] call _ready) && {count _rolls==1},"valid foreign lease retried/seized roll"] call _check;
        _serverClock=1101;
        [!([_roll] call _ready) && {count _rolls==2},"released lease did not retry normalization"] call _check;
        [!([_roll] call _ready) && {count _rolls==2},"normalization retry has no cadence"] call _check;
        _actualSide="front"; _patient setVariable ["ACME_CS_rollToken","still-lowering"];
        [!([_roll] call _ready),"nominal side bypassed active roll completion"] call _check;
        _patient setVariable ["ACME_CS_rollToken",""]; [_roll] call _deliver;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==1101,"actual roll completion did not publish ready"] call _check;
    ''')


@pytest.mark.parametrize('worn,animate',[(False,False),(True,False),(True,True)])
def test_suspension_actual_completion_gates_all_chestseal_carrier_paths(worn,animate):
    gear = '_vest="Vest_A"; _loadout set [4,["Vest_A",[]]];' if worn else ''
    execute(setup() + function('chestAccessVestAcquire') + gear + f'_blocked={str(not animate).lower()};' + r'''
        _patient setVariable ["ACME_CS_PreparationToken","viewer"];
        _patient setVariable ["ACME_CS_ProcedureTokens",["viewer"]];
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_Suspended",true];
        _patient setVariable ["ACME_headElev_suspendPending","suspension"];
        _patient setVariable ["ACME_headElev_suspendReadyAt",11];
        [_patient,objNull,"chestseal",true] call ACME_fnc_chestAccessVestAcquire;
        private _pending=call _take;
        CBA_missionTime=80; _serverClock=1200;
        [!([_pending] call _ready),"late suspension callback bypassed by nominal clock"] call _check;
        [count _commits==0 && {count _pins==0},"carrier work preceded actual suspension finish"] call _check;
        _patient setVariable ["ACME_headElev_suspendPending",""];
        [_pending] call _deliver;
    ''' + ('call _drain;' if animate else '') + r'''
        [(_patient getVariable ["ACME_CS_vestReadyServer",0])==1200,"actual suspension finish stranded readiness"] call _check;
    ''')


def test_cancel_invalidates_delayed_lift_and_preserves_competing_body_lock():
    execute(setup() + worn_acquire() + r'''
        _patient setVariable ["ACME_CS_ProcedureActive",true];
        _patient setVariable ["ACME_CS_ProcedureGeneration",1];
        _patient setVariable ["ACME_CS_PreProcedureState",["front",false,false,false,""]];
        private _start=call _take; [_start] call _deliver;
        private _oldLift=call _take;
        private _foreign=["other","other-procedure","provider",8,1100];
        _patient setVariable ["ACME_patientAnimLock",_foreign];
        [_patient,"viewer",_medic] call ACME_fnc_chestSealPatientEnd;
        _events=[]; _pins=[]; _rolls=[];
        [_patient,"new",_medic] call ACME_fnc_chestSealPatientBegin;
        private _pending=+_waits; [_oldLift] call _deliver;
        [count _commits==0 && {count _events==0} && {count _pins==0} && {count _rolls==0},"old lift changed cancelled/reopened workspace"] call _check;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo _foreign,"cancel cleared competing valid lock"] call _check;
        [_waits isEqualTo _pending,"cancelled callback resumed work"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;', '_patientAlive=false;',
    '_patient setVariable ["ACME_headElev_poseToken","replacement"];',
    '_patient setVariable ["ACME_headElev_Suspended",false];',
])
def test_suspension_aborted_completion_retires_only_its_own_marker(change):
    execute(head_setup() + head_begin('suspend') + change + r'''
        [_pending] call _deliver;
        [(_patient getVariable ["ACME_headElev_suspendPending","bad"])=="","aborted suspension retained pending marker"] call _check;
    ''')


def test_old_suspension_callback_cannot_clear_new_suspension_in_same_placement():
    execute(head_setup() + head_begin('suspend') + r'''
        _patient setVariable ["ACME_headElev_Suspended",false];
        [_patient] call ACME_fnc_headElevSuspend;
        private _newMarker=_patient getVariable ["ACME_headElev_suspendPending",""];
        private _newJob=_waits select 0; _waits=[]; _collisions=[]; _animRequests=[];
        [_pending] call _deliver;
        [(_patient getVariable ["ACME_headElev_suspendPending",""])==_newMarker,"old callback cleared replacement suspension"] call _check;
        [count _collisions==0 && {count _animRequests==0},"old suspension moved new body work"] call _check;
        [_newJob] call _deliver;
        [(_patient getVariable ["ACME_headElev_suspendPending","bad"])=="","actual new completion retained marker"] call _check;
    ''')


@pytest.mark.parametrize('side',['front','back'])
def test_existing_roll_must_actually_retire_before_carrier_choreography(side):
    execute(setup() + function('chestAccessVestAcquire') + f'_actualSide="{side}";' + r'''
        _vest="Vest_A"; _loadout set [4,["Vest_A",[]]];
        _patient setVariable ["ACME_CS_PreparationToken","viewer"];
        _patient setVariable ["ACME_CS_ProcedureTokens",["viewer"]];
        _patient setVariable ["ACME_CS_rollToken","prior-roll"];
        [_patient,objNull,"chestseal",false] call ACME_fnc_chestAccessVestAcquire;
        [count _rolls==0 && {count _pins==0} && {count _waits==1},"existing roll replaced or carrier started early"] call _check;
        private _front=call _take;
        CBA_missionTime=80; _serverClock=1200;
        [!([_front] call _ready),"clock replaced actual prior-roll completion"] call _check;
        _patient setVariable ["ACME_CS_rollToken",""]; _actualSide="front";
        [_front] call _deliver;
        private _start=call _take; [_start] call _deliver;
        [count _pins==1 && {count _rolls==0},"completed prior roll did not hand off once to carrier"] call _check;
    ''')


def test_no_vest_suspension_passes_back_facing_body_to_normalization_retry():
    execute(setup() + function('chestAccessVestAcquire') + r'''
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_Suspended",true];
        _patient setVariable ["ACME_headElev_suspendPending","suspension"];
        _patient setVariable ["ACME_headElev_suspendReadyAt",11];
        [_patient,"viewer",_medic] call ACME_fnc_chestSealPatientBegin;
        private _suspend=call _take; private _prep=call _take;
        CBA_missionTime=80; _serverClock=1200; _actualSide="back";
        _patient setVariable ["ACME_headElev_suspendPending",""];
        _patient setVariable ["ACME_patientAnimLock",["other","procedure","provider",8,1300]];
        [_suspend] call _deliver;
        [_prep] call _deliver;
        [count _rolls==1 && {count _waits==1},"back-facing suspension stranded before normalization retry"] call _check;
        private _normalize=call _take;
        [!([_normalize] call _ready),"foreign lease bypassed by no-vest handoff"] call _check;
        _serverClock=1301; CBA_missionTime=81;
        [!([_normalize] call _ready) && {count _rolls==2},"no-vest body never retried after foreign lease"] call _check;
        _actualSide="front"; [_normalize] call _deliver;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==1301,"normalized no-vest body failed readiness"] call _check;
    ''')
