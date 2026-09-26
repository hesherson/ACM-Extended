"""B167 continuous-action / medical-menu recovery contracts.

The reported failures were shared-lifetime defects: Head Tilt-Chin Lift and manual Semi-Fowler are non-dialog
continuous actions, but neither opted back into medical-menu reopen, and a broken action callback could refresh the
shared heartbeat before throwing. These checks protect the corrected ownership boundaries.
"""
from pathlib import Path

import pytest

from test_menu_death_lifecycle import ROOT, core, execute
from test_b156_menu_pose import setup as menu_setup

AIRWAY = ROOT / "addons" / "airway" / "functions" / "fnc_beginHeadTiltChinLift.sqf"
ACME = ROOT / "addons" / "acm_extended" / "functions"
CORE = ROOT / "addons" / "core"


def read(path):
    return Path(path).read_text(encoding="utf-8")


def test_shared_continuous_controller_has_explicit_reopen_policy_and_bool_result():
    source = read(CORE / "functions" / "fnc_beginContinuousAction.sqf")
    assert '["_reopenOnEnd", false, [false]]' in source
    assert 'GVAR(ContinuousAction_ShouldReopen) = _reopenOnEnd;' in source
    assert 'exitWith {false};' in source
    assert source.rstrip().endswith("true")
    # Startup grace must preserve, not erase, the action's opt-in.
    grace = source[source.index("private _dialogCondition = false;"):source.index("if (_patientCondition", source.index("private _dialogCondition = false;"))]
    assert 'GVAR(ContinuousAction_ShouldReopen) = _reopenOnEnd;' in grace
    assert 'GVAR(ContinuousAction_ShouldReopen) = false;' not in grace


def test_heartbeat_is_published_only_after_action_perframe_returns():
    source = read(CORE / "functions" / "fnc_beginContinuousAction.sqf")
    perframe = source.rindex("_args call _perFrame;")
    heartbeat = source.rindex('setVariable [QGVAR(ContinuousAction_LastSeen), CBA_missionTime, true]')
    assert perframe < heartbeat


def test_head_tilt_uses_shared_stale_recovery_and_reopens_on_cancel():
    source = read(AIRWAY)
    entry = source[:source.index("if (_patient getVariable [QGVAR(HeadTilt_State), false])")]
    assert 'ContinuousAction_Active' not in entry
    assert '}, false, -1, false, true] call EFUNC(core,beginContinuousAction)' in source
    assert 'continuousHoldRelease' in source


def test_manual_semifowler_uses_shared_stale_recovery_and_reopens_on_cancel():
    source = read(ACME / "fn_headElevHoldStart.sqf")
    guard = source[:source.index("if (!_ready) exitWith")]
    assert 'ContinuousAction_Active' not in guard
    assert 'private _started = [[' in source
    assert '}, false, -1, true, true] call ACM_core_fnc_beginContinuousAction;' in source
    assert 'if !(_started isEqualTo true) then {' in source
    assert 'call _releasePatient;' in source


def test_medical_menu_open_immediately_yields_only_exact_head_hands_on_session():
    source = read(ACME / "fn_registerMedicalMenuOpenRuntime.sqf")
    assert 'ACM_airway_HeadTilt_State_Session' in source
    assert 'ACME_headElev_holding' in source
    assert '_headTiltSession isEqualTo [_medic, _epoch]' in source
    assert 'if (_ownsHeadTilt || {_ownsManualSemiFowler}) then {' in source
    assert 'missionNamespace setVariable ["ACM_core_ContinuousAction_Active", false];' in source
    assert 'if (!_cancelledHandsOn) then {' in source


def test_treatment_bridge_does_not_supersede_hands_on_epoch_before_old_cancel():
    source = read(CORE / "overrides" / "fnc_treatment.sqf")
    assert 'ACM_airway_HeadTilt_State_Session' not in source
    assert 'ACME_headElev_holding' not in source
    assert 'Non-dialog continuous hands-on holds are cancelled by the medical-menu-open event' in source


def continuous_setup():
    return menu_setup() + '''
        ACM_core_fnc_beginContinuousAction={''' + core("beginContinuousAction") + '''};
        ace_weaponselect_fnc_putWeaponAway={};
        private _started=0; private _cancelled=0;
        private _onStart={_started=_started+1;};
        private _onCancel={_cancelled=_cancelled+1;};
        private _perFrame={};
        CBA_fnc_localEvent={_events pushBack _this;};
    '''


def test_opted_in_non_dialog_action_reopens_after_cancel():
    execute(continuous_setup() + '''
        private _accepted=[[_medic,_patient,"head"],_onStart,_onCancel,_perFrame,false,-1,false,true]
            call ACM_core_fnc_beginContinuousAction;
        [_accepted && {_started==1} && {ACM_core_ContinuousAction_ShouldReopen},"reopen episode was not accepted"] call _check;
        ACM_core_ContinuousAction_Active=false;
        call _tick;
        [_cancelled==1,"cancel callback did not run"] call _check;
        [("ACM_core_openMedicalMenu" in (_events apply {_x select 0})),"cancel did not request medical-menu return"] call _check;
        [(_medic getVariable ["ACM_core_ContinuousAction_Session",[]]) isEqualTo [],"provider session survived cancel"] call _check;
    ''')


def test_existing_medical_menu_is_not_destroyed_and_reopened_again():
    execute(continuous_setup() + '''
        private _accepted=[[_medic,_patient,"head"],_onStart,_onCancel,_perFrame,false,-1,false,true]
            call ACM_core_fnc_beginContinuousAction;
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
        missionNamespace setVariable ["ace_medical_gui_target",_patient];
        ACM_core_ContinuousAction_Active=false;
        _events=[];
        call _tick;
        [_cancelled==1,"cancel callback did not run with existing menu"] call _check;
        [!("ACM_core_openMedicalMenu" in (_events apply {_x select 0})),"existing menu was redundantly reopened"] call _check;
    ''')


def test_user_reopened_menu_during_startup_grace_is_not_closed_again():
    execute(continuous_setup() + '''
        private _accepted=[[_medic,_patient,"head"],_onStart,_onCancel,_perFrame,false,-1,false,true]
            call ACM_core_fnc_beginContinuousAction;
        _dialog=true;
        uiNamespace setVariable ["ace_medical_gui_menuDisplay",missionNamespace];
        missionNamespace setVariable ["ace_medical_gui_target",_patient];
        ACM_core_ContinuousAction_Active=false;
        call _tick;
        [_dialog,"startup grace closed the newly reopened medical menu"] call _check;
        [_cancelled==1,"reopened menu did not retire hands-on action"] call _check;
    ''')
