"""Run the production 15-second observation clock and controller in SQF-VM.

Arma display/pose commands are explicit boundaries; clock integration, readiness,
cancellation, generation ownership and completion reporting run as shipped SQF.
"""
import re

import pytest

from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute, read


def function(name):
    source = read(name).replace('disableSerialization;', '')
    source = source.replace('local _medic', '_localMedic')
    source = source.replace('objectParent _medic', '_currentVehicle').replace('objectParent _patient', '_patientVehicle')
    source = source.replace('_medic distance2D _patient', '_distance')
    source = source.replace('findDisplay 46', '_mainDisplay')
    for command, value in [('safezoneX', '0'), ('safezoneY', '0'), ('safezoneW', '1'), ('safezoneH', '1')]:
        source = source.replace(command, value)
    source = re.sub(r'finite (_\w+)', 'true', source)
    source = source.replace('"ACME_Respiration" cutRsc ["ACME_Respiration_Display", "PLAIN", 0, false];',
                            'uiNamespace setVariable ["ACME_RespirationDisplay", missionNamespace];')
    source = source.replace('"ACME_Respiration" cutText ["", "PLAIN", 0, false];',
                            '_closed = _closed + 1; uiNamespace setVariable ["ACME_RespirationDisplay", objNull];')
    # Replace the display's native input registration primitive, not its callback or generation checks.
    tokens = lex(source)
    pairs = matching(tokens)
    for index in reversed(range(len(tokens) - 1)):
        if tokens[index].value == 'displayAddEventHandler':
            opening = index + 1
            end = tokens[pairs[opening]].offset + 1
            start = tokens[index - 1].offset
            source = source[:start] + '(' + source[tokens[opening].offset:end] + ' call _displayAddEH)' + source[end:]
    source = source.replace('_main displayRemoveEventHandler ["KeyDown", _keyEH];', '_removedEH pushBack _keyEH;')
    source = re.sub(r'\(_display displayCtrl (\d+)\) ctrlSetText ([^;]+);', r'_texts pushBack [\1, \2];', source)
    # Native control allocation/show/delete are modeled; session ownership remains production code.
    source = source.replace('_display ctrlCreate ["RscWatch", 71596]',
        '(call {_watchCreates = _watchCreates + 1; missionNamespace})')
    source = source.replace('_watchControl ctrlShow true;', '_watchShows = _watchShows + 1;')
    source = source.replace('ctrlDelete _watchControl;', '_watchDeletes = _watchDeletes + 1;')
    source = source.replace('_display displayCtrl 71593', '71593')
    source = re.sub(r'_circle ctrlSetPosition ([^;]+);', r'_circlePosition = \1;', source)
    source = re.sub(r'_circle ctrlSetTextColor ([^;]+);', r'_circleColor = \1;', source)
    source = source.replace('_circle ctrlCommit 0;', '')
    return f'ACME_fnc_{name}={{' + adapt(source) + '};\n'


def setup():
    return r'''
        private _watchCreates=0; private _watchShows=0; private _watchDeletes=0;
        private _localMedic=true; private _currentVehicle=objNull; private _patientVehicle=objNull;
        private _mainDisplay=missionNamespace; private _inputEH={}; private _removedEH=[];
        private _closed=0; private _texts=[]; private _circlePosition=[]; private _circleColor=[];
        private _starts=[]; private _stops=[]; private _reports=[]; private _logs=[]; private _reopened=[];
        private _poseEpoch=0; private _startAllowed=true;
        safezoneX=0; safezoneY=0; safezoneW=1; safezoneH=1;
        _patient setVariable ["ACM_breathing_RespirationRate", 16];
        private _displayAddEH={_inputEH=_this select 1; 17};
        ACME_fnc_a11yColor={[0.30,0.55,1,_this select 1]};
        private _airway=1; private _breathing=1; private _bagging=false;
        ACM_airway_fnc_getAirwayState={_airway}; ACM_breathing_fnc_getBreathingState={_breathing};
        ACM_core_fnc_bvmActive={_bagging}; ACM_core_fnc_cprActive={false};
        ace_common_fnc_displayTextStructured={_reports pushBack _this;};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        ACME_fnc_reopenMedicalMenu={_reopened pushBack _this;};
        ACME_fnc_treatmentPoseStart={
            _starts pushBack _this;
            if (!_startAllowed) exitWith {-1};
            _poseEpoch=_poseEpoch+1;
            _medic setVariable ["ACME_treatmentPoseState",[_poseEpoch,"pulse","ACME_StethoscopeWork",1,0,0,0,0,0,0,0,0.421]];
            _poseEpoch
        };
        ACME_fnc_treatmentPoseStop={
            _stops pushBack _this;
            if (((_medic getVariable ["ACME_treatmentPoseState",[]]) param [0,-1])==(_this select 2)) then {
                _medic setVariable ["ACME_treatmentPoseState",[]];
            };
        };
        private _frame={
            private _session=uiNamespace getVariable ["ACME_RespirationSession",[]];
            if (_session isEqualTo []) exitWith {};
            private _id=_session select 4;
            private _handler=_handlers select _id;
            [_handler select 1,_id] call (_handler select 0);
        };
        private _ready={(_medic getVariable ["ACME_treatmentPoseState",[]]) set [3,3]; call _frame;};
    ''' + ''.join(function(name) for name in ('respirationRate', 'respirationStep', 'respirationStop', 'respirationStart', 'respirationTick'))


