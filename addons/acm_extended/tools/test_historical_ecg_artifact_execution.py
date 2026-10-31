"""Batch 7: actual motion-artifact producers, readers and native ECG buffers.

Engine object/clock/transport boundaries are explicit fixtures. Unsupported array
resize-with-fill and triangular random use equivalent size/fill and modal draws;
random distribution, audible beeps and rendered monitor geometry are not certified.
"""
import re
import pytest
from source_scan import lex, matching
from historical_source import source_bundle
from test_menu_death_lifecycle import ROOT, execute
from test_historical_cardiac_execution import code as cardiac_code, setup as cardiac_setup

F=ROOT/'addons/acm_extended/functions'
C=ROOT/'addons/circulation/functions'


def engine_code(text):
    text=text.replace('gestureState _patient','_patientGesture').replace('animationState _patient','_patientAnimation').replace('_patient getUnitMovesInfo 3','_patientBlend').replace('getAnimSpeedCoef _patient','_patientRate').replace('vectorMagnitude velocity _patient','_patientSpeed')
    text=text.replace('serverTime','_serverTime').replace('netId _medic','"provider"')
    # SQF-VM lacks resize [size,fill] and triangular random. Preserve every
    # production argument; mock only these engine primitive boundaries.
    ts=lex(text);pairs=matching(ts);edits=[]
    for i,t in enumerate(ts[:-1]):
        if t.kind!='ident' or t.value not in ('resize','random') or ts[i+1].value!='[':continue
        assert i+1 in pairs
        end=pairs[i+1];arg=text[ts[i+1].offset:ts[end].offset+1]
        if t.value=='resize':
            assert ts[i-1].kind=='ident'
            edits.append((ts[i-1].offset,ts[end].offset+1,'['+ts[i-1].value+','+arg+'] call _resizeFill'))
        else:edits.append((t.offset,ts[end].offset+1,'('+arg+' select 1)'))
    for a,b,new in reversed(edits):text=text[:a]+new+text[b:]
    return cardiac_code(text).replace('objNull,[objNull]', 'objNull,[profileNamespace]')


def function(name):return 'ACME_fnc_'+name+'={'+engine_code((F/('fn_'+name+'.sqf')).read_text())+'};\n'


def setup():
    return cardiac_setup()+'''
        private _serverTime=10; private _patientGesture="";
        private _patientAnimation="acm_lyingstate"; private _patientBlend=1; private _patientRate=1; private _patientSpeed=0;
        private _resizeFill={params ["_a","_args"];_args params ["_size","_fill"];
            private _old=count _a; _a resize _size;
            for "_n" from _old to (_size-1) do {_a set [_n,_fill];};
        };
        private _eventsByName=createHashMap;
        CBA_fnc_addEventHandler={_eventsByName set [_this select 0,_this select 1];};
        ACME_fnc_ownerDispatch={_events pushBack _this;
            if ((_this select 1)=="ecgJostle") then {(_this select 2) call ACME_fnc_ecgJostleLocal;};};
        ACME_fnc_ownerRegister={};
        ace_common_fnc_getCountOfItem={1};
        ACME_fnc_treatmentSupplyCount={1}; // supply availability is external to the artifact reader
    '''+''.join(function(n) for n in ('seizureMotorMode','ecgJostleLocal','ecgJostleRequest','ecgMotionStrength','ecgArtifactStrength','ecgArtifactApply','suctionStateLocal'))


