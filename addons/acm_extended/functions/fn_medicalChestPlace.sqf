/* Fit the case to the floor, using bounds to detect a model authored flat. */
params ["_object", "_base", "_heading", ["_upright", true]];
(boundingBoxReal _object) params ["_min", "_max"];
private _extent = _max vectorDiff _min;
private _forward = [sin _heading, cos _heading, 0];
private _up = [0, 0, 1];
private _laidBack = (_extent select 2) < (_extent select 1) min (_extent select 0);
private _bottom = _min select 2;
if (_upright && {_laidBack}) then {
    _up = _forward;
    _forward = [0, 0, 1];
    _bottom = _min select 1;
};
if (!_upright && {!_laidBack}) then {
    _up = _forward;
    _forward = [0, 0, 1];
    _bottom = _min select 1;
};
_object setVariable ["ACME_medicalChestHeading", _heading];
_object setVectorDirAndUp [_forward, _up];
_object setPosWorld (_base vectorAdd [0, 0, 0.008 - _bottom]);
