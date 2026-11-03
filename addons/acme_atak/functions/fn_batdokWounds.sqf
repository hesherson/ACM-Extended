params [["_u", objNull]];
if (isNull _u) exitWith {[]};
private _slots = createHashMapFromArray [
	["head", [[49, 9], [45, 12], [53, 12], [49, 15]]],
	["body", [[49, 27], [43, 33], [55, 33], [49, 40], [43, 47], [55, 47], [49, 53]]],
	["leftarm", [[66, 31], [68, 39], [71, 47], [75, 55]]],
	["rightarm", [[32, 31], [30, 39], [27, 47], [24, 55]]],
	["leftleg", [[55, 64], [56, 72], [55, 80], [54, 90]]],
	["rightleg", [[44, 64], [43, 72], [44, 80], [45, 90]]]
];
private _names = missionNamespace getVariable ["ace_medical_damage_woundClassNames", []];
private _kind = {
	params ["_id"];
	private _n = toLowerANSI (_names param [floor (_id / 10), ""]);
	switch (true) do {
		case ("velocity" in _n): {["gsw", "GSW"]};
		case ("burn" in _n || {"thermal" in _n}): {["burn", "Burn"]};
		case ("abrasion" in _n || {"contusion" in _n} || {"crush" in _n}): {["blunt", "Blunt"]};
		case (_n isEqualTo ""): {["gsw", "Wound"]};
		default {["penetrating", "Penetrating"]};
	}
};
private _out = [];
private _used = createHashMap;
private _put = {
	params ["_part", "_type", "_label"];
	private _s = _slots getOrDefault [_part, []];
	if (_s isEqualTo []) exitWith {};
	private _n = _used getOrDefault [_part, 0];
	_used set [_part, _n + 1];
	(_s select (_n mod count _s)) params ["_x", "_y"];
	private _r = floor (_n / count _s);
	_out pushBack [format ["w%1%2", _part, _n], _x + _r * 2.5, _y + _r * 1.5, "front", _type, _label];
};
{
	_x params ["_var", "_suffix"];
	private _w = _u getVariable [_var, createHashMap];
	if (_w isEqualType createHashMap) then {
		{
			private _part = _x;
			{
				_x params [["_id", 0], ["_amount", 0]];
				if (_amount > 0) then {
					([_id] call _kind) params ["_type", "_label"];
					[_part, _type, _label + _suffix] call _put;
				};
			} forEach _y;
		} forEach _w;
	};
} forEach [["ace_medical_openWounds", ""], ["ace_medical_bandagedWounds", ""]];
private _fr = _u getVariable ["ace_medical_fractures", []];
{
	if (_x != 0) then {
		[["head", "body", "leftarm", "rightarm", "leftleg", "rightleg"] select _forEachIndex, "fracture", "Fracture"] call _put;
	};
} forEach _fr;
_out
