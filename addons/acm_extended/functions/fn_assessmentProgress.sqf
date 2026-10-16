/* ACE progress condition; descendants retain their normal conditions and seated care needs no pose. */
params ["_args"];
_args params ["_medic", "_patient", "_part", "_classname"];
if !((toLowerANSI _classname) in ["checkairway", "checkbreathing"]) exitWith {true};
if (isNull _medic || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {false};
if (!isNull objectParent _medic) exitWith {
    // Only an assessment STARTED seated has no pose epoch. Entering a vehicle cancels an on-foot episode;
    // its progress callback must not silently become a fresh no-pose seated assessment.
    (_args param [7, -2]) == -1 && {objectParent _medic isEqualTo objectParent _patient}
};
private _record = _medic getVariable ["ACME_assessment", []];
if (_record isEqualTo []
    || {(_args param [7, -1]) != (_record select 0)}) exitWith {false};
private _owned = _record select 1;
(_owned param [1, objNull]) isEqualTo _patient
    && {(_owned param [2, ""]) == _part}
    && {(toLowerANSI (_owned param [3, ""])) == toLowerANSI _classname}
    && {((_medic getVariable ["ACME_treatmentPoseState", []]) param [0, -1]) == (_record select 0)}
    && {([_medic, _patient] call ACME_fnc_patientInteractionDistance) <= ace_medical_gui_maxDistance}
