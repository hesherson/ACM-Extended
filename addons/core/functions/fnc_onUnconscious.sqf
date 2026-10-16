#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle patient unconscious event. (LOCAL)
 *
 * Arguments:
 * 0: Patient <OBJECT>
 * 1: Unconscious State <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, true] call ACM_core_fnc_onUnconscious;
 *
 * Public: No
 */

params ["_patient", "_state"];
private _acmeBinding = "NA4:onUnconscious";
if (_patient getVariable ["ACME_clinicalRestoring", false]) exitWith {};

if (!local _patient) exitWith {};

// A fresh unconscious episode invalidates any earlier deferred wake request.
if (_state) then {
    _patient setVariable ["ACME_wakeRepairTicket", (_patient getVariable ["ACME_wakeRepairTicket", 0]) + 1, false];
};

if !(_state) then {
    if (_patient getVariable [QGVAR(WasTreated), false]) then {
        _patient setVariable [QGVAR(Lying_State), true, true];
        _patient setVariable [QGVAR(WasTreated), false, true];
    };

    if ((_patient getVariable [QGVAR(Lying_State), false]) && (((animationState _patient) in LYING_ANIMATION) || !(isNull (objectParent _patient)))) then {
        [QGVAR(getUpPrompt), [_patient], _patient] call CBA_fnc_targetEvent;
    };

    _patient setVariable [QEGVAR(breathing,BVM_lastBreath), -1, true];
} else {
    [_patient] call ACEFUNC(weaponselect,putWeaponAway);
    [_patient] call FUNC(handleKnockOut);

    if !(_patient getVariable [QGVAR(WasWounded), false]) then {
        _patient setVariable [QGVAR(WasWounded), true, true];
    };
};

// B224 presentation runs only after the actual wake edge and existing awake-state bookkeeping.
if (!isNil "ACME_fnc_wakeAnimationEvent") then {[_patient,_state] call ACME_fnc_wakeAnimationEvent;};

// Compose ACME medical lying protection with ACE's unconscious reason.
if (!isNil "ACME_fnc_aiProtectionSync") then {[_patient] call ACME_fnc_aiProtectionSync;};
