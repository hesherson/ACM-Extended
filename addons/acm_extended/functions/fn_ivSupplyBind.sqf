/* B236. Bind an actual local supply reservation to exactly one IV request.
   Donor and vehicle provenance remain the original ACE/EFAK receipt. This is a
   trusted-client reservation boundary, not authentication of arbitrary scripts. */
params ["_medic","_patient","_uid","_action","_token","_epoch","_deadline","_receipt"];
if (isNull _medic || {!local _medic} || {isNull _patient}) exitWith {false};
if !(_receipt isEqualType [] && {count _receipt==4}
    && {(_receipt select 0) isEqualType objNull} && {(_receipt select 1) isEqualType ""}
    && {(_receipt select 2) isEqualType objNull} && {(_receipt select 3) isEqualType ""}
    && {(_receipt select 3)!=""} && {count (_receipt select 3)<=120}
    && {_deadline isEqualType 0} && {finite _deadline} && {_deadline>=serverTime}
    && {_deadline<=serverTime+100}) exitWith {false};
private _stock=missionNamespace getVariable ["ACME_supplyReceipts",createHashMap];
private _scopes=missionNamespace getVariable ["ACME_IV_SupplyScopes",createHashMap];
if !(_stock isEqualType createHashMap && {_scopes isEqualType createHashMap}) exitWith {false};
// Expired unknown outcomes are committed, never refunded or rebound. Cleanup
// is demand-driven and only touches reservations owned by this IV subsystem.
{
    private _old=_scopes get _x;
    if (_old isEqualType [] && {count _old==8} && {(_old select 6) isEqualType 0} && {(_old select 6)+30<serverTime}) then {
        if ((_stock getOrDefault [_x,[]]) isEqualTo (_old select 0)) then {_stock deleteAt _x;};
        _scopes deleteAt _x;
    };
} forEach keys _scopes;
private _id=_receipt select 3;
if !((_stock getOrDefault [_id,[]]) isEqualTo _receipt) exitWith {false};
private _scope=[+_receipt,_patient,_uid,_action,_token,_epoch,_deadline,_medic];
private _existing=_scopes getOrDefault [_id,[]];
if (_existing isNotEqualTo [] && {!(_existing isEqualTo _scope)}) exitWith {false};
private _bindings=_medic getVariable ["ACME_IV_SupplyBindings",[]];
if !(_bindings isEqualType [] && {count _bindings<=64}) exitWith {false};
_bindings=_bindings select {_x isEqualType [] && {count _x==8} && {(_x select 6) isEqualType 0} && {(_x select 6)+30>=serverTime}};
if (count _bindings>=64 && {(_bindings findIf {_x isEqualTo _scope})<0}) exitWith {false};
_bindings pushBackUnique _scope;
_scopes set [_id,_scope];
missionNamespace setVariable ["ACME_IV_SupplyScopes",_scopes];
_medic setVariable ["ACME_IV_SupplyBindings",_bindings,true];
true
