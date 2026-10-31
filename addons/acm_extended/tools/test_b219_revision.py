"""B219 production-SQF motor/UI/AI/lifecycle tests with explicit Arma engine boundaries.
No real animation, native inventory window, PhysX or network rendering is simulated.
"""
import json
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_bounded_head_completion import setup as head_setup
from test_historical_cardiac_execution import code as cardiac_code, setup as cardiac_setup
from test_historical_ecg_artifact_execution import setup as ecg_setup
from test_debug_single_overlay import definition
from test_historical_vial_execution import map_defaults


def binary_array(source, command, replacement):
    """Replace an engine command, keeping the exact production array/code argument."""
    ts=lex(source); pairs=matching(ts); edits=[]
    for i,t in enumerate(ts[:-1]):
        if t.kind=='ident' and t.value==command and ts[i+1].value=='[':
            end=pairs[i+1]
            unit=ts[i-1].value
            array=source[ts[i+1].offset:ts[end].offset+1]
            edits.append((ts[i-1].offset,ts[end].offset+1,replacement(unit,array)))
    for a,b,v in reversed(edits): source=source[:a]+v+source[b:]
    return source


@pytest.mark.parametrize('count',[0,1,2,3,4,5,8,15,31])
def test_medications_are_sorted_down_left_then_down_right_without_mutating_source(count):
    rows=[[f'Med {n:02}',str(n),'color'] for n in reversed(range(count))]
    expected=sorted(r[0] for r in rows)
    execute('ACME_fnc_debugMedicationColumns={'+adapt(read('debugMedicationColumns'))+'};'+f'''
        private _rows={json.dumps(rows)}; private _before=+_rows;
        private _pairs=[_rows] call ACME_fnc_debugMedicationColumns;
        private _left=[]; private _right=[];
        {{_left pushBack (_x select 0);if (count _x>3) then {{_right pushBack (_x select 3);}};}} forEach _pairs;
        [_left+_right isEqualTo {json.dumps(expected)},"column-major alphabetical order lost"] call _check;
        [_rows isEqualTo _before,"source medication table mutated"] call _check;
    ''')


@pytest.mark.parametrize('side,color',[('WEST','#4FA3FF'),('EAST','#FF5555'),('CIV','#BD83EA'),('GUER','#64D978'),('UNKNOWN','muted')])
def test_debug_side_and_faction_use_requested_colors(side,color):
    s=read('debugMenuClinical'); start=s.index('private _sideColor =');end=s.index('\n};',start)+3
    execute(f'private _patientSide="{side}";private _cMute="muted";'+s[start:end].replace('toUpperANSI','toUpper')+
            f'[_sideColor=="{color}","wrong faction/side color"] call _check;')
    assert '"Faction", _factionName, _sideColor' in s
    assert 'forEach ([_medicationRows] call ACME_fnc_debugMedicationColumns)' in s
    assert 'if (count _x == 3) then {_x call _one} else {_x call _pair}' in s


def shock_setup():
    s=read('shockLocal').replace('serverTime','_serverTime')
    s=re.sub(r'playSound3D \[[^;]*;', '_sounds=_sounds+1;',s)
    return cardiac_setup()+'''
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _serverTime=100;private _logs=[];private _sounds=0;private _notices=[];private _roscResult=true;
        private _providerName="M. Harlow";
        ace_common_fnc_getName={_providerName};ace_common_fnc_isAwake={true};
        ace_medical_gui_maxDistance=3.5;
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        ACME_fnc_clinicalNotice={_notices pushBack _this;};
        ACM_circulation_fnc_AED_CanAdministerShock={true};
        ACM_circulation_fnc_setRuntimeState={};
        ACME_fnc_rhythmNativeShockGraceCommit={};ACME_fnc_rhythmNativeHoldCommit={};ACME_fnc_rhythmNativeHighHRFloorCommit={};
        ACME_fnc_shockROSC={_roscResult};ACME_fnc_lidoEffectiveness={0};
        ACME_fnc_rhythmRelease={};ACME_fnc_arrestLocal={};ACME_fnc_rhythmSet={};
        ACM_circulation_fnc_getCardiacMedicationEffects={createHashMapFromArray [["amiodarone",5]]};
        _patient setVariable ["ACM_circulation_CardiacArrest_ResistChecked",true];
        _patient setVariable ["ACM_circulation_CardiacArrest_ShockResistant",false];
        _rhythm=2;CBA_missionTime=100;
    '''+'ACME_fnc_shockLocal={'+map_defaults(cardiac_code(s))+'};'


