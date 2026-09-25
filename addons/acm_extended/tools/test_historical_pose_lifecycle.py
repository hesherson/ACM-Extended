"""Run current pose start/stop and observer receiver, not retired text assertions.

Arma movement, duration/phase, stance, locality, and delivery are explicit fixtures.
The actual episode/state/queue/release logic executes. Callbacks are delivered in
controlled orders, not at simulated real network latency. No live RTM rendering.
"""
import re
from pathlib import Path
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute

F=ROOT/'addons/acm_extended/functions'


def source(name):
    return (F/('fn_'+name+'.sqf')).read_text()


def pose_source(name):
    text=source(name)
    # Replace engine primitives before the shared adapter's default object mocks.
    for var in ('_medic','_unit','_u'):
        for old,new in [('local '+var,'_isLocal'),('alive '+var,'_alive'),
                        ('objectParent '+var,'_parent'),('stance '+var,'_stance'),
                        ('animationState '+var,'_animation'),('getAnimSpeedCoef '+var,'_speed'),
                        ('netId '+var,'"provider"')]:
            text=re.sub(re.escape(old)+r'\b',lambda m:new,text)
        text=text.replace(var+' getUnitMovesInfo 2','_duration')
        text=text.replace(var+' getUnitMovesInfo 1','_nativeElapsed')
        text=text.replace(var+' getUnitMovesInfo 0','_visiblePhase')
        text=re.sub(re.escape(var)+r' setUnitPos ([^;]+);',r'_positions pushBack (\1);',text)
        text=re.sub(re.escape(var)+r' setAnimSpeedCoef ([^;]+);',r'_speed=(\1); _speedWrites pushBack _speed;',text)
        # Model the documented concern in the source: seeking may reset speed.
        text=re.sub(re.escape(var)+r' switchMove (\[[^;]+\]);',r'_seeks pushBack \1; _speed=1;',text)
    text=text.replace('currentWeapon _medic','_weapon').replace('_medic selectWeapon "";','_weapon="";')
    text=text.replace('finite _nativeElapsed','_nativeFinite')
    text=text.replace('isServer','_server').replace('hasInterface','_interface').replace('clientOwner','_client')
    text=text.replace('owner _medic','_ownerNum')
    text=text.replace('getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _main >> "speed")','_configSpeed')
    # SQF-VM lacks getOrDefault; keep real maps and emulate only that primitive.
    for key in ('ACME_poseHoldAt','ACME_poseStopAfterHold'):
        old=f'(missionNamespace getVariable ["{key}", createHashMap]) getOrDefault [_mode, -1]'
        text=text.replace(old,f'[(missionNamespace getVariable ["{key}", createHashMap]),_mode,-1] call _getDefault')
    return adapt(text)


def settings_source():
    text=source('initChestSealProcedureRuntime')
    result=''
    for name in ('ACME_poseHoldAt','ACME_poseStopAfterHold'):
        anchor=name+' = createHashMapFromArray '
        assert text.count(anchor)==1
        start=text.index(anchor); pos=start+len(anchor)
        tokens=lex(text); pairs=matching(tokens)
        i=next(i for i,t in enumerate(tokens) if t.offset==pos and t.value=='[')
        result+=text[start:tokens[pairs[i]].offset+1]+';\n'
    return result


