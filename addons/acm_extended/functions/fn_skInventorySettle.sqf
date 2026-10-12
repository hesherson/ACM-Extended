/* The current row already includes receipt refunds. Restore the same identity
 * with that exact final payload; a fully consumed syringe retires its token. */
params ["_owner","_request","_sid"];
if (isNull _owner || {!local _owner} || {_request == ""}) exitWith {false};
private _rows = _owner getVariable ["ACME_narcStore",[]];
private _at = _rows findIf {(_x param [11,"",[""]]) == _sid};
private _payload = [];
if (_at >= 0) then {
    private _row = _rows select _at;
    if ((_row param [2,0]) + (_row param [4,0]) > 0.0005) then {_payload = [_sid,+_row];};
};
private _hidden = _owner getVariable ["ACME_syringeInventoryHidden",[]];
_hidden = _hidden - [_sid];
_owner setVariable ["ACME_syringeInventoryHidden",_hidden,false];
[_owner,_request,_payload isEqualTo [],_payload] call ACME_fnc_inventoryLedgerSettle;
true