@pytest.mark.parametrize('living,rosc',[(True,True),(True,False),(False,False)])
def test_shock_log_names_actual_actor_and_not_inferred_outcome_or_duplicate(living,rosc):
    execute(shock_setup()+f'_patientAlive={str(living).lower()};_roscResult={str(rosc).lower()};'+'''
        private _request=[_medic,_patient,"one",1,-60,false,100];
        _request call ACME_fnc_shockLocal; _request call ACME_fnc_shockLocal;
        [count _logs==1,"committed shock logged zero/two times"] call _check;
        private _entry=_logs select 0;
        [(_entry select 2)=="%1 initiated defibrillation" && {(_entry select 3) isEqualTo ["M. Harlow"]},"actor missing or outcome leaked into activity"] call _check;
    ''')


@pytest.mark.parametrize('clinical',[False,True])
@pytest.mark.parametrize('action',['RecoveryPosition','CPR'])
def test_lowering_event_retains_actual_provider_and_only_suppresses_recovery_theatre(clinical,action):
    s=adapt(read('registerHeadElevationTreatmentRuntime'))
    execute(head_setup()+'''
        private _logs=[];private _handlersByName=createHashMap;
        ace_common_fnc_getName={"A. Patel"};ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        CBA_fnc_addEventHandler={_handlersByName set [_this select 0,_this select 1];};
    '''+'ACME_fnc_medLog={'+adapt(read('medLog'))+'};'+s+
    f'missionNamespace setVariable ["ACME_hc_descriptors",{str(clinical).lower()}];'+f'''
        [_medic,_patient,"Head","{action}"] call (_handlersByName get "ace_treatmentStarted");
        [count _logs==1 && {{((_logs select 0) select 3) isEqualTo ["A. Patel"]}},"lowering lost the initiating actor"] call _check;
        [count _provider=={int(action=='CPR')},"recovery duplicated provider lowering"] call _check;
    ''')


def motor_code(name):
    s=read(name)
    for unit in ('_patient','_p','_unit'):
        for old,new in [('local '+unit,'_patientLocal'),('alive '+unit,'_patientAlive'),
                        ('objectParent '+unit,'_parent'),('gestureState '+unit,'_gestureState'),
                        ('owner '+unit,'7'),('isAwake '+unit,'_physicalAwake'),('velocity '+unit,'_engineVelocity')]:
            s=re.sub(r'(?<!\w)'+re.escape(old)+r'\b',lambda _:new,s)
    s=s.replace('serverTime','_clock').replace('hasInterface','true')
    # This harness uses finite numeric clock inputs; native finite() is not in SQF-VM.
    s=re.sub(r'finite (_\w+)', r'(\1 isEqualType 0)', s)
    s=binary_array(s,'switchGesture',lambda u,a:f'[{a}] call ACME_test_playGesture')
    s=s.replace('_patient switchGesture "GestureEmpty";','[["GestureEmpty"]] call ACME_test_playGesture;')
    s=binary_array(s,'switchMove',lambda u,a:f'_baseMoves pushBack {a}')
    s=binary_array(s,'addEventHandler',lambda u,a:f'[{u},{a}] call _addEH')
    s=binary_array(s,'removeEventHandler',lambda u,a:f'_removedEH pushBack {a}')
    return 'ACME_fnc_'+name+'={'+adapt(s)+'};'


