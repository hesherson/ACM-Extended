params ["_from", "_to"];
if (isNull _from || {isNull _to} || {_from isEqualTo _to}) exitWith {};
private _pat = _from getVariable ["acme_tempusls_pat", objNull];
if (!isNull _pat) then {[_from, _pat, false] remoteExecCall ["ACME_fnc_tempusLsPace", _pat];};
[_from] call ACME_fnc_tempusLsChargeClear;
[_to] call ACME_fnc_tempusLsChargeClear;
_to setVariable ["acme_tempusls_operator", call ACME_fnc_controlledProvider, true];
_from setVariable ["acme_tempusls_pat", objNull, true];
{
	_to setVariable [_x, _from getVariable _x, true];
	_from setVariable [_x, nil, true];
} forEach ["acme_tempusls_pw", "acme_tempusls_st", "acme_tempusls_v", "acme_tempusls_link", "acme_tempusls_metro", "acme_tempusls_pace"];
if (isNull _pat) exitWith {};
_to setVariable ["acme_tempusls_pat", _pat, true];
[_to, _pat] remoteExecCall ["ACME_fnc_tempusLsFeed", _pat];
private _pace = _to getVariable ["acme_tempusls_pace", [false, 70, 0, false]];
if (_pace select 0) then { ([_to, _pat] + _pace) remoteExecCall ["ACME_fnc_tempusLsPace", _pat] };
