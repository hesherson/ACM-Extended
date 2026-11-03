params [["_u", objNull], ["_op", ""], ["_a", []], ["_by", objNull]];
if (!isServer || {isNull _u} || {!(_u isKindOf "CAManBase")}) exitWith {};
// Network callers identify their own provider; server sampling has no remote sender.
if (isRemoteExecuted && {isNull _by || {remoteExecutedOwner != owner _by}}) exitWith {};
if !(_op in ["add", "upd", "inj", "log", "vit", "sample", "sen", "xfer", "touch"]) exitWith {};
if (isNil "ACME_batdok_units") then { ACME_batdok_units = [] };
private _fields = ["name", "callsign", "age", "sex", "triage", "dob", "height", "weight", "medications", "allergies", "history", "evac"];
private _rec = _u getVariable ["acme_batdok_rec", []];
if (_rec isEqualTo []) then {
	ACME_batdok_seq = (missionNamespace getVariable ["ACME_batdok_seq", 0]) + 1;
	_rec = [format ["b%1", ACME_batdok_seq], [[_u, false, true] call ace_common_fnc_getName, [_u] call ACME_fnc_batdokCallsign, "", "Unknown", "Unassigned", "", "", "", "", "", "", "None"], [], [], [], []];
	ACME_batdok_units pushBackUnique _u;
	_u setVariable ["acme_batdok_log", [], true];
	_u setVariable ["acme_batdok_trend", [], true];
	if (isNil "ACME_batdok_tick") then { ACME_batdok_tick = [ACME_fnc_batdokTick, 5] call CBA_fnc_addPerFrameHandler };
};
_rec params ["_id", "_info", "_inj", "_man", "_sen", "_xfer"];
private _log = _u getVariable ["acme_batdok_log", []];
private _trend = _u getVariable ["acme_batdok_trend", []];
private _logged = false;
private _trended = false;
private _now = call ACME_fnc_batdokNow;
private _add = {
	params ["_kind", "_label", ["_pairs", []]];
	ACME_batdok_rid = (missionNamespace getVariable ["ACME_batdok_rid", 0]) + 1;
	_log pushBack [format ["r%1", ACME_batdok_rid], _kind, _label, _pairs, _now];
	if (count _log > 200) then { _log deleteRange [0, count _log - 200] };
	_logged = true;
};
private _tell = {
	if (!isNull _by && {isPlayer _by}) then { [_this] remoteExecCall ["ACME_fnc_batdokToast", _by] };
};
private _who = [_u, false, true] call ace_common_fnc_getName;

switch (_op) do {
	case "add": {
		{
			if (_x isNotEqualTo "") then { _info set [_forEachIndex, _x] };
		} forEach (_a select [0, 5]);
		private _tri = _a param [4, ""];
		if (_tri isNotEqualTo "") then { [_u, _tri] call ACME_fnc_batdokTriage };
	};
	case "upd": {
		_a params [["_f", ""], ["_v", ""]];
		private _i = _fields find _f;
		if (_i < 0) exitWith {};
		_info set [_i, _v];
		if (_f isEqualTo "triage") then { [_u, _v] call ACME_fnc_batdokTriage };
	};
	case "inj": {
		_a params [["_m", ""], ["_px", 0], ["_py", 0], ["_side", "front"], ["_type", "gsw"], ["_label", "Injury"]];
		if (_m isEqualTo "+") then {
			ACME_batdok_iid = (missionNamespace getVariable ["ACME_batdok_iid", 0]) + 1;
			_inj pushBack [format ["i%1", ACME_batdok_iid], _px, _py, _side, _type, _label];
		} else {
			private _i = _inj findIf { (_x select 0) isEqualTo (_a param [1, ""]) };
			if (_i >= 0) then { _inj deleteAt _i };
		};
	};
	case "log": { _a call _add };
	case "vit": {
		_a params [["_hr", -1], ["_spo2", -1], ["_rr", -1], ["_sys", -1], ["_dia", -1], ["_temp", -1], ["_co2", -1], ["_gcs", ""]];
		_man = [_hr, _spo2, _rr, _sys, _dia, _temp, _co2, _gcs, _now];
		_trend pushBack [_now, _hr, _spo2, _rr, _sys, _dia, _temp, _co2];
		if (count _trend > 120) then { _trend deleteRange [0, count _trend - 120] };
		_trended = true;
	};
	case "sample": {
		_trend pushBack ([_now] + _a);
		if (count _trend > 120) then { _trend deleteRange [0, count _trend - 120] };
		_trended = true;
	};
	case "sen": {
		_a params [["_dev", ""], ["_on", false]];
		if (_on) then {
			if (([_u, _dev] call ACME_fnc_batdokSense) select 0) then {
				_sen = [_dev, true];
				_u setVariable ["acme_batdok_miss", 0];
				private _t = format ["%1 connected", _dev];
				["event", _t, ["note", _t]] call _add;
			} else {
				(format ["No %1 on %2", _dev, _who]) call _tell;
			};
		} else {
			if (_sen isNotEqualTo [] && {_sen select 1}) then {
				_sen = [_sen select 0, false];
				private _t = format ["%1 disconnected", _sen select 0];
				["event", _t, ["note", _t]] call _add;
			};
		};
	};
	case "xfer": {
		_a params [["_to", objNull], ["_toName", ""], ["_dest", ""]];
		_xfer = [_toName, _dest];
		["transfer", format ["Transfer to %1", [_dest, _toName] select (_dest isEqualTo "")], ["recipient", _toName, "destination", _dest]] call _add;
		if (!isNull _to && {isPlayer _to}) then {
			private _from = if (isNull _by) then {""} else {[_by, false, true] call ace_common_fnc_getName};
			[_u, _from, _dest] remoteExecCall ["ACME_fnc_batdokRecv", _to];
		};
	};
};
_u setVariable ["acme_batdok_rec", [_id, _info, _inj, _man, _sen, _xfer], true];
if (_logged) then { _u setVariable ["acme_batdok_log", _log, true] };
if (_trended) then { _u setVariable ["acme_batdok_trend", _trend, true] };
_u setVariable ["acme_batdok_rev", (_u getVariable ["acme_batdok_rev", 0]) + 1, true];
