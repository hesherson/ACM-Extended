params ["_from", "_to"];
private _pat = _from getVariable ["acme_tempus_pat", objNull];
_from setVariable ["acme_tempus_pat", objNull, true];
{
	_to setVariable [_x, _from getVariable _x, true];
	_from setVariable [_x, nil, true];
} forEach ["acme_tempus_pw", "acme_tempus_st", "acme_tempus_nibp", "acme_tempus_v"];
if (isNull _pat) exitWith {};
_to setVariable ["acme_tempus_pat", _pat, true];
[_to, _pat] remoteExecCall ["ACME_fnc_tempusFeed", _pat];
