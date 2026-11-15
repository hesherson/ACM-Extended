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
private _footprintOffset = [0, 0, 0];
private _surfaceDirection = [_up, _dir] select ((_extent select 1) < (_extent select 2));

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

        // Match the rear of the covered and uncovered bodies across the model swap.
        _surfaceDirection = _front vectorMultiply -1;
        private _rear = 0;
        {
            private _projection = _x vectorDotProduct _surfaceDirection;
            private _edge = [_max, _min] select (_projection >= 0);
            _rear = _rear + _projection * (_edge select _forEachIndex);
        } forEach [_dir vectorCrossProduct _up, _dir, _up];
        private _closedRear = _closedMin select ([2, 1] select _closedFaceY);
        _footprintOffset = _surfaceDirection vectorMultiply (_closedRear - _rear);
    } else {
        // Rest the lid on its inner face so the paint is visible on top.
        if ((_normal select 2) > .7) then {_supportNormal = vectorNormalized _normal;};
        private _right = vectorNormalized (_forward vectorCrossProduct _supportNormal);
        private _faceY = (_extent select 1) < (_extent select 2);
        _surfaceDirection = _supportNormal;
        _dir = [_right, _supportNormal] select _faceY;
        _up = [_supportNormal, _right vectorMultiply -1] select _faceY;
        _bottom = _min select ([2, 1] select _faceY);
    };
};

// Moving along world Z preserves the planned landing coordinates even on a slope.
private _lift = (0.008 - _bottom) / (_supportNormal select 2);
private _position = _base vectorAdd _footprintOffset vectorAdd (_vertical vectorMultiply _lift);
if (_apply) then {
    _object setVectorDirAndUp [_dir, _up];
    _object setPosWorld _position;
};
[_position, _dir, _up, _surfaceDirection]
