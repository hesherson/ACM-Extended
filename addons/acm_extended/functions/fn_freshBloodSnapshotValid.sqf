/* Whole-registry startup checkpoint. Native fresh-blood class IDs stay fixed. */
params ["_snapshot"];
if (isNil "_snapshot" || {!(_snapshot isEqualType [])} || {count _snapshot != 2}) exitWith {false};
if (isNil {_snapshot select 0} || {isNil {_snapshot select 1}}
    || {(_snapshot select 0) isNotEqualTo 1} || {!((_snapshot select 1) isEqualType [])}
    || {count (_snapshot select 1) > 513}) exitWith {false};
private _seen = [];
private _ok = true;
{
    if !(_x isEqualType [] && {count _x == 6}) exitWith {_ok = false;};
    private _row = _x;
    if ([0,1,2,3,4,5] findIf {isNil {_row select _x}} >= 0) exitWith {_ok = false;};
    _x params ["_id","_donor","_volume","_type","_alive","_age"];
    if !(_id isEqualType 0 && {finite _id} && {_id >= 0} && {_id <= 512}
        && {_id == floor _id} && {!(_id in _seen)}
        && {_donor isEqualType []} && {count _donor in [2,4]}
        && {(_donor select 0) isEqualTo "O"}
        && {[_donor] call ACME_fnc_clinicalEncodedValid}
        && {_volume isEqualType 0} && {finite _volume} && {_volume >= 0} && {_volume <= 10000}
        && {_type isEqualType 0} && {finite _type} && {_type >= 0} && {_type <= 7} && {_type == floor _type}
        && {_alive isEqualType true}
        && {_age isEqualType 0} && {finite _age} && {_age >= 0} && {_age <= 1e9}) exitWith {_ok = false;};
    _seen pushBack _id;
} forEach (_snapshot select 1);
_ok
