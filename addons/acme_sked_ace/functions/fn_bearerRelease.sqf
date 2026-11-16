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
[_unit, "forceWalk", "acme_sked", false] call ace_common_fnc_statusEffect_set;
if (alive _unit && {lifeState _unit in ["HEALTHY", "INJURED"]}) then {
    [_unit, "AmovPercMstpSnonWnonDnon", 1] call ace_common_fnc_doAnimation;
};
