/* All three cabinet models share a longitudinal X axis and a +Y front. */
params ["_object", "_base", "_heading", ["_faceDown", false]];
(boundingBoxReal _object) params ["_min", "_max"];
private _forward = [sin _heading, cos _heading, 0];
private _right = [cos _heading, -(sin _heading), 0];
private _bottom = _min select 0;
private _orientation = [_forward, _right vectorMultiply -1];
if (_faceDown) then {
    _orientation = [[0, 0, -1], _right];
    _bottom = -(_max select 1);
};
_object setVariable ["ACME_medicalChestHeading", _heading];
_object setPosWorld (_base vectorAdd [0, 0, 0.008 - _bottom]);
_object setVectorDirAndUp _orientation;
