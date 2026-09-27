"""Execute actual chest entry, pose and cancellation code with sparse owner ticks.

UI creation, native move timing, vehicles/locality and CBA/network delivery are
explicit boundaries. Patient readiness is an owner acknowledgement supplied by
these tests; patient physical/custody completion has its own runtime tests.
"""
import re
import pytest
import test_historical_pose_lifecycle as pose
from test_menu_death_lifecycle import adapt, execute


def engine(text):
    for var in ('_medic', '_m', '_flipMedic'):
        for old, new in [('local '+var, '_isLocal'), ('alive '+var, '_alive'),
                         ('objectParent '+var, '_parent'), ('animationState '+var, '_animation'),
                         ('netId '+var, '"provider"')]:
            text=re.sub(re.escape(old)+r'\b', lambda _: new, text)
    for var in ('_patient', '_p'):
        for old,new in [('objectParent '+var, '_patientParent'), ('owner '+var, '_patientOwnerFixture')]:
            text=re.sub(re.escape(old)+r'\b', lambda _: new,text)
    text=text.replace('_m distance _p','_distance')
    text=text.replace('serverTime','_serverTime').replace('netId _viewer','"provider"')
    return adapt(text)


def setup():
    code=pose.setup()+r'''
        private _patientParent=objNull; private _patientOwnerFixture=2;
        private _serverTime=10; private _opened=[]; private _preparing=[];
        private _capturedKeys=[];
        CBA_fnc_addKeyHandler={private _id=format ["key%1",count _capturedKeys]; _capturedKeys pushBack [_id,_this select 2]; _id};
        private _exits=[]; private _reopens=[]; private _probes=[];
        CBA_fnc_waitUntilAndExecute={_probes pushBack _this;};
        ACME_fnc_chestAccessPreparing={_preparing pushBack _this;};
        ACME_fnc_minigameOpen={_opened pushBack _this; uiNamespace setVariable ["ACME_CS_DLG",missionNamespace];};
        ACME_fnc_headElevMedicSeq={_exits pushBack _this;};
        ACME_fnc_rollProviderCancel={};
        ACM_GUI_fnc_resumeMedicalMenuPFH={};
        ACME_fnc_reopenMedicalMenu={_reopens pushBack _this;};
        private _entryTick={
            private _id=uiNamespace getVariable ["ACME_CS_EntryPFH",-1];
            if (_id>=0) then {[_id] call _poseTick;};
        };
        private _ack={
            private _tok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
            _patient setVariable ["ACME_CS_ProcedureTokens",[_tok]];
            _patient setVariable ["ACME_CS_ProcedureReadyAt",_serverTime];
        };
    '''
    for name in ('chestAccessVestProvider','chestSealProviderHoldStart','chestSealClose','chestSealOpen'):
        code+='ACME_fnc_'+name+'={'+engine(pose.source(name))+'};\n'
    return code


def test_patient_acknowledgement_has_no_nominal_wall_clock_deadline():
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _tok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        _patient setVariable ["ACME_CS_ProcedureTokens",[_tok]];
        _patient setVariable ["ACME_CS_ProcedureReadyAt",-1];
        {CBA_missionTime=_x; _serverTime=_x; call _entryTick;} forEach [12,22,45,90];
        [count _opened==0 && {(uiNamespace getVariable ["ACME_CS_SessionToken",""])==_tok},"slow valid patient preparation was closed or bypassed"] call _check;
        call _ack; call _entryTick;
        [count _opened==1,"completed patient acknowledgement did not open"] call _check;
        [count _capturedKeys==2 && {{_x in _removed} count ["key0","key1"]==2},"pending keys leaked into minigame"] call _check;
        [(_preparing select 0) select 0 && {!((_preparing select 1) select 0)},"Preparing lifecycle missing"] call _check;
    ''')


def test_provider_fallback_is_bounded_only_after_patient_completion():
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _tok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        _patient setVariable ["ACME_CS_ProcedureTokens",[_tok]];
        private _ep=[_medic,_patient,"start",false,"vest:chestseal:test",uiNamespace getVariable ["ACME_CS_SessionToken",""]] call ACME_fnc_chestAccessVestProvider;
        CBA_missionTime=100; _serverTime=100; call _entryTick;
        [count _opened==0,"presentation fallback bypassed unfinished patient"] call _check;
        call _ack; call _entryTick;
        [count _opened==0,"presentation fallback skipped normal hold opportunity"] call _check;
        CBA_missionTime=104.49; call _entryTick;
        [count _opened==0,"presentation budget shortened"] call _check;
        CBA_missionTime=104.5; call _entryTick;
        [count _opened==1,"stalled presentation still vetoes completed workspace"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) select 1=="chestSealWorkspace","workspace did not receive pose ownership"] call _check;
        [(_medic getVariable ["ACME_chestAccessProvider",[0]]) isEqualTo [],"carrier provider entry not retired"] call _check;
    ''')


