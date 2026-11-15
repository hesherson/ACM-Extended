/* Position the detached lid on the closed chest's cover plane. */
params ["_chest", "_cabinetPose"];
private _outward = _cabinetPose select 3;
private _side = [0, 0, 1] vectorCrossProduct _outward;
// Offset of the detached lid's origin from the closed chest's origin.
[getPosWorld _chest vectorAdd (_outward vectorMultiply 0.1222), _outward, _side]
