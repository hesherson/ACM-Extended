/* Local item reservation plus an idempotent, field-level intention. Pending requests
   survive dialog close. Only a definitive rejection refunds the reserved item. */
params ["_operation", ["_payload", []], ["_item", ""]];
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
private _viewer = uiNamespace getVariable ["ACME_CS_presenceViewer", player];
if (isNull _patient || {isNull _medic} || {isNull _viewer} || {!local _medic}) exitWith {false};
if (_operation in ["ncd", "miss"] && {!([_medic, "ncd"] call ACME_fnc_procedureAllowed)}) exitWith {false};
private _snapshot = uiNamespace getVariable ["ACME_CS_netSnapshot", []];
if (count _snapshot < 5) exitWith {
    ["Synchronizing this patient's chest state.", 2, _medic] call ace_common_fnc_displayTextStructured;
    ["ACME_CS_session", [_patient, _viewer, "sync", uiNamespace getVariable ["ACME_CS_SessionToken", ""]]] call CBA_fnc_serverEvent;
    false
};
private _duplicate = false;
{
    private _req = (ACME_CS_pending get _x) select 0;
    if ((_req select 0) == _patient && {(_req select 4) == (_snapshot select 0)} && {(_req select 6) == _operation} && {(_req select 7) isEqualTo _payload}) exitWith { _duplicate = true; };
} forEach (keys ACME_CS_pending);
if (_duplicate) exitWith {false};
if (_item != "" && {([_medic, _item] call ace_common_fnc_getCountOfItem) <= 0}) exitWith {false};
if (_item != "") then {
    private _before = [_medic, _item] call ace_common_fnc_getCountOfItem;
    _medic removeItem _item;
    if (([_medic, _item] call ace_common_fnc_getCountOfItem) >= _before) then { _item = "__RESERVATION_FAILED__"; };
};
if (_item == "__RESERVATION_FAILED__") exitWith {false};
ACME_CS_requestSequence = (missionNamespace getVariable ["ACME_CS_requestSequence", 0]) + 1;
private _id = format ["%1:%2:%3", clientOwner, diag_tickTime, ACME_CS_requestSequence];
private _request = [_patient, _medic, _viewer, _id, _snapshot select 0, _snapshot select 1, _operation, _payload, CBA_missionTime, clientOwner];
ACME_CS_pending set [_id, [_request, _item, diag_tickTime]];
// On a listen server CBA can deliver inline. Let the caller finish local prediction
// before an immediate rejection/ack refreshes it; this does not throttle the live stream.
[{ ["ACME_CS_edit", _this] call CBA_fnc_serverEvent; }, _request] call CBA_fnc_execNextFrame;
true
