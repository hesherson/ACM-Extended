"""Execute recovery provider/owner transactions; engine move graph and RTM blending remain boundaries."""
import re
from pathlib import Path
from functools import lru_cache
import pytest
from test_menu_death_lifecycle import adapt, execute, read

ROOT = Path(__file__).resolve().parents[3]


def source(name, native=False):
    raw = (ROOT/'addons/airway/functions'/f'fnc_{name}.sqf').read_text() if native else read(name)
    for old,new in {
        'local _patient':'_patientLocal', 'local _medic':'_medicLocal',
        'animationState _patient':'_patientAnim', 'animationState _medic':'_providerAnim',
        'objectParent _patient':'_patientParent', 'objectParent _medic':'_medicParent',
        'IS_UNCONSCIOUS(_patient)':'_patientUnconscious',
        'alive (_patient getVariable ["ACM_breathing_BVM_Medic", objNull])':'_bvm',
        'serverTime':'_serverClock', '_patient getUnitMovesInfo 3':'_moveBlend', 'finite _moveBlend':'true', 'netId _medic':'"medic"',
    }.items():
        raw = raw.replace(old,new)
    raw = re.sub(r'_patient switchMove ([^;]+);', r'_moves pushBack [_patient, \1];', raw)
    return adapt(raw, 'airway')


@lru_cache(maxsize=1)
def setup():
    code = '''
        private _patientLocal=true; private _medicLocal=true; private _patientUnconscious=true;
        private _patientAnim="acm_lyingstate"; private _providerAnim="prep";
        private _patientParent=objNull; private _medicParent=objNull;
        private _serverClock=10; private _clinicalEpoch=0; private _moveBlend=1; private _drag=false; private _carry=false; private _bvm=false; private _cpr=false;
        private _reject=false; private _logs=[]; private _rolls=[]; private _poseStops=[];
        ACME_fnc_doAnim={_moves pushBack _this;};
        ace_common_fnc_isAwake={if ((_this select 0) isEqualTo _patient) then {!_patientUnconscious} else {!_unconscious}};
        ace_common_fnc_isBeingDragged={_drag}; ace_common_fnc_isBeingCarried={_carry};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        ACME_fnc_clinicalEpoch={_clinicalEpoch};
        ACM_core_fnc_cprActive={_cpr}; ACME_fnc_patientInteractionDistance={_distance};
        ACME_fnc_patientAnimRequest={
            _this params ["_p","_a","_prio","_source","_m","_duration","_lockPriority","_token"];
            if (_reject) exitWith {""};
            _p setVariable ["ACME_patientAnimLock",[_token,_source,"medic",_lockPriority,_serverClock+_duration]];
            if (_a!="") then {[_p,_a,_prio] call ACME_fnc_doAnim;}; _token
        };
        ACME_fnc_patientAnimRelease={
            _this params ["_p","_token"];
            private _retired=_p getVariable ["ACME_patientAnimRetired",[]]; _retired pushBackUnique _token;
            _p setVariable ["ACME_patientAnimRetired",_retired];
            if (((_p getVariable ["ACME_patientAnimLock",[]]) param [0,""])==_token) then {_p setVariable ["ACME_patientAnimLock",[]];};
        };
        ACME_fnc_rollProviderStart={
            _rolls pushBack _this;
            private _e=(_medic getVariable ["ACME_treatmentPoseEpoch",0])+1;
            _medic setVariable ["ACME_treatmentPoseEpoch",_e];
            _medic setVariable ["ACME_treatmentPoseState",[_e,"roll","AinvPknlMstpSnonWnonDnon_medic4",0]];
            _medic setVariable ["ACME_rollProviderToken",format["roll:%1",_e]]; true
        };
        ACME_fnc_treatmentPoseStop={_poseStops pushBack _this;};
        private _run={private _h=+(_handlers select 0); if (_h select 2) then {[_h select 1,0] call (_h select 0);};};
    '''
    for name in ['setRecoveryPosition','handleRecoveryPosition','resetVariables']:
        code += f'ACM_airway_fnc_{name}={{'+source(name, True)+'};'
    for name in ['recoveryPositionStart','recoveryPositionProgress','recoveryPositionFinish']:
        code += f'ACME_fnc_{name}={{'+source(name)+'};'
    return code


