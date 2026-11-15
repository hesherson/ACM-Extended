/* Eden-only render objects. The editable chest remains the saved entity. */
if (!is3DEN) exitWith {false};
params ["_action", ["_entity", objNull]];
private _previews = uiNamespace getVariable ["ACME_medicalChestEdenPreviews", createHashMap];
uiNamespace setVariable ["ACME_medicalChestEdenPreviews", _previews];
private _remove = {
    params ["_id"];
    (_previews getOrDefault [_id, []]) params [
        ["_chest", objNull], ["_look", []], ["_parts", []], ["_decals", []]
    ];
    {deleteVehicle (_x select 1);} forEach _decals;
    {deleteVehicle _x;} forEach _parts;
    if (!isNull _chest) then {_chest hideObject false;};
    _previews deleteAt _id;
};

if (_action == "clear") exitWith {
    {[_x] call _remove;} forEach (keys _previews);
    false
};
if (_action == "reload") exitWith {
    {[_x] call _remove;} forEach (keys _previews);
    {["update", _x] call ACME_fnc_medicalChestEden;} forEach (all3DENEntities select 0);
};
if !(_entity isEqualType objNull) exitWith {};
if (isNull _entity) exitWith {};
private _id = get3DENEntityID _entity;
if (_id < 0) exitWith {
    // Eden can release the ID before its removal callback.
    if (_action == "remove") then {
        {
            if (((_previews get _x) select 0) isEqualTo _entity) exitWith {[_x] call _remove;};
        } forEach (keys _previews);
    };
};
if (_action == "remove" || {!(_entity isKindOf "ACME_MedicalChest")}) exitWith {
    if (_id in _previews) then {[_id] call _remove;};
};

private _open = (_entity get3DENAttribute "ACME_medicalChestStartOpen") param [0, false];
private _look = [typeOf _entity, _open];
(_previews getOrDefault [_id, []]) params [
    ["_owner", objNull], ["_oldLook", []], ["_parts", []], ["_decals", []], ["_transform", []]
];
private _heading = getDir _entity;
private _base = [getPosWorld _entity, [_entity], 0.3, 2, true] call ACME_fnc_medicalChestGround;
private _lidSupport = if (_open) then {
    private _closedPose = [_entity, _base, _heading, "closed", [0, 0, 1], objNull, false] call ACME_fnc_medicalChestPlace;
    private _seatPose = [_entity, _closedPose] call ACME_fnc_medicalChestLidSeat;
    [_base, _seatPose, [_entity], true] call ACME_fnc_medicalChestLidBase
} else {[]};
private _next = [_base, _heading, _lidSupport];
private _replace = _entity isNotEqualTo _owner || {_look isNotEqualTo _oldLook}
    || {(_parts findIf {isNull _x}) >= 0} || {(_decals findIf {isNull (_x select 1)}) >= 0};
if (_replace) then {
    [_id] call _remove;
    private _class = if (_open) then {"ACME_MedicalChest4Drawers"} else {typeOf _entity};
    _parts = [createSimpleObject [_class, _base, true]];
    if (_open) then {
        _parts pushBack (createSimpleObject ["Land_PortableCabinet_01_lid_olive_F", _lidSupport select 0, true]);
    };
    if ((_parts findIf {isNull _x}) >= 0) exitWith {
        {deleteVehicle _x;} forEach _parts;
        _parts = [];
    };
    {
        _x setPhysicsCollisionFlag false;
        _x setVariable ["ACME_medicalChestEdenVisual", true];
    } forEach _parts;
    _decals = [];
};
if (_parts isEqualTo []) exitWith {};
if (_replace || {_next isNotEqualTo _transform}) then {
    [_parts select 0, _base, _heading, ["closed", "cabinet"] select _open, [0, 0, 1], _entity] call ACME_fnc_medicalChestPlace;
    if (_open) then {
        _lidSupport params ["_side", "_normal"];
        [_parts select 1, _side, _heading, "lid", _normal, _entity] call ACME_fnc_medicalChestPlace
    };
    if (_replace && {_open}) then {
        private _cabinet = _parts select 0;
        [_cabinet, [_cabinet] call ACME_fnc_medicalChestDrawerPlan, 0] call ACME_fnc_medicalChestDrawers;
    };
    if (_replace) then {
        private _bodyTexture = getArray (configOf _entity >> "hiddenSelectionsTextures") param [0, ""];
        if (_bodyTexture != "") then {(_parts select 0) setObjectTexture [0, _bodyTexture];};
        private _variant = getNumber (configOf _entity >> "acmeChestVariant");
        {
            private _part = _x;
            private _surface = ["closed", "cabinet", "lid"] select (_forEachIndex + ([0, 1] select _open));
            {
                _x setVariable ["ACME_medicalChestEdenVisual", true];
                _decals pushBack [
                    _part, _x,
                    _part worldToModel (ASLToAGL getPosWorld _x),
                    _part vectorWorldToModel (vectorDir _x),
                    _part vectorWorldToModel (vectorUp _x)
                ];
            } forEach ([_part, _surface, _variant, true] call ACME_fnc_medicalChestDecals);
        } forEach _parts;
    } else {
        {
            _x params ["_part", "_decal", "_position", "_forward", "_up"];
            _decal setVectorDirAndUp [_part vectorModelToWorld _forward, _part vectorModelToWorld _up];
            _decal setPosWorld (_part modelToWorldWorld _position);
        } forEach _decals;
    };
    _previews set [_id, [_entity, _look, _parts, _decals, _next]];
};
if (!isObjectHidden _entity) then {_entity hideObject true;};
