/* Place the native model on its support surface. */
params ["_object", "_base", "_heading", "_part", ["_normal", [0, 0, 1]], ["_closed", objNull], ["_apply", true]];
if (_part == "cabinet") then {_heading = (_heading + 180) % 360;};
(0 boundingBoxReal _object) params ["_min", "_max"];
private _extent = _max vectorDiff _min;
private _forward = [sin _heading, cos _heading, 0];
private _left = [-(cos _heading), sin _heading, 0];
private _vertical = [0, 0, 1];
private _dir = _forward;
private _up = _left;
private _bottom = _min select 0;
private _supportNormal = _vertical;

if (_part != "closed") then {
    (0 boundingBoxReal _closed) params ["_closedMin", "_closedMax"];
    private _closedExtent = _closedMax vectorDiff _closedMin;
    private _closedFaceY = (_closedExtent select 1) < (_closedExtent select 2);
    private _front = [_left, _forward] select _closedFaceY;
    if (_part == "cabinet") then {
        private _faceY = (_extent select 1) < (_extent select 2);
        private _drawerAxis = [1, 2] select _faceY;
        // Flip end over end around the drawer-face normal to keep its heading.
        if ((_extent select _drawerAxis) > (_extent select 0)) then {
            _dir = [[0, 0, -1], _front] select _faceY;
            _up = [_front, _vertical] select _faceY;
            _bottom = if (_faceY) then {_min select 2} else {-(_max select 1)};
        } else {
            _dir = [_vertical vectorCrossProduct _front, _front] select _faceY;
            _up = [_front, _front vectorCrossProduct _vertical] select _faceY;
            _bottom = -(_max select 0);
        };
    } else {
        // Rest the lid on its inner face so the paint is visible on top.
        if ((_normal select 2) > .7) then {_supportNormal = vectorNormalized _normal;};
        private _right = vectorNormalized (_front vectorCrossProduct _supportNormal);
        private _faceY = (_extent select 1) < (_extent select 2);
        _dir = [_right, _supportNormal] select _faceY;
        _up = [_supportNormal, _right vectorMultiply -1] select _faceY;
        _bottom = _min select ([2, 1] select _faceY);
    };
};

private _position = _base vectorAdd (_supportNormal vectorMultiply (0.008 - _bottom));
if (_apply) then {
    _object setVectorDirAndUp [_dir, _up];
    _object setPosWorld _position;
};
[_position, _dir, _up]