@pytest.mark.parametrize('epoch',[1,9,20])
@pytest.mark.parametrize('mode,device',[('hand',1),('salad',1),('manual',0)])
def test_suction_artifact_uses_session_expiry_not_clinical_epoch(epoch,mode,device):
    # Use the real suction writer to produce the eight-field row. Do not invent
    # a reduced fixture that could hide an index/schema mismatch.
    writer=function('suctionStateLocal').replace('(_proof param [0, objNull]) == _patient','(_proof param [0, objNull]) isEqualTo _patient')
    execute(setup()+writer+f'_patient setVariable ["ACME_clinicalEpoch",{epoch}];'+'''
        _medic setVariable ["ACME_suctionManualSession",[_patient,"suction"]];
    '''+f'[_patient,_medic,{epoch},"suction",1,"{mode}",[0.3,0.4],{device}] call ACME_fnc_suctionStateLocal;'+'''
        private _sessions=+(_patient getVariable ["ACME_suctionSessions",[]]);
        [count _sessions==1 && {((_sessions select 0) select 2)==11.5},"real producer did not create session"] call _check;
        private _s=[_patient] call ACME_fnc_ecgArtifactStrength;
        [abs (_s-0.42)<0.00001,"active suction artifact missing"] call _check;
        CBA_missionTime=11.5;_serverTime=11.5;
        [([_patient] call ACME_fnc_ecgArtifactStrength)==0,"expired suction artifact survived"] call _check;
        [(_patient getVariable ["ACME_suctionSessions",[]]) isEqualTo _sessions,"visual reader mutated suction state"] call _check;
    ''')


@pytest.mark.parametrize('ending',['ace_treatmentSucceded','ace_treatmentFailed'])
def test_timed_treatments_publish_and_release_only_their_own_artifact_lease(ending):
    execute(setup()+engine_code((F/'fn_registerEcgJostleRuntime.sqf').read_text())+'''
        [_medic,_patient,"leftarm","FieldDressing"] call (_eventsByName get "ace_treatmentStarted");
        [_medic,_patient,"leftarm","FieldDressing"] call (_eventsByName get "ace_treatmentStarted");
        [count (_patient getVariable ["ACME_ecgJostleLeases",[]])==1,"duplicate start stacked lease"] call _check;
        [_medic,_patient,"rightleg","FieldDressing"] call (_eventsByName get "ace_treatmentStarted");
        [abs (([_patient] call ACME_fnc_ecgArtifactStrength)-0.58)<0.00001,"two independent leases lost"] call _check;
    '''+f'[_medic,_patient,"leftarm","FieldDressing"] call (_eventsByName get "{ending}");'+'''
        [count (_patient getVariable ["ACME_ecgJostleLeases",[]])==1,"stop removed another lease"] call _check;
        [abs (([_patient] call ACME_fnc_ecgArtifactStrength)-0.48)<0.00001,"surviving procedure artifact lost"] call _check;
        CBA_missionTime=191;
        [([_patient] call ACME_fnc_ecgArtifactStrength)==0,"interrupted lease never expired"] call _check;
    ''')


@pytest.mark.parametrize('change,expected',[
    ('',0.62),('_medic setVariable ["ACME_DP_Paused",true];',0),
    ('_medic setVariable ["ACME_DP_Patient",missionNamespace];',0),
    ('_medic setVariable ["ACME_DP_Part","rightleg"];',0),
    ('_medic setVariable ["ACME_DP_Active",false];',0),('_alive=false;',0)])
def test_direct_pressure_artifact_follows_active_matching_provider_only(change,expected):
    execute(setup()+'''
        _patient setVariable ["ACME_DP_press_leftarm",_medic];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Part","leftarm"];
    '''+change+f'[([_patient] call ACME_fnc_ecgArtifactStrength)=={expected},"invalid DP artifact"] call _check;')


@pytest.mark.parametrize('age,expected',[(0,0.3),(1.19,0.3),(1.2,0),(2,0)])
def test_recent_bagging_artifact_uses_shared_breath_clock(age,expected):
    execute(setup()+f'_serverTime={age}; _patient setVariable ["ACME_bvm_lastBreathServer",0];'+
            f'[([_patient] call ACME_fnc_ecgArtifactStrength)=={expected},"bagging window mismatch"] call _check;')


