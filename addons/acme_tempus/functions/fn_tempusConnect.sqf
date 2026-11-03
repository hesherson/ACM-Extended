params ["_o", "_u"];
if (isNull _o || {_o getVariable ["ACME_eq_busy",false]}) exitWith {};
if (_o isEqualTo player && {!isNull _u} && {!isNil "ACME_fnc_equipmentSetup"}) exitWith {[_u,"pro"] call ACME_fnc_equipmentSetup;};

private _old = _o getVariable ["acme_tempus_pat", objNull];
_o setVariable ["acme_tempus_pat", _u, true];
_o setVariable ["acme_tempus_sensors",[!isNull _u,false,false,false,false],true];
_o setVariable ["acme_tempus_v", [], true];
if (isNull _u) exitWith {
	if (!isNull _old) then { [format ["Tempus Pro disconnected from %1", [_old, false, true] call ace_common_fnc_getName], 1.5] call ace_common_fnc_displayTextStructured };
};
[_o, _u] remoteExecCall ["ACME_fnc_tempusFeed", _u];
[format ["Tempus Pro connected to %1", [_u, false, true] call ace_common_fnc_getName], 1.5] call ace_common_fnc_displayTextStructured;
