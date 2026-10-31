"""Run chest entry cancellation and patient-owner cleanup after medical-menu reopen.

Native display creation is a recorded boundary. The production entry worker,
token cleanup and patient-owner begin/end callbacks execute in SQF-VM.
"""
import re
import pytest

from test_chest_entry_timing import setup as entry_setup
from test_chestseal_preparation_progress import setup as owner_setup
from test_menu_death_lifecycle import adapt, execute, read


def native_open_setup():
    """Execute minigameOpen; record only native createDialog/createDisplay."""
    source = read("minigameOpen")
    source = source.replace("findDisplay 46", "missionNamespace")
    source = re.sub(r"\bcreateDialog (_\w+)\b", r'[\1] call _nativeDialog', source)
    source = source.replace('!isNull (_p createDisplay _cls)',
                            '(([_cls] call _nativeDisplay) isNotEqualTo objNull)')
    return entry_setup() + r'''
        private _created=[]; private _nextFrames=[];
        private _nativeDialog={_created pushBack ["nativeDialog",_this select 0];true};
        private _nativeDisplay={
            _created pushBack ["nativeDisplay",_this select 0];
            uiNamespace setVariable ["ACME_CS_DLG",missionNamespace];missionNamespace
        };
        CBA_fnc_execNextFrame={_nextFrames pushBack [_this select 0,_this select 1];};
    ''' + 'ACME_fnc_minigameOpen={' + adapt(source) + '};\n'


@pytest.mark.parametrize("ready", [False, True])
def test_medical_menu_reopened_before_load_cancels_pending_entry_and_allows_retry(ready):
    execute(entry_setup() + r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _token=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        private _pending=uiNamespace getVariable ["ACME_CS_EntryPFH",-1];
        // ACE H keydown creates a fresh medical menu during owner preparation.
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
    ''' + ('call _ack;' if ready else '') + r'''
        call _entryTick;
        [count _opened==0,"pending chest entry replaced the reopened medical menu"] call _check;
        [(uiNamespace getVariable ["ACME_CS_SessionToken","wrong"])=="",
            "medical-menu cancellation stranded chest session token"] call _check;
        [(uiNamespace getVariable ["ace_medical_gui_menuDisplay",objNull]) isEqualTo missionNamespace,
            "cancellation closed the newly opened medical menu"] call _check;
        [_pending in _removed && {(uiNamespace getVariable ["ACME_CS_EntryPFH",-2])==-1},
            "entry PFH survived medical-menu cancellation"] call _check;
        [{_x in _removed} count ["key0","key1"]==2
            && {(uiNamespace getVariable ["ACME_CS_EntryKeys",[1]]) isEqualTo []},
            "entry input handlers survived medical-menu cancellation"] call _check;
        [{count _x>=3 && {(_x select 1) isEqualTo "chestSealPatientEnd"}
            && {((_x select 2) select 1)==_token}} count _events==1,
            "medical-menu cancellation did not release exact owner token once"] call _check;
        [!((_preparing select ((count _preparing)-1)) select 0),
            "preparing banner survived medical-menu cancellation"] call _check;

        // Model ACE closing the source display for the next treatment click.
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",objNull];
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _newToken=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        call _ack; call _entryTick;
        [_newToken!=_token && {count _opened==1}
            && {(uiNamespace getVariable ["ACME_CS_SessionToken",""])==_newToken},
            "subsequent chest treatment could not open a clean session"] call _check;
    ''')


def test_old_pending_completion_and_watchdog_cannot_close_retried_session():
    execute(entry_setup() + r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _token=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        private _pending=uiNamespace getVariable ["ACME_CS_EntryPFH",-1];
        private _oldOpen=((_handlers select _pending) select 1) select 3;
        call _ack; call _entryTick;
        private _watchdog=_waits select ((count _waits)-1);
        [] call ACME_fnc_chestSealClose;
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _newToken=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        private _newPending=uiNamespace getVariable ["ACME_CS_EntryPFH",-1];
        [_patient,_token,_medic,objNull] call _oldOpen;
        [_pending] call _poseTick;
        [_watchdog] call _deliver;
        [(uiNamespace getVariable ["ACME_CS_SessionToken",""])==_newToken
            && {(uiNamespace getVariable ["ACME_CS_EntryPFH",-1])==_newPending},
            "stale entry continuation retired the retried session"] call _check;
        call _ack; call _entryTick;
        [count _opened==2,"retried session failed after stale continuation delivery"] call _check;
    ''')


@pytest.mark.parametrize("ready", [False, True])
def test_medical_open_then_close_between_entry_ticks_still_cancels(ready):
    execute(entry_setup() + r'''
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        uiNamespace setVariable ["ACME_medicalMenuRendererEpoch",1];
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",objNull];
    ''' + ('call _ack;' if ready else '') + r'''
        call _entryTick;
        [count _opened==0 && {(uiNamespace getVariable ["ACME_CS_SessionToken","bad"])==""},
            "H open/close between sparse entry ticks did not cancel preparation"] call _check;
    ''')


