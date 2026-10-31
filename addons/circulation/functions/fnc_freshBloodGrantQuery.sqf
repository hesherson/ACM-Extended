#include "..\script_component.hpp"
/* Only the captured machine incarnation can prove delivery or cancel an unseen
 * attempt. The cancellation precedes any permission for another owner to add. */
if (canSuspend) exitWith {isNil {_this call FUNC(freshBloodGrantQuery);};};
if !(_this isEqualType [] && {count _this==8}) exitWith {};
params ["_medic","_volume","_id","_request","_facts","_expectedOwner","_nonce","_attempt"];
if (([0,1,2,3,4,5,6,7] findIf {isNil {_this select _x}})>=0) exitWith {};
if !(_medic isEqualType objNull && {_volume isEqualType 0} && {_id isEqualType 0} && {finite _id}
    && {_request isEqualType ""} && {_facts isEqualType []} && {_expectedOwner isEqualType 0}
    && {finite _expectedOwner} && {_nonce isEqualType ""} && {_attempt isEqualType 0} && {finite _attempt}) exitWith {};
if (clientOwner!=_expectedOwner || {_nonce==""}
    || {(missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""])!=_nonce}) exitWith {};
private _all=missionNamespace getVariable [QGVAR(FreshBloodGrantDecisions),createHashMap];
private _key=format ["%1:%2",_request,_attempt];
private _fingerprint=[_medic,_volume,_id,+_facts,_nonce];
private _decision=_all getOrDefault [_key,[]];
if (_decision isNotEqualTo [] && {(_decision select 0) isNotEqualTo _fingerprint}) exitWith {};
if (_decision isEqualTo [] || {(_decision select 1)=="unplaced"}) then {
    _decision=[_fingerprint,"cancelled"];_all set [_key,_decision];missionNamespace setVariable [QGVAR(FreshBloodGrantDecisions),_all];
};
[QGVAR(freshBloodGrantDecision),[_medic,_request,_id,_facts,clientOwner,_nonce,_attempt,_decision select 1]] call CBA_fnc_serverEvent;
