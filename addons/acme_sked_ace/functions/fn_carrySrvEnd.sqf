/*
 * Server: the second rescuer no longer has the foot end of his litter (he let go, or cannot go on, or the drag
 * is over). The litter goes on as a drag by one, its foot end on the ground.
 * Arguments: 0: rescuer.
 */
params ["_unit"];
if (!isServer || {isNull _unit}) exitWith {};
private _litter = _unit getVariable ["acme_carry_litter", objNull];
_unit setVariable ["acme_carry_litter", nil, true];
if (!isNull _litter && {(_litter getVariable ["acme_carry_rear", objNull]) isEqualTo _unit}) then {
    _litter setVariable ["acme_carry_rear", nil, true];
    ["foot end set down", _litter, _unit, []] call acme_sked_fnc_traceTransport;
};
[_unit, "carryRearStop", [_unit, false]] call acme_sked_fnc_sendLocal;
