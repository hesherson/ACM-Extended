/* AAJT provider theatre follows ACE's real treatment lifetime, including mission timing modifiers.
 * One shared pose owner holsters once, preserves prone, and repeats Flip's medic4 work until success/cancel.
 * The patient device commit remains in aajtApply/aajtRemove on the casualty owner.
 */
params ["_medic", "_patient", "_bodyPart", "_classname"];
if (isNull _medic || {!local _medic} || {isNull _patient}) exitWith {-1};
private _serial = (_medic getVariable ["ACME_aajtTreatmentSerial", 0]) + 1;
_medic setVariable ["ACME_aajtTreatmentSerial", _serial, false];
private _classKey = toLowerANSI _classname;
private _epoch = -1;
// Seated care remains native; an on-foot kneeling/prone work animation must never eject a provider from a seat.
if (isNull objectParent _medic) then {
    _epoch = [_medic, "aajt", -1, _patient] call ACME_fnc_treatmentPoseStart;
};
_medic setVariable ["ACME_aajtTreatment", [_serial, _patient, _bodyPart, _classKey, _epoch], false];
if ((_classKey find "acme_applyaajt_") == 0) then {
    [_patient, "aajtApplying", [toLowerANSI _bodyPart, true]] call ACME_fnc_ownerDispatch;
};
_serial
