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
if (isNull _patient) exitWith {};
_patient setVariable ["acme_sked_litter", nil, true];
if (_stow) exitWith {
    _patient setVariable ["acme_sked_stowedOpen", getText (configOf _litter >> "acmeLitterOpen"), true];
    _patient setVariable ["acme_sked_stowed", true, true];
    ["stowed", _litter, _patient, [objectParent _patient]] call acme_sked_fnc_traceTransport;
};
["unstrapped", _litter, _patient] call acme_sked_fnc_traceTransport;
[_patient, "releaseLocal", [_patient, _litter]] call acme_sked_fnc_sendLocal;
[_patient] call acme_sked_fnc_srvDragOn;
