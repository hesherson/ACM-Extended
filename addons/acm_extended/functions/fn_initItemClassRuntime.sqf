// Upgrade local gear in place when it is loaded or accessed. Magazine ammo can
// encode a partial dose or oxygen charge, so carry over its exact value.
["CAManBase", "InitPost", {
    [ACME_fnc_itemCargoMigrate, _this] call CBA_fnc_execNextFrame;
}, true, [], true] call CBA_fnc_addClassEventHandler;

["loadout", {
    [_this select 0] call ACME_fnc_itemCargoMigrate;
}] call CBA_fnc_addPlayerEventHandler;

["CBA_loadoutSet", {
    [_this select 0] call ACME_fnc_itemCargoMigrate;
}] call CBA_fnc_addEventHandler;

["ace_arsenal_loadoutsDisplayOpened", {
    // ACE validates item availability as it fills this display. Upgrade stored
    // classnames first so it resolves the visible classes, including magazines.
    private _saved = profileNamespace getVariable ["ace_arsenal_saved_loadouts", []];
    private _convert = {_this apply {[_x select 0, (_x select 1) call ACME_fnc_itemDataCanonical]}};
    private _converted = _saved call _convert;
    if (_converted isNotEqualTo _saved) then {
        profileNamespace setVariable ["ace_arsenal_saved_loadouts", _converted];
    };
    private _defaults = missionNamespace getVariable ["ace_arsenal_defaultLoadoutsList", []];
    private _convertedDefaults = _defaults call _convert;
    if (_convertedDefaults isNotEqualTo _defaults) then {
        missionNamespace setVariable ["ace_arsenal_defaultLoadoutsList", _convertedDefaults];
    };
}] call CBA_fnc_addEventHandler;

["ACME_migrateItemCargo", ACME_fnc_itemCargoMigrate] call CBA_fnc_addEventHandler;
["CAManBase", "InventoryOpened", {
    params ["", "_container", ["_secondary", objNull]];
    {
        if (!isNull _x) then {
            if (local _x) then {[_x] call ACME_fnc_itemCargoMigrate} else {
                ["ACME_migrateItemCargo", [_x], _x] call CBA_fnc_targetEvent;
            };
        };
    } forEach [_container, _secondary];
    false
}] call CBA_fnc_addClassEventHandler;
