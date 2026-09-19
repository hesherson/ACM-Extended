#include "..\script_component.hpp"
// Release public ownership first, before any interface or input cleanup can fail.
params ["_medic", "_patient", "_epoch"];
[_medic, _patient, _epoch] call FUNC(bvmRelease);
if !((missionNamespace getVariable [QGVAR(BVM_LocalSession), []]) isEqualTo [_medic, _patient, _epoch]) exitWith {false};
GVAR(BVM_LocalSession) = [];
GVAR(BVMTarget) = objNull;
GVAR(BVMActive) = false;
GVAR(CPRActive) = false;
GVAR(SwapToCPR) = false;
GVAR(BVM_OxygenActive) = false;
GVAR(BVM_PortableOxygen) = false;
private _ownsController = (missionNamespace getVariable [QEGVAR(core,ContinuousAction_Epoch), -1]) == _epoch;
if (_ownsController) then {
    EGVAR(core,ContinuousAction_Active) = false;
    private _pfh = missionNamespace getVariable [QEGVAR(core,ContinuousAction_PFH), -1];
    if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
    EGVAR(core,ContinuousAction_PFH) = -1;
    private _escape = missionNamespace getVariable [QEGVAR(core,ContinuousAction_Cancel_EscapeID), -1];
    EGVAR(core,ContinuousAction_Cancel_EscapeID) = -1;
    if (!(_escape isEqualTo -1) && {!(_escape isEqualTo "")}) then {[_escape, "keydown"] call CBA_fnc_removeKeyHandler;};
};
{
    private _id = missionNamespace getVariable [_x, -1];
    missionNamespace setVariable [_x, -1];
    // CBA returns string IDs. Numeric comparisons abort cleanup on a live session.
    if (!(_id isEqualTo -1) && {!(_id isEqualTo "")}) then {[_id, "keydown"] call CBA_fnc_removeKeyHandler;};
} forEach [QGVAR(BVMCancel_MouseID), QGVAR(BVMToggle_MouseID), QGVAR(BVMSwap_MouseID)];
"ACM_UseBVM" cutText ["", "PLAIN", 0, false];
if (_ownsController) then {[] call ACEFUNC(interaction,hideMouseHint);};
_ownsController
