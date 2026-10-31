#include "..\script_component.hpp"
/*
 * Author: Inferno
 * Clear ophthalmology dust and irritation state.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Public: No
 */

params ["_patient", ["_epoch", -1], ["_hops",0]];
if (isNull _patient) exitWith {};
if (_epoch < 0) then {_epoch = _patient getVariable ["ACME_clinicalEpoch", 0];};
if (!local _patient) exitWith {
    if (_hops < 4) then {
        [QGVAR(clearEyeInjury), [_patient, _epoch, _hops + 1], _patient] call CBA_fnc_targetEvent;
    };
};
// A late wash from before full-heal/respawn must not clear a replacement injury.
if (_epoch != (_patient getVariable ["ACME_clinicalEpoch", 0]) || {!alive _patient}) exitWith {};

_patient setVariable [QGVAR(dustInjuryLight), 0, true];
_patient setVariable [QGVAR(dustInjuryHeavy), 0, true];
