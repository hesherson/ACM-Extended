params ["_o", "_on"];
if (isNull _o) exitWith {};
_o setVariable ["acme_tempusls_pw", [_on, CBA_missionTime], true];
if (!_on) then {
	private _pat = _o getVariable ["acme_tempusls_pat", objNull];
	if (((_o getVariable ["acme_tempusls_pace", [false]]) select 0) && {!isNull _pat}) then { [_o, _pat, false] remoteExecCall ["ACME_fnc_tempusLsPace", _pat] };
	_o setVariable ["acme_tempusls_pace", [false, 70, 0, false], true];
	[_o] call ACME_fnc_tempusLsChargeClear;
	_o setVariable ["acme_tempusls_metro", [false, ""], true];
	_o setVariable ["acme_tempusls_st", "", true];
	_o setVariable ["acme_tempusls_link", objNull, true];
};
[["Tempus LS powering off", "Tempus LS self test"] select _on, 1.5] call ace_common_fnc_displayTextStructured;
