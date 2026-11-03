params ["_o", "_u"];
if (isNull _o) exitWith {};
private _old = _o getVariable ["acme_tempusls_pat", objNull];
if (_old isNotEqualTo _u) then {
    [_o] call ACME_fnc_tempusLsChargeClear;
    _o setVariable ["acme_tempusls_st", "", true];
    _o setVariable ["acme_tempusls_pace", [false, 70, 0, false], true];
};
if (!isNull _old && {_old isNotEqualTo _u}) then { [_o, _old, false] remoteExecCall ["ACME_fnc_tempusLsPace", _old] };
_o setVariable ["acme_tempusls_pat", _u, true];
_o setVariable ["acme_tempusls_v", [], true];
private _me = [player, false, true] call ace_common_fnc_getName;
if (isNull _u) exitWith {
	if (!isNull _old) then {
		[format ["Tempus LS pads removed from %1", [_old, false, true] call ace_common_fnc_getName], 1.5] call ace_common_fnc_displayTextStructured;
		[_old, "activity", "%1 removed Tempus LS pads", [_me]] call ace_medical_treatment_fnc_addToLog;
	};
};
[_o, _u] remoteExecCall ["ACME_fnc_tempusLsFeed", _u];
private _pace = _o getVariable ["acme_tempusls_pace", [false, 70, 0, false]];
if (_pace select 0) then { ([_o, _u] + _pace) remoteExecCall ["ACME_fnc_tempusLsPace", _u] };
[format ["Tempus LS pads applied to %1", [_u, false, true] call ace_common_fnc_getName], 1.5] call ace_common_fnc_displayTextStructured;
[_u, "activity", "%1 applied Tempus LS pads", [_me]] call ace_medical_treatment_fnc_addToLog;
