/*
 * The nearest unit within 3 m of a laid out SKED that can be strapped into it.
 * Arguments: 0: SKED, 1: rescuer (left out). Returns: object (objNull if none).
 */
params ["_litter", ["_rescuer", objNull], ["_all", false]];
private _near = (nearestObjects [_litter, ["CAManBase"], 3.5]) select {
    _x != _rescuer && {isNull _rescuer || {_rescuer distance _x <= 3.5}}
        && {[_x] call acme_sked_fnc_validCasualty}
};
if (_all) exitWith {_near};
_near param [0, objNull]
