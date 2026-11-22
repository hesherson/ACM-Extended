/*
 * The vehicles near a litter that have a free place for it on their cabin floor (fn_vehicleLitterSpot.sqf), and
 * stand still on the ground.
 * Arguments: 0: litter. Returns: array of vehicles.
 */
params ["_litter"];
if (isNull _litter || {getNumber (configOf _litter >> "acmeLitterExtraCrew") <= 0}) exitWith {[]};
private _kinds = missionNamespace getVariable ["acme_sked_vehicleLitterKinds", ["vtx_H60_base"]];
(nearestObjects [_litter, _kinds select {isClass (configFile >> "CfgVehicles" >> _x)}, 12]) select {
    alive _x && {abs (speed _x) < 4} && {((getPosATL _x) select 2) < 3} && {([_x, _litter] call acme_sked_fnc_vehicleLitterSpot) isNotEqualTo []}
}