def setup():
    code=r'''
        private _isLocal=true; private _parent=objNull; private _stance="CROUCH";
        private _server=true; private _interface=true; private _client=7;
        private _animation="amovpknlmstpsnonwnondnon"; private _weapon="";
        private _positions=[]; private _seeks=[]; private _speedWrites=[];
        private _speed=1; private _duration=12; private _nativeElapsed=-1; private _nativeFinite=true;
        private _visiblePhase=0; private _configSpeed=-12;
        private _testPrepDelay=0; private _preps=0; private _blocked=false; private _removedJip=[];
        private _getDefault={params ["_map","_key","_default"]; if (_key in _map) then {_map get _key} else {_default}};
        CBA_fnc_waitAndExecute={_waits pushBack [_this select 0,_this select 1,_this select 2];};
        CBA_fnc_waitUntilAndExecute={_waits pushBack [_this select 1,_this select 2,_this select 3,_this select 0];};
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
        CBA_fnc_globalEvent={_events pushBack _this;};
        CBA_fnc_globalEventJIP={_events pushBack _this;};
        CBA_fnc_removeGlobalEventJIP={_removedJip pushBack _this;};
        ACM_core_fnc_setAceMedicalState={
            (_this select 0) setVariable ["ace_medical_treatment_endInAnim",""];
        };
        ACME_fnc_animBlocked={_blocked || {_parent isNotEqualTo objNull}};
        ACME_fnc_doAnim={_moves pushBack _this;};
        ACME_fnc_menuPoseStop={};
        ACME_fnc_medicAnimationPrep={_preps=_preps+1; _testPrepDelay};
        ace_advanced_fatigue_setAnimExclusions=["unrelated"];
        private _deliver={params ["_job"]; (_job select 1) call (_job select 0);};
        private _poseTick={
            params ["_id"];
            private _h=_handlers select _id;
            [_h select 1,_id] call (_h select 0);
        };
    '''
    code+=settings_source()
    for name in ('providerStanceOwned','treatmentPoseStop','treatmentPoseStart','treatmentPoseSync'):
        code+='ACME_fnc_'+name+'={'+pose_source(name)+'};\n'
    return code


OWNERS=[
    ('preflight','_medic setVariable ["ACME_treatmentPreflightActive",true];'),
    ('native','_medic setVariable ["ace_medical_treatment_endInAnim","new-treatment"];'),
    ('roll','_medic setVariable ["ACME_rollProviderActive",true];'),
    ('head','_medic setVariable ["ACME_headElev_seqActive",true];'),
    ('menu','_medic setVariable ["ACME_menuPose",[77]];'),
    ('raising','_medic setVariable ["ACME_hang_Raising",true];'),
    ('hang','_medic setVariable ["ACME_hang_Active",true];'),
    ('pressure','_medic setVariable ["ACME_DP_InPose",true];'),
    ('pressure-treatment','_medic setVariable ["ACME_DP_TreatmentBusy",true];'),
    ('cpr','_medic setVariable ["ACM_circulation_isPerformingCPR",true];'),
    ('continuous','ACM_core_ContinuousAction_Active=true;'),
]


def ended_setup(handoff=False):
    return setup()+r'''
        private _epoch=[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        [_medic,"stethoscope",_epoch,'''+str(handoff).lower()+r'''] call ACME_fnc_treatmentPoseStop;
        _moves=[]; _positions=[]; _events=[]; _speedWrites=[];
    '''


@pytest.mark.parametrize('name,owner',OWNERS,ids=[p[0] for p in OWNERS])
def test_delayed_crouch_cannot_override_new_provider_controller(name,owner):
    execute(ended_setup()+owner+r'''
        _stance="STAND";
        [count _waits==1,"missing bounded crouch correction"] call _check;
        [_waits select 0] call _deliver;
        [_moves isEqualTo [] && {_positions isEqualTo []},"old crouch callback overrode new controller"] call _check;
        [count _waits==1,"old cleanup scheduled additional stance work"] call _check;
    ''')


@pytest.mark.parametrize('name,owner',OWNERS,ids=[p[0] for p in OWNERS])
def test_final_stance_release_preserves_later_controller(name,owner):
    execute(ended_setup()+r'''
        _stance="STAND"; [_waits select 0] call _deliver;
        [count _waits==2,"missing final stance release"] call _check;
        _moves=[]; _positions=[];
    '''+owner+r'''
        [_waits select 1] call _deliver;
        [_moves isEqualTo [] && {_positions isEqualTo []},"late release broke new controller"] call _check;
    ''')


@pytest.mark.parametrize('name,owner',OWNERS,ids=[p[0] for p in OWNERS])
def test_handoff_callbacks_preserve_next_provider_controller(name,owner):
    execute(ended_setup(True)+owner+r'''
        [count _waits==2,"handoff callback count changed"] call _check;
        {[_x] call _deliver;} forEach +_waits;
        [_positions isEqualTo [] && {_moves isEqualTo []},"handoff cleanup broke new controller"] call _check;
    ''')


