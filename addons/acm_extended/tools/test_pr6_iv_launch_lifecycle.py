"""Execute IV launch, creation, pending cancellation and menu handoff SQF.

The real Open/Close/minigameOpen/reopenMedicalMenu and init's ownership prefix
run in SQF-VM. Native displays, their synchronous onLoad, UI stacks and CBA
scheduling are explicit engine adapters; renderer geometry, PhysX and transport
are not simulated. Separate frame and timed queues permit sparse-frame races.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read


def engine(text):
    # Native UI/liveness boundaries only; keep production identity and branching.
    text = text.replace('findDisplay 38580', '_medicalDisplay').replace('findDisplay 46', '_missionDisplay')
    text = text.replace('allDisplays', '_displayStack')
    text = re.sub(r'\blocal (_medic|_provider)\b', '_providerLocal', text)
    text = text.replace('createDialog _dialogClass', '[_dialogClass] call _createDialog')
    text = text.replace('createDialog _cls', '[_cls] call _createDialog')
    text = text.replace('!isNull (_p createDisplay _cls)', '(([_cls] call _createDisplay) isNotEqualTo objNull)')
    text = text.replace('_med closeDisplay 2;', '_medicalDisplay = objNull; _displayStack = _displayStack - [_med];')
    text = text.replace('_old closeDisplay 2;', '[_old] call ACME_fnc_ivMinigameClose; _displayStack = _displayStack - [_old]; _dialog = false;')
    text = text.replace('_display closeDisplay 2;', '[_display] call ACME_fnc_ivMinigameClose; _displayStack = _displayStack - [_display]; _dialog = false;')
    return adapt(text)


def setup(display_mode=False, fail=False):
    code = r'''
        private _providerLocal=true; private _frames=[]; private _leases=[];
        private _created=[]; private _reopened=[]; private _saves=0; private _creationSideEffect={};
        private _medicalDisplay=missionNamespace; private _missionDisplay=parsingNamespace;
        private _displayStack=[_missionDisplay,_medicalDisplay];
        private _drawDisplay=missionNamespace;
        private _controlled=_medic;
        ACME_fnc_controlledProvider={_controlled};
        CBA_fnc_execNextFrame={_frames pushBack _this;};
        private _frame={private _run=+_frames;_frames=[];{(_x select 1) call (_x select 0);} forEach _run;};
        private _timers={private _run=+_waits;_waits=[];{(_x select 1) call (_x select 0);} forEach _run;};
        ACME_fnc_ivSiteData={["valid site"]};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["epoch",7]};
        ACME_fnc_ecgJostleRequest={_leases pushBack +_this;};
        ACME_fnc_ivMinigameSaveState={_saves=_saves+1;};
        ACME_fnc_ivMinigameResetView={}; ACME_fnc_ivMinigamePrepView={};
        ace_medical_gui_fnc_canOpenMenu={true};
        ace_medical_gui_fnc_openMenu={
            _reopened pushBack [_this select 0,ace_medical_gui_selectedCategory,ace_medical_gui_selectedBodyPart];
            ace_medical_gui_lastOpenedOn=ace_medical_gui_lastOpenedOn+1;
        };
        ace_medical_gui_lastOpenedOn=10;
        uiNamespace setVariable ["ACME_medicalMenuRendererEpoch",12];
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",_medicalDisplay];
        ace_medical_gui_target=_patient; ace_medical_gui_selectedCategory="advanced";
        ace_medical_gui_selectedBodyPart=3;
    '''
    for name in ('ivUiValid', 'ivMinigameClose', 'reopenMedicalMenu', 'minigameOpen', 'ivMinigameOpen'):
        code += 'ACME_fnc_' + name + '={' + engine(read(name)) + '};\n'
    prefix = read('ivMinigameInit').split('private _bodyPart =', 1)[0]
    code += 'private _init={' + engine(prefix) + '};\n'
    tick = read('ivMinigameTick').split('// Update band presence', 1)[0] + '};'
    code += 'private _activeTick={' + engine(tick) + '};\n'
    code += f'private _fail={str(fail).lower()}; missionNamespace setVariable ["ACME_minigame_displayMode",{str(display_mode).lower()}];'
    return code + r'''
        private _createDialog={
            if (_fail) exitWith {call _creationSideEffect;false};
            _created pushBack (_this select 0); _displayStack pushBack _drawDisplay;
            [_drawDisplay] call _init; _dialog=true; true
        };
        private _createDisplay={
            if (_fail) exitWith {call _creationSideEffect;objNull};
            _created pushBack (_this select 0); _displayStack pushBack _drawDisplay;
            [_drawDisplay] call _init; _drawDisplay
        };
        private _launch={[_medic,_patient,"rightarm","lower"] call ACME_fnc_ivMinigameOpen;};
        private _close={
            _dialog=false; _displayStack=_displayStack-[_drawDisplay];
            [_drawDisplay] call ACME_fnc_ivMinigameClose;
        };
    '''


@pytest.mark.parametrize('display_mode', [False, True])
@pytest.mark.parametrize('patient_alive', [False, True])
def test_current_living_or_dead_patient_opens_and_returns_exact_page(display_mode, patient_alive):
    execute(setup(display_mode)+f'_patientAlive={str(patient_alive).lower()};'+r'''
        call _launch; call _frame; call _frame;
        [count _created==1,"current launch failed"] call _check;
        [(uiNamespace getVariable ["ACME_IV_PendingLaunch",[1]]) isEqualTo [],"pending ownership survived onLoad"] call _check;
        call _close;call _close;call _timers;
        [_reopened isEqualTo [[_patient,"advanced",3]],"captured page did not return once"] call _check;
        [_saves==1,"duplicate unload saved twice"] call _check;
        [{!(_x select 2)} count _leases==1,"normal close did not retire one lease"] call _check;
    ''')


INVALIDATIONS = [
    '_patient setVariable ["epoch",8];',
    '_controlled=parsingNamespace;',
    '_alive=false;',
    '_providerLocal=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    'uiNamespace setVariable ["ACME_IV_Patient",objNull];',
]


@pytest.mark.parametrize('display_mode', [False, True])
@pytest.mark.parametrize('change', INVALIDATIONS)
def test_invalid_pending_launch_releases_its_lease_without_stale_menu(display_mode, change):
    execute(setup(display_mode)+r'''
        call _launch; private _pending=+(uiNamespace getVariable ["ACME_IV_PendingLaunch",[]]);
    '''+change+r'''
        call _frame;call _frame;call _timers;
        [count _created==0 && {count _reopened==0},"invalid launch created or reopened stale UI"] call _check;
        [(uiNamespace getVariable ["ACME_IV_PendingLaunch",[1]]) isEqualTo [],"cancelled pending launch leaked"] call _check;
        [count _leases==2 && {!((_leases select 1) select 2)},"pending cancellation did not release exactly its lease"] call _check;
        [objNull,_pending,true] call ACME_fnc_ivMinigameClose;
        [count _leases==2 && {_saves==0},"duplicate cancellation released or saved again"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_displayStack pushBack profileNamespace;',
    'uiNamespace setVariable ["ACME_medicalMenuRendererEpoch",13];',
    'ace_medical_gui_lastOpenedOn=11;',
    'uiNamespace setVariable ["ACME_medicalReturnSerial",99];',
    'uiNamespace setVariable ["ACME_minigame_open",true];',
    'missionNamespace setVariable ["ACME_flashlightMenuActive",true];',
    'uiNamespace setVariable ["ACME_minigame_reopen","other panel"];',
])
@pytest.mark.parametrize('boundary', ['outer', 'inner'])
def test_new_ui_wins_even_when_opened_and_closed_between_frames(change, boundary):
    execute(setup(boundary == 'inner')+r'''call _launch;'''+('call _frame;' if boundary == 'inner' else '')+change+r'''
        private _before=+_displayStack;
        call _frame;call _frame;call _timers;
        [count _created==0 && {count _reopened==0},"pending launch stole newer UI"] call _check;
        [_displayStack isEqualTo _before,"pending cleanup closed replacement UI"] call _check;
        [count _leases==2 && {!((_leases select 1) select 2)},"new UI cancellation leaked lease"] call _check;
    ''')


@pytest.mark.parametrize('change', INVALIDATIONS)
def test_display_mode_rechecks_provider_and_patient_at_actual_creation(change):
    execute(setup(True)+r'''call _launch;call _frame;'''+change+r'''
        call _frame;call _timers;
        [count _created==0 && {count _reopened==0},"inner creation ignored invalidation"] call _check;
        [count _leases==2 && {!((_leases select 1) select 2)},"inner cancellation leaked lease"] call _check;
    ''')


@pytest.mark.parametrize('change', INVALIDATIONS)
def test_open_panel_closes_when_its_provider_or_clinical_episode_changes(change):
    execute(setup()+r'''call _launch;call _frame;'''+change+r'''
        call _activeTick;call _timers;
        [(uiNamespace getVariable ["ACME_IV_DLG",objNull]) isEqualTo objNull,"invalid active panel survived"] call _check;
        [count _reopened==0,"active cancellation reopened stale provider/clinical context"] call _check;
        [{!(_x select 2)} count _leases==1,"active cancellation did not release exactly its lease"] call _check;
    ''')


def test_active_panel_remains_usable_on_current_dead_patient():
    execute(setup()+r'''
        _patientAlive=false;call _launch;call _frame;call _activeTick;
        [(uiNamespace getVariable ["ACME_IV_DLG",objNull]) isEqualTo _drawDisplay,"corpse lost active IV panel"] call _check;
        [{!(_x select 2)} count _leases==0,"current corpse released active lease"] call _check;
    ''')


@pytest.mark.parametrize('display_mode', [False, True])
@pytest.mark.parametrize('other_patient', [False, True])
def test_new_launch_retires_old_pending_without_cross_session_release(display_mode, other_patient):
    execute(setup(display_mode)+r'''
        call _launch; private _old=+(uiNamespace getVariable ["ACME_IV_PendingLaunch",[]]);
        private _oldKey=_old select 7;
    '''+('_patient=missionNamespace;' if other_patient else '')+r'''
        call _launch;private _new=+(uiNamespace getVariable ["ACME_IV_PendingLaunch",[]]);
        private _newKey=_new select 7;
        [objNull,_old,true] call ACME_fnc_ivMinigameClose;
        call _frame;call _frame;call _timers;
        [count _created==1 && {count _reopened==0},"stale queued launch replaced current launch"] call _check;
        [_oldKey!=_newKey,"reused monitor lease key"] call _check;
        [{(_x select 1)==_oldKey && {!(_x select 2)}} count _leases==1,"old lease not retired once"] call _check;
        [{(_x select 1)==_newKey && {!(_x select 2)}} count _leases==0,"stale callback released new lease"] call _check;
        [(_drawDisplay getVariable ["ACME_IV_Session",[]]) isEqualTo (_new select 0),"wrong display owner"] call _check;
    ''')


@pytest.mark.parametrize('display_mode', [False, True])
def test_two_concrete_displays_replacement_then_old_unload_preserves_new_workspace(display_mode):
    execute(setup(display_mode)+r'''
        call _launch;call _frame;call _frame;
        private _oldDisplay=_drawDisplay;
        private _oldKey=_oldDisplay getVariable ["ACME_IV_ECGKey",""];
        _drawDisplay=parsingNamespace;call _launch;call _frame;call _frame;
        private _newKey=_drawDisplay getVariable ["ACME_IV_ECGKey",""];
        private _newSession=+(uiNamespace getVariable ["ACME_IV_Session",[]]);
        uiNamespace setVariable ["ACME_IV_Held","needle"];
        private _before=+_leases;private _saved=_saves;
        [_oldDisplay] call ACME_fnc_ivMinigameClose;[_oldDisplay] call ACME_fnc_ivMinigameClose;
        [_drawDisplay isNotEqualTo _oldDisplay,"fixture did not create distinct display identities"] call _check;
        [(uiNamespace getVariable ["ACME_IV_DLG",objNull]) isEqualTo _drawDisplay
            && {(uiNamespace getVariable ["ACME_IV_Session",[]]) isEqualTo _newSession}
            && {(uiNamespace getVariable ["ACME_IV_Held",""])=="needle"},"old unload tore down replacement workspace"] call _check;
        [_leases isEqualTo _before && {_saves==_saved},"old unload dispatched duplicate cleanup or save"] call _check;
        [{(_x select 1)==_oldKey && {!(_x select 2)}} count _leases==1,"replacement did not retire old display lease once"] call _check;
        [{(_x select 1)==_newKey && {!(_x select 2)}} count _leases==0,"old unload released replacement lease"] call _check;
    ''')


def test_late_unload_releases_only_its_uncleaned_captured_display_lease_once():
    execute(setup()+r'''
        call _launch;call _frame;
        private _oldDisplay=_drawDisplay;
        private _oldKey=_oldDisplay getVariable ["ACME_IV_ECGKey",""];
        private _session=+(uiNamespace getVariable ["ACME_IV_Session",[]]);
        // Model delayed native Unload after replacement onLoad, with independent
        // concrete handles. Never give the obsolete display current globals.
        _drawDisplay=parsingNamespace;_session set [2,2];
        uiNamespace setVariable ["ACME_IV_Session",_session];
        uiNamespace setVariable ["ACME_IV_ECGKey","replacement-key"];
        [_drawDisplay] call _init;
        uiNamespace setVariable ["ACME_IV_Held","new workspace"];
        private _before=count _leases;private _saved=_saves;
        [_oldDisplay] call ACME_fnc_ivMinigameClose;[_oldDisplay] call ACME_fnc_ivMinigameClose;
        [count _leases==_before+1 && {((_leases select _before) select 1)==_oldKey}
            && {!((_leases select _before) select 2)},"late display lease was lost, duplicated or released wrong key"] call _check;
        [(uiNamespace getVariable ["ACME_IV_DLG",objNull]) isEqualTo _drawDisplay
            && {(uiNamespace getVariable ["ACME_IV_Session",[]]) isEqualTo _session}
            && {(uiNamespace getVariable ["ACME_IV_Held",""])=="new workspace"}
            && {_saves==_saved} && {count _waits==0},"late unload touched replacement controls, saved work or queued a return"] call _check;
    ''')


@pytest.mark.parametrize('display_mode', [False, True])
def test_failed_native_creation_returns_once_without_watchdog_or_saved_work(display_mode):
    execute(setup(display_mode, fail=True)+r'''
        call _launch;private _pending=+(uiNamespace getVariable ["ACME_IV_PendingLaunch",[]]);
        CBA_missionTime=200;call _frame; CBA_missionTime=1000;call _frame;
        [objNull,_pending,true] call ACME_fnc_ivMinigameClose;
        call _timers;
        [count _created==0 && {_saves==0},"failed creation touched uninitialized renderer"] call _check;
        [_reopened isEqualTo [[_patient,"advanced",3]],"creation failure did not restore exact page once"] call _check;
        [count _leases==2 && {!((_leases select 1) select 2)},"creation failure leaked or double-released lease"] call _check;
    ''')


@pytest.mark.parametrize('display_mode', [False, True])
@pytest.mark.parametrize('replacement', [
    '_displayStack pushBack profileNamespace;',
    'uiNamespace setVariable ["ACME_medicalMenuRendererEpoch",13];',
])
def test_creation_failure_does_not_adopt_replacement_ui_as_return_baseline(display_mode, replacement):
    execute(setup(display_mode, fail=True)+'_creationSideEffect={'+replacement+r'''};
        call _launch;call _frame;call _frame;
        // A newer display may close again before the delayed return would run.
        _displayStack=_displayStack-[profileNamespace];call _timers;
        [count _reopened==0,"failed create adopted newer UI as return baseline"] call _check;
        [count _leases==2 && {!((_leases select 1) select 2)},"failed create with replacement leaked lease"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_controlled=parsingNamespace;',
    '_alive=false;',
    '_providerLocal=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_patient setVariable ["epoch",8];',
    '_displayStack pushBack profileNamespace;',
    'call _launch;',
])
def test_delayed_return_cannot_survive_control_or_ui_replacement(change):
    execute(setup(fail=True)+r'''call _launch;call _frame;'''+change+r'''
        call _timers;
        [count _reopened==0,"delayed return stole provider or replacement UI"] call _check;
    ''')


def test_shared_opener_defaults_still_create_for_existing_callers():
    execute(setup()+r'''
        ["existing panel"] call ACME_fnc_minigameOpen;
        [_created isEqualTo ["existing panel"],"default opener behavior changed"] call _check;
    ''')


@pytest.mark.parametrize('display_mode', [False, True])
@pytest.mark.parametrize('fail', [False, True])
@pytest.mark.parametrize('parent_present', [False, True])
def test_shared_opener_reports_actual_creation_result_with_original_guard_args(display_mode, fail, parent_present):
    execute(setup(display_mode, fail)+('' if parent_present else '_missionDisplay=objNull;')+r'''
        private _completions=[];
        ["existing panel",{true},["captured identity"],{_completions pushBack +_this;}] call ACME_fnc_minigameOpen;
        call _frame;
    '''+f'[_completions isEqualTo [[{str(not fail).lower()},["captured identity"]]],"creation completion lost result or captured guard arguments"] call _check;')


def test_parent_deleted_after_queue_uses_truthful_dialog_fallback():
    execute(setup(True)+r'''
        ["existing panel"] call ACME_fnc_minigameOpen;
        // Namespace stand-ins do not delete: adapt the captured display handle
        // to the objNull handle Arma supplies after its display is destroyed.
        ((_frames select 0) select 1) set [1,objNull];
        call _frame;
        [_created isEqualTo ["existing panel"] && {_dialog},"lost parent did not use native dialog fallback"] call _check;
        [!(uiNamespace getVariable ["ACME_minigame_openedAsDisplay",true]),"lost parent retained false display-mode identity"] call _check;
    ''')


def test_provider_deleted_during_return_delay_cannot_rebind_to_new_controller():
    execute(setup(fail=True)+r'''
        call _launch;call _frame;
        // Mirror the engine invalidating a destroyed object in captured args.
        ((_waits select 0) select 1) set [7,objNull];
        _controlled=parsingNamespace;call _timers;
        [count _reopened==0,"deleted captured provider rebound stale return to another unit"] call _check;
    ''')
