/* Recover serializable custody intent after locality changes or delayed ACKs. */
params ["_owner"];
if (isNull _owner || {!local _owner}) exitWith {};
private _requests=_owner getVariable ["ACME_coolerBoxRequests",createHashMap];
private _intents=_owner getVariable ["ACME_coolerIntents",createHashMap];
private _native=[_owner,"cooler"] call ACME_fnc_inventoryLedgerNative;
if (count _requests == 0 && {count _intents == 0} && {_native isEqualTo []}) exitWith {};
private _requestsChanged=false;
{
    private _args=+_y;
    if (serverTime >= (_args param [5,0])) then {
        _args set [5,serverTime+1]; _requests set [_x,_args];
        _requestsChanged=true;
        ["ACME_coolerBoxBroker",(_args select [0,5])+[_args param [6,-1],_args param [7,-1]]] call CBA_fnc_serverEvent;
    };
} forEach _requests;
if (_requestsChanged) then {_owner setVariable ["ACME_coolerBoxRequests",_requests,true];};
private _intentsChanged=false;
private _escrow=_owner getVariable ["ACME_inventoryEscrow",createHashMap];
private _callbacks=missionNamespace getVariable ["ACME_inventoryCallbacks",createHashMap];
{
    private _request=_x;
    private _held=_escrow getOrDefault [_request,[]];
    if (_held isEqualTo []) then {_intents deleteAt _request; _intentsChanged=true; continue;};
    if (_request in _requests || {_request in _callbacks}) then {continue;};
    private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_held select 0],[]];
    if (count _record < 9 || {(_record select 4) != _request}) then {continue;};
    if ((_record select 5) == "reserved") then {
        private _intent=_y;
        if ((_intent select 0) == "mutationResult") then {[_owner,_request,_intent select 2,_intent select 3] call ACME_fnc_inventoryLedgerSettle;}
        else {[_owner,_request,false] call ACME_fnc_inventoryLedgerSettle;};
    };
} forEach _intents;
if (_intentsChanged) then {_owner setVariable ["ACME_coolerIntents",_intents,true];};
// A token may be moved through Gear before its packing ACK is received. Its
// real current holder can finish placement; this never creates another token.
{
    private _token=_x select 0;
    private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
    if (count _record >= 11 && {(_record select 5) == "spent"} && {(_record select 10) == "coolerKitRetirement"}) then {
        [_owner,_record select 8,_token] call ace_common_fnc_removeSpecificMagazine;
    };
    if (count _record >= 9 && {(_record select 5) in ["packing","packingAbort"]}) then {
        private _box=objNull;
        private _boxMap=missionNamespace getVariable ["ACME_coolerPackingBoxes",createHashMap];
        _box=_boxMap getOrDefault [str _token,objNull];
        if (!isNull _box) then {["ACME_coolerBoxBroker",["placed",_owner,_record select 1,_box,_record select 4]] call CBA_fnc_serverEvent;};
    };
} forEach _native;
