"""Execute B219 world-inventory, marked-AI and death handoff source.
Native UI, animation, physics, AI commands and locality are recorded engine boundaries.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b219_revision import binary_array, motor_setup, late_jerk


def commands(source, names):
    for command in names:
        source=re.sub(r'(_\w+) '+command+r' ([^;]+);',
                      lambda m:'_engineCalls pushBack ["'+command+'",'+m[2]+'];',source)
    return source


def training_setup():
    out='''
        private _patientLocal=true;private _isPlayer=false;private _parent=objNull;private _attached=objNull;
        private _dragged=false;private _carried=false;private _clock=100;private _engineStance="STAND";
        private _trainingAnimation="amovpercmstpsnonwnondnon";
        private _engineCalls=[];private _enabledFeatures=["MOVE","PATH","TARGET","AUTOTARGET","FSM"];
        private _engineUnitPos="AUTO";private _engineBehaviour="AWARE";private _engineCombat="YELLOW";
        ace_common_fnc_isPlayer={_isPlayer};ace_common_fnc_isBeingDragged={_dragged};ace_common_fnc_isBeingCarried={_carried};
        _patient setVariable ["ACME_trainingCrouchOnly",true];CBA_missionTime=100;
    '''
    for name in ['trainingPatientHoldTick','trainingPatientHold']:
        s=(ROOT/'addons/mission/functions'/f'fnc_{name}.sqf').read_text()
        for old,new in {'local _patient':'_patientLocal','alive _patient':'_patientAlive',
                        '_patient checkAIFeature _x':'(_x in _enabledFeatures)',
                        'unitPos _patient':'_engineUnitPos','behaviour _patient':'_engineBehaviour',
                        'unitCombatMode _patient':'_engineCombat','stance _patient':'_engineStance',
                        'animationState _patient':'_trainingAnimation',
                        'objectParent _patient':'_parent','attachedTo _patient':'_attached',
                        'serverTime':'_clock','doStop _patient;':'_engineCalls pushBack ["doStop",true];'}.items():s=s.replace(old,new)
        s=commands(s,['disableAI','enableAI','setUnitPos','setBehaviourStrong','setUnitCombatMode','allowFleeing','forceSpeed','playMoveNow'])
        out+='ACM_mission_fnc_'+name+'={'+adapt(s,'mission')+'};'
    return out


def test_spawned_ai_suppresses_autonomy_without_freezing_animation_and_crouches_unarmed():
    execute(training_setup()+'''
        [_patient] call ACM_mission_fnc_trainingPatientHold;
        [["setUnitPos","MIDDLE"] in _engineCalls,"crouch missing"] call _check;
        [["playMoveNow","AmovPknlMstpSnonWnonDnon"] in _engineCalls,"unarmed kneeling move missing"] call _check;
        [["forceSpeed",0] in _engineCalls && {["allowFleeing",0] in _engineCalls},"flight/motion not blocked"] call _check;
        {[["disableAI",_x] in _engineCalls,"autonomous AI feature not suppressed"] call _check;} forEach ["MOVE","PATH","TARGET","AUTOTARGET","AUTOCOMBAT","COVER","SUPPRESSION","FSM","WEAPONAIM"];
        [!(["disableAI","ANIM"] in _engineCalls),"medical animation frozen"] call _check;
        [count (missionNamespace getVariable ["ACME_trainingHeldPatients",[]])==1,"not enrolled"] call _check;
        [_patient] call ACM_mission_fnc_trainingPatientHold;
        [count (missionNamespace getVariable ["ACME_trainingHeldPatients",[]])==1,"duplicate enrollment"] call _check;
    ''')


@pytest.mark.parametrize('condition',[
    '_patient setVariable ["ACE_isUnconscious",true];','_parent=missionNamespace;',
    '_attached=missionNamespace;','_dragged=true;','_carried=true;',
    '_patient setVariable ["ACME_patientAnimLock",["pose","",1,1,101]];',
    '_patient setVariable ["ACME_headElevated",true];',
    '_patient setVariable ["ACM_airway_RecoveryPosition_State",true];',
    '_patient setVariable ["ACME_lido_seizureState","active"];'])
def test_training_stance_yields_to_medical_position_life_transport_and_seizure(condition):
    execute(training_setup()+condition+'''
        [[_patient] call ACM_mission_fnc_trainingPatientHold,"keeper lost marked patient"] call _check;
        [(_engineCalls findIf {(_x select 0) in ["playMoveNow","setUnitPos"]})<0,"keeper overrode medical/transport pose"] call _check;
    ''')


@pytest.mark.parametrize('condition',['_patientLocal=false;','_patientAlive=false;', '_patient setVariable ["ACME_trainingCrouchOnly",false];'])
def test_training_start_does_not_touch_unowned_dead_or_unmarked_ai(condition):
    execute(training_setup()+condition+'''
        [!([_patient] call ACM_mission_fnc_trainingPatientHold),"ineligible patient enrolled"] call _check;
        [count _engineCalls==0,"ineligible AI changed"] call _check;
    ''')


@pytest.mark.parametrize('release',['_isPlayer=true;', '_patient setVariable ["ACME_trainingCrouchOnly",false];'])
def test_training_release_restores_previously_owned_ai_features_only(release):
    execute(training_setup()+'''
        [_patient] call ACM_mission_fnc_trainingPatientHold;_engineCalls=[];
    '''+release+'''
        [!([_patient] call ACM_mission_fnc_trainingPatientHoldTick),"player/unmarked AI stayed enrolled"] call _check;
        {[["enableAI",_x] in _engineCalls,"original AI feature not restored"] call _check;} forEach _enabledFeatures;
        [!(["enableAI","SUPPRESSION"] in _engineCalls),"enabled feature that had already been disabled"] call _check;
        [["setUnitPos","AUTO"] in _engineCalls && {["forceSpeed",-1] in _engineCalls},"stance/speed not released"] call _check;
        [isNil {_patient getVariable "ACME_trainingSavedAI"},"stale saved control record"] call _check;
    ''')


def test_training_crouch_retry_is_bounded_and_resumes_after_unconsciousness():
    execute(training_setup()+'''
        _patient setVariable ["ACE_isUnconscious",true];[_patient] call ACM_mission_fnc_trainingPatientHold;
        _patient setVariable ["ACE_isUnconscious",false];[_patient] call ACM_mission_fnc_trainingPatientHoldTick;
        _engineCalls=[];CBA_missionTime=101;[_patient] call ACM_mission_fnc_trainingPatientHoldTick;
        [(_engineCalls findIf {(_x select 0)=="playMoveNow"})<0,"replayed crouch every polling tick"] call _check;
        CBA_missionTime=102;[_patient] call ACM_mission_fnc_trainingPatientHoldTick;
        [["playMoveNow","AmovPknlMstpSnonWnonDnon"] in _engineCalls,"bounded retry missing"] call _check;
    ''')


def healing_setup(name):
    s=(ROOT/'addons/core/overrides'/f'fnc_{name}.sqf').read_text()
    s=re.sub(r'#ifdef DEBUG_MODE_FULL.*?#endif','',s,flags=re.S)
    s=s.replace('IS_UNCONSCIOUS(_this)','(_this getVariable ["ACE_isUnconscious",false])').replace('IN_LYING_STATE(_this)','(_this getVariable ["ACM_core_inLyingState",false])')
    s=s.replace('alive _target','_targetAlive').replace('_this distance _target','_healerDistance').replace('getPosATL _target','[0,0,0]').replace('leader _this','_patient')
    s=commands(s,['forceSpeed','doFollow','doMove'])
    return '''private _heals=[];private _engineCalls=[];private _isPlayer=false;private _targetAlive=true;private _healerDistance=1;
       ace_common_fnc_isPlayer={_isPlayer};ace_medical_ai_fnc_isInjured={true};ace_medical_ai_fnc_healingLogic={_heals pushBack _this;};
       _medic setVariable ["ace_medical_ai_healQueue",[_patient]];
    '''+'ACME_test_heal={'+adapt(s,'core')+'};'


@pytest.mark.parametrize('name',['healSelf','healUnit'])
@pytest.mark.parametrize('marked',[False,True])
def test_native_ai_healing_stops_only_marked_spawner_actors(name,marked):
    execute(healing_setup(name)+f'_medic setVariable ["ACME_trainingCrouchOnly",{str(marked).lower()}];'+'''
        _medic setVariable ["ace_medical_ai_currentTreatment",["busy"]];_medic call ACME_test_heal;
    '''+f'[count _heals=={int(not marked)},"marked blocker affected ordinary medic or allowed self treatment"] call _check;'+('''
        [count _engineCalls==0 && {isNil {_medic getVariable "ace_medical_ai_currentTreatment"}},"training AI moved or retained autonomous treatment"] call _check;
    ''' if marked else ''))


def test_training_uses_single_existing_ace_overrides_and_marks_both_spawners():
    for name in ['generatePatient','spawnCustomPatient']:
        s=(ROOT/'addons/mission/functions'/f'fnc_{name}.sqf').read_text()
        assert 'setVariable ["ACME_trainingCrouchOnly",true,true]' in s
        assert '[_patient] call FUNC(trainingPatientHold)' in s
    cfg=(ROOT/'addons/core/CfgFunctions.hpp').read_text()
    assert 'class overwrite_medical_ai' in cfg
    assert 'overrides\\fnc_healSelf.sqf' in cfg and 'overrides\\fnc_healUnit.sqf' in cfg
    assert not (ROOT/'addons/mission/CfgFunctions.hpp').exists()
    runtime=(ROOT/'addons/mission/XEH_postInit.sqf').read_text()
    assert '},0.5,[]] call CBA_fnc_addPerFrameHandler' in runtime
    assert 'GVAR(trainingHoldScanAt) = CBA_missionTime + 10' in runtime


def inventory_setup():
    s=read('carrierInventoryOpen')
    s=s.replace('local _medic','_medicLocal').replace('alive _medic','_alive').replace('_medic distance _cargo','_cargoDistance')
    s=s.replace('uiNamespace getVariable ["ace_medical_gui_menuDisplay",displayNull]','_menuDisplay')
    s=s.replace('dialog','_dialog').replace('closeDialog 0;','_dialog=false;_closes=_closes+1;')
    s=binary_array(s,'actionNow',lambda u,a:f'_opened pushBack [{u},{a}]')
    return '''
        private _medicLocal=true;private _cargoDistance=1;private _closes=0;private _opened=[];private _jobs=[];
        private _menuDisplay=missionNamespace;_dialog=true;private _worldCargo=parsingNamespace;
        _worldCargo setVariable ["ACME_carrierPatient",_patient];_patient setVariable ["ACME_carrierCargo",_worldCargo];
        CBA_fnc_waitAndExecute={_jobs pushBack _this;};
        private _deliver={params ["_job"];(_job select 1) call (_job select 0);};
    '''+'ACME_fnc_carrierInventoryGet={'+adapt(read('carrierInventoryGet'))+'};ACME_fnc_carrierInventoryOpen={'+adapt(s)+'};'


def test_inventory_waits_until_medical_close_and_uses_instant_native_gear_on_actual_cargo():
    execute(inventory_setup()+'''
        [[_medic,_patient] call ACME_fnc_carrierInventoryOpen,"inventory refused"] call _check;
        [count _opened==0 && {_closes==1} && {count _jobs==1},"native Gear opened over old medical dialog"] call _check;
        [(_jobs select 0 select 2)>=0.15,"no deferred display teardown"] call _check;
        [_jobs select 0] call _deliver;
        [_opened isEqualTo [[_medic,["Gear",_worldCargo]]],"wrong native cargo target/action"] call _check;
        [!ace_medical_gui_pendingReopen,"medical dialog reopened over inventory"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_alive=false;','_medicLocal=false;','_medic setVariable ["ACE_isUnconscious",true];',
    '_worldCargo setVariable ["ACME_carrierClosing",true];',
    '_patient setVariable ["ACME_carrierCargo",objNull];','_cargoDistance=3.3;', '_dialog=true;',
    '_medic setVariable ["ACME_carrierOpenToken",99];'])
def test_delayed_inventory_cannot_open_after_custody_provider_range_dialog_or_token_change(change):
    execute(inventory_setup()+'''[_medic,_patient] call ACME_fnc_carrierInventoryOpen;'''+change+'''
        [_jobs select 0] call _deliver;[count _opened==0,"stale inventory request opened"] call _check;
    ''')


def test_inventory_does_not_close_an_unrelated_dialog_or_open_a_different_carrier():
    execute(inventory_setup()+'''
        _menuDisplay=objNull;
        [!([_medic,_patient] call ACME_fnc_carrierInventoryOpen),"closed another inventory"] call _check;
        _dialog=false;
        [!([_medic,_patient,uiNamespace] call ACME_fnc_carrierInventoryOpen),"opened another casualty's carrier"] call _check;
        [count _jobs==0 && {_closes==0},"queued unauthorized inventory"] call _check;
    ''')


def test_native_world_inventory_action_is_idempotent_and_preserves_cargo_patient_binding():
    s=read('carrierInventoryWorld').replace('hasInterface','true').replace('typeOf _cargo','"ACME_RemovedCarrierCargo"')
    s=binary_array(s,'addAction',lambda u,a:f'[{a}] call ACME_test_addAction')
    execute(inventory_setup()+'''
        private _actions=[];ACME_test_addAction={_actions pushBack (_this select 0);count _actions};
    '''+'ACME_fnc_carrierInventoryWorld={'+adapt(s)+'};'+'''
        [_worldCargo] call ACME_fnc_carrierInventoryWorld;[_worldCargo] call ACME_fnc_carrierInventoryWorld;
        [count _actions==0 && {count _opened==0},"custom action or forced Gear open remains"] call _check;
        [(_worldCargo getVariable ["ACME_carrierPatient",objNull]) isEqualTo _patient,"native holder lost patient binding"] call _check;
    ''')


def death_setup():
    s=read('recoveryDeathSlump')
    for old,new in {'local _patient':'_patientLocal','alive _patient':'_patientAlive','animationState _patient':'_patientAnimation',
                    'objectParent _patient':'_parent','attachedTo _patient':'_attached','velocity _patient':'_engineVelocity',
                    'getPosATL _patient':'_posATL','getPosASL _patient':'_posASL','diag_tickTime':'_clock',
                    '_patient distance2D (_record select 2)':'_horizDistance'}.items():s=s.replace(old,new)
    s=binary_array(s,'addEventHandler',lambda u,a:f'[{a}] call ACME_test_addHit')
    s=binary_array(s,'removeEventHandler',lambda u,a:f'_removedHits pushBack {a}')
    s=binary_array(s,'setVelocity',lambda u,a:f'_velocityWrites pushBack {a}')
    return '''
        private _patientLocal=true;_patientAlive=false;private _patientAnimation="ACM_RecoveryPosition";
        private _parent=objNull;private _attached=objNull;private _engineVelocity=[0.1,0.2,1.5];
        private _posATL=[0,0,0.2];private _posASL=[0,0,0.2];private _clock=100;private _horizDistance=0;
        private _velocityWrites=[];private _hitEvents=[];private _removedHits=[];private _dragged=false;private _carried=false;
        ACME_test_addHit={_hitEvents pushBack (_this select 0);count _hitEvents};
        ace_common_fnc_isBeingDragged={_dragged};ace_common_fnc_isBeingCarried={_carried};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",1]};
        _patient setVariable ["ACM_airway_RecoveryPosition_State",true];
        private _dampTick={private _h=_handlers select 0;[_h select 1,0] call (_h select 0);};
    '''+'ACME_fnc_recoveryDeathSlump={'+adapt(s)+'};'


def test_recovery_death_only_damps_upward_motion_preserving_gravity_and_horizontal_slump():
    execute(death_setup()+'''
        [[_patient] call ACME_fnc_recoveryDeathSlump,"recovery death not enrolled"] call _check;
        [_patient] call ACME_fnc_recoveryDeathSlump;[count _handlers==1,"duplicate death handler"] call _check;
        call _dampTick;[_velocityWrites isEqualTo [[0.1,0.2,0]],"damping modified horizontal motion"] call _check;
        _engineVelocity=[0.1,0.2,-0.8];call _dampTick;
        [count _velocityWrites==1,"downward gravity was cancelled"] call _check;
        _clock=100.65;call _dampTick;
        [!(_handlers select 0 select 2) && {count _removedHits==1},"death damping or hit hook leaked"] call _check;
        [(_patient getVariable ["ACME_recoveryDeathDamp",[]]) isEqualTo [],"damping state not released"] call _check;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"death erased position evidence"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;', '_patientAlive=true;', '_parent=missionNamespace;', '_attached=missionNamespace;',
    '_dragged=true;', '_carried=true;', '_engineVelocity=[3,0,0];','_engineVelocity=[0,0,6.1];',
    '_posATL=[0,0,2];','_patientAnimation="dead";_patient setVariable ["ACM_airway_RecoveryPosition_State",false];'])
def test_death_mitigation_skips_living_unowned_transport_fast_airborne_and_nonrecovery_cases(change):
    execute(death_setup()+change+'''
        [!([_patient] call ACME_fnc_recoveryDeathSlump),"ineligible corpse enrolled"] call _check;
        [count _handlers==0 && {count _velocityWrites==0},"ineligible physics changed"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;','_patientAlive=true;','_parent=missionNamespace;',
    '_patient setVariable ["ACME_clinicalEpoch",2];','_engineVelocity=[0,0,7];',
    '_horizDistance=0.8;','[_patient] call (_hitEvents select 0 select 1);'])
def test_death_damping_cancels_on_new_hit_transport_reset_owner_or_real_impulse(change):
    execute(death_setup()+'''[_patient] call ACME_fnc_recoveryDeathSlump;'''+change+'''
        call _dampTick;
        [count _velocityWrites==0 && {!(_handlers select 0 select 2)},"cancelled corpse damping continued"] call _check;
    ''')


def test_short_jerk_blend_cleanup_finishes_and_never_overrides_successor_gesture():
    execute(motor_setup()+late_jerk()+'''
        [_short] call _deliver;private _tail=_jobs select ((count _jobs)-1);
        [_tail] call _deliver;
        [(_capturedGestures select ((count _capturedGestures)-1)) isEqualTo ["GestureEmpty",0,1,false],"blend cleanup never completed"] call _check;
        _gestureState="unrelatedMedicalGesture";private _count=count _capturedGestures;[_tail] call _deliver;
        [count _capturedGestures==_count,"old cleanup clobbered a medical gesture"] call _check;
    ''')
