/*
 * The nearest unit within 3 m of a laid out SKED that can be strapped into it.
 * Arguments: 0: SKED, 1: rescuer (left out). Returns: object (objNull if none).
 */
params ["_litter", ["_rescuer", objNull]];
((nearestObjects [_litter, ["CAManBase"], 3]) select {
    _x != _rescuer && {[_x] call acme_sked_fnc_validCasualty}
}) param [0, objNull]
