/* Trusted server-side transition used after validation or during initialization. */
params ["_chest", "_opening", "_revision", ["_initial", false]];
if (!isServer || {is3DEN} || {isRemoteExecuted && {_initial}}) exitWith {};
private _cabinet = _chest getVariable ["ACME_medicalChestCabinet", objNull];
private _cargo = _chest getVariable ["ACME_medicalChestCargo", objNull];

private _variant = getNumber (configOf _chest >> "acmeChestVariant");
(_chest getVariable "ACME_medicalChestPlacement") params ["_base", "_heading"];
if (_opening) then {
    private _class = if (_initial) then {"ACME_MedicalChest4Drawers"} else {
        selectRandom ["ACME_MedicalChest4Drawers", "ACME_MedicalChest7Drawers"]
    };
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
    _cabinet enableSimulationGlobal false;
    // The detached cover lies to the side, clear of the open drawers.
    private _side = [_base, _heading, _chest, _lid] call ACME_fnc_medicalChestLidBase;
    [_lid, _side, _heading, true] call ACME_fnc_medicalChestPlace;
    [_cabinet, _base, _heading] call ACME_fnc_medicalChestPlace;
    _cargo attachTo [_cabinet, [0, 0, 0]];
    _cabinet setVariable ["ACME_medicalChestAnchor", _chest, true];
    _chest setVariable ["ACME_medicalChestCabinet", _cabinet, true];
    _chest setVariable ["ACME_medicalChestLid", _lid];
    _chest hideObjectGlobal true;
    [_cabinet, _initial, true] call ACME_fnc_medicalChestDrawers;
    {deleteVehicle _x;} forEach (_chest getVariable ["ACME_medicalChestDecals", []]);
    _chest setVariable ["ACME_medicalChestDecals",
        ([_cabinet, "cabinet", _variant] call ACME_fnc_medicalChestDecals) + ([_lid, "lid", _variant] call ACME_fnc_medicalChestDecals)];
} else {
    // Keep the same cargo, and move it out of native Gear reach while shut.
    detach _cargo;
    _cargo setPosWorld (_base vectorAdd [0, 0, -25]);
    _chest hideObjectGlobal false;
    deleteVehicle _cabinet;
    deleteVehicle (_chest getVariable ["ACME_medicalChestLid", objNull]);
    {deleteVehicle _x;} forEach (_chest getVariable ["ACME_medicalChestDecals", []]);
    _chest setVariable ["ACME_medicalChestDecals", [_chest, "closed", _variant] call ACME_fnc_medicalChestDecals];
    _chest setVariable ["ACME_medicalChestCabinet", objNull, true];
    _chest setVariable ["ACME_medicalChestLid", objNull];
};
if (_opening && {isNull _cabinet}) exitWith {};

_chest setVariable ["ACME_medicalChestState", [_revision + 1, _opening], true];
if (!_opening) then {
    ["ACME_medicalChestClosed", [_cargo, _revision + 1]] call CBA_fnc_globalEvent;
};
if (!_initial) then {
    private _sound = ["medical_chest_close", "medical_chest_open"] select _opening;
    playSound3D [format ["acm_extended\sound\%1.ogg", _sound], objNull, false, getPosWorld _chest, 1.5, 1, 18];
};
