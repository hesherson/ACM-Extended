/* The original stencils sit on the vanilla surfaces. Cast against the
   rendered mesh so the panel ribs and handle recesses set their depth. */
params ["_object", "_title", "_sides", ["_flat", false]];
(boundingBoxReal _object) params ["_min", "_max"];
private _origin = getPosWorld _object;
private _bounds = [];
{
    private _xPos = _x;
    {
        private _yPos = _x;
        {_bounds pushBack (_object modelToWorldWorld [_xPos, _yPos, _x]);}
            forEach [_min select 2, _max select 2];
    } forEach [_min select 1, _max select 1];
} forEach [_min select 0, _max select 0];

private _heading = _object getVariable "ACME_medicalChestHeading";
private _forward = [sin _heading, cos _heading, 0];
private _right = [cos _heading, -(sin _heading), 0];
private _up = [0, 0, 1];
private _low = selectMin (_bounds apply {_x select 2});
private _high = selectMax (_bounds apply {_x select 2});
_origin set [2, (_low + _high) * 0.5];
private _surfaces = [];
if (_title) then {
    private _normal = if (_flat) then {_up} else {_forward};
    private _vertical = if (_flat) then {_forward} else {_up};
    _surfaces pushBack ["chest_title", _normal, _vertical,
        _origin vectorAdd (_vertical vectorMultiply (if (_flat) then {0} else {(_high - _low) * 0.19})), 0.12];
};
if (_sides) then {
    {
        _surfaces pushBack ["chest_cross", _right vectorMultiply _x, _up,
            _origin vectorAdd (_forward vectorMultiply 0.11), 0.04];
    } forEach [-1, 1];
};

private _decals = [];
{
    _x params ["_asset", "_normal", "_vertical", "_center", "_radius"];
    private _tangent = _normal vectorCrossProduct _vertical;
    private _depth = -1e6;
    {
        private _v = _x;
        {
            private _sample = (_center vectorAdd (_vertical vectorMultiply _v)) vectorAdd (_tangent vectorMultiply _x);
            private _reach = _normal vectorMultiply 1.25;
            private _hits = lineIntersectsSurfaces [
                _sample vectorAdd _reach, _sample vectorDiff _reach, objNull, objNull, true, -1, "VIEW", "GEOM"
            ];
            private _i = _hits findIf {(_x select 2) isEqualTo _object || {(_x select 3) isEqualTo _object}};
            if (_i >= 0) then {
                _depth = _depth max (((_hits select _i select 0) vectorDiff _center) vectorDotProduct _normal);
            };
        } forEach [-_radius, 0, _radius];
    } forEach [-_radius * 0.44, 0, _radius * 0.44];
    if (_depth < -1e5) then {
        _depth = selectMax (_bounds apply {(_x vectorDiff _center) vectorDotProduct _normal});
    };
    private _position = _center vectorAdd (_normal vectorMultiply (_depth + 0.0015));
    private _decal = createSimpleObject [format ["\acm_extended\data\medical_chest\%1.p3d", _asset], _position, false];
    if (!isNull _decal) then {
        _decal setVectorDirAndUp [_normal, _vertical];
        _decals pushBack _decal;
    };
} forEach _surfaces;
_decals
