"""B220 recovery interruption and the real supine provider sequence.

Production SQF executes in SQF-VM. Engine animation, multiplayer transport,
clock and Gear commands are explicit fixtures, not rendered Arma validation.
"""
import pytest
from test_menu_death_lifecycle import adapt, execute, read, ROOT
from test_b215_recovery_position import setup as recovery_setup, begin as recovery_begin
from test_bounded_head_provider_sequence import setup as provider_setup, begin as provider_begin, finish as provider_finish, FIRST, SECOND


def engine_source(name):
    raw = read(name)
    for old,new in {
        'local _patient':'_patientLocal', 'local _p':'_patientLocal',
        'objectParent _patient':'_patientParent', 'objectParent _p':'_patientParent',
        'serverTime':'_serverClock', 'animationState _patient':'_patientAnim',
        'netId _provider':'"medic"', 'finite _rollTime':'true',
        'animationState _p':'_patientAnim', 'lifeState _patient':'"INCAPACITATED"',
    }.items():
        raw=raw.replace(old,new)
    return adapt(raw, 'airway')


def active_recovery():
    return recovery_begin()+'''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01;call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"fixture recovery failed to commit"] call _check;
        _moves=[];_logs=[];
    '''


@pytest.mark.parametrize('phase',['pending','committed'])
def test_interrupt_retires_exact_recovery_without_injecting_supine_or_logging(phase):
    execute(recovery_setup()+(active_recovery() if phase=='committed' else recovery_begin())+'''
        _moves=[];_logs=[];
        [_medic,_patient,false,true,"interrupt"] call ACM_airway_fnc_setRecoveryPosition;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"roll retained clinical recovery"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Episode",""])=="","roll retained committed episode"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"roll retained pending episode"] call _check;
        ["one" in (_patient getVariable ["ACME_patientAnimRetired",[]]),"old recovery not tombstoned"] call _check;
        [count _moves==0 && {count _logs==0},"interrupt moved the patient or produced an unrelated activity result"] call _check;
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        [_medic,_patient,true,false,"apply","one"] call ACM_airway_fnc_setRecoveryPosition;
        [_medic,_patient,true,false,"begin","one"] call ACM_airway_fnc_setRecoveryPosition;
        call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]) && {count _moves==0},"late callback restored recovery"] call _check;
        [!((_handlers select 0) select 2),"retired worker survived"] call _check;
    ''')


@pytest.mark.parametrize('phase',['pending','committed'])
def test_interrupt_preserves_foreign_patient_lock(phase):
    execute(recovery_setup()+(active_recovery() if phase=='committed' else recovery_begin())+'''
        _patient setVariable ["ACME_patientAnimLock",["new","stethoscope","other",4,500]];
        _moves=[];
        [_medic,_patient,false,true,"interrupt"] call ACM_airway_fnc_setRecoveryPosition;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) param [0,""])=="new","interruption released successor"] call _check;
        [count _moves==0,"interruption snapped successor"] call _check;
    ''')


def test_no_recovery_does_not_cancel_independent_head_tilt():
    execute(recovery_setup()+'''
        _patient setVariable ["ACM_airway_HeadTilt_State",true];
        [_medic,_patient,false,true,"interrupt"] call ACM_airway_fnc_setRecoveryPosition;
        [_patient getVariable ["ACM_airway_HeadTilt_State",false],"unrelated HTCL cancelled"] call _check;
        [count _moves==0 && {count _logs==0},"no-op had side effects"] call _check;
    ''')


@pytest.mark.parametrize('phase',['pending','committed'])
@pytest.mark.parametrize('animation',[
    'AinjPpneMstpSnonWrflDnon_rolltofront',
    'AinjPpneMstpSnonWrflDnon_rolltoback',
])
@pytest.mark.parametrize('rejected',[False,True])
def test_real_arbiter_cancels_recovery_only_when_roll_is_accepted(phase,animation,rejected):
    init = recovery_setup()+(active_recovery() if phase=='committed' else recovery_begin())
    init += '''ACME_fnc_headElevCollision={};'''
    init += 'ACME_fnc_patientAnimRequest={'+engine_source('patientAnimRequest')+'};'
    if rejected:
        init += '_patient setVariable ["ACME_patientAnimLock",["foreign","cpr","other",10,500]];'
    execute(init+f'''
        _moves=[];
        private _token=[_patient,"{animation}",1,"chest-seal-roll",_medic,2.3,3,"roll:new"] call ACME_fnc_patientAnimRequest;
        [_token=="{'' if rejected else 'roll:new'}","unexpected roll arbitration"] call _check;
    '''+('''
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Episode",""])=="one" || {((_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) param [0,""])=="one"},"rejected roll cancelled recovery"] call _check;
        [count _moves==0,"rejected roll moved patient"] call _check;
    ''' if rejected else f'''
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"accepted roll retained recovery"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"accepted roll left pending recovery"] call _check;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) param [0,""])=="roll:new","recovery retirement erased new roll"] call _check;
        [count _moves==1 && {{((_moves select 0) select 1)=="{animation}"}},"roll injected a supine snap"] call _check;
    '''))