@pytest.mark.parametrize('stage',[-1,-2,0,1,2,3])
def test_matching_stop_clears_its_pending_work_once_and_returns_to_crouch(stage):
    execute(setup()+r'''
        private _epoch=[_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
    '''+f'_state set [3,{stage}];'+r'''
        _medic setVariable ["ACME_animQ",["pending"]]; _medic setVariable ["ACME_animQEnd",100];
        private _generation=_medic getVariable ["ACME_dah_gen",0];
        _moves=[];
        [_medic,"inspect",_epoch] call ACME_fnc_treatmentPoseStop;
        [(_medic getVariable ["ACME_treatmentPoseState",[0]]) isEqualTo [],"pose not cleared"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseEpisode",[]]) isEqualTo [_epoch,false],"episode not retired"] call _check;
        [(_medic getVariable ["ACME_animQ",[0]]) isEqualTo [] && {(_medic getVariable ["ACME_animQEnd",-1])==0},"queued move retained"] call _check;
        [(_medic getVariable ["ACME_dah_gen",0])==_generation+1,"held move was not invalidated"] call _check;
        [ace_advanced_fatigue_setAnimExclusions isEqualTo ["unrelated"],"fatigue exclusion not scoped"] call _check;
        [_moves isEqualTo [[_medic,"AmovPknlMstpSnonWnonDnon",1]],"wrong neutral exit"] call _check;
        private _count=count _waits;
        [_medic,"inspect",_epoch] call ACME_fnc_treatmentPoseStop;
        [count _waits==_count && {count _moves==1},"duplicate stop repeated cleanup"] call _check;
    ''')


