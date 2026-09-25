params ["_patient", "_id", "_ok", "_message", "_snapshot"];
if (!hasInterface) exitWith {};
["ACME_CS_ackSeen", [_id, clientOwner]] call CBA_fnc_serverEvent;
private _pending = ACME_CS_pending getOrDefault [_id, []];
if (count _pending == 0) exitWith {};
ACME_CS_pending deleteAt _id; // refund/log/feedback at most once, even after dialog close
_pending params ["_request", "_receipt"];
// A rejected intention returns the exact patient's/provider's item or original vehicle cargo.
// Successful/wasted placements commit once. Missing ACK never authorizes a refund.
if !(_receipt isEqualTo []) then {[_receipt, !_ok] call ACME_fnc_treatmentSupplyRefund;};
if (_message != "") then { [_message, 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured; };
[_patient, _snapshot, true] call ACME_fnc_chestSealSyncUI;
if ((uiNamespace getVariable ["ACME_CS_Patient", objNull]) == _patient && {!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}) then {
    private _currentMedic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
    uiNamespace setVariable ["ACME_CS_SealsLeft", if (isNull _currentMedic) then {0} else {[_currentMedic, uiNamespace getVariable ["ACME_CS_Patient", objNull], "ACM_ChestSeal"] call ACME_fnc_treatmentSupplyCount}];
    uiNamespace setVariable ["ACME_CS_SpearsLeft", if (isNull _currentMedic) then {0} else {[_currentMedic, uiNamespace getVariable ["ACME_CS_Patient", objNull], "ACME_NARSPEAR"] call ACME_fnc_treatmentSupplyCount}];
    [] call ACME_fnc_chestSealRefreshSlot;
    [] call ACME_fnc_chestSealRefreshSpearSlot;
};
