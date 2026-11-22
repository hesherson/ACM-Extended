/* Eden-only render objects. The editable chest remains the saved entity. */
if (!is3DEN) exitWith {false};
params ["_action", ["_entity", objNull]];
private _previews = uiNamespace getVariable ["ACME_medicalChestEdenPreviews", createHashMap];
uiNamespace setVariable ["ACME_medicalChestEdenPreviews", _previews];
private _remove = {
    params ["_id"];
    (_previews getOrDefault [_id, []]) params [
        ["_chest", objNull], ["_look", []], ["_parts", []]
    ];
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
(getObjectTextures _entity) params [["_texture", ""], ["_artwork", ""]];
private _look = [typeOf _entity, _open, _texture, _artwork];
(_previews getOrDefault [_id, []]) params [
    ["_owner", objNull], ["_oldLook", []], ["_parts", []], ["_transform", []]
];
private _heading = getDir _entity;
// (as the mission's chest will stand: on its four feet, leaning with the ground: fn_medicalChestRest.sqf)
(0 boundingBoxReal _entity) params ["_boxMin", "_boxMax"];
([getPosWorld _entity, [_entity], _heading,
    [(((_boxMax select 0) - (_boxMin select 0)) / 2 - 0.03) max 0.1, (((_boxMax select 1) - (_boxMin select 1)) / 2 - 0.03) max 0.1], true]
    call ACME_fnc_medicalChestRest) params ["_base", "_ground"];
private _lidSupport = if (_open) then {
    [_base, _heading, _entity, objNull, true] call ACME_fnc_medicalChestLidBase
} else {[]};
private _next = [_base, _heading, _lidSupport, _ground];
private _replace = _entity isNotEqualTo _owner || {_look isNotEqualTo _oldLook}
    || {(_parts findIf {isNull _x}) >= 0};
if (_replace) then {
    [_id] call _remove;
    private _class = if (_open) then {[_entity] call ACME_fnc_medicalChestCabinetClass} else {typeOf _entity};
    _parts = [createSimpleObject [_class, _base, true]];
    if (_open) then {
        private _lidClass = getText (configOf _entity >> "acmeChestLidClass");
        _parts pushBack (createSimpleObject [[_lidClass, "ACME_MedicalChestLid"] select (_lidClass == ""), _lidSupport select 0, true]);
    };
    if ((_parts findIf {isNull _x}) >= 0) exitWith {
        {deleteVehicle _x;} forEach _parts;
        _parts = [];
    };
    {
        _x setPhysicsCollisionFlag false;
        _x setVariable ["ACME_medicalChestEdenVisual", true];
        if (_texture != "") then {_x setObjectTexture ["camo", _texture];};
    } forEach _parts;
    if (_artwork != "") then {(_parts select ([0, 1] select _open)) setObjectTexture ["lid_artwork", _artwork];};
};
if (_parts isEqualTo []) exitWith {};
if (_replace || {_next isNotEqualTo _transform}) then {
    [_parts select 0, _base, _heading, ["closed", "cabinet"] select _open, _ground] call ACME_fnc_medicalChestPlace;
    if (_open) then {
        _lidSupport params ["_side", "_normal"];
        [_parts select 1, _side, _heading, "lid", _normal] call ACME_fnc_medicalChestPlace;
    };
    if (_replace && {_open}) then {
        private _cabinet = _parts select 0;
        [_cabinet, [_cabinet] call ACME_fnc_medicalChestDrawerPlan, 0] call ACME_fnc_medicalChestDrawers;
    };
    _previews set [_id, [_entity, _look, _parts, _next]];
};
if (!isObjectHidden _entity) then {_entity hideObject true;};
