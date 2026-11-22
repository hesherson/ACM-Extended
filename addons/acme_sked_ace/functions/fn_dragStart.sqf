/*
 * The drag action: ask the server for the target. Arguments: 0: rescuer, 1: target.
 */
params ["_unit", "_target"];
if !([_unit, _target] call acme_sked_fnc_dragCan) exitWith {};
[_unit, "dragBegin", _target] call acme_sked_fnc_request;
