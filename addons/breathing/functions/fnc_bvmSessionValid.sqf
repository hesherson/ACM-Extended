#include "..\script_component.hpp"
// ACM's BVM_Medic reserves the patient even while breaths are paused. Recover only an
// unavailable provider; replicated cleanup tokens and clocks do not decide who is active.
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient} || {!alive _medic}
    || {!([_medic] call ACEFUNC(common,isAwake))}) exitWith {false};
((_patient getVariable [QGVAR(BVM_Medic), objNull]) isEqualTo _medic)
    && {(objectParent _medic) isEqualTo (objectParent _patient)}
    && {(_medic distance2D _patient) <= ACEGVAR(medical_gui,maxDistance)}
