#include "..\script_component.hpp"
/*
 * Author: ACM Extended Fork
 * Core-owned mutation endpoint for the shared continuous-action controller.
 *
 * Mission-level controller fields are local to the provider machine. Provider session/heartbeat fields may be
 * published because server-side stale-hold reconciliation reads them.
 *
 * Arguments:
 * 0: Provider <OBJECT> (objNull is valid for mission-only changes)
 * 1: Changes <ARRAY> of [field,value]
 * 2: Public provider fields <BOOL> (default true)
 *
 * Supported mission fields:
 *   active, epoch, isDialog, shouldReopen, pfh, openMedicalMenuID, cancelEscapeID, controller
 * Supported provider fields:
 *   session, lastSeen
 */
params [
    ["_medic", objNull, [objNull]],
    ["_changes", [], [[]]],
    ["_public", true, [true]]
];

private _applied = 0;
{
    if !(_x isEqualType [] && {count _x >= 2}) then {continue;};
    _x params ["_field", "_value"];
    switch (_field) do {
        case "active": { missionNamespace setVariable [QGVAR(ContinuousAction_Active), _value]; _applied = _applied + 1; };
        case "epoch": { missionNamespace setVariable [QGVAR(ContinuousAction_Epoch), _value]; _applied = _applied + 1; };
        case "isDialog": { missionNamespace setVariable [QGVAR(ContinuousAction_IsDialog), _value]; _applied = _applied + 1; };
        case "shouldReopen": { missionNamespace setVariable [QGVAR(ContinuousAction_ShouldReopen), _value]; _applied = _applied + 1; };
        case "pfh": { missionNamespace setVariable [QGVAR(ContinuousAction_PFH), _value]; _applied = _applied + 1; };
        case "controller": { missionNamespace setVariable [QGVAR(ContinuousAction_Controller), _value]; _applied = _applied + 1; };
        case "openMedicalMenuID": { missionNamespace setVariable [QGVAR(ContinuousAction_OpenMedicalMenu_ID), _value]; _applied = _applied + 1; };
        case "cancelEscapeID": { missionNamespace setVariable [QGVAR(ContinuousAction_Cancel_EscapeID), _value]; _applied = _applied + 1; };
        case "session": {
            if (!isNull _medic) then {
                _medic setVariable [QGVAR(ContinuousAction_Session), _value, _public];
                _applied = _applied + 1;
            };
        };
        case "lastSeen": {
            if (!isNull _medic) then {
                _medic setVariable [QGVAR(ContinuousAction_LastSeen), _value, _public];
                _applied = _applied + 1;
            };
        };
    };
} forEach _changes;
_applied
