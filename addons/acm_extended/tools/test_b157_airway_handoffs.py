"""Run HTCL/Semi-Fowler ownership regressions; UI, RTM and transport are engine boundaries."""
import pytest

from test_menu_death_lifecycle import ROOT, F, adapt, execute, hold_setup
from test_historical_weapon_preflight import setup as treatment_setup
from test_bounded_head_provider_sequence import setup as sequence_setup, begin
from test_bounded_head_provider_consciousness import setup as cancel_setup


def treatment_events():
    source = (F / 'fn_registerHeadElevationTreatmentRuntime.sqf').read_text()
    # HTCL returns before reading these values. The stale flag fixture also verifies
    # the runtime exclusion if another config patch inherits ACM_rollToBack again.
    source = source.replace('getNumber (_cfg >> "ACM_rollToBack")', '1')
    source = source.replace('!= _patient', 'isNotEqualTo _patient')
    return r'''
        private _listeners = []; private _postureCalls = [];
        CBA_fnc_addEventHandler = {_listeners pushBack _this;};
        ACME_fnc_headElevateStop = {_postureCalls pushBack _this;};
        ACME_fnc_headElevTreatmentEvent = {_postureCalls pushBack _this;};
        private _fire = {
            params ["_name", "_args"];
            {if ((_x select 0) == _name) then {_args call (_x select 1);};} forEach _listeners;
        };
    ''' + adapt(source)


@pytest.mark.parametrize('manual', [False, True])
def test_htcl_does_not_lower_supported_or_other_provider_manual_semifowler(manual):
    execute(treatment_events() + hold_setup() + f'_patient setVariable ["ACME_headElev_manualUnsupported",{str(manual).lower()}];' + r'''
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_hold",[missionNamespace,"support"]];
        ["ace_treatmentStarted",[_medic,_patient,"head","BeginHeadTiltChinLift"]] call _fire;
        [_medic,_patient] call _start;
        ["ace_treatmentSucceded",[_medic,_patient,"head","BeginHeadTiltChinLift"]] call _fire;
        call _tick;
        [ACM_core_ContinuousAction_Active && {_patient getVariable ["ACM_airway_HeadTilt_State",false]},"HTCL did not remain active"] call _check;
        [count _postureCalls==0,"HTCL lowered or leased the torso"] call _check;
        [(_medic getVariable ["ACME_headElev_treatment",[]]) isEqualTo [],"HTCL stranded a suspension lease"] call _check;
        ACM_core_ContinuousAction_Active=false; call _tick;
        [!(_patient getVariable ["ACM_airway_HeadTilt_State",true]),"cancel stranded head tilt"] call _check;
        [_patient getVariable ["ACME_headElevated",false],"cancel changed supported posture"] call _check;
        [(_patient getVariable ["ACME_headElev_hold",[]]) isEqualTo [missionNamespace,"support"],"HTCL stole another provider's support"] call _check;
    ''')


def test_busy_provider_rejected_before_native_treatment_mutates_semifowler():
    execute(treatment_setup() + r'''
        ACM_core_ContinuousAction_Active=true;
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_hold",[_medic,"support"]];
        private _accepted=[_medic,_patient,"head","BeginHeadTiltChinLift"] call ace_medical_treatment_fnc_treatment;
        [!_accepted && {count _nativeCalls==0} && {count _timers==0},"busy launcher mutated patient through native treatment"] call _check;
        [ACM_core_ContinuousAction_Active && {_patient getVariable ["ACME_headElevated",false]},"rejection canceled current support"] call _check;
    ''')


@pytest.mark.parametrize('invalid', [
    'ACM_core_ContinuousAction_Active=true;',
    '_unconscious=true;',
    '_patient setVariable ["ACM_airway_AirwayItem_Oral","SGA"];',
    '_patient setVariable ["ACME_ETT_Inserted",true];',
    '_patient setVariable ["ACM_airway_SurgicalAirway_InProgress",true];',
    '_patient setVariable ["ACM_airway_RecoveryPosition_State",true];',
])
def test_invalid_htcl_callback_never_installs_locks_or_handlers(invalid):
    execute(hold_setup() + invalid + r'''
        [_medic,_patient] call _start;
        [count _keys==0 && {count _handlers==0},"rejected callback installed controller"] call _check;
        [!(_patient getVariable ["ACM_airway_HeadTilt_State",false]),"rejected callback reserved airway"] call _check;
    ''')


