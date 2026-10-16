/* Provider-local reserve/intent. Last-spare confirmation does not consume an
 * item; the exact receipt settles only on an owner ACK, even after dialog close. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_lineWarmerRequest;};};
params [["_operation", "add", [""]], ["_uid", "", [""]]];
if (_operation == "no") exitWith {uiNamespace setVariable ["ACME_lineWarmerConfirm", []]; true};
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _medic = missionNamespace getVariable ["ACE_player", objNull];
private _part = toLowerANSI (missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""]);
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
if (isNull _patient || {isNull _medic} || {!local _medic} || {!alive _medic}
    || {!([_medic] call ace_common_fnc_isAwake)} || {isNull findDisplay 86000} || {_uid == ""}) exitWith {false};
private _state = [_patient, _part, _iv, _site, _uid, _medic, true] call ACME_fnc_lineWarmerActionState;
private _context = [_patient, _medic, [_patient] call ACME_fnc_clinicalEpoch, _part, _iv, _site, _uid];
if (_operation == "yes") then {
    if !(_state select 4) exitWith {_operation = "invalid";};
    _operation = "add";
} else {
    if (_operation == "add" && {_state select 3} && {!(_state select 1)} && {(_state select 2) > 0}) exitWith {
        uiNamespace setVariable ["ACME_lineWarmerConfirm", _context];
        _operation = "confirm";
    };
};
if (_operation == "confirm") exitWith {true};
if !(_operation in ["add", "remove"]) exitWith {false};
if (!(_state select 0) || {_operation == "add" && {(_state select 1) || {(_state select 2) <= 0}}}
    || {_operation == "remove" && {!(_state select 1)}}) exitWith {false};
private _pending = _medic getVariable ["ACME_lineWarmerEscrow", createHashMap];
if ((values _pending findIf {
    private _request = _x select 0;
    !(_x select 1) && {(_request select 0) isEqualTo _patient} && {(_request select 3) == _part}
        && {(_request select 4) isEqualTo _iv} && {(_request select 5) == _site}
}) >= 0) exitWith {false};
private _receipt = [];
if (_operation == "add") then {_receipt = [_medic, _patient, ["ACME_BloodWarmer"], true] call ACME_fnc_treatmentSupplyTake;};
if (_operation == "add" && {_receipt isEqualTo []}) exitWith {false};
uiNamespace setVariable ["ACME_lineWarmerConfirm", []];
uiNamespace setVariable ["ACME_lineWarmerSupplyCache", []];
private _serial = (missionNamespace getVariable ["ACME_lineWarmerSerial", 0]) + 1;
missionNamespace setVariable ["ACME_lineWarmerSerial", _serial];
private _id = format ["warmer:%1:%2:%3", clientOwner, _serial, floor (diag_tickTime * 1000)];
private _request = [_patient, _medic, _operation, _part, _iv, _site, _uid, _context select 2, _id, _receipt, serverTime, 1];
_pending set [_id, [_request, false]];
_medic setVariable ["ACME_lineWarmerEscrow", _pending, true];
[_medic] call ACME_fnc_lineWarmerRecover;
true
