"""Run flip completion and carrier retry regressions with actual SQF closures.

The queue fixture retains CBA's live forEach behavior, including callbacks appended
while it is iterating. A test-only budget stops the old infinite path safely.
Engine animation, UI controls and object state remain explicit boundaries.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read
from test_historical_core_boundaries import block_at
from test_chestseal_preparation_progress import setup as patient_setup, function
from test_historical_pose_lifecycle import setup as pose_setup


def live_queue():
    return r'''
        private _conditions=[]; private _delayed=[]; private _queueAdds=0;
        CBA_fnc_waitUntilAndExecute={
            _queueAdds=_queueAdds+1;
            // This is a test escape hatch, not production behavior.
            if (_queueAdds<=30) then {_conditions pushBack _this;};
        };
        CBA_fnc_waitAndExecute={_delayed pushBack _this;};
        private _runConditions={
            {
                if ((_x select 2) call (_x select 0)) then {
                    (_x select 2) call (_x select 1);
                    _conditions set [_forEachIndex,objNull];
                };
            } forEach _conditions;
            _conditions=_conditions-[objNull];
        };
    '''


@pytest.mark.parametrize('name,closure',[
    ('chestAccessVestAcquire','_beginPatient'),
    ('chestAccessVestRestore','_beginRestore'),
])
def test_permanent_animation_denial_cannot_spin_in_one_cba_frame(name,closure):
    text=function(name)
    start=text.index('private '+closure+' = {')
    opening=text.index('{',start)
    definition=text[start:opening]+block_at(text,opening)+';'
    args = ('[_patient,objNull,"access","saved","prop","pfh","busy","ready","retired",'
            '{},0.8,0.04,0.9,1.5,1.74,_beginPatient,true]') if name.endswith('Acquire') else (
            '[_patient,objNull,"access",["Vest_A",[]],"saved","prop","busy","ready","pfh","retired",'
            '0.8,0.02,0.9,1.5,1.72,{},_beginRestore]')
    execute(patient_setup()+function('patientAnimRequest')+live_queue()+definition+r'''
        _patient setVariable ["busy","retired"];
        _patient setVariable ["ACME_patientAnimLock",[]];
        _patient setVariable ["ACME_patientAnimRetired",["retired"]];
        private _requests=0;
        // Execute the actual arbiter's retired-token rejection with no competing lock.
        private _requestNative=ACME_fnc_patientAnimRequest;
        ACME_fnc_patientAnimRequest={_requests=_requests+1; _this call _requestNative};
    '''+args+' call '+closure+';'+r'''
        [_requests==1 && {count _conditions==1},"initial rejected claim not observed"] call _check;
        call _runConditions;
        [_requests==1 && {_queueAdds==1},"rejected claim repeatedly ran in the same CBA frame"] call _check;
        [count _conditions==0 && {count _delayed==1},"retry was not moved out of live condition iteration"] call _check;
        [((_delayed select 0) select 2)>0,"retry permits a zero-delay spin"] call _check;
        private _retry=_delayed deleteAt 0;
        // Exact transaction cancellation must retire the queued retry, too.
        _patient setVariable ["busy","replacement"];
        (_retry select 1) call (_retry select 0);
        [_requests==1 && {count _conditions==0} && {count _delayed==0},"cancelled retry acquired a new body owner"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientAlive=false;', '_parent=missionNamespace;',
    '_patient setVariable ["ACE_isUnconscious",false]; _animation="amovpercmstpsnonwnondnon";',
])
def test_delayed_breathing_lift_rechecks_patient_before_requesting_animation(change):
    execute(patient_setup()+function('chestAccessVestAcquire')+r'''
        _vest="Vest_A"; _loadout set [4,["Vest_A",[]]];
        [_patient,objNull,"access",true,"checkbreathing"] call ACME_fnc_chestAccessVestAcquire;
        private _start=call _take;
    '''+change+r'''
        _leaseAllowed=false;
        [_start] call _deliver;
        [count _animRequests==0 && {count _pins==0},"ineligible patient still received delayed lift"] call _check;
        [count _waits==0 && {count _commits==1},"nonanimated gear completion rearmed a denied lift"] call _check;
        [(_patient getVariable ["ACME_chestAccess_vestBusy","bad"])=="","ineligible lift left busy marker"] call _check;
    ''')


def test_restore_losing_patient_during_foreign_lease_wait_restores_gear_without_retry():
    execute(patient_setup()+function('chestAccessVestRestore')+r'''
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[]]];
        _patient setVariable ["ACME_patientAnimLock",["foreign","other","provider",8,1100]];
        _leaseAllowed=false;
        [_patient,false,objNull,"access",true] call ACME_fnc_chestAccessVestRestore;
        private _waiting=call _take;
        _patientAlive=false; _serverClock=1101;
        [_waiting] call _deliver;
        private _retry=call _take; [_retry] call _deliver;
        [count _waits==0 && {count _animRequests==1},"dead restoration kept retrying animation"] call _check;
        [_vest=="Vest_A" && {count _loadouts==1},"carrier was lost on death during restoration"] call _check;
        [(_patient getVariable ["ACME_chestAccess_vestBusy","bad"])=="","dead restoration retained busy marker"] call _check;
    ''')


def flip_tick(name):
    source=read(name)
    source=source.replace('findDisplay 81000','_liveDisplay')
    source=re.sub(r'_display displayCtrl \d+', '"button"', source)
    source=source.replace('_button ctrlEnable true;', '_unlocks=_unlocks+1;')
    source=re.sub(r'_button ctrlSetText "[^"]+";', '', source)
    for command,replacement in [('local _provider','_isLocal'),('alive _provider','_alive'),
                                 ('objectParent _provider','_parent'),('animationState _provider','_animation'),
                                 ('netId _provider','"medic"'),('animationState _patient','"ACM_LyingState"')]:
        source=source.replace(command,replacement)
    source=source.replace('_provider distance _patient','_distance')
    return 'private _flipTick={'+adapt(source)+'};'


def flip_setup(name,side):
    source=pose_setup()+r'''
        private _display=missionNamespace; private _liveDisplay=_display;
        private _unlocks=0; private _holds=0; private _rolls=[];
        ACME_fnc_chestSealCanPhysicalRoll={true};
        ACME_fnc_chestSealProviderHoldStart={_holds=_holds+1; 90};
        ACME_fnc_patientAnimRequest={"hold"};
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        ACME_fnc_chestSealRender={};
        ACME_fnc_stethoscopeSetView={};
        private _ep=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5;
        _medic setVariable ["ACME_rollProviderToken","roll"];
        _animation=toLower (_state select 2);
        [_id] call _poseTick;
        private _flipArgs=[];
    '''
    if name=='chestSealFlipTick':
        source+=r'''
            uiNamespace setVariable ["ACME_CS_FlipPendingToken","click"];
            uiNamespace setVariable ["ACME_CS_SessionToken","session"];
            uiNamespace setVariable ["ACME_CS_Patient",_patient];
        '''+f'_flipArgs=[_patient,_medic,_display,"session","click",_ep,"roll","{side}",1.23,10,15.5];'
    else:
        source+=r'''
            _display setVariable ["ACME_stethFlipToken","click"];
            _display setVariable ["ACME_stethFlipActive",true];
        '''+f'_display setVariable ["ACME_stethView","{side}"]; _flipArgs=[_patient,_medic,_display,"click",_ep,"roll","{side}",1.23,10,15.5,true];'
    return source+flip_tick(name)


@pytest.mark.parametrize('name',['chestSealFlipTick','stethoscopeFlipTick'])
@pytest.mark.parametrize('side',['front','back'])
@pytest.mark.parametrize('sparse',[False,True])
def test_flip_unlocks_after_completed_roll_even_if_hold_was_cleared(name,side,sparse):
    source=flip_setup(name,side)
    if sparse:
        source+=r'''
            // The work state was observed, then a sparse frame skips its final sample.
            _animation="amovpknlmstpsnonwnondnon";
            CBA_missionTime=12; [_id] call _poseTick;
            [count _seeks==0,"completed roll was visibly replayed"] call _check;
        '''
    else:
        source+=r'''
            CBA_missionTime=11.5; _nativeElapsed=2.2; [_id] call _poseTick;
            CBA_missionTime=11.8; [_id] call _poseTick;
        '''
    execute(source+r'''
        [(_medic getVariable ["ACME_treatmentPoseState",[0]]) isEqualTo [],"test did not retire short hold"] call _check;
        [(_medic getVariable ["ACME_rollProviderCompletedEpoch",-1])==_ep,"completed roll lost its signal"] call _check;
        // Model the roll watcher retiring the now-finished provider episode.
        _medic setVariable ["ACME_rollProviderToken",""];
        _nowTime=12;
        [_flipArgs,99] call _flipTick;
        [_unlocks==1 && {99 in _removed},"finished flip waited for 5.5-second timeout"] call _check;
        [count _rolls==0,"completion dispatched another patient roll"] call _check;
    ''')


@pytest.mark.parametrize('name',['chestSealFlipTick','stethoscopeFlipTick'])
@pytest.mark.parametrize('case',['patient_not_done','old_epoch','running','cancelled_early'])
def test_flip_cannot_reuse_old_or_incomplete_provider_completion(name,case):
    source=flip_setup(name,'back')
    change={
        'patient_not_done':'_medic setVariable ["ACME_rollProviderCompletedEpoch",_ep]; _nowTime=10.5;',
        'old_epoch':'_medic setVariable ["ACME_rollProviderCompletedEpoch",_ep-1]; _nowTime=12;',
        'running':'_nowTime=12;',
        'cancelled_early':'[_medic,"roll",_ep] call ACME_fnc_treatmentPoseStop; _nowTime=12;',
    }[case]
    execute(source+change+r'''
        [_flipArgs,99] call _flipTick;
        [_unlocks==0,"incomplete/old roll unlocked current flip"] call _check;
    ''')
