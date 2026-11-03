params ["_o", "_tex", ["_s", objNull]];
if (isNull _o) exitWith {};
if (isNull _s) then { _s = _o };
if (_tex isEqualTo "") then {
	_tex = ["#(argb,8,8,3)color(0,0,0,1,co)", "\acme_tempusls\data\screen_co.paa"] select ((_s getVariable ["acme_tempusls_pw", [false]]) select 0);
};
if ((_o getVariable ["acme_tempusls_tex", ""]) isNotEqualTo _tex) then {
	_o setVariable ["acme_tempusls_tex", _tex];
	_o setObjectTexture [0, _tex];
};
