/* Take can precede metadata publication. Block the kind synchronously, then certify every held matching token. */
params ["_owner",["_kind",""]];
if (isNull _owner || {!local _owner}) exitWith {};
private _incoming = _owner getVariable ["ACME_inventoryIncoming",createHashMap];
private _kinds = _owner getVariable ["ACME_inventoryIncomingKinds",[]];
if (_kind != "") then {_kinds pushBackUnique _kind;};
{
    _incoming set [str (_x select 0),_x select 1];
    _kinds pushBackUnique (_x select 1);
} forEach ([_owner,_kind] call ACME_fnc_inventoryLedgerNative);
_owner setVariable ["ACME_inventoryIncoming",_incoming,true];
_owner setVariable ["ACME_inventoryIncomingKinds",_kinds,true];
