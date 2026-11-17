/*
 * Where a rescuer is local: they have let go. Walk is free again; standing.
 * Arguments: 0: rescuer.
 */
params ["_unit", "_released"];
private _current = _unit getVariable ["acme_sked_bearing", objNull];
if (!local _unit || {!isNull _current && {_current isNotEqualTo _released}}) exitWith {};
private _parent = _unit getVariable ["acme_sked_bearerParent", objNull];
if (!isNull _parent && {(attachedTo _unit) isEqualTo _parent}) then {detach _unit;};
_unit setVariable ["acme_sked_bearerParent", nil];
private _watch = _unit getVariable ["acme_sked_bearerWatch", -1];
if (_watch >= 0) then {[_watch] call CBA_fnc_removePerFrameHandler;};
_unit setVariable ["acme_sked_bearerWatch", nil];
[_unit, "forceWalk", "acme_sked", false] call ace_common_fnc_statusEffect_set;
