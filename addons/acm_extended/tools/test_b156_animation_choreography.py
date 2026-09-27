"""Execute animation timing and lease ownership. Native RTM rendering remains an Arma MP check."""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, core
from test_historical_pose_lifecycle import setup as pose_setup, source


def patient_setup():
    code = r'''
        private _patientLocal=true; private _serverTime=10;
        private _patientParent=objNull; private _patientRequests=[];
        private _speedEvents=[];
        ACME_fnc_doAnim={_patientRequests pushBack _this;};
        ACME_fnc_ownerDispatch={_events pushBack _this;};
        CBA_fnc_globalEvent={_speedEvents pushBack _this;};
        CBA_fnc_waitAndExecute={_waits pushBack _this;};
        private _job={params ["_i"]; private _j=_waits select _i; (_j select 1) call (_j select 0);};
    '''
    for name in ('patientAnimRequest', 'patientAnimRelease'):
        text = source(name)
        for var in ('_patient', '_p'):
            text = re.sub(r'\blocal '+re.escape(var)+r'\b', '_patientLocal', text)
            text = re.sub(r'\bobjectParent '+re.escape(var)+r'\b', '_patientParent', text)
        text = text.replace('netId _provider', '"provider"').replace('netId _patient', '"patient"')
        text = text.replace('serverTime', '_serverTime')
        code += f'ACME_fnc_{name}={{'+adapt(text)+'};\n'
    return code


def test_release_arriving_before_remote_request_cannot_reacquire_patient():
    execute(patient_setup()+r'''
        [_patient,"cancelled"] call ACME_fnc_patientAnimRelease;
        private _result=[_patient,"ACME_HeadElevPatientGrab",2,"chest-access-vest",_medic,2,4,"cancelled"] call ACME_fnc_patientAnimRequest;
        [_result=="" && {count _patientRequests==0} && {_testAnimationSpeed==1},"late request revived cancelled lease"] call _check;
    ''')


def test_rejected_lease_cannot_change_animation_speed():
    execute(patient_setup()+r'''
        [_patient,"ACME_HeadElevPatientGrab",2,"chest-access-vest",_medic,2,4,"first"] call ACME_fnc_patientAnimRequest;
        _testAnimationSpeed=0;
        private _result=[_patient,"ACME_HeadElevPatientRelease",2,"other",objNull,2,1,"lower"] call ACME_fnc_patientAnimRequest;
        [_result=="" && {count _patientRequests==1} && {_testAnimationSpeed==0},"rejected lease changed presentation"] call _check;
    ''')


def test_old_release_and_expiry_preserve_new_lease_rate():
    execute(patient_setup()+r'''
        [_patient,"ACME_HeadElevPatientGrab",2,"chest-access-vest",_medic,2,4,"first"] call ACME_fnc_patientAnimRequest;
        [_patient,"ACME_HeadElevPatientRelease",2,"chest-access-vest",_medic,5,4,"second"] call ACME_fnc_patientAnimRequest;
        [_patient,"first"] call ACME_fnc_patientAnimRelease;
        _serverTime=13; [0] call _job;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="second" && {_testAnimationSpeed==1.5},"old timer/release reset new lease"] call _check;
        [_patient,"second"] call ACME_fnc_patientAnimRelease;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo [] && {_testAnimationSpeed==1},"matching release leaked rate/lock"] call _check;
    ''')


def test_lease_expiry_restores_rate_but_allows_late_stage_of_valid_transaction():
    execute(patient_setup()+r'''
        [_patient,"ACME_HeadElevPatientGrab",2,"chest-access-vest",_medic,1,4,"transaction"] call ACME_fnc_patientAnimRequest;
        _serverTime=12; [0] call _job;
        [_testAnimationSpeed==1 && {(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo []},"expired movement left rate/lock"] call _check;
        private _result=[_patient,"ACME_HeadElevPatientRelease",2,"chest-access-vest",_medic,1,4,"transaction"] call ACME_fnc_patientAnimRequest;
        [_result=="transaction" && {_testAnimationSpeed==1.5},"sparse-frame continuation was cancelled by expiry"] call _check;
    ''')