@pytest.mark.parametrize('takeover', [
    'ACM_core_ContinuousAction_Active=true; _medic setVariable ["ACM_core_ContinuousAction_Session",[_patient,8]];',
    '_medic setVariable ["ACME_nativeTreatmentRate",[1,_patient,"head","InsertOPA",8]];',
    '_medic setVariable ["ACME_treatmentPoseState",[8,"airway"]];',
    '_medic setVariable ["ACME_chestAccessPreflightActive",true];',
])
def test_pending_head_position_sequence_yields_without_resetting_new_airway_pose(takeover):
    execute(sequence_setup() + begin() + takeover + r'''
        _moves=[]; _stances=[]; _events=[]; _waits=[]; _testAnimationSpeed=0;
        [_job] call _tick;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"old head sequence stayed active"] call _check;
        [count _moves==0 && {count _stances==0} && {count _events==0} && {count _waits==0},"old sequence touched new owner's pose"] call _check;
        [_testAnimationSpeed==0 && {_removed isEqualTo [73]},"old sequence reset new freeze or leaked PFH"] call _check;
    ''')


def test_head_sequence_cancel_retires_without_replacing_a_new_treatment():
    execute(cancel_setup() + begin() + r'''
        _stanceOwned=true; _moves=[]; _stances=[]; _events=[]; _waits=[]; _testAnimationSpeed=0;
        call ACME_fnc_headElevateCancelSeq;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"cancel left old sequence active"] call _check;
        [count _moves==0 && {count _stances==0} && {count _events==0} && {count _waits==0} && {_testAnimationSpeed==0},"cancel overwrote newer treatment"] call _check;
        call _patientUntouched;
    ''')


@pytest.mark.parametrize('cancel', [False, True])
def test_head_cleanup_keeps_new_treatment_direct_pressure_exclusion(cancel):
    execute(cancel_setup() + begin() + r'''
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","acme_elevatehead"];
        _medic setVariable ["ACME_DP_Paused",true];
        // The newly accepted airway treatment owns Busy but did not replace the old head pause label.
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        _medic setVariable ["ACME_nativeTreatmentRate",[1,_patient,"head","InsertOPA",8]];
        _stanceOwned=true;
    ''' + ('call ACME_fnc_headElevateCancelSeq;' if cancel else '[_job] call _tick;') + r'''
        [_medic getVariable ["ACME_DP_TreatmentBusy",false],"old head cleanup released newer treatment DP exclusion"] call _check;
        [!(_medic getVariable ["ACME_DP_Paused",true]) && {(_medic getVariable ["ACME_DP_PauseTreatmentClass","bad"])==""},"old head pause was not retired"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"old head sequence remained active"] call _check;
    ''')


def test_htcl_config_and_roll_listener_do_not_request_a_flattening_animation():
    config = (ROOT / 'addons/airway/ACE_Medical_Treatment_Actions.hpp').read_text()
    htcl = config.split('class BeginHeadTiltChinLift:', 1)[1].split('class RecoveryPosition:', 1)[0]
    assert 'ACM_rollToBack = 0;' in htcl
    source = (F / 'fn_registerTreatmentRollRuntime.sqf').read_text()
    source = source.replace('getNumber _cfgRollB39', '1')
    execute(r'''
        private _listeners=[]; private _rolls=[];
        CBA_fnc_addEventHandler={_listeners pushBack _this;};
        ACME_fnc_rollProviderStart={_rolls pushBack _this;};
    ''' + adapt(source) + r'''
        [_medic,_patient,"head","BeginHeadTiltChinLift"] call ((_listeners select 0) select 1);
        [count _rolls==0,"HTCL queued a competing roll provider"] call _check;
    ''')
