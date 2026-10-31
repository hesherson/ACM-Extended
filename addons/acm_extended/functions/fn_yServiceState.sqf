/* Read-only snapshot for this exact IV/IO. Does not alter volume, prime state or queues. */
params ["_p", "_part", "_iv", "_site"];
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
private _bags = (_p getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
private _reserve = 0; private _blood = false; private _id = "";
{
    if ((_x param [3,-1]) == _site && {(_x param [4,true]) isEqualTo _iv}) then {
        if ((_x param [0, ""]) in ["Saline", "ACME_SalineY"]) then {_reserve = _x param [1,0]; _id = _x param [8, ""];};
        if ((_x param [0, ""]) in ["Blood", "FreshBlood"] && {(_x param [1,0]) > 0.01}) then {_blood = true;};
    };
} forEach _bags;
private _job = (_p getVariable ["ACME_yFlushJobs", createHashMap]) getOrDefault [_key, []];
private _reserved = _job param [4, 0];
{_reserved = _reserved + _x;} forEach (_job param [9, []]);
private _dirty = (_p getVariable ["ACME_YLineDirty", createHashMap]) getOrDefault [_key, false];
// A pre-B227 existing line is grandfathered, not retroactively drained/blocked on load.
private _primed = (_p getVariable ["ACME_YLinePrimed", createHashMap]) getOrDefault [_key, true];
private _kind = if (_job isEqualTo []) then {""} else {_job param [10, "flush"]};
[_reserve, _reserved, _blood, _dirty, _primed, _kind, _id, _job]
