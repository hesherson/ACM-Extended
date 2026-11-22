/*
 * Server: a second rescuer takes the foot end of a litter that is being dragged by its head end.
 * Arguments: 0: rescuer, 1: litter.
 */
params ["_unit", "_litter"];
if (!isServer || {!([_unit, _litter] call acme_sked_fnc_carryCan)}) exitWith {};
_litter setVariable ["acme_carry_rear", _unit, true];
_unit setVariable ["acme_carry_litter", _litter, true];
["foot end lifted", _litter, _unit, []] call acme_sked_fnc_traceTransport;
[_unit, "carryRearLocal", [_unit, _litter]] call acme_sked_fnc_sendLocal;
