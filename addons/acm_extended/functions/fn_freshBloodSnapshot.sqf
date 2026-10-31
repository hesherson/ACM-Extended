/* Server export, before saving units/cargo. Save this global metadata once. */
if (!isServer) exitWith {[]};
private _grants = missionNamespace getVariable ["ACM_circulation_FreshBloodGrants",createHashMap];
if !(_grants isEqualType createHashMap) exitWith {[]};
if ((values _grants findIf {(_x param [5,""]) != "delivered"}) >= 0) exitWith {[]};
private _registry = missionNamespace getVariable ["ACM_circulation_FreshBloodList",createHashMap];
if !(_registry isEqualType createHashMap) exitWith {[]};
private _rows = [];
private _ok = true;
{
    private _entry = _registry get _x;
    if !(_entry isEqualType [] && {count _entry >= 5}
        && {!isNil {_entry select 4}} && {(_entry select 4) isEqualType 0}
        && {finite (_entry select 4)}) exitWith {_ok = false;};
    _rows pushBack [_x,[_entry select 0,true] call ACME_fnc_clinicalCodec,
        _entry select 1,_entry select 2,_entry select 3,(CBA_missionTime - (_entry select 4)) max 0];
} forEach keys _registry;
private _snapshot = [1,_rows];
if (!_ok || {!([_snapshot] call ACME_fnc_freshBloodSnapshotValid)}) exitWith {[]};
_snapshot
