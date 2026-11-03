params [["_a", []]];
private _cmd = _a param [0, ""];
private _unit = {
	params ["_pid"];
	private _i = ACME_batdok_roster findIf { ((_x getVariable ["acme_batdok_rec", []]) param [0, ""]) isEqualTo _pid };
	if (_i < 0) then {objNull} else {ACME_batdok_roster select _i}
};
private _op = {
	params ["_u", "_o", "_args"];
	if (!isNull _u) then { [_u, _o, _args, ACE_player] remoteExecCall ["ACME_fnc_batdokOp", 2] };
};
private _num = { params ["_s"]; if (_s isEqualTo "") then {-1} else { parseNumber _s } };
private _pick = {
	params ["_key", "_list", "_tag"];
	if ((_key select [0, 1]) isNotEqualTo _tag) exitWith {objNull};
	_list param [parseNumber (_key select [1]), objNull]
};
if (_cmd isEqualTo "ready") then {
	(missionNamespace getVariable ["ACME_batdok_ui", []]) params [["_pid", ""], ["_tab", ""]];
	if (_pid isNotEqualTo "" && {!isNull ([_pid] call _unit)}) then {
		ACME_batdok_focus = [((missionNamespace getVariable ["ACME_batdok_focus", [0]]) param [0, 0]) + 1, _pid, [_tab, "INFO"] select (_tab isEqualTo "")];
	};
};
if (_cmd in ["ready", "sync"]) then { _cmd = "sync" };
switch (_cmd) do {
	case "sync": { ACME_batdok_sent = createHashMap };
	case "ui": { ACME_batdok_ui = [_a param [1, ""], _a param [2, ""]] };
	case "upd": { [[_a param [1, ""]] call _unit, "upd", [_a param [2, ""], _a param [3, ""]]] call _op };
	case "inj": {
		private _u = [_a param [1, ""]] call _unit;
		if ((_a param [2, ""]) isEqualTo "+") then {
			[_u, "inj", ["+", parseNumber (_a param [3, "0"]), parseNumber (_a param [4, "0"]), _a param [5, "front"], _a param [6, "gsw"], _a param [7, "Injury"]]] call _op;
		} else {
			[_u, "inj", ["-", _a param [3, ""]]] call _op;
		};
	};
	case "rec": { [[_a param [1, ""]] call _unit, "log", [_a param [2, "event"], _a param [3, ""], _a select [4]]] call _op };
	case "vit": { [[_a param [1, ""]] call _unit, "vit", ((_a select [2, 7]) apply { [_x] call _num }) + [_a param [9, ""]]] call _op };
	case "add": {
		private _u = [_a param [1, ""], ACME_batdok_nearList, "n"] call _pick;
		if (isNull _u) exitWith {};
		ACME_batdok_roster pushBackUnique _u;
		ACME_batdok_want = _u;
		private _t = _a param [6, ""];
		if (_t isEqualTo "Unassigned") then { _t = "" };
		[_u, "add", [_a param [2, ""], _a param [3, ""], _a param [4, ""], _a param [5, ""], _t]] call _op;
	};
	case "sen": { [[_a param [1, ""]] call _unit, "sen", [_a param [2, ""], (_a param [3, ""]) isEqualTo "1"]] call _op };
	case "xfer": {
		private _to = [_a param [2, ""], ACME_batdok_peerList, "u"] call _pick;
		[[_a param [1, ""]] call _unit, "xfer", [_to, _a param [3, ""], _a param [4, ""]]] call _op;
	};
	case "exp": {
		private _t = [[_a param [1, ""]] call _unit] call ACME_fnc_batdokExport;
		if (_t isNotEqualTo "") then {
			copyToClipboard _t;
			["BATDOK: record copied to clipboard"] call ACME_fnc_batdokToast;
		};
	};
	case "del": {
		private _i = ACME_batdok_roster find ([_a param [1, ""]] call _unit);
		if (_i >= 0) then { ACME_batdok_roster deleteAt _i };
	};
	case "log": { diag_log text ("[ACME] BATDOK: " + (_a param [1, ""])) };
};
