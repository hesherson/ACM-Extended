#include "..\script_component.hpp"
/*
 * Author: BaerMitUmlaut
 * Makes the unit heal itself.
 *
 * Arguments:
 * Unit <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * cursorObject call ace_medical_ai_fnc_healSelf
 *
 * Public: No
 */

// B219: explicitly marked training casualties cannot start autonomous healing or movement.
// Other AI retain ACM's native lying-state and treatment logic below.
if (_this getVariable ["ACME_trainingCrouchOnly",false]) exitWith {
    _this setVariable [QACEGVAR(medical_ai,currentTreatment),nil];
};

// Player will have to do this manually of course
if ([_this] call ACEFUNC(common,isPlayer)) exitWith {};
// Can't heal self when unconscious
if (IS_UNCONSCIOUS(_this) || IN_LYING_STATE(_this)) exitWith {
    _this setVariable [QACEGVAR(medical_ai,currentTreatment), nil];
};

[_this, _this] call ACEFUNC(medical_ai,healingLogic);
