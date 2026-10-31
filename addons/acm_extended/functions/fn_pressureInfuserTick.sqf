/* NA5 cuff decay. Flow reads the selected bag's cuff in fn_getIVFlowRate.sqf.
   Drop absent and empty bags without rewriting unchanged maps each tick.
   A deflated cuff remains fitted and can be pumped without spending another item. */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};
[_patient] call ACME_fnc_lineWarmerReturnsTick;
private _warmers = _patient getVariable ["ACME_lineWarmers", createHashMap];
private _removedWarmers = [];
{
    private _site = _x splitString "#";
    if (count _site != 3 || {!([_patient, _site select 0, (_site select 1) == "true", parseNumber (_site select 2)] call ACME_fnc_transfusionAccessValid)}) then {_removedWarmers pushBack _x;};
} forEach keys _warmers;
if (_removedWarmers isNotEqualTo []) then {
    {
        private _parts = _x splitString "#";
        if (count _parts == 3) then {
            [_patient,_parts select 0,(_parts select 1) == "true",parseNumber (_parts select 2)] call ACME_fnc_lineWarmerDetach;
        };
    } forEach _removedWarmers;
};
private _cuffs = _patient getVariable ["ACME_piCuffs", createHashMap];
if (count _cuffs == 0) exitWith {};
private _live = [];
{
    {_x params ["_type", "_remaining"]; if (_remaining > 0.5) then {_live pushBack (_x param [8, ""]);};} forEach _y;
} forEach (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);
private _drop = [];
{
    if (!(_x in _live)) then {_drop pushBack _x;};
} forEach _cuffs;
if !(_drop isEqualTo []) then {
    {_cuffs deleteAt _x;} forEach _drop;
    [_patient, "cuffs", _cuffs] call ACME_fnc_pressureInfuserStateCommit;
};