def test_normal_frozen_provider_hands_off_at_patient_ack_without_extra_delay():
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _ep=[_medic,_patient,"start",false,"vest:chestseal:test",uiNamespace getVariable ["ACME_CS_SessionToken",""]] call ACME_fnc_chestAccessVestProvider;
        (_medic getVariable ["ACME_treatmentPoseState",[]]) set [3,3];
        call _ack; call _entryTick;
        [count _opened==1,"ready frozen provider was needlessly delayed"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_alive=false;', '_isLocal=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_parent=missionNamespace;', '_patientParent=missionNamespace;', '_distance=3.1;',
    '_patientOwnerFixture=3;', 'ACE_player=missionNamespace;',
    'call ((_capturedKeys select 0) select 1);', 'call ((_capturedKeys select 1) select 1);',
    '_patient setVariable ["ACME_CS_ProcedureTokens",[]];',
])
def test_pending_invalidation_releases_workspace_input_and_preparing(change):
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _tok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        private _pending=uiNamespace getVariable ["ACME_CS_EntryPFH",-1];
        _patient setVariable ["ACME_CS_ProcedureTokens",[_tok]];
        call _entryTick;
    '''+change+r'''
        call _entryTick;
        [count _opened==0 && {(uiNamespace getVariable ["ACME_CS_SessionToken","wrong"])==""},"invalid pending session survived"] call _check;
        [_pending in _removed,"pending PFH was not removed"] call _check;
        [{_x in _removed} count ["key0","key1"]==2,"pending key handlers leaked"] call _check;
        [!((_preparing select ((count _preparing)-1)) select 0),"Preparing banner survived cancel"] call _check;
        [{count _x>=2 && {(_x select 1) isEqualTo "chestSealPatientEnd"}} count _events==1,"cancel did not release patient token exactly once"] call _check;
    ''')


def test_repeated_click_and_stale_key_cannot_reuse_or_cancel_new_session():
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _oldKey=(_capturedKeys select 0) select 1;
        private _tok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        [count _capturedKeys==2 && {(uiNamespace getVariable ["ACME_CS_SessionToken",""])==_tok},"second click restarted pending entry"] call _check;
        call _oldKey; call _entryTick;
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _newTok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        call _oldKey; call _entryTick;
        [_newTok!=_tok && {(uiNamespace getVariable ["ACME_CS_SessionToken",""])==_newTok},"stale key cancelled new entry"] call _check;
    ''')


