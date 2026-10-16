/* Native Gear transfer is followed by server-certified adoption before a receiver can edit/debit contents. */
params ["_owner","_kind","_token",["_force",false]];
if (isNull _owner || {!local _owner}) exitWith {false};
private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
if (count _record < 7 || {(_record select 5) != "held"} || {!_force && {(_record select 3) isEqualTo _owner}}) exitWith {false};
private _escrow = _owner getVariable ["ACME_inventoryEscrow",createHashMap];
if ((values _escrow findIf {(_x param [0,0]) == _token}) >= 0) exitWith {false};
private _cache = _owner getVariable ["ACME_inventoryPayloadCache",createHashMap];
_cache deleteAt (_kind + ":" + (_record select 1)); _owner setVariable ["ACME_inventoryPayloadCache",_cache,false];
private _serial = (missionNamespace getVariable ["ACME_inventoryAdoptSerial",0])+1; missionNamespace setVariable ["ACME_inventoryAdoptSerial",_serial];
private _request = format ["inventory-adopt:%1:%2:%3",clientOwner,_token,_serial];
private _receipt = [_owner,_kind,_record select 1,_request,true] call ACME_fnc_inventoryLedgerReserve;
if (_receipt isEqualTo []) exitWith {false};
private _adoptions = _owner getVariable ["ACME_inventoryAdoptions",createHashMap]; _adoptions set [_request,_token]; _owner setVariable ["ACME_inventoryAdoptions",_adoptions,true];
[_owner,_request,{
    params ["_accepted","_args"]; _args params ["_owner","_request"];
    // Rejected stale snapshots return the current canonical payload, with no source-funded edit to merge/refund.
    [_owner,_request,false] call ACME_fnc_inventoryLedgerSettle;
},[_owner,_request]] call ACME_fnc_inventoryLedgerClaim;
true
