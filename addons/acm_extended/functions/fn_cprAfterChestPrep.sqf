/* B223: an already validated chest-preparation click hands directly to native CPR.
   No second 10 ms progress dialog / inherited treatment animation between the released carrier pose
   and beginCPR. Native CPR still owns eligibility, session, input, clinical effect and cancellation. */
params ["_medic", "_patient", "_bodyPart", "_class"];
if (isNull _medic || {isNull _patient} || {!local _medic}
    || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
    || {toLowerANSI _class != "cpr"}
    || {_medic getVariable ["ACME_chestAccessPreflightActive", false]}) exitWith {false};
if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
private _exceptions = [["isNotInside", "isNotSwimming", "isNotInZeus"], ["isNotSwimming", "isNotInZeus"]]
    select (!isNull objectParent _medic && {objectParent _medic isEqualTo objectParent _patient});
if !([_medic, _patient, _exceptions] call ace_common_fnc_canInteractWith) exitWith {false};
if (objectParent _medic isNotEqualTo objectParent _patient
    || {isNull objectParent _medic && {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}}) exitWith {false};
private _eventArgs = [_medic, _patient, _bodyPart, _class, objNull, "", false];
ace_medical_gui_pendingReopen = false;
["ace_treatmentStarted", _eventArgs] call CBA_fnc_localEvent;
[_medic, _patient] call ACM_circulation_fnc_beginCPR;
private _started = (_medic getVariable ["ACM_circulation_CPR_Patient", objNull]) isEqualTo _patient
    && {_medic getVariable ["ACM_circulation_isPerformingCPR", false]};
// These events keep the existing stable chest lease/watch. They do not deliver compressions.
[["ace_treatmentFailed", "ace_treatmentSucceded"] select _started, _eventArgs] call CBA_fnc_localEvent;
if (!_started) then {diag_log "[ACME CPR] prepared chest handoff did not acquire native CPR session";};
_started
