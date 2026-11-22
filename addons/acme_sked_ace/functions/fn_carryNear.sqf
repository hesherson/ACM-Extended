/*
 * The litter near this rescuer whose foot end he could lift (fn_carryCan.sqf), or objNull.
 * (A litter that is being dragged is claimed by the rescuer who drags it, and ACE shows nobody else its menu;
 * so the action is on the rescuer who drags, and in the self menu.)
 * Arguments: 0: rescuer. Returns: object.
 */
params ["_unit"];
private _near = (nearestObjects [_unit, ["ACME_SKED_Base"], 4.5]) select {[_unit, _x] call acme_sked_fnc_carryCan};
_near param [0, objNull]
