params ["_patient", "_id", "_ok", "_message", "_snapshot"];
if (!hasInterface) exitWith {};
["ACME_CS_ackSeen", [_id, clientOwner]] call CBA_fnc_serverEvent;
private _pending = ACME_CS_pending getOrDefault [_id, []];
if (count _pending == 0) exitWith {};
ACME_CS_pending deleteAt _id; // refund/log/feedback at most once, even after dialog close
_pending params ["_request", "_item"];
private _medic = _request select 1;
if (!_ok && {_item != ""}) then {
    // Respawn may have replaced the original medic while the request was in flight.
    private _recipient = if (!isNull _medic && {local _medic} && {alive _medic}) then {_medic} else {player};
    if (!isNull _recipient) then { [_recipient, _item] call ace_common_fnc_addToInventory; };
};
if (_message != "") then { [_message, 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured; };
[_patient, _snapshot, true] call ACME_fnc_chestSealSyncUI;
if ((uiNamespace getVariable ["ACME_CS_Patient", objNull]) == _patient && {!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}) then {
    private _currentMedic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
    uiNamespace setVariable ["ACME_CS_SealsLeft", if (isNull _currentMedic) then {0} else {[_currentMedic, "ACM_ChestSeal"] call ACME_fnc_itemCount}];
    uiNamespace setVariable ["ACME_CS_SpearsLeft", if (isNull _currentMedic) then {0} else {[_currentMedic, "ACME_NARSPEAR"] call ACME_fnc_itemCount}];
    [] call ACME_fnc_chestSealRefreshSlot;
    [] call ACME_fnc_chestSealRefreshSpearSlot;
};
