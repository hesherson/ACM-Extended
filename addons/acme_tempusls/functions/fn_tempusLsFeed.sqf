params ["_o", "_u"];
if (isNull _o || {isNull _u}) exitWith {};
if (!local _u) exitWith { [_o, _u] remoteExecCall ["ACME_fnc_tempusLsFeed", _u] };
if ((_o getVariable ["acme_tempusls_feeding", objNull]) isEqualTo _u) exitWith {};
_o setVariable ["acme_tempusls_feeding", _u];
[{
	params ["_args", "_id"];
	_args params ["_o", "_u"];
	private _stop = {
		if (!isNull _o) then { _o setVariable ["acme_tempusls_feeding", objNull] };
		[_id] call CBA_fnc_removePerFrameHandler;
	};
	if (isNull _o || {isNull _u} || {(_o getVariable ["acme_tempusls_pat", objNull]) isNotEqualTo _u}) exitWith { call _stop };
	if (!local _u) exitWith {
		call _stop;
		[_o, _u] remoteExecCall ["ACME_fnc_tempusLsFeed", _u];
	};
	if (_u distance _o > 6) exitWith {
		call _stop;
		[_o, _u, false] call ACME_fnc_tempusLsPace;
		_o setVariable ["acme_tempusls_pat", objNull, true];
		_o setVariable ["acme_tempusls_v", [], true];
	};
	if !((_o getVariable ["acme_tempusls_pw", [false]]) select 0) exitWith {};
	private _v = [_u] call ACME_fnc_tempusLsVitals;
	if (_v isNotEqualTo (_o getVariable ["acme_tempusls_v", []])) then { _o setVariable ["acme_tempusls_v", _v, true] };
}, 1, [_o, _u]] call CBA_fnc_addPerFrameHandler;
