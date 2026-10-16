/* Original request-machine supply settlement; never follows provider locality. */
params ["_patient", "_side", "_epoch", "_request", "_receipt", "_accepted", ["_operation", "widen"]];
if !(_receipt isEqualTo []) then {[_receipt, !_accepted] call ACME_fnc_treatmentSupplyRefund;};
private _pendingKey = if (_operation == "seal") then {"ACME_Thora_SealPending"} else {"ACME_Thora_WidenPending"};
private _pending = uiNamespace getVariable [_pendingKey, []];
if (count _pending >= 5 && {(_pending select 0) isEqualTo _patient}
    && {(_pending select 1) == _side} && {(_pending select 2) == _epoch}
    && {(_pending select 4) isEqualTo _request}) then {
    uiNamespace setVariable [_pendingKey, []];
    if (!_accepted && {hasInterface}) then {
        ["Thoracostomy state changed; check the current tract and retry.", 3] call ace_common_fnc_displayTextStructured;
    };
};
