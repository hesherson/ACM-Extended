// Direct Pressure entry. Every body region now uses the same non-blocking persistent hold model.
// The clinical pressure state remains active while ordinary medical work is performed, but real ACM maneuvers
// temporarily suspend it and movement yields the provider pose. The same action can then release the hold.
params ["_medic", "_patient", ["_bodyPart", ""]];
_bodyPart = toLower _bodyPart;
if (isNull _medic || {isNull _patient}) exitWith {};

// Every region needs this provider's hands. Reject before cleanup can touch the input hints or animation of
// BVM, CPR or another continuous maneuver. CPR is native and does not use ContinuousAction_Active.
private _providerManeuver = (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])
    || {_medic getVariable ["ACM_circulation_isPerformingCPR", false]}
    || {_medic getVariable ["ACM_breathing_isUsingBVM", false]}
    || {[_patient] call ACM_core_fnc_cprActive}
    || {[_patient] call ACM_core_fnc_bvmActive};
if (_providerManeuver) exitWith {
    ["Another active maneuver is already in progress.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

if (_medic getVariable ["ACME_DP_Active", false]) exitWith {
    ["You're already holding direct pressure.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
if !((_medic getVariable ["ACME_DP_ClaimPending", []]) isEqualTo []) exitWith {
    ["Direct pressure is already being started.", 1.5, _medic] call ace_common_fnc_displayTextStructured;
};

// Clear stale provider-local presentation from an interrupted prior episode, then atomically reserve this patient
// body part on the casualty owner. No pressure pose or clinical effect begins until that owner accepts the claim.
[true, _medic] call ACME_fnc_directPressureStop;
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _token = format ["%1:%2:%3:%4", owner _medic, netId _medic, diag_frameNo, serverTime];
_medic setVariable ["ACME_DP_ClaimPending", [_patient, _bodyPart, _token, _epoch], false];
_medic setVariable ["ACME_DP_ClaimRequestedAt", diag_tickTime, false];
[_patient, "directPressureClaim", ["claim", [_medic, _bodyPart, _token, _epoch, owner _medic]]] call ACME_fnc_ownerDispatch;
