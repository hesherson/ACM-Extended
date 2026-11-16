/*
 * Server: take the casualty out of the SKED. The casualty stays where they lie; the SKED, laid out and
 * empty, goes beside them (pulled out from under them).
 * Arguments: 0: SKED.
 */
params ["_litter"];
if (!isServer || {isNull _litter}) exitWith {};
private _pos = _litter modelToWorld [1.1, 0, 0];
private _dir = getDir _litter;
private _open = [getText (configOf _litter >> "acmeLitterOpen"), _pos, _dir] call acme_sked_fnc_place;
if (isNull _open) exitWith {};
[_litter, false] call acme_sked_fnc_srvRelease;
deleteVehicle _litter;