@pytest.mark.parametrize('rate,count', [(0, 0), (4, 1), (12, 3), (16, 4), (18, 4), (60, 15), (80, 20)])
def test_fifteen_second_window_counts_whole_breaths_and_not_an_instant_start_beat(rate, count):
    execute(setup() + f'''
        private _s=[10,10,0,0,{rate}];
        private _same=[_s,10,{rate}] call ACME_fnc_respirationStep;
        [(_same select 1)==0,"start invented an observed breath"] call _check;
        private _done=[_s,25,{rate}] call ACME_fnc_respirationStep;
        [((_done select 0) select 3)=={count},"wrong fifteen-second breath count"] call _check;
        [(_done select 2)==15 && {{_done select 3}},"watch did not finish at fifteen"] call _check;
    ''')


@pytest.mark.parametrize('mission_multiplier', [0.1, 1, 12, 120, 1000])
def test_day_night_acceleration_and_clock_jumps_do_not_change_watch_or_estimate(mission_multiplier):
    execute(setup() + f'''
        _currentVehicle=missionNamespace; _patientVehicle=_currentVehicle;
        [_medic,_patient] call ACME_fnc_respirationStart;
        call _frame;
        for "_i" from 1 to 15 do {{
            _nowTime=10+_i; CBA_missionTime=10+(_i*{mission_multiplier});
            call _frame;
        }};
        _nowTime=27; call _frame;
        [count _reports==1,"no single completed measurement"] call _check;
        [((_reports select 0) select 0)=="Respirations: 16~ /min (4 breaths in 15 seconds)","daytime changed observed result"] call _check;
        [count _starts==0 && {{count _stops==0}},"seated watch changed occupant animations"] call _check;
    ''')


def test_rate_changes_are_counted_over_the_window_instead_of_reporting_final_instantaneous_rate():
    execute(setup() + r'''
        private _a=[[10,10,0,0,12],20,60] call ACME_fnc_respirationStep;
        private _b=[_a select 0,25,60] call ACME_fnc_respirationStep;
        [((_b select 0) select 3)==7,"rate change lost previously observed breaths"] call _check;
        [((_b select 0) select 3)*4==28,"rate change reported final instantaneous rate"] call _check;
    ''')


def test_apnea_interval_and_recovery_do_not_generate_extra_breaths():
    execute(setup() + r'''
        private _a=[[10,10,0,0,12],15,0] call ACME_fnc_respirationStep;
        private _b=[_a select 0,22,60] call ACME_fnc_respirationStep;
        [(_b select 1)==0,"apnea generated breaths"] call _check;
        private _c=[_b select 0,25,60] call ACME_fnc_respirationStep;
        [((_c select 0) select 3)==4,"recovered breaths miscounted"] call _check;
    ''')


def test_sparse_frames_are_capped_at_fifteen_and_no_second_completion_inflates_count():
    execute(setup() + r'''
        private _late=[[10,10,0,0,16],80,16] call ACME_fnc_respirationStep;
        private _again=[_late select 0,90,16] call ACME_fnc_respirationStep;
        [((_late select 0) select 3)==4 && {(_late select 2)==15},"late PFH inflated count/window"] call _check;
        [(_again select 1)==0 && {((_again select 0) select 3)==4},"finished sample counted twice"] call _check;
    ''')


