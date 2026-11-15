/* Derive the release direction from the visible cover on the closed model. */
params ["_chest", ["_previewPose", []]];
// Difference between the closed shell's front and the detached stock lid's front.
private _offset = 0.1222;
if (_previewPose isNotEqualTo []) exitWith {
    _previewPose params ["_center", "_forward", "_up"];
    [_center vectorAdd (_forward vectorMultiply _offset), _forward, _up]
};
private _center = getPosWorld _chest;
private _coverDirection = (_chest modelToWorldWorld [0, 1, 0]) vectorDiff _center;
_coverDirection set [2, 0];
private _forward = vectorNormalized _coverDirection;
private _up = [0, 0, 1] vectorCrossProduct _forward;
[_center vectorAdd (_forward vectorMultiply _offset), _forward, _up]
