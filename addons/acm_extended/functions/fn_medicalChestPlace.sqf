/* Fit the case to the floor, using bounds to detect a model authored flat. */
params ["_object", "_base", "_heading", ["_upright", true]];
(boundingBoxReal _object) params ["_min", "_max"];
private _extent = _max vectorDiff _min;
private _forward = [sin _heading, cos _heading, 0];
private _up = [0, 0, 1];
private _right = [cos _heading, -(sin _heading), 0];
private _laidBack = (_extent select 2) < (_extent select 1) min (_extent select 0);
private _longAxisX = (_object isKindOf "ACME_MedicalChest")
    || {(_extent select 0) > 1.25 * ((_extent select 1) max (_extent select 2))};
private _bottom = _min select 2;
if (_upright) then {
    if (_longAxisX) then {
        _up = _right vectorMultiply -1;
        _bottom = _min select 0;
    } else {
        if (_laidBack) then {
            _up = _forward;
            _forward = [0, 0, 1];
            _bottom = _min select 1;
        };
    };
};
if (!_upright) then {
    _up = _right;
    _forward = [0, 0, 1];
    _bottom = _min select 1;
};
_object setVariable ["ACME_medicalChestHeading", _heading];
_object setVectorDirAndUp [_forward, _up];
_object setPosWorld (_base vectorAdd [0, 0, 0.008 - _bottom]);