def motor_setup():
    return '''
        private _clock=100;CBA_missionTime=100;private _patientLocal=true;private _parent=objNull;
        private _physicalAwake=true;private _engineVelocity=[0,0,0];private _gestureState="";
        private _capturedGestures=[];private _baseMoves=[];private _jobs=[];private _ehs=[];private _removedEH=[];
        _patient setVariable ["ACME_clinicalEpoch",1];
        _patient setVariable ["ACME_lido_seizureState","active"];
        ACME_test_playGesture={params ["_array"];_gestureState=_array select 0;_capturedGestures pushBack _array;};
        private _addEH={_ehs pushBack _this;count _ehs};
        CBA_fnc_waitAndExecute={_jobs pushBack _this;};
        CBA_fnc_execNextFrame={_jobs pushBack [_this select 0,_this select 1,0];};
        CBA_fnc_globalEvent={_events pushBack _this; if ((_this select 0)=="ACME_seizureGestureSync") then {(_this select 1) call ACME_fnc_seizureGestureSync;};};
        ace_common_fnc_isBeingDragged={false};ace_common_fnc_isBeingCarried={false};ACM_core_fnc_cprActive={false};
        private _deliver={params ["_job"]; (_job select 1) call (_job select 0);};
    '''+''.join(motor_code(n) for n in ['clinicalEpoch','seizureMotorMode','seizureArrestTrack','seizureGestureSync','seizureJerkTiming','seizureGestureAdvance','seizureMotion'])


@pytest.mark.parametrize('arrest,onset,now,expected',[(False,70,100,'full'),(True,100,100,'full'),(True,100,119.999,'full'),(True,100,120,'jerks'),(True,100,140,'jerks'),(True,-1,100,'jerks')])
def test_motor_clock_cutoff_does_not_reset_for_observer_or_late_arrest(arrest,onset,now,expected):
    execute(motor_setup()+f'''
        _patient setVariable ["ace_medical_inCardiacArrest",{str(arrest).lower()}];
        _patient setVariable ["ACME_seizure_arrestStartedAt",{onset}];_clock={now};
        [([_patient] call ACME_fnc_seizureMotorMode)=="{expected}","wrong arrest motor phase"] call _check;
        [(_patient getVariable ["ACME_lido_seizureState",""])=="active","motor reader treated seizure"] call _check;
    ''')


def test_arrest_edge_is_idempotent_and_switches_to_jerks_at_twenty_without_stopping_seizure():
    execute(motor_setup()+'''
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        [_patient,true] call ACME_fnc_seizureArrestTrack;private _edge=_jobs select 0;
        _clock=103;[_patient,true] call ACME_fnc_seizureArrestTrack;
        [count _jobs==1 && {(_patient getVariable "ACME_seizure_arrestStartedAt")==100},"duplicate edge restarted window"] call _check;
        [_patient,true] call ACME_fnc_seizureMotion;
        CBA_missionTime=102;[_jobs select 1] call _deliver;
        [(_patient getVariable "ACME_seizure_motionMode")=="full" && {count _capturedGestures==1},"initial convulsion missing"] call _check;
        _clock=120;CBA_missionTime=120;[_edge] call _deliver;
        [(_patient getVariable "ACME_seizure_motionMode")=="jerks","full movement survived twenty seconds"] call _check;
        [(_patient getVariable "ACME_lido_seizureState")=="active","cutoff treated the seizure"] call _check;
        [_gestureState=="GestureEmpty","old full gesture was not retired"] call _check;
        [_patient,false] call ACME_fnc_seizureArrestTrack;
        [(_patient getVariable "ACME_seizure_arrestStartedAt")==-1,"ROSC did not clear edge"] call _check;
    ''')


def late_jerk():
    return '''
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        _patient setVariable ["ACME_seizure_arrestStartedAt",70];
        [_patient,true] call ACME_fnc_seizureMotion;
        CBA_missionTime=100.15;_clock=100.15;[_jobs select 0] call _deliver;
        private _short=_jobs select ((count _jobs)-1);
        private _next=_jobs select ((count _jobs)-2);
    '''


