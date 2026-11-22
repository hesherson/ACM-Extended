/*
 * SKED action children: one per vehicle within 10 m with a free seat for the casualty.
 * Arguments (ACE insertChildren): 0: SKED, 1: player. Returns: array of actions.
 */
params ["_target", "_player"];
private _patient = _target getVariable ["acme_sked_patient", objNull];
if (isNull _patient) exitWith {[]};
// the litter itself, casualty and all, onto the cabin floor (fn_vehicleLitter.sqf); then the seats
(([_target] call acme_sked_fnc_vehicleLitterNear) apply {
    private _action = ["litter_" + str _x, format ["%1 (%2 m) - litter on the cabin floor", getText ((configOf _x) >> "displayName"), (_player distance _x) toFixed 1], "", {
        params ["_target", "_player", "_vehicle"];
        [_player, _target, _vehicle, true] call acme_sked_fnc_vehicleLitter;
    }, {true}, {}, _x] call ace_interact_menu_fnc_createAction;
    [_action, [], _target]
}) + (([_patient, 10] call ace_common_fnc_nearestVehiclesFreeSeat) apply {
    private _name = format ["%1 (%2 m)", getText ((configOf _x) >> "displayName"), (_player distance _x) toFixed 1];
    if (_x isKindOf "vtx_H60_base") then {
        private _preferred = [0, _x] call acme_sked_fnc_preferredLitter;
        private _open = getText (configOf _target >> "acmeLitterOpen");
        _name = _name + ([" - Talon II preferred", " - preferred litter"] select (_open == _preferred));
    };
    private _action = [str _x, _name, "", {
        params ["_target", "_player", "_vehicle"];
        [_player, _target, _vehicle] call acme_sked_fnc_loadVehicle;
    }, {true}, {}, _x] call ace_interact_menu_fnc_createAction;
    [_action, [], _target]
})
