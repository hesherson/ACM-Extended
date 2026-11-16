/*
 * Server: turn ACE body drag and carry off for a casualty going into a SKED, keeping what they had (once).
 * Arguments: 0: casualty.
 */
params ["_patient"];
if (isNil {_patient getVariable "acme_sked_prevDrag"}) then {
    _patient setVariable ["acme_sked_prevDrag", [
        _patient getVariable ["ace_dragging_canDrag", true],
        _patient getVariable ["ace_dragging_dragPosition", [0, 1.1, 0.092]],
        _patient getVariable ["ace_dragging_dragDirection", 180],
        _patient getVariable ["ace_dragging_canCarry", true],
        _patient getVariable ["ace_dragging_carryPosition", [0.4, -0.1, -1.25]],
        _patient getVariable ["ace_dragging_carryDirection", 195]
    ], true];
};
[_patient, false, nil, nil, nil, true] call ace_dragging_fnc_setDraggable;
[_patient, false, nil, nil, nil, true] call ace_dragging_fnc_setCarryable;
