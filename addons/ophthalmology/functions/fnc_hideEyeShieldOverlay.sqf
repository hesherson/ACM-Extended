#include "..\script_component.hpp"
/*
 * Author: Mazinski, Inferno
 * Hides the eye shield overlay on the local machine
 *
 * Return Value:
 * None
 *
 * Public: No
 */

if ((uiNamespace getVariable [QGVAR(shownShieldEye),-1]) == -1
    && {isNull (uiNamespace getVariable ["ACM_EyeShield", displayNull])}) exitWith {};
uiNamespace setVariable [QGVAR(shownShieldEye),-1];
uiNamespace setVariable ["ACM_EyeShield",displayNull];
"ACM_EyeShield" cutText ["","PLAIN",0,true];
