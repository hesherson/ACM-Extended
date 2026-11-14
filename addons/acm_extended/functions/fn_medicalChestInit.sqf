/* One server-owned Gear container lives for the entire chest lifetime. */
params ["_chest"];
if (!isServer || {is3DEN} || {isNull _chest} || {!isNil {_chest getVariable "ACME_medicalChestState"}}) exitWith {};
private _heading = getDir _chest;
private _origin = getPosWorld _chest;
private _hit = lineIntersectsSurfaces [
    _origin vectorAdd [0, 0, 0.3],
    _origin vectorAdd [0, 0, -2],
    _chest, objNull, true, 1, "ROADWAY", "GEOM"
];
private _base = if (_hit isEqualTo []) then {
    ATLToASL [(_origin select 0), (_origin select 1), 0]
} else {
    _hit select 0 select 0
};

private _cargo = createVehicle ["ACME_MedicalChestCargo", ASLToATL _base, [], 0, "CAN_COLLIDE"];
if (isNull _cargo) exitWith {};
_cargo allowDamage false;
_cargo setVariable ["ACME_medicalChestAnchor", _chest, true];
[_cargo] call ACME_fnc_medicalChestStock;

_chest enableSimulationGlobal false;
_chest allowDamage false;
[_chest, _base, _heading] call ACME_fnc_medicalChestPlace;
_cargo setPosWorld (_base vectorAdd [0, 0, -25]);
_chest setVariable ["ACME_medicalChestPlacement", [_base, _heading]];
_chest setVariable ["ACME_medicalChestCargo", _cargo, true];
_chest setVariable ["ACME_medicalChestState", [0, false], true];
_chest addEventHandler ["Deleted", {
    params ["_chest"];
    {
        private _object = _chest getVariable [_x, objNull];
        if (!isNull _object) then {deleteVehicle _object;};
    } forEach ["ACME_medicalChestCabinet", "ACME_medicalChestLid", "ACME_medicalChestCargo"];
    {if (!isNull _x) then {deleteVehicle _x;};} forEach (_chest getVariable ["ACME_medicalChestDecals", []]);
}];
_chest setVariable ["ACME_medicalChestDecals", [_chest, true, true] call ACME_fnc_medicalChestDecals];
