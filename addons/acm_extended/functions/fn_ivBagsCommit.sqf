/*
 * Authoritative ACM Extended mutation gate for ACM's IV-bag map.
 *
 * This deliberately preserves the existing setVariable semantics.  The first fork step is to make every
 * Extended-owned mutation cross one endpoint; owner/epoch validation can then be tightened here without
 * hunting independent writers across infusion, Y-line and transfusion UI code.
 */
params [
    ["_patient", objNull, [objNull]],
    "_bags",
    ["_public", true, [true]]
];

if (isNull _patient) exitWith {false};
private _ok = [_patient, _bags, _public] call ACM_circulation_fnc_setIVBagsState;
// Connected topology is keyed by physical endpoints. Removing either bag retires
// its PiB relation; a later replacement cannot inherit an orphaned relation.
if (local _patient) then {
    private _lines = _patient getVariable ["ACME_PiggybackLines",createHashMap];
    private _changed = false;
    {
        private _key = _x;
        private _line = _y;
        private _parts = _key splitString "#";
        private _arr = _bags getOrDefault [_parts param [0,""],[]];
        private _endpoints = _arr select {(_x param [8,""]) in (_line select [0,2])
            && {toLowerANSI format["%1#%2#%3",_parts param[0,""],_x param[4,true],_x param[3,-1]] == _key}};
        if (count _endpoints != 2 || {count (_endpoints select {(_x param[8,""]) == (_line param[0,""])}) != 1} || {count (_endpoints select {(_x param[8,""]) == (_line param[1,""])}) != 1}) then {_lines deleteAt _key; _changed = true;};
    } forEach _lines;
    if (_changed) then {[_patient,_lines,_public] call ACME_fnc_piggybackLinesCommit;};
    // The device belongs to the exact downstream access assembly. Returning one
    // branch retains it; removing the final branch returns exactly one device.
    private _warmers = _patient getVariable ["ACME_lineWarmers",createHashMap];
    {
        private _pieces = _x splitString "#";
        if (count _pieces != 3) then {continue;};
        private _part = _pieces select 0;
        private _iv = (_pieces select 1) == "true";
        private _site = parseNumber (_pieces select 2);
        private _remaining = (_bags getOrDefault [_part,[]]) findIf {(_x param[3,-1]) == _site && {(_x param[4,true]) == _iv}};
        if (_remaining < 0 && {!([_patient,_part,_iv,_site] call ACME_fnc_isYLineAccess)}) then {
            [_patient,_part,_iv,_site] call ACME_fnc_lineWarmerDetach;
        };
    } forEach (keys _warmers);
};
_ok
