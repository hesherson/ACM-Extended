/* Place the native model and return the matching frame for the fitted finish. */
params ["_object", "_base", "_heading", "_part", ["_normal", [0, 0, 1]], ["_closed", objNull]];
(0 boundingBoxReal _object) params ["_min", "_max"];
private _extent = _max vectorDiff _min;
private _forward = [sin _heading, cos _heading, 0];
private _left = [-(cos _heading), sin _heading, 0];
private _vertical = [0, 0, 1];
private _dir = _forward;
private _up = _left;
private _bottom = _min select 0;
private _finishDir = _dir;
private _finishUp = _up;
private _finishOffset = [0, 0, 0];
private _supportNormal = _vertical;

if (_part != "closed") then {
    (0 boundingBoxReal _closed) params ["_closedMin", "_closedMax"];
    private _closedExtent = _closedMax vectorDiff _closedMin;
    private _closedFaceY = (_closedExtent select 1) < (_closedExtent select 2);
    private _front = [_left, _forward] select _closedFaceY;
    if (_part == "cabinet") then {
        private _faceY = (_extent select 1) < (_extent select 2);
        private _drawerAxis = [1, 2] select _faceY;
        if ((_extent select _drawerAxis) > (_extent select 0)) then {
            // Rolling the sideways drawer bank puts drawer 1 at the top.
            _dir = [_vertical, _front] select _faceY;
            _up = [_front, [0, 0, -1]] select _faceY;
            _bottom = if (_faceY) then {-(_max select 2)} else {_min select 1};
        } else {
            _dir = [_front vectorCrossProduct _vertical, _front] select _faceY;
            _up = [_front, _vertical vectorCrossProduct _front] select _faceY;
        };
        _finishOffset = [0, 0, _bottom - (_closedMin select 0)];
    } else {
        // The broad painted face rests against the floor or local ground slope.
        if ((_normal select 2) > .7) then {_supportNormal = vectorNormalized _normal;};
        private _down = _supportNormal vectorMultiply -1;
        private _right = vectorNormalized (_front vectorCrossProduct _supportNormal);
        private _faceY = (_extent select 1) < (_extent select 2);
        _dir = [_right vectorMultiply -1, _down] select _faceY;
        _up = [_down, _right] select _faceY;
        _bottom = -(_max select ([2, 1] select _faceY));
        _finishDir = [_right vectorMultiply -1, _down] select _closedFaceY;
        _finishUp = [_down, _right] select _closedFaceY;
    };
};

_object setVariable ["ACME_medicalChestHeading", _heading];
_object setVectorDirAndUp [_dir, _up];
_object setPosWorld (_base vectorAdd (_supportNormal vectorMultiply (0.008 - _bottom)));
if (_part == "closed") exitWith {[]};
[(_object modelToWorldWorld [0, 0, 0]) vectorAdd _finishOffset, _finishDir, _finishUp]