def test_frozen_sample_uses_native_timeline_at_accelerated_rate_and_hold_is_wall_time():
    execute(pose_setup()+r'''
        ACME_poseStopAfterHold set ["inspect",6];
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5; _animation=toLower (_state select 2);
        _nativeElapsed=2.1; CBA_missionTime=11.4; [_id] call _poseTick;
        _nativeElapsed=2.2; CBA_missionTime=11.467; [_id] call _poseTick;
        [(_state select 3)==3 && {_speed==0} && {abs ((_state select 12)*12-2.2)<0.001},"accelerated sample incorrect"] call _check;
        CBA_missionTime=17.466; [_id] call _poseTick;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isNotEqualTo [],"clinical hold shortened with animation"] call _check;
        CBA_missionTime=17.468; [_id] call _poseTick;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo [],"clinical hold failed to finish"] call _check;
    ''')


@pytest.mark.parametrize('stance,native', [('STAND',.65),('PRONE',1.116)])
def test_provider_entry_timer_matches_rate(stance,native):
    execute(pose_setup()+f'_stance="{stance}";'+r'''
        [_medic,"roll",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
    '''+f'[abs (((_state select 8)-10)-({native}/1.5))<0.001 && {{_speed==1.5}},"entry timing/rate mismatch"] call _check;')


def test_native_continuous_exit_cannot_reset_new_treatment():
    execute('ACM_core_fnc_beginContinuousAction={'+core('beginContinuousAction')+'};'+r'''
        CBA_fnc_waitAndExecute={_waits pushBack _this;};
        ACME_fnc_providerStanceOwned={false};
        [[_medic,_patient,"head"],{},{},{}] call ACM_core_fnc_beginContinuousAction;
        [_testAnimationSpeed==1.5 && {"ACM_GenericContinuous" in _moves},"native continuous rate/idle mismatch"] call _check;
        ACM_core_ContinuousAction_Active=false;
        private _h=_handlers select 0;
        [_h select 1,0] call (_h select 0);
        [abs (((_waits select 0) select 2)-(0.85/1.5))<0.001,"native exit timer not scaled"] call _check;
        _medic setVariable ["ACME_treatmentPoseEpoch",8]; _testAnimationSpeed=0;
        private _j=_waits select 0; (_j select 1) call (_j select 0);
        [_testAnimationSpeed==0,"old continuous exit reset new frozen treatment"] call _check;
    ''')


def manual_support_setup():
    text=source('headElevHoldStart')
    for var in ('_medic','_m'):
        for old,new in [('local '+var,'_isLocal'),('alive '+var,'_alive'),
                        ('objectParent '+var,'_parent'),('animationState '+var,'_animation'),
                        ('getAnimSpeedCoef '+var,'_speed'),('currentWeapon '+var,'_weapon'),
                        ('netId '+var,'"provider"')]:
            text=re.sub(re.escape(old)+r'\b',lambda _:new,text)
        text=re.sub(re.escape(var)+r' setAnimSpeedCoef ([^;]+);',r'_speed=(\1);',text)
        text=re.sub(re.escape(var)+r' setUnitPos ([^;]+);',r'_positions pushBack (\1);',text)
        text=text.replace(var+' selectWeapon "";','_weapon="";')
    text=text.replace('isPlayer _medic','true').replace('inputAction _x','0').replace('_medic != ACE_player','_medic isNotEqualTo ACE_player')
    text=text.replace('finite _releaseTime','true')
    return pose_setup()+r'''
        private _continuous=[]; private _dispatches=[];
        ACME_fnc_ownerDispatch={_dispatches pushBack _this;};
        ACM_core_fnc_beginContinuousAction={
            _continuous=_this; ACM_core_ContinuousAction_Active=true;
            (_this select 0) call (_this select 1);
        };
        _patient setVariable ["ACME_headElev_poseToken","support"];
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_hold",[_medic,"support"]];
    '''+'ACME_fnc_headElevHoldStart={'+adapt(text)+'};\n'


