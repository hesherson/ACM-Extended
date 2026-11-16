/*
 * Server: give a casualty coming out of a SKED their ACE body drag and carry back as they were.
 * Arguments: 0: casualty.
 */
params ["_patient"];
(_patient getVariable ["acme_sked_prevDrag", [true, [0, 1.1, 0.092], 180, true, [0.4, -0.1, -1.25], 195]])
    params ["_canDrag", "_dragPos", "_dragDir", "_canCarry", "_carryPos", "_carryDir"];
_patient setVariable ["acme_sked_prevDrag", nil, true];
[_patient, _canDrag, _dragPos, _dragDir, false, true] call ace_dragging_fnc_setDraggable;
[_patient, _canCarry, _carryPos, _carryDir, false, true] call ace_dragging_fnc_setCarryable;
