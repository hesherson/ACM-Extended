params ["_medic", "_patient", "_epoch", "_id", "_accepted", "_reason"];
if (!hasInterface || {isNull _medic} || {!local _medic} || {!(_medic isEqualTo ACE_player)}) exitWith {false};
private _pending = +(_medic getVariable ["DD1380_Pending", []]);
private _index = _pending find [_id, _patient, _epoch];
if (_index < 0) exitWith {false};
_pending deleteAt _index;
_medic setVariable ["DD1380_Pending", _pending];
if (!_accepted && {_reason != ""}) then {[_reason] call ace_common_fnc_displayTextStructured;};
true
