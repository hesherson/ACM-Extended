/* Reserve one exact magazine in the provider's unscheduled frame before any network request. */
if (canSuspend) exitWith {private _receipt = []; isNil {_receipt = _this call ACME_fnc_inventoryLedgerReserve;}; _receipt};
params ["_owner","_kind","_sid","_request",["_adopting",false]];
if (isNull _owner || {!local _owner} || {_request == ""}) exitWith {[]};
private _escrow = _owner getVariable ["ACME_inventoryEscrow",createHashMap];
private _old = _escrow getOrDefault [_request,[]];
if !(_old isEqualTo []) exitWith {[_old select 0,+(_old select 1)]};
if (_owner getVariable ["ACME_persistenceFrozen",false]) exitWith {[]};
private _token = (missionNamespace getVariable ["ACME_inventoryLedgerIndex",createHashMap]) getOrDefault [_kind + ":" + _sid,0];
if (!_adopting && {str _token in (_owner getVariable ["ACME_inventoryIncoming",createHashMap]) || {_kind in (_owner getVariable ["ACME_inventoryIncomingKinds",[]])}}) exitWith {[]};
private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
if (count _record < 7 || {!_adopting && {(_record select 3) isNotEqualTo _owner}} || {(_record select 5) != "held"} || {(_record select 0) != _kind}
    || {(_record select 1) != _sid} || {(([_owner,_kind] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) < 0}) exitWith {[]};
private _prior = _record select 3;
if (_adopting && {!isNull _prior} && {_prior isNotEqualTo _owner}
    && {(([_prior,_kind] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) >= 0}) exitWith {[]};
private _cache = (_owner getVariable ["ACME_inventoryPayloadCache",createHashMap]) getOrDefault [_kind + ":" + _sid,[]];
private _payload = if (!(_cache isEqualTo []) && {(_cache select 1) > (_record select 6)}) then {+(_cache select 0)} else {+(_record select 2)};
// Wait for the exact latest settled payload before removing its carrier. Server update retries are durable.
if (_payload isNotEqualTo (_record select 2)) exitWith {[]};
private _class = _record param [8,["ACME_PreparedIVSet","ACME_PreparedSyringe"] select (_kind == "syringe")];
if !([_owner,_class,_token] call ace_common_fnc_removeSpecificMagazine) exitWith {[]};
_escrow set [_request,[_token,_payload,_kind,_request,_owner getVariable ["ACME_equipmentKitEpoch",0],false]];
_owner setVariable ["ACME_inventoryEscrow",_escrow,true];
[_token,_payload]
