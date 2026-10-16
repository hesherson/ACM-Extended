/* Exact physical line relation. Replicated state is only usable while both UID endpoints remain at this access. */
params ["_patient", "_part", "_iv", "_site"];
if (isNull _patient) exitWith {[]};
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
private _line = (_patient getVariable ["ACME_PiggybackLines", createHashMap]) getOrDefault [_key, []];
if (!(_line isEqualType []) || {count _line != 3} || {!((_line select 0) isEqualType "")} || {!((_line select 1) isEqualType "")} || {(_line select 0) == ""} || {(_line select 1) == ""} || {(_line select 0) == (_line select 1)} || {(_line select 2) != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {[]};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI _part, []];
private _found = _bags select {(_x param [3, -1]) == _site && {(_x param [4, true]) == _iv} && {(_x param [8, ""]) in (_line select [0,2])}};
if (count _found != 2 || {count (_found select {(_x param [8,""]) == (_line select 0)}) != 1} || {count (_found select {(_x param [8,""]) == (_line select 1)}) != 1}) exitWith {[]};
+_line