def test_artifact_buffer_preserves_inputs_physiology_and_existing_unsafe_columns():
    execute(setup()+'''
        [_patient,"test",true] call ACME_fnc_ecgJostleLocal;
        private _arr=[];_arr resize 176;_arr=_arr apply {0};
        private _safe=[];_safe resize 176;_safe=_safe apply {true}; _safe set [0,false];
        private _before=+_arr;private _maskBefore=+_safe;
        private _out=[_patient,_arr,_safe] call ACME_fnc_ecgArtifactApply;
        _out params ["_wave","_mask"];
        [count _wave==176 && {count _mask==176},"artifact resized window"] call _check;
        [_arr isEqualTo _before && {_safe isEqualTo _maskBefore},"artifact changed caller-owned buffers"] call _check;
        [!(_wave isEqualTo _arr) && {!(_mask select 0)},"artifact missing or unsafe column promoted"] call _check;
        [(_mask findIf {!_x})>=0,"no contaminated columns masked"] call _check;
        [(_wave findIf {abs _x>30})<0,"artifact exceeded configured envelope"] call _check;
        [(_patient getVariable ["ace_medical_heartRate",0])==80 && {(_patient getVariable ["ace_medical_bloodVolume",0])==6},"artifact changed physiology"] call _check;
    ''')


def generator_setup():
    body=(C/'fnc_displayAEDMonitor_generateEKG.sqf').read_text()
    return setup()+function('peaIsWide')+'''
        private _electrical=80;
        ACM_circulation_fnc_getEKGHeartRate={_electrical};
        ACME_fnc_rhythmGet={0};
        missionNamespace setVariable ["ACM_circulation_AED_Monitor_Target",_patient];
        _patient setVariable ["ACME_AED_MonitorCursorTime",10];
        _patient setVariable ["ACM_circulation_AED_Pads_LastBeep",10];
        _patient setVariable ["ACM_circulation_AED_UpdateStep",0];
        _patient setVariable ["ACME_AED_PreviousRR",0.75];
        _patient setVariable ["ACME_AED_NextRR",0.75];
    '''+'ACM_circulation_fnc_displayAEDMonitor_generateEKG={'+engine_code(body)+'};'


@pytest.mark.parametrize('rhythm',[0,1,2,3,4,5,104])
def test_native_and_custom_generator_paths_apply_same_artifact_boundary(rhythm):
    execute(generator_setup()+'''
        private _applied=0;
        private _realApply=ACME_fnc_ecgArtifactApply;
        ACME_fnc_ecgArtifactApply={_applied=_applied+1;_this call _realApply};
        ACME_fnc_genRhythmEKG={private _a=[];private _s=[];[_a,[176,0]] call _resizeFill;[_s,[176,true]] call _resizeFill;[_a,_s]};
        [_patient,"test",true] call ACME_fnc_ecgJostleLocal;
    '''+f'private _out=[{rhythm},15,0] call ACM_circulation_fnc_displayAEDMonitor_generateEKG;'+'''
        [_applied==1 && {count (_out select 0)==176} && {count (_out select 1)==176},"generator missed/doubled shared artifact"] call _check;
    ''')


@pytest.mark.parametrize('blood,calcium,wide',[(0,0,False),(2,0,False),(2.1,0,True),(2.1,0.1,False),(3,1,False),(3,0.5,True)])
def test_pea_subtype_changes_morphology_without_changing_rhythm_or_circulation(blood,calcium,wide):
    execute(generator_setup()+f'_patient setVariable ["ACM_circulation_TransfusedBlood_Volume",{blood}]; _patient setVariable ["ACM_circulation_Calcium_Count",{calcium}];'+'''
        _patient setVariable ["ace_medical_inCardiacArrest",true];
        _patient setVariable ["ACM_circulation_Cardiac_RhythmState",5];
        private _sinus=[0,15,0] call ACM_circulation_fnc_displayAEDMonitor_generateEKG;
        private _pea=[5,15,0] call ACM_circulation_fnc_displayAEDMonitor_generateEKG;
    '''+f'[([_patient] call ACME_fnc_peaIsWide) isEqualTo {str(wide).lower()},"wrong current subtype boundary"] call _check;'+
        f'[((_pea select 1) isEqualTo (_sinus select 1)) isEqualTo {str(not wide).lower()},"narrow/wide morphology mask mismatch"] call _check;'+'''
        [_patient getVariable ["ace_medical_inCardiacArrest",false],"morphology restored perfusion"] call _check;
        [(_patient getVariable ["ACM_circulation_Cardiac_RhythmState",0])==5,"morphology changed native PEA"] call _check;
    ''')


