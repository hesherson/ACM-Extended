params [["_u", objNull]];
if (isNull _u) exitWith {""};
private _rec = _u getVariable ["acme_batdok_rec", []];
if (_rec isEqualTo []) exitWith {""};
_rec params ["", "_info", "_inj", "_man", "_sen", "_xfer"];
_info params ["_name", "_cs", "_age", "_sex", "_tri", "_dob", "_h", "_w", "_meds", "_all", "_hist", "_evac"];
private _nl = toString [13, 10];
private _hhmm = {
	params ["_t"];
	private _h = _t select 3;
	private _m = _t select 4;
	(["", "0"] select (_h < 10)) + str _h + (["", "0"] select (_m < 10)) + str _m
};
private _lines = [
	"BATDOK PATIENT RECORD",
	format ["Patient: %1 (%2)", _name, _cs],
	format ["Age: %1  Sex: %2  Triage: %3  Evac: %4", [_age, "--"] select (_age isEqualTo ""), _sex, _tri, _evac]
];
if (_dob isNotEqualTo "") then { _lines pushBack format ["DOB: %1", _dob] };
if (_meds isNotEqualTo "") then { _lines pushBack format ["Medications: %1", _meds] };
if (_all isNotEqualTo "") then { _lines pushBack format ["Allergies: %1", _all] };
if (_hist isNotEqualTo "") then { _lines pushBack format ["History: %1", _hist] };
private _v = [];
if (_sen isNotEqualTo [] && {_sen select 1}) then {
	_v = ([_u, _sen select 0] call ACME_fnc_batdokSense) select 1;
} else {
	if (_man isNotEqualTo []) then { _v = _man select [0, 7] };
};
if (_v isNotEqualTo []) then {
	private _s = { params ["_n"]; [str _n, "--"] select (_n < 0) };
	_lines pushBack format ["Vitals: HR %1  SpO2 %2  RR %3  BP %4/%5  Temp %6  EtCO2 %7", [_v select 0] call _s, [_v select 1] call _s, [_v select 2] call _s, [_v select 3] call _s, [_v select 4] call _s, [_v select 5] call _s, [_v select 6] call _s];
};
private _w = ([_u] call ACME_fnc_batdokWounds) apply { _x select 5 };
_w append (_inj apply { _x select 5 });
_lines pushBack format ["Injuries: %1", [_w joinString ", ", "None"] select (_w isEqualTo [])];
_lines pushBack "Record:";
{
	_x params ["", "_kind", "_label", "", "_t"];
	_lines pushBack format ["  %1 %2 %3", [_t] call _hhmm, toUpperANSI _kind, _label];
} forEach (_u getVariable ["acme_batdok_log", []]);
if (_xfer isNotEqualTo []) then { _lines pushBack format ["Transfer: %1 to %2", _xfer select 0, _xfer select 1] };
_lines joinString _nl
