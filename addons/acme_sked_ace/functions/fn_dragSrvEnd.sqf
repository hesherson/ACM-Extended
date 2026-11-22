/*
 * Server: a drag is over (let go, or the rescuer is dead, out, gone). The target is free again. If the rescuer's
 * machine could not put it down itself, it is put down here.
 * Arguments: 0: rescuer.
 */
params ["_unit"];
if (!isServer || {isNull _unit}) exitWith {};
private _target = _unit getVariable ["acme_drag_target", objNull];
_unit setVariable ["acme_drag_target", nil, true];
if (isNull _target) exitWith {};
if ((_target getVariable ["acme_drag_by", objNull]) isNotEqualTo _unit) exitWith {};
// The rescuer's machine sets the target down itself. If it could not (the rescuer is gone), it is done here.
// a second rescuer at its foot end lets go with him
private _rear = _target getVariable ["acme_carry_rear", objNull];
if (!isNull _rear) then {[_rear] call acme_sked_fnc_carrySrvEnd;};
_target setVariable ["acme_carry_rear", nil, true];
[_target, _unit] call acme_sked_fnc_dragFree;
private _clone = _target getVariable ["acme_drag_clone", objNull];
if (!isNull _clone) then {
    // a dead body was being dragged as ACE's clone of it: the body comes back where the clone is
    [_clone, _unit] call acme_sked_fnc_dragFree;
    [_unit, _clone, false] call ace_dragging_fnc_deleteClone;
    _target setVariable ["acme_drag_clone", nil, true];
};
_target setVariable ["acme_drag_by", nil, true];
[objNull, _target, true] call ace_common_fnc_claim;
["drag ended", _target, _unit, []] call acme_sked_fnc_traceTransport;
