/* An old ownership period either proves delivery or cancels an unseen attempt
 * before the server authorizes another period. Partial/unknown writes stay held. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_resourceReturnQuery;};};
if !(_this isEqualType [] && {count _this==7}) exitWith {};
params ["_provider","_patient","_request","_products","_expectedOwner","_nonce","_attempt"];
if (([0,1,2,3,4,5,6] findIf {isNil {_this select _x}})>=0) exitWith {};
if !(_provider isEqualType objNull && {_patient isEqualType objNull} && {_request isEqualType ""}
    && {[_products] call ACME_fnc_resourceReturnProductsValid} && {_expectedOwner isEqualType 0}
    && {finite _expectedOwner} && {_nonce isEqualType ""} && {_attempt isEqualType 0}
    && {finite _attempt} && {_attempt>=1} && {_attempt==floor _attempt}) exitWith {};
if (clientOwner!=_expectedOwner || {_nonce==""}
    || {(missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""])!=_nonce}) exitWith {};
private _all=missionNamespace getVariable ["ACME_resourceReturnDecisions",createHashMap];
private _key=format ["%1:%2",_request,_attempt];
private _fingerprint=[_provider,_patient,[_products] call ACME_fnc_syringeDeliveryCopy,_nonce];
private _decision=_all getOrDefault [_key,[]];
if (_decision isNotEqualTo [] && {(_decision select 0) isNotEqualTo _fingerprint}) exitWith {};
if (_decision isEqualTo [] || {(_decision select 1)=="unplaced"}) then {
    _decision=[_fingerprint,"cancelled"];_all set [_key,_decision];missionNamespace setVariable ["ACME_resourceReturnDecisions",_all];
};
["ACME_resourceReturn",["decision",[_provider,_patient,_request,_products,clientOwner,_nonce,_attempt,_decision select 1]]] call CBA_fnc_serverEvent;