@pytest.mark.parametrize('mode,offset', [('stethoscope',-1),('inspect',0)])
def test_mismatched_stop_does_not_touch_the_current_episode(mode,offset):
    execute(setup()+r'''
        private _ep=[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _before=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
        _moves=[]; _events=[]; _positions=[]; _speedWrites=[];
    '''+f'[_medic,"{mode}",_ep+{offset}] call ACME_fnc_treatmentPoseStop;'+r'''
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _before,"wrong stop changed episode"] call _check;
        [count _moves==0 && {count _events==0} && {count _positions==0} && {count _speedWrites==0},"wrong stop had side effects"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_alive=false;', '_isLocal=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_parent=missionNamespace;', '_medic setVariable ["ACME_treatmentPoseEpoch",99];',
    '_medic setVariable ["ACME_treatmentPoseState",[99]];',
])
def test_delayed_crouch_rechecks_life_locality_vehicle_and_episode(change):
    execute(ended_setup()+change+r'''
        _stance="STAND"; [_waits select 0] call _deliver;
        [count _moves==0 && {count _positions==0},"invalid cleanup moved provider"] call _check;
    ''')


@pytest.mark.parametrize('stance',['CROUCH','STAND'])
def test_ordinary_cleanup_remains_bounded_and_releases_temporary_stance(stance):
    execute(ended_setup()+f'_stance="{stance}";'+r'''
        [_waits select 0] call _deliver;
        [_waits select 1] call _deliver;
        [(count _waits)==2,"cleanup was not bounded"] call _check;
        [(_waits select 0) select 2==0.12 && {(_waits select 1) select 2==0.85},"existing cleanup delays changed"] call _check;
        [(_positions select (count _positions-1))=="AUTO","stance left locked"] call _check;
    '''+f'[count _moves=={int(stance=="STAND")},"unnecessary/missing crouch correction"] call _check;')


@pytest.mark.parametrize('mode,hold',[('roll',2.2),('chestAccess',2.2),('inspect',2.2),('pulse',.421),('stethoscope',.421)])
@pytest.mark.parametrize('duration',[3,12])
def test_owner_freeze_uses_current_mode_timeline_despite_frame_overshoot(mode,hold,duration):
    execute(setup()+f'_duration={duration}; private _expectedHold={hold}; private _ep=[_medic,"{mode}",-1,_patient] call ACME_fnc_treatmentPoseStart;'+r'''
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5; _animation=toLower (_state select 2);
        [_id] call _poseTick;
        [(_state select 3)==2,"entry not observed"] call _check;
        CBA_missionTime=10+_expectedHold-0.001; [_id] call _poseTick;
        [_seeks isEqualTo [] && {_speed==1},"premature freeze"] call _check;
        CBA_missionTime=10+_expectedHold+0.07; [_id] call _poseTick;
        [count _seeks==1 && {_speed==0} && {(_state select 3)==3},"freeze/seek missing"] call _check;
        [abs (((_seeks select 0) select 1)*_duration-_expectedHold)<0.000001,"overshoot changed sample phase"] call _check;
        [(_events select 0) select 0=="ACME_treatmentPoseSync","observer hold not sent"] call _check;
        [((_events select 0) select 1) select 1==_ep,"wrong episode sent"] call _check;
        [(_state select 11)==_expectedHold,"mode hold rule changed"] call _check;
    ''')


@pytest.mark.parametrize('duration,configSpeed,expected',[(0,-12,.421/12),(0,0,-1),('"invalid"',0,-1)])
def test_unknown_duration_freezes_without_inventing_a_phase(duration,configSpeed,expected):
    execute(setup()+f'_duration={duration}; _configSpeed={configSpeed};'+r'''
        [_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5; _animation=toLower (_state select 2);
        [_id] call _poseTick; CBA_missionTime=10.5; [_id] call _poseTick;
        [_speed==0 && {(_state select 3)==3},"unknown duration did not freeze"] call _check;
    '''+f'[abs ((_state select 12)-({expected}))<0.000001,"incorrect fallback phase"] call _check;'+
    f'[count _seeks=={int(expected>=0)},"unknown duration manufactured seek"] call _check;')


@pytest.mark.parametrize('disturbance',['none','speed','state'])
def test_owner_hold_reasserts_only_observed_drift_and_never_replays_running_action(disturbance):
    execute(setup()+r'''
        [_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5; _animation=toLower (_state select 2);
        [_id] call _poseTick; CBA_missionTime=10.5; [_id] call _poseTick;
        _seeks=[]; _moves=[]; _events=[]; _speedWrites=[];
    '''+({'none':'','speed':'_speed=1;','state':'_animation="other";'}[disturbance])+r'''
        CBA_missionTime=10.6; [_id] call _poseTick;
        [count _events==0 && {count _seeks==0},"hold drift was not rate limited"] call _check;
        CBA_missionTime=10.8; [_id] call _poseTick;
        [count _moves==0,"hold restarted ordinary work"] call _check;
        [_speed==0,"hold speed not restored"] call _check;
    '''+f'[count _seeks=={int(disturbance=="state")} && {{count _events=={int(disturbance!="none")}}},"incorrect drift repair"] call _check;')


@pytest.mark.parametrize('mode',['response','airway','torsoBandage'])
def test_finite_work_enters_once_without_a_fixed_replay_loop(mode):
    execute(setup()+f'[_medic,"{mode}",6,_patient] call ACME_fnc_treatmentPoseStart;'+r'''
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]]; private _id=_state select 5;
        _animation=toLower (_state select 2); [_id] call _poseTick;
        for "_i" from 1 to 8 do {CBA_missionTime=10+_i; [_id] call _poseTick;};
        [count _moves==1 && {count _seeks==0} && {_speed==1},"finite work restarted or froze"] call _check;
        [_preps==1,"repeated weapon preflight"] call _check;
    ''')


@pytest.mark.parametrize('stance,transition',[('STAND','AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon'),('PRONE','AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon')])
def test_standing_or_prone_provider_enters_through_existing_crouch_transition(stance,transition):
    execute(setup()+f'_stance="{stance}";'+r'''
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]]; private _id=_state select 5;
    '''+f'[_moves isEqualTo [[_medic,"{transition}",1]],"missing authored entry transition"] call _check;'+r'''
        _animation="transition"; [_id] call _poseTick; [count _moves==1,"work entered before transition"] call _check;
        CBA_missionTime=12; [_id] call _poseTick;
        [count _moves==2 && {((_moves select 1) select 1)==(_state select 2)},"work did not follow transition"] call _check;
    ''')


@pytest.mark.parametrize('mode,main',[('roll','AinvPknlMstpSnonWnonDnon_medic4'),('inspect','ACME_ChestInspectWork'),('pulse','ACME_StethoscopeWork')])
def test_selected_assessment_states_are_crouch_authored_not_standing_substitutes(mode,main):
    execute(setup()+f'[_medic,"{mode}",6,_patient] call ACME_fnc_treatmentPoseStart;'+r'''
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        [!(_state select 16),"standing substitute enabled"] call _check;
    '''+f'[(_state select 2)=="{main}","authored state mapping changed"] call _check;')


def test_deleted_provider_retires_only_its_handler_jip_and_fatigue_exclusion():
    execute(setup()+r'''
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]]; private _id=_state select 5;
        private _args=+((_handlers select _id) select 1); _args set [0,objNull];
        _events=[]; _moves=[];
        [_args,_id] call ((_handlers select _id) select 0);
        [_id in _removed,"deleted provider handler retained"] call _check;
        [ace_advanced_fatigue_setAnimExclusions isEqualTo ["unrelated"],"deleted provider removed wrong exclusion"] call _check;
        [count _removedJip==1 && {count _moves==0} && {count _events==0},"deleted-provider cleanup had side effects"] call _check;
    ''')


def test_old_owner_tick_cannot_stop_a_new_treatment_episode():
    execute(setup()+r'''
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _old=+(_medic getVariable ["ACME_treatmentPoseState",[]]); private _oldId=_old select 5;
        [_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _new=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
        _moves=[]; _events=[];
        [_oldId] call _poseTick;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _new,"stale tick cleared new pose"] call _check;
        [_oldId in _removed && {count _moves==0} && {count _events==0},"old tick not retired cleanly"] call _check;
    ''')


@pytest.mark.parametrize('local,server,client',[(True,False,7),(False,False,8),(False,True,2)])
def test_hold_receiver_owner_does_not_seek_and_observer_seeks_before_freezing(local,server,client):
    execute(setup()+f'_isLocal={str(local).lower()}; _server={str(server).lower()}; _client={client};'+r'''
        _medic setVariable ["ACME_treatmentPoseEpisode",[12,true]];
        [_medic,12,"hold","work",0.3,7] call ACME_fnc_treatmentPoseSync;
        [_speed==0,"receiver did not freeze"] call _check;
    '''+f'[count _seeks=={int(not local)} && {{count _handlers=={int(not local)}}},"owner replayed or observer failed to track"] call _check;')


@pytest.mark.parametrize('record,episode',[
    ('[13,"hold",-1]','[13,true]'),('[12,"release",-1]','[12,true]'),
    ('[-1,"",-1]','[12,false]'),('[-1,"",-1]','[13,true]'),
])
def test_late_hold_is_rejected_after_new_episode_or_release(record,episode):
    execute(setup()+f'_isLocal=false; _medic setVariable ["ACME_treatmentPoseRemote",{record}]; _medic setVariable ["ACME_treatmentPoseEpisode",{episode}];'+r'''
        [_medic,12,"hold","work",0.3,7] call ACME_fnc_treatmentPoseSync;
        [count _seeks==0 && {count _speedWrites==0} && {count _handlers==0},"stale hold froze provider"] call _check;
    ''')


@pytest.mark.parametrize('episode',['[12,true]','[12,false]','[13,true]'])
def test_jip_hold_waits_for_atomic_episode_then_rechecks_it(episode):
    execute(setup()+r'''
        _isLocal=false;
        [_medic,12,"hold","work",0.3,7] call ACME_fnc_treatmentPoseSync;
        [count _waits==1 && {count _seeks==0},"unknown episode was prematurely applied"] call _check;
    '''+f'_medic setVariable ["ACME_treatmentPoseEpisode",{episode}];'+r'''
        private _job=_waits select 0;
        [(_job select 1) call (_job select 3),"JIP episode wait did not release"] call _check;
        [_job] call _deliver;
    '''+f'[count _seeks=={int(episode=="[12,true]")},"late JIP accepted wrong episode"] call _check;')


@pytest.mark.parametrize('change',[
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_parent=missionNamespace;', '_ownerNum=9;',
    '_medic setVariable ["ACME_treatmentPoseEpisode",[12,false]];',
])
def test_observer_watchdog_releases_dead_seated_transferred_or_ended_hold(change):
    execute(setup()+r'''
        _isLocal=false;
        _medic setVariable ["ACME_treatmentPoseEpisode",[12,true]];
        [_medic,12,"hold","work",0.3,7] call ACME_fnc_treatmentPoseSync;
        private _id=(_medic getVariable ["ACME_treatmentPoseRemote",[]]) select 2;
        _seeks=[];
    '''+change+r'''
        [_id] call _poseTick;
        [_speed==1 && {_id in _removed} && {count _seeks==0},"invalid observer hold retained"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseRemote",[]]) isEqualTo [12,"release",-1],"observer release not recorded"] call _check;
    ''')


def test_duplicate_hold_reuses_one_observer_worker_and_release_is_idempotent():
    execute(setup()+r'''
        _isLocal=false;
        _medic setVariable ["ACME_treatmentPoseEpisode",[12,true]];
        for "_i" from 1 to 4 do {[_medic,12,"hold","work",0.3,7] call ACME_fnc_treatmentPoseSync;};
        [count _handlers==1 && {count _seeks==1},"duplicate hold restarted presentation"] call _check;
        [_medic,12,"release"] call ACME_fnc_treatmentPoseSync;
        private _writes=count _speedWrites;
        [_medic,12,"release"] call ACME_fnc_treatmentPoseSync;
        [_speed==1 && {count _removed==1} && {count _speedWrites==_writes},"duplicate release repeated work"] call _check;
    ''')


WRAPPERS=[
    ('ACME_RollProviderWork','AinvPknlMstpSnonWnonDnon_medic4',0),
    ('ACME_ChestInspectWork','AinvPknlMstpSnonWnonDnon_medic4',0),
    ('ACME_JunctionalWork','AinvPknlMstpSnonWnonDnon_medic4',1),
    ('ACME_StethoscopeWork','UnconsciousReviveMedic_B',1),
    ('ACME_ResponseCheckWork','AinvPknlMstpSnonWrflDr_medic3_old',0),
    ('ACME_AirwayCheckWork','AinvPknlMstpSnonWrflDr_medic4_old',0),
]


@pytest.mark.parametrize('name,parent,looped',WRAPPERS)
def test_work_wrappers_keep_authored_entry_exit_and_weapon_restrictions(name,parent,looped):
    # This is source-defined config, not a rendered RTM. Existing HEMTT coverage
    # compiles the full config separately. Do not revive retired all-looped rules.
    from medication_inventory import parse
    text=(F.parent/'config.cpp').read_text()
    hit=re.search(r'\bclass\s+'+re.escape(name)+r'\s*:\s*\w+\s*\{',text)
    assert hit is not None,name
    tokens=lex(text); pairs=matching(tokens)
    i=next(i for i,t in enumerate(tokens) if t.offset==hit.end()-1 and t.value=='{')
    node=parse(text[hit.start():tokens[pairs[i]].offset+1]+';')['classes'][name]
    props=node['props']
    assert node['parent']==parent and props['looped']==looped
    assert props['disableWeapons']==1 and props['canPullTrigger']==0
    assert 'AmovPknlMstpSnonWnonDnon' in props['interpolateFrom']
    assert 'AmovPknlMstpSnonWnonDnon' in props['interpolateTo'] and 'Unconscious' in props['interpolateTo']
    if name=='ACME_StethoscopeWork':
        assert props['connectTo']==['AmovPknlMstpSnonWnonDnon',0.2]


@pytest.mark.parametrize('change',['_alive=false;','_isLocal=false;','_medic setVariable ["ACE_isUnconscious",true];','_parent=missionNamespace;'])
def test_invalid_provider_stop_releases_freeze_without_forcing_an_exit_move(change):
    execute(setup()+r'''
        private _epoch=[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        _speed=0; _moves=[]; _positions=[];
    '''+change+r'''
        [_medic,"stethoscope",_epoch] call ACME_fnc_treatmentPoseStop;
        [count _moves==0 && {count _positions==0} && {count _waits==0},"invalid provider received exit theatre"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[0]]) isEqualTo [],"invalid provider retained pose state"] call _check;
        [(_events select 0) isEqualTo ["ace_common_setAnimSpeedCoef",[_medic,1]],"freeze release not sent"] call _check;
    ''')
