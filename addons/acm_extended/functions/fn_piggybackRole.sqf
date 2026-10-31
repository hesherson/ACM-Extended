params ["_patient", "_part", "_uid"];
if (isNull _patient || {_uid == ""}) exitWith {""};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI _part, []];
private _index = _bags findIf {(_x param [8, ""]) == _uid};
if (_index < 0) exitWith {""};
private _bag = _bags select _index;
private _line = [_patient, _part, _bag param [4, true], _bag param [3, -1]] call ACME_fnc_piggybackLine;
if (_line isEqualTo []) exitWith {""};
["Primary", "Secondary"] select ((_line select 1) == _uid)
