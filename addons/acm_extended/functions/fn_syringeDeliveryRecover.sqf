/* Ownership recovery closes old flow; it never reconstructs a plunger worker.
 * Registration is frequent, so only an actual local period (or explicit fresh
 * kit replacement) sends recovery. Server journals do not depend on replication. */
params ["_medic",["_force",false]];
if (isNull _medic || {!local _medic}) exitWith {false};
private _period = [clientOwner,_medic getVariable ["ACME_providerLocalityEpoch",0]];
if (!_force && {(_medic getVariable ["ACME_syringeDeliveryRecoveryPeriod",[]]) isEqualTo _period}) exitWith {false};
_medic setVariable ["ACME_syringeDeliveryRecoveryPeriod",_period,false];
["recover",_medic,"",[]] call ACME_fnc_syringeDeliveryRequest
