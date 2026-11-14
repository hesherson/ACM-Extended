/* The closed cabinet and detached lid have measured model-space paint positions.
   The open cabinet variants use their own rendered surfaces for placement. */
params ["_object", "_surface", ["_variant", 0]];
private _hasRetexture = _variant in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
private _markings = switch (_surface) do {
    case "closed": {[
        ["chest_title", [0, 0.1539, 0], [0, 1, 0], [1, 0, 0]],
        ["chest_serial", [-0.195, 0.154, -0.093], [0, 1, 0], [1, 0, 0]],
        ["chest_tape_lid", [0.197, 0.1536, 0.026], [0, 1, 0], [1, 0, 0]],
        ["chest_cross", [0, -0.063, 0.2665], [0, 0, 1], [1, 0, 0]],
        ["chest_cross", [0, -0.063, -0.2665], [0, 0, -1], [1, 0, 0]],
        ["chest_cross", [0.4168, -0.075, 0.161], [1, 0, 0], [0, 0, -1]],
        ["chest_tape_side", [0.275, -0.068, 0.2662], [0, 0, 1], [1, 0, 0]],
        ["chest_tape_back", [0, -0.1617, -0.022], [0, -1, 0], [1, 0, 0]]
    ]};
    case "lid": {[
        ["chest_title", [0, 0.0319, 0], [0, 1, 0], [1, 0, 0]],
        ["chest_serial", [-0.195, 0.0319, -0.093], [0, 1, 0], [1, 0, 0]],
        ["chest_tape_lid", [0.197, 0.0319, 0.026], [0, 1, 0], [1, 0, 0]]
    ]};
    default {[]};
};

if (_hasRetexture) then {
    // These fitted finishes include their own paint and wear on every face.
    _markings = [];
};

private _placements = _markings apply {
    _x params ["_asset", "_point", "_normal", "_vertical"];
    [_asset, _object modelToWorldWorld _point, _object vectorModelToWorld _normal, _object vectorModelToWorld _vertical]
};

if (_surface == "cabinet") then {
    (boundingBoxReal _object) params ["_min", "_max"];
    private _center = _object modelToWorldWorld ((_min vectorAdd _max) vectorMultiply 0.5);
    private _heading = _object getVariable "ACME_medicalChestHeading";
    private _forward = [sin _heading, cos _heading, 0];
    private _right = [cos _heading, -(sin _heading), 0];
    private _up = [0, 0, 1];
    private _body = _center vectorAdd (_forward vectorMultiply -0.063);
    private _cross = ["chest_cross", "chest_cross_red"] select (_variant == 10);
    private _strips = [
        [_cross, _right, _up, _body, 0.052, 0.052],
        [_cross, _right vectorMultiply -1, _up, _body, 0.052, 0.052],
        ["chest_tape_side", _right vectorMultiply -1, _up, _body vectorAdd [0, 0, 0.275], 0.051, 0.0165],
        ["chest_tape_back", _forward vectorMultiply -1, _up, _center vectorAdd (_right vectorMultiply 0.022), 0.128, 0.0785]
    ];
    if (_variant != 10) then {
        _strips pushBack [_cross, _up, _right, _center vectorAdd ((_forward vectorMultiply -0.075) vectorAdd (_right vectorMultiply -0.161)), 0.052, 0.052];
    };
    {
        _x params ["_asset", "_normal", "_vertical", "_origin", "_halfWidth", "_halfHeight"];
        private _tangent = _vertical vectorCrossProduct _normal;
        private _reach = _normal vectorMultiply 1.25;
        private _depths = [];
        {
            private _row = _origin vectorAdd (_vertical vectorMultiply _x);
            {
                private _sample = _row vectorAdd (_tangent vectorMultiply _x);
                private _hits = lineIntersectsSurfaces [
                    _sample vectorAdd _reach, _sample vectorDiff _reach, objNull, objNull, true, -1, "VIEW", "NONE"
                ];
                private _index = _hits findIf {(_x select 2) isEqualTo _object || {(_x select 3) isEqualTo _object}};
                if (_index >= 0) then {
                    _depths pushBack (((_hits select _index select 0) vectorDiff _origin) vectorDotProduct _normal);
                };
            } forEach [-_halfWidth, 0, _halfWidth];
        } forEach [-_halfHeight, 0, _halfHeight];
        // Skip a marking if a handle or a cabinet edge breaks up its paint surface.
        if (count _depths == 9 && {(selectMax _depths) - (selectMin _depths) <= 0.008}) then {
            private _position = _origin vectorAdd (_normal vectorMultiply ((selectMax _depths) + 0.001));
            _placements pushBack [_asset, _position, _normal, _vertical];
        };
    } forEach _strips;
};

if (_hasRetexture && {_surface in ["closed", "lid"]}) then {
    _placements pushBack [
        format ["variants\chest_%1_%2", _variant, _surface],
        _object modelToWorldWorld [0, 0, 0], vectorDir _object, vectorUp _object
    ];
};

private _decals = [];
{
    _x params ["_asset", "_position", "_normal", "_vertical"];
    private _decal = createSimpleObject [format ["\acm_extended\data\medical_chest\%1.p3d", _asset], _position, false];
    if (!isNull _decal) then {
        _decal setVectorDirAndUp [_normal, _vertical];
        _decals pushBack _decal;
    };
} forEach _placements;
_decals