def test_preparation_uses_exact_pulse_sequence_and_does_not_consume_watch_seconds():
    execute(setup() + r'''
        [_medic,_patient] call ACME_fnc_respirationStart;
        [(_starts select 0) isEqualTo [_medic,"pulse",-1,_patient],"provider did not use Feel Pulse sequence"] call _check;
        _nowTime=14; call _frame;
        [((uiNamespace getVariable "ACME_RespirationSession") select 5) isEqualTo [],"prep consumed observation time"] call _check;
        call _ready;
        _nowTime=28.99; call _frame;
        [count _reports==0,"sample completed before fifteen watch seconds"] call _check;
        _nowTime=29; call _frame;
        [count _reports==0,"last counted breath was hidden by instant teardown"] call _check;
        _nowTime=31; call _frame;
        [count _reports==1 && {count _reopened==1},"sample did not complete once"] call _check;
        [count _removedEH==1 && {count _stops==1},"completion retained pose/input"] call _check;
    ''')


def test_each_breath_has_bvm_blue_gradient_and_watch_advances_same_seconds():
    execute(setup() + r'''
        [_medic,_patient] call ACME_fnc_respirationStart; call _ready;
        _nowTime=13.75; call _frame;
        [(_circleColor select 3)>0,"observed breath had no cue"] call _check;
        [(_circleColor select [0,3]) isEqualTo [0.30,0.55,1],"cue not BVM blue"] call _check;
        [(71594 in (_texts apply {_x select 0})),"watch was not updated"] call _check;
        _nowTime=15.5; call _frame;
        [(_circleColor select 3)==0,"circle remained on between breaths"] call _check;
    ''')


@pytest.mark.parametrize('invalidation', [
    '_alive=false;', '_localMedic=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_distance=10;', '_patientVehicle=missionNamespace;', '_currentVehicle=missionNamespace;',
    '_dialog=true;', 'uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];',
    'uiNamespace setVariable ["ACME_RespirationDisplay",objNull];',
])
def test_cancellation_never_reports_a_partial_measurement(invalidation):
    execute(setup() + r'''
        [_medic,_patient] call ACME_fnc_respirationStart; call _ready;
        _nowTime=14; call _frame;
    ''' + invalidation + r'''
        call _frame;
        [(uiNamespace getVariable "ACME_RespirationSession") isEqualTo [],"invalid observation stayed active"] call _check;
        [count _reports==0 && {count _logs==0},"canceled observation reported a result"] call _check;
        [count _removedEH==1,"cancel leaked input handler"] call _check;
    ''')


def test_escape_consumes_key_and_restores_menu_with_no_partial_result():
    execute(setup() + r'''
        [_medic,_patient] call ACME_fnc_respirationStart; call _ready;
        [[_mainDisplay,1] call _inputEH,"Escape was not consumed"] call _check;
        [count _reopened==1 && {count _reports==0},"Escape did not cancel cleanly"] call _check;
        [!([_mainDisplay,1] call _inputEH),"retired handler still intercepted Escape"] call _check;
    ''')


def test_old_worker_and_stop_cannot_retire_replacement_watch_or_pose():
    execute(setup() + r'''
        [_medic,_patient] call ACME_fnc_respirationStart;
        private _old=+(_handlers select 0);
        [_medic,_patient] call ACME_fnc_respirationStart;
        [false,true,1] call ACME_fnc_respirationStop;
        [_old select 1,0] call (_old select 0);
        [((uiNamespace getVariable "ACME_RespirationSession") select 0)==2,"stale callback retired successor"] call _check;
        [((_medic getVariable "ACME_treatmentPoseState") select 0)==2,"stale callback retired successor pose"] call _check;
        [count _reopened==0 && {_closed==1},"old callback replaced successor UI"] call _check;
    ''')


def test_failed_and_timed_out_provider_entry_release_busy_without_reporting():
    execute(setup() + r'''
        _medic setVariable ["ACME_DP_Active",true]; _medic setVariable ["ACME_DP_Patient",_patient];
        _startAllowed=false; [_medic,_patient] call ACME_fnc_respirationStart;
        [!(_medic getVariable ["ACME_DP_TreatmentBusy",true]),"failed entry stranded pressure pause"] call _check;
        _startAllowed=true; [_medic,_patient] call ACME_fnc_respirationStart;
        _nowTime=17; call _frame;
        [(uiNamespace getVariable "ACME_RespirationSession") isEqualTo [],"unentered animation did not time out"] call _check;
        [!(_medic getVariable ["ACME_DP_TreatmentBusy",true]),"entry timeout stranded pressure pause"] call _check;
        [count _logs==0,"entry failure reported completed observation"] call _check;
    ''')