def begin():
    return '''
        [_medic,_patient,true,false,"begin","one"] call ACM_airway_fnc_setRecoveryPosition;
        call _run;
        [_moves isEqualTo [[_patient,["ACM_RecoveryPosition",0,0,false]]],"patient snapped or did not request smooth ingress"] call _check;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"clinical state applied before treatment success"] call _check;
        _patientAnim="acm_recoveryposition"; call _run;
    '''


def test_observed_blend_and_native_success_both_required_before_airway_commit():
    execute(setup()+begin()+'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",1];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",1];
        _serverClock=12.01; call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]) && {count _logs==0},"pose-only stage credited treatment"] call _check;
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"settled successful recovery not committed"] call _check;
        [_patient getVariable ["ACM_airway_HeadTilt_State",false],"recovery lost airway protection"] call _check;
        [(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",-1])==0 && {(_patient getVariable ["ACM_airway_AirwayObstructionVomit_State",-1])==0},"native obstruction relief omitted"] call _check;
        [count _logs==1 && {(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo []},"duplicate log or retained lease"] call _check;
        call _run; [count _logs==1,"duplicate clinical commit"] call _check;
    ''')


def test_success_before_blend_finishes_waits_for_half_second_observation():
    execute(setup()+begin()+'''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=11.99; call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"incomplete blend counted"] call _check;
        _serverClock=12.01; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"complete observed blend did not commit"] call _check;
    ''')


@pytest.mark.parametrize('entered',[False,True])
def test_cancel_before_or_after_visible_entry_releases_only_owned_pose(entered):
    execute(setup()+'''
        [_medic,_patient,true,false,"begin","one"] call ACM_airway_fnc_setRecoveryPosition;
        call _run;
    '''+('_patientAnim="acm_recoveryposition"; call _run;' if entered else '')+'''
        _moves=[];
        [_medic,_patient,false,true,"cancel","one"] call ACM_airway_fnc_setRecoveryPosition;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"cancel retained pending state"] call _check;
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo [],"cancel retained animation ownership"] call _check;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"cancel granted recovery"] call _check;
    '''+f' [count _moves=={1 if entered else 0},"cancel did not restore only its visible provisional pose"] call _check;')


@pytest.mark.parametrize('change',[
    '_patientUnconscious=false;', '_patientAlive=false;', '_patientParent=missionNamespace;',
    '_drag=true;', '_carry=true;', '_alive=false;', '_unconscious=true;',
    '_medicParent=missionNamespace;', '_distance=6;', '_medic setVariable ["ACME_treatmentPoseEpoch",7];',
    '_cpr=true;', '_bvm=true;', '_patient setVariable ["ACME_CS_ProcedureActive",true];',
    '_patientAnim="unrelated-new-pose";',
])
def test_pending_invalidations_never_commit_or_reassert_recovery(change):
    execute(setup()+begin()+'''
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=11; _moves=[];
    '''+change+'''
        call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]) && {count _logs==0},"invalid episode committed"] call _check;
        [(_moves findIf {((_x select 1) param [0, ""])=="ACM_RecoveryPosition"})<0,"cancel reasserted pose"] call _check;
        [!((_handlers select 0) select 2),"invalid worker retained"] call _check;
    ''')


def test_successor_patient_lease_is_preserved_on_cancellation():
    execute(setup()+begin()+'''
        _patient setVariable ["ACME_patientAnimLock",["new","cpr","other",5,200]];
        _moves=[]; call _run;
        [((_patient getVariable ["ACME_patientAnimLock",[]]) select 0)=="new","old cleanup released successor"] call _check;
        [count _moves==0,"old cleanup moved successor"] call _check;
    ''')


def test_rejected_lease_and_unseen_engine_entry_never_grant_recovery():
    for reject in [False,True]:
        execute(setup()+f'_reject={str(reject).lower()};'+'''
            [_medic,_patient,true,false,"begin","one"] call ACM_airway_fnc_setRecoveryPosition;
            [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
            call _run; _serverClock=16; call _run;
            [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]) && {count _logs==0},"unseen/rejected pose credited"] call _check;
            [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"timeout retained transaction"] call _check;
        ''')


def test_cancel_overtaking_begin_retires_late_packet():
    execute(setup()+'''
        [_medic,_patient,false,true,"cancel","one"] call ACM_airway_fnc_setRecoveryPosition;
        [_medic,_patient,true,false,"begin","one"] call ACM_airway_fnc_setRecoveryPosition;
        [count _handlers==0 && {count _moves==0},"late cancelled begin started"] call _check;
    ''')


def test_owner_change_reroutes_exact_pending_cancel_without_local_mutation():
    execute(setup()+begin()+'''
        _patientLocal=false; _moves=[]; call _run;
        [count _moves==0 && {count _events==1},"owner loss mutated pose or did not route cleanup"] call _check;
        [((_events select 0 select 1) select 4)=="cancel" && {((_events select 0 select 1) select 5)=="one"},"owner loss cancelled wrong episode"] call _check;
        [!((_handlers select 0) select 2),"old owner retained worker"] call _check;
    ''')


def test_native_endpoint_routes_before_any_state_mutation_and_bounds_hops():
    execute(setup()+'''
        _patientLocal=false;
        [_medic,_patient,true,false,"begin","one"] call ACM_airway_fnc_setRecoveryPosition;
        [count _events==1 && {count _handlers==0},"remote path mutated native state"] call _check;
        [_medic,_patient,true,false,"begin","one",-1,-1,4] call ACM_airway_fnc_setRecoveryPosition;
        [count _events==1,"unbounded reroute"] call _check;
    ''')


def test_waits_for_existing_sf_lower_without_cutting_it_off():
    execute(setup()+'''
        _patient setVariable ["ACME_patientAnimLock",["lower","head-elev-lower","medic",1,200]];
        [_medic,_patient,true,false,"begin","one"] call ACM_airway_fnc_setRecoveryPosition;
        call _run; [count _moves==0,"recovery cut off Semi-Fowler lower"] call _check;
        _patient setVariable ["ACME_patientAnimLock",[]]; call _run;
        [count _moves==1,"recovery did not begin after lower"] call _check;
    ''')


def test_provider_uses_flip_and_observed_prone_mapping_then_commits_on_success():
    for prone in [False,True]:
        execute(setup()+'''
            private _args=[_medic,_patient,"Body","RecoveryPosition"];
            _args call ACME_fnc_recoveryPositionStart;
            [count _rolls==1 && {(_rolls select 0 select 1)=="recoveryPosition"},"provider did not use Flip controller"] call _check;
            [_args,3,5] call ACME_fnc_recoveryPositionProgress;
            [count _handlers==0,"patient started before observed provider work"] call _check;
            private _pose=_medic getVariable "ACME_treatmentPoseState"; _pose set [3,1];
        '''+('''_pose set [2,"ACM_ProneContinuous"]; _pose set [20,true]; _providerAnim="acm_pronecontinuous";''' if prone else '_providerAnim="ainvpknlmstpsnonwnondnon_medic4";')+'''
            [_args,3,5] call ACME_fnc_recoveryPositionProgress;
            [count _handlers==1,"provider at work did not request patient"] call _check;
            call _run; _patientAnim="acm_recoveryposition"; call _run;
            [_args,true] call ACME_fnc_recoveryPositionFinish;
            [count _poseStops==0 && {(_medic getVariable ["ACME_rollProviderToken",""])!=""},"success clipped the finite Flip scene"] call _check;
            _serverClock=12.01; call _run;
            [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"successful action did not commit"] call _check;
        ''')


def test_provider_successor_cannot_be_stopped_by_old_finish():
    execute(setup()+'''
        private _args=[_medic,_patient,"Body","RecoveryPosition"];
        _args call ACME_fnc_recoveryPositionStart;
        _medic setVariable ["ACME_recoveryAction",["new",_patient,99,"newroll",false]];
        [_args,false] call ACME_fnc_recoveryPositionFinish;
        [count _poseStops==0 && {(_medic getVariable "ACME_recoveryAction" select 0)=="new"},"stale finish affected successor"] call _check;
    ''')


def test_provider_sf_lower_completes_before_flip_controller_starts():
    # Provider Flip is already the body-handling scene. Only patient lowering must finish before ingress.
    runtime=source('registerHeadElevationTreatmentRuntime')
    execute(setup()+'''
        private _headEvent={}; private _headCalls=[];
        CBA_fnc_addEventHandler={if ((_this select 0)=="ace_treatmentStarted") then {_headEvent=_this select 1;};};
        ACME_fnc_headElevateStop={_headCalls pushBack _this;};
    '''+runtime+'''
        private _args=[_medic,_patient,"Body","RecoveryPosition"];
        _patient setVariable ["ACME_headElevated",true];
        _args call ACME_fnc_recoveryPositionStart;
        _args call _headEvent;
        [count _rolls==1,"recovery omitted Flip provider scene"] call _check;
        [(_headCalls select 0 select 0) isEqualTo _medic && {(_headCalls select 0 select 5)},"SF teardown lost actor or enabled a competing provider scene"] call _check;
        _patient setVariable ["ACME_headElevated",false];
        _patient setVariable ["ACME_patientAnimLock",["lower","head-elev-lower","",1,11]];
        private _pose=_medic getVariable "ACME_treatmentPoseState"; _pose set [3,1];
        _providerAnim="ainvpknlmstpsnonwnondnon_medic4";
        [_args,3,5] call ACME_fnc_recoveryPositionProgress; call _run;
        [count _moves==0,"recovery cut off patient lower"] call _check;
        _serverClock=11; _patient setVariable ["ACME_patientAnimLock",[]]; call _run;
        _patientAnim="acm_recoveryposition"; call _run;
        _serverClock=13; [_args,true] call ACME_fnc_recoveryPositionFinish; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"SF recovery failed after complete lower and two-second blend"] call _check;
        [count _rolls==1,"SF recovery replayed provider scene"] call _check;
    ''')


def test_config_keeps_complete_owned_state_and_severs_assessment_callbacks():
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    block=cfg.split('class RecoveryPosition: CheckAirway {',1)[1].split('\n    };',1)[0]
    for field in ['callbackStart','callbackProgress','callbackSuccess','callbackFailure']:
        assert field in block
    assert 'ACME_neverRollToBack = 1;' in block
    cancel=cfg.split('class CancelRecoveryPosition: RecoveryPosition {',1)[1].split('\n    };',1)[0]
    assert 'ACME_neverRollToBack = 0;' in cancel
    moves=(ROOT/'addons/airway/CfgMoves.hpp').read_text()
    assert 'class ACM_RecoveryPosition: DeadState {' in moves
    assert 'interpolateFrom[]' not in moves  # no native/owned graph mutation needed
    handler=(ROOT/'addons/airway/functions/fnc_handleRecoveryPosition.sqf').read_text()
    assert '_patient switchMove ["ACM_RecoveryPosition", 0, 0, false];' in handler
    assert '[_patient, "", 1, "recovery-position"' in handler
    assert 'diag_tickTime' not in handler
    assert '[QGVAR(setRecoveryPosition), LINKFUNC(setRecoveryPosition)]' in (ROOT/'addons/airway/XEH_postInit.sqf').read_text()


def test_stale_committed_episode_cancel_cannot_clear_new_recovery():
    execute(setup()+"""
        _patient setVariable ["ACM_airway_RecoveryPosition_State",true];
        _patient setVariable ["ACM_airway_RecoveryPosition_Episode","new"];
        _patient setVariable ["ACM_airway_HeadTilt_State",true];
        [_medic,_patient,false,true,"","old"] call ACM_airway_fnc_setRecoveryPosition;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"stale active cancel cleared successor"] call _check;
        [_patient getVariable ["ACM_airway_HeadTilt_State",false],"stale active cancel cleared successor airway"] call _check;
    """)


def test_provider_epoch_replication_can_follow_begin_packet():
    execute(setup()+"""
        _medic setVariable ["ACME_treatmentPoseEpoch",8];
        [_medic,_patient,true,false,"begin","one",9,0] call ACM_airway_fnc_setRecoveryPosition;
        call _run;
        [count _moves==0 && {(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isNotEqualTo []},"pending epoch delivery was cancelled or accepted early"] call _check;
        _medic setVariable ["ACME_treatmentPoseEpoch",9]; call _run;
        [count _moves==1,"replicated expected epoch did not release owner blend"] call _check;
    """)


def test_pending_clinical_reset_and_late_begin_cannot_reapply_recovery():
    execute(setup()+begin()+"""
        _clinicalEpoch=1;
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"clinical reset was overwritten"] call _check;
        [_medic,_patient,true,false,"begin","late",-1,0] call ACM_airway_fnc_setRecoveryPosition;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"pre-reset delayed begin accepted"] call _check;
    """)


def test_native_reset_retires_pending_token_and_episode():
    execute(setup()+begin()+"""
        [_patient] call ACM_airway_fnc_resetVariables;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Pending",[]]) isEqualTo [],"native reset retained pending recovery"] call _check;
        [(_patient getVariable ["ACM_airway_RecoveryPosition_Episode","bad"])=="","native reset retained active episode"] call _check;
        ["one" in (_patient getVariable ["ACME_patientAnimRetired",[]]),"reset failed to retire old token"] call _check;
    """)


def test_committed_death_preserves_intervention_evidence_and_retires_worker():
    execute(setup()+begin()+"""
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; call _run;
        _patientAlive=false; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"death erased established treatment evidence"] call _check;
        [!((_handlers select 0) select 2),"dead patient retained watcher"] call _check;
    """)


def test_elapsed_time_does_not_replace_native_blend_completion():
    execute(setup()+begin()+"""
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _serverClock=12.01; _moveBlend=0.6; call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"partial engine blend was counted as settled"] call _check;
        _moveBlend=1; call _run;
        [_patient getVariable ["ACM_airway_RecoveryPosition_State",false],"completed native blend did not authorize recovery"] call _check;
    """)


def test_patient_owner_away_and_back_between_ticks_invalidates_pending():
    execute(setup()+begin()+"""
        [_medic,_patient,true,false,"commit","one"] call ACM_airway_fnc_setRecoveryPosition;
        _patient setVariable ["ACME_providerLocalityEpoch",2]; _serverClock=12.01; call _run;
        [!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false]),"owner roundtrip revived old pending action"] call _check;
        [!((_handlers select 0) select 2),"old owner worker retained"] call _check;
    """)


def test_provider_owner_away_and_back_cannot_commit_old_ui_callback():
    execute(setup()+"""
        private _args=[_medic,_patient,"Body","RecoveryPosition"];
        _args call ACME_fnc_recoveryPositionStart;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        [!([_args] call ACME_fnc_recoveryPositionProgress),"provider ownership roundtrip allowed old progress"] call _check;
        [_args,true] call ACME_fnc_recoveryPositionFinish;
        [count _handlers==0 && {!(_patient getVariable ["ACM_airway_RecoveryPosition_State",false])},"old callback committed recovery"] call _check;
    """)
