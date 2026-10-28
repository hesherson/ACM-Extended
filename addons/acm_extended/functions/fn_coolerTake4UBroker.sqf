/* Exact-cargo transfer, serialized by the server. Failed placement returns its
 * funded item to the source; if rollback also fails, the receipt retains custody
 * and a repeat retries it without a second debit or a timeout-created item. */
if (!isServer) exitWith {};
if (canSuspend) exitWith {isNil {_this call ACME_fnc_coolerTake4UBroker;};};
params ["_owner","_source","_class","_token","_request","_kit","_locality","_destination"];
if (isNull _owner || {!(_request isEqualType "")} || {_request==""}) exitWith {};
if !(_class isEqualType "" && {_token isEqualType 0} && {finite _token} && {_token==floor _token}
    && {_kit isEqualType 0} && {finite _kit} && {_locality isEqualType 0} && {finite _locality}) exitWith {};
private _arguments=+_this;
private _receipts=missionNamespace getVariable ["ACME_coolerTake4UReceipts",createHashMap];
private _receipt=_receipts getOrDefault [_request,[]];
private _reply={
    params ["_ok","_reason",["_terminal",true]];
    ["ACME_coolerTake4UDone",[_owner,_request,_ok,_reason,_terminal],_owner] call CBA_fnc_targetEvent;
};
private _count={
    params ["_container"];
    if (isNull _container) exitWith {0};
    if (_token>0) then {{_x isEqualTo [_class,_token]} count magazinesAmmoCargo _container}
    else {{_x==_class} count itemCargo _container}
};
private _adjust={
    params ["_container","_amount"];
    if (isNull _container) exitWith {};
    if (_token>0) then {_container addMagazineAmmoCargo [_class,_amount,_token];}
    else {_container addItemCargoGlobal [_class,_amount];};
};
private _admitted={
    alive _owner && {_kit==(_owner getVariable ["ACME_equipmentKitEpoch",0])}
        && {_locality==(_owner getVariable ["ACME_providerLocalityEpoch",0])}
        && {!isNull _destination}
        && {_destination in [backpackContainer _owner,vestContainer _owner,uniformContainer _owner]}
};
private _markSource={
    params ["_active"];
    if (isNull _source) exitWith {};
    private _claims=_source getVariable ["ACME_coolerTake4UClaims",createHashMap];
    private _present=_request in _claims;
    if (_active && {!_present}) then {_claims set [_request,true];_source setVariable ["ACME_coolerTake4UClaims",_claims,true];};
    if (!_active && {_present}) then {_claims deleteAt _request;_source setVariable ["ACME_coolerTake4UClaims",_claims,true];};
};
private _store={
    _receipts set [_request,_receipt];missionNamespace setVariable ["ACME_coolerTake4UReceipts",_receipts];
    if ((_receipt select 1) in ["done","failed"]) then {[false] call _markSource;};
};
if (_receipt isNotEqualTo []) then {
    if ((_receipt select 0) isNotEqualTo _arguments) exitWith {_receipt=[];};
};
if (_request in _receipts && {_receipt isEqualTo []}) exitWith {};
if (_receipt isNotEqualTo []) then {
    if ((_receipt select 1)=="done") exitWith {[true,"Golden Hour 4U loaded. Inventory overloaded."] call _reply;};
    if ((_receipt select 1)=="failed") exitWith {[false,_receipt select 3] call _reply;};
};
// Keep terminal branches at function scope: an inner exitWith would otherwise
// fall through and repeat a previously completed placement.
if (_receipt isNotEqualTo [] && {(_receipt select 1) in ["done","failed"]}) exitWith {};
if (_receipt isEqualTo []) then {
    private _parent=if (isNull _source) then {objNull} else {objectParent _source};
    private _allowed=(_token==0 && {_class=="ACME_BloodCooler_CSWB4U"})
        || {_token>0 && {_token<65535} && {_token==floor _token} && {_class=="ACME_CoolerCarrier_CSWB4U"}};
    if (!_allowed || {_owner getVariable ["ACME_persistenceFrozen",false]} || {_source getVariable ["ACME_persistenceFrozen",false]}
        || {isNull _source} || {_source isEqualTo _destination} || {_source isKindOf "CAManBase"}
        || {!isNull _parent && {_parent isKindOf "CAManBase"}} || {_owner distance _source>6} || {!(call _admitted)}) exitWith {
        _receipt=[_arguments,"failed",0,"The cooler pickup is no longer valid."];call _store;
    };
    if (_token>0) then {
        private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
        if (count _record<9 || {(_record select 0)!="cooler"} || {(_record select 5)!="held"} || {(_record select 8)!=_class}
            || {(((_record select 2) select 1) select 0)!="ACME_BloodCooler_CSWB4U"}) exitWith {
            _receipt=[_arguments,"failed",0,"This cooler is already in use."];call _store;
        };
    };
    if (_receipt isNotEqualTo []) exitWith {};
    private _sourceBefore=[_source] call _count;
    if (_sourceBefore<1 || {_token>0 && {_sourceBefore!=1}}) exitWith {
        _receipt=[_arguments,"failed",0,"The cooler is no longer in this cargo."];call _store;
    };
    private _destinationBefore=[_destination] call _count;
    if (_token>0 && {_destinationBefore!=0}) exitWith {
        _receipt=[_arguments,"failed",0,"The cooler is already present."];call _store;
    };
    [true] call _markSource;
    [_source,-1] call _adjust;
    if (([_source] call _count)!=_sourceBefore-1) exitWith {
        _receipt=[_arguments,"failed",0,"The cooler could not be removed from its cargo."];call _store;
    };
    _receipt=[_arguments,"held",_destinationBefore,""];
    call _store;
};
if ((_receipt select 1)=="failed") exitWith {[false,_receipt select 3] call _reply;};
if ((_receipt select 1)!="held") exitWith {};
private _placed=false;
if (call _admitted) then {
    private _before=[_destination] call _count;
    if (_before==(_receipt select 2)) then {
        [_destination,1] call _adjust;
        _placed=([_destination] call _count)==_before+1;
    };
};
if (_placed) exitWith {
    _receipt set [1,"done"];call _store;
    [true,"Golden Hour 4U loaded. Inventory overloaded."] call _reply;
};
private _sourceBefore=[_source] call _count;
[_source,1] call _adjust;
if (!isNull _source && {([_source] call _count)==_sourceBefore+1}) then {
    _receipt set [1,"failed"];_receipt set [3,"The cooler could not be placed; it remains in its source cargo."];call _store;
    [false,_receipt select 3] call _reply;
} else {
    [false,"The cooler is reserved for recovery. Retry this pickup to finish it.",false] call _reply;
};
