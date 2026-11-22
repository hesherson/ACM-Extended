/*
 * Server: a chest is seated on the ground where it now is (fn_medicalChestRest.sqf): when it is made, and again
 * whenever something has moved it. An open chest is shut and opened again in its new place, without the motion
 * of the lid.
 * Arguments: 0: chest, 1: where its middle now is (ASL) <ARRAY> (default: where the chest is), 2: heading
 * <NUMBER> (default: the chest's).
 */
params ["_chest", ["_at", []], ["_heading", -1]];
if (!isServer || {isNull _chest}) exitWith {};
if (_at isEqualTo []) then {_at = getPosWorld _chest;};
if (_heading < 0) then {_heading = getDir _chest;};
private _cabinet = _chest getVariable ["ACME_medicalChestCabinet", objNull];
private _lid = _chest getVariable ["ACME_medicalChestLid", objNull];
(0 boundingBoxReal _chest) params ["_min", "_max"];
private _half = [(((_max select 0) - (_min select 0)) / 2 - 0.03) max 0.1, (((_max select 1) - (_min select 1)) / 2 - 0.03) max 0.1];
([_at, [_chest, _cabinet], _heading, _half] call ACME_fnc_medicalChestRest) params ["_base", "_normal"];
(_chest getVariable ["ACME_medicalChestState", [0, false]]) params ["_revision", "_open"];
if (_open) then {[_chest, false, _revision, true] call ACME_fnc_medicalChestSetOpen;};
_chest setVariable ["ACME_medicalChestPlacement", [_base, _heading, _normal]];
[_chest, _base, _heading, "closed", _normal] call ACME_fnc_medicalChestPlace;
private _cargo = _chest getVariable ["ACME_medicalChestCargo", objNull];
if (!isNull _cargo && {isNull attachedTo _cargo}) then {_cargo setPosWorld (_base vectorAdd [0, 0, -25]);};
// (where it was put: the watch in fn_medicalChestInit.sqf compares against this)
_chest setVariable ["ACME_medicalChestSeated", [getPosWorld _chest, vectorDir _chest, vectorUp _chest]];
if (_open) then {
    [_chest, true, (_chest getVariable ["ACME_medicalChestState", [0, false]]) select 0, true] call ACME_fnc_medicalChestSetOpen;
    private _moved = _chest getVariable ["ACME_medicalChestCabinet", objNull];
    if (!isNull _moved) then {_chest setVariable ["ACME_medicalChestCabinetSeated", [getPosWorld _moved, vectorDir _moved]];};
};
