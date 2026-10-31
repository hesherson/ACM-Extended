/* Local native materialization is idempotent; server proof retires the source. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_coolerBoxReply;};};
params ["_mode","_owner","_sid","_token","_request","_ok","_box","_revision",["_reason",""],["_entry",[]]];
if (isNull _owner || {!local _owner}) exitWith {};
private _requests=_owner getVariable ["ACME_coolerBoxRequests",createHashMap];
if (!(_request in _requests) && {_mode != "packAbort"}) exitWith {};
private _complete={
    _requests deleteAt _request; _owner setVariable ["ACME_coolerBoxRequests",_requests,true];
    private _intents=_owner getVariable ["ACME_coolerIntents",createHashMap]; _intents deleteAt _request; _owner setVariable ["ACME_coolerIntents",_intents,true];
};
private _callback={
    params ["_accepted"];
    private _callbacks=missionNamespace getVariable ["ACME_coolerBoxCallbacks",createHashMap];
    private _continuation=_callbacks getOrDefault [_request,[]];
    _callbacks deleteAt _request; missionNamespace setVariable ["ACME_coolerBoxCallbacks",_callbacks];
    if (_continuation isEqualTo [] || {(_continuation select 0) isNotEqualTo _owner}
        || {(_continuation select 2) != (_owner getVariable ["ACME_providerLocalityEpoch",0])}
        || {(_continuation select 3) != (_owner getVariable ["ACME_equipmentKitEpoch",0])}) exitWith {};
    private _handler=_continuation select 1;
    [_accepted,_handler param [1,[]]] call (_handler select 0);
};
if (!_ok) exitWith {
    call _complete;
    if (_mode == "deploy") then {[_owner,_request,false] call ACME_fnc_inventoryLedgerSettle;};
    if (_reason != "" && {hasInterface} && {_owner isEqualTo ACE_player}) then {[_reason,3] call ace_common_fnc_displayTextStructured;};
    [false] call _callback;
};
if (_mode == "draw") exitWith {
    private _delivered=_owner getVariable ["ACME_coolerDrawDelivered",createHashMap];
    if !(_request in _delivered) then {
        if (_entry isEqualTo [] || {!([_owner,_entry,true] call ACME_fnc_coolerGiveBag)}) exitWith {};
        _delivered set [_request,true]; _owner setVariable ["ACME_coolerDrawDelivered",_delivered,true];
    };
    if !(_request in (_owner getVariable ["ACME_coolerDrawDelivered",createHashMap])) exitWith {};
    ["ACME_coolerBoxBroker",["drawAck",_owner,_sid,_box,_request]] call CBA_fnc_serverEvent;
    // Keep durable retry state until the server acknowledgement (drawDone).
    [true] call _callback;
};
if (_mode == "drawDone") exitWith {call _complete;};
if (_mode == "packDone") exitWith {call _complete; [_owner] call ACME_fnc_inventoryLedgerReconcile; [true] call _callback;};
private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
if (count _record < 9 || {(_record select 0) != "cooler"} || {(_record select 1) != _sid} || {(_record select 6) < _revision}) exitWith {};
if (_mode == "packAbort") exitWith {
    if ((_record select 5) != "packingAbort" || {(_record select 4) != _request}) exitWith {};
    private _removed=_owner getVariable ["ACME_coolerPackRemoved",createHashMap];
    if !(_request in _removed) then {
        if !([_owner,_record select 8,_token] call ace_common_fnc_removeSpecificMagazine) exitWith {};
        _removed set [_request,_token]; _owner setVariable ["ACME_coolerPackRemoved",_removed,true];
    };
    if (_request in (_owner getVariable ["ACME_coolerPackRemoved",createHashMap])) then {
        ["ACME_coolerBoxBroker",["unplaced",_owner,_sid,_box,_request]] call CBA_fnc_serverEvent;
    };
};
if (_mode == "deploy") exitWith {
    // The server receipt proves that this exact escrow was converted to a box.
    private _escrow=_owner getVariable ["ACME_inventoryEscrow",createHashMap];
    private _held=_escrow getOrDefault [_request,[]];
    if (_held isNotEqualTo [] && {(_held select 0) == _token}) then {_escrow deleteAt _request; _owner setVariable ["ACME_inventoryEscrow",_escrow,true];};
    private _ledgerRequests=_owner getVariable ["ACME_inventoryRequests",createHashMap]; _ledgerRequests deleteAt _request; _owner setVariable ["ACME_inventoryRequests",_ledgerRequests,true];
    call _complete;
    [_owner] call ACME_fnc_inventoryLedgerReconcile;
    [true] call _callback;
};
if (_mode != "pack" || {(_record select 4) != _request}) exitWith {};
if ((_record select 5) == "held") exitWith {
    call _complete;
    [_owner] call ACME_fnc_inventoryLedgerReconcile;
    [true] call _callback;
};
if ((_record select 5) != "packing" || {(_record select 3) isNotEqualTo _owner}) exitWith {};
private _admission=_record param [9,[]];
if (_admission isNotEqualTo [] && {(_admission select 0) != (_owner getVariable ["ACME_equipmentKitEpoch",0])
    || {(_admission select 1) != (_owner getVariable ["ACME_providerLocalityEpoch",0])}}) exitWith {
    ["ACME_coolerBoxBroker",["cancel",_owner,_sid,_box,_request]] call CBA_fnc_serverEvent;
};
private _native=[_owner,"cooler"] call ACME_fnc_inventoryLedgerNative;
private _placed=_owner getVariable ["ACME_coolerPackPlaced",createHashMap];
if ((_native findIf {(_x select 0) == _token}) < 0 && {!(_request in _placed)}) then {
    private _class=_record select 8;
    if (_owner canAdd [_class,1,true]) then {_owner addMagazine [_class,_token];};
    if ((([_owner,"cooler"] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) < 0) then {
        private _destination=objNull;
        {if (!isNull _x) exitWith {_destination=_x;};} forEach [backpackContainer _owner,vestContainer _owner,uniformContainer _owner];
        if (!isNull _destination) then {_destination addMagazineAmmoCargo [_class,1,_token];};
    };
};
if ((([_owner,"cooler"] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) >= 0) then {
    // Once real placement happened, losing native custody is a Gear transfer,
    // never permission for a replayed ACK to create another physical token.
    _placed set [_request,_token]; _owner setVariable ["ACME_coolerPackPlaced",_placed,true];
    ["ACME_coolerBoxBroker",["placed",_owner,_sid,_box,_request]] call CBA_fnc_serverEvent;
};
