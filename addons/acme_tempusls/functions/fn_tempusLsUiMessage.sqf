params ["_c", "", "_msg"];
if (isNull _c || {!(_msg isEqualType "")} || {(_msg select [0, 4]) != "TLS|"}) exitWith {};
private _p = _msg splitString "|";
private _mode = _c getVariable ["acme_tempusls_mode", ""];
private _o = _c getVariable ["acme_tempusls_obj", objNull];
private _dlg = _mode isEqualTo "dialog" && {!isNull _o};
switch (_p param [1, ""]) do {
	case "hello": {
		_c ctrlWebBrowserAction ["ExecJS", format ["tls.mode('%1');tls.lcd(%2)", _mode, _mode isEqualTo "dialog"]];
		_c setVariable ["acme_tempusls_ready", true];
		_c setVariable ["acme_tempusls_size", [parseNumber (_p param [2, "0"]), parseNumber (_p param [3, "0"])]];
		if (_mode isEqualTo "mirror") then {
			(_c getVariable ["acme_tempusls_size", [0, 0]]) params ["_w", "_h"];
			if (abs (_w - 1024) > 8 || {abs (_h - 1024) > 8}) then {
				_c ctrlSetPosition [0, 0, 1, 1];
				_c ctrlCommit 0;
			};
		};
		[_c, _o, true] call ACME_fnc_tempusLsPush;
	};
	case "size": {
		_c setVariable ["acme_tempusls_size", [parseNumber (_p param [2, "0"]), parseNumber (_p param [3, "0"])]];
	};
	case "st": {
		if (_dlg) then {
			private _i = parseNumber (_p param [2, "0"]);
			private _n = parseNumber (_p param [3, "1"]);
			private _buf = if (_i == 0) then { [] } else { _c getVariable ["acme_tempusls_buf", []] };
			_buf set [_i, toString (((_p param [4, ""]) splitString ".") apply { parseNumber _x })];
			_c setVariable ["acme_tempusls_buf", _buf];
			if (_i == _n - 1 && {count _buf == _n}) then {
				private _s = _buf joinString "";
				_c setVariable ["acme_tempusls_buf", []];
				_c setVariable ["acme_tempusls_sSt", _s];
				if (count _s < 20000) then { _o setVariable ["acme_tempusls_st", _s, true] };
			};
		};
	};
	case "shock": {
		if (_dlg) then { [_o, parseNumber (_p param [2, "0"]), (_p param [3, "0"]) isEqualTo "1", _p param [5, "Adult"]] call ACME_fnc_tempusLsDischarge };
	};
	case "ev": {
		if (_dlg) then {
            private _event = _p param [2, ""];
            private _context = _c getVariable ["ACME_chargeContext", []];
            private _result = [_o, _event, _p param [3, ""], _context] call ACME_fnc_tempusLsSound;
            if (_event == "charge") then {_c setVariable ["ACME_chargeContext", _result];};
            if (_event in ["ready", "disarm"]) then {_c setVariable ["ACME_chargeContext", []];};
        };
	};
	case "pace": {
		if (_dlg) then {
			private _pace = [(_p param [2, "0"]) isEqualTo "1", parseNumber (_p param [3, "70"]), parseNumber (_p param [4, "0"]), (_p param [5, "0"]) isEqualTo "1"];
			if (_pace isNotEqualTo (_o getVariable ["acme_tempusls_pace", []])) then {
				_o setVariable ["acme_tempusls_pace", _pace, true];
				private _pat = _o getVariable ["acme_tempusls_pat", objNull];
				if (!isNull _pat) then { ([_o, _pat] + _pace) remoteExecCall ["ACME_fnc_tempusLsPace", _pat] };
			};
		};
	};
	case "metro": {
		if (_dlg) then { _o setVariable ["acme_tempusls_metro", [(_p param [2, "0"]) isEqualTo "1", _p param [3, ""]], true] };
	};
	case "pair": {
		if (_dlg) then { [_o] call ACME_fnc_tempusLsPair };
	};
};
