#include "..\script_component.hpp"
// Paused CPR still reserves the patient. isPerformingCPR only describes active compressions.
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient} || {!alive _medic}
    || {!([_medic] call ACEFUNC(common,isAwake))}) exitWith {false};
private _session = _patient getVariable [QGVAR(CPR_session), []];
(count _session == 2)
    && {(_session select 0) isEqualTo _medic}
    && {(_medic getVariable [QGVAR(CPR_Patient), objNull]) isEqualTo _patient}
    && {(_medic getVariable [QGVAR(CPR_Epoch), -1]) == (_session select 1)}
    && {CBA_missionTime - (_medic getVariable [QGVAR(CPR_lastSeen), -100]) < 10}
    && {(objectParent _medic) isEqualTo (objectParent _patient)}
    && {(_medic distance2D _patient) <= ACEGVAR(medical_gui,maxDistance)}
