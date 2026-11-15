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
private _texture = (getObjectTextures _entity) param [0, ""];
private _look = [typeOf _entity, _open, _texture];
(_previews getOrDefault [_id, []]) params [
    ["_owner", objNull], ["_oldLook", []], ["_parts", []], ["_transform", []]
];
private _heading = getDir _entity;
private _base = [getPosWorld _entity, [_entity], 0.3, 2, true] call ACME_fnc_medicalChestGround;
private _lidSupport = if (_open) then {
    [_base, _heading, _entity, objNull, true] call ACME_fnc_medicalChestLidBase
} else {[]};
private _next = [_base, _heading, _lidSupport];
private _replace = _entity isNotEqualTo _owner || {_look isNotEqualTo _oldLook}
    || {(_parts findIf {isNull _x}) >= 0};
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
        if (_texture != "") then {_x setObjectTexture ["camo_1", _texture];};
    } forEach _parts;
};
if (_parts isEqualTo []) exitWith {};
if (_replace || {_next isNotEqualTo _transform}) then {
    private _bodyPose = [_parts select 0, _base, _heading, ["closed", "cabinet"] select _open, [0, 0, 1], _entity] call ACME_fnc_medicalChestPlace;
    if (_open) then {
        _lidSupport params ["_side", "_normal"];
        private _coverForward = ([_entity, _bodyPose] call ACME_fnc_medicalChestLidSeat) select 1;
        private _coverHeading = (_coverForward select 0) atan2 (_coverForward select 1);
        [_parts select 1, _side, _coverHeading, "lid", _normal, _entity] call ACME_fnc_medicalChestPlace;
    };
    if (_replace && {_open}) then {
        private _cabinet = _parts select 0;
        [_cabinet, [_cabinet] call ACME_fnc_medicalChestDrawerPlan, 0] call ACME_fnc_medicalChestDrawers;
    };
    _previews set [_id, [_entity, _look, _parts, _next]];
};
if (!isObjectHidden _entity) then {_entity hideObject true;};
