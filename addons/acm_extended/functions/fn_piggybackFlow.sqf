/* Secondary gravity flow has priority even when its clamp is closed: the primary remains held. */
params ["_patient", "_part", "_iv", "_site", "_uid"];
private _line = [_patient, _part, _iv, _site] call ACME_fnc_piggybackLine;
if (_line isEqualTo []) exitWith {[false, false]};
private _secondary = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI _part, []];
private _i = _secondary findIf {(_x param [8, ""]) == (_line select 1)};
private _hasSecondary = _i >= 0 && {((_secondary select _i) param [1, 0]) > 0.01};
[(_line select 0) == _uid && {_hasSecondary}, (_line select 1) == _uid]
