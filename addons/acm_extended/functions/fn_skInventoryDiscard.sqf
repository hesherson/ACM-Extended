/* Discard consumes the same token used by native inventory transfer. */
params ["_owner","_row"];
private _request = [_owner,_row] call ACME_fnc_skInventoryReserve;
if (_request == "") exitWith {false};
[_owner,_request,{
    params ["_accepted","_args"];
    _args params ["_owner","_row","_request"];
    private _sid = _row param [11,"",[""]];
    if (!_accepted) exitWith {[_owner,_request,false,[_sid,_row]] call ACME_fnc_inventoryLedgerSettle;};
    private _rows = +(_owner getVariable ["ACME_narcStore",[]]);
    private _at = _rows findIf {(_x param [11,"",[""]]) == _sid};
    if (_at >= 0) then {_rows deleteAt _at;};
    private _hidden = _owner getVariable ["ACME_syringeInventoryHidden",[]];
    _hidden pushBackUnique _sid;
    _owner setVariable ["ACME_syringeInventoryHidden",_hidden,false];
    [_owner,_rows] call ACME_fnc_narcStoreCommit;
    [_owner,_request,true] call ACME_fnc_inventoryLedgerSettle;
    if (hasInterface && {_owner isEqualTo ACE_player}) then {
        uiNamespace setVariable ["ACME_SK_DiscardArmedId",""];
        uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
        [_at] call ACME_fnc_skAfterStoredRemoval;
        call ACME_fnc_skBodyActionRender;
    };
},[_owner,+_row,_request]] call ACME_fnc_inventoryLedgerClaim;
true
