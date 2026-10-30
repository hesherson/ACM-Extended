#include "..\script_component.hpp"
/*
 * Author: Mazinski, Inferno
 * Show a local blink effect.
 *
 * Arguments:
 * 0: Time <NUMBER>
 * 1: Shock blur <BOOL>
 *
 * Return Value:
 * None
 *
 * Public: No
 */

params ["_time", "_shock"];

if (isNull findDisplay 46) exitWith {};
GVAR(blinkGeneration) = (missionNamespace getVariable [QGVAR(blinkGeneration),0]) + 1;
private _generation = GVAR(blinkGeneration);
if (!_shock && {!isNil QGVAR(ppBlurBlink)}) then {GVAR(ppBlurBlink) ppEffectEnable false;};

private _controls = uiNamespace getVariable [QGVAR(blinkControls), [controlNull, controlNull]];
_controls params ["_upperLid", "_lowerLid"];

if (isNull _upperLid) then {
    _upperLid = findDisplay 46 ctrlCreate ["RscPicture", -1];
    _lowerLid = findDisplay 46 ctrlCreate ["RscPicture", -1];

    _upperLid ctrlSetText QPATHTOF(ui\UpperBlink.paa);
    _lowerLid ctrlSetText QPATHTOF(ui\LowerBlink.paa);

    _upperLid ctrlSetPosition [safeZoneXAbs, (safeZoneY - safeZoneH), safeZoneWAbs, safeZoneH];
    _lowerLid ctrlSetPosition [safeZoneXAbs, (safeZoneY + safeZoneH), safeZoneWAbs, safeZoneH];

    _upperLid ctrlSetFade 0;
    _lowerLid ctrlSetFade 0;

    _upperLid ctrlCommit 0;
    _lowerLid ctrlCommit 0;

    uiNamespace setVariable [QGVAR(blinkControls), [_upperLid, _lowerLid]];
};

_upperLid ctrlSetPosition [safeZoneXAbs, safeZoneY, safeZoneWAbs, safeZoneH];
_lowerLid ctrlSetPosition [safeZoneXAbs, safeZoneY, safeZoneWAbs, safeZoneH];

_upperLid ctrlCommit 0.04;
_lowerLid ctrlCommit 0.04;

if (_shock) then {
    if (isNil QGVAR(ppBlurBlink)) then {
        GVAR(ppBlurBlink) = ppEffectCreate ["DynamicBlur", 213706];
        GVAR(ppBlurBlink) ppEffectForceInNVG true;
    };

    GVAR(ppBlurBlink) ppEffectEnable true;
    GVAR(ppBlurBlink) ppEffectAdjust [0.4];
    GVAR(ppBlurBlink) ppEffectCommit 0.04;
};

[{
    params ["_upperLid", "_lowerLid", "_shock", "_time", "_generation"];
    if (_generation != GVAR(blinkGeneration) || {isNull _upperLid} || {isNull _lowerLid}) exitWith {};

    _upperLid ctrlSetPosition [safeZoneXAbs, (safeZoneY - safeZoneH), safeZoneWAbs, safeZoneH];
    _lowerLid ctrlSetPosition [safeZoneXAbs, (safeZoneY + safeZoneH), safeZoneWAbs, safeZoneH];

    if (_shock) then {
        _upperLid ctrlCommit 0.1;
        _lowerLid ctrlCommit 0.1;

        GVAR(ppBlurBlink) ppEffectAdjust [0];
        GVAR(ppBlurBlink) ppEffectCommit (_time * 4);

        [{
            params ["_generation"];
            if (_generation == GVAR(blinkGeneration)) then {GVAR(ppBlurBlink) ppEffectEnable false;};
        }, [_generation], (_time * 4)] call CBA_fnc_waitAndExecute;
    } else {
        _upperLid ctrlCommit 0.04;
        _lowerLid ctrlCommit 0.04;
    };
}, [_upperLid, _lowerLid, _shock, _time, _generation], _time] call CBA_fnc_waitAndExecute;
