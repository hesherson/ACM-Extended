/* [1,current stock,default stock,restock enabled,configured interval,remaining game minutes]. */
params ["_snapshot"];
if (isNil "_snapshot" || {!(_snapshot isEqualType [])} || {count _snapshot != 6}) exitWith {false};
if (([0,1,2,3,4,5] findIf {isNil {_snapshot select _x}}) >= 0) exitWith {false};
_snapshot params ["_version","_stock","_defaults","_restock","_interval","_remaining"];
if (_version isNotEqualTo 1 || {!(_restock isEqualType true)}) exitWith {false};
if !(_interval isEqualType 0 && {finite _interval} && {_interval >= -1} && {_interval <= 1e9}
    && {_remaining isEqualType 0} && {finite _remaining} && {_remaining >= 0} && {_remaining <= 1e9}) exitWith {false};
private _validStock = {
    params ["_rows"];
    if !(_rows isEqualType [] && {count _rows <= 128}) exitWith {false};
    private _seen = createHashMap;
    private _ok = true;
    {
        if (isNil "_x" || {!(_x isEqualType [])} || {count _x != 2}) exitWith {_ok = false;};
        if (isNil {_x select 0} || {isNil {_x select 1}}) exitWith {_ok = false;};
        _x params ["_class","_count"];
        if !(_class isEqualType "" && {count _class <= 128} && {!(_class in _seen)}
            && {_count isEqualType 0} && {finite _count} && {_count >= 0} && {_count == floor _count} && {_count <= 1e6}) exitWith {_ok = false;};
        if !((_class find "ACM_BloodBag_") == 0 || {(_class find "ACM_FreshBloodBag_") == 0}) exitWith {_ok = false;};
        if !(isClass (configFile >> "CfgWeapons" >> _class)) exitWith {_ok = false;};
        _seen set [_class,true];
    } forEach _rows;
    _ok
};
[_stock] call _validStock && {[_defaults] call _validStock}