def test_replaced_pose_preserves_successors_direct_pressure_busy_ownership():
    execute(setup() + r'''
        _medic setVariable ["ACME_DP_Active",true]; _medic setVariable ["ACME_DP_Patient",_patient];
        [_medic,_patient] call ACME_fnc_respirationStart;
        _medic setVariable ["ACME_treatmentPoseState",[2,"stethoscope"]];
        call _frame;
        [_medic getVariable ["ACME_DP_TreatmentBusy",false],"old observer cleared successor busy ownership"] call _check;
        [(_medic getVariable "ACME_treatmentPoseState") isEqualTo [2,"stethoscope"],"old observer retired new scope"] call _check;
        [count _reopened==0,"old observer reopened over scope"] call _check;
    ''')


def test_shared_pose_retiring_after_failed_holster_releases_pressure_instead_of_inventing_successor():
    execute(setup() + r'''
        _medic setVariable ["ACME_DP_Active",true]; _medic setVariable ["ACME_DP_Patient",_patient];
        [_medic,_patient] call ACME_fnc_respirationStart;
        _nowTime=13; _medic setVariable ["ACME_treatmentPoseState",[]];
        call _frame;
        [!(_medic getVariable ["ACME_DP_TreatmentBusy",true]),"failed holster left pressure permanently passive"] call _check;
        [(uiNamespace getVariable "ACME_RespirationSession") isEqualTo [],"failed shared pose retained observation"] call _check;
        [count _reports==0 && {count _logs==0},"failed shared pose reported a partial result"] call _check;
        [count _reopened==1,"failed shared pose did not return to medical menu"] call _check;
    ''')


@pytest.mark.parametrize('rate,alive,expected', [(-1, True, 0), (0, True, 0), (80, True, 80), (100, True, 80), (16, False, 0)])
def test_read_only_rate_handles_apnea_death_and_native_bounds(rate, alive, expected):
    execute(setup() + f'''
        _patientAlive={str(alive).lower()}; _patient setVariable ["ACM_breathing_RespirationRate",{rate}];
        [[_patient] call ACME_fnc_respirationRate=={expected},"rate boundary failed"] call _check;
        [(_patient getVariable "ACM_breathing_RespirationRate")=={rate},"observation wrote physiology"] call _check;
    ''')


def test_action_and_ui_resource_have_independent_state_and_bvm_texture():
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    action = config.split('class ACME_MeasureRespirations: CheckPulse {', 1)[1].split('\n    };', 1)[0]
    assert 'callbackSuccess = "ACME_fnc_respirationStart";' in action
    assert 'allowedSelections[] = {"Head", "Body"};' in action
    assert 'ACME_neverRollToBack = 1;' in action
    resource = (ROOT / 'addons/acm_extended/Respirations.hpp').read_text()
    assert r'\acm_extended\ui\dot_grad_ca.paa' in resource
    assert 'OBSERVING...' in resource
    assert '15 real seconds' not in resource
    assert 'timeMultiplier' not in re.sub(r'/\*.*?\*/|//[^\n]*', '', read('respirationStep'), flags=re.S)


@pytest.mark.parametrize('condition', [
    '_airway=0;', '_breathing=0;', '_patient setVariable ["ace_medical_heartRate",19];',
    '_patient setVariable ["ACM_breathing_TensionPneumothorax_State",true];',
    '_patient setVariable ["ACM_breathing_Hemothorax_Fluid",1.41];',
    '_patient setVariable ["ACME_roc_paralyzed",true];',
    '_patient setVariable ["ace_medical_inCardiacArrest",true];',
])
def test_observational_absence_rules_prevent_phantom_breaths_from_stale_native_rr(condition):
    execute(setup() + condition + r'''
        [[_patient] call ACME_fnc_respirationRate==0,"absent breathing displayed a stale positive rate"] call _check;
    ''')


@pytest.mark.parametrize('vte,rate,expected', [(500, 18, 18), (20, 20, 20), (0, 18, 0), (500, 0, 0)])
def test_measured_mechanical_ventilation_uses_delivered_breaths_even_with_no_spontaneous_effort(vte, rate, expected):
    execute(setup() + f'''
        _patient setVariable ["ACME_vent_driving",true];
        _patient setVariable ["ACME_roc_paralyzed",true];
        _patient setVariable ["ACM_breathing_RespirationRate",0];
        _patient setVariable ["ACME_vent_effectiveRR",{rate}];
        _patient setVariable ["ACME_vent_vte",{vte}];
        [[_patient] call ACME_fnc_respirationRate=={expected},"mechanical rate ignored delivered ventilation"] call _check;
    ''')


def test_bagging_can_deliver_observable_breaths_during_paralysis():
    execute(setup() + r'''
        _patient setVariable ["ACME_roc_paralyzed",true];
        _patient setVariable ["ACM_breathing_RespirationRate",10]; _bagging=true;
        [[_patient] call ACME_fnc_respirationRate==10,"paralysis hid active assisted breaths"] call _check;
    ''')


