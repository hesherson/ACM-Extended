/* Immutable bag metadata wins over the session registry. A nonempty invalid
 * marker deliberately fences an old save; it must never fall back to a reused ID. */
params [["_id",-1,[0]],["_inline",[],[[]]],["_bloodType",-1,[0]]];
private _entry = [];
if (_inline isNotEqualTo []) then {
    if (count _inline == 4 && {(_inline select 0) isEqualTo "freshV1"}
        && {(_inline select 1) isEqualType true}
        && {(_inline select 2) isEqualType 0} && {finite (_inline select 2)}
        && {(_inline select 3) isEqualType 0} && {finite (_inline select 3)}) then {
        _entry = [objNull,0,_inline select 3,_inline select 1,_inline select 2];
    };
} else {
    if (finite _id && {_id >= 0} && {_id == floor _id}) then {
        _entry = [_id] call ACM_circulation_fnc_getFreshBloodEntry;
    };
};
if !(_entry isEqualType [] && {count _entry >= 5}
    && {(_entry select 2) isEqualType 0} && {finite (_entry select 2)}
    && {(_entry select 2) >= 0} && {(_entry select 2) <= 7} && {(_entry select 2) == floor (_entry select 2)}
    && {(_entry select 3) isEqualType true}
    && {(_entry select 4) isEqualType 0} && {finite (_entry select 4)}
    && {_bloodType < 0 || {(_entry select 2) isEqualTo _bloodType}}) exitWith {[]};
+_entry
