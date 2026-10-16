"""Execute optional-presentation ownership and chest-flip integration in SQF-VM.

Production state machines run with explicit native animation, UI, cargo and CBA
delivery adapters. These checks do not render Arma RTMs or exercise real PhysX.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read
from test_historical_pose_lifecycle import pose_source, setup as pose_setup
from test_chestseal_preparation_progress import function, setup as patient_setup, worn_acquire
from test_historical_chest_workspace import code as patient_source
from test_b161_flip_and_breathing import flip_tick
from test_b212_assessment_sequence import function as assessment_function, setup as assessment_setup
from test_b215_recovery_position import setup as recovery_setup


MODES = [
    'response', 'airway', 'assessmentAirway', 'assessmentBreathing', 'roll',
    'chestAccess', 'inspect', 'chestSealWorkspace', 'junctional', 'stethoscope',
    'chestSeal', 'ncdSeat', 'pulse', 'torsoBandage', 'headBandageLeft',
    'headBandageRight', 'directPressureAction', 'feelSkin',
]


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('prone', [False, True])
def test_disabled_presentation_retains_owned_readiness_without_holster_stance_or_freeze(mode, prone):
    execute(pose_setup() + f'''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        _stance="{'PRONE' if prone else 'STAND'}"; _weapon="pistol";
        private _epoch=[_medic,"{mode}",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        [_epoch>0 && {{(_state select 0)==_epoch}} && {{(_state select 3)==3}},
            "disabled presentation failed ownership/readiness contract"] call _check;
        [count _handlers==0 && {{_preps==0}} && {{_weapon=="pistol"}}
            && {{count _moves==0}} && {{count _positions==0}} && {{count _seeks==0}},
            "disabled presentation emitted provider theatre"] call _check;
        [_speed==1 && {{(_speedWrites findIf {{_x!=1}})<0}},
            "ownership-only pose froze or accelerated the provider"] call _check;
        _moves=[]; _positions=[]; _speedWrites=[];
        [_medic,"{mode}",_epoch] call ACME_fnc_treatmentPoseStop;
        [(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo []
            && {{(_medic getVariable ["ACME_treatmentPoseEpisode",[]]) isEqualTo [_epoch,false]}},
            "ownership-only stop retained episode"] call _check;
        [count _moves==0 && {{count _positions==0}} && {{count _speedWrites==0}}
            && {{count _waits==0}}, "ownership-only release changed presentation"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '[_medic,"pulse",-1,_patient] call ACME_fnc_treatmentPoseStart;',
])
def test_late_finite_presentation_timer_cannot_retire_a_new_owner_or_episode(change):
    execute(pose_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _epoch=[_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        [count _waits==1 && {((_waits select 0) select 2)==6},
            "finite ownership did not retain real treatment interval"] call _check;
        private _old=_waits select 0;
    ''' + change + '''
        private _current=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
        [_old] call _deliver;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _current,
            "late timer retired newer ownership"] call _check;
    ''')


def test_finite_presentation_timer_releases_matching_ownership_once():
    execute(pose_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        private _job=_waits select 0; [_job] call _deliver;
        [(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo [],
            "finite ownership never released"] call _check;
        [(_medic getVariable ["ACME_rollProviderCompletedEpoch",-1])==_epoch,
            "finite ownership lost provider roll completion needed by recovery progress"] call _check;
        private _eventsBefore=count _events; [_job] call _deliver;
        [count _events==_eventsBefore && {count _moves==0},
            "duplicate timer repeated presentation or ownership"] call _check;
    ''')


@pytest.mark.parametrize('successor', [False, True])
def test_turning_off_during_visible_pose_releases_its_stance_without_overriding_successor(successor):
    execute(pose_setup() + '''
        private _epoch=[_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        _state set [3,2];
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        _positions=[]; _moves=[];
    ''' + ('_medic setVariable ["ACM_circulation_isPerformingCPR",true];' if successor else '') + f'''
        [_medic,"inspect",_epoch] call ACME_fnc_treatmentPoseStop;
        [_positions isEqualTo {('[]' if successor else '["AUTO"]')} && {{count _moves==0}}
            && {{_speed==1}}, "disabled visible-pose stop stranded stance or touched successor"] call _check;
    ''')


@pytest.mark.parametrize('stage', [2, 3])
def test_live_visible_pose_converts_to_owned_clinical_episode_without_freezing_or_restarting(stage):
    execute(pose_setup() + f'''
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5;
        _state set [3,{stage}]; _state set [14,10.25];
        _medic setVariable ["TEST_clinicalEpisode",["same-clinical-treatment",_epoch]];
        _animation=toLower (_state select 2); _nativeElapsed=2.2; _speed=0;
        CBA_missionTime=11; _positions=[]; _moves=[]; _seeks=[]; _waits=[];
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        [_id] call _poseTick;
        private _passive=_medic getVariable ["ACME_treatmentPoseState",[]];
        [(_passive select 0)==_epoch && {{(_passive select 1)=="roll"}}
            && {{(_passive select 3)==3}} && {{_passive select 21}},
            "mid-toggle conversion changed clinical identity or lost readiness"] call _check;
        [(_passive select 14)==10.25 && {{(_medic getVariable ["TEST_clinicalEpisode",[]]) isEqualTo ["same-clinical-treatment",_epoch]}},
            "mid-toggle conversion reset clinical/contact clock"] call _check;
        [_speed==1 && {{_positions isEqualTo ["AUTO"]}} && {{count _moves==0}} && {{count _seeks==0}}
            && {{_id in _removed}} && {{ace_advanced_fatigue_setAnimExclusions isEqualTo ["unrelated"]}},
            "mid-toggle conversion retained a freeze, stance or fatigue owner"] call _check;
        [count _waits==1 && {{abs (((_waits select 0) select 2)-1.2)<0.00001}},
            "mid-toggle conversion restarted finite provider interval"] call _check;
        missionNamespace setVariable ["ACME_interventionAnimations",true];
        [_id] call _poseTick;
        [_speed==1 && {{count _moves==0}} && {{count _seeks==0}},
            "retired visual handler resumed after re-enable"] call _check;
        [_waits select 0] call _deliver;
        [(_medic getVariable ["ACME_rollProviderCompletedEpoch",-1])==_epoch
            && {{(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo []}},
            "converted finite provider episode never completed"] call _check;
    ''')


def test_disabled_receiver_rejects_late_jip_hold_but_accepts_generation_release():
    execute(pose_setup() + '''
        _isLocal=false;
        _medic setVariable ["ACME_treatmentPoseEpisode",[4,true]];
        [_medic,4,"hold","ACME_StethoscopeWork",0.3,7] call ACME_fnc_treatmentPoseSync;
        [_speed==0,"fixture did not establish remote hold"] call _check;
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        _medic setVariable ["ACME_treatmentPoseEpisode",[5,true]];
        // Old release can be overtaken by the public new-episode variable.
        [_medic,4,"release"] call ACME_fnc_treatmentPoseSync;
        [_medic,5,"release"] call ACME_fnc_treatmentPoseSync;
        private _seekCount=count _seeks;
        [_medic,5,"hold","ACME_StethoscopeWork",0.3,7] call ACME_fnc_treatmentPoseSync;
        [_speed==1 && {count _seeks==_seekCount},
            "late hold re-froze presentation-disabled observer"] call _check;
    ''')


def test_disabled_provider_preparation_acknowledges_without_an_engine_state_probe():
    source = pose_source('chestAccessVestProvider').replace('serverTime', '1000')
    execute(pose_setup() + 'ACME_fnc_chestAccessVestProvider={' + source + '};' + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _epoch=[_medic,_patient,"start",false,"accepted",""] call ACME_fnc_chestAccessVestProvider;
        [(_medic getVariable ["ACME_chestAccessProviderReady",[]]) isEqualTo ["accepted",1000]
            && {_epoch>0} && {count _waits==0} && {count _handlers==0},
            "provider readiness waited for an intentionally suppressed engine state"] call _check;
        [_medic,_patient,"stop",true,"accepted",""] call ACME_fnc_chestAccessVestProvider;
        [(_medic getVariable ["ACME_chestAccessProvider",[1]]) isEqualTo []
            && {(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo []},
            "disabled provider preparation did not release ownership"] call _check;
    ''')


@pytest.mark.parametrize('action,duration', [('CheckAirway', 5.75), ('CheckBreathing', 4)])
@pytest.mark.parametrize('prone', [False, True])
def test_disabled_assessment_keeps_full_clinical_deadline_and_finishes_without_observed_rtm(action, duration, prone):
    source = assessment_setup() + pose_setup()
    for name in ('assessmentStart', 'assessmentStop', 'assessmentTick'):
        source += assessment_function(name).replace('_testAnimationSpeed', '_speed')
    execute(source + f'''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        _stance="{'PRONE' if prone else 'STAND'}"; _prone={str(prone).lower()};
        _request set [3,"{action}"];
        [_request call ACME_fnc_assessmentStart,"assessment start refused disabled presentation"] call _check;
        private _record=_medic getVariable ["ACME_assessment",[]];
        private _pose=_medic getVariable ["ACME_treatmentPoseState",[]];
        call _frame;
        [(_record select 2)==1 && {{count _nativeCalls==1}} && {{(_pose select 2)==""}},
            "assessment waited for an intentionally missing RTM"] call _check;
        [[_nativeArgs] call ACME_fnc_assessmentProgress,"disabled assessment lost native progress condition"] call _check;
        [["{action}",_medic] call ACME_fnc_assessmentTime == {duration},
            "disabled assessment shortened full clinical interval"] call _check;
        [[_nativeArgs,{duration},{duration},{duration}] call ACME_fnc_assessmentCompletion == {duration},
            "disabled assessment extended or failed despite full clinical deadline"] call _check;
        [(_record select 2)!=3,"assessment used early progress-completion shortcut"] call _check;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        [(_medic getVariable ["ACME_assessment",[1]]) isEqualTo []
            && {{(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo []}},
            "completed disabled assessment retained ownership"] call _check;
        [count _moves==0 && {{count _positions==0}} && {{count _seeks==0}},
            "disabled assessment completion emitted stance or theatre"] call _check;
    ''')


@pytest.mark.parametrize('action,duration', [('CheckAirway', 5.75), ('CheckBreathing', 4)])
def test_live_assessment_survives_presentation_disable_with_its_original_native_timer(action, duration):
    source = assessment_setup() + pose_setup()
    for name in ('assessmentStart', 'assessmentStop', 'assessmentTick'):
        source += assessment_function(name).replace('_testAnimationSpeed', '_speed')
    execute(source + f'''
        _request set [3,"{action}"]; _request call ACME_fnc_assessmentStart;
        private _record=_medic getVariable ["ACME_assessment",[]];
        private _pose=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_pose select 5; private _epoch=_pose select 0;
        _pose set [3,3]; _pose set [14,10]; _record set [2,1];
        CBA_missionTime=11; _speed=0;
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        [_id] call _poseTick; call _frame;
        [(_medic getVariable ["ACME_assessment",[]]) isEqualTo _record
            && {{(_record select 0)==_epoch}} && {{(_record select 11)==10}}
            && {{count _nativeCalls==1}}, "disable restarted or cancelled live clinical assessment"] call _check;
        [[_nativeArgs] call ACME_fnc_assessmentProgress,"disable invalidated live assessment progress"] call _check;
        [[_nativeArgs,{duration},{duration},{duration}] call ACME_fnc_assessmentCompletion == {duration},
            "converted assessment failed original clinical deadline"] call _check;
        [_nativeArgs] call ACME_fnc_assessmentFinish;
        [(_medic getVariable ["ACME_assessment",[1]]) isEqualTo [] && {{_speed==1}},
            "converted assessment retained clinical or freeze ownership"] call _check;
    ''')


def test_disabled_menu_presentation_does_not_start_a_separate_stance_controller():
    execute(pose_setup() + 'ACME_fnc_menuPoseStart={' + adapt(read('menuPoseStart')) + '};' + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _started=[_medic,_patient,missionNamespace] call ACME_fnc_menuPoseStart;
        [!_started && {count _positions==0} && {count _moves==0}
            && {count _handlers==0} && {count _waits==0},
            "medical menu bypassed disabled presentation"] call _check;
    ''')


def test_disabled_chest_flip_starts_once_and_finishes_without_an_observed_medic_rtm():
    execute(pose_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _display=missionNamespace;
        private _unlocks=0; private _holds=0; private _rolls=[];
        ACME_fnc_chestSealCanPhysicalRoll={true};
        ACME_fnc_chestSealProviderHoldStart={_holds=_holds+1;90};
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        ACME_fnc_chestSealRender={};
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        _medic setVariable ["ACME_rollProviderToken","roll"];
        uiNamespace setVariable ["ACME_CS_FlipPendingToken","click"];
        uiNamespace setVariable ["ACME_CS_SessionToken","session"];
        uiNamespace setVariable ["ACME_CS_Patient",_patient];
        private _args=[_patient,_medic,_display,"session","click",_epoch,"roll","back",1.23,-1,15];
    ''' + flip_tick('chestSealFlipTick') + '''
        [_args,99] call _flipTick;
        [count _rolls==1 && {(_args select 9)==10}
            && {(uiNamespace getVariable ["ACME_CS_Side",""])=="back"},
            "disabled flip waited for absent medic4 animation"] call _check;
        [_args,99] call _flipTick;
        [count _rolls==1,"disabled flip dispatched duplicate patient roll"] call _check;
        [_waits select 0] call _deliver; _nowTime=13;
        [_args,99] call _flipTick;
        [_unlocks==1 && {_holds==1} && {99 in _removed}
            && {(uiNamespace getVariable ["ACME_CS_FlipPendingToken","bad"])==""},
            "disabled flip never released button or workspace ownership"] call _check;
    ''')


@pytest.mark.parametrize('reenabled', [False, True])
def test_disabled_auscultation_entry_roll_uses_captured_readiness_and_opens_after_patient_interval(reenabled):
    execute(pose_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _rolls=[]; private _opened=[];
        ACME_fnc_chestSealCanPhysicalRoll={true};
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        ACM_breathing_fnc_useStethoscope={_opened pushBack _this;};
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        _medic setVariable ["ACME_rollProviderToken","roll"];
        private _args=[_medic,_patient,"body",_epoch,"roll",1.23,-1,15];
    ''' + f'missionNamespace setVariable ["ACME_interventionAnimations",{str(reenabled).lower()}];'
            + flip_tick('stethoscopeEntryFlipTick') + '''
        [_args,99] call _flipTick;
        [count _rolls==1 && {(_args select 6)==10} && {count _opened==0},
            "scope entry waited for absent medic4 or opened before reposition interval"] call _check;
        _nowTime=13; [_args,99] call _flipTick;
        [count _opened==1 && {99 in _removed},"scope entry never completed logical roll"] call _check;
    ''')


def test_visible_auscultation_entry_still_requires_exact_provider_work_before_patient_roll():
    execute(pose_setup() + '''
        private _rolls=[]; private _opened=[];
        ACME_fnc_chestSealCanPhysicalRoll={true};
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        ACM_breathing_fnc_useStethoscope={_opened pushBack _this;};
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        private _pose=_medic getVariable ["ACME_treatmentPoseState",[]];
        _pose set [3,1];
        _medic setVariable ["ACME_rollProviderToken","roll"];
        private _args=[_medic,_patient,"body",_epoch,"roll",1.23,-1,15];
    ''' + flip_tick('stethoscopeEntryFlipTick') + '''
        [_args,99] call _flipTick;
        [count _rolls==0 && {count _opened==0},"visible entry bypassed exact native work gate"] call _check;
        _animation=toLower (_pose select 2); [_args,99] call _flipTick;
        [count _rolls==1 && {(_args select 6)==10},"observed visible entry failed to start patient roll"] call _check;
        _pose set [3,3]; _nowTime=13; [_args,99] call _flipTick;
        [count _opened==1 && {99 in _removed},"visible entry did not finish native roll interval"] call _check;
    ''')


def test_disabled_scope_side_flip_dispatches_once_and_restores_workspace_without_an_rtm():
    execute(pose_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _display=missionNamespace; private _liveDisplay=_display;
        private _unlocks=0; private _rolls=[];
        ACME_fnc_chestSealCanPhysicalRoll={true};
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        ACME_fnc_patientAnimRequest={"hold"};
        ACME_fnc_stethoscopeSetView={(_this select 0) setVariable ["ACME_stethView",_this select 1];};
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        _medic setVariable ["ACME_rollProviderToken","roll"];
        _display setVariable ["ACME_stethFlipToken","click"];
        _display setVariable ["ACME_stethFlipActive",true];
        private _args=[_patient,_medic,_display,"click",_epoch,"roll","back",1.23,-1,15,false];
    ''' + flip_tick('stethoscopeFlipTick') + '''
        [_args,99] call _flipTick;
        [count _rolls==1 && {(_args select 8)==10} && {_args select 10},
            "scope side flip waited for an absent RTM"] call _check;
        [_args,99] call _flipTick;
        [count _rolls==1,"scope side flip dispatched duplicate roll"] call _check;
        _nowTime=13; [_args,99] call _flipTick;
        [_unlocks==1 && {!(_display getVariable ["ACME_stethFlipActive",true])}
            && {((_medic getVariable ["ACME_treatmentPoseState",[]]) select 1)=="stethoscope"},
            "scope side flip failed to restore ownership-only workspace"] call _check;
    ''')


def test_disabled_roll_provider_cancellation_retires_only_owned_presentation_without_forced_neutral_move():
    execute(pose_setup() + 'ACME_fnc_rollProviderCancel={' + pose_source('rollProviderCancel') + '};' + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        _medic setVariable ["ACME_rollProviderToken","roll"];
        _medic setVariable ["ACME_rollProviderSource","chestSealFlip"];
        [_medic,"chestSealFlip"] call ACME_fnc_rollProviderCancel;
        [(_medic getVariable ["ACME_rollProviderToken","bad"])==""
            && {(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo []},
            "provider cancel retained its ownership-only episode"] call _check;
        [count _moves==0 && {count _seeks==0},
            "ownership-only provider cancellation forced neutral animation"] call _check;
    ''')


def test_disabled_recovery_requires_clinical_success_and_settling_then_persists_without_visible_pose():
    execute(recovery_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _args=[_medic,_patient,"body","RecoveryPosition"];
        _args call ACME_fnc_recoveryPositionStart;
        private _pose=_medic getVariable ["ACME_treatmentPoseState",[]];
        _pose resize 22; _pose set [2,""]; _pose set [3,3]; _pose set [21,true];
        [_args,1,5] call ACME_fnc_recoveryPositionProgress;
        [count _handlers==0,"recovery began before its ordinary last-3.5-second window"] call _check;
        [_args,1.5,5] call ACME_fnc_recoveryPositionProgress;
        call _run; call _run;
        [count _moves==0 && {!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false])},
            "disabled recovery emitted a move or established without native success"] call _check;
        _serverClock=12.01; call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),
            "settling alone credited clinical recovery"] call _check;
        _medic setVariable ["ACME_rollProviderCompletedEpoch",_medic getVariable ["ACME_treatmentPoseEpoch",0]];
        _medic setVariable ["ACME_rollProviderToken",""];
        [_args,true] call ACME_fnc_recoveryPositionFinish; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],
            "successful logical recovery failed clinical commit"] call _check;
        [_patient getVariable ["ACM_airway_HeadTilt_State",false],"logical recovery omitted airway protection"] call _check;
        missionNamespace setVariable ["ACME_interventionAnimations",true]; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],
            "re-enabling presentation erased existing logical recovery"] call _check;
        [count _moves==0 && {count _logs==1},"logical recovery emitted theatre or duplicated clinical log"] call _check;
    ''')


@pytest.mark.parametrize('awake', [False, True])
def test_disabled_patient_roll_cancellation_releases_token_without_a_forced_rest_move(awake):
    execute(patient_setup() + function('patientRollCancel') + f'''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        _patient setVariable ["ACE_isUnconscious",{str(not awake).lower()}];
        _patient setVariable ["ACME_CS_rollToken","accepted"];
        _patient setVariable ["ACME_CS_rollUntil",100];
        [_patient,"front"] call ACME_fnc_patientRollCancel;
        [(_patient getVariable ["ACME_CS_rollToken","bad"])==""
            && {{(_patient getVariable ["ACME_CS_rollUntil",0])==-1}},
            "cancelled logical roll retained in-flight token"] call _check;
        [count _moves==0 && {{count _events==0}}
            && {{(_releases findIf {{(_x select 1)=="accepted"}})>=0}},
            "logical roll cancellation forced a body move or retained lease"] call _check;
    ''')


@pytest.mark.parametrize('context', ['access', 'chestseal'])
def test_disabled_carrier_access_commits_gear_without_body_lift_or_animation_wait(context):
    execute(patient_setup() + 'missionNamespace setVariable ["ACME_interventionAnimations",false];'
            + worn_acquire(context) + f'''
        [count _commits==1 && {{count _waits==0}} && {{count _pins==0}}
            && {{count _animRequests==0}}, "disabled carrier preparation waited for invisible RTM"] call _check;
        [(_patient getVariable ["{'ACME_CS_vestReadyServer' if context == 'chestseal' else 'ACME_chestAccess_readyServer'}",0])==1000,
            "disabled carrier preparation never acknowledged readiness"] call _check;
    ''')


def test_disabled_patient_lease_keeps_arbitration_without_collision_relaxation():
    source = patient_source('patientAnimRequest', server_clock='_serverClock')
    source = source.replace('netId _provider', '"provider"')
    execute(patient_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _collisions=[];
        ACME_fnc_headElevCollision={_collisions pushBack _this;};
    ''' + 'ACME_fnc_doAnim={' + adapt(read('doAnim')) + '};'
            + 'ACME_fnc_patientAnimRequest={' + source + '};' + '''
        private _token=[_patient,"ACME_HeadElevPatientGrab",2,"chest-access-vest",_medic,3,4,"accepted"]
            call ACME_fnc_patientAnimRequest;
        [_token=="accepted" && {((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="accepted"},
            "disabled theatre discarded accepted arbitration"] call _check;
        [count _collisions==0 && {count _moves==0} && {count _events==0},
            "disabled theatre changed collision, animation or speed"] call _check;
        private _denied=[_patient,"ACME_HeadElevPatientGrab",2,"other-controller",objNull,3,4,"denied"]
            call ACME_fnc_patientAnimRequest;
        [_denied=="" && {((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="accepted"},
            "disabled theatre bypassed competing owner"] call _check;
    ''')


def test_virtual_flip_retires_old_seal_callback_without_late_workspace_takeover():
    flip = read('chestSealFlip').replace('local _provider', 'true')
    flip = flip.replace('lifeState _patient', '"HEALTHY"')
    flip = re.sub(r'_display displayCtrl \d+', 'objNull', flip)
    execute(pose_setup() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        private _old=[_medic,"chestSeal",2.65,_patient] call ACME_fnc_treatmentPoseStart;
        private _oldTimer=_waits select 0;
        uiNamespace setVariable ["ACME_CS_Patient",_patient];
        uiNamespace setVariable ["ACME_CS_Medic",_medic];
        uiNamespace setVariable ["ACME_CS_Side","front"];
        uiNamespace setVariable ["ACME_CS_ApplyAnimSerial",9];
        uiNamespace setVariable ["ACME_CS_ApplyGestureUntil",100];
        ACME_fnc_chestSealCanPhysicalRoll={false};
        ACME_fnc_chestSealRender={};
    ''' + 'ACME_fnc_chestSealProviderHoldStart={' + pose_source('chestSealProviderHoldStart') + '};'
            + 'call {' + adapt(flip) + '};' + '''
        private _current=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
        [(uiNamespace getVariable ["ACME_CS_Side",""])=="back"
            && {(uiNamespace getVariable ["ACME_CS_ApplyAnimSerial",0])==10},
            "virtual flip failed to preempt placement generation"] call _check;
        [(_current select 1)=="chestSealWorkspace" && {(_current select 0)>_old},
            "virtual flip left placement pose unowned"] call _check;
        [_oldTimer] call _deliver;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _current,
            "old placement completion took over after virtual flip"] call _check;
    ''')
