params ["_snapshot"];
if (isNil "_snapshot" || {!(_snapshot isEqualType [])} || {count _snapshot != 2}) exitWith {false};
if (isNil {_snapshot select 0} || {isNil {_snapshot select 1}} || {(_snapshot select 0) isNotEqualTo 1}) exitWith {false};
private _rows = _snapshot select 1;
if !(_rows isEqualType [] && {count _rows <= 1024}) exitWith {false};
private _ok = true;
{
    if (isNil "_x" || {!(_x isEqualType [])} || {count _x != 2}) exitWith {_ok = false;};
    if (isNil {_x select 0} || {isNil {_x select 1}}) exitWith {_ok = false;};
    _x params ["_class","_warm"];
    if !(_class isEqualType "" && {count _class <= 128} && {([_class] call ACME_fnc_coolerBagVolume) > 0}
        && {_warm isEqualType 0} && {finite _warm} && {_warm >= 0} && {_warm <= 1e9}) exitWith {_ok = false;};
} forEach _rows;
_ok
