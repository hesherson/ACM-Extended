/* B279: source-funded Narc Box rows are carried by an opaque inventory identity.
 * Native ACM medication magazines retain their 0.01 mL quantization when upgraded;
 * the exact magazine is removed before its one token is registered. Public commits
 * are settlement boundaries. Private 20 Hz plunger writes never reach this helper.
 */
params ["_owner", ["_rows", [], [[]]]];
if (isNull _owner || {!local _owner}) exitWith {_rows};
private _out = +_rows;
private _serial = _owner getVariable ["ACME_narcStoreSerial", 0];
private _payloads = [];
private _seen = [];
{
    if !(_x isEqualType [] && {count _x >= 3}) then {continue};
    private _row = +_x;
    private _size = _row param [1, 0, [0]];
    private _drug = _row param [2, 0, [0]];
    private _saline = _row param [4, 0, [0]];
    if !(_size in [1,3,5,10] && {finite _drug} && {_drug >= 0} && {finite _saline} && {_saline >= 0}
        && {_drug + _saline > 0} && {_drug + _saline <= _size + 0.001}) then {continue};
    while {count _row < 14} do {_row pushBack "";};
    private _sid = _row param [11, "", [""]];
    if (_sid == "" || {_sid in _seen}) then {
        _serial = _serial + 1;
        _sid = format ["ACME_SYR_%1_%2_%3", clientOwner, floor (diag_tickTime * 1000), _serial];
        _row set [11, _sid];
    };
    _seen pushBack _sid;
    private _backed = (_row param [13, "", [""]]) == "inventoryB279";
    if (!_backed) then {
        private _kind = _row param [6, "", [""]];
        if (_kind in ["compoundB13","dilutionB13","epiMixB12"]) then {_backed = true;} else {
            private _med = _row param [0, "", [""]];
            private _class = format ["ACM_Syringe_%1_%2", _size, _med];
            private _ammo = round (_drug * 100);
            private _container = objNull;
            {
                if (!isNull _x && {((magazinesAmmoCargo _x) findIf {(_x select 0) == _class && {(_x select 1) == _ammo}}) >= 0}) exitWith {_container = _x;};
            } forEach [uniformContainer _owner,vestContainer _owner,backpackContainer _owner];
            if (!isNull _container && {_ammo > 0}) then {
                _container addMagazineAmmoCargo [_class,-1,_ammo];
                _row set [2, _ammo / 100];
                _backed = true;
            };
        };
        if (_backed) then {_row set [13,"inventoryB279"];};
    };
    _out set [_forEachIndex, _row];
    if (_backed) then {_payloads pushBack [_sid,+_row];};
} forEach _rows;
_owner setVariable ["ACME_narcStoreSerial",_serial,false];
[_owner,"syringe",_payloads] call ACME_fnc_inventoryLedgerCommit;
_out
