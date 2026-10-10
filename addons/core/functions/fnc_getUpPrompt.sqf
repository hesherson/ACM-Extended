#include "..\script_component.hpp"
/*
 * Author: Blue
 * Give interactions to get up
 *
 * Arguments:
 * 0: Unit <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_core_fnc_getUpPrompt;
 *
 * Public: No
 */

params ["_unit"];
private _acmeReconcile = "B106:getUpLifecycle";

if (ACE_player != _unit) exitWith {};

[LLSTRING(LyingState_GetUp), "", ""] call ACEFUNC(interaction,showMouseHint);

_unit setVariable [QGVAR(GetUpActionID), [0xF0, [false, false, false], {
    ACE_player call FUNC(getUp);
}, "keyup", "", false, 0] call CBA_fnc_addKeyHandler];

private _inVehicle = !(isNull (objectParent _unit));

[{
    params ["_unit", "_inVehicle"];

    private _anim = toLowerANSI animationState _unit;
    private _carryOwned = !isNull (attachedTo _unit) || {(_anim find "carried") >= 0};
    !(_unit getVariable [QGVAR(Lying_State), false]) || IS_UNCONSCIOUS(_unit) || !(alive _unit) || _carryOwned || (_inVehicle != !(isNull (objectParent _unit)));
}, {
    params ["_unit"];

    if ((animationState _unit != "AinjPfalMstpSnonWnonDf_carried_dead") || IS_UNCONSCIOUS(_unit) || !(alive _unit)) then {
        [] call ACEFUNC(interaction,hideMouseHint);

        if (alive _unit && (animationState _unit != "AinjPfalMstpSnonWnonDf_carried_dead") && !(IS_UNCONSCIOUS(_unit))) then {
            _unit setVariable [QGVAR(Lying_State), false, true];
            if (!isNil "ACME_fnc_aiProtectionSync") then {[_unit] call ACME_fnc_aiProtectionSync;};
        };
    };

    [_unit getVariable QGVAR(GetUpActionID), "keyup"] call CBA_fnc_removeKeyHandler;
    _unit setVariable [QGVAR(GetUpActionID), nil];
}, [_unit, _inVehicle], 3600, {}] call CBA_fnc_waitUntilAndExecute;
