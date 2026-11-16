/*
 * Server: strap a casualty into a laid out SKED. The laid out SKED is replaced by the wrapped one at the
 * same place; the casualty is posed and placed in it where they are local; ACE body drag and carry of the
 * casualty are turned off while they are strapped in (the SKED is what is moved). The casualty's own ACE
 * drag and carry state is kept, to give back when they come out.
 * Arguments: 0: rescuer, 1: casualty, 2: laid out SKED.
 * Returns: the wrapped SKED, or objNull if the casualty or the SKED could not be used.
 */
params ["_rescuer", "_patient", "_open"];
if (!isServer) exitWith {objNull};
if (isNull _open || {!(_open isKindOf "ACME_SKED_Open")} || {!isNull attachedTo _open}
    || {!isNull (_open getVariable ["ace_common_owner", objNull])} || {!([_patient] call acme_sked_fnc_validCasualty)}) exitWith {objNull};
private _posASL = getPosASL _open;
private _dir = getDir _open;
private _up = vectorUp _open;
private _class = getText (configOf _open >> "acmeLitterOccupied");
private _litter = createVehicle [_class, ASLToATL _posASL, [], 0, "CAN_COLLIDE"];
if (isNull _litter) exitWith {objNull};
deleteVehicle _open;
_litter setDir _dir;
_litter setPosASL _posASL;
_litter setVectorUp _up;
_litter setVariable ["acme_sked_patient", _patient, true];
_litter setVariable ["acme_sked_bearers", [objNull, objNull, objNull, objNull], true];
_patient setVariable ["acme_sked_litter", _litter, true];
[_patient] call acme_sked_fnc_srvDragOff;
if (_class == "ACME_SKED_Wrapped" && {missionNamespace getVariable ["acme_sked_hpmkSqueeze", true]}) then {
    [_patient, "hpmkSwap", [_patient, true]] call acme_sked_fnc_sendLocal;
};
["strapped", _litter, _patient, [_rescuer]] call acme_sked_fnc_traceTransport;
[_patient, "attachLocal", [_patient, _litter]] call acme_sked_fnc_sendLocal;
_litter
