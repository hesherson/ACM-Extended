/*
 * Where a rescuer is local: the rubber band (fn_carryBand.sqf) is off.
 * Arguments: 0: rescuer.
 */
params ["_unit"];
if !(_unit getVariable ["acme_carry_banded", false]) exitWith {};
_unit setVariable ["acme_carry_banded", nil];
_unit setVariable ["acme_carry_coef", nil];
[_unit] call acme_sked_fnc_paceApply;
