/* B393: Zeus modules "Persistence: save now", "Persistence: status" and "Persistence: forget saved state". Run where
 * the module was placed (the curator's machine); the work is the server's, which sends back a short summary
 * (players saved, fridges, cooler boxes, containers, placed devices, donor registry, anything busy that kept its
 * previous save: fn_persistServer.sqf "report", shown by fn_registerPersistenceRuntime.sqf). "Save now" in a
 * mission without the Eden module turns persistence on with the default settings first; "status" and "forget"
 * there only say that persistence is off. _this: [logic, units, activated]. */
params [["_logic", objNull, [objNull]], ["_units", []], ["_activated", true]];
if (isNull _logic || {!local _logic}) exitWith {};
private _type = typeOf _logic;
deleteVehicle _logic;
if (!_activated) exitWith {};
private _me = [player, ACE_player] select (isNull player);
switch (_type) do {
    case "ACME_ModulePersistenceClear": {
        if (isNil "ACME_persist") exitWith {["ACME persistence is not on in this mission.", 2] call ace_common_fnc_displayTextStructured;};
        ["ACME_persistClear", [_me]] call CBA_fnc_serverEvent;
    };
    case "ACME_ModulePersistenceStatus": {
        if (isNil "ACME_persist") exitWith {["ACME persistence is not on in this mission.", 2] call ace_common_fnc_displayTextStructured;};
        ["ACME_persistStatusRequest", [_me]] call CBA_fnc_serverEvent;
    };
    default {
        if (isNil "ACME_persist") then {["ACME_persistEnableDefault", []] call CBA_fnc_serverEvent;};
        // (after the server has turned it on: the save and its summary follow)
        [{["ACME_persistSaveNow", [_this]] call CBA_fnc_serverEvent;}, _me, 1] call CBA_fnc_waitAndExecute;
        ["ACME: saving...", 1.5] call ace_common_fnc_displayTextStructured;
    };
};
