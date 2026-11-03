params [["_medic", objNull], ["_patient", objNull], ["_part", ""], ["_cls", ""], "", ["_item", ""]];
if (isNull _patient || {!(_patient isKindOf "CAManBase")}) exitWith {};
private _c = [_cls, _part, _item] call ACME_fnc_batdokClassify;
if (_c isEqualTo []) exitWith {};
[_patient, "log", _c, _medic] remoteExecCall ["ACME_fnc_batdokOp", 2];
if (hasInterface && {_medic isEqualTo ACE_player} && {_patient isNotEqualTo _medic}) then {
	ACME_batdok_roster pushBackUnique _patient;
};
