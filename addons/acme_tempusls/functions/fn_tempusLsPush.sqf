params ["_c", "_o", ["_force", false]];
if (isNull _c || {isNull _o} || {!(_c getVariable ["acme_tempusls_ready", false])}) exitWith {};
private _mode = _c getVariable ["acme_tempusls_mode", ""];
private _pw = (_o getVariable ["acme_tempusls_pw", [false]]) select 0;
if (_force || {_pw isNotEqualTo (_c getVariable ["acme_tempusls_sPw", -1])}) then {
	_c setVariable ["acme_tempusls_sPw", _pw];
	_c ctrlWebBrowserAction ["ExecJS", format ["tls.power(%1)", _pw]];
};
private _st = _o getVariable ["acme_tempusls_st", ""];
if (_st isNotEqualTo "" && {_force || {_mode isEqualTo "mirror" && {_st isNotEqualTo (_c getVariable ["acme_tempusls_sSt", ""])}}}) then {
	_c setVariable ["acme_tempusls_sSt", _st];
	_c ctrlWebBrowserAction ["ExecJS", "tls.load(" + _st + ")"];
};
private _pat = _o getVariable ["acme_tempusls_pat", objNull];
private _v = [_o getVariable ["acme_tempusls_v", []], []] select (isNull _pat);
if (_force || {_v isNotEqualTo (_c getVariable ["acme_tempusls_sV", -1])} || {diag_tickTime - (_c getVariable ["acme_tempusls_vAt", 0]) > 5}) then {
	_c setVariable ["acme_tempusls_sV", _v];
	_c setVariable ["acme_tempusls_vAt", diag_tickTime];
	private _js = if (_v isEqualTo []) then {
		"tls.vitals({hr:0,rhythm:'asystole',pads:false,ecg:false,shockable:false,cpr:false,capture:false})"
	} else {
		_v params ["_hr", "_rh", "_shock", "_cpr", "_cap"];
		format ["tls.vitals({hr:%1,rhythm:'%2',pads:true,ecg:true,shockable:%3,cpr:%4,capture:%5})", _hr, _rh, _shock, _cpr, _cap]
	};
	_c ctrlWebBrowserAction ["ExecJS", _js];
};
private _link = !isNull (_o getVariable ["acme_tempusls_link", objNull]);
if (_force || {_link isNotEqualTo (_c getVariable ["acme_tempusls_sLink", -1])}) then {
	_c setVariable ["acme_tempusls_sLink", _link];
	_c ctrlWebBrowserAction ["ExecJS", format ["tls.link(%1)", _link]];
};

[_c, _o, true, _force] call ACME_fnc_tempusWaveforms;
