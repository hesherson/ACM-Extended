/* The Hardigg body origin is on its feet, with the cover facing model +Y. */
params ["_object", "_base", "_heading", "_part", ["_normal", [0, 0, 1]], ["_apply", true]];
// Preserve the forward direction of chests already placed in missions.
private _front = [-(cos _heading), sin _heading, 0];
private _vertical = [0, 0, 1];
private _position = _base;
// The ground it stands on (fn_medicalChestRest.sqf); something too steep to be ground counts as level.
private _ground = [_vertical, vectorNormalized _normal] select ((_normal select 2) > 0.7);
// The chest and its cabinet stand on their feet on that ground: up is the ground's normal, and the cover faces
// the way it always did, laid into the ground's plane.
private _up = _ground;
private _dir = vectorNormalized (_front vectorDiff (_ground vectorMultiply (_front vectorDotProduct _ground)));
private _surface = _dir;
if (_part == "lid") then {
    _surface = _ground;
    _dir = _surface;
    _up = vectorNormalized ((_surface vectorMultiply (_front vectorDotProduct _surface)) vectorDiff _front);
    private _innerEdge = (0 boundingBoxReal _object) select 0 select 1;
    _position = _base vectorAdd [0, 0, (0.008 - _innerEdge) / (_surface select 2)];
};
if (_apply) then {
    _object setVectorDirAndUp [_dir, _up];
    _object setPosWorld _position;
};
[_position, _dir, _up, _surface]
