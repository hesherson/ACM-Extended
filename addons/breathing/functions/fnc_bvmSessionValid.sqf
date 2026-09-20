#include "..\script_component.hpp"
// A paused BVM still reserves the patient. isUsingBVM only describes active breaths.
// The server watchdog owns expiry using heartbeat receive times, never a remote clock.
params ["_medic", "_patient"];
if (isNull _medic || {isNull _patient} || {!alive _medic}
    || {!([_medic] call ACEFUNC(common,isAwake))}) exitWith {false};
private _session = _patient getVariable [QGVAR(BVM_session), []];
(count _session == 2)
    && {(_session select 0) isEqualTo _medic}
    && {(_medic getVariable [QGVAR(BVM_patient), objNull]) isEqualTo _patient}
    && {(_medic getVariable [QGVAR(BVM_epoch), -1]) == (_session select 1)}
    && {(objectParent _medic) isEqualTo (objectParent _patient)}
    && {(_medic distance2D _patient) <= ACEGVAR(medical_gui,maxDistance)}