@pytest.mark.parametrize('active',[False,True])
def test_same_side_roll_still_normalizes_a_side_lying_recovery_patient(active):
    execute(recovery_setup()+'''
        private _actualSide="front";private _requests=[];
        ACME_fnc_chestSealCanPhysicalRoll={true};ACME_fnc_headElevYieldForRoll={};
        ACME_fnc_patientAnimRequest={_requests pushBack _this;"roll:new"};
    '''+'ACME_fnc_chestSealRoll={'+engine_source('chestSealRoll')+'};'+f'''
        _patient setVariable ["ACM_airway_RecoveryPosition_State",{str(active).lower()}];
        [_patient,"front",false,_medic,true] call ACME_fnc_chestSealRoll;
        [count _requests=={int(active)},"matching diagram side skipped recovery normalization or rolled an already-flat patient"] call _check;
    ''')


def roll_event_source():
    text=(ROOT/'addons/airway/XEH_postInit.sqf').read_text()
    block=text.split('GVAR(recoveryRollEH) = ["CAManBase", "AnimStateChanged", {',1)[1].split('}] call CBA_fnc_addClassEventHandler;',1)[0]
    return adapt(block.replace('local _patient','_patientLocal'),'airway')


@pytest.mark.parametrize('animation,cancel',[
    ('AinjPpneMstpSnonWrflDnon_rolltofront',True),
    ('AinjPpneMstpSnonWrflDnon_ROLLTOBACK',True),
    ('foreign_rolltofront_variant',True),
    ('ACM_RecoveryPosition',False),('GestureSpasm4',False),
])
def test_native_animation_event_cancels_rolls_without_waiting_for_worker(animation,cancel):
    execute(recovery_setup()+active_recovery()+f'''
        [_patient,"{animation}"] call {{ {roll_event_source()} }};
        [(_patient getVariable ["ACM_airway_RecoveryPosition_State",false])=={str(not cancel).lower()},"animation event cancellation mismatch"] call _check;
        [count _moves==0,"animation observer requested a competing pose"] call _check;
    ''')


@pytest.mark.parametrize('invalid',['_patientLocal=false;','_patientAlive=false;'])
def test_animation_event_cannot_change_remote_or_dead_patient_record(invalid):
    execute(recovery_setup()+active_recovery()+invalid+f'''
        [_patient,"AinjPpneMstpSnonWrflDnon_rolltoback"] call {{ {roll_event_source()} }};
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"animation observer mutated remote/dead state"] call _check;
        [count _events==0 && {{count _moves==0}},"remote observer dispatched unsolicited work"] call _check;
    ''')


def test_active_watcher_passively_retires_recovery_after_external_pose_change():
    execute(recovery_setup()+active_recovery()+'''
        _patientAnim="acm_lyingstate";call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"external positioning left stale recovery"] call _check;
        [count _moves==0 && {count _logs==0},"passive observer reasserted a body pose"] call _check;
        [!((_handlers select 0) select 2),"active recovery watcher leaked"] call _check;
    ''')


def test_remote_interrupt_is_forwarded_to_patient_owner_without_local_writes():
    execute(recovery_setup()+active_recovery()+'''
        _patientLocal=false;
        [_medic,_patient,false,true,"interrupt"] call ACM_airway_fnc_setRecoveryPosition;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"remote interruption wrote owner state"] call _check;
        [count _events==1 && {((_events select 0 select 1) select 4)=="interrupt"},"owner interruption payload lost"] call _check;
        [count _moves==0,"remote interruption moved patient"] call _check;
    ''')


