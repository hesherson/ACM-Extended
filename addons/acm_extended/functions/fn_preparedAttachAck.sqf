params ["_id", "_ok", "_doseId", ["_reason", "", [""]]];
private _pending = missionNamespace getVariable ["ACME_preparedPending", createHashMap];
private _p = _pending getOrDefault [_id, []];
if (_p isEqualTo [] || {_p select 2}) exitWith {};
_p set [2, true];
private _args = _p select 0;
_args params ["_medic", "_patient", "_target", "_item", "_action", "_vehicle", "_part", "_iv", "_site", "_volume", "_prepared", "_index", "_label", ["_staged", []]];
if (!_ok) exitWith {
    if (!(_staged isEqualTo []) || {(_prepared param [15, ""]) != ""}) exitWith {
        private _message = [_reason] call ACME_fnc_preparedAttachMessage;
        [_medic, _message] call ACME_fnc_clinicalNotice;
        [[_medic, _patient, _part, _iv, _site]] call ACME_fnc_reopenTransfusion;
    };
    private _mode = _prepared param [11, 0];
    if (_mode == 2 && {!isNull _vehicle}) then {_vehicle addItemCargoGlobal [_item, 1];} else {[if (isNull _target) then {_medic} else {_target}, _item] call ace_common_fnc_addToInventory;};
    [_medic, [_reason] call ACME_fnc_preparedAttachMessage] call ACME_fnc_clinicalNotice;
    [[_medic, _patient, _part, _iv, _site]] call ACME_fnc_reopenTransfusion;
};
private _uid = _prepared select 0;
{
    private _list = _medic getVariable [_x, []];
    _list = _list select {(_x param [0, ""]) != _uid};
    _medic setVariable [_x, _list, true];
} forEach ["ACME_infusion_PreparedBags", "ACME_preparedIVSets"];
[_patient, format ["Infusion connected: %1", _label]] call ace_medical_treatment_fnc_addToTriageCard;
[_patient, "activity", "%1 connected %2", [[_medic, false, true] call ace_common_fnc_getName, _label]] call ace_medical_treatment_fnc_addToLog;
[_patient, _doseId, _medic, _part, _id] call ACME_fnc_queueInfusionClamp;
