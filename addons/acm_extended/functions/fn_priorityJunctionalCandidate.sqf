/* B229 pure spawn policy. A junctional may replace one isolated native wound, never
   accompany another wound, internal hemorrhage, or hemothorax. Source wound remains the
   junctional's accounting anchor, not an extra injury. Returns [part, wound ID] or []. */
params ["_open", ["_internal", createHashMap], ["_hemothorax", 0]];
if (_hemothorax > 0) exitWith {[]};
private _count = 0;
private _candidate = [];
{
    private _part = _x;
    {
        _x params ["_id", "_amount"];
        if (_amount > 0) then {_count = _count + _amount; _candidate = [_part, _id];};
    } forEach (_open getOrDefault [_part, []]);
    {
        if ((_x param [1, 0]) > 0 && {(_x param [2, 0]) > 0}) then {_count = _count + 1;};
    } forEach (_internal getOrDefault [_part, []]);
} forEach ["head","body","leftarm","rightarm","leftleg","rightleg"];
if (_count != 1 || {!((_candidate param [0, ""]) in ["leftarm","rightarm","leftleg","rightleg"])}) exitWith {[]};
_candidate
