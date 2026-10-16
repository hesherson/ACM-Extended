// Complete ACM's fracture inspection with the selected descriptor register.
// ACM core/ACE_Medical_Treatment_Actions.hpp:217-228 retains the six-second action and gates.
// This callback keeps ACM's native function intact for the non-hardcore result.
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_bodyPart", "", [""]]];

if (isNull _medic || {isNull _patient}) exitWith {};
private _partIndex = ["head", "body", "leftarm", "rightarm", "leftleg", "rightleg"] find (toLowerANSI _bodyPart);
if !(_partIndex in [2, 3, 4, 5]) exitWith {};

if (!(((missionNamespace getVariable ["ACME_hc_descriptors", false]) isEqualTo true))) exitWith {
    _this call ACM_disability_fnc_inspectForFracture
};

// Read the action's captured patient and limb. Menu focus can change during the assessment.
// ACM disability/functions/fnc_inspectForFracture.sqf:29-59 supplies the native precedence.
private _read = {
    params ["_key", "_default"];
    private _values = _patient getVariable [_key, []];
    if !(_values isEqualType []) exitWith {_default};
    _values param [_partIndex, _default, [_default]]
};
private _fractureState = ["ACM_disability_Fracture_State", 0] call _read;
private _bodyPartDamage = ["ace_medical_bodyPartDamage", 0] call _read;
private _splint = ["ACM_disability_SplintStatus", 0] call _read;
private _aceFracture = ["ace_medical_fractures", 0] call _read;
private _prepared = ["ACM_disability_Fracture_Prepared", false] call _read;

// ACM main/script_macros.hpp:427-429 defines mild=1, severe=2 and complex=3.
// All three ACM grades are actual fractures. An ACE-positive fracture can also exist
// without an ACM grade when severity is disabled; it still reports crepitus in this register.
// Neither case invents a fracture from body-part damage alone.
// ACE medical_treatment/functions/fnc_splintLocal.sqf:25-27 uses -1 for a treated fracture.
private _key = switch (true) do {
    case (_splint > 0): {"STR_ACM_Disability_InspectForFracture_SplintApplied"};
    case (_aceFracture == -1): {"STR_ACME_Disability_InspectForFracture_Stabilized"};
    case (_fractureState == 3): {"STR_ACM_Disability_InspectForFracture_SignificantSwelling"};
    case (_fractureState == 2): {"STR_ACM_Disability_InspectForFracture_Swelling"};
    case (_fractureState == 1): {"STR_ACM_Disability_InspectForFracture_SevereBruising"};
    case (_aceFracture > 0): {"STR_ACME_Disability_InspectForFracture_Confirmed"};
    case (!(_fractureState in [0, 1, 2, 3])): {"STR_ACME_Disability_InspectForFracture_Indeterminate"};
    case (_bodyPartDamage > 1): {"STR_ACM_Disability_InspectForFracture_Bruised"};
    default {"STR_ACM_Disability_InspectForFracture_NoInjury"};
};

private _bodyPartString = [_bodyPart, "display"] call ACME_fnc_bodyPartName;
private _hint = format [[_key] call ACME_fnc_clinTerm, toLower _bodyPartString];
private _hintLog = [_key + "_Short"] call ACME_fnc_clinTerm;
private _hintHeight = 3;

// Preserve realignment history without reporting a healed fracture or clearing its severity.
if (_prepared) then {
    _hint = format ["%1<br />%2", _hint, ["STR_ACM_Disability_InspectForFracture_RealignmentPerformed"] call ACME_fnc_clinTerm];
    _hintLog = format ["%1, %2", _hintLog, ["STR_ACM_Disability_InspectForFracture_RealignmentPerformed_Short"] call ACME_fnc_clinTerm];
    _hintHeight = 3.5;
};

// Emit one hint and one native quick-view entry, as the original callback does.
// ACE medical_treatment/functions/fnc_addToLog.sqf:23-25 routes remote-patient logs to their owner.
[_hint, _hintHeight, _medic] call ace_common_fnc_displayTextStructured;
[_patient, "quick_view", localize "STR_ACM_Disability_InspectForFracture_ActionLog", [[_medic, false, true] call ace_common_fnc_getName, toLower _bodyPartString, _hintLog]] call ace_medical_treatment_fnc_addToLog;
