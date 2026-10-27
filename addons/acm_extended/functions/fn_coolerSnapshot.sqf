/* [holder, optional scope]. JSON-safe state for CBA extended loadouts or a mission adapter.
 * [] means NOT saveable yet (pending custody, mutation, or malformed state), never an empty cooler.
 * Timers are stored as elapsed coolant seconds and accumulated per-bag warm seconds. */
params ["_holder",["_scope",""]];
if (isNull _holder) exitWith {[]};
if ((_holder getVariable ["ACME_coolerTake4UPending",[]]) isNotEqualTo [] || {count (_holder getVariable ["ACME_coolerTake4UClaims",createHashMap])>0}) exitWith {[]};
private _boxClasses = ["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"];
if (_scope == "") then {_scope = ["holder","box"] select ((typeOf _holder) in _boxClasses);};
if !(_scope in ["holder","box"]) exitWith {[]};
private _now = serverTime;
private _records = [];
private _ready = false;
if (_scope == "box") then {
    if (!isServer || {!((typeOf _holder) in _boxClasses)}) exitWith {};
    // A packing box and its unusable native carrier are one transaction, not
    // two independently saveable objects. Retired shells own no cooler state.
    if (_holder getVariable ["ACME_coolerPacking",false]
        || {_holder getVariable ["ACME_coolerRetired",false]}) exitWith {};
    private _state = [_holder,_now] call ACME_fnc_coolerBoxReconcile;
    if !(_state isEqualType [] && {count _state == 4}) exitWith {};
    private _sid = _holder getVariable ["ACME_boxCoolerSID",""];
    if (_sid == "") then {_sid = _holder getVariable ["ACME_boxCoolerId",""];};
    if (_sid == "") then {
        _sid = format ["cooler-box-save:%1:%2",_now,random 1e9];
        _holder setVariable ["ACME_boxCoolerId",_sid,true];
    };
    _records pushBack [_sid,0,_state select 0,(_now - (_state select 1)) max 0,(_state select 2) apply {+_x}];
    _ready = true;
} else {
    private _pending = _holder getVariable ["ACME_inventoryPending",createHashMap];
    private _escrow = _holder getVariable ["ACME_inventoryEscrow",createHashMap];
    private _restore = _holder getVariable ["ACME_coolerRestoreJournal",[]];
    private _blocked = ((keys _pending) findIf {((_pending get _x) param [0,""]) == "cooler"}) >= 0
        || {((keys _escrow) findIf {((_escrow get _x) param [2,""]) == "cooler"}) >= 0}
        || {count (_holder getVariable ["ACME_coolerBoxRequests",createHashMap]) > 0}
        || {count (_holder getVariable ["ACME_coolerIntents",createHashMap]) > 0}
        || {count _restore == 6 && {!(_restore select 3)}};
    if (_blocked) exitWith {};
    private _native = [_holder,"cooler"] call ACME_fnc_inventoryLedgerNative;
    private _rows = [_holder] call ACME_fnc_coolerRows;
    // Unknown, not-yet-adopted, or duplicated native tokens cannot silently become empty metadata.
    if (count _native != count _rows) exitWith {};
    private _index = missionNamespace getVariable ["ACME_inventoryLedgerIndex",createHashMap];
    private _ok = true;
    {
        _x params ["_sid","_raw"];
        private _state = [_raw,_now] call ACME_fnc_coolerAdvance;
        private _token = _index getOrDefault ["cooler:" + _sid,0];
        if (count _state != 4 || {(_native findIf {(_x select 0) == _token}) < 0}) exitWith {_ok = false;};
        _records pushBack [_sid,_token,_state select 0,(_now - (_state select 1)) max 0,(_state select 2) apply {+_x}];
    } forEach _rows;
    _ready = _ok;
};
if (!_ready) exitWith {[]};
private _snapshot = [1,_scope,_records];
if !([_snapshot] call ACME_fnc_coolerSnapshotValid) exitWith {[]};
_snapshot
