/* This origin is the center of the detached lid in the assembled Hardigg model. */
params ["_cabinetPose"];
_cabinetPose params ["_base", "", ["_up", [0, 0, 1]], "_outward"];
// (along the cabinet's own axes: it leans with the ground it stands on)
private _position = _base vectorAdd (_outward vectorMultiply 0.1175) vectorAdd (_up vectorMultiply 0.416);
[_position, _outward, _outward vectorCrossProduct _up, _up]
