/* Projection is driven by physical native possession. Ordinary Gear transfer moves identity plus all metadata. */
params ["_owner"];
if (isNull _owner || {!local _owner}) exitWith {};
private _incoming = _owner getVariable ["ACME_inventoryIncoming",createHashMap];
private _kinds = _owner getVariable ["ACME_inventoryIncomingKinds",[]];
private _incomingChanged = false;
{
    if ((_x select 1) in _kinds && {!(str (_x select 0) in _incoming)}) then {_incoming set [str (_x select 0),_x select 1]; _incomingChanged = true;};
} forEach ([_owner] call ACME_fnc_inventoryLedgerNative);
if (_incomingChanged) then {_owner setVariable ["ACME_inventoryIncoming",_incoming,true];};
if (_kinds isNotEqualTo []) then {_owner setVariable ["ACME_inventoryIncomingKinds",[],true];};
{
    private _force = str (_x select 0) in _incoming;
    private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_x select 0],[]];
    if (count _record >= 7 && {_force || {(_record select 3) isNotEqualTo _owner}}) then {[_owner,_x select 1,_x select 0,_force] call ACME_fnc_inventoryLedgerAdopt;};
} forEach ([_owner] call ACME_fnc_inventoryLedgerNative);
private _adoptions = _owner getVariable ["ACME_inventoryAdoptions",createHashMap];
private _escrow = (values (_owner getVariable ["ACME_inventoryEscrow",createHashMap])) select {(_x select 4) == (_owner getVariable ["ACME_equipmentKitEpoch",0]) && {!((_x select 3) in _adoptions)}};
private _pending = (values (_owner getVariable ["ACME_inventoryPending",createHashMap])) select {(_x select 3) == (_owner getVariable ["ACME_equipmentKitEpoch",0])};
private _cache = _owner getVariable ["ACME_inventoryPayloadCache",createHashMap];
private _native = [_owner] call ACME_fnc_inventoryLedgerNative;
private _index = missionNamespace getVariable ["ACME_inventoryLedgerIndex",createHashMap];
{
    private _key = _x;
    private _token = _index getOrDefault [_x,0];
    private _held = (_native findIf {(_x select 0) == _token}) >= 0;
    private _reserved = (_escrow findIf {(_x select 0) == _token}) >= 0;
    private _funded = (_pending findIf {((_x select 0) + ":" + (_x select 1)) == _key}) >= 0;
    if (!_held && {!_reserved} && {!_funded}) then {_cache deleteAt _x;};
} forEach _cache;
_owner setVariable ["ACME_inventoryPayloadCache",_cache,false];
private _physical = [_owner,"prepared"] call ACME_fnc_inventoryLedgerRows;
private _payloads = +_physical;
private _mutations = _owner getVariable ["ACME_inventoryMutations",createHashMap];
// Reserved rows remain visible for the existing request receipts but cannot be selected twice (native gate).
{if ((_x select 2) == "prepared" && {(_x select 4) == (_owner getVariable ["ACME_equipmentKitEpoch",0])}) then {_payloads pushBack +(_mutations getOrDefault [_x select 3,_x select 1]);};} forEach _escrow;
{if ((_x select 0) == "prepared" && {(_x select 3) == (_owner getVariable ["ACME_equipmentKitEpoch",0])}) then {_payloads pushBack +(_x select 2);};} forEach _pending;
private _sets = []; private _meds = [];
{
    private _set = +(_x select 1);
    if ((_sets findIf {(_x select 0) == (_set select 0)}) < 0) then {_sets pushBack _set;};
    private _med = +(_x param [2,[]]);
    if !(_med isEqualTo []) then {_med set [11,0]; _med set [12,_owner]; _med set [13,objNull]; _meds pushBack _med;};
} forEach _payloads;
if (_sets isNotEqualTo (_owner getVariable ["ACME_preparedIVSets",[]])) then {_owner setVariable ["ACME_preparedIVSets",_sets,true]; uiNamespace setVariable ["ACME_preparedRowSig","__force__"];};
if (_meds isNotEqualTo (_owner getVariable ["ACME_infusion_PreparedBags",[]])) then {_owner setVariable ["ACME_infusion_PreparedBags",_meds,true];};
if (!isNil "ACME_fnc_skInventoryReconcile") then {
    private _reservedS = (_escrow select {(_x select 2) == "syringe"}) apply {+(_x select 1)};
    private _pendingS = (_pending select {(_x select 0) == "syringe"}) apply {+(_x select 2)};
    [_owner,[_owner,"syringe"] call ACME_fnc_inventoryLedgerRows,_reservedS,_pendingS] call ACME_fnc_skInventoryReconcile;
};