def commit_setup():
    raw=read('manualPlateCarrierCommit').replace('local _patient','_patientLocal').replace('local _p','_patientLocal').replace('serverTime','_clock')
    raw=raw.replace('vest _patient','_worn').replace('vest _p','_worn').replace('getPosASL _patient','[0,0,0]')
    return '''
        private _patientLocal=true;private _allowed=true;private _worn="";private _clock=10;
        private _presentationCalls=[];private _restores=[];
        ACME_fnc_manualPlateCarrierCanToggle={_allowed};
        ACME_fnc_headElevMedicSeq={_presentationCalls pushBack _this;};
        ACME_fnc_chestAccessVestRestore={_restores pushBack _this;};
        ACME_fnc_chestAccessVestEvent={};
        _patient setVariable ["ACME_manualPlateCarrierLease","manualpc:one"];
        _patient setVariable ["ACME_manualPlateCarrierState","off"];
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest",[]]];
    '''+'ACME_fnc_manualPlateCarrierCommit={'+adapt(raw)+'};'


@pytest.mark.parametrize('restore',[False,True])
@pytest.mark.parametrize('allowed',[False,True])
def test_only_accepted_manual_replace_requests_supine_provider_sequence(restore,allowed):
    expect=restore and allowed
    execute(commit_setup()+f'''
        _allowed={str(allowed).lower()};
        [_medic,_patient,{str(restore).lower()},[7,3,13,2,8]] call ACME_fnc_manualPlateCarrierCommit;
        [count _presentationCalls=={int(expect)},"wrong action played replacement reach"] call _check;
        [count _restores=={int(expect)},"restore transaction changed"] call _check;
    '''+('''
        [_presentationCalls isEqualTo [[_medic,"lower","",[7,3,13,2,8]]],"manual replacement did not reuse exact lower sequence/fingerprint"] call _check;
        [(_patient getVariable ["ACME_manualPlateCarrierState",""])=="restoring","accepted replacement not tracked"] call _check;
    ''' if expect else ''))


def test_manual_replace_forwards_original_provider_fingerprint_unchanged():
    execute(commit_setup()+'''
        _patientLocal=false;
        [_medic,_patient,true,[7,3,13,2,8]] call ACME_fnc_manualPlateCarrierCommit;
        [count _presentationCalls==0 && {count _restores==0},"remote owner performed local replacement"] call _check;
        [count _events==1 && {((_events select 0) select 2) isEqualTo [_medic,_patient,true,[7,3,13,2,8]]},"provider fingerprint dropped in owner routing"] call _check;
    ''')


@pytest.mark.parametrize('fingerprint', ['[1,0,13,0,0]', '[0,1,13,0,0]', '[0,0,9,0,0]', '[0,0]', '[0,0,13]', '[0,0,13,1,0]', '[0,0,13,0,1]'])
def test_stale_replace_presentation_cannot_interrupt_newer_provider(fingerprint):
    execute(provider_setup().replace('serverTime','_clock')+f'''
        private _clock=10;
        [_medic,"lower","",{fingerprint}] call ACME_fnc_headElevMedicSeq;
        [count _jobs==0 && {{_prep==0}} && {{count _moves==0}} && {{_testAnimationSpeed==1}},"stale replacement disturbed provider"] call _check;
    ''')


def test_accepted_replace_uses_real_putdown_reach_and_return_once():
    start=provider_begin('lower').replace('[_medic,"lower"] call ACME_fnc_headElevMedicSeq;', '[_medic,"lower","",[0,0,13,0,0]] call ACME_fnc_headElevMedicSeq;')
    execute(provider_setup().replace('serverTime','_clock')+'private _clock=10;'+start+provider_finish()+'''
        [count _moves==4,"replace sequence repeated an animation"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",false]),"completed reach retained animation owner"] call _check;
        [_testAnimationSpeed==1,"completed replace kept accelerated speed"] call _check;
    ''')


def test_both_ui_entry_points_capture_provider_identity_and_auto_return_stays_separate():
    treatment=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    manual=treatment.split('if (_classname in ["ACME_ManualRemovePlateCarrier", "ACME_ManualReplacePlateCarrier"]) exitWith {',1)[1].split('// Inventory is a UI handoff',1)[0]
    assert 'ACME_treatmentPoseEpoch' in manual and 'ACME_providerLocalityEpoch' in manual and 'serverTime + 3' in manual
    config=(ROOT/'addons/acm_extended/config.cpp').read_text().split('class ACME_ManualReplacePlateCarrier:',1)[1].split('class ACME_OpenPlateCarrierInventory:',1)[0]
    assert 'ACME_treatmentPoseEpoch' in config and 'ACME_providerLocalityEpoch' in config
    for fingerprint in ('ACME_providerTreatmentEpoch', 'ACME_headElev_medicAnimToken'):
        assert fingerprint in config and fingerprint in manual
    assert 'headElevMedicSeq' not in read('manualPlateCarrierAutoReturn')
