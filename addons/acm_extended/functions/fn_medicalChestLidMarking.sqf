/* The lid has mirrored stock UVs, so its marking follows a fitted outer surface. */
params ["_object", "_chest", "_closed", ["_localOnly", false], ["_marking", objNull]];
private _position = _object modelToWorldWorld [0, 0, 0];
if (isNull _marking) then {
    private _variant = getNumber (configOf _chest >> "acmeChestVariant");
    private _part = ["lid", "closed_lid"] select _closed;
    private _model = format ["\acm_extended\data\medical_chest\variants\chest_%1_%2.p3d", _variant, _part];
    _marking = createSimpleObject [_model, _position, _localOnly];
    if (isNull _marking) then {diag_log format ["[ACME] Medical chest could not create lid marking: %1", _model];};
};
if (!isNull _marking) then {
    _marking setVectorDirAndUp [vectorDir _object, vectorUp _object];
    _marking setPosWorld _position;
};
_marking
