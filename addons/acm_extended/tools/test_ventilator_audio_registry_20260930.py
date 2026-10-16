"""Execute the server audio registry with SQF-VM; simulate engine object/audio calls.

This checks actual runtime control flow. Positional audio and replication still
require an Arma multiplayer session.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


FUNCTION = Path(__file__).resolve().parents[1] / "functions" / "fn_registerVentilatorAudioRuntime.sqf"


def execute(scenario):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM is required for ventilator registry execution checks")
    # The unmodified server registration and PFH are executed; engine objects
    # are represented by namespaces and engine-only audio calls are recorded.
    source = FUNCTION.read_text().split("// ventilator alarm tones.", 1)[0]
    source = source.replace("isServer", "true").replace("allUnits", "[]").replace("allPlayers", "[]")
    source = re.sub(r"\bisNull (\w+)", r"(\1 isEqualTo objNull)", source)
    source = re.sub(r"\balive (\w+)", r'(\1 getVariable ["test_alive", true])', source)
    source = re.sub(r"\bdetach (\w+);", "", source)
    source = re.sub(r"\bdeleteVehicle (\w+);", r"_deleted pushBack \1;", source)
    source = source.replace('["_patient", objNull, [objNull]]', '["_patient", objNull]')
    source = source.replace(', true];', '];')
    source = source.replace('createSoundSource ["ACME_VentRun_SoundSource", getPosATL _pat, [], 0]', 'uiNamespace')
    source = source.replace('_src attachTo [_pat, [0,0,0]];', '')
    code = r'''
        private _ok = true;
        private _patient = profileNamespace;
        private _source = uiNamespace;
        private _deleted = [];
        private _published = [];
        private _handlers = [];
        private _track = {};
        CBA_missionTime = 10;
        CBA_fnc_addEventHandler = {_track = _this select 1;};
        CBA_fnc_addPerFrameHandler = {_handlers pushBack _this; count _handlers - 1};
        CBA_fnc_targetEvent = {};
        ACME_fnc_setVarNet = {
            params ["_object", "_key", "_value"];
            if ((_object getVariable [_key, -1]) isNotEqualTo _value) then {
                _published pushBack [_key, _value];
                _object setVariable [_key, _value];
            };
        };
        private _check = {
            if !(_this select 0) then {_ok = false; diag_log ("VENT_REGISTRY_FAIL " + (_this select 1));};
        };
    ''' + source + r'''
        private _tick = {[] call ((_handlers select 0) select 0);};
    ''' + scenario + r'''
        diag_log (if (_ok) then {"VENT_REGISTRY_OK"} else {"VENT_REGISTRY_FAIL"});
    '''
    result = subprocess.run(
        [vm, "--automated", "--suppress-welcome", "--no-execute-print", "--no-work-print", "--sqf", code],
        capture_output=True, text=True, timeout=15,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and "[ERR]" not in output and "[FAT]" not in output, output
    assert "VENT_REGISTRY_OK" in output and "VENT_REGISTRY_FAIL" not in output, output


@pytest.mark.parametrize("state", [0, 1, 2, 3])
@pytest.mark.parametrize("has_source", [False, True])
def test_death_retires_each_audio_phase_even_with_attached_configuration(state, has_source):
    execute(f'''
        _patient setVariable ["test_alive", false];
        _patient setVariable ["ACME_vent_onPatient", true];
        _patient setVariable ["ACME_vent_configured", true];
        _patient setVariable ["ACME_vent_sndState", {state}];
        _patient setVariable ["ACME_vent_sndLoopAt", 100];
        _patient setVariable ["ACME_vent_sndSrc", {"_source" if has_source else "objNull"}];
        ACME_vent_serverPatients = [_patient];
        ACME_vent_soundSources = {"[[_patient, _source]]" if has_source else "[]"};
        call _tick;
        [ACME_vent_serverPatients isEqualTo [], "dead casualty retained in hot registry"] call _check;
        [ACME_vent_soundSources isEqualTo [], "dead source retained"] call _check;
        [(_patient getVariable ["ACME_vent_sndState", -1]) == 0, "dead audio phase retained"] call _check;
        [(_patient getVariable ["ACME_vent_sndLoopAt", -1]) == 0, "dead startup timer retained"] call _check;
        [count _deleted == {int(has_source)}, "source deletion count incorrect"] call _check;
        private _sent = count _published;
        call _tick;
        [count _published == _sent, "dead casualty continued publishing"] call _check;
    ''')


def test_living_startup_and_configuration_remain_registered():
    execute('''
        _patient setVariable ["ACME_vent_onPatient", true];
        _patient setVariable ["ACME_vent_configured", true];
        _patient setVariable ["ACME_vent_driving", true];
        _patient setVariable ["ACME_vent_sndState", 1];
        _patient setVariable ["ACME_vent_sndLoopAt", 100];
        [_patient, true] call _track;
        call _tick;
        [ACME_vent_serverPatients isEqualTo [_patient], "living startup lost registry"] call _check;
        [(_patient getVariable "ACME_vent_sndState") == 1, "living startup cancelled"] call _check;
        [count _deleted == 0, "living source deleted"] call _check;
    ''')


def test_unconfigured_living_shutdown_is_kept_until_source_is_removed():
    execute('''
        _patient setVariable ["ACME_vent_sndState", 3];
        _patient setVariable ["ACME_vent_sndSrc", _source];
        _patient setVariable ["ACME_vent_sndLoopKillAt", 11];
        ACME_vent_soundSources = [[_patient, _source]];
        [_patient, false] call _track;
        call _tick;
        [ACME_vent_serverPatients isEqualTo [_patient], "shutdown retired before cleanup"] call _check;
        [count _deleted == 0, "shutdown overlap cut short"] call _check;
        CBA_missionTime = 12;
        call _tick;
        [ACME_vent_serverPatients isEqualTo [], "finished shutdown retained registry"] call _check;
        [count _deleted == 1, "shutdown source not removed"] call _check;
    ''')


def test_tracking_can_reenrol_a_new_living_patient_after_corpse_cleanup():
    execute('''
        _patient setVariable ["test_alive", false];
        _patient setVariable ["ACME_vent_configured", true];
        [_patient, true] call _track;
        call _tick;
        private _replacement = missionNamespace;
        _replacement setVariable ["test_alive", true];
        _replacement setVariable ["ACME_vent_configured", true];
        [_replacement, true] call _track;
        call _tick;
        [ACME_vent_serverPatients isEqualTo [_replacement], "new casualty failed to register"] call _check;
    ''')
