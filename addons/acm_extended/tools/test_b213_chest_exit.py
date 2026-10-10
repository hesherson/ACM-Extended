"""Run the provider exit and patient restore gate with actual SQF controllers.

Animation names, native phase/duration, input, clocks and transport are explicit
engine boundaries. These checks do not render RTMs or simulate Arma networking.
"""
import re

import pytest

from test_bounded_head_provider_consciousness import setup as head_setup
from test_bounded_head_provider_sequence import FIRST, SECOND, REST
from test_chestseal_preparation_progress import setup as patient_setup
from test_chest_entry_timing import setup as entry_setup
from test_historical_chest_workspace import workspace, setup as workspace_setup
from test_menu_death_lifecycle import execute, read


END = "AinvPknlMstpSnonWnonDnon_medicEnd"


def provider_setup():
    text = head_setup()
    text = text.replace('getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _end >> "speed")', '_endSpeed')
    text = text.replace('_u getUnitMovesInfo 1', '_nativeElapsed').replace('_u getUnitMovesInfo 2', '_nativeDuration')
    text = text.replace('serverTime', '_serverClock')
    text = re.sub(r'finite (_\w+)', 'true', text)
    return '''
        private _endSpeed=-2; private _nativeElapsed=0; private _nativeDuration=2;
        private _serverClock=1000;
    ''' + text


def begin():
    return f'''
        _anim="frozen-workspace"; _testAnimationSpeed=0;
        [_medic,"chestsealexit","close1"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0;
        [_job] call _tick;
        [_moves isEqualTo [[_medic,"{END}",1]],"medicEnd did not directly interpolate from workspace"] call _check;
        [_prep==0 && {{_weapon==""}},"exit replayed holster or retained weapon selection"] call _check;
        [_testAnimationSpeed==1.5,"exit not accelerated"] call _check;
        [!((_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2),"carrier released before exit"] call _check;
        _anim=toLower "{END}";
        [_job] call _tick;
    '''


def finish_end():
    return f'''
        _nativeElapsed=2;
        CBA_missionTime=11.34;
        [_job] call _tick;
        [(_moves select 1) isEqualTo [_medic,"{FIRST}",1],"carrier reach did not follow completed medicEnd"] call _check;
        [(_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2,"patient restore gate not released"] call _check;
    '''


def test_exit_runs_once_then_full_carrier_reach_and_return_without_weapon_redraw():
    execute(provider_setup()+begin()+f'''
        _nativeElapsed=1.9; CBA_missionTime=11.2;
        for "_i" from 0 to 4 do {{[_job] call _tick;}};
        [count _moves==1,"medicEnd replayed or reach started before end"] call _check;
    '''+finish_end()+f'''
        _anim=toLower "{FIRST}"; [_job] call _tick;
        _anim=toLower "{REST}"; [_job] call _tick;
        [(_moves select 2) isEqualTo [_medic,"{SECOND}",2],"Putdown return lost"] call _check;
        _anim=toLower "{SECOND}"; [_job] call _tick;
        _anim=toLower "{REST}"; [_job] call _tick;
        [count _moves==4 && {{_removed isEqualTo [73]}},"provider exit did not retire once"] call _check;
        [_weapon=="" && {{_testAnimationSpeed==1}},"exit restored weapon or retained speed"] call _check;
        [_waits select 0] call _deliver;
        [(_stances select ((count _stances)-1))=="AUTO","provider remained stance locked"] call _check;
    ''')


def test_animate_walk_speed_reset_is_corrected_only_during_owned_end():
    execute(provider_setup()+begin()+'''
        _testAnimationSpeed=1;
        [_job] call _tick;
        [_testAnimationSpeed==1.5 && {count _moves==1},"walk cleanup reset rate or caused move replay"] call _check;
        _medic setVariable ["ACME_nativeTreatmentRate",[99]];
        _testAnimationSpeed=1.7; _moves=[];
        [_job] call _tick;
        [_testAnimationSpeed==1.7 && {count _moves==0},"old exit touched new rate owner"] call _check;
    ''')


