/* Resolve exactly one current original list row; stale/filtered/duplicate cards cannot select a neighbour. */
params ["_list","_identity"];
if (isNull _list || {_identity isEqualTo []}) exitWith {-1};
private _matches = [];
for "_row" from 0 to ((lbSize _list) - 1) do {
    if (([_list,_row] call ACME_fnc_transfusionCardIdentity) isEqualTo _identity) then {_matches pushBack _row;};
};
if (count _matches == 1) then {_matches select 0} else {-1}
