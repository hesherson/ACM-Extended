/* One server-owned Gear container lives for the entire chest lifetime. */
params ["_chest"];
if (!isServer || {is3DEN} || {isNull _chest} || {!isNil {_chest getVariable "ACME_medicalChestState"}}) exitWith {};
private _heading = getDir _chest;
// (only to make its cargo somewhere near; fn_medicalChestSeat.sqf seats it below)
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
_chest setVariable ["ACME_medicalChestCargo", _cargo, true];
_chest setVariable ["ACME_medicalChestState", [0, false], true];
[_chest] call ACME_fnc_medicalChestSeat;
// Every chest is looked at once a second: one that something has moved (Zeus, a script, another mod) is seated
// again where it now is, once it has been still for a second. An open chest is moved by its cabinet.
if (isNil "ACME_medicalChests") then {
    ACME_medicalChests = [];
    [{
        ACME_medicalChests = ACME_medicalChests select {!isNull _x};
        {
            private _chest = _x;
            if !(_chest getVariable ["ACME_medicalChestTransition", false]) then {
                private _cabinet = _chest getVariable ["ACME_medicalChestCabinet", objNull];
                // what Zeus or a script would have moved: the cabinet of an open chest, else the chest
                private _thing = [_chest, _cabinet] select (!isNull _cabinet);
                private _seated = _chest getVariable [["ACME_medicalChestSeated", "ACME_medicalChestCabinetSeated"] select (!isNull _cabinet), []];
                if (_seated isEqualTo []) then {
                    _chest setVariable [["ACME_medicalChestSeated", "ACME_medicalChestCabinetSeated"] select (!isNull _cabinet), [getPosWorld _thing, vectorDir _thing]];
                } else {
                    private _now = [getPosWorld _thing, vectorDir _thing];
                    // (not while somebody carries it or it is stowed as cargo: it is seated once it has been put down)
                    if (isNull attachedTo _thing && {!isObjectHidden _thing}
                        && {(_now select 0) distance (_seated select 0) > 0.02 || {(_now select 1) vectorDotProduct (_seated select 1) < 0.9999}}) then {
                        // moved: wait until it has been still for a second
                        private _last = _chest getVariable ["ACME_medicalChestMoving", []];
                        if (_last isEqualTo [] || {(_now select 0) distance (_last select 0) > 0.005} || {(_now select 1) vectorDotProduct (_last select 1) < 0.99999}) then {
                            _chest setVariable ["ACME_medicalChestMoving", _now + [CBA_missionTime]];
                        } else {
                            if (CBA_missionTime - (_last select 2) >= 1) then {
                                _chest setVariable ["ACME_medicalChestMoving", nil];
                                // (fn_medicalChestPlace.sqf turns a heading a quarter turn to keep chests of old missions facing as they
                                // did; the heading asked for here is the way the thing faces now)
                                [_chest, _now select 0, ((getDir _thing) + 90) % 360] call ACME_fnc_medicalChestSeat;
                            };
                        };
                    };
                };
            };
        } forEach ACME_medicalChests;
    }, 1] call CBA_fnc_addPerFrameHandler;
};
ACME_medicalChests pushBackUnique _chest;
_chest addEventHandler ["Deleted", {
    params ["_chest"];
    {
        private _object = _chest getVariable [_x, objNull];
        if (!isNull _object) then {deleteVehicle _object;};
    } forEach ["ACME_medicalChestCabinet", "ACME_medicalChestLid", "ACME_medicalChestCargo"];
}];
if (_chest getVariable ["ACME_medicalChestStartOpen", false]) then {
    [_chest, true, 0, true] call ACME_fnc_medicalChestSetOpen;
};
