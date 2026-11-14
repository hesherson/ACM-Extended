/* The server serializes the visual swap; the native cargo object never changes. */
params [
    ["_target", objNull, [objNull]], ["_actor", objNull, [objNull]],
    ["_opening", false, [false]], ["_revision", -1, [0]]
];
if (!isServer || {isNull _actor} || {isNull _target} || {!alive _actor}
    || {_actor getVariable ["ACE_isUnconscious", false]} || {_actor distance _target > 4}
    || {isRemoteExecuted && {remoteExecutedOwner != owner _actor}}) exitWith {};

private _chest = if (_opening) then {_target} else {_target getVariable ["ACME_medicalChestAnchor", objNull]};
if (isNull _chest || {!(_chest isKindOf "ACME_MedicalChest")}) exitWith {};
if ((_chest getVariable ["ACME_medicalChestState", []]) isNotEqualTo [_revision, !_opening]) exitWith {};
private _cabinet = _chest getVariable ["ACME_medicalChestCabinet", objNull];
if (!_opening && {_target isNotEqualTo _cabinet}) exitWith {};
private _cargo = _chest getVariable ["ACME_medicalChestCargo", objNull];
if (isNull _cargo) exitWith {};

(_chest getVariable "ACME_medicalChestPlacement") params ["_base", "_heading"];
if (_opening) then {
    private _class = selectRandom ["ACME_MedicalChest4Drawers", "ACME_MedicalChest7Drawers"];
    _cabinet = createVehicle [_class, ASLToATL _base, [], 0, "CAN_COLLIDE"];
    private _lid = createVehicle ["Land_PortableCabinet_01_lid_olive_F", ASLToATL _base, [], 0, "CAN_COLLIDE"];
    if (isNull _cabinet || {isNull _lid}) exitWith {
        if (!isNull _cabinet) then {deleteVehicle _cabinet;};
        if (!isNull _lid) then {deleteVehicle _lid;};
        _cabinet = objNull;
    };
    _cabinet allowDamage false;
    _lid allowDamage false;
    _lid enableSimulationGlobal false;
    // The detached cover lies to the side, clear of the open drawers.
    private _right = [cos _heading, -(sin _heading), 0];
    private _side = _base vectorAdd (_right vectorMultiply 0.95);
    private _surface = lineIntersectsSurfaces [
        _side vectorAdd [0, 0, 0.65], _side vectorAdd [0, 0, -0.7],
        _chest, _lid, true, 1, "ROADWAY", "GEOM"
    ];
    _side = if (_surface isNotEqualTo []) then {_surface select 0 select 0} else {
        ATLToASL [_side select 0, _side select 1, 0]
    };
    [_lid, _side, _heading, false] call ACME_fnc_medicalChestPlace;
    [_cabinet, _base, _heading] call ACME_fnc_medicalChestPlace;
    // Hold the cabinet upright while allowing its native drawer animations.
    private _cabinetDir = _chest vectorWorldToModel (vectorDir _cabinet);
    private _cabinetUp = _chest vectorWorldToModel (vectorUp _cabinet);
    _cabinet attachTo [_chest, _chest worldToModel (ASLToAGL getPosWorld _cabinet)];
    _cabinet setVectorDirAndUp [_cabinetDir, _cabinetUp];
    _cargo attachTo [_cabinet, [0, 0, 0]];
    _cabinet setVariable ["ACME_medicalChestAnchor", _chest, true];
    _chest setVariable ["ACME_medicalChestCabinet", _cabinet, true];
    _chest setVariable ["ACME_medicalChestLid", _lid];
    _chest hideObjectGlobal true;
    [_cabinet] call ACME_fnc_medicalChestDrawers;
    {deleteVehicle _x;} forEach (_chest getVariable ["ACME_medicalChestDecals", []]);
    _chest setVariable ["ACME_medicalChestDecals",
        ([_cabinet, "cabinet"] call ACME_fnc_medicalChestDecals) + ([_lid, "lid"] call ACME_fnc_medicalChestDecals)];
} else {
    // Keep the same cargo, and move it out of native Gear reach while shut.
    detach _cargo;
    _cargo setPosWorld (_base vectorAdd [0, 0, -25]);
    _chest hideObjectGlobal false;
    deleteVehicle _cabinet;
    deleteVehicle (_chest getVariable ["ACME_medicalChestLid", objNull]);
    {deleteVehicle _x;} forEach (_chest getVariable ["ACME_medicalChestDecals", []]);
    _chest setVariable ["ACME_medicalChestDecals", [_chest, "closed"] call ACME_fnc_medicalChestDecals];
    _chest setVariable ["ACME_medicalChestCabinet", objNull, true];
    _chest setVariable ["ACME_medicalChestLid", objNull];
};
if (_opening && {isNull _cabinet}) exitWith {};

_chest setVariable ["ACME_medicalChestState", [_revision + 1, _opening], true];
if (!_opening) then {
    ["ACME_medicalChestClosed", [_cargo, _revision + 1]] call CBA_fnc_globalEvent;
};
private _sound = ["medical_chest_close", "medical_chest_open"] select _opening;
playSound3D [format ["acm_extended\sound\%1.ogg", _sound], objNull, false, getPosWorld _chest, 1.5, 1, 18];
