/*
 * Where the second rescuer is local: he has the foot end of a litter that another rescuer drags by its head end
 * (the Talon). He walks by himself; the litter is laid between the two on the first rescuer's machine
 * (fn_dragLocal.sqf), and the rubber band (fn_carryBand.sqf) holds him to the first one's pace. He lets go
 * when he is told to, when either of them cannot go on, or when they are torn 0.9 m apart.
 * Arguments: 0: rescuer, 1: litter.
 */
params ["_unit", "_litter"];
if (!local _unit || {isNull _litter}) exitWith {};
if ((_unit getVariable ["acme_carry_litter", objNull]) isNotEqualTo _litter) exitWith {[_unit, "carryRearEnd"] call acme_sked_fnc_request;};
if (!isNil {_unit getVariable "acme_carry_pfh"}) then {[_unit, false] call acme_sked_fnc_carryRearStop;};
[_unit, "forceWalk", "acme_carry", true] call ace_common_fnc_statusEffect_set;
[_unit, "blockSprint", "acme_carry", true] call ace_common_fnc_statusEffect_set;
private _pfh = [{
    params ["_args"];
    _args params ["_unit", "_litter"];
    private _lead = if (isNull _litter) then {objNull} else {_litter getVariable ["acme_drag_by", objNull]};
    if (isNull _unit || {!alive _unit} || {!local _unit} || {_unit getVariable ["ACE_isUnconscious", false]} || {!isNull objectParent _unit}
        || {isNull _lead} || {!alive _lead}
        || {(_litter getVariable ["acme_carry_rear", objNull]) isNotEqualTo _unit}
        || {_unit getVariable ["ace_dragging_isDragging", false]} || {_unit getVariable ["ace_dragging_isCarrying", false]}) exitWith {
        [_unit, true] call acme_sked_fnc_carryRearStop;
    };
    [_unit, "acme_carry"] call acme_sked_fnc_dragPace;
    private _stretch = [_unit, _lead, _litter, false] call acme_sked_fnc_carryBand;
    if (_stretch > 0.9 || {_stretch < -1.4}) then {[_unit, true] call acme_sked_fnc_carryRearStop;};
}, 0, [_unit, _litter]] call CBA_fnc_addPerFrameHandler;
_unit setVariable ["acme_carry_pfh", _pfh];
