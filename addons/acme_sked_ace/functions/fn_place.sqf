/*
 * Create a SKED object on the ground. Server or any machine (createVehicle is global).
 * Arguments: 0: class, 1: position ATL, 2: direction (the head end points this way).
 * Returns: object.
 */
params ["_class", "_pos", "_dir"];
private _obj = createVehicle [_class, _pos, [], 0, "CAN_COLLIDE"];
if (isNull _obj) exitWith {objNull};
_obj setDir _dir;
_obj setPosATL _pos;
_obj setVectorUp (surfaceNormal _pos);
_obj
