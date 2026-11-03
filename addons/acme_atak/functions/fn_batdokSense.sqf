params [["_u", objNull], ["_dev", ""]];
private _none = [-1, -1, -1, -1, -1, -1, -1];
if (isNull _u) exitWith {[false, _none]};
private _near = {
	params ["_cls", "_var"];
	private _all = (_u nearObjects [_cls, 10]) + ((_u nearEntities ["CAManBase", 10]) select { isPlayer _x });
	private _i = _all findIf { (_x getVariable [_var, objNull]) isEqualTo _u };
	if (_i < 0) then {objNull} else {_all select _i}
};
switch (_dev) do {
	case "Tempus Pro": {
		private _o = ["ACME_TempusPro", "acme_tempus_pat"] call _near;
		if (isNull _o) exitWith {[false, _none]};
		private _v = _o getVariable ["acme_tempus_v", []];
		if (!((_o getVariable ["acme_tempus_pw", [false]]) select 0) || {count _v < 9}) exitWith {[true, _none]};
		_v params ["_hr", "_ehr", "", "_sys", "_dia", "_spo2", "_rr", "_co2", "_temp"];
		[true, [_ehr max 0, _spo2, _rr, _sys, _dia, (round (_temp * 10)) / 10, [-1, _co2] select (_co2 >= 0)]]
	};
	case "Tempus LS": {
		private _o = ["ACME_TempusLS", "acme_tempusls_pat"] call _near;
		if (isNull _o) exitWith {[false, _none]};
		private _v = _o getVariable ["acme_tempusls_v", []];
		if (!((_o getVariable ["acme_tempusls_pw", [false]]) select 0) || {_v isEqualTo []}) exitWith {[true, _none]};
		[true, [(_v select 0) max 0, -1, -1, -1, -1, -1, -1]]
	};
	case "Pulse oximeter": {
		private _pl = _u getVariable ["ACM_breathing_PulseOximeter_Placement", [false, false]];
		private _side = _pl findIf { _x isEqualTo true };
		if (_side < 0) exitWith {[false, _none]};
		private _d = (_u getVariable ["ACM_breathing_PulseOximeter_Display", [[0, 0], [0, 0]]]) param [_side, [0, 0]];
		_d params [["_hr", 0], ["_spo2", 0]];
		if (_hr <= 0 && {_spo2 <= 0}) exitWith {[true, _none]};
		[true, [round _hr, round _spo2, -1, -1, -1, -1, -1]]
	};
	case "Capnometer": {
		private _medic = _u getVariable ["ACM_breathing_BVM_Medic", objNull];
		private _bvm = !isNull _medic && {_medic getVariable ["ACME_emma_bvmAttached", false]} && {_medic distance _u < 5};
		private _tube = (_u getVariable ["ACME_emma_igelAttached", false]) && {isNil "ACME_fnc_emmaAirwayKind" || {([_u] call ACME_fnc_emmaAirwayKind) != ""}};
		if (!_bvm && {!_tube}) exitWith {[false, _none]};
		private _co2 = if (isNil "ACM_breathing_fnc_getEtCO2") then {-1} else { [_u] call ACM_breathing_fnc_getEtCO2 };
		if !(_co2 isEqualType 0) then { _co2 = -1 };
		private _rr = _u getVariable ["ACM_breathing_RespirationRate", -1];
		if !(_rr isEqualType 0) then { _rr = -1 };
		[true, [-1, -1, round _rr, -1, -1, -1, round _co2]]
	};
	default {[false, _none]};
}