def test_manual_head_support_publishes_held_sample_and_retires_it_on_cancel():
    execute(manual_support_setup()+r'''
        [_medic,_patient,"head","support",true] call ACME_fnc_headElevHoldStart;
        private _id=_medic getVariable ["ACME_headElev_manualAnimPFH",-1];
        [_id>=0 && {_speed==1.5},"manual support did not acquire moving presentation"] call _check;
        [_id] call _poseTick;
        _animation="ainvpknlmstpsnonwnondnon_putdown";
        [_id] call _poseTick;
        private _holdPackets=_events select {(_x select 0)=="ACME_treatmentPoseSync" && {((_x select 1) select 2)=="hold"}};
        [count _holdPackets==1 && {_speed==0},"manual frozen sample not replicated"] call _check;
        private _packet=(_holdPackets select 0) select 1;
        [(_packet select 3)=="AinvPknlMstpSnonWnonDnon_Putdown" && {(_packet select 4)==0},"manual sample payload incorrect"] call _check;
        private _epoch=_packet select 1;
        ACM_core_ContinuousAction_Active=false;
        (_continuous select 0) call (_continuous select 2);
        [(_medic getVariable ["ACME_treatmentPoseEpisode",[]]) isEqualTo [_epoch,false] && {_id in _removed},"cancel retained manual hold episode/handler"] call _check;
        [_speed==1.5 && {count _speedWaits==1},"manual exit speed not bounded"] call _check;
        [_speedWaits select 0] call _deliver;
        [_speed==1,"manual exit left provider accelerated"] call _check;
        [_waits select 0] call _deliver;
        [(_positions select (count _positions-1))=="AUTO","manual exit left stance locked"] call _check;
    ''')


def owner_adoption_setup():
    text=source('ownerInit')
    start=text.index('        private _animLock = _unit getVariable ["ACME_patientAnimLock", []];')
    end=text.index('        [_unit] call ACME_fnc_ownerRegister;',start)
    text=text[start:end].replace('serverTime','_serverTime').replace('local _unit','_patientLocal')
    return patient_setup()+'private _adopt={params ["_unit"];'+adapt(text)+'};\n'


def test_locality_transfer_reinstalls_live_lease_expiry_and_does_not_reset_new_owner_lease():
    execute(owner_adoption_setup()+r'''
        _patient setVariable ["ACME_patientAnimLock",["transferred","head-elev-lift","provider",1,12,1.5]];
        [_patient] call _adopt;
        [_testAnimationSpeed==1.5 && {((_waits select 0) select 2)==2},"new owner did not adopt rate and remaining expiry"] call _check;
        [_patient,"ACME_HeadElevPatientRelease",2,"head-elev-lower",_medic,8,1,"new"] call ACME_fnc_patientAnimRequest;
        _serverTime=13; [0] call _job;
        [_testAnimationSpeed==1.5 && {((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="new"},"old transfer expiry cleared new lease"] call _check;
    ''')


@pytest.mark.parametrize('expired',[False,True])
def test_locality_transfer_releases_orphan_or_expired_speed(expired):
    fixture='["old","head-elev-lift","provider",1,9,1.5]' if expired else '[]'
    execute(owner_adoption_setup()+f'_patient setVariable ["ACME_patientAnimLock",{fixture}];'+r'''
        _patient setVariable ["ACME_patientAnimSpeedToken","old"]; _testAnimationSpeed=1.5;
        [_patient] call _adopt;
        [_testAnimationSpeed==1 && {(_patient getVariable ["ACME_patientAnimSpeedToken","bad"])==""},"locality transfer left orphan acceleration"] call _check;
    ''')


def test_carrier_return_rejected_lease_does_not_change_foreign_presentation():
    from test_historical_chest_workspace import setup as workspace_setup, function
    execute(workspace_setup()+function('chestSealCanPhysicalRoll')+function('chestAccessVestRestore')+r'''
        _actualSide="front"; _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[]]];
        _patient setVariable ["ACME_patientAnimLock",["foreign","other","",5,100]];
        _leaseAllowed=false;
        [_patient,false,_medic,"access",true] call ACME_fnc_chestAccessVestRestore;
        [count _events==0 && {count _waits==1} && {count _animRequests==1},"rejected restore changed foreign speed or queued motion"] call _check;
        _patient setVariable ["ACME_patientAnimLock",[]]; _leaseAllowed=true;
        private _retry=_waits deleteAt 0;
        [_retry] call _deliver;
        [count _animRequests==2 && {count _waits==3},"carrier restore did not resume exact owned transaction"] call _check;
    ''')


def test_natural_roll_completion_retires_ownership_before_exit_speed_release():
    from test_historical_pose_lifecycle import pose_source
    text=re.sub(r'inputAction "[^"]+"','0',pose_source('rollProviderStart'))
    execute(pose_setup()+'ACME_fnc_rollProviderStart={'+text+'};'+r'''
        [_medic,"test",_patient] call ACME_fnc_rollProviderStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _poseId=_state select 5;
        private _rollId=_medic getVariable ["ACME_rollProviderPFH",-1];
        _animation=toLower (_state select 2); _nativeElapsed=0;
        [_poseId] call _poseTick;
        CBA_missionTime=11.467; _nativeElapsed=2.2; [_poseId] call _poseTick;
        CBA_missionTime=11.718; [_poseId] call _poseTick;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo [],"natural roll failed to finish"] call _check;
        [_rollId] call _poseTick;
        [!(_medic getVariable ["ACME_rollProviderActive",true]) && {_rollId in _removed},"finished roll blocked subsequent controller"] call _check;
        [_speedWaits select 0] call _deliver;
        [_speed==1,"finished roll prevented bounded speed release"] call _check;
    ''')


