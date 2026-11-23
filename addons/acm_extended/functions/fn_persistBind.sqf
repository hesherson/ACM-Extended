/* B393: the ACME Persistence module's durable object IDs. [object, id] -> true when the object holds that ID on this
 * machine (ACME_fnc_clinicalObjectRef "bind": the object is marked publicly, the binding is this machine's).
 * IDs the module allocates: "acme-player-<uid>" (a player's unit, bound on the server and on that player's own
 * machine), "acme-dev-<n>" (a placed device), "acme-obj-<class>-<x>_<y>_<z>" (a litter, mount, vehicle or other
 * object a device refers to). A binding left on an old object is released first when it can no longer be the
 * object that ID names: the object was deleted or destroyed, or (player IDs) it is no longer that player's unit,
 * such as his corpse after a respawn or his old unit after a reconnect. A live object that still owns the ID keeps
 * it: two live players with the same UID do not steal each other's binding (the bind then fails). */
params [["_object", objNull, [objNull]], ["_id", "", [""]]];
if (isNull _object || {_id == ""} || {count _id > 256}) exitWith {false};
if ((_object getVariable ["ACME_persistenceId", ""]) isEqualTo _id
    && {((missionNamespace getVariable ["ACME_clinicalObjectBindings", createHashMap]) getOrDefault [_id, objNull]) isEqualTo _object}) exitWith {true};
private _bindings = missionNamespace getVariable ["ACME_clinicalObjectBindings", createHashMap];
private _other = _bindings getOrDefault [_id, objNull];
if (!isNull _other && {_other isNotEqualTo _object}) then {
    private _player = (_id find "acme-player-") == 0;
    private _stale = !alive _other
        || {_player && {(getPlayerUID _other) != (_id select [12])}}
        || {(_other getVariable ["ACME_persistenceId", ""]) isNotEqualTo _id};
    if (_stale) then {
        _bindings deleteAt _id;
        missionNamespace setVariable ["ACME_clinicalObjectBindings", _bindings];
        if ((_other getVariable ["ACME_persistenceId", ""]) isEqualTo _id) then {_other setVariable ["ACME_persistenceId", "", true];};
    };
};
["bind", _object, _id] call ACME_fnc_clinicalObjectRef
