#include "..\script_component.hpp"
/*
 * Author: Mazinski, Inferno
 * Shows the eye shield overlay on the local machine for the given eye control
 *
 * Arguments:
 * 0: Eye display IDC <NUMBER>
 *
 * Return Value:
 * None
 *
 * Public: No
 */

params ["_eyeDisplay"];
if (!hasInterface || {!(_eyeDisplay in [17102,17103])}) exitWith {};

private _display = uiNamespace getVariable ["ACM_EyeShield", displayNull];
if (isNull _display) then {
    uiNamespace setVariable [QGVAR(shownShieldEye),-1];
    "ACM_EyeShield" cutRsc ["ACM_EyeShield", "PLAIN", 0, true];
    _display = uiNamespace getVariable ["ACM_EyeShield", displayNull];
};
if (isNull _display) exitWith {};
if ((uiNamespace getVariable [QGVAR(shownShieldEye),-1]) == _eyeDisplay) exitWith {};
uiNamespace setVariable [QGVAR(shownShieldEye),_eyeDisplay];

{(_display displayCtrl _x) ctrlShow false;} forEach [17102,17103];
private _activeEye = _display displayCtrl _eyeDisplay;
_activeEye ctrlShow true;
_activeEye ctrlCommit 0;