def test_megacode_routes_both_ecg_windows_through_native_generator():
    text=(F/'fn_megacodePanelTick.sqf').read_text()
    assert text.count('call ACM_circulation_fnc_displayAEDMonitor_generateEKG')==2
    assert 'ACME_fnc_ecgArtifactApply' not in text and 'ACME_fnc_ecgArtifactStrength' not in text
    # No separate Kelly artifact generator should be reinstated: native buffers
    # already traverse the tested artifact function above.
    start=text.index('private _panelHR =');end=text.index('private _displayEtCO2',start)
    body=text[start:end].replace('private _dummy','private _unusedDummy')
    execute(setup()+'''
        private _dummy=_patient;private _arrest=true;private _nativeRhythm=5;private _ekgHR=92;private _cpr=false;
        ACM_circulation_fnc_hasPulse={false};
    '''+engine_code(body)+'''
        [_displayHR==92 && {_displaySpO2==0} && {_displayBP=="--/--"},"PEA display inferred mechanical perfusion"] call _check;
        [_sbp==0 && {_dbp==0},"PEA panel retained pressure"] call _check;
    ''')


def test_minigame_artifact_start_and_close_use_matching_keys_at_current_entry_modules():
    for opened,closed,key in [('ivMinigameInit','ivMinigameClose','ui:iv:'),('chestSealInit','chestSealClose','ui:chest:'),
                             ('thoraInit','thoraClose','ui:thora:'),('laryngoInit','laryngoClose','ui:laryngo:')]:
        a=(F/('fn_'+opened+'.sqf')).read_text();b=(F/('fn_'+closed+'.sqf')).read_text()
        for text in (a,b):assert '"'+key+'"' in text and 'call ACME_fnc_ecgJostleRequest' in text
    calls=[p.name for p,t in source_bundle(F/'fn_postInit.sqf')]
    assert calls.count('fn_registerEcgJostleRuntime.sqf')==1


@pytest.mark.parametrize('rate,pressure,recovered',[(80,[80,120],True),(46,[61,90],True),
                                                   (45,[80,120],False),(210,[80,120],False),(80,[45,65],False)])
def test_native_critical_vitals_owns_recovery_without_an_extended_vt_timer(rate,pressure,recovered):
    text=(ROOT/'addons/core/functions/fnc_handleCriticalVitals.sqf').read_text()
    text=text.replace('GET_HEART_RATE(_patient)','(_patient getVariable ["ace_medical_heartRate",80])')
    text=text.replace('IS_UNCONSCIOUS(_patient)','(_patient getVariable ["ACE_isUnconscious",false])')
    macro=(ROOT/'addons/main/script_macros.hpp').read_text()
    assert '#define GET_MAP(systolic,diastolic) (diastolic + ((systolic - diastolic) / 3))' in macro
    text=text.replace('GET_MAP(_BPSystolic,_BPDiastolic)','(_BPDiastolic + ((_BPSystolic-_BPDiastolic)/3))')
    constants=''.join(name+'='+value+';' for name,value in re.findall(r'^#define\s+(ACM_Rhythm_\w+)\s+(-?\d+)\b',macro,re.M))
    execute(cardiac_setup()+constants+f'_pressure={pressure};_patient setVariable ["ace_medical_heartRate",{rate}];'+'''
        _patient setVariable ["ACM_circulation_Cardiac_RhythmState",4];
        private _critical={'''+cardiac_code(text,'core')+'''};
        [_patient] call _critical;
        private _id=_patient getVariable ["ACM_core_CriticalVitals_PFH",-1];
        private _job=_handlers select _id;
        [_job select 1,_id] call (_job select 0);
    '''+f'[(_patient getVariable ["ACM_circulation_Cardiac_RhythmState",-1])=={0 if recovered else 4},"native recovery boundary changed"] call _check;'+
        f'[(_patient getVariable ["ACM_core_CriticalVitals_State",false]) isEqualTo {str(not recovered).lower()},"wrong native critical-state lifetime"] call _check;')