def test_patient_owner_receives_cancel_before_begin_without_resurrecting_workspace():
    execute(owner_setup() + r'''
        // Dedicated ownership transport may deliver End before an initial Begin/retry.
        [_patient,"canceled",_medic] call ACME_fnc_chestSealPatientEnd;
        private _before=+_waits;
        [_patient,"canceled",_medic] call ACME_fnc_chestSealPatientBegin;
        [_waits isEqualTo _before
            && {(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo []}
            && {!(_patient getVariable ["ACME_CS_ProcedureActive",false])},
            "late Begin resurrected canceled owner workspace"] call _check;
        [_patient,"retry",_medic] call ACME_fnc_chestSealPatientBegin;
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo ["retry"],
            "cancel tombstone prevented a fresh treatment attempt"] call _check;
        private _pending=+_waits;
        [_patient,"canceled",_medic] call ACME_fnc_chestSealPatientEnd;
        [_waits isEqualTo _pending
            && {(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo ["retry"]},
            "late old End released the new owner workspace"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '[] call ACME_fnc_chestSealClose;',
    '[] call ACME_fnc_chestSealClose; [_medic,_patient] call ACME_fnc_chestSealOpen;',
    'uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];',
    'uiNamespace setVariable ["ACME_CS_Patient",missionNamespace];',
    'uiNamespace setVariable ["ACME_CS_Medic",missionNamespace];',
    '_patient setVariable ["ACME_equipmentKitEpoch",1];',
    'uiNamespace setVariable ["ACME_CS_SessionSerial",99];',
    'uiNamespace setVariable ["ACME_medicalMenuRendererEpoch",99];',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_patientOwnerFixture=3;',
    '_alive=false;',
    '_isLocal=false;',
])
def test_queued_native_open_rechecks_episode_and_does_not_create_stale_panel(change):
    execute(native_open_setup() + r'''
        missionNamespace setVariable ["ACME_minigame_displayMode",true];
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        call _ack; call _entryTick;
        [count _nextFrames==1 && {count _created==0},"display creation was not deferred"] call _check;
        private _old=+(_nextFrames select 0);
    ''' + change + r'''
        (_old select 1) call (_old select 0);
        [count _created==0,"queued chest open created a stale panel"] call _check;
    ''')


def test_valid_queued_open_and_other_callers_preserve_existing_creation_behavior():
    execute(native_open_setup() + r'''
        // A default caller requires no new guard or argument.
        ["ACME_IV_Dialog"] call ACME_fnc_minigameOpen;
        [_created isEqualTo [["nativeDialog","ACME_IV_Dialog"]],"ordinary dialog caller changed"] call _check;
        _created=[];
        missionNamespace setVariable ["ACME_minigame_displayMode",true];
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        call _ack; call _entryTick;
        private _frame=_nextFrames select 0;
        (_frame select 1) call (_frame select 0);
        [_created isEqualTo [["nativeDisplay","ACME_ChestSeal_Dialog"]],
            "valid queued chest episode could not open"] call _check;
    ''')


def test_rejected_open_does_not_close_the_newer_dialog():
    execute(native_open_setup() + r'''
        _dialog=true;
        missionNamespace setVariable ["ACME_minigame_displayMode",true];
        ["ACME_IV_Dialog",{false},[]] call ACME_fnc_minigameOpen;
        [_dialog && {count _created==0} && {count _nextFrames==0},
            "rejected open closed a newer dialog before evaluating its guard"] call _check;
    ''')


def test_medical_menu_reopened_during_queued_open_keeps_menu_and_watchdog_cleans_up():
    execute(native_open_setup() + r'''
        missionNamespace setVariable ["ACME_minigame_displayMode",true];
        [_medic,_patient] call ACME_fnc_chestSealOpen;
        private _token=uiNamespace getVariable ["ACME_CS_SessionToken",""];
        call _ack; call _entryTick;
        private _frame=_nextFrames select 0;
        private _watchdog=_waits select ((count _waits)-1);
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
        (_frame select 1) call (_frame select 0);
        [_watchdog] call _deliver;
        [count _created==0 && {(uiNamespace getVariable ["ACME_CS_SessionToken","bad"])==""},
            "blocked queued open retained its chest session"] call _check;
        [(uiNamespace getVariable ["ace_medical_gui_menuDisplay",objNull]) isEqualTo missionNamespace,
            "queued cancellation destroyed reopened medical menu"] call _check;
        [{count _x>=3 && {(_x select 1) isEqualTo "chestSealPatientEnd"}
            && {((_x select 2) select 1)==_token}} count _events==1,
            "queued cancellation did not retire exact patient owner token"] call _check;
    ''')
