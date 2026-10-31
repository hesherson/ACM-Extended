"""Execute changed timings, class grouping, parked geometry and seizure selection.

Each interpreter executes production SQF with documented engine/UI boundaries.
These tests cannot verify the rendered skeleton, physical clipping or real MP transport.
"""
from functools import lru_cache
import math
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, read, ROOT
from test_b211_direct_pressure_inputs import setup as dp_setup
from test_b212_assessment_sequence import setup as assessment_setup
from test_b215_recovery_position import setup as recovery_setup, begin
from test_b206_seizure_gesture_locality_execution import setup as sync_setup
from test_historical_menu_execution import menu_setup as _menu_setup, section_setup as _section_setup

menu_setup=lru_cache(maxsize=1)(_menu_setup)
section_setup=lru_cache(maxsize=1)(_section_setup)

@pytest.mark.parametrize('elapsed',[0,.1,1,1.99,1.999,2,2.001,3])
def test_pressure_reentry_has_two_second_quiet_boundary(elapsed):
    execute(dp_setup()+'''
        ["leftarm"] call _start; _animation="acme_directpressurehold";
        _inputActions=["MoveForward"]; call _pressTick;
        private _claim=_medic getVariable "ACME_DP_ClaimToken";
        _inputActions=[]; call _finishPressureExit;
        private _quietAt=_medic getVariable "ACME_DP_IdleStart";
        _animation="amovpknlmstpsnonwnondnon";
    '''+f'''
        CBA_missionTime=_quietAt+{elapsed}; call _pressTick;
        [(_medic getVariable ["ACME_DP_InPose",false]) isEqualTo {str(elapsed>=2).lower()},"two-second boundary wrong"] call _check;
        [(_medic getVariable ["ACME_DP_ClaimToken",""])==_claim,"pause replaced clinical session"] call _check;
    ''')


def test_pressure_repeated_movement_restarts_pause_and_first_application_is_immediate():
    execute(dp_setup()+'''
        ["body"] call _start;
        [_medic getVariable ["ACME_DP_InPose",false],"first application acquired unwanted delay"] call _check;
        _animation="acme_directpressurehold"; _inputActions=["MoveForward"]; call _pressTick;
        _inputActions=[]; call _finishPressureExit; _animation="amovpknlmstpsnonwnondnon";
        CBA_missionTime=11.8; _inputActions=["MoveRight"]; call _pressTick;
        _inputActions=[]; CBA_missionTime=13.79; call _pressTick;
        [!(_medic getVariable ["ACME_DP_InPose",true]),"renewed motion did not restart pause"] call _check;
        CBA_missionTime=13.8; call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"renewed pause never completed"] call _check;
    ''')

@pytest.mark.parametrize('action',['CheckBreathing','CheckAirway'])
def test_assessment_progress_starts_during_entry_without_duplicated_launcher(action):
    execute(assessment_setup()+f'_request set [3,"{action}"];'+'''
        _request call ACME_fnc_assessmentStart;
        [count _nativeCalls==1 && {(_medic getVariable "ACME_assessment" select 2)==0},"timer did not include entry"] call _check;
        [[_nativeArgs] call ACME_fnc_assessmentProgress,"entry was treated as progress failure"] call _check;
        CBA_missionTime=11.5; call _ready; call _frame;
        [count _nativeCalls==1,"timer restarted at work"] call _check;
    ''')

@pytest.mark.parametrize('entered',[True,False])
def test_breathing_completion_counts_entry_but_never_credits_missing_work(entered):
    execute(assessment_setup()+'''_request set [3,"CheckBreathing"]; _request call ACME_fnc_assessmentStart;
        CBA_missionTime=11.8;
    '''+('call _ready;' if entered else '')+f'''
        private _end=[_nativeArgs,2,2,2] call ACME_fnc_assessmentCompletion;
        [_end=={3},"nominal deadline did not include entry or credited missing work"] call _check;
    ''')

