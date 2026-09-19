"""Execute multiplayer menu and hold lifetimes in SQF-VM.

Engine UI, animation and networking commands are mocked; actual session,
reservation, interpolation and cancellation code runs in the VM.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / 'addons/acm_extended/functions'


def read(name):
    return (F / f'fn_{name}.sqf').read_text()


def adapt(s, component='core'):
    s = re.sub(r'^#include.*$', '', s, flags=re.M)
    for macro, prefix, quote in [('QACEGVAR', 'ace', True), ('QEGVAR', 'ACM', True), ('EGVAR', 'ACM', False), ('ACEGVAR', 'ace', False)]:
        s = re.sub(r'\b' + macro + r'\((\w+),\s*(\w+)\)', lambda m: ('"' if quote else '') + f'{prefix}_{m[1]}_{m[2]}' + ('"' if quote else ''), s)
    for macro, suffix, quote in [('QGVAR', '', True), ('GVAR', '', False), ('FUNC', 'fnc_', False)]:
        s = re.sub(r'\b' + macro + r'\((\w+)\)', lambda m: ('"' if quote else '') + f'ACM_{component}_{suffix}{m[1]}' + ('"' if quote else ''), s)
    for macro, prefix in [('ACEFUNC', 'ace'), ('EFUNC', 'ACM')]:
        s = re.sub(r'\b' + macro + r'\((\w+),\s*(\w+)\)', lambda m: f'{prefix}_{m[1]}_fnc_{m[2]}', s)
    s = re.sub(r'\b(?:LLSTRING|LSTRING|ACELLSTRING)\([^)]*\)', '"text"', s)
    for old, new in {
        'IS_UNCONSCIOUS(_medic)': '_unconscious',
        'alive _medic': '_alive', 'alive _m': '_alive',
        'alive _patient': '_patientAlive', 'alive _target': '_patientAlive', 'alive _custodyTarget': '_patientAlive', 'alive _provider': '_alive', 'alive _p': '_patientAlive',
        'local _medic': 'true', 'local _m': 'true', 'local _patient': 'true', 'local _p': 'true',
        'owner _medic': '_ownerNum',
        'objectParent _medic': 'objNull', 'objectParent _patient': 'objNull', 'objectParent _p': 'objNull',
        '_patient distance2D _medic': '_distance', '_medic distance _patient': '_distance',
        'stance _medic': '"CROUCH"', 'stance _patient': '"PRONE"', 'stance _p': '"PRONE"',
        'animationState _patient': '"unconscious"', 'lifeState _p': '"DEAD"',
        'currentWeapon _medic': '""',
        'closeDialog 0;': '_dialog = false;', 'hasInterface': 'true', 'isServer': 'true',
        'findDisplay 46': 'objNull', 'displayNull': 'objNull', 'controlNull': 'objNull',
        'netId _patient': '"casualty"', 'clientOwner': '7',
        'toLowerANSI': 'toLower', 'diag_tickTime': '_nowTime', 'vest _p': '""',
        'addMissionEventHandler ["HandleDisconnect",': '_disconnect = (["HandleDisconnect",',
    }.items():
        s = re.sub(re.escape(old) + (r'\b' if old[-1].isalnum() else ''), lambda _: new, s)
    s = s.replace('objNull, [objNull]', 'objNull, [profileNamespace]')
    s = s.replace('ACME_CS_sessions getOrDefault', 'ACME_CS_sessions getVariable')
    s = s.replace('ACME_CS_sessions set ', 'ACME_CS_sessions setVariable ')
    s = re.sub(r'\bisNull (\(uiNamespace getVariable \[[^\n]*?\]\))', r'(\1 isEqualTo objNull)', s)
    s = re.sub(r'\bisNull (_\w+)', r'(\1 isEqualTo objNull)', s)
    s = re.sub(r'(setVariable \[[^;\n]*,[^;\n]*), (?:true|false)(\])', r'\1\2', s)
    s = re.sub(r'"ACM_[^"]+" cut(?:Rsc|Text) \[[^;]*;', '', s)
    s = re.sub(r'private (_ctrl\w+) = _display displayCtrl \w+;', r'private \1 = objNull;', s)
    s = re.sub(r'_ctrl\w+ ctrlSetText [^;]*;', '', s)
    s = s.replace('_medic setUnitPos "AUTO";', '_stanceFreed = true;')
    s = re.sub(r'\bdialog\b', '_dialog', s)
    s = s.replace('    false\n}];', '    false\n}] select 1);')
    return s


PREAMBLE = r'''
private _ok = true;
private _medic = uiNamespace;
private _patient = profileNamespace;
private _alive = true;
private _patientAlive = true;
private _unconscious = false;
private _ownerNum = 7;
private _distance = 1;
private _dialog = false;
private _stanceFreed = false;
private _moves = [];
private _removed = [];
private _keys = [];
private _handlers = [];
private _waits = [];
private _events = [];
private _disconnect = {};
private _track = {};
private _nowTime = 10;
CBA_missionTime = 10;
ACE_player = _medic;
ace_medical_gui_maxDistance = 3;
ACM_core_ContinuousAction_Active = false;
private _check = {if !(_this select 0) then {_ok = false; diag_log ("MENU_FIX_FAIL " + (_this select 1));};};
CBA_fnc_addKeyHandler = {private _id = format ["key%1",count _keys]; _keys pushBack [_id,_this select 2]; _id};
CBA_fnc_removeKeyHandler = {_removed pushBack (_this select 0);};
CBA_fnc_addPerFrameHandler = {_handlers pushBack [_this select 0,_this select 2,true]; count _handlers - 1};
CBA_fnc_removePerFrameHandler = {(_handlers select (_this select 0)) set [2,false];};
CBA_fnc_waitAndExecute = {_waits pushBack [_this select 0,_this select 1];};
CBA_fnc_waitUntilAndExecute = {_waits pushBack [_this select 1,_this select 2,_this select 0,_this select 4];};
CBA_fnc_addEventHandler = {_track = _this select 1;};
CBA_fnc_serverEvent = {_events pushBack _this; (_this select 1) call _track;};
CBA_fnc_targetEvent = {_events pushBack _this;};
CBA_fnc_localEvent = {};
CBA_fnc_globalEvent = {};
ace_common_fnc_doAnimation = {_moves pushBack (_this select 1);};
ace_common_fnc_displayTextStructured = {};
ace_common_fnc_getName = {"Provider"};
ace_common_fnc_isBeingDragged = {false};
ace_common_fnc_isBeingCarried = {false};
ace_medical_treatment_fnc_addToLog = {};
ace_interaction_fnc_showMouseHint = {};
ACME_fnc_chestSealGenHoles = {};
ACME_fnc_chestSealActualSide = {_actualSide};
ACME_fnc_chestSealRoll = {};
ACME_fnc_ownerDispatch = {_events pushBack _this;};
ACME_fnc_procedureAllowed = {true};
ACME_fnc_ecgJostleRequest = {};
private _tick = {private _id = ACM_core_ContinuousAction_PFH; if (_id < 0) exitWith {}; private _h = _handlers select _id; if (_h select 2) then {[_h select 1,_id] call (_h select 0);};};
'''


def execute(code):
    vm = os.environ.get('SQFVM') or shutil.which('sqfvm')
    if not vm:
        pytest.skip('SQF-VM required')
    result = subprocess.run([vm, '--automated', '--suppress-welcome', '--no-execute-print', '--no-work-print', '--sqf', PREAMBLE + code + '\ndiag_log (if (_ok) then {"MENU_FIX_OK"} else {"MENU_FIX_FAIL"});'], capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and '[ERR]' not in output and '[FAT]' not in output, output
    assert 'MENU_FIX_OK' in output and 'MENU_FIX_FAIL' not in output, output


def core(name):
    return adapt((ROOT / 'addons/core/functions' / f'fnc_{name}.sqf').read_text())


def test_three_chest_viewers_join_and_leave_independently():
    execute('private _session = {' + adapt(read('chestSealSession')) + '};' + '''
        ACME_CS_sessions = missionNamespace;
        {[_patient,_x select 0,"join",_x select 1] call _session;} forEach [["one","a"],["two","b"],["three","c"]];
        [count ((ACME_CS_sessions getVariable "casualty") select 1) == 3,"third viewer lost"] call _check;
        [_patient,"two","leave","b"] call _session;
        [(((ACME_CS_sessions getVariable "casualty") select 1) apply {_x select 0}) isEqualTo ["one","three"],"another viewer removed"] call _check;
        [_patient,"two","join","new"] call _session;
        [_patient,"two","leave","b"] call _session;
        [count ((ACME_CS_sessions getVariable "casualty") select 1) == 3,"old leave removed replacement"] call _check;
    ''')


def test_duplicate_open_attempts_share_one_pending_request():
    # Native panel creation is held until the async readiness callback runs.
    execute('private _open = {' + adapt(read('chestSealOpen')) + '};' + '''
        [_medic,_patient,"body"] call _open;
        private _token = uiNamespace getVariable "ACME_CS_SessionToken";
        [_medic,_patient,"body"] call _open;
        [count _waits == 1,"duplicate open queued"] call _check;
        [(uiNamespace getVariable "ACME_CS_SessionToken") == _token,"pending token overwritten"] call _check;
        uiNamespace setVariable ["ACME_CS_SessionToken","replacement"];
        private _w = _waits select 0;
        (_w select 1) call (_w select 0);
        [count _waits == 1,"old callback opened replacement"] call _check;
    ''')


@pytest.mark.parametrize('elapsed', [0, .016, .1])
def test_drag_retains_resistance_with_duplicate_timestamp(elapsed):
    s = read('chestSealTick')
    s = s[s.index('private _now = diag_tickTime;'):s.index('_py = _py + (_lagY * _f);') + len('_py = _py + (_lagY * _f);')]
    execute('''
        private _mx = 1; private _my = 1; private _bh = 1;
        private _isFiniteNumber = {(_this select 0) isEqualType 0};
        private _resetDragFrame = {};
        uiNamespace setVariable ["ACME_CS_DragLast",10];
        uiNamespace setVariable ["ACME_CS_DragPt",[0,0]];
    ''' + f'_nowTime = 10 + {elapsed};' + adapt(s) + '''
        [_px < 0.3 && {_py < 0.3},"resistance bypassed"] call _check;
    ''' + ('[_px == 0 && {_py == 0},"zero-time update moved finger"] call _check;' if elapsed == 0 else '[_px > 0,"finger failed to move"] call _check;'))


def test_last_viewer_restore_cannot_clear_reopened_workspace():
    execute('private _begin = {' + adapt(read('chestSealPatientBegin')) + '}; private _end = {' + adapt(read('chestSealPatientEnd')) + '};' + '''
        _patient setVariable ["ACME_CS_ProcedureActive",true];
        _patient setVariable ["ACME_CS_PreProcedureState",["front",false,false,false,""]];
        _patient setVariable ["ACME_CS_ProcedureGeneration",1];
        _patient setVariable ["ACME_CS_ProcedureTokens",["first","second","third"]];
        [_patient,"second"] call _end;
        [(_patient getVariable "ACME_CS_ProcedureTokens") isEqualTo ["first","third"],"other viewers released"] call _check;
        [_patient,"third"] call _end;
        _patient setVariable ["ACME_CS_rollUntil",12];
        [_patient,"first"] call _end;
        [count _waits == 1,"last viewer did not schedule restore"] call _check;
        [_patient,"new"] call _begin;
        private _w = _waits select 0;
        (_w select 1) call (_w select 0);
        [_patient getVariable "ACME_CS_ProcedureActive","old restore ended new workspace"] call _check;
        [(_patient getVariable "ACME_CS_PreProcedureState") isEqualTo ["front",false,false,false,""],"new viewer lost original restore state"] call _check;
    ''')


def test_final_corpse_viewer_restores_workspace_without_rolling_body():
    execute('private _end = {' + adapt(read('chestSealPatientEnd')) + '};' + '''
        private _actualSide = "front";
        _patientAlive = false;
        _patient setVariable ["ACME_CS_ProcedureActive",true];
        _patient setVariable ["ACME_CS_ProcedureGeneration",1];
        _patient setVariable ["ACME_CS_ProcedureTokens",["last"]];
        [_patient,"last"] call _end;
        [!(_patient getVariable "ACME_CS_ProcedureActive"),"corpse workspace stranded"] call _check;
        [count _waits == 0,"corpse rolled"] call _check;
    ''')


def hold_setup(runtime=False):
    s = 'ACM_core_fnc_continuousHoldRelease = {' + core('continuousHoldRelease') + '};\n'
    if runtime:
        s += core('registerContinuousRuntime')
    s += 'ACM_core_fnc_beginContinuousAction = {' + core('beginContinuousAction') + '};\n'
    s += 'private _start = {' + adapt((ROOT / 'addons/airway/functions/fnc_beginHeadTiltChinLift.sqf').read_text(), 'airway') + '};\n'
    return s


@pytest.mark.parametrize('ending', ['ACM_core_ContinuousAction_Active = false;', '_alive = false;', '_unconscious = true;', 'ACE_player = missionNamespace;'])
def test_head_tilt_cancels_with_string_handlers_on_stop_death_and_respawn(ending):
    execute(hold_setup() + '''
        [_medic,_patient] call _start;
        [_patient getVariable "ACM_airway_HeadTilt_State","head tilt did not start"] call _check;
    ''' + ending + '''
        call _tick;
        [!ACM_core_ContinuousAction_Active,"global gate stranded"] call _check;
        [!(_patient getVariable "ACM_airway_HeadTilt_State"),"patient hold stranded"] call _check;
        [count _removed == 2,"string key cleanup failed"] call _check;
    ''')


def test_patient_death_keeps_head_tilt_usable_and_releasable():
    execute(hold_setup() + '''
        [_medic,_patient] call _start;
        _patientAlive = false; call _tick;
        [ACM_core_ContinuousAction_Active,"patient death broke manual hold"] call _check;
        ACM_core_ContinuousAction_Active = false; call _tick;
        [!(_patient getVariable "ACM_airway_HeadTilt_State") && {_stanceFreed},"corpse release failed"] call _check;
        [_medic,_patient] call _start;
        [ACM_core_ContinuousAction_Active,"could not restart on corpse"] call _check;
    ''')


@pytest.mark.parametrize('ending', ['_alive = false;', '_ownerNum = 9;', 'CBA_missionTime = 30;', '[_medic] call _disconnect;'])
def test_abandoned_head_tilt_is_released_by_server(ending):
    execute(hold_setup(True) + '''
        [_medic,_patient] call _start;
        [[],0] call ((_handlers select 0) select 0);
        CBA_missionTime = 14;
    ''' + ending + '''
        private _watchdog = _handlers select 0;
        [[],0] call (_watchdog select 0);
        [!(_patient getVariable "ACM_airway_HeadTilt_State"),"server retained abandoned hold"] call _check;
        call _tick; call _tick;
        [!ACM_core_ContinuousAction_Active,"client did not observe server release"] call _check;
    ''')


def test_old_hold_cleanup_preserves_replacement_and_recovery_position():
    execute('ACM_core_fnc_continuousHoldRelease = {' + core('continuousHoldRelease') + '};' + '''
        _patient setVariable ["ACM_airway_HeadTilt_State",true];
        _patient setVariable ["ACM_airway_HeadTilt_State_Session",[_medic,2]];
        [_medic,_patient,1,"ACM_airway_HeadTilt_State"] call ACM_core_fnc_continuousHoldRelease;
        [_patient getVariable "ACM_airway_HeadTilt_State","old cleanup cleared new hold"] call _check;
        _patient setVariable ["ACM_airway_RecoveryPosition_State",true];
        [_medic,_patient,2,"ACM_airway_HeadTilt_State"] call ACM_core_fnc_continuousHoldRelease;
        [_patient getVariable "ACM_airway_HeadTilt_State","recovery head tilt erased"] call _check;
        [(_patient getVariable "ACM_airway_HeadTilt_State_Session") isEqualTo [],"manual reservation retained"] call _check;
    ''')


@pytest.mark.parametrize('dead', [False, True])
def test_connected_vent_panel_opens_on_alive_or_dead_patient(dead):
    execute('private _open = {' + adapt(read('ventPanelOpen')) + '};' + f'_patientAlive = {str(not dead).lower()};' + '''
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_custodyId","device-1"];
        _patient setVariable ["ACME_vent_configured",true];
        _patient setVariable ["ACME_vent_powerOn",true];
        _patient setVariable ["ACME_vent_hasBooted",true];
        [_patient] call _open;
        [count _waits == 1,"device view rejected"] call _check;
        [(uiNamespace getVariable "ACME_vent_target") isEqualTo _patient,"panel rebound to provider"] call _check;
        [!(uiNamespace getVariable "ACME_vent_presetMode"),"corpse changed panel to presets"] call _check;
        [!(_patient getVariable ["ACME_vent_recovering",false]),"view changed custody"] call _check;
        [_patient] call _open;
        [count _waits == 1,"duplicate vent open queued"] call _check;
    ''')


def test_vent_recovery_gate_requires_an_actual_recovery():
    execute('private _open = {' + adapt(read('ventPanelOpen')) + '};' + '''
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_recovering",true];
        [_patient] call _open;
        [count _waits == 0,"actual recovery ignored"] call _check;
    ''')


@pytest.mark.parametrize('name,key', [('chestSealClose','ACME_CS_DLG'), ('ventPanelClose','ACME_vent_dlg')])
def test_late_panel_unload_cannot_clear_current_panel(name, key):
    execute('private _close = {' + adapt(read(name)) + '};' + f'''
        uiNamespace setVariable ["{key}",missionNamespace];
        uiNamespace setVariable ["ACME_CS_SessionToken","new-token"];
        uiNamespace setVariable ["ACME_vent_openSerial",8];
        [profileNamespace] call _close;
        [(uiNamespace getVariable "{key}") isEqualTo missionNamespace,"new panel closed"] call _check;
        [(uiNamespace getVariable "ACME_CS_SessionToken") == "new-token","new workspace released"] call _check;
        [(uiNamespace getVariable "ACME_vent_openSerial") == 8,"new open cancelled"] call _check;
    ''')


@pytest.mark.parametrize('name,boundary', [('ventPanelTick','// Refresh a visible panel'), ('ventPanelNavClick','playSound "ACME_VentClick";')])
def test_dead_patient_stays_accessible_after_panel_is_open(name, boundary):
    s = read(name).split(boundary)[0]
    execute('''
        ACME_fnc_ventFlipKeyHint = {};
        private _allowed = false;
        missionNamespace setVariable ["ACME_vent_viewer",_medic];
        uiNamespace setVariable ["ACME_vent_dlg",missionNamespace];
        uiNamespace setVariable ["ACME_vent_target",_patient];
        uiNamespace setVariable ["ACME_vent_powered",true];
        _patient setVariable ["ACME_vent_onPatient",true];
        _patientAlive = false;
    ''' + 'private _gate = {' + adapt(s) + '_allowed = true;}; ["home"] call _gate;' + '''
        [_allowed,"death closed or disabled device panel"] call _check;
    ''')


def test_heartbeat_expiry_uses_server_receive_time():
    execute(hold_setup(True) + '''
        [_medic,_patient] call _start;
        _medic setVariable ["ACM_core_ContinuousAction_LastSeen",-500];
        [[],0] call ((_handlers select 0) select 0);
        CBA_missionTime = 14;
        [[],0] call ((_handlers select 0) select 0);
        [_patient getVariable "ACM_airway_HeadTilt_State","client clock offset expired active hold"] call _check;
    ''')


def test_repeated_pulse_start_removes_string_escape_handler():
    s = (ROOT / 'addons/circulation/functions/fnc_feelPulse.sqf').read_text().split('private _oldMain')[0]
    execute('private _start = {' + adapt(s) + '};' + '''
        uiNamespace setVariable ["ACME_PulseEscKey","old-pulse-key"];
        [_medic,_patient,"head"] call _start;
        ["old-pulse-key" in _removed,"pulse startup aborted on string id"] call _check;
    ''')


def test_stethoscope_start_removes_previous_continuous_action_string_handlers():
    s = read('beginStethoscopeAction').split('if (dialog)')[0]
    execute('private _start = {' + adapt(s) + '};' + '''
        ACM_core_ContinuousAction_OpenMedicalMenu_ID = "old-open-key";
        ACM_core_ContinuousAction_Cancel_EscapeID = "old-escape-key";
        [[_medic,_patient,"head"],{},{},{}] call _start;
        [_removed isEqualTo ["old-open-key","old-escape-key"],"scope startup aborted on string id"] call _check;
    ''')


def test_carry_assist_releases_after_provider_death():
    execute('ACM_core_fnc_continuousHoldRelease = {' + core('continuousHoldRelease') + '}; ACM_core_fnc_beginContinuousAction = {' + core('beginContinuousAction') + '}; private _start = {' + core('beginCarryAssist') + '};' + '''
        [_medic,_patient] call _start;
        [_patient getVariable "ACM_core_CarryAssist_State","carry assist failed to start"] call _check;
        _alive = false; call _tick;
        [!(_patient getVariable "ACM_core_CarryAssist_State"),"carry assist stranded after provider death"] call _check;
        [!ACM_core_ContinuousAction_Active && {count _removed == 2},"carry assist cleanup aborted"] call _check;
    ''')
