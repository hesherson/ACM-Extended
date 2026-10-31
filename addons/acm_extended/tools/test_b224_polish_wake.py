"""B224 production SQF state-machine tests. Engine animation/UI, config and network
boundaries are mocked explicitly. These tests do not establish native rendering."""
import itertools
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b223_interaction_flow import function


@pytest.mark.parametrize('direction',[-1,1])
@pytest.mark.parametrize('partial',range(1,6))
def test_scroll_can_close_same_corner_without_unlocking_it(direction,partial):
    execute(function('chestSealScrollStep')+f'''
        private _state=[0,0,false];private _actions=0;
        for "_i" from 1 to {partial} do {{
            private _r=(_state+[{direction}]) call ACME_fnc_chestSealScrollStep;
            _state=_r select [0,3]; if (_r select 3) then {{_actions=_actions+1;}};
        }};
        for "_i" from 1 to 15 do {{
            private _r=(_state+[{direction*-1}]) call ACME_fnc_chestSealScrollStep;
            _state=_r select [0,3]; [!(_r select 3),"closing generated burp"] call _check;
        }};
        [_state isEqualTo [0,{direction},false],"fully closed state unlocked or flipped corner"] call _check;
        private _r=(_state+[{direction}]) call ACME_fnc_chestSealScrollStep;
        [_r isEqualTo [1,{direction},false,false],"same corner did not reopen"] call _check;
    ''')


@pytest.mark.parametrize('direction',[-1,1])
def test_partial_reclosure_does_not_resubmit_burp_but_full_close_rearms(direction):
    execute(function('chestSealScrollStep')+f'''
        private _state=[5,{direction},true];
        for "_i" from 1 to 10 do {{
            _state=((_state+[{direction*-1}]) call ACME_fnc_chestSealScrollStep) select [0,3];
            private _r=(_state+[{direction}]) call ACME_fnc_chestSealScrollStep;
            [!(_r select 3),"partial fidget spammed completed burp"] call _check; _state=_r select [0,3];
        }};
        for "_i" from 1 to 5 do {{_state=((_state+[{direction*-1}]) call ACME_fnc_chestSealScrollStep) select [0,3];}};
        private _actions=0;
        for "_i" from 1 to 20 do {{
            private _r=(_state+[{direction}]) call ACME_fnc_chestSealScrollStep;_state=_r select [0,3];
            if (_r select 3) then {{_actions=_actions+1;}};
        }};
        [_actions==1,"new full cycle did not trigger exactly once"] call _check;
    ''')


@pytest.mark.parametrize('source',['facility','vehicle','portable','bogus'])
@pytest.mark.parametrize('facility,vehicle,tank',itertools.product([False,True],repeat=3))
def test_oxygen_action_uses_only_its_own_source(source,facility,vehicle,tank):
    expected={'facility':facility,'vehicle':vehicle,'portable':tank,'bogus':False}[source]
    execute(function('bvmOxygenSourceAllowed')+f'''
        ace_medical_treatment_fnc_isInMedicalFacility={{{str(facility).lower()}}};
        ace_medical_treatment_fnc_isInMedicalVehicle={{{str(vehicle).lower()}}};
        ACME_fnc_itemCount={{{int(tank)}}};
        [([_medic,_patient,"{source}"] call ACME_fnc_bvmOxygenSourceAllowed) isEqualTo {str(expected).lower()},"oxygen source leaked into different action"] call _check;
    ''')


@pytest.mark.parametrize('speed,seconds',[(-4.6,4.6),(-5,5),(0.2,5),(0.4,2.5),(0,0)])
def test_native_duration_uses_config_seconds_without_guessing_or_fitting(speed,seconds):
    s=read('nativeAnimationTime')
    s=re.sub(r'getNumber \(configFile[^;]*',str(speed),s)
    s=s.replace('finite _speed','(_speed isEqualType 0)')
    execute('private _native={'+adapt(s)+'};'+f'''[abs ((["native"] call _native)-{seconds})<0.000001,"native duration wrong"] call _check;''')


