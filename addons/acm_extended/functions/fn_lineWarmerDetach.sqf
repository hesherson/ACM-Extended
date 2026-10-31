/* Patient-owner lifecycle hook. Call only when the whole downstream assembly is
 * removed (or for explicit Remove Fluid Warmer); pulling one branch keeps it.
 * Removal deletes custody before replying, so a duplicate cannot return it twice. */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_lineWarmerDetach;};
    _result
};
params ["_patient", "_part", "_iv", "_site", ["_recipient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {false};
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
private _lines = _patient getVariable ["ACME_lineWarmers", createHashMap];
if !(_lines getOrDefault [_key, false]) exitWith {false};
private _custody = _patient getVariable ["ACME_lineWarmerCustody", createHashMap];
private _record = _custody getOrDefault [_key, []];
if (isNull _recipient) then {_recipient = _record param [1, objNull, [objNull]];};
private _id = _record param [0, "", [""]];
private _restorePlan = _patient getVariable ["ACME_lineWarmerRestorePlan", []];
private _restoreCustody = if (count _restorePlan == 2) then {_restorePlan select 1} else {createHashMap};
if (_id != "" && {_patient getVariable ["ACME_clinicalRestoring", false]}
    && {count _restorePlan == 2}
    && {((keys _restoreCustody) findIf {((_restoreCustody get _x) param [0, ""]) == _id}) >= 0}) exitWith {
    // Native reset/topology hooks may detach the old site during deserialize.
    // The preflight plan already reserved this same physical device for restore.
    false
};
_lines deleteAt _key;
_custody deleteAt _key;
[_patient, "ACME_lineWarmerCustody", _custody] call ACME_fnc_setVarNet;
[_patient, "ACME_lineWarmers", _lines] call ACME_fnc_setVarNet;
if (_id != "") then {
    private _retired = _patient getVariable ["ACME_lineWarmerRetired", createHashMap];
    _retired set [_id, true];
    [_patient, "ACME_lineWarmerRetired", _retired] call ACME_fnc_setVarNet;
};
// Before B275 possession created a free boolean without consuming an item.
// Clearing such a legacy flag cannot manufacture a replacement warmer.
if (!isNull _recipient && {_id != ""}) then {
    private _returned = _patient getVariable ["ACME_lineWarmerReturns", createHashMap];
    _returned set [_id, [_recipient, serverTime]];
    [_patient, "ACME_lineWarmerReturns", _returned] call ACME_fnc_setVarNet;
    private _patients = missionNamespace getVariable ["ACME_lineWarmerReturnPatients", []];
    _patients pushBackUnique _patient;
    missionNamespace setVariable ["ACME_lineWarmerReturnPatients", _patients];
    ["ACME_lineWarmerReturn", [_patient, _recipient, _id, serverTime], _recipient] call CBA_fnc_targetEvent;
};
true
