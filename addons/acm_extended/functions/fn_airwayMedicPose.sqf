// Compatibility entry for old callers. Only the exact assessment class owns the new bounded sequence.
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_bodyPart", "", [""]], ["_classname", "", [""]]];
if ((toLowerANSI _classname) != "checkairway") exitWith {};
if ((_medic getVariable ["ACME_assessment", []]) isNotEqualTo []) exitWith {};
_this call ACME_fnc_assessmentStart;