def native_bridge_setup():
    from test_historical_weapon_preflight import setup as weapon_setup, engine
    return weapon_setup()+r'''
        private _rateEvents=[]; private _rateWaits=[];
        CBA_fnc_addEventHandler={_rateEvents pushBack _this;};
        CBA_fnc_waitAndExecute={
            if ((str (_this select 0) find "ACME_nativeTreatmentRate")>=0) then {_rateWaits pushBack _this;} else {_waits pushBack _this;};
        };
        ACM_core_fnc_cprActive={false}; ACM_core_fnc_bvmActive={false};
    '''+engine(source('registerProviderStanceReleaseRuntime'))+r'''
        private _complete={
            private _matches=_rateEvents select {(_x select 0)=="ace_treatmentSucceded" && {(str (_x select 1) find "ACME_nativeTreatmentRate")>=0}};
            [_medic,_patient,"LeftArm","FieldDressing"] call ((_matches select 0) select 1);
        };
        private _rateTick={private _j=_rateWaits select _this; (_j select 1) call (_j select 0);};
    '''


@pytest.mark.parametrize('state', ['ACM_GenericContinuous','ACM_ProneContinuous'])
def test_native_continuous_empty_hands_can_launch_treatment_without_holster_wait(state):
    execute(native_bridge_setup()+f'_animNowFixture="{state}";'+r'''
        _weaponNow=""; _stanceNow="CROUCH";
        private _started=[_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        [_started && {count _nativeCalls==1} && {count _timers==0} && {count _holsters==0},"native continuous idle trapped treatment in preflight"] call _check;
        [_testAnimationSpeed==1.5 && {count (_medic getVariable ["ACME_nativeTreatmentRate",[]])==5},"native finite action lost rate ownership"] call _check;
    ''')


def test_native_finite_completion_releases_speed_after_bounded_exit():
    execute(native_bridge_setup()+r'''
        _animNowFixture="ACM_GenericContinuous"; _weaponNow=""; _stanceNow="CROUCH";
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        call _complete;
        [_testAnimationSpeed==1.5 && {count _rateWaits==1} && {abs (((_rateWaits select 0) select 2)-(0.85/1.5))<0.001},"native finite exit rate/window wrong"] call _check;
        0 call _rateTick;
        [_testAnimationSpeed==1 && {(_medic getVariable ["ACME_nativeTreatmentRate",[]]) isEqualTo []},"native finite completion left accelerated rate"] call _check;
    ''')


def test_old_native_completion_cannot_clear_new_action_or_frozen_pose():
    execute(native_bridge_setup()+r'''
        _animNowFixture="ACM_GenericContinuous"; _weaponNow=""; _stanceNow="CROUCH";
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        call _complete;
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        private _new=+(_medic getVariable ["ACME_nativeTreatmentRate",[]]);
        0 call _rateTick;
        [_testAnimationSpeed==1.5 && {(_medic getVariable ["ACME_nativeTreatmentRate",[]]) isEqualTo _new},"old completion reset new native action"] call _check;
        call _complete;
        _medic setVariable ["ACME_treatmentPoseEpoch",9]; _testAnimationSpeed=0;
        1 call _rateTick;
        [_testAnimationSpeed==0,"native completion thawed newer frozen pose"] call _check;
    ''')


def test_preflight_abort_and_native_rejection_release_only_their_own_rate():
    execute(native_bridge_setup()+r'''
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        [_testAnimationSpeed==1.5,"ordinary holster/preparation was not accelerated"] call _check;
        0 call _timeout;
        [_testAnimationSpeed==1 && {!(_medic getVariable ["ACME_treatmentPreflightActive",true])},"preflight timeout left rate or reservation"] call _check;
        _animNowFixture="ACM_GenericContinuous"; _weaponNow=""; _stanceNow="CROUCH"; _nativeAccepted=false;
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        [_testAnimationSpeed==1 && {(_medic getVariable ["ACME_nativeTreatmentRate",[]]) isEqualTo []},"rejected treatment retained accelerated rate"] call _check;
    ''')
