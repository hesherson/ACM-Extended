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
    || {_open getVariable ["acme_talon_busy", false]}
    || {!isNull (_open getVariable ["ace_common_owner", objNull])} || {!([_patient] call acme_sked_fnc_validCasualty)}
    // another casualty is being laid on this litter
    || {(((_open getVariable ["acme_sked_placer", []]) param [1, -100]) > serverTime - 30)
        && {(_patient getVariable ["acme_sked_placing", objNull]) isNotEqualTo _open}}) exitWith {objNull};
private _laid = (attachedTo _patient) isEqualTo _open;
private _posASL = getPosASL _open;
private _dir = getDir _open;
private _up = vectorUp _open;
private _class = getText (configOf _open >> "acmeLitterOccupied");
private _litter = createVehicle [_class, ASLToATL _posASL, [], 0, "CAN_COLLIDE"];
if (isNull _litter) exitWith {objNull};
// A casualty who was laid on the open litter during the timer hangs on it until they are on the new one: the
// open litter is only hidden now and deleted a moment later, so the casualty never drops to the ground.
{deleteVehicle _x} forEach (_open getVariable ["acme_strap_arcs", []]);
// An HPMK was laid out ready on the litter ("Stage HPMK", fn_stageHpmk.sqf): the casualty is wrapped in it below.
private _staged = _open getVariable ["acme_sked_hpmkStaged", false];
if (_staged) then {
    deleteVehicle (_open getVariable ["acme_sked_hpmkSheet", objNull]);
    _open setVariable ["acme_sked_hpmkStaged", false, true];
};
if (_laid) then {
    _open hideObjectGlobal true;
    [{deleteVehicle _this;}, _open, 3] call CBA_fnc_waitAndExecute;
} else {
    deleteVehicle _open;
};
_patient setVariable ["acme_sked_placing", nil, true];
_litter setDir _dir;
_litter setPosASL _posASL;
_litter setVectorUp _up;
_litter setVariable ["acme_sked_patient", _patient, true];
_litter setVariable ["acme_sked_bearers", [objNull, objNull, objNull, objNull], true];
_patient setVariable ["acme_sked_litter", _litter, true];
// its straps are on the casualty from the first moment (fn_strapFit.sqf)
[_litter] call acme_sked_fnc_strapFit;
[_patient] call acme_sked_fnc_srvDragOff;
if (_class == "ACME_SKED_Wrapped" && {missionNamespace getVariable ["acme_sked_hpmkSqueeze", true]}) then {
    [_patient, "hpmkSwap", [_patient, true]] call acme_sked_fnc_sendLocal;
};
["strapped", _litter, _patient, [_rescuer]] call acme_sked_fnc_traceTransport;
[_patient, "attachLocal", [_patient, _litter]] call acme_sked_fnc_sendLocal;
if (_staged) then {[_rescuer, _patient, "wrap", _litter] call acme_sked_fnc_stageHpmk;};
_litter