def test_late_arrest_jerks_are_brief_randomized_and_cleanly_stop_without_base_pose_reset():
    execute(motor_setup()+late_jerk()+'''
        private _duration=_short select 2;
        [_duration>=0.04 && {_duration<=0.12},"jerk is not a brief snippet"] call _check;
        [(_next select 2)-_duration>=4 && {(_next select 2)-_duration<=10},"quiet interval outside bounds"] call _check;
        [count _capturedGestures==1,"jerk failed to start"] call _check;
        private _oldCount=count _jobs;
        [_patient,_gestureState] call ((_ehs select 0) select 1 select 1);
        [count _jobs==_oldCount,"GestureDone prematurely advanced timed jerk"] call _check;
        CBA_missionTime=CBA_missionTime+_duration;[_short] call _deliver;
        [_gestureState=="GestureEmpty" && {count _baseMoves==0},"jerk stop reset base or failed to clear gesture"] call _check;
        [_patient,true] call ACME_fnc_seizureMotion;
        [count _capturedGestures==2,"quiet interval was bypassed"] call _check;
        CBA_missionTime=100.15+(_next select 2);_clock=CBA_missionTime;[_next] call _deliver;
        [count _capturedGestures==3 && {(_capturedGestures select 0 select 0)!=(_capturedGestures select 2 select 0)},"next jerk missing or immediately repeated"] call _check;
    ''')


@pytest.mark.parametrize('change',['_patientLocal=false;','_patientAlive=false;','_patient setVariable ["ACME_clinicalEpoch",2];','_patient setVariable ["ACME_roc_paralyzed",true];','_parent=missionNamespace;'])
def test_delayed_jerk_never_restarts_after_owner_life_epoch_paralysis_or_vehicle_change(change):
    execute(motor_setup()+late_jerk()+change+'''
        [_short] call _deliver;private _count=count _capturedGestures;
        CBA_missionTime=110;_clock=110;[_next] call _deliver;
        [count _capturedGestures==_count,"retired jerk restarted"] call _check;
    ''')


def test_stale_pulse_stop_and_old_packet_cannot_clear_or_restart_successor():
    execute(motor_setup()+late_jerk()+'''
        private _old=_patient getVariable "ACME_seizure_motionSession";
        [_patient,false] call ACME_fnc_seizureMotion;
        [_patient,true] call ACME_fnc_seizureMotion;
        CBA_missionTime=101;_clock=101;[_jobs select ((count _jobs)-1)] call _deliver;
        private _current=_gestureState;private _count=count _capturedGestures;
        [_short] call _deliver;
        [_patient,_old,"",false] call ACME_fnc_seizureGestureSync;
        [_patient,_old,"ACME_SeizureSpasm4",true,1,0.2] call ACME_fnc_seizureGestureSync;
        [count _capturedGestures==_count && {_gestureState==_current},"old sequence interfered with successor"] call _check;
    ''')


@pytest.mark.parametrize('gesture,expected',[('',0),('GestureEmpty',0),('ACME_SeizureSpasm0',.82),('ACME_SeizureSpasm5',.82)])
def test_late_arrest_monitor_is_quiet_between_actual_jerks(gesture,expected):
    execute(ecg_setup()+f'''
        _serverTime=100;CBA_missionTime=100;_patientGesture="{gesture}";
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        _patient setVariable ["ACME_seizure_arrestStartedAt",70];
        _patient setVariable ["ACME_lido_seizureState","active"];
        [abs (([_patient] call ACME_fnc_ecgArtifactStrength)-{expected})<0.001,"quiet interval falsely convulsive"] call _check;
    ''')


@pytest.mark.parametrize('clinical',[False,True])
def test_head_elevation_log_resolves_the_real_acting_medic(clinical):
    execute('''
        private _logs=[];private _nameQueries=[];
        _patient setVariable ["ACME_headElevated",true];
        ace_common_fnc_getName={_nameQueries pushBack (_this select 0);if ((_this select 0) isEqualTo _medic) then {"M. Harlow"} else {"Casualty"}};
        ACME_fnc_headElevMedicSeq={};ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
    '''+'ACME_fnc_medLog={'+adapt(read('medLog'))+'};'+
    f'missionNamespace setVariable ["ACME_hc_descriptors",{str(clinical).lower()}];'+
    'ACME_test_elevate={'+adapt(read('headElevMedicStart')).replace('diag_tickTime','10')+'};'+'''
        [_medic,_patient] call ACME_test_elevate;
        [count _logs==1 && {((_logs select 0) select 3) isEqualTo ["M. Harlow"]},"elevation logged placeholder or casualty's name"] call _check;
        [_medic in _nameQueries,"provider identity never resolved"] call _check;
    ''')
