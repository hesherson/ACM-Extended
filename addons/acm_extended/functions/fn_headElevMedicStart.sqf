/* Provider animation and UI stay on the provider's machine. */
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]]];
if (isNull _medic || {isNull _patient} || {!alive _medic} || {!alive _patient}
    || {!(_patient getVariable ["ACME_headElevated", false])}) exitWith {};
if (!local _medic) exitWith {[_medic, "headElevMedicStart", [_medic, _patient]] call ACME_fnc_ownerDispatch;};
missionNamespace setVariable ["ACME_headElev_TunePatient", _patient];
// the forced medic positioning sequence, which is cancellable.
    private _token = diag_tickTime;
    _medic setVariable ["ACME_headElev_seqToken", _token];
    _medic setVariable ["ACME_headElev_seqActive", true];
    _medic setVariable ["ACME_headElev_seqPatient", _patient];

    // B89: elevate intentionally uses the same provider Putdown sequence as lay-flat/supine.
    // The patient animation path is independent and untouched.
    [_medic, "elevate", _patient, _patient getVariable ["ACME_headElev_poseToken", ""]] call ACME_fnc_headElevMedicSeq;

    // fn_headElevMedicSeq clears seqActive after the provider sequence completes.

    private _placementMsg = if (missionNamespace getVariable ["ACME_hc_descriptors", false]) then {
        format ["%1 was placed in Semi-Fowler's position", [_patient, false, true] call ace_common_fnc_getName]
    } else {
        "Head Elevated 30°"
    };
    [_placementMsg, 3, _medic] call ace_common_fnc_displayTextStructured;
    if (!isNil "ace_medical_treatment_fnc_addToLog") then {
        [_patient, "activity",
 "%1 elevated head 30 degrees",
 "%1 placed them in Semi-Fowler's position",
 [[_medic, false, true] call ace_common_fnc_getName]] call ACME_fnc_medLog;
    };
