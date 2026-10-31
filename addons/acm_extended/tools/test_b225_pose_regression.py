"""B225 regression: no shared-graph wake routes; normal awake lying persistence;
exact scope/pressure cleanup. Production SQF executes under explicit engine mocks.
These tests cannot establish native Arma graph selection or rendered blending.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b224_polish_wake import wake_setup
from test_b219_world_lifecycle import training_setup
from test_bounded_stethoscope_exit_generation import setup as scope_setup

FAMILIES=[f'{family}{letter}' for family,letters in [('Default','AB'),('Body','AB'),('Arms','ABC'),('Head','ABC')] for letter in letters]


def wake_block(family):
    source=(ROOT/'addons/acm_extended/config.cpp').read_text()
    return source.split(f'class ACME_Wake{family}:',1)[1].split('\n        };',1)[0]


@pytest.mark.parametrize('family',FAMILIES)
def test_wake_wrappers_cannot_add_edges_out_of_shared_native_states(family):
    block=wake_block(family)
    # From/With properties add REVERSE edges to shared nodes, including inherited
    # ones. Empty them explicitly instead of adding a new corrective polling loop.
    for edge in ['connectFrom','interpolateFrom','interpolateWith']:
        assert re.search(rf'{edge}\[\]\s*=\s*\{{\s*\}};',block)
    assert 'connectAs = "";' in block
    assert f'class ACME_Wake{family}_Prone:' not in (ROOT/'addons/acm_extended/config.cpp').read_text()


@pytest.mark.parametrize('family',FAMILIES)
def test_natural_wake_graph_can_only_complete_into_medical_lying(family):
    block=wake_block(family)
    for edge in ['connectTo','interpolateTo']:
        targets=re.findall(r'"([^"]+)"',re.search(rf'{edge}\[\]\s*=\s*\{{([^}}]*)\}}',block)[1])
        assert targets==['ACM_LyingState']
    assert 'UnconsciousOutProne' not in block
    assert 'AmovPpne' not in block
    assert 'looped = 0;' in block and 'minPlayTime = 0;' in block


@pytest.mark.parametrize('lying', [False,True])
@pytest.mark.parametrize('stance',['CROUCH','PRONE','UNDEFINED'])
def test_actual_wake_arms_lying_even_if_old_native_path_cleared_the_flag(lying,stance):
    execute(wake_setup()+f'''
        _patient setVariable ["ACM_core_Lying_State",{str(lying).lower()}];_stance="{stance}";
        call _wake;call _observe;
        [_patient getVariable ["ACM_core_Lying_State",false],"wake failed to hold medical lying"] call _check;
        [((_patient getVariable "ACME_wakeVisual") select 2)=="ACM_LyingState","ordinary prone rest selected"] call _check;
        _progress=1;call _frame;private _count=count _moves;
        for "_i" from 1 to 20 do {{CBA_missionTime=CBA_missionTime+.5;call _frame;}};
        [count _moves==_count && {{(_moves select (_count-1))=="ACM_LyingState"}},"completion replayed/walked away"] call _check;
    ''')


@pytest.mark.parametrize('state',['acm_lyingstate','acme_wakeheadc','ainjppnemstpsnonwrfldnon_rolltofront','acme_headelevpatientgrab','acme_headelevpatientrelease'])
def test_training_keeper_never_crouches_during_or_after_medical_wake(state):
    execute(training_setup()+f'''
        _patient setVariable ["ACM_core_Lying_State",true];
        _patient setVariable ["ACME_wakeVisualToken",[]];_trainingAnimation="{state}";
        for "_i" from 1 to 30 do {{CBA_missionTime=CBA_missionTime+1;[_patient] call ACM_mission_fnc_trainingPatientHoldTick;}};
        [(_engineCalls findIf {{(_x select 0) in ["playMoveNow","setUnitPos"]}})<0,"AI rose without Get Up"] call _check;
        [!(["disableAI","ANIM"] in _engineCalls),"AI animation frozen"] call _check;
    ''')


def test_training_keeper_also_respects_visible_lying_during_flag_replication_gap():
    execute(training_setup()+'''
        _trainingAnimation="acm_lyingstate";_patient setVariable ["ACM_core_Lying_State",false];
        [_patient] call ACM_mission_fnc_trainingPatientHoldTick;
        [(_engineCalls findIf {(_x select 0) in ["playMoveNow","setUnitPos"]})<0,"replication gap crouched patient"] call _check;
        _trainingAnimation="amovppnemstpsnonwnondnon";_engineCalls=[];
        [_patient] call ACM_mission_fnc_trainingPatientHoldTick;
        [["setUnitPos","MIDDLE"] in _engineCalls,"explicit lying release did not restore training behavior"] call _check;
    ''')


@pytest.mark.parametrize('animation',['ainjppnemstpsnonwrfldnon_rolltofront','ainjppnemstpsnonwrfldnon_rolltoback','acme_headelevpatientgrab','acme_headelevpatientrelease'])
def test_new_patient_body_controller_preempts_wake_without_pose_reset(animation):
    execute(wake_setup()+f'''
        call _wake;call _observe;
        // Accepted arbiter request calls Stop without exit BEFORE new body pose.
        [_patient] call ACME_fnc_wakeAnimationStop;
        _animation="{animation}";private _n=count _moves;
        [[_patient,1],0] call ACME_fnc_wakeAnimationTick;
        [_patient,1,true] call ACME_fnc_wakeAnimationStop;
        [count _moves==_n,"late wake callback replaced body choreography"] call _check;
        [_patient getVariable ["ACM_core_Lying_State",false],"preemption cleared medical lying"] call _check;
    ''')


@pytest.mark.parametrize('observed',[False,True])
def test_renewed_unconsciousness_retires_wake_without_choosing_generic_prone(observed):
    execute(wake_setup()+f'''
        call _wake;{ 'call _observe;' if observed else '' }
        _patient setVariable ["ACE_isUnconscious",true];private _n=count _moves;
        [_patient,true] call ACME_fnc_wakeAnimationEvent;
        [[_patient,1],0] call ACME_fnc_wakeAnimationTick;
        [count _moves==_n,"unconscious edge forced a rest/prone pose"] call _check;
        [_patient getVariable ["ACME_wakeVisualArmed",false],"new unconscious episode not armed"] call _check;
    ''')


def pressure_setup():
    s=read('stethoscopePressureRelease').replace('local _medic','_medicLocal')
    return '''
        private _medicLocal=true;
        missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch",10];
        ACM_core_ContinuousAction_Active=false;
        _medic setVariable ["ACME_providerTreatmentEpoch",20];
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Paused",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","usestethoscope"];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        _medic setVariable ["ACME_DP_PFH",99];
        _medic setVariable ["ACME_DP_ClaimToken","same-claim"];
        _medic setVariable ["ACME_DP_ClaimEpoch",7];
        _medic setVariable ["ACME_DP_ClinicalYield",true];
    '''+'ACME_fnc_stethoscopePressureRelease={'+adapt(s)+'};'


@pytest.mark.parametrize('carrier',['bare','manual','temporary'])
def test_actual_scope_unload_releases_its_carrier_preflight_pressure_pause(carrier):
    state={'bare':'_patient setVariable ["ACME_chestAccess_vestLoadout",[]];',
           'manual':'_patient setVariable ["ACME_manualPlateCarrierState","off"];',
           'temporary':'_medic setVariable ["ACME_chestAccess_treatment",[_patient,"usestethoscope","chest-token"]];'}[carrier]
    execute(scope_setup()+pressure_setup()+state+'''
        ACM_core_ContinuousAction_Active=true;
        _display setVariable ["ACME_stethProviderTreatmentEpoch",20];
        [_display] call _close;
        [!(_medic getVariable ["ACME_DP_Paused",true]),"DP remained paused after scope"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"scope stopped persistent pressure"] call _check;
        [(_medic getVariable "ACME_DP_ClaimToken")=="same-claim" && {(_medic getVariable "ACME_DP_PFH")==99},"scope reset DP claim/session"] call _check;
        [(_medic getVariable "ACME_DP_IdleStart")==CBA_missionTime,"two-second quiet window not restarted"] call _check;
        [_medic getVariable ["ACME_DP_ClinicalYield",false],"scope applied clinical pressure during restoration"] call _check;
    ''')


@pytest.mark.parametrize('changed',[
    '_medicLocal=false;',
    'ACM_core_ContinuousAction_Active=true;',
    'missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch",11];',
    '_medic setVariable ["ACME_providerTreatmentEpoch",21];',
    '_medic setVariable ["ACME_DP_Patient",missionNamespace];',
    '_medic setVariable ["ACME_DP_Active",false];',
    '_medic setVariable ["ACME_DP_PauseTreatmentClass","cpr"];',
    '_medic setVariable ["ACME_DP_PauseTreatmentClass","checkairway"];',
    '_medic setVariable ["ACME_DP_PauseTreatmentClass",""];',
])
def test_late_scope_pressure_cleanup_cannot_release_another_action(changed):
    execute(pressure_setup()+changed+'''
        [!([_medic,_patient,10,20] call ACME_fnc_stethoscopePressureRelease),"wrong owner released pause"] call _check;
        [_medic getVariable ["ACME_DP_Paused",false],"different pause cleared"] call _check;
        [(_medic getVariable "ACME_DP_ClaimToken")=="same-claim","claim changed"] call _check;
    ''')


def test_duplicate_unload_and_controller_cleanup_do_not_extend_dp_resume_delay():
    execute(pressure_setup()+'''
        [[_medic,_patient,10,20] call ACME_fnc_stethoscopePressureRelease,"first cleanup failed"] call _check;
        CBA_missionTime=11;
        [!([_medic,_patient,10,20] call ACME_fnc_stethoscopePressureRelease),"duplicate cleanup changed pause"] call _check;
        [(_medic getVariable "ACME_DP_IdleStart")==10,"duplicate reset two-second delay"] call _check;
    ''')


def test_scope_controller_and_unload_share_exact_cleanup_without_restarting_dp():
    controller=read('beginStethoscopeAction');close=read('stethoscopeClose');helper=read('stethoscopePressureRelease')
    assert 'ACME_stethProviderTreatmentEpoch' in controller and 'ACME_stethProviderTreatmentEpoch' in close
    assert 'call ACME_fnc_stethoscopePressureRelease' in controller and 'call ACME_fnc_stethoscopePressureRelease' in close
    assert 'call ACME_fnc_directPressureStop' not in helper and 'call ACME_fnc_directPressureStart' not in helper
    assert 'setAnimSpeedCoef' not in helper and 'playMove' not in helper and 'switchMove' not in helper
    assert 'ACME_DP_idleToPose", 2' in read('directPressurePose')


def test_existing_patient_and_provider_rest_states_are_not_rewritten_by_patch():
    source=(ROOT/'addons/acm_extended/config.cpp').read_text().split('// B225: one-shot wake RTMs')[1].split('class ACME_',1)[0]
    assert 'class ACM_LyingState:' not in source
    # Invariant: no rolling or carrier operation synthesizes a medical wake event.
    for name in ['patientAnimRequest','stethoscopeFlip','chestAccessVestRestore','chestAccessVestPrep']:
        p=ROOT/'addons/acm_extended/functions'/f'fn_{name}.sqf'
        if p.exists(): assert 'call ACME_fnc_wakeAnimationEvent' not in p.read_text()


def native_uncon_setup():
    s=(ROOT/'addons/core/overrides/fnc_setUnconsciousAnim.sqf').read_text()
    s=re.sub(r'^\s*(?:TRACE_\d|ERROR_\d)\([^\n]*\);','',s,flags=re.M)
    for old,new in [
        ('local _unit','_unitLocal'),('alive _unit','_patientAlive'),
        ('objectParent _unit','_nativeVehicle'),('attachedTo _unit','_nativeAttached'),
        ('animationState _unit','_nativeAnimation'),('lifeState _unit','_nativeLife'),
        ('vehicle _unit isKindOf "StaticWeapon"','false'),
        ('vehicle _unit isKindOf "Pod_Heli_Transport_04_crewed_base_F"','false'),
        ('_unit setUnconscious _isUnconscious;','_nativeUncon=_isUnconscious;'),
        ('LYING_ANIMATION','["acm_lyingstate"]'),('serverTime','CBA_missionTime'),
    ]:s=s.replace(old,new)
    return '''
        private _unitLocal=true;private _nativeVehicle=objNull;private _nativeAttached=objNull;
        private _nativeAnimation="unconscious";private _nativeLife="HEALTHY";private _nativeUncon=false;
        private _wakeStops=0;
        ACME_fnc_wakeAnimationStop={_wakeStops=_wakeStops+1;};
        ACM_core_fnc_setWasTreated={params ["_p","_v"];_p setVariable ["ACM_core_WasTreated",_v];};
        ACM_core_fnc_setLyingState={params ["_p","_v"];_p setVariable ["ACM_core_Lying_State",_v];};
        CBA_fnc_globalEvent={_events pushBack _this;};
        ace_common_fnc_getDeathAnim={"native-seat-death"};
        ace_common_fnc_getAwakeAnim={"native-seat-awake"};
    '''+'private _coreNative={'+adapt(s)+'};'


@pytest.mark.parametrize('armed', [False,True])
def test_native_wake_pins_lying_before_engine_release_without_requesting_prone(armed):
    execute(native_uncon_setup()+f'''
        _patient setVariable ["ACME_wakeVisualArmed",{str(armed).lower()}];
        _nativeLife="INCAPACITATED";
        [_patient,false] call _coreNative;
        [_patient getVariable ["ACM_core_Lying_State",false],"native wake missed medical lying"] call _check;
        [count _moves==0,"native wake rolled into normal prone"] call _check;
        [(_events select 0) isEqualTo ["ace_common_switchMove",[_patient,"ACM_LyingState"]],"native resting pose changed"] call _check;
        [!_nativeUncon,"native wake failed to release engine unconsciousness"] call _check;
    ''')


@pytest.mark.parametrize('state',['unconscious','acm_lyingstate','acme_wakeheadc','acme_headelevpatientrelease'])
def test_native_unconscious_edge_keeps_engine_pose_selection(state):
    execute(native_uncon_setup()+f'''
        _nativeAnimation="{state}";_patient setVariable ["ACE_isUnconscious",true];
        [_patient,true] call _coreNative;
        [_nativeUncon && {{_wakeStops==1}},"native unconscious edge was blocked"] call _check;
        [count _moves==0 && {{count _events==0}},"unconscious edge forced generic prone/face-up"] call _check;
    ''')


@pytest.mark.parametrize('interruption',[
    '_patient setVariable ["ACE_isUnconscious",true];[_patient,true] call _coreNative;',
    '_patient setVariable ["ACME_wakePoseTicket",999];',
    '_unitLocal=false;',
    '_patient setVariable ["ACM_core_Lying_State",false];',
    '_patient setVariable ["ACME_patientAnimLock",["new","roll","medic",4,999]];',
    '_patient setVariable ["ACME_headElevated",true];',
    '_patient setVariable ["ACM_airway_RecoveryPosition_State",true];',
    '_nativeVehicle=missionNamespace;',
    '_nativeAttached=missionNamespace;',
])
def test_delayed_native_wake_repair_cannot_undo_new_unconsciousness_or_body_action(interruption):
    execute(native_uncon_setup()+'''
        _patient setVariable ["ACME_wakeVisualArmed",true];
        [_patient,false] call _coreNative;
        private _job=_waits select 0;
    '''+interruption+'''
        private _n=count _events;
        (_job select 1) call (_job select 0);
        [count _events==_n && {count _moves==0},"old wake repair replaced new body pose"] call _check;
    ''')


@pytest.mark.parametrize('unconscious',[False,True])
def test_seated_native_unconscious_controller_preserves_existing_seat_path(unconscious):
    execute(native_uncon_setup()+f'''
        _nativeVehicle=missionNamespace;_patient setVariable ["ACME_wakeVisualArmed",true];
        [_patient,{str(unconscious).lower()}] call _coreNative;
        [!(_patient getVariable ["ACM_core_Lying_State",false]),"seat path forced lying"] call _check;
        [_moves isEqualTo ["native-seat-{'death' if unconscious else 'awake'}"],"seat controller changed"] call _check;
    ''')


@pytest.mark.parametrize('restoring',[False,True])
def test_real_dp_tick_resumes_after_scope_and_yields_until_carrier_provider_finishes(restoring):
    from test_b213_direct_pressure_flow import setup as dp_setup
    from test_b223_interaction_flow import function
    execute(dp_setup()+function('stethoscopePressureRelease')+f'''
        ["body"] call _start;
        _animation="acme_directpressurehold";
        private _claim=_medic getVariable "ACME_DP_ClaimToken";
        private _pfh=_medic getVariable "ACME_DP_PFH";
        missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch",10];
        _medic setVariable ["ACME_providerTreatmentEpoch",20];
        ACM_core_ContinuousAction_Active=true;
        _medic setVariable ["ACME_DP_Paused",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","usestethoscope"];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];call _pressTick;
        ACM_core_ContinuousAction_Active=false;
        _medic setVariable ["ACME_headElev_seqActive",{str(restoring).lower()}];
        [[_medic,_patient,10,20] call ACME_fnc_stethoscopePressureRelease,"scope pause not retired"] call _check;
        if ({str(restoring).lower()}) then {{
            for "_i" from 1 to 4 do {{CBA_missionTime=CBA_missionTime+1;call _pressTick;}};
            [!(_medic getVariable ["ACME_DP_InPose",false]),"DP overrode carrier reach"] call _check;
            _medic setVariable ["ACME_headElev_seqActive",false];
        }};
        _animation="amovpknlmstpsnonwnondnon";
        CBA_missionTime=(_medic getVariable "ACME_DP_IdleStart")+1.99;call _pressTick;
        [!(_medic getVariable ["ACME_DP_InPose",false]),"DP skipped quiet delay"] call _check;
        CBA_missionTime=(_medic getVariable "ACME_DP_IdleStart")+2.01;call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"DP did not re-enter after scope"] call _check;
        [(_medic getVariable "ACME_DP_ClaimToken")==_claim && {{(_medic getVariable "ACME_DP_PFH")==_pfh}},"resumption replaced original DP claim"] call _check;
    ''')


def getup_setup():
    from test_b210_ai_protection_lifecycle import lifecycle
    # Record only the engine blend command; all native release checks and callbacks execute.
    source=lifecycle().replace('attachedTo _p','(_p getVariable ["TEST_attached",objNull])')
    for field in ('TEST_vehicle','TEST_attached'):
        source=source.replace(f'isNull (_p getVariable ["{field}",objNull])',
                              f'((_p getVariable ["{field}",objNull]) isEqualTo objNull)')
    source=source.replace('_patient switchMove [_roll,0,0.25,false];',
                          '_moves pushBack [_patient,[_roll,0,0.25,false]];')
    return source+'''
        ACME_fnc_wakeAnimationStop={params ["_p"];_p setVariable ["ACME_wakeVisual",[]];};
        _patient setVariable ["ACM_core_Lying_State",true];
        _patient setVariable ["TEST_animation","acme_wakeheadc"];
        _patient setVariable ["ACME_wakeVisual",[17]];
    '''


def test_early_explicit_get_up_cancels_clip_and_uses_a_single_partial_blend():
    execute(getup_setup()+'''
        [_patient,true,_medic] call ACM_core_fnc_getUp;
        [!(_patient getVariable ["ACM_core_Lying_State",true]),"explicit Get Up remained lying"] call _check;
        [(_patient getVariable "ACME_wakeVisual") isEqualTo [],"early Get Up retained wake worker"] call _check;
        [_moves isEqualTo [[_patient,["UnconsciousOutProne",0,0.25,false]]],"early Get Up did not use a single controlled blend"] call _check;
    ''')


@pytest.mark.parametrize('interruption',[
    '_patient setVariable ["ACE_isUnconscious",true];',
    '_patient setVariable ["ACM_core_Lying_State",true];',
    '_patient setVariable ["TEST_owner",8];',
    '_patient setVariable ["TEST_vehicle",missionNamespace];',
    '_patient setVariable ["TEST_attached",missionNamespace];',
    '_patient setVariable ["ACME_patientAnimLock",["flip","body","medic",4,999]];',
    '_patient setVariable ["ACME_headElevated",true];',
    '_patient setVariable ["ACM_airway_RecoveryPosition_State",true];',
])
def test_delayed_explicit_get_up_repair_cannot_force_prone_over_new_patient_episode(interruption):
    execute(getup_setup()+'''
        [_patient,true,_medic] call ACM_core_fnc_getUp;
        _patient setVariable ["TEST_animation","unconscious"];
        private _n=count _moves;
    '''+interruption+'''
        {(_x select 1) call (_x select 0);} forEach +_waits;
        [count _moves==_n,"stale Get Up repair overrode newer patient pose"] call _check;
    ''')
