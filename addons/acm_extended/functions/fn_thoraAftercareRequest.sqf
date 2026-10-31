/* One discrete surgical-tract input, identified before crossing patient locality. */
params ["_patient", "_medic", "_side", "_operation", ["_usedKit", false], ["_receipt", []]];
if (isNull _patient || {isNull _medic}) exitWith {};
private _sequence = (missionNamespace getVariable ["ACME_pleuralDrainSequence", 0]) + 1;
missionNamespace setVariable ["ACME_pleuralDrainSequence", _sequence];
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _request = [clientOwner, _sequence, serverTime];
private _packet = [_patient, "thoraAftercare", [_patient, _medic, _side, _operation, _epoch, _request, _usedKit, _receipt]];
if (_operation in ["widen", "seal"]) then {
    private _pendingKey = if (_operation == "seal") then {"ACME_Thora_SealPending"} else {"ACME_Thora_WidenPending"};
    uiNamespace setVariable [_pendingKey, [_patient, _side, _epoch, diag_tickTime, _request]];
};
_packet call ACME_fnc_ownerDispatch;
if !(_receipt isEqualTo []) then {
    // Query the SAME transaction; seals keep reconciling until settled, while
    // widening retains its single legacy query. Never refund on timeout alone.
    [ACME_fnc_thoraAftercareRetry, [_packet, _receipt], 16] call CBA_fnc_waitAndExecute;
};
