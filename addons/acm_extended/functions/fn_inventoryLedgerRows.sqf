params ["_owner", "_kind"];
private _rows = [];
private _incoming = _owner getVariable ["ACME_inventoryIncoming",createHashMap];
if (_kind in (_owner getVariable ["ACME_inventoryIncomingKinds",[]])) exitWith {[]};
{
    private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1", _x select 0], []];
    if (!(str (_x select 0) in _incoming) && {count _record >= 7} && {(_record select 0) == _kind} && {(_record select 5) == "held"} && {(_record select 3) isEqualTo _owner}) then {
        private _cache = (_owner getVariable ["ACME_inventoryPayloadCache",createHashMap]) getOrDefault [_kind + ":" + (_record select 1),[]];
        private _payload = if (!(_cache isEqualTo []) && {(_cache select 1) > (_record select 6)}) then {_cache select 0} else {_record select 2};
        _rows pushBack +_payload;
    };
} forEach ([_owner, _kind] call ACME_fnc_inventoryLedgerNative);
_rows
