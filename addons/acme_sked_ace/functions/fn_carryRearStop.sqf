/*
 * Where the second rescuer is local: he lets go of the foot end. Safe to call when he holds nothing.
 * Arguments: 0: rescuer, 1: tell the server <BOOL> (default: true).
 */
params ["_unit", ["_tell", true]];
private _pfh = _unit getVariable ["acme_carry_pfh", -1];
if (_pfh >= 0) then {
    [_pfh] call CBA_fnc_removePerFrameHandler;
    _unit setVariable ["acme_carry_pfh", nil];
};
[_unit, "forceWalk", "acme_carry", false] call ace_common_fnc_statusEffect_set;
[_unit, "blockSprint", "acme_carry", false] call ace_common_fnc_statusEffect_set;
[_unit] call acme_sked_fnc_carryBandEnd;
[_unit, "acme_carry", true] call acme_sked_fnc_dragPace;
if (_tell) then {[_unit, "carryRearEnd"] call acme_sked_fnc_request;};
