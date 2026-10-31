/* Settle one exact reservation at the physical provider's current owner. The
 * published escrow permits recovery after NPC/provider-locality transfer. */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_lineWarmerAck;};
    _result
};
params ["_patient", "_medic", "_id", "_accepted", "_receipt", ["_message", "", [""]], ["_attempt", 0, [0]]];
if (isNull _patient || {isNull _medic} || {!local _medic}) exitWith {false};
private _escrows = _medic getVariable ["ACME_lineWarmerEscrow", createHashMap];
private _escrow = _escrows getOrDefault [_id, []];
if (count _escrow != 2) exitWith {
    // On provider-locality handoff the result can reach the new owner before
    // that unit's public escrow. Missing evidence must wait, never settle twice.
    if (_attempt < 20) then {
        [{_this call ACME_fnc_lineWarmerAck;}, [_patient, _medic, _id, _accepted, _receipt, _message, _attempt + 1], 0.1] call CBA_fnc_waitAndExecute;
    };
    false
};
if (_escrow select 1) exitWith {false};
private _request = _escrow select 0;
if (!((_request select 0) isEqualTo _patient) || {!((_request select 1) isEqualTo _medic)}
    || {!((_request select 9) isEqualTo _receipt)}) exitWith {false};
private _result = (_patient getVariable ["ACME_lineWarmerResults", createHashMap]) getOrDefault [_id, []];
if (count _result != 4 || {!((_result select 0) isEqualTo _request)} || {!((_result select 1) isEqualTo _accepted)}) exitWith {
    if (_attempt < 20) then {
        [{_this call ACME_fnc_lineWarmerAck;}, [_patient, _medic, _id, _accepted, _receipt, _message, _attempt + 1], 0.1] call CBA_fnc_waitAndExecute;
    };
    false
};
if (_receipt isNotEqualTo []) then {
    // The original reservation may have been made on the previous provider
    // owner. Adopt only this exact public, unsettled, owner-decided receipt.
    private _supplies = missionNamespace getVariable ["ACME_supplyReceipts", createHashMap];
    private _receiptId = _receipt select 3;
    private _localReceipt = _supplies getOrDefault [_receiptId, []];
    if (_localReceipt isNotEqualTo [] && {!(_localReceipt isEqualTo _receipt)}) exitWith {_accepted = objNull;};
    if (_localReceipt isEqualTo []) then {
        _supplies set [_receiptId, +_receipt];
        missionNamespace setVariable ["ACME_supplyReceipts", _supplies];
    };
};
if !(_accepted isEqualType true) exitWith {false};
_escrows set [_id, [_request, true]];
_medic setVariable ["ACME_lineWarmerEscrow", _escrows, true];
if (_receipt isNotEqualTo []) then {[_receipt, !_accepted] call ACME_fnc_treatmentSupplyRefund;};
uiNamespace setVariable ["ACME_lineWarmerSupplyCache", []];
if (hasInterface && {!isNull findDisplay 86000}
    && {(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull]) isEqualTo _patient}
    && {(missionNamespace getVariable ["ACE_player", objNull]) isEqualTo _medic}) then {
    if (_message != "" && {!_accepted}) then {[_medic, _message] call ACME_fnc_clinicalNotice;};
    call ACME_fnc_updateTransfusionControls;
};
true
