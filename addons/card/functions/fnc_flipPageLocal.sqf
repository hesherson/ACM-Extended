/* Preserve the imported public event entry point; never close unrelated UI. */
params ["_medic", "_patient"];
if (!hasInterface || {!local _medic} || {!(_medic isEqualTo ACE_player)}) exitWith {false};
private _display = findDisplay 1380;
if (isNull _display) then {_display = findDisplay 13802;};
if (isNull _display) exitWith {false};
private _context = _display getVariable ["DD1380_context", []];
if (count _context != 7 || {!((_context select 1) isEqualTo _patient)}) exitWith {false};
[_display displayCtrl 2000] call DD1380_card_fnc_flipPage
