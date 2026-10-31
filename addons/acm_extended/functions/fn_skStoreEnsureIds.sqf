/* B59: normalize prepared-syringe records and give every physical/virtual syringe a stable identity.
   Store indexes are presentation order only. The ID at slot 11 is the identity used by the carousel,
   Body Map preview and ACE self interactions. Existing B58 records are upgraded in place on first use. */
params [["_owner", ACE_player, [objNull]]];
if (isNull _owner) exitWith {[]};

private _store = +(_owner getVariable ["ACME_narcStore", []]);
private _changed = false;
if (local _owner && {!isNil "ACME_fnc_inventoryLedgerCommit"}) then {
    private _imported = [_owner,_store] call ACME_fnc_skInventoryImportNative;
    _changed = !(_imported isEqualTo _store);
    _store = _imported;
    if ((_store findIf {count _x >= 3 && {(_x param [13,"",[""]]) != "inventoryB279"}}) >= 0) then {_changed = true;};
};
private _seen = [];
private _serial = _owner getVariable ["ACME_narcStoreSerial", 0];

for "_i" from 0 to ((count _store) - 1) do {
    private _row = +(_store select _i);
    if ((count _row) < 12) then {
        while {(count _row) < 12} do {_row pushBack "";};
        _changed = true;
    };

    private _id = _row param [11, "", [""]];
    if (_id == "" || {_id in _seen}) then {
        _serial = _serial + 1;
        _id = format ["ACME_SYR_%1_%2_%3", clientOwner, floor (diag_tickTime * 1000), _serial];
        while {_id in _seen} do {
            _serial = _serial + 1;
            _id = format ["ACME_SYR_%1_%2_%3", clientOwner, floor (diag_tickTime * 1000), _serial];
        };
        _row set [11, _id];
        _changed = true;
    };
    _seen pushBack _id;
    _store set [_i, _row];
};

_owner setVariable ["ACME_narcStoreSerial", _serial, false];
if (_changed) then {[_owner, _store] call ACME_fnc_narcStoreCommit;};
_store
