"""Execute presentation ownership and audible episode decisions in SQF-VM.

Engine RTMs, native sound playback, controls and transport are explicit
boundaries. These tests do not certify in-game animation blending or audio.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from test_b212_prone_providers import hang_setup
from test_b265_equipment_transactions import weapon_setup
from test_b156_menu_pose import setup as menu_setup
from test_historical_pose_lifecycle import setup as pose_setup
from test_historical_weapon_preflight import helper_setup as weapon_helper_setup
from test_menu_death_lifecycle import adapt, execute, read


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def delayed_bag_setup():
    return hang_setup() + '''
        private _preflights=0;
        ACME_fnc_medicAnimationPrep={_preflights=_preflights+1;0.95};
        CBA_fnc_waitAndExecute={_waits pushBack [_this select 0,_this select 1,_this select 2];};
        _stance="STAND";_animation="holstering-sidearm";
        [_medic] call ACME_fnc_hangBagPrep;
        [count _held==0 && {count _stances==0} && {count _waits==1} && {(_waits select 0 select 2)==0.95},
            "bag preparation interrupted the outstanding holster"] call _check;
        [_preflights==1,"bag preparation requested more than one weapon stow"] call _check;
    '''


def test_hang_bag_waits_for_holster_before_one_stance_entry_and_work_handoff():
    execute(delayed_bag_setup() + '''
        [_waits select 0] call _deliver;
        [count _held==1 && {((_held select 0) select 1)=="AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"}
            && {count _waits==2},"settled weapon did not enter one normal crouch"] call _check;
        _stance="CROUCH";[_waits select 1] call _deliver;
        [count _held==2 && {((_held select 1) select 1)=="ACM_GenericContinuous"}
            && {_preflights==1},"bag work repeated holstering or missed its handoff"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '[_medic] call ACME_fnc_hangBagPrepStop;',
    '_medic setVariable ["ACME_hang_PrepToken",2];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_hang_Raising",false];',
    '_alive=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    'missionNamespace setVariable ["ACME_interventionAnimations",false];',
    'ACME_fnc_animBlocked={true};',
])
def test_cancelled_or_superseded_holster_callback_cannot_reenter_bag_theatre(change):
    execute(delayed_bag_setup() + change + '''
        _held=[];_stances=[];_moves=[];
        [_waits select 0] call _deliver;
        [count _held==0 && {count _stances==0} && {count _moves==0},
            "retired bag preflight reasserted its old stance or animation"] call _check;
    ''')


def test_prone_selected_during_holstering_is_preserved_before_bag_preparation():
    execute(delayed_bag_setup() + '''
        _stance="PRONE";_animation="amovppnemstpsnonwnondnon";
        [_waits select 0] call _deliver;
        [count _held==1 && {((_held select 0) select 1)=="ACM_ProneContinuous"}
            && {!('MIDDLE' in _stances)} && {count _waits==1},
            "delayed bag preparation raised a newly prone provider"] call _check;
    ''')


def test_bag_weapon_custody_waits_for_same_valid_settle_handoff():
    execute(weapon_setup("hangBagPrep") + '''
        ACME_fnc_medicAnimationPrep={0.95};ACME_fnc_animBlocked={false};
        _loadout set [0,+_rifle];_loadout set [1,+_launcher];
        [_medic] call ACME_fnc_hangBagPrep;
        [_removedWeapons isEqualTo [] && {(_medic getVariable ["ACME_hang_savedWeaponSlots",[]]) isEqualTo []},
            "bag custody interrupted the weapon before holstering settled"] call _check;
        (_waits select 0 select 1) call (_waits select 0 select 0);
        [_removedWeapons isEqualTo ["Rifle","Launcher"]
            && {(_medic getVariable "ACME_hang_savedWeaponSlots") isEqualTo [_rifle,_launcher]},
            "settled preparation did not preserve the exact original weapon slots"] call _check;
    ''')


def ready_source(animation="_animation", weapon="_currentWeapon"):
    source = read("medicAnimationReady")
    source = source.replace('animationState _medic', animation).replace('currentWeapon _medic', weapon)
    return 'ACME_fnc_medicAnimationReady={' + adapt(source) + '};'


@pytest.mark.parametrize("weapon,animation,expected", [
    ('Pistol', 'amovpknlmstpsnonwnondnon', False),
    ('', 'amovpknlmstpsraswpstdnon', False),
    ('', 'pistol-holster-transition', False),
    ('', 'AmovPknlMstpSrasWpstDnon_AmovPknlMstpSnonWnonDnon', False),
    ('', 'AmovPercMstpSrasWrflDnon_AmovPercMstpSnonWnonDnon', False),
    ('', 'AmovPercMstpSrasWlnrDnon_AmovPercMstpSnonWnonDnon', False),
    ('', 'AmovPercMstpSoptWbinDnon_AmovPercMstpSnonWnonDnon', False),
    ('', 'amovpknlmstpsnonwnondnon', True),
    ('', 'ACM_GenericContinuous', True),
    ('', 'ACM_ProneContinuous', True),
])
def test_shared_readiness_requires_both_logical_and_visible_empty_hands(weapon, animation, expected):
    execute('ACME_fnc_animBlocked={false};' + f'private _currentWeapon="{weapon}";private _animation="{animation}";'
            + ready_source() + f'''
        [([_medic] call ACME_fnc_medicAnimationReady) isEqualTo {str(expected).lower()},
            "logical weapon selection and visible holster readiness disagreed"] call _check;
    ''')


def test_real_weapon_preparation_preserves_pending_holster_during_mixed_transition():
    execute(weapon_helper_setup() + '''
        _weaponNow="";
        _animNowFixture="AmovPknlMstpSrasWpstDnon_AmovPknlMstpSnonWnonDnon";
        private _reservation=["empty_hands_once",10,"pistol"];
        _medic setVariable ["ACME_medicAnimationPrep",+_reservation];CBA_missionTime=10.2;
        private _delay=[_medic] call ACME_fnc_medicAnimationPrep;
        [_delay>0 && {(_medic getVariable "ACME_medicAnimationPrep") isEqualTo _reservation}
            && {_holsters isEqualTo []},"mixed transition was mistaken for completed weapon preparation"] call _check;
    ''')


def test_general_treatment_waits_for_mixed_pistol_transition_to_leave_native_skeleton():
    execute(pose_setup() + '''
        _testPrepDelay=0.5;_weapon="";
        _animation="AmovPknlMstpSrasWpstDnon_AmovPknlMstpSnonWnonDnon";
        [_medic,"inspect",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable "ACME_treatmentPoseState";
        private _id=_state select 5;CBA_missionTime=11;[_id] call _poseTick;
        [count _moves==0 && {(_state select 3)==-1},"medical work interrupted a mixed weapon holster transition"] call _check;
        _animation="amovpknlmstpsnonwnondnon";[_id] call _poseTick;
        [count _moves==1 && {(_state select 3)==1},"completed native holster failed medical handoff"] call _check;
    ''')


def test_slow_visible_holster_stays_quiet_after_minimum_then_enters_once_when_ready():
    execute(delayed_bag_setup() + 'private _currentWeapon="";' + ready_source() + '''
        CBA_missionTime=10.95;[_waits select 0] call _deliver;
        [count _held==0 && {count _stances==0} && {count _waits==2} && {_preflights==1},
            "minimum settle deadline interrupted an unfinished visible holster"] call _check;
        _animation="amovpercmstpsnonwnondnon";CBA_missionTime=11.1;
        [_waits select 1] call _deliver;
        [count _held==1 && {count _waits==3} && {_preflights==1},
            "ready handoff repeated stow or failed its one stance entry"] call _check;
    ''')


def test_holster_timeout_retires_preparation_without_invented_medical_exit():
    execute(delayed_bag_setup() + 'private _currentWeapon="Pistol";' + ready_source() + '''
        CBA_missionTime=13;[_waits select 0] call _deliver;
        [!(_medic getVariable ["ACME_hang_Raising",true])
            && {count _stances==0} && {count _moves==0}
            && {(_held findIf {(_x param [1,""])!=""})<0} && {_preflights==1},
            "failed holster retained a worker or fabricated crouch work/exit"] call _check;
    ''')


def activation_gate():
    source = read("hangBagActivate").split('_medic setVariable ["ACME_hang_Raising", false];', 1)[0]
    return 'ACME_fnc_hangBagActivate={' + adapt(source) + '''
        _presented=_presented+1;_medic setVariable ["ACME_hang_Raising",false];
    };'''


def test_early_clinical_claim_keeps_heartbeat_while_slow_preflight_waits_then_presents_once():
    execute(delayed_bag_setup() + 'private _currentWeapon="";private _presented=0;' + ready_source()
            + activation_gate() + '''
        call _activate;
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagActivate;
        [_presented==0 && {count _waits==2},"early claim created presentation over the holster"] call _check;
        CBA_missionTime=11;[[_medic,_patient],7] call ACME_fnc_hangBagTick;
        [_medic getVariable ["ACME_hang_Active",false],"visual watchdog cancelled an accepted waiting claim"] call _check;
        [_waits select 0] call _deliver;[_waits select 1] call _deliver;
        [_presented==0 && {_preflights==1},"waiting callbacks repeated stow or presented while busy"] call _check;
        _animation="amovpknlmstpsnonwnondnon";_stance="CROUCH";
        [_waits select 2] call _deliver;[_waits select 3] call _deliver;
        [_presented==1 && {_medic getVariable ["ACME_hang_PrepComplete",false]},
            "actual ready handoff did not produce one presentation"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_medic setVariable ["ACME_hang_Active",false];',
    '_medic setVariable ["ACME_hang_Start",11];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
])
def test_waiting_activation_cannot_resume_cancelled_replaced_or_transferred_episode(change):
    execute(delayed_bag_setup() + 'private _currentWeapon="";private _presented=0;' + ready_source()
            + activation_gate() + '''
        call _activate;[_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagActivate;
    ''' + change + '''
        _medic setVariable ["ACME_hang_PrepComplete",true];_animation="amovpknlmstpsnonwnondnon";
        [_waits select 1] call _deliver;
        [_presented==0,"retired ready callback created replacement presentation"] call _check;
    ''')


def test_disabled_presentation_does_not_defer_an_accepted_claim_for_weapon_readiness():
    execute(hang_setup() + 'private _presented=0;ACME_fnc_medicAnimationReady={false};'
            + activation_gate() + '''
        missionNamespace setVariable ["ACME_interventionAnimations",false];
        call _activate;[_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagActivate;
        [_presented==1 && {count _waits==0},"disabled theatre delayed the accepted clinical claim"] call _check;
    ''')


def hint_source():
    source = read("hangBagHint").replace('findDisplay 46', '_hintDisplay')
    source = source.replace('_disp ctrlCreate ["RscStructuredText", -1]', 'call _createHint')
    source = source.replace('ctrlDelete _old;', '_deletedHints pushBack _old;')
    source = re.sub(r'_ctrl ctrlSetPosition \[.*?\];', '', source, flags=re.S)
    source = re.sub(r'_ctrl ctrlSetStructuredText parseText \(.*?\);', '', source, flags=re.S)
    source = re.sub(r'_ctrl ctrl(?:SetBackgroundColor|Commit) [^;]+;', '', source)
    return 'ACME_fnc_hangBagHint={' + adapt(source) + '};'


@pytest.mark.parametrize("finish", ["cancel", "timeout", "control_change"])
def test_waiting_claim_prompt_is_deleted_on_cancel_timeout_and_control_change(finish):
    execute(delayed_bag_setup() + 'private _currentWeapon="";private _presented=0;' + ready_source()
            + activation_gate() + hint_source() + '''
        private _createdHints=0;private _deletedHints=[];private _hintDisplay=missionNamespace;
        private _createHint={_createdHints=_createdHints+1;parsingNamespace};
        missionNamespace setVariable ["ACME_ui_helpText",true];
        call _activate;[_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagActivate;
        CBA_missionTime=11;[[_medic,_patient],7] call ACME_fnc_hangBagTick;
        [_createdHints==1 && {(uiNamespace getVariable "ACME_hang_HintCtrl") isEqualTo parsingNamespace}
            && {(uiNamespace getVariable "ACME_hang_HintMedic") isEqualTo _medic},
            "fixture did not create the real waiting-claim prompt"] call _check;
    ''' + ('''
        CBA_missionTime=13;[_waits select 0] call _deliver;
    ''' if finish == "timeout" else ('''
        ACE_player=_patient;[true,_medic] call ACME_fnc_hangBagStop;
    ''' if finish == "control_change" else '''
        [true,_medic] call ACME_fnc_hangBagStop;
    ''')) + '''
        [_deletedHints isEqualTo [parsingNamespace]
            && {(uiNamespace getVariable "ACME_hang_HintCtrl") isEqualTo objNull}
            && {(uiNamespace getVariable "ACME_hang_HintMedic") isEqualTo objNull}
            && {!(_medic getVariable ["ACME_hang_Active",true])},
            "ended waiting claim stranded its Lower IV Bag prompt"] call _check;
    ''')


@pytest.mark.parametrize("launcher", [False, True])
def test_menu_holster_branches_wait_for_actual_empty_hands_without_a_second_stow(launcher):
    execute(menu_setup() + ready_source("_menuAnimation", "_currentWeapon") + '''
        private _preflights=0;ACME_fnc_medicAnimationPrep={_preflights=_preflights+1;0.2};
        _menuAnimation="holstering-pistol";
    ''' + ('''
        _medic setVariable ["ACME_menuPoseAfterTreatment",objNull];
        _currentWeapon="Launcher";_secondaryWeapon="Launcher";
    ''' if launcher else '') + '''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        CBA_missionTime=10.2;0 call _runWait;
        [_moves isEqualTo [] && {count _waits==2} && {_preflights==1},
            "menu interrupted an unfinished native holster"] call _check;
        _currentWeapon="";_menuAnimation="amovpknlmstpsnonwnondnon";
        CBA_missionTime=10.3;1 call _runWait;
    ''' + ('''
        [_moves isEqualTo ["AmovPknlMstpSnonWnonDnon"] && {_preflights==1},
            "first-contact launcher menu failed one ready crouch entry"] call _check;
    ''' if launcher else '''
        2 call _runWait;
        [_moves isEqualTo ["ACM_GenericContinuous"] && {_preflights==1},
            "after-treatment menu failed one ready generic handoff"] call _check;
    '''))


@pytest.mark.parametrize("launcher", [False, True])
def test_menu_holster_timeout_releases_stance_speed_and_display_lease_without_animation(launcher):
    execute(menu_setup() + ready_source("_menuAnimation", "_currentWeapon") + '''
        _menuAnimation="holstering-pistol";
    ''' + ('''
        _medic setVariable ["ACME_menuPoseAfterTreatment",objNull];
        _currentWeapon="Launcher";_secondaryWeapon="Launcher";
    ''' if launcher else '') + '''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        CBA_missionTime=13;0 call _runWait;
        [_moves isEqualTo [] && {_stanceFreed} && {_testAnimationSpeed==1}
            && {(_medic getVariable ["ACME_menuPose",[1]]) isEqualTo []},
            "expired menu holster retained ownership or forced an exit animation"] call _check;
    ''')


def seating_setup():
    source = read("ivMinigameStickSuccess")
    source = re.sub(r'\(_dlg displayCtrl \d+\) ctrl(?:Show|SetText) [^;]+;', '', source)
    source = re.sub(r'_\w+ ctrlShow [^;]+;', '', source)
    source = re.sub(r'playSound ([^;]+);', r'_sounds pushBack (\1);', source)
    return '''
        private _validView=true;private _accepted=true;
        private _sounds=[];private _registered=0;private _placed=[];
        private _dlg=missionNamespace;
        uiNamespace setVariable ["ACME_IV_DLG",_dlg];
        uiNamespace setVariable ["ACME_IV_BodyRect",[0,0,1,1]];
        uiNamespace setVariable ["ACME_IV_InsStage","retract"];
        uiNamespace setVariable ["ACME_IV_InsSite","middle"];
        uiNamespace setVariable ["ACME_IV_InsHit",true];
        ACME_fnc_ivUiValid={true};
        ACME_fnc_ivMinigameViewValid={_validView};
        ACME_fnc_ivMinigameRegister={_registered=_registered+1;uiNamespace setVariable ["ACME_IV_RegOK",_accepted];};
        ACME_fnc_ivMinigameRefreshBandSlot={};ACME_fnc_ivMinigameSaveState={};
        ACME_fnc_ivMinigameAddMark={_placed pushBack _this;};
        private _deliver={params ["_job"];(_job select 1) call (_job select 0);};
    ''' + 'ACME_fnc_ivMinigameStickSuccess={' + adapt(source) + '};'


@pytest.mark.parametrize("accepted,valid", [(True, True), (False, True), (True, False)])
def test_catheter_seating_plays_one_cue_only_after_valid_registration(accepted, valid):
    execute(seating_setup() + f'''
        _accepted={str(accepted).lower()};
        [0.5,0.5] call ACME_fnc_ivMinigameStickSuccess;
        [_sounds isEqualTo [] && {{_registered==0}} && {{count _waits==1}},
            "seating emitted an early duplicate cue"] call _check;
        _validView={str(valid).lower()};[_waits select 0] call _deliver;
        [count _sounds=={int(accepted and valid)} && {{_registered=={int(valid)}}}
            && {{count _placed=={int(accepted and valid)}}},
            "seating cue did not match its actual accepted visible completion"] call _check;
    ''')


def pulling_setup():
    source = ''
    for name in ("ivMinigamePullStop", "ivMinigamePullTick"):
        code = read(name)
        for old, new in {
            'getMousePosition': '_mouse', 'safeZoneWAbs': '1', 'safeZoneH': '1',
            'pixelW': '1', 'pixelH': '1', 'diag_deltaTime': '0.016',
        }.items():
            code = code.replace(old, new)
        code = re.sub(r'setMousePosition \[[^;]+;', '', code)
        code = re.sub(r'playSound ([^;]+);', r'_sounds pushBack (\1);', code)
        source += f'ACME_fnc_{name}={{' + adapt(code) + '};'
    return '''
        private _sounds=[];private _commands=[];private _rendered=0;
        private _mouse=[0.9,0.5];
        private _mark=[];_mark resize 16;
        _mark set [4,"hub"];_mark set [14,"hub-one"];_mark set [15,[false,false,false,false]];
        _patient setVariable ["ACME_IV_Marks",[_mark]];
        uiNamespace setVariable ["ACME_IV_Patient",_patient];
        uiNamespace setVariable ["ACME_IV_PullIdx",0];
        uiNamespace setVariable ["ACME_IV_PullUID","hub-one"];
        uiNamespace setVariable ["ACME_IV_PullKind","catheter"];
        uiNamespace setVariable ["ACME_IV_PullPin",[0.5,0.5]];
        uiNamespace setVariable ["ACME_IV_BodyRect",[0,0,1,1]];
        ACME_fnc_ivUiValid={true};ACME_fnc_clinicalEpoch={1};
        ACME_fnc_ivCathGeometry={[0.1,0.1,[],[-1,0]]};
        ACME_fnc_ownerDispatch={_commands pushBack _this;};
        ACME_fnc_ivMinigameRenderMarks={_rendered=_rendered+1;};
    ''' + source


def test_fast_complete_catheter_pull_emits_one_breakaway_cue_and_one_owner_command():
    execute(pulling_setup() + '''
        [true] call ACME_fnc_ivMinigamePullTick;
        [true] call ACME_fnc_ivMinigamePullTick;
        [_sounds isEqualTo ["ACE_Sound_Click"] && {count _commands==1}
            && {(_commands select 0 select 1)=="ivCatheterPull"}
            && {(uiNamespace getVariable "ACME_IV_PullIdx")==-1},
            "one quick yank emitted duplicate completion audio or owner commands"] call _check;
    ''')


def test_releasing_a_partial_pull_emits_no_new_cue_or_removal_command():
    execute(pulling_setup() + '''
        uiNamespace setVariable ["ACME_IV_PullProg",0.3];
        uiNamespace setVariable ["ACME_IV_PullBroke",true];
        [false] call ACME_fnc_ivMinigamePullTick;
        [_sounds isEqualTo [] && {_commands isEqualTo []} && {_rendered==1}
            && {(uiNamespace getVariable "ACME_IV_PullIdx")==-1},
            "release replayed completion audio or removed the catheter"] call _check;
    ''')


def wrapping_setup():
    source = read("wrapSfxServer")
    source = source.replace('getPosATL _medic', '[0,0,0]')
    source = source.replace('createSoundSource ["ACME_JunctionalPack_SoundSource", [0,0,0], [], 0]', 'call _createEmitter')
    source = source.replace('_src attachTo [_medic, [0, 0, 0]];', '_attachments pushBack [_src,_medic];')
    source = re.sub(r'deleteVehicle ([^;]+);', r'_deletes pushBack (\1);', source)
    source = source.replace('owner _provider', '_ownerNum').replace('isPlayer _medic', 'true').replace('isPlayer _provider', 'true')
    source = source.replace('serverTime', 'CBA_missionTime')
    source = source.replace('isNull (_x select 3)', '((_x select 3) isEqualTo objNull)')
    return '''
        private _created=0;private _deletes=[];private _attachments=[];
        private _createEmitter={_created=_created+1;[parsingNamespace,missionNamespace] select (_created-1);};
        ACME_fnc_markImportantSfx={};
        CBA_fnc_addPerFrameHandler={_handlers pushBack [_this select 0,_this param [2,[]],true];count _handlers-1};
    ''' + 'ACME_fnc_wrapSfxServer={' + adapt(source) + '};'


def test_exact_wrapping_start_replay_keeps_existing_loop_and_new_token_replaces_once():
    execute(wrapping_setup() + '''
        ["start",_medic,_patient,"7:1",7] call ACME_fnc_wrapSfxServer;
        ["start",_medic,_patient,"7:1",7] call ACME_fnc_wrapSfxServer;
        [_created==1 && {_deletes isEqualTo []} && {count _attachments==1}
            && {count (missionNamespace getVariable ["ACME_wrapSfxSources",[]])==1},
            "duplicate wrapping start restarted or doubled the emitter"] call _check;
        ["start",_medic,_patient,"7:2",7] call ACME_fnc_wrapSfxServer;
        [_created==2 && {_deletes isEqualTo [parsingNamespace]},
            "new wrapping episode did not replace just its predecessor"] call _check;
        ["stop",_medic,_patient,"7:1",7] call ACME_fnc_wrapSfxServer;
        [count _deletes==1 && {((missionNamespace getVariable "ACME_wrapSfxSources") select 0 select 2)=="7:2"},
            "old wrapping stop silenced the replacement episode"] call _check;
        ["stop",_medic,_patient,"7:2",7] call ACME_fnc_wrapSfxServer;
        [_deletes isEqualTo [parsingNamespace,missionNamespace]
            && {(missionNamespace getVariable "ACME_wrapSfxSources") isEqualTo []}
            && {(missionNamespace getVariable "ACME_wrapSfxPFH")==-1},
            "current wrapping stop leaked emitter or watchdog"] call _check;
    ''')
