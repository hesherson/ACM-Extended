/* Read-only proximity to the measured volume endpoint. Smoothstep peaks at +35%, never moves a tick. */
params ["_fraction","_markFraction","_count"];
if (_fraction < 0 || {_count < 2}) exitWith {1};
private _radius = 0.7 / ((_count - 1) max 1);
private _near = (1 - abs (_fraction - _markFraction) / _radius) max 0 min 1;
1 + 0.35 * (_near * _near * (3 - 2 * _near))