@pytest.mark.parametrize('elapsed',[0,1,2,2.999,3,4,5])
def test_recovery_only_begins_in_last_two_seconds(elapsed):
    execute(recovery_setup()+'''
        private _args=[_medic,_patient,"Head","RecoveryPosition"];
        _args call ACME_fnc_recoveryPositionStart;
        (_medic getVariable "ACME_treatmentPoseState") set [3,1];
        _providerAnim="ainvpknlmstpsnonwnondnon_medic4";
    '''+f'''
        [_args,{elapsed},5] call ACME_fnc_recoveryPositionProgress;
        [count _handlers=={int(elapsed>=1.5)},"recovery did not use late blend window"] call _check;
    ''')

@pytest.mark.parametrize('blend',[0,.2,.6,.98,.99,1])
def test_recovery_requires_observed_engine_blend_and_real_settle_time(blend):
    execute(recovery_setup()+begin()+'''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
    '''+f'''
        _serverClock=12.1; _moveBlend={blend}; call _run;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]) isEqualTo {str(blend>=.99).lower()},"engine blending falsely committed recovery"] call _check;
    ''')

CHEST=['UseStethoscope','ACME_InspectChest','ACME_ApplyChestSeal','ACME_PerformNARSPEAR',
       'ACME_PerformThoracostomy','ACME_AdjustThoracostomy','ACME_InsertChestTube',
       'ACME_DrainFluid_ACCUVAC','ACME_DrainFluid_SuctionBag','ACME_ReSealChestTube',
       'ACME_CloseIncision','ACME_SutureChestTube']
@pytest.mark.parametrize('name',CHEST)
def test_chest_actions_route_to_breathing_before_inherited_airway_suction(name):
    execute(menu_setup()+f'''
        private _c=["{name}","airway",["SuctionBag","airway",[],"Suction"],"Translated name"];
        [([_c] call ACME_fnc_menuActionInfo) isEqualTo ["airway","ventilation",false],"chest action not in Breathing"] call _check;
    ''')

@pytest.mark.parametrize('part',[0,1])
@pytest.mark.parametrize('view',['flat','closed','open'])
@pytest.mark.parametrize('tab',['examine','airway','advanced','medication'])
def test_own_bvm_emma_is_pinned_immediately_below_carrier(part,view,tab):
    code=section_setup()+'ACME_fnc_debugEnabled={false};'+read('initMedicalMenuConfig')+f'''
        _bodyPart={part}; ace_medical_gui_selectedBodyPart=_bodyPart;
        _selectedCategory="{tab}"; _nestEnabled={str(view!='flat').lower()};
        missionNamespace setVariable ["ace_medical_gui_actions",[]]; _configList=[];
        ["RecoveryPosition","airway"] call _add;
        ["ACME_InspectChest","airway"] call _add;
        ["ACME_AttachEMMA","airway"] call _add;
        ["ACME_ManualRemovePlateCarrier","advanced"] call _add;
        call _collect;
    '''
    if view=='open': code+='_display setVariable ["ACME_menuOpen",["adjuncts","ventilation","capno"]];'
    if part != 0:
        code+='''
            private _rows=call _render;
            [(_rows findIf {(_x param [8,""])=="ACME_AttachEMMA"})<0,"off-head EMMA row retained"] call _check;
            [(_rows select 0 select 8)=="ACME_ManualRemovePlateCarrier","carrier pin lost"] call _check;
        '''
        execute(code)
        return
    code+='''
        private _rows=call _render;
        [(_rows select 0 select 8)=="ACME_ManualRemovePlateCarrier" && {(_rows select 1 select 8)=="ACME_AttachEMMA"},"pin order changed"] call _check;
        [(_rows select 1 select 1)==_selectedCategory && {(_rows select 1 select 9)==""},"EMMA captured by category/dropdown"] call _check;
        [(_rows findIf {(_x param [7,""])=="chest"})<0,"retired Chest header present"] call _check;
        private _emma=_rows select 1; ["unchanged"] call (_emma select 3);
        [_callbacks isEqualTo [["unchanged"]],"pinned native callback changed"] call _check;
    '''
    execute(code)

@pytest.mark.parametrize('name',['RecoveryPosition','CancelRecoveryPosition'])
def test_recovery_is_airway_not_positioning(name):
    execute(menu_setup()+f'''private _c=["{name}","airway",[],"Translated"];
        [([_c] call ACME_fnc_menuActionInfo) isEqualTo ["airway","adjuncts",false],"recovery not Airway"] call _check;''')

