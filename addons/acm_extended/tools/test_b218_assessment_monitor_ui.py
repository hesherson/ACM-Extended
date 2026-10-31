"""B218 actual-SQF assessment returns, motion envelopes, logging and measured hints.

Engine animation/UI/drawing/transport are explicit boundaries. No rendered Arma
pose, real network latency, or clinical fidelity is implied by these tests.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read, namespace_public_arguments
from test_b212_assessment_sequence import setup as assessment_setup
from test_historical_ecg_artifact_execution import setup as ecg_setup, engine_code


@pytest.mark.parametrize('action',['CheckAirway','CheckBreathing'])
def test_completion_reopens_after_native_cleanup_with_generic_menu_handoff(action):
    execute(assessment_setup()+f'_request set [3,"{action}"];'+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        [count _poseStops==1 && {(_poseStops select 0) select 3},"completion requested a standing exit"] call _check;
        [_reopened==0 && {count _waits==1},"menu opened inside native callback"] call _check;
        private _frameJob=_waits deleteAt 0; (_frameJob select 1) call (_frameJob select 0);
        private _returnJob=_waits deleteAt 0;
        _newOwner=true;
        [!((_returnJob select 1) call (_returnJob select 2)),"menu preempted active cleanup"] call _check;
        _newOwner=false;
        [(_returnJob select 1) call (_returnJob select 2),"cleanup did not release return"] call _check;
        (_returnJob select 1) call (_returnJob select 0);
        [_reopened==1 && {(_medic getVariable ["ACME_menuPoseAfterTreatment",objNull]) isEqualTo _patient},"generic pose handoff missing"] call _check;
        [(_medic getVariable ["ACME_assessmentReturn",[]]) isEqualTo [],"return request retained"] call _check;
    ''')


@pytest.mark.parametrize('invalidation',[
    '_medic setVariable ["ACME_assessmentReturn",[]];',
    '_medic setVariable ["ACME_providerLocalityEpoch",4];',
    '_medic setVariable ["ACME_menuPoseEpoch",4];',
    '_distance=20;', '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];', '_dialog=true;',
])
def test_stale_assessment_menu_return_never_steals_successor_pose_or_focus(invalidation):
    execute(assessment_setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        private _frameJob=_waits deleteAt 0; (_frameJob select 1) call (_frameJob select 0);
        private _returnJob=_waits deleteAt 0;
    '''+invalidation+r'''
        (_returnJob select 1) call (_returnJob select 0);
        [_reopened==0 && {(_medic getVariable ["ACME_menuPoseAfterTreatment",objNull]) isEqualTo objNull},"stale return stole focus/pose"] call _check;
    ''')


def test_assessment_return_timeout_releases_only_its_request_without_forcing_pose():
    execute(assessment_setup()+r'''
        _request call ACME_fnc_assessmentStart; call _ready;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        private _frameJob=_waits deleteAt 0; (_frameJob select 1) call (_frameJob select 0);
        private _returnJob=_waits deleteAt 0;
        (_returnJob select 1) call (_returnJob select 3);
        [(_medic getVariable ["ACME_assessmentReturn",[]]) isEqualTo [] && {_reopened==0},"timeout forced menu or leaked request"] call _check;
    ''')


@pytest.mark.parametrize('elapsed',[0,1,2,3.99,4])
def test_breathing_runs_complete_unaccelerated_rtm_after_entry(elapsed):
    execute(assessment_setup()+r'''
        _request set [3,"CheckBreathing"]; _request call ACME_fnc_assessmentStart;
        CBA_missionTime=11.5; call _ready;
        _nativeDuration=4;
    '''+f'_nativeElapsed={elapsed}; CBA_missionTime=11.5+{elapsed}; call _frame;'+f'''
        private _r=_medic getVariable "ACME_assessment";
        [((_r select 2)==3)=={str(elapsed>=4).lower()},"breathing completed before full RTM"] call _check;
        [abs ((_r select 12)-5.5)<0.001,"total omitted real entry"] call _check;
    ''')


@pytest.mark.parametrize('anim,blend,rate,expected',[
    ('ACM_LyingState',1,1,0),('ACM_RecoveryPosition',1,0,0),
    ('ACM_RecoveryPosition',.5,1,.72),('ACM_RecoveryPosition',.5,0,.72),
    ('ACME_headElevPatientGrab',1,1,.62),('ACME_headElevPatientRelease',1,1,.62),
    ('ACME_headElevPatientGrab',1,0,0),('ACME_headElevHold',.4,0,.48),
    ('ACME_RollLeft',.5,1,.78),('ACME_RollRight',1,1,.78),('ACME_RollLeft',1,0,0),
    ('ainjppnemstpsnonwrfldnon',.2,1,.40),
])
def test_motion_magnitude_tracks_rendered_action_and_held_pose_is_quiet(anim,blend,rate,expected):
    execute(ecg_setup()+f'''
        _patientAnimation="{anim}"; _patientBlend={blend}; _patientRate={rate};
        private _strength=[_patient] call ACME_fnc_ecgArtifactStrength;
        [abs (_strength-{expected})<0.001,"wrong motion envelope"] call _check;
    ''')


@pytest.mark.parametrize('suppressed,paralyzed,alive,expected',[
    (False,False,True,.98),(True,False,True,0),(False,True,True,0),(False,False,False,0),
])
def test_visible_seizure_major_artifact_excludes_suppressed_paralyzed_or_dead(suppressed,paralyzed,alive,expected):
    execute(ecg_setup()+f'''
        _patientAlive={str(alive).lower()};
        _patient setVariable ["ACME_lido_seizureState","active"];
        _patient setVariable ["ACME_seizure_suppressed",{str(suppressed).lower()}];
        _patient setVariable ["ACME_roc_paralyzed",{str(paralyzed).lower()}];
        [abs (([_patient] call ACME_fnc_ecgArtifactStrength)-{expected})<0.001,"wrong seizure artifact"] call _check;
    ''')


def test_seizure_artifact_obscures_entire_sweep_without_changing_rhythm_or_source():
    execute(ecg_setup()+r'''
        _patient setVariable ["ACME_lido_seizureState","active"];
        private _wave=[]; _wave resize 176; _wave=_wave apply {0};
        private _safe=_wave apply {true};
        private _out=[_patient,_wave,_safe] call ACME_fnc_ecgArtifactApply;
        [count (_out select 0)==176 && {(_out select 1) findIf {_x} == -1},"convulsive EMG left falsely safe SYNC columns"] call _check;
        [((_out select 0) findIf {abs _x>12})>=0,"seizure did not produce major artifact"] call _check;
        [(_wave findIf {_x!=0})==-1 && {(_safe findIf {!_x})==-1},"caller buffer changed"] call _check;
        [(_patient getVariable ["ace_medical_heartRate",0])==80 && {_rhythm==0},"presentation converted rhythm"] call _check;
    ''')


def hint_setup(height):
    s=(ROOT/'addons/core/overrides/fnc_displayTextStructured.sqf').read_text()
    s=s.replace('["_target", ACE_player, [objNull]]','["_target", ACE_player, [uiNamespace]]')
    s=s.replace('_target != ACE_player','!(_target isEqualTo ACE_player)')
    s=s.replace('isLocalized _x','false').replace('isLocalized _text','false')
    s=s.replace('parseText format','format')
    s=re.sub(r'^\("ACE_RscHint".*$','',s,flags=re.M)
    s=s.replace('disableSerialization;','')
    s=s.replace('private _ctrlHint = uiNamespace getVariable "ACE_ctrlHint";','private _ctrlHint=uiNamespace;')
    s=re.sub(r'_ctrlHint ctrlSet(?:BackgroundColor|TextColor) [^;]+;','',s)
    s=s.replace('_ctrlHint ctrlSetStructuredText _text;','_rendered=_text;')
    s=s.replace('ctrlTextHeight _ctrlHint','_measuredHeight')
    s=re.sub(r'_ctrlHint ctrlSetPosition (\[[^;]*\]);',r'_positions pushBack \1;',s)
    s=s.replace('_ctrlHint ctrlCommit 0;','')
    s=s.replace('curatorCamera','objNull')
    for k,v in [('safeZoneX','0'),('safeZoneY','0'),('safeZoneW','1.6'),('safeZoneH','1')]:
        s=re.sub(r'\b'+k+r'\b',v,s)
    return f'private _measuredHeight={height}; private _positions=[]; private _rendered="";'+ 'ACME_test_hint={'+adapt(s)+'};'


@pytest.mark.parametrize('height',[.025,.05,.075,.15])
@pytest.mark.parametrize('legacy_size',[1,3,4,12])
def test_hint_height_uses_measured_wrapped_content_not_legacy_size(height,legacy_size):
    execute(hint_setup(height)+f'''
        ["Example result",{legacy_size},_medic] call ACME_test_hint;
        [count _positions==2,"width was not set before measuring"] call _check;
        [abs ((_positions select 1 select 3)-({height}+.003))<0.0001,"unnecessary lower dead space retained"] call _check;
    ''')


def log_setup():
    s=adapt((ROOT/'addons/core/overrides/fnc_addToLog.sqf').read_text())
    s=s.replace('local _unit','true').replace('date params','[2026,10,1,12,30] params')
    return r'''
        ACME_fnc_emmaMarkContact={};
        ACME_fnc_ivLogRelabel={_this};
        CBA_fnc_formatNumber={str (_this select 0)};
    '''+'ace_medical_treatment_fnc_addToLog={'+s+'};'


def test_quick_view_retains_multiple_assessments_and_replaces_only_matching_sensor_side():
    execute(log_setup()+r'''
        [_patient,"quick_view","Pupils: %1",["equal/reactive"]] call ace_medical_treatment_fnc_addToLog;
        [_patient,"quick_view","Skin: %1",["cool/clammy"]] call ace_medical_treatment_fnc_addToLog;
        [_patient,"quick_view","Pulse oximeter (%1): %2",["left arm","SpO2 95%"]] call ace_medical_treatment_fnc_addToLog;
        [_patient,"quick_view","Pulse oximeter (%1): %2",["right arm","SpO2 96%"]] call ace_medical_treatment_fnc_addToLog;
        [_patient,"quick_view","Pulse oximeter (%1): %2",["left arm","SpO2 97%"]] call ace_medical_treatment_fnc_addToLog;
        private _rows=_patient getVariable ["ace_medical_log_quick_view",[]];
        [count _rows==4 && {((_rows select 3) select 2) isEqualTo ["left arm","SpO2 97%"]},"sensor rows duplicated or discarded other examinations"] call _check;
        for "_i" from 1 to 40 do {[_patient,"quick_view","Exam %1",[_i]] call ace_medical_treatment_fnc_addToLog;};
        [count (_patient getVariable ["ace_medical_log_quick_view",[]])==32,"quick-view history not bounded"] call _check;
        for "_i" from 1 to 12 do {[_patient,"activity","Exam %1",[_i]] call ace_medical_treatment_fnc_addToLog;};
        [count (_patient getVariable ["ace_medical_log_activity",[]])==8,"activity retention changed"] call _check;
    ''')


@pytest.mark.parametrize('assessment',['feelSkin','tbiAssessPupils','readCoreTemp'])
def test_completed_findings_are_written_to_activity_and_quick_view(assessment):
    s=adapt(read(assessment))
    # Normal pupil fixture has no TBI map; only state selection/logging executes.
    execute(r'''
        private _logs=[]; private _hints=[];
        ace_common_fnc_displayTextStructured={_hints pushBack _this;};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        ACME_fnc_skinSigns={["abnormal","Cool and clammy",[],"#ffffff"]};
        ACME_fnc_treatmentSupplyCount={1};
    '''+'ACME_fnc_medLog={'+adapt(read('medLog'))+'};'+
    '[_medic,_patient] call {'+s+'};'+r'''
        [count _logs==2 && {(_logs select 0 select 1)=="activity"} && {(_logs select 1 select 1)=="quick_view"},"completed finding not in both logs"] call _check;
        [count _hints==1,"display result missing or duplicated"] call _check;
    ''')


def test_monitor_refresh_is_triggered_by_motion_band_and_bridges_only_future_columns():
    s=(ROOT/'addons/circulation/functions/fnc_displayAEDMonitor.sqf').read_text()
    assert 'if (_artifactChanged || {_stepCondition}' in s
    assert 'ACME_AED_Monitor_ArtifactBand' in s
    assert 'if (_artifactChanged && {!_rhythmChangeEKG})' in s
    assert '[_ekgBasis, _freshEKG, _startIndex, 3] call _fnc_bridge' in s
    assert '_startIndex' in s and 'ACME_AED_MonitorCursorTime' in s


def test_debug_and_assessment_contracts_follow_user_requested_layout_and_normal_rate():
    debug=read('debugMenuClinical')
    for text in ['_topPadding',"size='1.12'",'"Faction"','"Obtunded"']:
        assert text in debug
    assert '"Obtund"' not in debug
    pose=read('treatmentPoseStart')
    assert 'assessmentAirway' in pose and 'assessmentBreathing' in pose
    assert 'ACME_menuPoseAfterTreatment' in read('menuPoseStart')
    assert 'ACM_GenericContinuous' in read('menuPoseStart')
    shock=read('shockLocal')
    assert '"%1 initiated defibrillation"' in shock
    assert '[[_medic, false, true] call ace_common_fnc_getName]' in shock
    assert "Defibrillation with ROSC" not in shock


@pytest.mark.parametrize('action',['CheckAirway','CheckBreathing'])
def test_seated_assessment_has_identity_checked_menu_return_without_on_foot_pose(action):
    execute(assessment_setup()+f'_request set [3,"{action}"];'+r'''
        _vehicle=_patient; _patientVehicle=_patient;
        [_request call ACME_fnc_assessmentStart,"seated start failed"] call _check;
        [(_nativeArgs select 7)==-1 && {(_nativeArgs select 8)==1},"seated callback identity missing"] call _check;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo [] && {_poseEpoch==0},"seated action forced on-foot work"] call _check;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        [count _poseStops==0 && {count _waits==1},"seated completion forced a pose or did not schedule return"] call _check;
        private _job=_waits deleteAt 0; (_job select 1) call (_job select 0);
        _job=_waits deleteAt 0; (_job select 1) call (_job select 0);
        [_reopened==1 && {(_medic getVariable ["ACME_assessmentSeated",[]]) isEqualTo []},"seated return failed or leaked identity"] call _check;
    ''')


@pytest.mark.parametrize('invalidation',[
    '_medic setVariable ["ACME_assessmentSeated",[]];',
    '_request call ACME_fnc_assessmentStart;',
    '_vehicle=objNull;', '_patientVehicle=objNull;',
])
def test_stale_seated_completion_does_not_reopen_or_release_newer_action(invalidation):
    execute(assessment_setup()+r'''
        _vehicle=_patient; _patientVehicle=_patient;
        _request call ACME_fnc_assessmentStart;
        private _old=+_nativeArgs;
    '''+invalidation+r'''
        [_old] call ACME_fnc_assessmentFinish;
        [count _waits==0 && {count _poseStops==0} && {_reopened==0},"stale seated result stole menu/pose"] call _check;
    ''')


@pytest.mark.parametrize('classname',['CheckAirway','CheckBreathing'])
def test_native_seated_callback_adds_only_the_seated_identity_and_keeps_public_event_shape(classname):
    source=(ROOT/'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    source=source[source.index('private _callbackArgs ='):]
    source=source.replace('getText (_config >> "displayNameProgress")','"Checking"')
    execute(r'''
        private _bodyPart="Head"; private _itemUser=objNull; private _usedItem=""; private _createLitter=false;
        private _treatmentTime=5; private _startedArgs=[]; private _progressArgs=[]; private _startedEvent=[];
        private _callbackStart={_startedArgs=+_this;}; private _callbackProgress={true};
        ace_medical_treatment_fnc_treatmentSuccess={}; ace_medical_treatment_fnc_treatmentFailure={};
        ACME_fnc_assessmentProgressBar={_progressArgs=+(_this select 1);};
        CBA_fnc_localEvent={_startedEvent=_this select 1;};
        _medic setVariable ["ACME_assessmentSeated",[42,[_medic,_patient,"Head","CheckAirway"],objNull]];
    '''+f'private _classname="{classname}";'+ 'call {'+adapt(source)+'};'+r'''
        [count _progressArgs==9 && {(_progressArgs select 7)==-1} && {(_progressArgs select 8)==42},"native seated identity not captured"] call _check;
        [_startedArgs isEqualTo _progressArgs && {count _startedEvent==7},"native public event shape changed"] call _check;
    ''')
