/* One server-owned Gear container lives for the entire chest lifetime. */
params ["_chest"];
if (!isServer || {is3DEN} || {isNull _chest} || {!isNil {_chest getVariable "ACME_medicalChestState"}}) exitWith {};
private _heading = getDir _chest;
private _base = [getPosWorld _chest, [_chest], 0.3, 2] call ACME_fnc_medicalChestGround;

private _profile = getText (configOf _chest >> "acmeChestStock");
private _cargoClass = ["ACME_MedicalChestCargo", "ACME_MedicalChestSpecialtyCargo"] select (_profile != "");
private _cargo = createVehicle [_cargoClass, ASLToATL _base, [], 0, "CAN_COLLIDE"];
if (isNull _cargo) exitWith {};
_cargo allowDamage false;
_cargo setVariable ["ACME_medicalChestAnchor", _chest, true];
[_cargo, _profile] call ACME_fnc_medicalChestStock;

_chest enableSimulationGlobal false;
_chest allowDamage false;
[_chest, _base, _heading, "closed"] call ACME_fnc_medicalChestPlace;
_cargo setPosWorld (_base vectorAdd [0, 0, -25]);
_chest setVariable ["ACME_medicalChestPlacement", [_base, _heading]];
_chest setVariable ["ACME_medicalChestCargo", _cargo, true];
_chest setVariable ["ACME_medicalChestState", [0, false], true];
_chest addEventHandler ["Deleted", {
    params ["_chest"];
    {
        private _object = _chest getVariable [_x, objNull];
        if (!isNull _object) then {deleteVehicle _object;};
    } forEach ["ACME_medicalChestCabinet", "ACME_medicalChestLid", "ACME_medicalChestLidMarking", "ACME_medicalChestCargo"];
}];
if (_chest getVariable ["ACME_medicalChestStartOpen", false]) then {
    [_chest, true, 0, true] call ACME_fnc_medicalChestSetOpen;
};
if !((_chest getVariable "ACME_medicalChestState") select 1) then {
    _chest setVariable ["ACME_medicalChestLidMarking", [_chest, _chest, true] call ACME_fnc_medicalChestLidMarking];
};
