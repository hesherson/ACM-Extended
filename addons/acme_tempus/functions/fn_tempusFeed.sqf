params ["_o", "_u"];
if (isNull _o || {isNull _u}) exitWith {};
if (!local _u) exitWith { [_o, _u] remoteExecCall ["ACME_fnc_tempusFeed", _u] };
if ((_o getVariable ["acme_tempus_feeding", objNull]) isEqualTo _u) exitWith {};
_o setVariable ["acme_tempus_feeding", _u];
[{
	params ["_args", "_id"];
	_args params ["_o", "_u"];
	private _stop = {
		if (!isNull _o) then { _o setVariable ["acme_tempus_feeding", objNull] };
		[_id] call CBA_fnc_removePerFrameHandler;
	};
	if (isNull _o || {isNull _u} || {(_o getVariable ["acme_tempus_pat", objNull]) isNotEqualTo _u}) exitWith { call _stop };
	if (!local _u) exitWith {
		call _stop;
		[_o, _u] remoteExecCall ["ACME_fnc_tempusFeed", _u];
	};
	if (_u distance _o > 6) exitWith {
		call _stop;
		_o setVariable ["acme_tempus_pat", objNull, true];
		_o setVariable ["acme_tempus_v", [], true];
	};
	if !((_o getVariable ["acme_tempus_pw", [false]]) select 0) exitWith {};
	private _v = [_u] call ACME_fnc_tempusVitals;
	if (_v isNotEqualTo (_o getVariable ["acme_tempus_v", []])) then { _o setVariable ["acme_tempus_v", _v, true] };
}, 1.5, [_o, _u]] call CBA_fnc_addPerFrameHandler;
