/* Use the fitted drawer face to position the detached lid. */
params ["_chest", "_cabinetPose"];
_cabinetPose params ["", "_dir", "_up"];
// Stock drawer fronts face native -Z. An upright Y-facing cabinet uses its direction.
private _outward = [_up vectorMultiply -1, _dir] select (abs (_up select 2) > 0.7);
_outward set [2, 0];
private _forward = vectorNormalized _outward;
private _side = [0, 0, 1] vectorCrossProduct _forward;
// Offset of the detached lid's origin from the closed chest's origin.
[getPosWorld _chest vectorAdd (_forward vectorMultiply 0.1222), _forward, _side]
