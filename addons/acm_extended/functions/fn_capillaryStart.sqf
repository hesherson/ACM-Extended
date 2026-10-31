/* B223: pulse-family provider pose for the existing capillary-refill timer. */
params ["_medic", "_patient"];
if (isNull _medic || {!local _medic}) exitWith {};
private _serial = (_medic getVariable ["ACME_capillarySerial", 0]) + 1;
_medic setVariable ["ACME_capillarySerial", _serial, false];
private _pose = if (isNull objectParent _medic) then {
    [_medic, "pulse", -1, _patient] call ACME_fnc_treatmentPoseStart
} else {-1};
_medic setVariable ["ACME_capillaryPose", [_serial, _patient, _pose], false];
