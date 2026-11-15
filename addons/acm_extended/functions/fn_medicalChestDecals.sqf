/* Paint geometry is authored in the native coordinates of each part. */
params ["_object", "_surface", ["_variant", 0], ["_localOnly", false]];
if !(_variant in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) then {_variant = 0;};
private _finish = _surface;
if (_surface == "cabinet") then {
    _finish = ["cabinet4", "cabinet7"] select (typeOf _object == "ACME_MedicalChest7Drawers");
};

private _placements = [[format ["variants\chest_%1_%2", _variant, _finish], [0, 0, 0], [0, 1, 0], [0, 0, 1]]];
if (_surface == "closed" && {_variant == 0}) then {
    _placements append [
        ["chest_title", [0, 0.1539, 0], [0, 1, 0], [1, 0, 0]],
        ["chest_serial", [-0.195, 0.154, -0.093], [0, 1, 0], [1, 0, 0]],
        ["chest_tape_lid", [0.197, 0.1536, 0.026], [0, 1, 0], [1, 0, 0]],
        ["chest_cross", [0, -0.063, 0.2665], [0, 0, 1], [1, 0, 0]],
        ["chest_cross", [0, -0.063, -0.2665], [0, 0, -1], [1, 0, 0]],
        ["chest_cross", [0.4168, -0.075, 0.161], [1, 0, 0], [0, 0, -1]],
        ["chest_tape_side", [0.275, -0.068, 0.2662], [0, 0, 1], [1, 0, 0]],
        ["chest_tape_back", [0, -0.1617, -0.022], [0, -1, 0], [1, 0, 0]]
    ];
};

private _decals = [];
{
    _x params ["_asset", "_modelPos", "_modelDir", "_modelUp"];
    private _position = _object modelToWorldWorld _modelPos;
    private _decal = createSimpleObject [format ["\acm_extended\data\medical_chest\%1.p3d", _asset], _position, _localOnly];
    if (!isNull _decal) then {
        _decal setVectorDirAndUp [_object vectorModelToWorld _modelDir, _object vectorModelToWorld _modelUp];
        _decal setPosWorld _position;
        _decals pushBack _decal;
    };
} forEach _placements;
_decals