def test_apneic_observation_reports_zero_only_after_full_watch_window():
    execute(setup() + r'''
        _patient setVariable ["ACM_breathing_RespirationRate",0];
        [_medic,_patient] call ACME_fnc_respirationStart; call _ready;
        _nowTime=24.9; call _frame;
        [count _reports==0 && {(_circleColor select 3)==0},"apnea completed early or generated a breath cue"] call _check;
        _nowTime=25; call _frame;
        [((_reports select 0) select 0)=="Respirations: 0~ /min (0 breaths in 15 seconds)","zero observation wrong"] call _check;
    ''')


def provider_events():
    source = read('registerProviderStanceReleaseRuntime')
    source = source.replace('objectParent _medic', '_currentVehicle').replace('objectParent _m', '_currentVehicle')
    return r'''
        private _registered=[];
        CBA_fnc_addEventHandler={_registered pushBack _this;};
    ''' + adapt(source) + r'''
        private _success=((_registered select {(_x select 0)=="ace_treatmentSucceded"}) select 0) select 1;
        private _started=((_registered select {(_x select 0)=="ace_treatmentStarted"}) select 0) select 1;
    '''


def test_ace_setup_success_does_not_resume_pressure_or_reopen_over_observation():
    execute(setup() + provider_events() + r'''
        _medic setVariable ["ACME_DP_Active",true]; _medic setVariable ["ACME_DP_Patient",_patient];
        [_medic,_patient] call ACME_fnc_respirationStart;
        [_medic,_patient,"Body","ACME_MeasureRespirations"] call _success;
        [_medic getVariable ["ACME_DP_TreatmentBusy",false],"ACE setup success resumed pressure"] call _check;
        [(count _waits)==1,"setup queued an unwanted menu reopen"] call _check;
        [count (uiNamespace getVariable "ACME_RespirationSession")>0,"setup retired live watch"] call _check;
    ''')


def test_new_treatment_retires_observation_then_holds_pressure_passive():
    execute(setup() + provider_events() + r'''
        _medic setVariable ["ACME_DP_Active",true]; _medic setVariable ["ACME_DP_Patient",_patient];
        [_medic,_patient] call ACME_fnc_respirationStart;
        [_medic,_patient,"Body","FieldDressing"] call _started;
        [(uiNamespace getVariable "ACME_RespirationSession") isEqualTo [],"new treatment retained watch"] call _check;
        [_medic getVariable ["ACME_DP_TreatmentBusy",false],"new treatment lost pressure busy flag"] call _check;
        [count _reopened==0 && {count _reports==0},"new treatment was interrupted by old result/menu"] call _check;
    ''')


def pulse_worker():
    source = (ROOT / 'addons/circulation/functions/fnc_feelPulse.sqf').read_text()
    source = source.split('private _pfh = [{', 1)[1].split('},0,[_medic', 1)[0]
    source = source.replace('_medic distance2D _patient', '_distance')
    return 'private _pulseWorker={' + adapt(source) + '};'


@pytest.mark.parametrize('successor', ['native', 'stethoscope', 'respiration'])
def test_retired_pulse_worker_cannot_clear_successor_busy_or_play_old_exit(successor):
    replacement = {
        'native': '_medic setVariable ["ACME_treatmentPoseState",[1,"pulse"]];',
        'stethoscope': '_medic setVariable ["ACME_treatmentPoseState",[2,"stethoscope"]];',
        'respiration': 'uiNamespace setVariable ["ACME_RespirationSession",[2,_medic,_patient]];',
    }[successor]
    execute(setup() + pulse_worker() + r'''
        _medic setVariable ["ACME_DP_Active",true]; _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        _medic setVariable ["ACME_providerTreatmentEpoch",1];
        uiNamespace setVariable ["ACME_PulseEpoch",1];
        uiNamespace setVariable ["ACME_PulseCheckActive",true];
        uiNamespace setVariable ["ACME_PulseCheckCancel",true];
        uiNamespace setVariable ["ACME_PulseEscKey","key"];
        _handlers pushBack [{},[],true];
    ''' + replacement + r'''
        [[_medic,_patient,"Head","key",1,1,objNull,-1,0],0] call _pulseWorker;
        [_medic getVariable ["ACME_DP_TreatmentBusy",false],"old pulse cleared successor busy reservation"] call _check;
        [(_stops select 0) select 3,"old pulse played its exit over successor treatment"] call _check;
        [count _reopened==0,"old pulse reopened medical menu over successor"] call _check;
    ''')
