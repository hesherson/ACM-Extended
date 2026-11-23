/* B393: the ACME Persistence module (Eden, server). Keeps ACME's own state across a player reconnecting and across
 * the mission being restarted, and nothing else: it never saves or sets a loadout, a position or an object that is
 * not ACME's, so it works next to any other persistence system, which keeps doing those.
 *  - each player, by player ID: his medical state (wounds, bandages, tourniquets, fractures, blood volume, vitals,
 *    medications, airway/breathing/circulation, IVs and every ACME condition: ace_medical_fnc_serializeState as
 *    ACME extends it) and the state of the ACME items he carries (prepared IVs and syringes, partial vials, bag
 *    volumes, cooler times, warm blood ages, ventilator settings). His medical state comes back as soon as he joins
 *    again, his items' state once the ACME items he carried are on him again (from his slot, or from the other
 *    persistence system); a player who died is not restored.
 *  - ACME objects in the world: blood fridges (stock, restock timer), blood cooler boxes (coolant and warm times),
 *    prepared items in ACME containers, loose blood ages, and the fresh whole blood donor registry. Matched again by
 *    their class and place (the mission or the other persistence system puts the objects back).
 *  - placed medical devices (Tempus Pro and LS monitors, Accuvac, ventilator): ACME items, recreated by this module
 *    at mission start (fn_persistDevices.sqf). Turn "Placed medical devices" off when another persistence system
 *    already recreates placed objects.
 * Saved on the server in the mission's profile (missionProfileNamespace), every few minutes, when a player leaves
 * and when the mission ends; the Zeus module "Persistence: save now" saves at once, "Persistence: status" shows
 * what is saved. One module per mission: a second one is ignored.
 * Module arguments: see ACME_ModulePersistence in config.cpp. */
params [["_logic", objNull, [objNull]], ["_units", [], [[]]], ["_activated", true, [true]]];
if (!isServer || {!_activated} || {isNull _logic}) exitWith {};
if (!isNil "ACME_persist") exitWith {};   // one per mission
private _arg = {params ["_name", "_default"]; private _v = _logic getVariable [_name, _default]; if (isNil "_v") then {_default} else {_v}};
// Eden gives BOOL as a Boolean or a number depending on the version; anything else is the default
private _bool = {
    params ["_name", "_default"];
    private _v = [_name, _default] call _arg;
    if (_v isEqualType 0) exitWith {_v > 0};
    if (_v isEqualType true) exitWith {_v};
    _default
};
private _number = {
    params ["_name", "_default", "_min"];
    private _v = [_name, _default] call _arg;
    if (_v isEqualType "") then {_v = parseNumber _v;};
    if (!(_v isEqualType 0) || {!finite _v}) then {_v = _default;};
    (_v max _min) min 86400
};
private _key = ["Campaign", ""] call _arg;
if !(_key isEqualType "") then {_key = str _key;};
_key = _key select [0, 64];
private _config = createHashMapFromArray [
    ["medical", ["Medical", true] call _bool],
    ["items", ["Items", true] call _bool],
    ["restoreItems", ["RestoreItems", false] call _bool],
    ["world", ["World", true] call _bool],
    ["devices", ["Devices", true] call _bool],
    ["ageOffline", ["AgeOffline", false] call _bool],
    ["interval", ["Interval", 180, 30] call _number],
    ["capture", ["CaptureInterval", 30, 10] call _number],
    ["late", _logic getVariable ["ACME_persistLate", false]],
    ["key", "ACME_persist_v1" + (["", "_" + _key] select (_key != ""))]
];
ACME_persist = _config;
publicVariable "ACME_persist";
["load"] call ACME_fnc_persistServer;
["start"] call ACME_fnc_persistServer;
// every client (and every later joiner) starts its side: capture its player, ask for his saved state
["ACME_persistStart", [], "ACME_persistStart"] call CBA_fnc_globalEventJIP;