@pytest.mark.parametrize('speed,duration',[(-3,3),(0.25,4),(0,2)])
def test_native_end_duration_read_supports_negative_seconds_and_positive_reciprocal(speed,duration):
    execute(provider_setup()+f'''
        _endSpeed={speed};
        [_medic,"chestsealexit","close1"] call ACME_fnc_headElevMedicSeq;
        [abs (((_jobs select 0 select 2) select 15)-{duration})<0.001,"wrong native duration"] call _check;
    ''')


def test_delayed_native_entry_does_not_consume_end_playback_time():
    execute(provider_setup()+'''
        [_medic,"chestsealexit","close1"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0; [_job] call _tick;
        CBA_missionTime=11.2; [_job] call _tick;
        [count _moves==1,"unseen exit advanced"] call _check;
    '''+f'''
        _anim=toLower "{END}"; _nativeElapsed=0; [_job] call _tick;
        CBA_missionTime=11.5; [_job] call _tick;
        [count _moves==1,"entry delay counted as playback"] call _check;
        CBA_missionTime=12.55; [_job] call _tick;
        [count _moves==2,"observed end failed to advance"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_input setVariable ["MoveForward",1];',
    '_anim="unrelated-new-action";',
    '_medic setVariable ["ACME_treatmentPoseState",[19,"stethoscope"]];',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_alive=false;', '_blocked=true;',
])
def test_interruption_releases_patient_gate_and_never_appends_carrier_reach(change):
    execute(provider_setup()+begin()+change+f'''
        _moves=[]; [_job] call _tick;
        [(_moves findIf {{(_x select 1)=="{FIRST}"}})<0,"interruption appended stale reach"] call _check;
        [(_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2,"interruption stranded patient gate"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"interruption retained provider sequence"] call _check;
    ''')


def test_unseen_end_has_bounded_cleanup_and_never_fakes_reach_completion():
    execute(provider_setup()+'''
        [_medic,"chestsealexit","close1"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0; [_job] call _tick;
        CBA_missionTime=13.5; [_job] call _tick;
        [(_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2,"timeout retained patient gate"] call _check;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"unseen animation retained owner"] call _check;
    '''+f'''
        [(_moves findIf {{(_x select 1)=="{FIRST}"}})<0,"timeout invented successful carrier reach"] call _check;
    ''')


def test_late_unrelated_animation_is_not_mistaken_for_completed_exit():
    execute(provider_setup()+begin()+f'''
        CBA_missionTime=12; _anim="weapon-reload"; _moves=[];
        [_job] call _tick;
        [count _moves==0,"elapsed wall clock appended reach behind unrelated animation"] call _check;
        [(_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2,"late interruption retained patient gate"] call _check;
    ''')


def test_stale_provider_worker_cannot_release_new_close_or_animate_it():
    execute(provider_setup()+begin()+'''
        [_medic,"chestsealexit","close2"] call ACME_fnc_headElevMedicSeq;
        private _replacement=+(_medic getVariable ["ACME_CS_ProviderExitReady",[]]);
        _moves=[]; _events=[]; _stances=[];
        [_job] call _tick;
        [(_medic getVariable ["ACME_CS_ProviderExitReady",[]]) isEqualTo _replacement,"old worker acknowledged new close"] call _check;
        [count _moves==0 && {count _events==0} && {count _stances==0},"old worker altered new provider sequence"] call _check;
    ''')


@pytest.mark.parametrize('late',[False,True])
def test_prone_exit_uses_supported_work_and_never_kneels(late):
    execute(provider_setup()+('' if late else '_providerStance="PRONE";')+'''
        [_medic,"chestsealexit","close1"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0;
        _providerStance="PRONE"; [_job] call _tick;
        [(_moves select 0 select 1)=="ACM_ProneContinuous","prone exit requested kneeling medicEnd"] call _check;
        [!('MIDDLE' in _stances),"prone exit forced crouch"] call _check;
        [(_medic getVariable ["ACME_CS_ProviderExitReady",[]]) select 2,"prone exit blocked patient restoration"] call _check;
    ''')


def gated_patient():
    return patient_setup()+workspace()+'''
        _actualSide="front";
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[]]];
        private _restores=[];
        ACME_fnc_chestAccessVestRestore={_restores pushBack _this; false};
        [_patient,"old",_medic,["old",7,false,1004]] call ACME_fnc_chestSealPatientEnd;
        private _gate=call _take;
        [count _restores==0,"patient carrier restored before provider exit"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo [],"presentation wait retained workspace token"] call _check;
        [(_gate select 3)==4,"patient presentation wait not bounded"] call _check;
    '''


def test_patient_wait_handles_late_public_packet_then_exact_ready_ack():
    execute(gated_patient()+'''
        [!([_gate] call _ready),"missing network packet skipped provider exit"] call _check;
        _medic setVariable ["ACME_CS_ProviderExitReady",["old",7,false,1004]];
        [!([_gate] call _ready),"pending provider exit treated as complete"] call _check;
        _medic setVariable ["ACME_CS_ProviderExitReady",["old",7,true,1004]];
        [_gate] call _deliver;
        [count _restores==1,"completed provider exit did not release carrier"] call _check;
    ''')


@pytest.mark.parametrize('marker',[
    '["old",6,true,1004]', '["other",7,true,1004]', '["newer",8,false,1004]',
])
def test_patient_gate_rejects_wrong_old_ack_and_yields_to_newer_provider(marker):
    execute(gated_patient()+f'''
        _medic setVariable ["ACME_CS_ProviderExitReady",{marker}];
        [([_gate] call _ready) isEqualTo {str('8' in marker).lower()},"wrong provider episode gate result"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;',
    '_patient setVariable ["ACME_CS_ProcedureGeneration",5];',
    '_patient setVariable ["ACME_CS_ProcedureTokens",["new"]];',
])
def test_stale_patient_gate_never_restores_or_finalizes_replacement_workspace(change):
    execute(gated_patient()+change+'''
        _serverClock=1005; [_gate] call _deliver;
        [count _restores==0,"stale patient callback restored carrier"] call _check;
        [_patient getVariable ["ACME_CS_ProcedureActive",false],"stale patient callback finalized new workspace"] call _check;
    ''')


@pytest.mark.parametrize('timeout_callback',[False,True])
def test_patient_restore_has_finite_fallback_even_if_provider_disappears(timeout_callback):
    execute(gated_patient()+f'''
        _serverClock=1005;
        [_gate,{str(timeout_callback).lower()}] call _deliver;
        [count _restores==1,"missing provider left carrier removed forever"] call _check;
    ''')


def test_close_passes_exact_provider_exit_record_to_casualty_owner():
    close = read('chestSealClose')
    assert '[_flipMedic,"chestsealexit",uiNamespace getVariable ["ACME_CS_SessionToken", ""]] call ACME_fnc_headElevMedicSeq;' in close
    assert '[_patient, "chestSealPatientEnd", [_patient, _sessionToken, _flipMedic, _providerExit]] call ACME_fnc_ownerDispatch;' in close
    assert close.index('call ACME_fnc_treatmentPoseStop') < close.index('call ACME_fnc_headElevMedicSeq') < close.index('"chestSealPatientEnd"')


@pytest.mark.parametrize('stage,animation,exit_expected',[
    (-1,'pistol-holstering',False), (-2,'stand-to-kneel',False),
    (1,'pistol-holstering',False), (3,'new-unrelated-action',False),
    (1,'owned-work',True), (3,'owned-work',True),
])
def test_close_during_preflight_never_injects_weaponless_exit_under_visible_weapon(stage,animation,exit_expected):
    execute(entry_setup()+f'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _ep=[_medic,_patient,"start",false,"vest:chestseal:test",uiNamespace getVariable ["ACME_CS_SessionToken",""]] call ACME_fnc_chestAccessVestProvider;
        private _pose=_medic getVariable ["ACME_treatmentPoseState",[]];
        _pose set [3,{stage}];
        _animation={'toLower (_pose select 2)' if animation=='owned-work' else '"'+animation+'"'};
        [] call ACME_fnc_chestSealClose;
        [count _exits=={int(exit_expected)},"close confused pending holster with acquired medical work"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo [],"close did not retire old provider worker"] call _check;
    '''+('''
        [(_exits select 0 select 1)=="chestsealexit","acquired chest pose did not enter medicEnd sequence"] call _check;
    ''' if exit_expected else ''))


def shared_restore_setup():
    return workspace_setup()+'''
        _actualSide="front"; _blocked=true;
        private _maneuver=false;
        ACME_fnc_chestAccessManeuverActive={_maneuver};
        _patient setVariable ["ACME_CS_ProcedureGeneration",4];
        _patient setVariable ["ACME_CS_ProcedureTokens",[]];
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[]]];
    '''


@pytest.mark.parametrize('force',[False,True])
@pytest.mark.parametrize('ownership',[
    '_patient setVariable ["ACME_chestAccess_leases",createHashMapFromArray [["new-care",[_medic,10,"cpr"]]]];',
    '_maneuver=true;',
    '_patient setVariable ["ACME_chestAccess_maneuverHandoffUntil",20];',
])
def test_new_shared_chest_owner_defers_carrier_return_even_for_foreign_body_force(force,ownership):
    execute(shared_restore_setup()+ownership+f'''
        private _started=[_patient,{str(force).lower()},_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
        [!_started && {{count _loadouts==0}} && {{count _waits==1}},"carrier returned under newer shared care"] call _check;
        [_patient,{str(force).lower()},_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
        [count _waits==1,"deferred carrier wait duplicated"] call _check;
        private _wait=_waits deleteAt 0;
        [(_wait select 3)==900,"shared ownership retry is not finite"] call _check;
        [!((_wait select 2) call (_wait select 4)),"active shared owner did not retain chest"] call _check;
        _maneuver=false;
        _patient setVariable ["ACME_chestAccess_leases",createHashMap];
        _patient setVariable ["ACME_chestAccess_maneuverHandoffUntil",-1];
        [_wait] call _deliver;
        [count _loadouts==1 && {{_vest=="Vest_A"}},"last shared release did not return original carrier"] call _check;
        [(_patient getVariable ["ACME_CS_vestLoadout",[]]) isEqualTo [],"restored carrier retained duplicate custody"] call _check;
    ''')


def test_long_lived_shared_care_retries_bounded_wait_without_forcing_carrier_back():
    execute(shared_restore_setup()+'''
        _maneuver=true;
        [_patient,false,_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
        private _first=_waits deleteAt 0;
        [_first,true] call _deliver;
        [count _loadouts==0 && {count _waits==1},"timeout restored under continuing maneuver or stranded retry"] call _check;
        [(_waits select 0 select 3)==900,"retry interval became unbounded"] call _check;
        _maneuver=false;
        [_waits deleteAt 0] call _deliver;
        [_vest=="Vest_A","continued care could never release custody"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;',
    '_patient setVariable ["ACME_CS_ProcedureGeneration",5];',
    '_patient setVariable ["ACME_CS_ProcedureTokens",["new-viewer"]];',
])
def test_deferred_shared_restore_cannot_modify_new_patient_generation_or_viewer(change):
    execute(shared_restore_setup()+'''
        _maneuver=true;
        [_patient,false,_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
        private _wait=_waits deleteAt 0;
    '''+change+'''
        _maneuver=false; [_wait] call _deliver;
        [count _loadouts==0 && {(_patient getVariable ["ACME_CS_vestLoadout",[]]) isEqualTo ["Vest_A",[]]},"stale shared wait changed newer custody"] call _check;
    ''')


def test_old_shared_restore_callback_cannot_clear_replacement_wait():
    execute(shared_restore_setup()+'''
        _maneuver=true;
        [_patient,false,_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
        private _old=_waits deleteAt 0;
        _patient setVariable ["ACME_CS_ProcedureGeneration",5];
        [_patient,false,_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
        private _pending=+(_patient getVariable ["ACME_CS_SharedRestorePending",[]]);
        [_old] call _deliver;
        [(_patient getVariable ["ACME_CS_SharedRestorePending",[]]) isEqualTo _pending,"old callback cleared replacement restore"] call _check;
        [count _loadouts==0,"old callback restored newer custody"] call _check;
    ''')


def test_shared_cpr_acquired_during_medic_end_survives_actual_patient_close_pipeline():
    execute(patient_setup()+workspace()+'''
        _actualSide="front"; _blocked=true;
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[]]];
        private _maneuver=false;
        ACME_fnc_chestAccessManeuverActive={_maneuver};
        [_patient,"old",_medic,["old",7,false,1004]] call ACME_fnc_chestSealPatientEnd;
        private _gate=call _take;
        _maneuver=true;
        _patient setVariable ["ACME_patientAnimLock",["cpr","cpr","provider",8,1100]];
        _medic setVariable ["ACME_CS_ProviderExitReady",["old",7,true,1004]];
        [_gate] call _deliver;
        [count _loadouts==0 && {count _waits==1},"provider exit restored vest under newly acquired CPR"] call _check;
        [!(_patient getVariable ["ACME_CS_ProcedureActive",true]),"deferred cleanup retained workspace"] call _check;
        _maneuver=false; _patient setVariable ["ACME_patientAnimLock",[]];
        [call _take] call _deliver;
        [_vest=="Vest_A" && {count _loadouts==1},"CPR completion did not finish deferred chest-seal restoration"] call _check;
    ''')


def test_provider_gate_migrates_authorized_return_and_preserves_unfinished_medic_end():
    execute(gated_patient()+'''
        private _handoffs=[];
        ACME_fnc_ownerDispatch={_handoffs pushBack _this;};
        _patientLocal=false; [_gate] call _deliver;
        [count _handoffs==1 && {count _restores==0},"locality loss abandoned or locally executed authorized return"] call _check;
        [(_handoffs select 0 select 1)=="chestSealPatientEnd","migration did not use fixed owner operation"] call _check;
        private _args=(_handoffs select 0) select 2;
        [_args select 4==4 && {(_args select 3) isEqualTo ["old",7,false,1004]},"migration lost generation or provider exit deadline"] call _check;
        _patientLocal=true;
        _args call ACME_fnc_chestSealPatientEnd;
        private _continued=call _take;
        [!([_continued] call _ready) && {count _restores==0},"new owner bypassed unfinished medicEnd"] call _check;
        _medic setVariable ["ACME_CS_ProviderExitReady",["old",7,true,1004]];
        [_continued] call _deliver;
        [count _restores==1,"continued authorized return never completed"] call _check;
    ''')


@pytest.mark.parametrize('replacement',[
    '_patient setVariable ["ACME_CS_ProcedureGeneration",5];',
    '_patient setVariable ["ACME_CS_ProcedureTokens",["new-viewer"]];',
])
def test_migrated_return_rejects_replacement_workspace_generation_or_viewer(replacement):
    execute(gated_patient()+'''
        private _handoffs=[];
        ACME_fnc_ownerDispatch={_handoffs pushBack _this;};
        _patientLocal=false; [_gate] call _deliver;
        _patientLocal=true;
    '''+replacement+'''
        ((_handoffs select 0) select 2) call ACME_fnc_chestSealPatientEnd;
        [count _restores==0 && {count _waits==0},"migrated old return acquired replacement workspace"] call _check;
        [_patient getVariable ["ACME_CS_ProcedureActive",false],"migrated stale return finalized new session"] call _check;
    ''')


def test_shared_restore_locality_loss_clears_local_pending_and_can_reacquire_on_return():
    execute(shared_restore_setup()+'''
        private _handoffs=[];
        ACME_fnc_ownerDispatch={_handoffs pushBack _this;};
        _maneuver=true;
        [_patient,false,_medic,"chestseal",true] call ACME_fnc_chestAccessVestRestore;
        private _old=_waits deleteAt 0;
        _patientLocal=false; [_old] call _deliver;
        [(_patient getVariable ["ACME_CS_SharedRestorePending",[]]) isEqualTo [],"locality loss retained receiver-local pending marker"] call _check;
        [count _handoffs==1 && {count _loadouts==0},"locality loss abandoned return or changed gear locally"] call _check;
        _patientLocal=true;
        ((_handoffs select 0) select 2) call ACME_fnc_chestSealPatientEnd;
        [count _waits==1,"returning locality was blocked by stale pending marker"] call _check;
        [(_patient getVariable ["ACME_CS_SharedRestorePending",[]]) isEqualTo [2,4],"returning locality did not acquire fresh restore episode"] call _check;
        _maneuver=false; [_waits deleteAt 0] call _deliver;
        [_vest=="Vest_A" && {count _loadouts==1},"migrated shared return failed to finish once"] call _check;
    ''')
