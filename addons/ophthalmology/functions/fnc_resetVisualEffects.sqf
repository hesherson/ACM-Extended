#include "..\script_component.hpp"
/* Retire presentation belonging to the old controlled unit/clinical episode. */
GVAR(blinkGeneration) = (missionNamespace getVariable [QGVAR(blinkGeneration),0]) + 1;
if (!isNil QGVAR(ppBlurBlink)) then {
    GVAR(ppBlurBlink) ppEffectEnable false;
};
{
    if (!isNull _x) then {ctrlDelete _x;};
} forEach (uiNamespace getVariable [QGVAR(blinkControls),[]]);
uiNamespace setVariable [QGVAR(blinkControls),[controlNull,controlNull]];
[] call FUNC(hideEyeShieldOverlay);
[false,0] call FUNC(effectEyeInjury);
[false,[1,1]] call FUNC(effectHurtEye);