def test_xstat_is_exact_unarmed_medic1_with_rounded_native_time_and_normal_rate():
    s=(ROOT/'addons/acm_extended/config.cpp').read_text().split('class ACME_ApplyXStat: CheckPulse {')[1].split('\n    };')[0]
    assert 'animationMedic = "AinvPknlMstpSnonWnonDnon_medic1";' in s
    assert 'round (' in s and 'call ACME_fnc_nativeAnimationTime' in s
    assert 'ACME_normalSpeedAnimation = 1;' in s
    for p in ['addons/core/functions/fnc_treatmentNative.sqf','addons/core/overrides/fnc_treatment.sqf']:
        t=(ROOT/p).read_text()
        assert '"ACME_normalSpeedAnimation") > 0) then {1}' in t
    n=(ROOT/'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    assert '_isInZeus && {getNumber (_config >> "ACME_normalSpeedAnimation") == 0}' in n


@pytest.mark.parametrize('tbi,arms,torso',itertools.product([False,True],repeat=3))
@pytest.mark.parametrize('sample',[0,.4,.999999,1])
def test_injury_choice_uses_requested_clips_and_priority(tbi,arms,torso,sample):
    family='Head' if tbi else 'Arms' if arms else 'Body' if torso else 'Default'
    pools={'Head':['HeadA','HeadB','HeadC'],'Arms':['ArmsA','ArmsB','ArmsC'],'Body':['BodyA','BodyB'],'Default':['DefaultA','DefaultB','HeadC']}
    pool=pools[family];expected='ACME_Wake'+pool[min(int(sample*len(pool)),len(pool)-1)]
    b=lambda x:str(x).lower()
    execute(function('wakeAnimationChoice')+f'''[([{b(tbi)},{b(arms)},{b(torso)},{sample}] call ACME_fnc_wakeAnimationChoice)=="{expected}","wrong injury clip/priority"] call _check;''')


def wake_code(name):
    s=read(name).replace('objNull,[objNull]', 'objNull, [profileNamespace]')
    s=s.replace('createHashMap', 'parsingNamespace').replace('_tbiState getOrDefault', '_tbiState getVariable')
    for old,new in [
        ('local _patient','_localPatient'),('alive _patient','_patientAlive'),('objectParent _patient','_vehicle'),
        ('attachedTo _patient','_attached'),('getPosWorld _patient','_position'),
        ('animationState _patient','_animation'),('stance _patient','_stance'),('lifeState _patient','_life'),
        ('_patient distance2D (_record select 8)','_displacement'),('_patient getUnitMovesInfo 0','_progress'),
        ('inputAction _x','_inputValue'),('serverTime','CBA_missionTime'),
    ]:s=s.replace(old,new)
    s=re.sub(r'_patient playMoveNow ([^;]+);',r'_moves pushBack (\1);',s)
    s=s.replace('_patient switchMove [_move,0,0.25,false];','_fallback pushBack _move;')
    return 'ACME_fnc_'+name+'={'+adapt(s)+'};'


def wake_setup():
    return '''
        private _localPatient=true;private _vehicle=objNull;private _attached=objNull;
        private _position=[0,0,0];private _displacement=0;private _progress=0;private _inputValue=0;
        private _animation="acm_lyingstate";private _stance="PRONE";private _life="HEALTHY";
        private _duration=4;private _epoch=1;private _fallback=[];
        ACE_player=_patient;
        ACME_fnc_clinicalEpoch={_epoch};ACME_fnc_nativeAnimationTime={_duration};
        ACM_core_fnc_setLyingState={params ["_p","_v"];_p setVariable ["ACM_core_Lying_State",_v];};
        _patient setVariable ["ACM_core_Lying_State",true];
        private _frame={private _r=_patient getVariable ["ACME_wakeVisual",[]];if (_r isEqualTo []) exitWith {};
            private _id=_r select 7;[[_patient,_r select 0],_id] call ACME_fnc_wakeAnimationTick;};
        private _wake={[_patient,true] call ACME_fnc_wakeAnimationEvent;[_patient,false] call ACME_fnc_wakeAnimationEvent;};
        private _observe={call _frame;_animation=toLower ((_patient getVariable "ACME_wakeVisual") select 1);call _frame;};
    '''+function('wakeAnimationChoice')+''.join(wake_code(n) for n in ['wakeAnimationStop','wakeAnimationEvent','wakeAnimationTick'])


def test_wake_plays_once_then_returns_to_existing_lying_posture():
    execute(wake_setup()+'''
        call _wake;call _observe;
        [count _moves==1,"wake started more than once"] call _check;
        [_patient,false] call ACME_fnc_wakeAnimationEvent;
        [count _handlers==1,"duplicate wake event created second episode"] call _check;
        _progress=0.99;call _frame;
        [count _moves==2 && {(_moves select 1)=="ACM_LyingState"},"clip did not exit to normal posture"] call _check;
        [(_patient getVariable ["ACME_wakeVisual",[]]) isEqualTo [],"finished record retained"] call _check;
        [(_patient getVariable ["ACME_wakeVisualToken",[]]) isEqualTo [],"keeper token retained"] call _check;
        [_patient getVariable ["ACM_core_Lying_State",false],"visual consumed normal Get Up flag"] call _check;
        [!(_patient getVariable ["ACE_isUnconscious",false]),"visual re-induced unconsciousness"] call _check;
    ''')


@pytest.mark.parametrize('cause',[
    '_inputValue=1;', '_displacement=.5;', '_patient setVariable ["ACM_core_Lying_State",false];',
    '_patientAlive=false;', '_patient setVariable ["ACE_isUnconscious",true];', '_epoch=2;',
    '_localPatient=false;', '_vehicle=missionNamespace;', '_attached=missionNamespace;',
    '_patient setVariable ["ACME_patientAnimLock",["a","b","c",1,30]];',
    '_patient setVariable ["ACME_roc_paralyzed",true];',
    '_patient setVariable ["ACME_headElevated",true];',
])
def test_wake_interruptions_retire_without_clinical_or_pose_reassertion(cause):
    execute(wake_setup()+'''call _wake;call _observe;'''+cause+'''
        call _frame;private _n=count _moves;
        [(_patient getVariable ["ACME_wakeVisual",[]]) isEqualTo [],"interruption retained wake record"] call _check;
        [!((_handlers select 0) select 2),"interruption retained PFH"] call _check;
        [[_patient,1],0] call ACME_fnc_wakeAnimationTick;
        [count _moves==_n,"late callback reasserted wake or rest"] call _check;
        [_testAnimationSpeed==1,"visual modified global speed"] call _check;
    ''')


def test_old_wake_callback_cannot_cancel_or_change_new_episode():
    execute(wake_setup()+'''
        call _wake;call _observe;[_patient,true] call ACME_fnc_wakeAnimationEvent;
        _animation="acm_lyingstate";[_patient,false] call ACME_fnc_wakeAnimationEvent;call _observe;
        [[_patient,1],0] call ACME_fnc_wakeAnimationTick;
        [_patient,1,true] call ACME_fnc_wakeAnimationStop;
        [(_patient getVariable "ACME_wakeVisual" select 0)==2,"stale callback retired new wake"] call _check;
        [count _moves==2,"stale callback overwrote animation"] call _check;
    ''')


@pytest.mark.parametrize('block',['_duration=0;','_duration=50;','_vehicle=missionNamespace;',
    '_patient setVariable ["ACME_roc_paralyzed",true];','_patient setVariable ["ACE_isUnconscious",true];'])
def test_ineligible_wake_leaves_native_awake_path_alone(block):
    execute(wake_setup()+block+'''call _wake;[count _moves==0 && {count _handlers==0},"invalid clip seized patient"] call _check;''')


def test_wait_for_body_lease_is_bounded_and_never_delays_clinical_wake():
    execute(wake_setup()+'''
        _patient setVariable ["ACME_patientAnimLock",["x","x","x",1,50]];
        call _wake;call _frame;
        [count _moves==0 && {!(_patient getVariable ["ACE_isUnconscious",false])},"pending visual changed awake state"] call _check;
        CBA_missionTime=11.6;call _frame;
        [(_patient getVariable ["ACME_wakeVisual",[]]) isEqualTo [],"pending visual never timed out"] call _check;
        _patient setVariable ["ACME_patientAnimLock",[]];call _frame;
        [count _moves==0,"late lease release replayed abandoned wake"] call _check;
    ''')


def test_entry_fallback_runs_once_and_only_from_unchanged_rest():
    execute(wake_setup()+'''
        call _wake;call _frame;CBA_missionTime=10.3;call _frame;call _frame;
        [count _fallback==1,"entry fallback repeated"] call _check;
        CBA_missionTime=11.6;call _frame;
        [(_patient getVariable ["ACME_wakeVisual",[]]) isEqualTo [],"unobserved entry stuck"] call _check;
    ''')


def test_nonlying_wake_keeps_medical_lying_rest_and_clips_never_repeat():
    execute(wake_setup()+'''
        _patient setVariable ["ACM_core_Lying_State",false];call _wake;call _observe;
        private _r=_patient getVariable "ACME_wakeVisual";
        [(_r select 1) find "_Prone" < 0,"ordinary prone graph selected"] call _check;
        [(_r select 2)=="ACM_LyingState","medical rest lost"] call _check;
        _animation="acm_lyingstate";call _frame;
        [count _moves==1,"natural graph return replayed animation"] call _check;
    ''')


@pytest.mark.parametrize('history',['arms','tbi','torso'])
def test_injury_history_survives_treatment_during_unconscious_episode(history):
    prepare={'arms':'_patient setVariable ["ace_medical_fractures",[0,0,1,0,0,0]];',
             'tbi':'_patient setVariable ["ACME_tbi_HasTBI",true];',
             'torso':'_patient setVariable ["ace_medical_bodyPartDamage",[0,.8,0,0,0,0]];'}[history]
    family={'arms':'Arms','tbi':'Head','torso':'Body'}[history]
    execute(wake_setup()+prepare+f'''
        [_patient,true] call ACME_fnc_wakeAnimationEvent;
        _patient setVariable ["ace_medical_fractures",[0,0,0,0,0,0]];
        _patient setVariable ["ACME_tbi_HasTBI",false];
        _patient setVariable ["ace_medical_bodyPartDamage",[0,0,0,0,0,0]];
        [_patient,false] call ACME_fnc_wakeAnimationEvent;
        [((_patient getVariable "ACME_wakeVisual") select 1) find "ACME_Wake{family}"==0,"treated injury history lost"] call _check;
    ''')


def test_native_hooks_include_early_get_up_and_no_speed_or_input_freeze():
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    for fam,letters in [('Default','AB'),('Body','AB'),('Arms','ABC'),('Head','ABC')]:
        for l in letters:
            block=cfg.split(f'class ACME_Wake{fam}{l}: UnconsciousRevive{fam}_{l} {{')[1].split('};',1)[0]
            assert 'looped = 0;' in block and 'minPlayTime = 0;' in block
    getup=(ROOT/'addons/core/functions/fnc_getUp.sqf').read_text()
    assert getup.index('call ACME_fnc_wakeAnimationStop') < getup.index('setVariable ["ACM_core_Lying_State", false')
    assert '_patient switchMove [_roll,0,0.25,false];' in getup
    assert 'call ACME_fnc_wakeAnimationEvent' in (ROOT/'addons/core/functions/fnc_onUnconscious.sqf').read_text()
    assert 'ACME_wakeVisualToken' in (ROOT/'addons/mission/functions/fnc_trainingPatientHoldTick.sqf').read_text()
    for n in ['wakeAnimationEvent','wakeAnimationTick','wakeAnimationStop']:
        s=read(n)
        assert 'disableUserInput' not in s and 'setUnconscious' not in s and 'setAnimSpeedCoef' not in s


@pytest.mark.parametrize('requested', [0, 1])
@pytest.mark.parametrize('sharing', [0, 1, 2, 3])
def test_explicit_suction_action_uses_selected_device_when_both_are_carried(requested, sharing):
    from test_b156_procedure_supplies import suction_setup
    execute(suction_setup()+f'''
        ace_medical_treatment_allowSharedEquipment={sharing};
        _medic setVariable ["fixtureStock",["ACM_SuctionBag","ACM_ACCUVAC"]];
        uiNamespace setVariable ["ACME_suction_standalone",true];
        uiNamespace setVariable ["ACME_suction_requestedType",{requested}];
        [([true] call ACME_fnc_suctionSelectDevice)=={requested},"standalone device selection was overridden"] call _check;
        [count _debits==0,"selection prematurely spent a device"] call _check;
    ''')


@pytest.mark.parametrize('requested,other', [(0,'ACM_ACCUVAC'),(1,'ACM_SuctionBag')])
def test_missing_requested_suction_device_never_silently_substitutes_other(requested,other):
    from test_b156_procedure_supplies import suction_setup
    execute(suction_setup()+f'''
        _medic setVariable ["fixtureStock",["{other}"]];
        uiNamespace setVariable ["ACME_suction_standalone",true];
        uiNamespace setVariable ["ACME_suction_requestedType",{requested}];
        [([true] call ACME_fnc_suctionSelectDevice)==-1,"lost selected device silently substituted another"] call _check;
        [count _debits==0,"rejected device selection consumed inventory"] call _check;
    ''')


def test_manual_bag_stays_manual_after_first_squeeze_with_accuvac_still_carried():
    from test_b156_procedure_supplies import suction_setup
    execute(suction_setup()+'''
        _medic setVariable ["fixtureStock",["ACM_SuctionBag","ACM_ACCUVAC"]];
        uiNamespace setVariable ["ACME_suction_standalone",true];
        uiNamespace setVariable ["ACME_suction_requestedType",0];
        [true] call ACME_fnc_suctionSelectDevice;
        ["squeeze"] call ACME_fnc_suctionBulb;
        [([true] call ACME_fnc_suctionSelectDevice)==0,"spent session bag changed to powered suction"] call _check;
        uiNamespace setVariable ["ACME_suction_sqT0",-1];
        ["squeeze"] call ACME_fnc_suctionBulb;
        [count _debits==1 && {count _drained==2},"bag was spent twice or stopped after first squeeze"] call _check;
        [([_medic,"ACM_ACCUVAC"] call ace_common_fnc_getCountOfItem)==1,"manual suction consumed ACCUVAC"] call _check;
    ''')


@pytest.mark.parametrize('manual', [True,False])
def test_scope_without_automatic_carrier_removal_uses_plain_clean_exit(manual):
    from test_bounded_stethoscope_exit_generation import setup as scope_setup
    state='_patient setVariable ["ACME_manualPlateCarrierState","off"];' if manual else '_patient setVariable ["ACME_chestAccess_vestLoadout",[]];'
    execute(scope_setup()+state+'''
        [_display] call _close;
        [count _lower==0,"ordinary scope close inserted carrier reaching animation"] call _check;
        [_stops isEqualTo [[_medic,"stethoscope",5,false]],"ordinary scope pose not released cleanly"] call _check;
        [!ACM_core_ContinuousAction_Active && {_speed==1},"ordinary scope left action/animation frozen"] call _check;
    ''')


def test_scope_cancel_leaves_live_display_exit_to_unload_instead_of_handoff_only_stop():
    s=read('beginStethoscopeAction')
    assert 'if (_poseEpoch >= 0 && {isNull _scopeDisplay}) then' in s
    assert '[_medic, "stethoscope", _poseEpoch, false] call ACME_fnc_treatmentPoseStop;' in s


def test_wake_histories_are_persisted_but_runtime_callbacks_are_not():
    s=read('clinicalFields')
    for field in ['ACME_wakeHadArmFracture','ACME_wakeHadTBI','ACME_wakeHadTorsoDamage','ACME_wakeVisualArmed']:
        assert f'["{field}", "", true, true]' in s
    for field in ['ACME_wakeVisual','ACME_wakeVisualToken','ACME_wakeVisualSerial']:
        assert f'["{field}", "", true, false]' in s
