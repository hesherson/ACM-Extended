"""Execute CPR entry, input callbacks, animation loop and cleanup in SQF-VM.

Native animation, object and network commands are simulated. CBA input handlers
return strings, and the real startup/watchdog/cancellation code runs unchanged.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest
from test_menu_death_lifecycle import namespace_public_arguments

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / 'addons/circulation/functions'


def source(name):
    s = (F / f'fnc_{name}.sqf').read_text()
    s = re.sub(r'^#include.*$', '', s, flags=re.M)
    for macro, prefix, quote in [('QACEGVAR', 'ace', True), ('QEGVAR', 'ACM', True), ('EGVAR', 'ACM', False), ('ACEGVAR', 'ace', False)]:
        s = re.sub(r'\b' + macro + r'\((\w+),\s*(\w+)\)', lambda m: ('"' if quote else '') + f'{prefix}_{m[1]}_{m[2]}' + ('"' if quote else ''), s)
    for macro, prefix, quote in [('QGVAR', 'ACM_circulation_', True), ('GVAR', 'ACM_circulation_', False), ('FUNC', 'ACM_circulation_fnc_', False)]:
        s = re.sub(r'\b' + macro + r'\((\w+)\)', lambda m: ('"' if quote else '') + prefix + m[1] + ('"' if quote else ''), s)
    for macro, prefix in [('ACEFUNC', 'ace'), ('EFUNC', 'ACM')]:
        s = re.sub(r'\b' + macro + r'\((\w+),\s*(\w+)\)', lambda m: f'{prefix}_{m[1]}_fnc_{m[2]}', s)
    s = re.sub(r'\bLLSTRING\((\w+)\)', lambda m: '"' + m[1] + '"', s)
    for a, b in {
        'IS_UNCONSCIOUS(_patient)': '_patientUnconscious',
        'IS_UNCONSCIOUS(_medic)': '!_awake',
        'objectParent _medic': '_medicVehicle',
        'objectParent _patient': '_patientVehicle',
        '_patient distance2D _medic': '_distance',
        '_medic distance2D _patient': '_distance',
        'alive _medic': '_alive',
        'alive _patient': '_patientAlive',
        'local _medic': '_local',
        'owner _medic': '_testOwner',
        'currentWeapon _medic': '""',
        '_medic setUnitPos "AUTO";': '_stanceFreed = true;',
        'animationState _medic': '"amovpknlmstpsnonwnondnon"',
        'closeDialog 0;': '_closed = _closed + 1;',
        'hasInterface': '_hasInterface',
        'isServer': '_isServer',
        # All configured delay fixtures are finite; the VM lacks this command.
        'finite _lowerDelay': '(_lowerDelay isEqualType 0)',
        'addMissionEventHandler ["HandleDisconnect",': '_disconnectHandler = (["HandleDisconnect",',
    }.items():
        s = s.replace(a, b)
    s = namespace_public_arguments(s)
    # This fixture represents engine objects with namespaces. SQF-VM also returns
    # nil for a missing typed-object param, unlike Arma's objNull default. Keep the
    # actual fallback/ownership logic while adapting only the object type check.
    s = re.sub(r'(\bparam\s*\[\s*\d+\s*,\s*objNull)\s*,\s*\[objNull\](\s*\])', r'\1\2', s)
    s = re.sub(r'\bisNull (_\w+)', r'(\1 isEqualTo objNull)', s)
    s = re.sub(r'\bdialog\b', '_dialog', s)
    s = re.sub(r'_medic removeEventHandler (\[[^;]+\]);', r'\1 call _removeAnim;', s)
    if name == 'beginCPR':
        s = s.replace('_medic addEventHandler ["AnimDone", {', '(["AnimDone", {')
        s = s.replace('        }];\n        _medic setVariable ["ACM_circulation_CPR_AnimEH", _animEH', '        }] call _addAnim);\n        _medic setVariable ["ACM_circulation_CPR_AnimEH", _animEH')
    if name == 'registerCPRRuntime':
        s = s.replace('        false\n    }];', '        false\n    }] select 1);')
        # Server watchdog age must use the dedicated server's receive clock, not the provider's client clock.
        s = s.replace('CBA_missionTime', '_serverClock')
    return s


def execute(scenario, runtime=False):
    vm = os.environ.get('SQFVM') or shutil.which('sqfvm')
    if not vm:
        pytest.skip('SQF-VM required')
    code = r'''
        private _ok = true;
        private _medic = uiNamespace;
        private _patient = profileNamespace;
        private _alive = true;
        private _awake = true;
        private _patientAlive = true;
        private _patientUnconscious = true;
        private _local = true;
        private _testOwner = 7;
        private _medicVehicle = objNull;
        private _patientVehicle = objNull;
        private _distance = 1;
        private _dialog = false;
        private _closed = 0;
        private _stanceFreed = false;
        private _hints = 0;
        private _keys = [];
        private _removedKeys = [];
        private _anims = [];
        private _removedAnims = [];
        private _moves = [];
        private _handlers = [];
        private _unitHandler = {};
        private _disconnectHandler = {};
        private _trackHandler = {};
        private _hasInterface = true;
        private _isServer = false;
        private _hasBVM = false;
        private _bvmHandoff = 0;
        private _bvmActive = false;
        private _reopens = 0;
        private _logs = [];
        private _texts = [];
        private _dispatches = [];
        private _duringSwitch = false;
        private _fireAnimOnSwitch = false;
        CBA_missionTime = 20;
        private _serverClock = 1000;
        ACE_player = _medic;
        ace_medical_gui_maxDistance = 3;
        ACM_breathing_SwapToCPR = false;
        ACM_core_ContinuousAction_Active = false;
        ace_common_fnc_isAwake = {_awake};
        ACME_fnc_ownerDispatch = {_dispatches pushBack _this;};
        ace_common_fnc_uniqueItems = {if (_hasBVM) then {["ACM_BVM"]} else {[]}};
        ace_common_fnc_displayTextStructured = {_texts pushBack (_this select 0);};
        ace_common_fnc_getName = {"Provider"};
        ace_weaponselect_fnc_putWeaponAway = {};
        ace_common_fnc_doAnimation = {
            _moves pushBack (_this select 1);
            [!(_medic getVariable ["ACM_circulation_CPR_Loop", false]) || {(_this select 1) != "AinvPknlMstpSnonWnonDnon_medicEnd"}, "exit while loop enabled"] call _check;
        };
        ace_medical_treatment_fnc_addToLog = {_logs pushBack (_this select 2);};
        BIS_fnc_secondsToString = {"00:10"};
        ace_interaction_fnc_showMouseHint = {};
        ace_interaction_fnc_hideMouseHint = {_hints = _hints + 1;};
        CBA_fnc_addKeyHandler = {
            private _id = format ["key-%1", count _keys];
            _keys pushBack [_id, _this select 2];
            _id
        };
        CBA_fnc_removeKeyHandler = {_removedKeys pushBack (_this select 0);};
        CBA_fnc_addPerFrameHandler = {_handlers pushBack [_this select 0, _this select 2, true]; count _handlers - 1};
        CBA_fnc_removePerFrameHandler = {(_handlers select (_this select 0)) set [2, false];};
        CBA_fnc_addEventHandler = {_trackHandler = _this select 1;};
        CBA_fnc_addPlayerEventHandler = {_unitHandler = _this select 1;};
        CBA_fnc_serverEvent = {(_this select 1) call _trackHandler;};
        CBA_fnc_targetEvent = {};
        CBA_fnc_localEvent = {_reopens = _reopens + 1;};
        CBA_fnc_globalEvent = {
            if ((_this select 0) == "ace_common_setAnimSpeedCoef") exitWith {};
            private _move = (_this select 1) select 1;
            _moves pushBack _move;
            if (_fireAnimOnSwitch && {!_duringSwitch}) then {
                _duringSwitch = true;
                private _id = _medic getVariable ["ACM_circulation_CPR_AnimEH", -1];
                if (_id >= 0) then {
                    private _thisEventHandler = _id;
                    private _thisEvent = "AnimDone";
                    [_medic, "ACM_CPR"] call (_anims select _id);
                };
                _duringSwitch = false;
            };
        };
        private _addAnim = {_anims pushBack (_this select 1); count _anims - 1};
        private _removeAnim = {_removedAnims pushBack (_this select 1);};
        ACM_core_fnc_cprActive = {!((_patient getVariable ["ace_medical_CPR_provider", objNull]) isEqualTo objNull)};
        ACM_core_fnc_bvmActive = {_bvmActive};
        ACM_breathing_fnc_useBVM = {
            [(_patient getVariable ["ACM_circulation_CPR_Medic", objNull]) isEqualTo objNull, "handoff before CPR release"] call _check;
            _bvmHandoff = _bvmHandoff + 1;
        };
        private _check = {if !(_this select 0) then {_ok = false; diag_log ("CPR_FIX_FAIL " + (_this select 1));};};
        private _tick = {
            private _id = missionNamespace getVariable ["ACM_circulation_CPR_ControllerPFH", -1];
            if (_id >= 0) then {
                private _h = _handlers select _id;
                if (_h select 2) then {[_h select 1, _id] call (_h select 0);};
            };
        };
        private _key = {private _id = missionNamespace getVariable (_this select 0); private _entry = _keys select {_x select 0 == _id}; call ((_entry select 0) select 1);};
        private _start = {[_medic, _patient] call ACM_circulation_fnc_beginCPR;};
        private _enter = {CBA_missionTime = CBA_missionTime + 2; call _tick;};
        private _cancel = {["ACM_circulation_CPRCancel_MouseID"] call _key; call _tick;};
        private _freed = {
            [(_patient getVariable ["ACM_circulation_CPR_Medic", objNull]) isEqualTo objNull, "patient reserved"] call _check;
            [(_patient getVariable ["ace_medical_CPR_provider", objNull]) isEqualTo objNull, "ACE provider retained"] call _check;
            [!(_medic getVariable ["ACM_circulation_isPerformingCPR", false]), "provider restricted"] call _check;
            [!(_medic getVariable ["ACM_circulation_CPR_Loop", false]), "animation loop retained"] call _check;
            [ACM_circulation_CPR_LocalSession isEqualTo [] && {ACM_circulation_CPR_ControllerPFH == -1}, "controller retained"] call _check;
        };
    '''
    for name in ('cprSessionValid', 'cprRelease', 'cprCleanupLocal', 'registerCPRRuntime', 'beginCPR'):
        code += f'ACM_circulation_fnc_{name} = {{' + source(name) + '};\n'
    if runtime:
        code += '_isServer = true; call ACM_circulation_fnc_registerCPRRuntime;\n'
    code += scenario + '\ndiag_log (if (_ok) then {"CPR_FIX_OK"} else {"CPR_FIX_FAIL"});'
    result = subprocess.run([vm, '--automated', '--suppress-welcome', '--no-execute-print', '--no-work-print', '--sqf', code], capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and '[ERR]' not in output and '[FAT]' not in output, output
    assert 'CPR_FIX_OK' in output and 'CPR_FIX_FAIL' not in output, output


def test_direct_cpr_start_yields_same_patient_direct_pressure_without_destroying_episode():
    execute('''
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_PFH",77];
        _medic setVariable ["ACME_DP_KeyIDs",["dp-key"]];
        _medic setVariable ["ACME_DP_InPose",true];
        _medic setVariable ["ACME_DP_PoseToken",4];
        _medic setVariable ["ACME_dah_gen",9];

        call _start;

        [_medic getVariable ["ACME_DP_Active",false],"CPR destroyed Direct Pressure"] call _check;
        [(_medic getVariable ["ACME_DP_Patient",objNull]) isEqualTo _patient,"CPR changed DP target"] call _check;
        [(_medic getVariable ["ACME_DP_PFH",-1]) == 77,"CPR removed DP worker"] call _check;
        [(_medic getVariable ["ACME_DP_KeyIDs",[]]) isEqualTo ["dp-key"],"CPR removed DP inputs"] call _check;
        [_medic getVariable ["ACME_DP_Paused",false],"CPR did not pause DP"] call _check;
        [(_medic getVariable ["ACME_DP_PauseTreatmentClass",""]) == "cpr","CPR used wrong DP pause owner"] call _check;
        [!(_medic getVariable ["ACME_DP_InPose",true]),"CPR left DP pose active"] call _check;
        [(_medic getVariable ["ACME_dah_gen",0]) == 10,"CPR did not retire DP pose generation"] call _check;

        call _cancel; call _freed;
        [_medic getVariable ["ACME_DP_Active",false],"CPR cleanup destroyed DP episode"] call _check;
    ''')


def test_stop_with_string_ids_releases_patient_loop_and_requests_native_exit():
    execute('''
        call _start; call _enter;
        call _cancel; call _freed;
        [count _removedKeys == 4 && {count _removedAnims == 1}, "handlers not removed"] call _check;
        [(_moves select [count _moves - 2,2]) isEqualTo ["AinvPknlMstpSnonWnonDnon_medicEnd","AmovPknlMstpSnonWnonDnon"], "release and controllable idle missing"] call _check;
        [_stanceFreed, "stance lock retained"] call _check;
        ["CPR_ActionLog_Stopped" in _logs && {_reopens == 1}, "normal stop completion missing"] call _check;
    ''')


def test_start_cancel_and_start_again_with_existing_string_handlers():
    execute('''
        ACM_circulation_CPRCancel_EscapeID = "stale-escape";
        ACM_circulation_CPRCancel_MouseID = "stale-mouse";
        call _start; call _enter; call _cancel;
        call _start; call _enter; call _cancel; call _freed;
        [count _removedKeys == 10 && {count _removedAnims == 2}, "repeat cycle lost handlers"] call _check;
    ''')


def test_escape_during_entry_cannot_start_delayed_compressions():
    execute('''
        call _start;
        ["ACM_circulation_CPRCancel_EscapeID"] call _key; call _tick;
        call _enter; call _freed;
        [count _anims == 0 && {!("ACM_CPR" in _moves)}, "cancelled entry started compressions"] call _check;
    ''')


@pytest.mark.parametrize('airway', ['', 'SGA'])
def test_pause_disables_animdone_before_switch_then_resume_and_stop(airway):
    execute(f'_patient setVariable ["ACM_airway_AirwayItem_Oral", "{airway}"];'+'''
        call _start; call _enter;
        _fireAnimOnSwitch = true;
        ["ACM_circulation_CPRToggle_MouseID"] call _key; call _tick;
        [(_moves select (count _moves - 1)) == "ACM_CPR_Stop", "pause restarted CPR"] call _check;
        [[_medic, _patient] call ACM_circulation_fnc_cprSessionValid, "paused patient released"] call _check;
        _fireAnimOnSwitch = false;
        ["ACM_circulation_CPRToggle_MouseID"] call _key; call _tick;
        [count _anims == 1 && {_medic getVariable "ACM_circulation_CPR_Loop"}, "resume duplicated/lost loop"] call _check;
        call _cancel; call _freed;
    ''')


def test_delayed_animdone_and_input_cannot_restart_stopped_episode():
    execute('''
        call _start; call _enter;
        private _oldAnim = _anims select 0;
        private _oldToggle = (_keys select 2) select 1;
        call _cancel;
        private _count = count _moves;
        private _thisEventHandler = 0; private _thisEvent = "AnimDone";
        [_medic, "ACM_CPR"] call _oldAnim;
        call _oldToggle;
        call _freed;
        [count _moves == _count, "stopped callback restarted animation"] call _check;
    ''')


def test_old_cleanup_cannot_cancel_replacement_cpr():
    execute('''
        call _start; call _enter;
        private _oldEpoch = ACM_circulation_CPR_Epoch;
        call _cancel;
        call _start; call _enter;
        [_medic, _patient, _oldEpoch] call ACM_circulation_fnc_cprCleanupLocal;
        [[_medic, _patient] call ACM_circulation_fnc_cprSessionValid, "old cleanup cleared new reservation"] call _check;
        [_medic getVariable "ACM_circulation_CPR_Loop", "old cleanup stopped new loop"] call _check;
    ''')


def test_cpr_to_bvm_handoff_releases_cpr_first():
    execute('''
        _hasBVM = true;
        call _start; call _enter;
        ["ACM_circulation_CPRToggle_MouseID"] call _key; call _tick;
        ["ACM_circulation_CPRSwap_MouseID"] call _key; call _tick;
        call _freed;
        [_bvmHandoff == 1 && {_reopens == 0}, "BVM handoff failed"] call _check;
    ''')


def test_stop_keeps_another_providers_bvm_session():
    execute('''
        _patient setVariable ["ACM_breathing_BVM_Medic", missionNamespace];
        _patient setVariable ["ACM_breathing_BVM_provider", missionNamespace];
        _bvmActive = true;
        call _start; call _enter; call _cancel; call _freed;
        [(_patient getVariable "ACM_breathing_BVM_Medic") isEqualTo missionNamespace, "other BVM reservation released"] call _check;
        [(_patient getVariable "ACM_breathing_BVM_provider") isEqualTo missionNamespace, "other BVM ventilation stopped"] call _check;
    ''')


@pytest.mark.parametrize('airway', ['', 'SGA'])
def test_vent_provider_flap_does_not_reannounce_or_restart_cpr(airway):
    execute(f'''_patient setVariable ["ACM_airway_AirwayItem_Oral", "{airway}"];
        call _start; call _enter;
        private _continued0 = {{ _x == "CPR_Continued" }} count _texts;
        private _moveCount0 = count _moves;

        // ACME's ventilator deliberately registers/unregisters itself through ACM's BVM provider channel
        // as useful minute ventilation appears or disappears. CPR itself remains continuously active.
        _bvmActive = true; call _tick;
        _bvmActive = false; call _tick;
        _bvmActive = true; call _tick;
        _bvmActive = false; call _tick;

        [{{ _x == "CPR_Continued" }} count _texts == _continued0, "vent provider flap re-announced CPR"] call _check;
        [count _moves == _moveCount0, "vent provider flap restarted CPR animation"] call _check;
        call _cancel; call _freed;
    ''')


@pytest.mark.parametrize('ending', ['_alive = false;', '_awake = false;', '_local = false;', '_distance = 10;', '_medicVehicle = missionNamespace;'])
def test_interrupted_provider_is_released(ending):
    execute('call _start; call _enter; '+ending+' call _tick; call _freed;')


def test_respawn_cleans_old_session_without_animating_or_reopening_on_new_player():
    execute('''
        call _start; call _enter;
        private _count = count _moves;
        ACE_player = missionNamespace;
        [ACE_player, _medic] call _unitHandler;
        call _freed;
        [count _moves == _count && {_reopens == 0}, "respawn altered replacement player"] call _check;
    ''', runtime=True)


@pytest.mark.parametrize('ending', ['[_medic] call _disconnectHandler;', '_testOwner = 8;'])
def test_server_release_is_followed_by_local_animation_cleanup(ending):
    execute('call _start; call _enter; '+ending+'''
        [[], 0] call ((_handlers select 0) select 0);
        call _tick; call _freed;
        [count _removedAnims == 1, "server release stranded local loop"] call _check;
    ''', runtime=True)


def test_server_heartbeat_uses_receive_time_not_client_clock_value():
    execute('''
        call _start; call _enter;

        // Provider/client time is 22 while the dedicated-server clock is 1000.
        // First server observation records the current heartbeat token on the server clock.
        _serverClock = 1000;
        [[], 0] call ((_handlers select 0) select 0);
        [[_medic, _patient] call ACM_circulation_fnc_cprSessionValid, "clock offset invalidated CPR"] call _check;

        _serverClock = 1009.9;
        [[], 0] call ((_handlers select 0) select 0);
        [(_patient getVariable ["ACM_circulation_CPR_Medic", objNull]) isEqualTo _medic, "heartbeat expired early"] call _check;

        _serverClock = 1010;
        [[], 0] call ((_handlers select 0) select 0);
        call _tick; call _freed;
    ''', runtime=True)


def test_changed_client_heartbeat_resets_server_receive_age_even_with_clock_offset():
    execute('''
        call _start; call _enter;
        _serverClock = 1000;
        [[], 0] call ((_handlers select 0) select 0);

        CBA_missionTime = 24; call _tick;
        _serverClock = 1009.9;
        [[], 0] call ((_handlers select 0) select 0);

        _serverClock = 1019.8;
        [[], 0] call ((_handlers select 0) select 0);
        [(_patient getVariable ["ACM_circulation_CPR_Medic", objNull]) isEqualTo _medic, "new heartbeat did not refresh server receive age"] call _check;
    ''', runtime=True)


def test_server_tracks_only_latest_cpr_episode_for_each_provider():
    execute('''
        call _start;
        ["ACM_circulation_cprTrack", [_medic, profileNamespace, ACM_circulation_CPR_Epoch + 1]] call CBA_fnc_serverEvent;
        [count ACM_circulation_CPR_Sessions == 1, "duplicate server watchdog records for one provider"] call _check;
    ''', runtime=True)


def test_provider_sequence_survives_change_to_another_clients_counter():
    execute('''
        call _start; call _enter;
        private _oldEpoch = ACM_circulation_CPR_Epoch;
        call _cancel;
        ACM_circulation_CPR_Epoch = 0;
        call _start; call _enter;
        [ACM_circulation_CPR_Epoch > _oldEpoch, "new client reused old epoch"] call _check;
        [_medic, _patient, _oldEpoch] call ACM_circulation_fnc_cprRelease;
        [[_medic, _patient] call ACM_circulation_fnc_cprSessionValid, "old owner cleared new CPR"] call _check;
    ''')


def test_death_during_cpr_does_not_prevent_stop_or_restart():
    execute('''call _start; call _enter;
        _patientAlive = false; call _tick;
        call _cancel; call _freed;
        call _start; call _enter; call _cancel; call _freed;
    ''')
