params ["_c", "_o", ["_force", false]];
if (isNull _c || {isNull _o} || {!(_c getVariable ["acme_tempus_ready", false])}) exitWith {};
private _pw = _o getVariable ["acme_tempus_pw", [false, 0, false]];
private _pwKey = str _pw;
if (_force || {_pwKey isNotEqualTo (_c getVariable ["acme_tempus_sPw", ""])}) then {
	_c setVariable ["acme_tempus_sPw", _pwKey];
	_pw params [["_on", false], ["_t0", 0], ["_adm", false]];
	_c ctrlWebBrowserAction ["ExecJS", format ["tp.power(%1,%2,%3)", ["false", "true"] select _on, (round ((CBA_missionTime - _t0) * 1000)) max 0, ["false", "true"] select _adm]];
};
private _st = _o getVariable ["acme_tempus_st", ""];
if (_st isNotEqualTo "" && {_force || {(_c getVariable ["acme_tempus_mode", ""]) isEqualTo "mirror" && {_st isNotEqualTo (_c getVariable ["acme_tempus_sSt", ""])}}}) then {
	_c setVariable ["acme_tempus_sSt", _st];
	_c ctrlWebBrowserAction ["ExecJS", "tp.load(JSON.stringify(" + _st + "))"];
};
private _nb = _o getVariable ["acme_tempus_nibp", -1];
if ((_c getVariable ["acme_tempus_mode", ""]) isEqualTo "mirror" && {_nb isNotEqualTo (_c getVariable ["acme_tempus_sNb", -1])}) then {
	_c setVariable ["acme_tempus_sNb", _nb];
	if (_nb >= 0) then { _c ctrlWebBrowserAction ["ExecJS", "tp.nibp()"] };
};
private _v = _o getVariable ["acme_tempus_v", []];
private _pat = _o getVariable ["acme_tempus_pat", objNull];
if (isNull _pat) then { _v = [] };
if (_force || {_v isNotEqualTo (_c getVariable ["acme_tempus_sV", []])} || {diag_tickTime - (_c getVariable ["acme_tempus_vAt", 0]) > 5}) then {
	_c setVariable ["acme_tempus_sV", _v];
	_c setVariable ["acme_tempus_vAt", diag_tickTime];
	private _js = if (_v isEqualTo []) then {
		"tp.vitals({hr:null,electricalHR:null,rhythm:1,spo2:null,resp:null,etco2:null,sys:null,dia:null,mean:null,t1:null,t2:null,pi:null})"
	} else {
		_v params ["_hr", "_ehr", "_rh", "_sys", "_dia", "_spo2", "_rr", "_co2", "_tc"];
		private _r = switch (true) do {
			case (_rh in [0, 1, 2, 3, 4, 5]): {_rh};
			case (_rh == 102): {4};
			default {0};
		};
		private _n = { if (_this < 0) then {"null"} else {str _this} };
		private _mean = round (_dia + (_sys - _dia) / 3);
		private _pi = if (_spo2 > 0) then { (round (linearConversion [60, 120, _sys, 4, 60, true])) / 10 } else { 0 };
		private _t = if (_tc < 0) then {"null"} else { str ((round ((_tc * 9 / 5 + 32) * 10)) / 10) };
		format ["tp.vitals({hr:%1,electricalHR:%2,rhythm:%3,spo2:%4,resp:%5,etco2:%6,sys:%7,dia:%8,mean:%9,t1:%10,t2:null,pi:%11})",
			_hr, _ehr, _r, _spo2, _rr call _n, _co2 call _n, _sys, _dia, _mean, _t, _pi]
	};
	_c ctrlWebBrowserAction ["ExecJS", _js];
};

[_c, _o, false, _force] call ACME_fnc_tempusWaveforms;
