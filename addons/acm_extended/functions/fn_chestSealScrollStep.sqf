/* B224: lock the CORNER for this hover, not the wheel direction. Reverse input
 * reseals the same edge, clamped at zero; it cannot open the opposite edge.
 * A complete re-seal rearms clinical relief; partial reversal does not spam burps.
 * Return [frame, locked corner direction, fired, newly completed]. */
params [["_frame", 0, [0]], ["_openDir", 0, [0]], ["_fired", false, [false]], ["_delta", 0, [0]]];
if (!finite _frame) then {_frame = 0;};
_frame = (floor _frame) max 0 min 5;
if (!finite _delta || {_delta == 0}) exitWith {[_frame, _openDir, _fired, false]};
private _direction = [1, -1] select (_delta < 0);
if !(_openDir in [-1, 1]) then {_openDir = _direction;};
private _next = (_frame + ([1, -1] select (_direction != _openDir))) max 0 min 5;
private _complete = _next == 5 && {_frame < 5} && {!_fired};
if (_next == 0) then {_fired = false;};
[_next, _openDir, _fired || _complete, _complete]
