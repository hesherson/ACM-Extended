/* Authoritative server import after native inventory is present. No item is
 * created/removed. Class-count evidence is exact; same-class ambiguity retains
 * the older exposure. Call on server, retry false after replication settles. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_bloodExposureRestore;}; _ok};
params ["_holder","_snapshot",["_offline",0]];
if (!isServer || {isNull _holder} || {!([_snapshot] call ACME_fnc_bloodExposureSnapshotValid)}) exitWith {false};
if !(_offline isEqualType 0 && {finite _offline} && {_offline >= 0} && {_offline <= 1e9}) exitWith {false};
if (count (_holder getVariable ["ACME_bloodExposurePending",[]]) > 0
    || {count (_holder getVariable ["ACME_bloodSeedPending",createHashMap]) > 0}) exitWith {false};
private _kit = _holder getVariable ["ACME_equipmentKitEpoch",0];
private _key = [str _snapshot,_offline,_kit];
if ((_holder getVariable ["ACME_bloodRestoreReceipt",[]]) isEqualTo _key) exitWith {true};
private _items = if (_holder isKindOf "CAManBase") then {(uniformItems _holder) + (vestItems _holder) + (backpackItems _holder)} else {itemCargo _holder};
private _bags = _items select {([_x] call ACME_fnc_coolerBagVolume) > 0};
private _saved = (_snapshot select 1) apply {_x select 0};
_bags sort true;
_saved sort true;
if (_bags isNotEqualTo _saved) exitWith {false};
private _now = serverTime;
private _store = missionNamespace getVariable ["ACME_ccByHolder",createHashMap];
private _record = _store getOrDefault [netId _holder,[[],[]]];
private _old = createHashMap;
{
    _x params ["_class","","_warm",["_at",_now]];
    private _ages = _old getOrDefault [_class,[]];
    _ages pushBack (_warm + ((_now - _at) max 0));
    _old set [_class,_ages];
} forEach (_record select 0);
{private _ages = _old get _x; _ages sort false;} forEach keys _old;
private _ranked = (_snapshot select 1) apply {[_x select 1,_x select 0]};
_ranked sort false;
private _entries = [];
{
    _x params ["_warm","_class"];
    private _ages = _old getOrDefault [_class,[]];
    private _existing = if (_ages isEqualTo []) then {0} else {_ages deleteAt 0};
    _entries pushBack [_class,[_class] call ACME_fnc_coolerBagVolume,(_warm + _offline) max _existing,_now];
} forEach _ranked;
_store set [netId _holder,[_entries,_record select 1]];
missionNamespace setVariable ["ACME_ccByHolder",_store];
_holder setVariable ["ACME_bloodExposure",[_entries apply {[_x select 0,_x select 1,_x select 2]},_now],true];
_holder setVariable ["ACME_bloodRestoreReceipt",_key,false];
true
