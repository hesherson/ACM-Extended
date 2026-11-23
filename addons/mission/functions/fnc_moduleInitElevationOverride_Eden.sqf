#include "..\script_component.hpp"
/*
 * Author: mavis
 * Correct ACE's map elevation datum from an Eden module.
 *
 * Calibration mode preserves the terrain's relative elevation. The module is
 * placed at a point with a known real-world elevation and calculates the ACE
 * base offset required to make that point correct.
 *
 * Manual mode directly replaces ace_common_mapAltitude.
 *
 * Arguments:
 * 0: The module logic <OBJECT>
 * 1: Synchronized objects <ARRAY> (unused)
 * 2: Activated <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [LOGIC, [], true] call ACM_mission_fnc_moduleInitElevationOverride_Eden;
 *
 * Public: No
 */

params ["_logic", "_syncedObjects", "_activated"];

if (!_activated || {isNull _logic}) exitWith {};

private _fnc_number = {
    params ["_value", ["_fallback", 0]];

    if (_value isEqualType 0) exitWith {_value};
    if (_value isEqualType "") exitWith {parseNumber _value};

    _fallback;
};

private _mode = [(_logic getVariable ["Mode", 0]), 0] call _fnc_number;
private _units = [(_logic getVariable ["ElevationUnits", 1]), 1] call _fnc_number;
private _requestedElevation = [(_logic getVariable ["DesiredElevation", 0]), 0] call _fnc_number;
private _showStartupReport = _logic getVariable ["ShowStartupReport", true];

// Eden uses the selected unit only for the user-entered value. Internally ACE is meters.
if (_units == 1) then {
    _requestedElevation = _requestedElevation * 0.3048;
};

private _configuredBase = getNumber (configFile >> "CfgWorlds" >> worldName >> "elevationOffset");
private _aceBaseBefore = missionNamespace getVariable ["ace_common_mapAltitude", _configuredBase];

private _worldPosition = getPosWorld _logic;
private _terrainASL = getTerrainHeightASL [_worldPosition select 0, _worldPosition select 1];

private _correctedBase = if (_mode == 1) then {
    // Manual mode: the entered value is the desired ACE map datum itself.
    _requestedElevation
} else {
    // Calibration mode: actual altitude = ACE base datum + raw terrain ASL.
    // Solve for the base datum using the known elevation at the module.
    _requestedElevation - _terrainASL
};

private _oldEffectiveElevation = _aceBaseBefore + _terrainASL;
private _newEffectiveElevation = _correctedBase + _terrainASL;

// Module functions are global, so every machine applies the same local ACE value.
// Apply immediately and again just after mission initialization so ACE post-init/map
// data resolution cannot overwrite the Eden correction because of init ordering.
missionNamespace setVariable ["ace_common_mapAltitude", _correctedBase];

[{
    params ["_base"];
    missionNamespace setVariable ["ace_common_mapAltitude", _base];
}, [_correctedBase], 0.5] call CBA_fnc_waitAndExecute;

[{
    params ["_base"];
    missionNamespace setVariable ["ace_common_mapAltitude", _base];
}, [_correctedBase], 2] call CBA_fnc_waitAndExecute;

// Publish ACME's resolved state from the server for diagnostics/JIP consumers.
if (isServer) then {
    missionNamespace setVariable ["ACME_ElevationOverride_Active", true, true];
    missionNamespace setVariable ["ACME_ElevationOverride_Base", _correctedBase, true];
    missionNamespace setVariable ["ACME_ElevationOverride_OriginalACEBase", _aceBaseBefore, true];
    missionNamespace setVariable ["ACME_ElevationOverride_TerrainASLAtModule", _terrainASL, true];
};

private _modeName = if (_mode == 1) then {"manual base"} else {"module calibration"};
private _mToFt = 3.280839895;

private _configuredBaseFt = round (_configuredBase * _mToFt);
private _aceBaseBeforeFt = round (_aceBaseBefore * _mToFt);
private _correctedBaseFt = round (_correctedBase * _mToFt);
private _terrainASLFt = round (_terrainASL * _mToFt);
private _oldEffectiveFt = round (_oldEffectiveElevation * _mToFt);
private _newEffectiveFt = round (_newEffectiveElevation * _mToFt);

if (!isNil "ACME_fnc_debugEnabled" && {call ACME_fnc_debugEnabled}) then {diag_log format [
    "[ACME][Elevation] World=%1 | mode=%2 | CfgWorlds base=%3m (%4ft) | ACE base before=%5m (%6ft) | raw terrain at module=%7m (%8ft) | corrected ACE base=%9m (%10ft) | effective at module: %11m/%12ft -> %13m/%14ft",
    worldName,
    _modeName,
    round _configuredBase,
    _configuredBaseFt,
    round _aceBaseBefore,
    _aceBaseBeforeFt,
    round _terrainASL,
    _terrainASLFt,
    round _correctedBase,
    _correctedBaseFt,
    round _oldEffectiveElevation,
    _oldEffectiveFt,
    round _newEffectiveElevation,
    _newEffectiveFt
];};

if (_showStartupReport && {hasInterface}) then {
    systemChat format ["[ACME Elevation] Map: %1 | ACE base: %2 m / %3 ft", worldName, round _aceBaseBefore, _aceBaseBeforeFt];
    systemChat format ["[ACME Elevation] Corrected base: %1 m / %2 ft", round _correctedBase, _correctedBaseFt];
    systemChat format ["[ACME Elevation] Effective elevation here: %1 m / %2 ft", round _newEffectiveElevation, _newEffectiveFt];
};
