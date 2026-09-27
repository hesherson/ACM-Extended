"""Execute the actual observer receiver with native animation/network calls simulated.

SQF-VM verifies packet ordering and handler lifecycle. Arma multiplayer is still
required to verify rendered motion, interpolation and network timing.
"""
import os
import re
from pathlib import Path
import shutil
import subprocess

import pytest

FUNCTIONS = Path(__file__).resolve().parents[1] / "functions"


def execute(scenario):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM is required for observer execution checks")
    source = (FUNCTIONS / "fn_treatmentPoseSync.sqf").read_text()
    substitutions = {
        "!isNull objectParent _medic": "_testVehicle",
        "isNull objectParent _medic": "(!_testVehicle)",
        "isNull _medic": "_testNull",
        "local _medic": "_testLocal",
        "owner _medic": "(if (_testServer) then {_testOwner} else {0})",
        "clientOwner": "_testClient",
        "isServer": "_testServer",
        "finite _visiblePhase": "true",
        "finite _rate": "true",
        "alive _medic": "_testAlive",
        "getAnimSpeedCoef _medic": "_testSpeed",
        "animationState _medic": "_testMove",
        "_medic getUnitMovesInfo 0": "_testPhase",
        "_medic setAnimSpeedCoef 0;": "_testSpeed = 0;",
        "_medic setAnimSpeedCoef 1;": "_testSpeed = 1;",
        'netId _medic': '"provider"',
        "_medic switchMove [_main, _phase, 1, false];":
            "_seeks = _seeks + 1; if (!_deferSeek) then {_testMove = _main; _testPhase = _phase;};",
        '[_epoch, false], true]': '[_epoch, false]]',
    }
    for original, replacement in substitutions.items():
        source = source.replace(original, replacement)
    source = re.sub(r"_medic setAnimSpeedCoef ([^;]+);", r"_testSpeed = (\1);", source)
    code = r'''
        private _ok = true;
        private _testNull = false;
        private _testLocal = false;
        private _testOwner = 7;
        private _testClient = 8;
        private _testServer = false;
        private _testAlive = true;
        private _testVehicle = false;
        private _testSpeed = 1;
        private _testMove = "ACME_StethoscopeWork";
        private _testPhase = 0.1;
        private _seeks = 0;
        private _deferSeek = false;
        private _handlers = [];
        private _waits = [];
        private _delays = [];
        private _removedJIP = 0;
        private _exitMoves = 0;
        CBA_missionTime = 10;
        private _medic = missionNamespace;
        _medic setVariable ["ACME_treatmentPoseEpisode", [1, true]];
        CBA_fnc_addPerFrameHandler = {
            params ["_code", "_delay", "_args"];
            _handlers pushBack [_code, _args, true];
            (count _handlers) - 1
        };
        CBA_fnc_removePerFrameHandler = {(_handlers select (_this select 0)) set [2, false];};
        CBA_fnc_waitUntilAndExecute = {_waits pushBack _this;};
        CBA_fnc_waitAndExecute = {_delays pushBack _this;};
        CBA_fnc_removeGlobalEventJIP = {_removedJIP = _removedJIP + 1;};
        ACME_fnc_doAnim = {_exitMoves = _exitMoves + 1;};
        private _tick = {
            params [["_id", 0]];
            private _handler = _handlers select _id;
            if (_handler select 2) then {[_handler select 1, _id] call (_handler select 0);};
        };
        private _hold = {[_medic, 1, "hold", "ACME_StethoscopeWork", 0.14, 7] call ACME_fnc_treatmentPoseSync;};
        private _release = {[_medic, 1, "release"] call ACME_fnc_treatmentPoseSync;};
        private _check = {if !(_this select 0) then {_ok = false; diag_log ("POSE_SYNC_FAIL: " + (_this select 1));};};
        ACME_fnc_treatmentPoseSync = {''' + source + "};\n" + scenario + r'''
        diag_log (if (_ok) then {"POSE_SYNC_OK"} else {"POSE_SYNC_FAIL"});
    '''
    result = subprocess.run([vm, "--automated", "--suppress-welcome", "--no-execute-print",
                             "--no-work-print", "--sqf", code], capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and "[ERR]" not in output, output
    assert "POSE_SYNC_OK" in output and "POSE_SYNC_FAIL" not in output, output


def test_remote_hold_survives_delayed_animation_entry_and_repairs_state_and_phase():
    execute('''
        _deferSeek = true;
        _testMove = "crouch";
        call _hold;
        [] call _tick;
        [(_handlers select 0) select 2, "early transition retired hold"] call _check;
        _deferSeek = false;
        CBA_missionTime = 10.3;
        [] call _tick;
        [_testMove == "ACME_StethoscopeWork" && {_testSpeed == 0}, "state drift not repaired"] call _check;
        _testPhase = 0.4;
        CBA_missionTime = 10.6;
        [] call _tick;
        [abs (_testPhase - 0.14) < 0.001 && {_seeks == 4}, "phase drift not repaired"] call _check;
    ''')


def test_speed_resets_and_duplicate_hold_do_not_restart_animation_or_handler():
    execute('''
        call _hold;
        call _hold;
        _testSpeed = 1;
        [] call _tick;
        [_testSpeed == 0 && {_seeks == 1} && {count _handlers == 1}, "duplicate/speed reset restarted hold"] call _check;
    ''')


def test_release_restores_speed_and_rejects_late_hold():
    execute('''
        call _hold;
        call _release;
        call _hold;
        [_testSpeed == 1 && {!((_handlers select 0) select 2)} && {_seeks == 1}, "release did not remain released"] call _check;
    ''')


def test_cancelled_owner_and_newer_episode_reject_delayed_old_hold():
    execute('''
        _testLocal = true; _testClient = 7;
        _medic setVariable ["ACME_treatmentPoseEpisode", [1, false]];
        call _hold;
        [_testSpeed == 1 && {_seeks == 0}, "cancelled owner refrozen"] call _check;
        _medic setVariable ["ACME_treatmentPoseEpisode", [2, true]];
        call _hold;
        [_testSpeed == 1 && {_seeks == 0}, "newer owner episode refrozen"] call _check;
    ''')


def test_active_owner_echo_never_seeks_or_installs_observer_handler():
    execute('''
        _testLocal = true; _testClient = 7;
        call _hold;
        [_testSpeed == 0 && {_seeks == 0} && {count _handlers == 0}, "owner echo restarted animation"] call _check;
    ''')


def test_old_release_cannot_stop_new_remote_hold():
    execute('''
        call _hold;
        _medic setVariable ["ACME_treatmentPoseEpisode", [2, true]];
        [_medic, 2, "hold", "ACME_StethoscopeWork", 0.14, 7] call ACME_fnc_treatmentPoseSync;
        call _release;
        [_testSpeed == 0 && {(_handlers select 1) select 2}, "old release stopped new hold"] call _check;
        [!((_handlers select 0) select 2), "superseded handler remained active"] call _check;
    ''')


@pytest.mark.parametrize("ending", [
    "_testAlive = false;",
    '_medic setVariable ["ACE_isUnconscious", true];',
    "_testVehicle = true;",
    '_medic setVariable ["ACME_treatmentPoseEpisode", [1, false]];',
    "_testOwner = 8; _testServer = true;",
])
def test_hard_end_releases_observer(ending):
    execute('call _hold; ' + ending + '''
        [] call _tick;
        [_testSpeed == 1 && {!((_handlers select 0) select 2)}, "ended context stayed frozen"] call _check;
    ''')


def test_jip_hold_waits_for_episode_and_cancel_wins_before_delivery():
    execute('''
        _medic setVariable ["ACME_treatmentPoseEpisode", [-1, false]];
        call _hold;
        [count _waits == 1 && {count _handlers == 0}, "JIP did not await episode"] call _check;
        call _release;
        _medic setVariable ["ACME_treatmentPoseEpisode", [1, true]];
        private _wait = _waits select 0;
        (_wait select 2) call (_wait select 1);
        [_testSpeed == 1 && {count _handlers == 0}, "late JIP revived cancelled hold"] call _check;
    ''')


def test_jip_hold_applies_after_episode_arrives():
    execute('''
        _medic setVariable ["ACME_treatmentPoseEpisode", [-1, false]];
        call _hold;
        _medic setVariable ["ACME_treatmentPoseEpisode", [1, true]];
        private _wait = _waits select 0;
        (_wait select 2) call (_wait select 1);
        [_testSpeed == 0 && {count _handlers == 1}, "JIP failed to apply hold"] call _check;
    ''')


def test_unknown_phase_freezes_without_inventing_a_seek():
    execute('''
        [_medic, 1, "hold", "ACME_StethoscopeWork", -1, 7] call ACME_fnc_treatmentPoseSync;
        [] call _tick;
        [_testSpeed == 0 && {_seeks == 0}, "unknown phase invented seek"] call _check;
    ''')


def test_deleted_provider_retires_observer_handler():
    execute("""
        call _hold;
        _testNull = true;
        [] call _tick;
        [!((_handlers select 0) select 2), "deleted provider kept handler"] call _check;
    """)


def test_new_owner_aborts_old_episode_and_releases_to_crouch():
    execute("""
        call _hold;
        _testLocal = true; _testClient = 8;
        [] call _tick;
        [_testSpeed == 1 && {_removedJIP == 1} && {_exitMoves == 1}, "new owner retained old hold"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseEpisode", []]) isEqualTo [1, false], "old episode still active"] call _check;
    """)


def test_remote_phase_update_is_repaired_on_next_frame_without_quarter_second_motion():
    execute('''
        call _hold;
        _testPhase = 0.20;
        CBA_missionTime = 10.016;
        [] call _tick;
        [abs (_testPhase - 0.14) < 0.001 && {_seeks == 2} && {_testSpeed == 0}, "remote update visibly escaped held sample"] call _check;
        [] call _tick;
        [_seeks == 2, "stable frozen phase was needlessly restarted"] call _check;
    ''')


def test_reordered_run_cannot_unfreeze_hold_or_release():
    execute('''
        call _hold;
        [_medic, 1, "run", "", -1, 7, 1.5] call ACME_fnc_treatmentPoseSync;
        [_testSpeed == 0, "late run unfroze hold"] call _check;
        call _release;
        [_medic, 1, "run", "", -1, 7, 1.5] call ACME_fnc_treatmentPoseSync;
        [_testSpeed == 1, "late run revived stopped episode"] call _check;
    ''')


def test_new_episode_variable_overtakes_old_release_and_watchdog():
    execute('''
        call _hold;
        _medic setVariable ["ACME_treatmentPoseEpisode", [2, true]];
        _testSpeed = 1.5;
        call _release;
        [] call _tick;
        [_testSpeed == 1.5, "old cleanup reset new episode speed"] call _check;
    ''')


def test_cancel_before_run_or_hold_stays_terminal():
    execute('''
        call _release;
        [_medic, 1, "run", "", -1, 7, 1.5] call ACME_fnc_treatmentPoseSync;
        call _hold;
        [_testSpeed == 1 && {count _handlers == 0}, "cancel-before-entry was revived"] call _check;
    ''')


def test_accelerated_exit_is_bounded_and_old_exit_cannot_reset_next_hold():
    execute('''
        call _hold;
        _medic setVariable ["ACME_treatmentPoseEpisode", [1, false]];
        [_medic, 1, "exit", "", -1, 7, 1.5] call ACME_fnc_treatmentPoseSync;
        [_testSpeed == 1.5 && {abs (((_delays select 0) select 2) - (0.85 / 1.5)) < 0.001}, "exit rate/duration mismatch"] call _check;
        _medic setVariable ["ACME_treatmentPoseEpisode", [2, true]];
        [_medic, 2, "hold", "ACME_StethoscopeWork", 0.14, 7] call ACME_fnc_treatmentPoseSync;
        private _job = _delays select 0;
        (_job select 1) call (_job select 0);
        [_testSpeed == 0, "old exit reset next hold"] call _check;
    ''')
