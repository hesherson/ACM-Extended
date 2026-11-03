params [["_u", objNull], ["_from", ""], ["_dest", ""]];
if (isNull _u || {!hasInterface}) exitWith {};
ACME_batdok_roster pushBackUnique _u;
private _cs = ((_u getVariable ["acme_batdok_rec", []]) param [1, []]) param [1, ""];
if (_cs isEqualTo "") then { _cs = [_u, false, true] call ace_common_fnc_getName };
private _t = if (_from isEqualTo "") then { format ["BATDOK: %1 received", _cs] } else { format ["BATDOK: %1 from %2", _cs, _from] };
if (_dest isNotEqualTo "") then { _t = _t + format [" (%1)", _dest] };
[_t] call ACME_fnc_batdokToast;
