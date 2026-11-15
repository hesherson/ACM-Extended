/* The cabinet clears on the negative-Y side of the closed chest. */
params ["_chest"];
// Offset of the detached lid's origin from the closed chest's origin.
private _offset = 0.1222;
private _center = getPosWorld _chest;
private _outward = _center vectorDiff (_chest modelToWorldWorld [0, 1, 0]);
_outward set [2, 0];
private _forward = vectorNormalized _outward;
private _up = [0, 0, 1] vectorCrossProduct _forward;
[_center vectorAdd (_forward vectorMultiply _offset), _forward, _up]
