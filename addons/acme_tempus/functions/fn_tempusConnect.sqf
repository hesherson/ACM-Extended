params ["_o", "_u"];
if (isNull _o) exitWith {};
private _old = _o getVariable ["acme_tempus_pat", objNull];
_o setVariable ["acme_tempus_pat", _u, true];
_o setVariable ["acme_tempus_v", [], true];
if (isNull _u) exitWith {
	if (!isNull _old) then { [format ["Tempus Pro disconnected from %1", [_old, false, true] call ace_common_fnc_getName], 1.5] call ace_common_fnc_displayTextStructured };
};
[_o, _u] remoteExecCall ["ACME_fnc_tempusFeed", _u];
[format ["Tempus Pro connected to %1", [_u, false, true] call ace_common_fnc_getName], 1.5] call ace_common_fnc_displayTextStructured;
