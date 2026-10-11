/* UI contract: [show, installed, available count, last personal spare, confirming].
 * Confirmations describe one patient/epoch/access/physical bag, never an index. */
params ["_patient", "_part", "_iv", "_site", "_uid", ["_medic", objNull, [objNull]], ["_refresh", false, [false]]];
private _epoch = if (isNull _patient) then {-1} else {[_patient] call ACME_fnc_clinicalEpoch};
private _context = [_patient, _medic, _epoch, toLowerANSI _part, _iv, _site, _uid];
private _confirm = uiNamespace getVariable ["ACME_lineWarmerConfirm", []];
if (_confirm isNotEqualTo [] && {!(_confirm isEqualTo _context)}) then {
    uiNamespace setVariable ["ACME_lineWarmerConfirm", []];
    _confirm = [];
};
if (isNull _patient || {isNull _medic} || {_uid == ""}
    || {!([_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid)}) exitWith {[false, false, 0, false, false]};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
private _index = _bags findIf {
    (_x param [8, ""]) == _uid && {(_x param [3, -1]) == _site} && {(_x param [4, true]) isEqualTo _iv}
};
if (_index < 0) exitWith {[false, false, 0, false, false]};
private _bag = _bags select _index;
private _fitted = [_patient, _part, _iv, _site] call ACME_fnc_lineWarmer;
private _eligible = (_bag param [0, ""]) in ["Blood", "FreshBlood", "Saline", "ACME_SalineY", "Plasma"] && {(_bag param [1, 0]) > 0.01};
private _available = 0;
if (_eligible && {!_fitted}) then {
    private _cache = uiNamespace getVariable ["ACME_lineWarmerSupplyCache", []];
    if (!_refresh && {count _cache == 3} && {(_cache select 0) isEqualTo _context} && {diag_tickTime - (_cache select 1) < 0.5}) then {
        _available = _cache select 2;
    } else {
        // Fitting uses treatmentSupplyTake's personal-only physical reservation;
        // availability and the last-spare warning must describe that same stock.
        _available = [_medic, "ACME_BloodWarmer"] call ace_common_fnc_getCountOfItem;
        uiNamespace setVariable ["ACME_lineWarmerSupplyCache", [_context, diag_tickTime, _available]];
    };
};
[_fitted || {_eligible}, _fitted, _available, _available == 1, _confirm isEqualTo _context]
