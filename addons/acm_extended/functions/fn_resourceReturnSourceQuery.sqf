/* The producer's private committed decision survives deletion of its patient
 * object. A merely staged or uncertain source write is never funding proof. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_resourceReturnSourceQuery;};};
if !(_this isEqualType [] && {count _this==5}) exitWith {};
params ["_provider","_patient","_request","_products","_certificate"];
if (([0,1,2,3,4] findIf {isNil {_this select _x}})>=0) exitWith {};
if !(_provider isEqualType objNull && {_patient isEqualType objNull} && {_request isEqualType ""}
    && {[_products] call ACME_fnc_resourceReturnProductsValid}
    && {_certificate isEqualType []} && {count _certificate==2}
    && {(_certificate select 0) isEqualType 0} && {finite (_certificate select 0)}
    && {(_certificate select 1) isEqualType ""}) exitWith {};
_certificate params ["_owner","_nonce"];
if (clientOwner!=_owner || {_nonce==""}
    || {(missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""])!=_nonce}) exitWith {};
private _all=missionNamespace getVariable ["ACME_resourceReturnSources",createHashMap];
private _record=_all getOrDefault [_request,[]];
if (count _record!=3 || {(_record select 0) isNotEqualTo [_provider,_patient,_products,_nonce]}
    || {!((_record select 1) in ["funded","admitted"])} || {(_record select 2) isNotEqualTo _certificate}) exitWith {};
["ACME_resourceReturn",["sourceProof",[_provider,_patient,_request,_products,_certificate]]] call CBA_fnc_serverEvent;
