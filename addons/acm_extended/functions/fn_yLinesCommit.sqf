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
    private _removed = _old - _new;
    {
        private _pieces = _x splitString "#";
        if (count _pieces == 3) then {
            private _part = _pieces select 0;
            private _iv = (_pieces select 1) == "true";
            private _site = parseNumber (_pieces select 2);
            private _bags = (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
            // Changing/removing one branch does not remove downstream equipment.
            // Move transfers custody first; complete disconnection returns it once.
            if ((_bags findIf {(_x param [3,-1]) == _site && {(_x param [4,true]) isEqualTo _iv}}) < 0) then {
                [_patient,_part,_iv,_site] call ACME_fnc_lineWarmerDetach;
            };
        };
    } forEach _removed;
};
_patient setVariable ["ACME_YLines", _lines, _public];
true
