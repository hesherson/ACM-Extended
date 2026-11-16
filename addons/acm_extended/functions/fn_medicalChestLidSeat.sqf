/* This origin is the center of the detached lid in the assembled Hardigg model. */
params ["_cabinetPose"];
_cabinetPose params ["_base", "", "", "_outward"];
private _position = _base vectorAdd (_outward vectorMultiply 0.1175) vectorAdd [0, 0, 0.416];
[_position, _outward, _outward vectorCrossProduct [0, 0, 1]]
