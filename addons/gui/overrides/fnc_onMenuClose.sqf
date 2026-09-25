#include "..\script_component.hpp"
/*
 * Author: joko // Jonas
 * Handles closing the Medical Menu. Called from onUnload event.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call ace_medical_gui_fnc_onMenuClose
 *
 * Public: No
 */

// Release while the original display still exists. Relying only on an added
// display Unload handler can miss teardown through other UI/mod close paths.
private _display = _this param [0, displayNull];
if (!isNull _display && {!isNil "ACME_fnc_menuPoseStop"}) then {
    private _owner = _display getVariable ["ACME_menuPoseOwner", []];
    if (count _owner == 2) then {[_owner select 0, false, _owner select 1] call ACME_fnc_menuPoseStop;};
};

if (ACEGVAR(interact_menu,menuBackground) == 1) then {[QACEGVAR(medical_gui,id), false] call ACEFUNC(common,blurScreen)};
if (ACEGVAR(interact_menu,menuBackground) == 2) then {(uiNamespace getVariable [QACEGVAR(interact_menu,menuBackground), displayNull]) closeDisplay 0};

// Keep the medical-menu lifecycle identical to ACE. Treatment buttons arm pendingReopen after their statement;
// manual closes never do. Direct Pressure no longer participates in this lifecycle at all.
ACEGVAR(medical_gui,pendingReopen) = false;
ACEGVAR(medical_gui,menuPFH) call CBA_fnc_removePerFrameHandler;
ACEGVAR(medical_gui,menuPFH) = -1;
