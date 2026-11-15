/* Seat the separate lid at the painted face of the closed model. */
params ["_chest", "_lid", "_heading"];
private _forward = [sin _heading, cos _heading, 0];
private _up = [-(cos _heading), sin _heading, 0];
private _shellFront = (0 boundingBoxReal _chest) select 1 select 1;
private _lidFront = (0 boundingBoxReal _lid) select 1 select 1;
private _position = getPosWorld _chest vectorAdd (_forward vectorMultiply (_shellFront - _lidFront));
[_position, _forward, _up]
