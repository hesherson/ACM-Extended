#include "..\script_component.hpp"
// Retire animation re-entry and public ownership before any input/UI operation can fail.
params ["_medic", "_patient", "_epoch"];
private _ownsMedic = !isNull _medic && {(_medic getVariable [QGVAR(CPR_Epoch), -1]) == _epoch};
private _ownsLocal = (missionNamespace getVariable [QGVAR(CPR_LocalSession), []]) isEqualTo [_medic, _patient, _epoch];
if (_ownsMedic || {_ownsLocal && {!isNull _medic} && {local _medic}
    && {(_medic getVariable [QGVAR(CPR_Epoch), -1]) == -1}}) then {
    // The server may already have invalidated this epoch. Its local animation handler still needs removal.
    _medic setVariable [QGVAR(CPR_Loop), false];
    private _animEH = _medic getVariable [QGVAR(CPR_AnimEH), -1];
    _medic setVariable [QGVAR(CPR_AnimEH), -1];
    if (_animEH >= 0) then {_medic removeEventHandler ["AnimDone", _animEH];};
    _medic setVariable [QGVAR(CPR_StartedEpoch), -1];
};
[_medic, _patient, _epoch] call FUNC(cprRelease);
if (!_ownsLocal) exitWith {false};
GVAR(CPR_LocalSession) = [];
GVAR(loopCPR) = false;
GVAR(CPRActive) = false;
GVAR(CPRTarget) = objNull;
GVAR(SwapToBVM) = false;
GVAR(BVMActive) = false;
private _pfh = missionNamespace getVariable [QGVAR(CPR_ControllerPFH), -1];
GVAR(CPR_ControllerPFH) = -1;
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
{
    private _id = missionNamespace getVariable [_x, -1];
    missionNamespace setVariable [_x, -1];
    // CBA key handler IDs are strings; numeric comparisons abort cancellation.
    if (!(_id isEqualTo -1) && {!(_id isEqualTo "")}) then {[_id, "keydown"] call CBA_fnc_removeKeyHandler;};
} forEach [QGVAR(CPRCancel_EscapeID), QGVAR(CPRCancel_MouseID), QGVAR(CPRToggle_MouseID), QGVAR(CPRSwap_MouseID)];
[] call ACEFUNC(interaction,hideMouseHint);
true
