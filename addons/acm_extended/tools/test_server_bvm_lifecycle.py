"""Execute BVM session and cleanup code with native UI/network operations simulated."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / 'addons/breathing/functions'


def source(name):
    s = (F / f'fnc_{name}.sqf').read_text()
    s = re.sub(r'^#include.*$', '', s, flags=re.M)
    for macro, prefix, quote in [('QEGVAR', 'ACM', True), ('EGVAR', 'ACM', False), ('ACEGVAR', 'ace', False)]:
        s = re.sub(r'\b' + macro + r'\((\w+),\s*(\w+)\)', lambda m: ('"' if quote else '') + f'{prefix}_{m[1]}_{m[2]}' + ('"' if quote else ''), s)
    for macro, prefix, quote in [('QGVAR', 'ACM_breathing_', True), ('GVAR', 'ACM_breathing_', False), ('FUNC', 'ACM_breathing_fnc_', False)]:
        s = re.sub(r'\b' + macro + r'\((\w+)\)', lambda m: ('"' if quote else '') + prefix + m[1] + ('"' if quote else ''), s)
    s = re.sub(r'\bACEFUNC\((\w+),\s*(\w+)\)', lambda m: f'ace_{m[1]}_fnc_{m[2]}', s)
    for a, b in {
        'isNull _medic': '(_medic isEqualTo objNull)',
        'isNull _patient': '(_patient isEqualTo objNull)',
        'isNull _unit': '(_unit isEqualTo objNull)',
        'alive _medic': '_alive',
        'owner _medic': '_testOwner',
        'objectParent _medic': '_medicVehicle',
        'objectParent _patient': '_patientVehicle',
        '_medic distance2D _patient': '_distance',
        ', true];': '];',
        '"ACM_UseBVM" cutText ["", "PLAIN", 0, false];': '_cuts = _cuts + 1;',
        'hasInterface': '_hasInterface',
        'isServer': '_isServer',
        'addMissionEventHandler ["HandleDisconnect",': '_disconnectHandler = (["HandleDisconnect",',
    }.items():
        s = s.replace(a, b)
    if name == 'registerBVMRuntime':
        s = s.replace('        false\n    }];', '        false\n    }] select 1);')
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
        private _testOwner = 7;
        private _medicVehicle = objNull;
        private _patientVehicle = objNull;
        private _distance = 1;
        private _cuts = 0;
        private _hints = 0;
        private _removedKeys = [];
        private _removedPFHs = [];
        private _handlers = [];
        private _unitHandler = {};
        private _disconnectHandler = {};
        private _trackHandler = {};
        private _hasInterface = true;
        private _isServer = true;
        CBA_missionTime = 20;
        ace_medical_gui_maxDistance = 3;
        ACM_core_ContinuousAction_Epoch = 4;
        ACM_core_ContinuousAction_Active = true;
        ACM_core_ContinuousAction_PFH = 12;
        ACM_core_ContinuousAction_Cancel_EscapeID = "escape-key";
        ACM_breathing_BVM_LocalSession = [_medic, _patient, 4];
        ACM_breathing_BVMTarget = _patient;
        ACM_breathing_BVMCancel_MouseID = "cancel-key";
        ACM_breathing_BVMToggle_MouseID = "toggle-key";
        ACM_breathing_BVMSwap_MouseID = "swap-key";
        _medic setVariable ["ACM_breathing_BVM_patient", _patient];
        _medic setVariable ["ACM_breathing_BVM_epoch", 4];
        _medic setVariable ["ACM_breathing_BVM_lastSeen", 20];
        _medic setVariable ["ACM_breathing_isUsingBVM", true];
        _patient setVariable ["ACM_breathing_BVM_Medic", _medic];
        _patient setVariable ["ACM_breathing_BVM_provider", _medic];
        _patient setVariable ["ACM_breathing_BVM_session", [_medic, 4]];
        _patient setVariable ["ACM_breathing_BVM_ConnectedOxygen", true];
        ace_common_fnc_isAwake = {_awake};
        ace_interaction_fnc_hideMouseHint = {_hints = _hints + 1;};
        CBA_fnc_removeKeyHandler = {_removedKeys pushBack (_this select 0);};
        CBA_fnc_removePerFrameHandler = {_removedPFHs pushBack (_this select 0);};
        CBA_fnc_addPerFrameHandler = {_handlers pushBack _this; count _handlers - 1};
        CBA_fnc_addEventHandler = {_trackHandler = _this select 1;};
        CBA_fnc_addPlayerEventHandler = {_unitHandler = _this select 1;};
        private _check = {if !(_this select 0) then {_ok = false; diag_log ("SERVER_FIX_FAIL " + (_this select 1));};};
    '''
    for name in ('bvmSessionValid', 'bvmRelease', 'bvmCleanupLocal', 'registerBVMRuntime'):
        code += f'ACM_breathing_fnc_{name} = {{' + source(name) + '};\n'
    if runtime:
        code += 'call ACM_breathing_fnc_registerBVMRuntime; [_medic, _patient, 4] call _trackHandler;\n'
    code += scenario + '\ndiag_log (if (_ok) then {"SERVER_FIX_OK"} else {"SERVER_FIX_FAIL"});'
    result = subprocess.run([vm, '--automated', '--suppress-welcome', '--no-execute-print', '--no-work-print', '--sqf', code], capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and '[ERR]' not in output and '[FAT]' not in output, output
    assert 'SERVER_FIX_OK' in output and 'SERVER_FIX_FAIL' not in output, output


def test_cleanup_accepts_string_ids_and_frees_patient_provider_and_controller():
    execute('''
        [_medic, _patient, 4] call ACM_breathing_fnc_bvmCleanupLocal;
        [(_patient getVariable "ACM_breathing_BVM_Medic") isEqualTo objNull, "patient reserved"] call _check;
        [!(_medic getVariable "ACM_breathing_isUsingBVM"), "provider restricted"] call _check;
        [!ACM_core_ContinuousAction_Active && {ACM_core_ContinuousAction_PFH == -1}, "controller stuck"] call _check;
        [count _removedKeys == 4 && {_cuts == 1}, "string handlers not removed"] call _check;
        [!(_patient getVariable "ACM_breathing_BVM_ConnectedOxygen"), "oxygen ownership retained"] call _check;
    ''')


def test_old_cleanup_cannot_release_new_bvm_episode():
    execute('''
        _patient setVariable ["ACM_breathing_BVM_session", [_medic, 5]];
        _medic setVariable ["ACM_breathing_BVM_epoch", 5];
        ACM_core_ContinuousAction_Epoch = 5;
        ACM_breathing_BVM_LocalSession = [_medic, _patient, 5];
        [_medic, _patient, 4] call ACM_breathing_fnc_bvmCleanupLocal;
        [(_patient getVariable "ACM_breathing_BVM_Medic") isEqualTo _medic, "replacement reservation cleared"] call _check;
        [ACM_core_ContinuousAction_Active && {count _removedKeys == 0} && {_hints == 0}, "replacement UI cleared"] call _check;
    ''')


def test_old_cleanup_leaves_new_non_bvm_controller_and_mouse_hint_alone():
    execute('''
        ACM_core_ContinuousAction_Epoch = 5;
        [_medic, _patient, 4] call ACM_breathing_fnc_bvmCleanupLocal;
        [ACM_core_ContinuousAction_Active && {_hints == 0} && {count _removedPFHs == 0}, "new controller affected"] call _check;
    ''')


def test_paused_session_remains_reserved_and_live():
    execute('''
        _patient setVariable ["ACM_breathing_BVM_provider", objNull];
        _medic setVariable ["ACM_breathing_isUsingBVM", false];
        [[_medic, _patient] call ACM_breathing_fnc_bvmSessionValid, "paused reservation lost"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['_testOwner = 8;', '_alive = false;', '_awake = false;', '_distance = 10;', 'CBA_missionTime = 31;', '_medicVehicle = uiNamespace;'])
def test_server_releases_invalid_session(invalid):
    execute('CBA_missionTime = 24; ' + invalid + '''
        [[], 0] call ((_handlers select 0) select 0);
        [(_patient getVariable "ACM_breathing_BVM_Medic") isEqualTo objNull, "server retained stale reservation"] call _check;
        [count ACM_breathing_BVM_Sessions == 0, "server retained stale session"] call _check;
    ''', runtime=True)


def test_disconnect_releases_patient_without_provider_callback():
    execute('''
        [_medic] call _disconnectHandler;
        [(_patient getVariable "ACM_breathing_BVM_Medic") isEqualTo objNull, "disconnect retained reservation"] call _check;
    ''', runtime=True)


def test_respawn_cleans_captured_old_provider_and_local_gate():
    execute('''
        [missionNamespace, _medic] call _unitHandler;
        [!ACM_core_ContinuousAction_Active && {ACM_breathing_BVMTarget isEqualTo objNull}, "respawn gate retained"] call _check;
        [(_patient getVariable "ACM_breathing_BVM_Medic") isEqualTo objNull, "respawn retained reservation"] call _check;
        [count _removedKeys == 4, "respawn handlers retained"] call _check;
    ''', runtime=True)


def test_server_waits_for_session_publication_then_reaps_timeout():
    execute('''
        _patient setVariable ["ACM_breathing_BVM_session", []];
        [[], 0] call ((_handlers select 0) select 0);
        [count ACM_breathing_BVM_Sessions == 1, "early track event lost"] call _check;
        _patient setVariable ["ACM_breathing_BVM_session", [_medic, 4]];
        CBA_missionTime = 31;
        [[], 0] call ((_handlers select 0) select 0);
        [(_patient getVariable "ACM_breathing_BVM_Medic") isEqualTo objNull, "late publication not monitored"] call _check;
    ''', runtime=True)


def test_startup_removal_accepts_existing_string_handlers():
    s = source('useBVM')
    block = s[s.index('    {\n        private _oldID'):s.index('    private _cancelCode')]
    execute(block + '\n[count _removedKeys == 3, "startup failed on string handler IDs"] call _check;')