def test_pending_completion_cannot_replace_unrelated_new_pose():
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _ep=[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        call _ack; call _entryTick;
        [count _opened==0,"pending chest entry stole new intervention"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) select 0==_ep,"cancel stopped new intervention"] call _check;
        [count _exits==0,"cancel Putdown overrode unrelated pose"] call _check;
    ''')


@pytest.mark.parametrize('exit_move',[False, True])
def test_late_native_medic4_observation_freezes_exact_sample_even_after_skipped_end(exit_move):
    execute(pose.setup()+r'''
        private _ep=[_medic,"chestAccess",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5;
        CBA_missionTime=12.7; _nativeElapsed=2.7;
        _animation=toLower (_state select 2); [_id] call _poseTick;
        [(_state select 3)==2,"native entry not observed"] call _check;
    '''+('_animation="amovpknlmstpsnonwnondnon"; _duration=1; CBA_missionTime=30;' if exit_move else 'CBA_missionTime=12.71;')+r'''
        [_id] call _poseTick;
        [(_state select 3)==3 && {_speed==0} && {count _seeks==1},"late owner frame stranded chestAccess before freeze"] call _check;
        [count _seeks==1 && {abs (((_seeks select 0) select 1)-2.2/12)<0.000001},"recovery sought wrong native frame/duration"] call _check;
        [count _moves==1,"recovery replayed finite medic4"] call _check;
    ''')


def test_unobserved_chest_access_retires_without_replaying_animation():
    execute(pose.setup()+r'''
        private _ep=[_medic,"chestAccess",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _id=(_medic getVariable ["ACME_treatmentPoseState",[]]) select 5;
        CBA_missionTime=14.49; [_id] call _poseTick;
        [count (_medic getVariable ["ACME_treatmentPoseState",[]])>0,"presentation retired early"] call _check;
        CBA_missionTime=14.5; [_id] call _poseTick;
        [(_medic getVariable ["ACME_treatmentPoseState",[0]]) isEqualTo [],"unobserved medic4 stayed pending forever"] call _check;
        [count _moves==1,"timeout replayed or inserted neutral animation"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseEpisode",[]]) isEqualTo [_ep,false],"presentation episode did not retire"] call _check;
    ''')


def test_old_sparse_pose_tick_does_not_recover_over_new_epoch():
    execute(pose.setup()+r'''
        [_medic,"chestAccess",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _id=(_medic getVariable ["ACME_treatmentPoseState",[]]) select 5;
        private _ep=[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        _moves=[]; _seeks=[]; CBA_missionTime=90; [_id] call _poseTick;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) select 0==_ep && {count _moves==0} && {count _seeks==0},"stale pose timer recovered over new owner"] call _check;
    ''')


@pytest.mark.parametrize('replace_epoch',[False, True])
def test_pending_abort_preserves_replacement_carrier_episode(replace_epoch):
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _ep=[_medic,_patient,"start",false,"vest:chestseal:old",uiNamespace getVariable ["ACME_CS_SessionToken",""]] call ACME_fnc_chestAccessVestProvider;
        call _entryTick;
    '''+('private _next=[_medic,"chestAccess",-1,_patient] call ACME_fnc_treatmentPoseStart;' if replace_epoch else 'private _next=_ep;')+r'''
        _medic setVariable ["ACME_chestAccessProvider",[_patient,_next,"new-episode"]];
        call _ack; call _entryTick;
        [count _opened==0 && {(uiNamespace getVariable ["ACME_CS_SessionToken",""])==""},"old entry did not retire after replacement"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) select 0==_next && {count _exits==0},"old entry cancellation moved replacement carrier episode"] call _check;
    ''')


def test_chest_access_native_clock_honors_slow_animation_before_held_sample():
    execute(pose.setup()+r'''
        [_medic,"chestAccess",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5;
        _animation=toLower (_state select 2); _nativeElapsed=0.1; [_id] call _poseTick;
        CBA_missionTime=14; _nativeElapsed=1.9; [_id] call _poseTick;
        [(_state select 3)==2 && {count _seeks==0},"wall clock overrode valid native timeline"] call _check;
        _nativeElapsed=2.2; [_id] call _poseTick;
        [(_state select 3)==3 && {count _seeks==1},"native hold sample was missed"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_alive=false;', '_isLocal=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_medic setVariable ["ACME_chestAccessProvider",[_patient,99,"episode"]];',
])
@pytest.mark.parametrize('callback',[1,4])
def test_provider_probe_does_not_publish_from_invalid_or_replaced_owner(change,callback):
    execute(setup()+r'''
        [_medic,_patient,"start",false,"episode"] call ACME_fnc_chestAccessVestProvider;
        private _probe=_probes select 0;
        _animation="ainvpknlmstpsnonwnondnon_medic4";
    '''+change+f'(_probe select 2) call (_probe select {callback});'+r'''
        [(_medic getVariable ["ACME_chestAccessProviderReady",[]]) isEqualTo ["episode",-1],"invalid provider published presentation readiness"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    'call ((_capturedKeys select 0) select 1);',
    '[] call ACME_fnc_chestSealClose;',
    '[] call ACME_fnc_chestSealClose; [_medic,_patient] call ACME_fnc_chestSealOpen;',
    'call _ack; call _entryTick;',
])
def test_late_carrier_start_cannot_replace_cancelled_reopened_or_open_workspace(change):
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _tok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
    '''+change+r'''
        private _before=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
        _moves=[];
        private _result=[_medic,_patient,"start",false,"vest:chestseal:old",_tok] call ACME_fnc_chestAccessVestProvider;
        [_result==-1 && {count _moves==0} && {(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _before},"late carrier start replaced current animation ownership"] call _check;
    ''')


def test_local_carrier_start_is_allowed_before_pending_pfh_registration():
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _tok=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        uiNamespace setVariable ["ACME_CS_EntryPFH",-1];
        private _result=[_medic,_patient,"start",false,"vest:chestseal:current",_tok] call ACME_fnc_chestAccessVestProvider;
        [_result>=0 && {(_medic getVariable ["ACME_treatmentPoseState",[]]) select 1=="chestAccess"},"synchronous patient owner delivery lost provider entry"] call _check;
    ''')


def test_stale_pending_tick_cannot_remove_reopened_entry_resources():
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _old=uiNamespace getVariable ["ACME_CS_EntryPFH",-1];
        [] call ACME_fnc_chestSealClose;
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _new=uiNamespace getVariable ["ACME_CS_EntryPFH",-1];
        _removed=[]; [_old] call _poseTick;
        [(uiNamespace getVariable ["ACME_CS_EntryPFH",-1])==_new && {!(_new in _removed)},"stale tick removed reopened entry PFH"] call _check;
        [count (uiNamespace getVariable ["ACME_CS_EntryKeys",[]])==2 && {count _removed==1},"stale tick removed reopened inputs"] call _check;
    ''')


@pytest.mark.parametrize('cancel',[False, True])
def test_pending_entry_cannot_adopt_foreign_carrier_before_its_first_tick(cancel):
    execute(setup()+r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _ep=[_medic,"chestAccess",-1,_patient] call ACME_fnc_treatmentPoseStart;
        _medic setVariable ["ACME_chestAccessProvider",[_patient,_ep,"vest:access:foreign"]];
    '''+('call ((_capturedKeys select 0) select 1);' if cancel else 'call _ack;')+r'''
        call _entryTick;
        [count _opened==0 && {(uiNamespace getVariable ["ACME_CS_SessionToken",""])==""},"foreign carrier was adopted as chest seal preparation"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) select 0==_ep && {count _exits==0},"pending cleanup stopped a foreign carrier episode"] call _check;
    ''')
