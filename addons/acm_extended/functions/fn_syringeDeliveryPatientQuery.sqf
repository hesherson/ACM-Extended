/* The captured machine can prove execution, or permanently cancel an unseen
 * request. The tombstone precedes the reply, so a late packet after A-B-A cannot
 * apply a dose whose source has already been returned. No remote patient write. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_syringeDeliveryPatientQuery;};};
params ["_medic","_request","_session","_batchId","_id","_patient","_expectedOwner","_nonce"];
if (clientOwner != _expectedOwner || {_nonce == ""}
    || {(missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""]) != _nonce}) exitWith {};
private _decisions = missionNamespace getVariable ["ACME_syringeDeliveryPatientDecisions",createHashMap];
private _fingerprint = [_patient,_request,_session,_batchId,_nonce];
private _decision = _decisions getOrDefault [_id,[]];
if (!(_decision isEqualTo []) && {(_decision select 0) isNotEqualTo _fingerprint}) exitWith {};
if (_decision isEqualTo []) then {
    private _receipt = if (isNull _patient) then {[]} else {
        (_patient getVariable ["ACME_medicationReceiptsB14",createHashMap]) getOrDefault [_id,[]]
    };
    private _accepted = false;
    private _reason = "patient ownership changed before local execution";
    if (count _receipt >= 2) then {_accepted = _receipt select 0; _reason = _receipt select 1;};
    _decision = [_fingerprint,_accepted,_reason];
    _decisions set [_id,_decision];
    missionNamespace setVariable ["ACME_syringeDeliveryPatientDecisions",_decisions];
};
["ACME_syringeDelivery",["receipt",_medic,_request,clientOwner,[_session,_batchId,_id,_patient,_decision select 1,_decision select 2]]] call CBA_fnc_serverEvent;
