/*
 * Server: give a target to a rescuer to drag. The target is claimed (ACE claim too, so ACE cargo, drag and carry
 * leave it alone), then the rescuer's machine does the dragging (fn_dragLocal.sqf).
 * Arguments: 0: rescuer, 1: target.
 */
params ["_unit", "_target"];
if (!isServer || {isNull _target} || {_unit distance _target > 5}) exitWith {};
if !([_unit, _target] call acme_sked_fnc_dragCan) exitWith {};
_target setVariable ["acme_drag_by", _unit, true];
_unit setVariable ["acme_drag_target", _target, true];
[_unit, _target, true] call ace_common_fnc_claim;
acme_drag_active pushBack [_unit, _target, serverTime];      // watched from XEH_postInit.sqf
["drag begun", _target, _unit, []] call acme_sked_fnc_traceTransport;
[_unit, "dragLocal", [_unit, _target]] call acme_sked_fnc_sendLocal;
