"""Execute new-life admission and the real registered retry with explicit engine boundaries."""
import pytest
from test_menu_death_lifecycle import adapt, execute, read


def boundary(text):
    replacements = {
        'alive _newUnit': '_newAlive', 'local _newUnit': '_newLocal',
        'local _oldUnit': '_oldLocal', '_newUnit isKindOf "CAManBase"': '_newHuman',
        'damage _newUnit': '_newDamage', 'finite _issuedAt': '_issueFinite',
        'finite _age': '_ageFinite', 'serverTime': '_serverTime',
        'addMissionEventHandler ': '_respawnEvent = ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return adapt(text)


def setup():
    return '''
        private _newLocal=true; private _oldLocal=false; private _newAlive=true;
        private _newHuman=true; private _newDamage=0;
        private _issueFinite=true; private _ageFinite=true; private _serverTime=100;
        private _newUnit=_patient; private _oldUnit=_medic;
        private _resetCalls=0; private _visualClears=0; private _frozen=[]; private _commands=[];
        private _timers=[]; private _respawnEvent=[];
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACME_fnc_ownerDispatch={_commands pushBack _this;};
        ACME_fnc_clearAllAilments={
            private _p=_this select 0;
            _resetCalls=_resetCalls+1;
            _p setVariable ["ACME_clinicalEpoch",1+(_p getVariable ["ACME_clinicalEpoch",0])];
            _p setVariable ["fixtureTreatment",[]];
        };
        ACME_fnc_deathFreeze={_frozen pushBack (_this select 0);};
        ACME_fnc_obtundedStateCommit={}; ACME_fnc_rhythmActiveCommit={};
        ACME_fnc_rhythmNativeHoldCommit={}; ACME_fnc_rhythmNativeHighHRFloorCommit={};
        ACME_fnc_rhythmNativeShockGraceCommit={}; ACM_circulation_fnc_setRuntimeState={};
        ACME_fnc_nrbStateCommit={}; ACME_fnc_hpmkStateCommit={};
        ACME_fnc_obtundedApply={_visualClears=_visualClears+1; (_this select 0) setVariable ["fixturePose",[]];};
        CBA_fnc_addPerFrameHandler={0}; CBA_fnc_addEventHandler={};
        CBA_fnc_waitAndExecute={_timers pushBack _this;};
        ACME_fnc_respawnClinicalReset={
    ''' + boundary(read('respawnClinicalReset')) + '''};
        ACME_fnc_clinicalFields={
    ''' + adapt(read('clinicalFields')) + '''};
    ''' + boundary(read('registerRhythmLifecycleRuntime')) + '''
        private _event=_respawnEvent select 1;
    '''


def retry():
    return '''
        private _timer=_timers select 0;
        (_timer select 1) call (_timer select 0);
    '''


def test_registered_event_and_delayed_retry_never_repeat_a_completed_full_heal():
    execute(setup() + '''
        [_newUnit,_oldUnit] call _event;
        [_resetCalls==1,"fresh life did not initialize once"] call _check;
        _newUnit setVariable ["fixtureTreatment",["new-treatment"]];
        _serverTime=102;
    ''' + retry() + '''
        [_resetCalls==1 && {(_newUnit getVariable "fixtureTreatment") isEqualTo ["new-treatment"]},
            "delayed new-life reset erased subsequent treatment"] call _check;
        [_newUnit,_oldUnit] call _event;
        [_resetCalls==1,"duplicate respawn event repeated baseline reset"] call _check;
    ''')


def test_epoch_fence_covers_completion_publication_lag_and_prior_restore():
    execute(setup() + '''
        _newUnit setVariable ["ACME_clinicalEpoch",1];
        _newUnit setVariable ["fixtureTreatment",["restored"]];
        [_newUnit,100] call ACME_fnc_respawnClinicalReset;
        [_resetCalls==0 && {_newUnit getVariable ["ACME_respawnResetComplete",false]},
            "new owner replayed initialization over a reset/restore"] call _check;
        [(_newUnit getVariable "fixtureTreatment") isEqualTo ["restored"],"restore was erased"] call _check;
    ''')


@pytest.mark.parametrize('active', [
    '_newDamage=.1;',
    '_newUnit setVariable ["ACE_isUnconscious",true];',
    '_newUnit setVariable ["ace_medical_inCardiacArrest",true];',
    '_newUnit setVariable ["ACME_obtunded",true];',
    '_newUnit setVariable ["ACME_aspiration_State",[0,"new-life-emesis",.2,.1,1]];',
    '_newUnit setVariable ["ACME_hpmk_on",true];',
    '_newUnit setVariable ["ACME_nrb_on",true];',
    '_newUnit setVariable ["ACME_vent_onPatient",true];',
    '_newUnit setVariable ["ACME_rhythm_active",103];',
    '_newUnit setVariable ["ACM_circulation_Cardiac_RhythmState",4];',
    '_newUnit setVariable ["ACM_breathing_Pneumothorax_State",2];',
    '_newUnit setVariable ["ACM_breathing_TensionPneumothorax_State",true];',
    '_newUnit setVariable ["ACM_breathing_ChestInjury_State",true];',
    '_newUnit setVariable ["ACM_airway_AirwayCollapse_State",true];',
    '_newUnit setVariable ["ACM_airway_AirwayObstructionVomit_State",2];',
    '_newUnit setVariable ["ACM_airway_AirwayObstructionBlood_State",1];',
    '_newUnit setVariable ["ACM_circulation_isPerformingCPR",true];',
    '_newUnit setVariable ["ACME_resusPending",["pending-other-patient"]];',
    '_newUnit setVariable ["ACME_resusToken_cpr",["active-compressor"]];',
    '_newUnit setVariable ["ACME_resusToken_bvm",["active-ventilation"]];',
    '_newUnit setVariable ["ACME_ptx_state",[1,1,0,0,0,0,0,0,0]];',
    '_newUnit setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[1]]]];',
    '_newUnit setVariable ["ace_medical_medications",[["medication",1]]];',
    '_newUnit setVariable ["ace_medical_openWounds",createHashMapFromArray [["torso",[1]]]];',
    '_newUnit setVariable ["ace_medical_bandagedWounds",createHashMapFromArray [["torso",[1]]]];',
    '_newUnit setVariable ["ace_medical_medications","external-malformed-state"];',
])
def test_first_late_owner_delivery_preserves_already_started_new_life(active):
    execute(setup() + active + '''
        _newUnit setVariable ["fixtureTreatment",["mission-initializer"]];
        [_newUnit,100] call ACME_fnc_respawnClinicalReset;
        [_resetCalls==0 && {_newUnit getVariable ["ACME_respawnResetComplete",false]},
            "fresh life clinical activity was baseline-healed"] call _check;
        _newUnit setVariable ["ace_medical_medications",[]]; _newDamage=0;
        _serverTime=102;
        [_newUnit,100] call ACME_fnc_respawnClinicalReset;
        [_resetCalls==0,"later neutral state reopened skipped initialization"] call _check;
    ''')


@pytest.mark.parametrize('edge', [
    '_newAlive=false;', '_newHuman=false;', '_issueFinite=false;', '_ageFinite=false;',
    '_serverTime=104;', '_serverTime=97;',
])
def test_dead_nonhuman_invalid_and_expired_initializers_do_not_mutate(edge):
    execute(setup() + edge + '''
        _newUnit setVariable ["fixtureTreatment",["preserve"]];
        [_newUnit,100] call ACME_fnc_respawnClinicalReset;
        [_resetCalls==0 && {count _commands==0},"invalid new-life request mutated or routed"] call _check;
        [!(_newUnit getVariable ["ACME_respawnResetComplete",false]),"invalid request completed initialization"] call _check;
    ''')


def test_nonowner_routes_original_timestamp_and_current_owner_initializes_once():
    execute(setup() + '''
        _newLocal=false;
        [_newUnit,100] call ACME_fnc_respawnClinicalReset;
        [_resetCalls==0 && {count _commands==1},"nonowner mutated fresh patient"] call _check;
        private _args=(_commands select 0) select 2;
        [_args isEqualTo [_newUnit,100],"reroute refreshed initializer issue time"] call _check;
        _newLocal=true; _serverTime=100.5;
        _args call ACME_fnc_respawnClinicalReset;
        _serverTime=102;
        _args call ACME_fnc_respawnClinicalReset;
        [_resetCalls==1,"ownership settlement duplicated reset"] call _check;
    ''')


def test_respawn_preserves_old_body_and_retry_does_not_refresh_issue_time():
    execute(setup() + '''
        _oldLocal=true;
        _oldUnit setVariable ["fixtureEvidence",["old-injury"]];
        [_newUnit,_oldUnit] call _event;
        [count _frozen==1 && {(_frozen select 0) isEqualTo _oldUnit},"old corpse worker not retired"] call _check;
        [(_oldUnit getVariable "fixtureEvidence") isEqualTo ["old-injury"],"old corpse evidence erased"] call _check;
        [(((_timers select 0) select 1) select 1)==100,"retry did not retain original issue time"] call _check;
    ''')


def test_registered_event_preserves_pose_and_hpmk_registry_of_initialized_life():
    execute(setup() + '''
        _newUnit setVariable ["ACME_clinicalEpoch",1];
        _newUnit setVariable ["fixturePose",["treatment-pose"]];
        ACME_hpmk_activePatients=[_oldUnit,_newUnit];
        [_newUnit,_oldUnit] call _event;
        [_resetCalls==0 && {_visualClears==0},"preserved initializer still cleared physical posture"] call _check;
        [(_newUnit getVariable "fixturePose") isEqualTo ["treatment-pose"],"new-life pose overwritten"] call _check;
        [ACME_hpmk_activePatients isEqualTo [_newUnit],"active new-life blanket worker orphaned"] call _check;
    ''')


def test_runtime_clock_and_floor_lease_alone_do_not_block_fresh_body_initialization():
    execute(setup() + '''
        _newUnit setVariable ["ACME_flightContainment",["old-owner"]];
        _newUnit setVariable ["ACME_alt_ptxSample",["old-clock"]];
        [_newUnit,100] call ACME_fnc_respawnClinicalReset;
        [_resetCalls==1,"runtime bookkeeping blocked fresh life initialization"] call _check;
    ''')
