/* A presentation slot belongs to an installed administration line, never to a
 * zero-volume native fluid bag. Repeat this read-only check on the owner. */
params ["_patient", "_part", "_iv", "_site", ["_expectedUID", ""]];
if (isNull _patient || {!_iv} || {_site < 0}
    || {!([_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid)}
    || {[_patient, _part, _iv, _site] call ACME_fnc_isYLineAccess}) exitWith {[]};
_part = toLowerANSI _part;
private _marks = (_patient getVariable ["ACME_IV_Marks", []]) select {
    toLowerANSI (_x param [0, ""]) == _part && {(_x param [4, ""]) == "hub"}
        && {([_x param [10, ""]] call ACME_fnc_ivSiteIndex) == _site}
};
if (count _marks != 1) exitWith {[]};
private _row = _marks select 0;
private _hubUID = _row param [14, ""];
private _uid = _row param [17, ""];
if !(_uid isEqualType "") exitWith {[]};
if (_uid == "") then {_uid = _hubUID;}; // Existing assemblies acquire an installation stamp when replaced.
if (_hubUID == "" || {_expectedUID != "" && {_uid != _expectedUID}}
    || {!((_row param [15, []]) param [3, false])}) exitWith {[]};
private _detached = (_patient getVariable ["ACME_detachedBags", []])
    + (_patient getVariable ["ACME_IV_DisconnectedBagUIDs", []]);
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
if ((_bags findIf {
    (_x param [3, -1]) == _site && {(_x param [4, false]) isEqualTo _iv}
        && {!((_x param [8, ""]) in _detached)}
}) >= 0) exitWith {[]};
private _pi = ACME_infusion_bodyParts find _part;
private _access = if (_pi >= 0) then {[_patient, _iv, _pi, _site] call ACM_circulation_fnc_getAccessType} else {0};
if (_access <= 0) exitWith {[]};
[_uid, _access]
