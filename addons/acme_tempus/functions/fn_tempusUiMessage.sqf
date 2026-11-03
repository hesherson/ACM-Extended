params ["_c", "", "_msg"];
if (isNull _c || {!(_msg isEqualType "")} || {(_msg select [0, 3]) != "TP|"}) exitWith {};
private _p = _msg splitString "|";
private _mode = _c getVariable ["acme_tempus_mode", ""];
private _o = _c getVariable ["acme_tempus_obj", objNull];
switch (_p param [1, ""]) do {
	case "hello": {
		_c ctrlWebBrowserAction ["ExecJS", format ["tp.mode('%1');tp.lcd(%2)", _mode, ["false", "true"] select (_mode isEqualTo "dialog")]];
		_c setVariable ["acme_tempus_ready", true];
		if (_mode isEqualTo "mirror") then {
			private _w = parseNumber (_p param [2, "0"]);
			private _h = parseNumber (_p param [3, "0"]);
			_c setVariable ["acme_tempus_size", [_w, _h]];
			if (abs (_w - 1024) > 8 || {abs (_h - 1024) > 8}) then {
				_c ctrlSetPosition [0, 0, 1, 1];
				_c ctrlCommit 0;
			};
		};
		[_c, _o, true] call ACME_fnc_tempusPush;
	};
	case "size": {
		_c setVariable ["acme_tempus_size", [parseNumber (_p param [2, "0"]), parseNumber (_p param [3, "0"])]];
	};
	case "mon": {
		if (_mode isEqualTo "dialog" && {!isNull _o} && {(_p param [2, "0"]) isEqualTo "1"}) then {
			private _pw = _o getVariable ["acme_tempus_pw", [false, 0, false]];
			if ((_pw select 0) && {!(_pw param [2, false])}) then { _o setVariable ["acme_tempus_pw", [true, _pw select 1, true], true] };
		};
	};
	case "nibp": {
		if (_mode isEqualTo "dialog" && {!isNull _o}) then { _o setVariable ["acme_tempus_nibp", CBA_missionTime, true] };
	};
	case "state": {
		if (_mode isEqualTo "dialog" && {!isNull _o}) then {
			private _i = parseNumber (_p param [2, "0"]);
			private _n = parseNumber (_p param [3, "1"]);
			private _buf = if (_i == 0) then { [] } else { _c getVariable ["acme_tempus_buf", []] };
			_buf set [_i, toString (((_p param [4, ""]) splitString ".") apply { parseNumber _x })];
			_c setVariable ["acme_tempus_buf", _buf];
			if (_i == _n - 1 && {count _buf == _n}) then {
				private _s = _buf joinString "";
				_c setVariable ["acme_tempus_buf", []];
				if (count _s < 60000) then { _o setVariable ["acme_tempus_st", _s, true] };
			};
		};
	};
};