@pytest.mark.parametrize('angle',[0,45,90,135,180,270])
@pytest.mark.parametrize('missing_shoulders',[False,True])
def test_carrier_park_uses_patient_left_at_any_heading(angle,missing_shoulders):
    a=math.radians(angle); axis=[math.sin(a),math.cos(a),0]; left=[-axis[1],axis[0],0]
    head=[10+axis[0],20+axis[1],.3]; pelvis=[10,20,.3]
    ls=[head[i]+left[i]*.2 for i in range(3)]; rs=[head[i]-left[i]*.2 for i in range(3)]
    if missing_shoulders: ls=rs=head
    raw=read('carrierParkTarget')
    for key,val in [('pelvis',pelvis),('head',head),('leftshoulder',ls),('rightshoulder',rs)]:
        raw=raw.replace(f'_patient modelToWorldVisual (_patient selectionPosition "{key}")',str(val))
    raw=raw.replace('getDir _patient',str(angle)).replace('surfaceNormal [_pos select 0, _pos select 1]','[0,0,1]')
    expected=[head[0]+axis[0]*.45+left[0]*.75,head[1]+axis[1]*.45+left[1]*.75,.02]
    execute('private _park={'+adapt(raw)+'};'+f'''
        private _result=[_patient] call _park;
        [((_result select 0) distance {expected})<0.0001,"carrier not 0.75m anatomically left"] call _check;
        [(_result select 2) isEqualTo [0,0,1],"ground orientation lost"] call _check;
    ''')


def test_random_seizures_use_only_requested_four_without_immediate_repeat():
    raw=read('seizureGestureAdvance').replace('isAwake _patient','true').replace('serverTime','CBA_missionTime')
    raw=re.sub(r'_patient switchMove [^;]+;','',raw)
    execute('''
        private _session=[0,7,1]; private _recordedGestures=[];
        _patient setVariable ["ACME_seizure_motionSession",_session];
        _patient setVariable ["ACME_seizure_motionActive",true];
        ACME_fnc_clinicalEpoch={0}; ace_common_fnc_isBeingDragged={false}; ace_common_fnc_isBeingCarried={false};
        ACM_core_fnc_cprActive={false};
        CBA_fnc_globalEvent={_recordedGestures pushBack (_this select 1 select 2);};
    '''+'ACME_fnc_seizureMotorMode={'+adapt(read('seizureMotorMode'))+'};'+'private _advance={'+adapt(raw)+'};'+'''
        for "_i" from 1 to 120 do {[_patient,_session] call _advance;};
        [count _recordedGestures==120,"gesture sequencer did not run"] call _check;
        private _allowed=["ACME_SeizureSpasm0","ACME_SeizureSpasm4","ACME_SeizureSpasm5","ACME_SeizureSpasm6"];
        [(_recordedGestures findIf {!(_x in _allowed)})<0,"retired/unrequested seizure selected"] call _check;
        {[_x in _recordedGestures,"random cycle omitted a requested gesture"] call _check;} forEach _allowed;
        for "_i" from 1 to 119 do {[(_recordedGestures select _i)!=(_recordedGestures select (_i-1)),"gesture repeated immediately"] call _check;};
    ''')

@pytest.mark.parametrize('gesture',['ACME_SeizureSpasm3','GestureSpasm3','GestureSpasm1','Unknown'])
def test_observers_reject_retired_gesture_packets(gesture):
    execute(sync_setup()+f'''
        [!([_patient,_validSession,"{gesture}",true] call _sync),"retired packet accepted"] call _check;
        [count _played==0,"retired packet rendered"] call _check;
    ''')


def test_config_and_park_callers_share_the_new_contracts():
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    block=cfg.split('class RecoveryPosition: CheckAirway {',1)[1].split('\n    };',1)[0]
    assert 'treatmentTime = 5;' in block and 'allowedSelections[] = {"Head", "Body"};' in block
    assert 'interpolationSpeed = 0.5;' in (ROOT/'addons/airway/CfgMoves.hpp').read_text()
    assert '"chest", "Chest"' not in read('initMedicalMenuConfig')
    for name in ('chestAccessVestPark','chestSealParkCarrier'):
        text=read(name)
        assert 'call ACME_fnc_carrierParkTarget' in text and 'ACME_chestFixedPark' in text
