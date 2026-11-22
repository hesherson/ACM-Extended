/*
 * Server: free the casualty and the rescuers of a wrapped SKED (before it is deleted). The casualty is
 * detached and posed where they lie; their ACE body drag and carry come back; the HPMK-I shell is
 * unsqueezed. With _stow the casualty keeps their SKED state (stowed in a vehicle with them).
 * Arguments: 0: SKED, 1: stow <BOOL>.
 */
params ["_litter", ["_stow", false]];
if (!isServer || {isNull _litter}) exitWith {};
{
    if (!isNull _x) then {[_x] call acme_sked_fnc_srvLetGo};
} forEach (_litter getVariable ["acme_sked_bearers", []]);
private _patient = _litter getVariable ["acme_sked_patient", objNull];
_litter setVariable ["acme_sked_patient", objNull, true];
// the picture of their pack on their legs goes with the litter
private _bag = _litter getVariable ["acme_sked_bag", objNull];
if (!isNull _bag) then {deleteVehicle _bag;};
if (isNull _patient) exitWith {};
_patient setVariable ["acme_sked_litter", nil, true];
if (_stow) exitWith {
    _patient setVariable ["acme_sked_stowedOpen", getText (configOf _litter >> "acmeLitterOpen"), true];
    _patient setVariable ["acme_sked_stowed", true, true];
    ["stowed", _litter, _patient, [objectParent _patient]] call acme_sked_fnc_traceTransport;
};
["unstrapped", _litter, _patient] call acme_sked_fnc_traceTransport;
// The server's own copy of what they wore goes with the order, in case the copy on the casualty is gone.
private _gear = if (isNil "acme_sked_gearKept") then {[]} else {acme_sked_gearKept getVariable [netId _patient, []]};
[_patient, "releaseLocal", [_patient, _litter, _gear]] call acme_sked_fnc_sendLocal;
[_patient] call acme_sked_fnc_srvDragOn;
