/* Protocol 1 patient-owner transaction for one downstream IV/IO warmer.
 * The provider holds the exact physical supply receipt in replicated escrow;
 * terminal decisions follow patient locality and survive clinical resets. */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_lineWarmerCommit;};
    _result
};
params [
    ["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]], ["_operation", "", [""]],
    ["_part", "", [""]], ["_iv", true, [true]], ["_site", -1, [0]], ["_uid", "", [""]],
    ["_epoch", -1, [0]], ["_id", "", [""]], ["_receipt", [], [[]]], ["_issued", -1, [0]], ["_protocol", 1, [0]]
];
if (isNull _patient || {!local _patient} || {isNull _medic}) exitWith {false};
if (_protocol != 1 || {_id == ""} || {count _id > 128} || {_uid == ""} || {count _uid > 128}
    || {!(_operation in ["add", "remove"])} || {!finite _epoch} || {!finite _issued} || {_issued < 0}) exitWith {false};
_part = toLowerANSI _part;
private _request = [_patient, _medic, _operation, _part, _iv, _site, _uid, _epoch, _id, _receipt, _issued, _protocol];
private _results = _patient getVariable ["ACME_lineWarmerResults", createHashMap];
private _old = _results getOrDefault [_id, []];
if (_old isNotEqualTo []) exitWith {
    if ((_old select 0) isEqualTo _request) then {
        ["ACME_lineWarmerAck", [_patient, _medic, _id, _old select 1, _receipt, _old select 2], _medic] call CBA_fnc_targetEvent;
    };
    _old param [1, false]
};
private _escrow = (_medic getVariable ["ACME_lineWarmerEscrow", createHashMap]) getOrDefault [_id, []];
// Missing replicas are not rejections. Provider recovery repeats this intention
// after the escrow/certificate arrives on the current patient owner.
if (count _escrow != 2 || {_escrow select 1} || {!((_escrow select 0) isEqualTo _request)}) exitWith {false};
{
    private _result = _results get _x;
    private _priorRequest = _result select 0;
    private _provider = _priorRequest select 1;
    private _entry = if (isNull _provider) then {[]} else {(_provider getVariable ["ACME_lineWarmerEscrow", createHashMap]) getOrDefault [_x, []]};
    if (serverTime - (_result select 3) > 180 && {_entry isEqualTo [] || {_entry param [1, false]}}) then {_results deleteAt _x;};
} forEach keys _results;
private _finish = {
    params ["_accepted", "_message"];
    _results set [_id, [_request, _accepted, _message, serverTime]];
    [_patient, "ACME_lineWarmerResults", _results] call ACME_fnc_setVarNet;
    ["ACME_lineWarmerAck", [_patient, _medic, _id, _accepted, _receipt, _message], _medic] call CBA_fnc_targetEvent;
    _accepted
};
// An unknown old escrow can now be rejected definitively: pending decisions
// are retained, so an accepted request is always answered by the replay above.
if (serverTime - _issued > 10 || {_issued > serverTime + 2}) exitWith {[false, "Fluid warmer request expired. Select the bag again."] call _finish};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {[false, "Patient state changed. Select the bag again."] call _finish};
if (!alive _medic || {!([_medic] call ace_common_fnc_isAwake)}
    || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > 5}) exitWith {[false, "Provider can no longer service this line."] call _finish};
if !([_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid) exitWith {[false, "That access is no longer available."] call _finish};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
private _index = _bags findIf {
    (_x param [8, ""]) == _uid && {(_x param [3, -1]) == _site} && {(_x param [4, true]) isEqualTo _iv}
};
if (_index < 0) exitWith {[false, "That bag changed or was moved. Select it again."] call _finish};
private _fitted = [_patient, _part, _iv, _site] call ACME_fnc_lineWarmer;
if (_operation == "remove") exitWith {
    if (!_fitted) exitWith {[false, "This line no longer has a fluid warmer."] call _finish};
    [_patient, _part, _iv, _site, _medic] call ACME_fnc_lineWarmerDetach;
    [true, "Fluid warmer removed."] call _finish
};
if (!alive _patient) exitWith {[false, "A fluid warmer cannot be fitted to a dead patient."] call _finish};
if (_fitted) exitWith {[false, "A fluid warmer is already fitted downstream on this line."] call _finish};
if (count _receipt != 4 || {isNull (_receipt param [0, objNull])}
    || {(_receipt param [1, ""]) != "ACME_BloodWarmer"} || {(_receipt param [3, ""]) == ""}) exitWith {[false, "No reserved fluid warmer is available."] call _finish};
private _bag = _bags select _index;
if (!((_bag param [0, ""]) in ["Blood", "FreshBlood", "Saline", "ACME_SalineY", "Plasma"])
    || {(_bag param [1, 0]) <= 0.01}) exitWith {[false, "Select a blood, saline or plasma bag with fluid remaining."] call _finish};
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
private _lines = _patient getVariable ["ACME_lineWarmers", createHashMap];
private _custody = _patient getVariable ["ACME_lineWarmerCustody", createHashMap];
_custody set [_key, [_id, _medic, _epoch]];
_lines set [_key, true];
[_patient, "ACME_lineWarmerCustody", _custody] call ACME_fnc_setVarNet;
[_patient, "ACME_lineWarmers", _lines] call ACME_fnc_setVarNet;
[true, "Fluid warmer fitted downstream."] call _finish
