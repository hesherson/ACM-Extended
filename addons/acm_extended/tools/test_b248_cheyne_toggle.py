"""B248 toggle cleanup contracts."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "functions"

def test_cheyne_stokes_disable_releases_drive_without_forgetting_enrollment():
    s = (ROOT / "fn_cheyneStokesTick.sqf").read_text(encoding="utf-8-sig")
    disabled = s.split('if !(missionNamespace getVariable ["ACME_sys_cheyneStokes", true]) exitWith {', 1)[1].split('\n};', 1)[0]
    assert 'ACME_cs_activePatients' in disabled
    assert 'local _x' in disabled
    assert '[_x, "ACME_cs_rrDrive", -1] call ACME_fnc_setVarNet;' in disabled
    assert 'ACME_cs_activePatients =' not in disabled
    assert 'if ((_p getVariable ["ACME_cs_rrDrive", -1]) != _rr) then {' in s

def test_cheyne_stokes_audio_retires_when_system_disabled():
    s = (ROOT / "fn_breathSoundsStart.sqf").read_text(encoding="utf-8-sig")
    assert 'if (_mode == "cheyne" && {!(_u getVariable ["ACME_cs_active", false]) || {!(missionNamespace getVariable ["ACME_sys_cheyneStokes", true])}}) exitWith { call _kill };' in s
