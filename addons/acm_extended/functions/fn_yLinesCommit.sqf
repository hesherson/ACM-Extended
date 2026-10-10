/* Authoritative mutation gate for Y-line membership topology. */
params [["_patient",objNull,[objNull]],["_lines",[],[[]]],["_public",true,[true]]];
if (isNull _patient || {!local _patient}) exitWith {false};
private _old = (_patient getVariable ["ACME_YLines", []]) apply {toLowerANSI _x};
private _new = _lines apply {toLowerANSI _x};
if (local _patient) then {
    private _prime = _patient getVariable ["ACME_YLinePrimed", createHashMap];
    {if !(_x in _old) then {_prime set [_x, false];};} forEach _new;
    {if !(_x in _new) then {_prime deleteAt _x;};} forEach _old;
    [_patient, "ACME_YLinePrimed", _prime] call ACME_fnc_setVarNet;
    private _jobs = _patient getVariable ["ACME_yFlushJobs", createHashMap];
    {if !(_x in _new) then {_jobs deleteAt _x;};} forEach keys _jobs;
    [_patient, "ACME_yFlushJobs", _jobs] call ACME_fnc_setVarNet;
    private _warmers = _patient getVariable ["ACME_lineWarmers", createHashMap];
    private _removed = _old - _new;
    if (_removed isNotEqualTo [] || {(_new - _old) isNotEqualTo []}) then {
        {_warmers deleteAt _x;} forEach _removed;
        [_patient, "ACME_lineWarmers", _warmers] call ACME_fnc_setVarNet;
    };
};
_patient setVariable ["ACME_YLines", _lines, _public];
true
