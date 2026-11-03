params ["_o", "_tex"];
if (isNull _o) exitWith {};
if (_tex isEqualTo "") then {
	_tex = ["#(argb,8,8,3)color(0,0,0,1,co)", "\acme_tempus\data\screen_co.paa"] select ((_o getVariable ["acme_tempus_pw", [false]]) select 0);
};
if ((_o getVariable ["acme_tempus_tex", ""]) isNotEqualTo _tex) then {
	_o setVariable ["acme_tempus_tex", _tex];
	_o setObjectTexture [0, _tex];
};
