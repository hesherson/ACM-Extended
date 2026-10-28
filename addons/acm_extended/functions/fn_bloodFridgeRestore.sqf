/* Restore onto a newly recreated fridge, before admitting viewer/take requests.
 * Explicit offlineGameMinutes defaults to paused. Replays never refill consumed stock. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_bloodFridgeRestore;}; _ok};
params ["_fridge","_snapshot",["_offlineGameMinutes",0]];
if (!isServer || {isNull _fridge} || {!([_snapshot] call ACME_fnc_bloodFridgeSnapshotValid)}) exitWith {false};
if !(_offlineGameMinutes isEqualType 0 && {finite _offlineGameMinutes} && {_offlineGameMinutes >= 0} && {_offlineGameMinutes <= 1e9}) exitWith {false};
private _key = [str _snapshot,_offlineGameMinutes];
private _receipt = _fridge getVariable ["ACME_bf_restoreReceipt",[]];
if (_receipt isEqualTo _key) exitWith {true};
// A different save cannot overwrite an imported or currently used object.
if (_receipt isNotEqualTo [] || {count (_fridge getVariable ["ACME_bf_takers",createHashMap]) > 0}
    || {count (_fridge getVariable ["ACME_bf_viewers",createHashMap]) > 0}
    || {((values (_fridge getVariable ["ACME_bf_grants",createHashMap])) findIf {!((_x param [3,""]) in ["delivered","failed"])}) >= 0}) exitWith {false};
_snapshot params ["","_stock","_defaults","_restock","_interval","_remaining"];
if !(_fridge getVariable ["ACME_bf_setup",false]) then {[_fridge,[],false] call ACME_fnc_bloodFridgeSetup;};
private _minutes = _interval;
if (_minutes < 0) then {_minutes = (missionNamespace getVariable ["ACME_bf_regenHours",24]) * 60 + (missionNamespace getVariable ["ACME_bf_regenMinutes",0]);};
private _due = _restock && {_minutes > 0} && {_offlineGameMinutes >= _remaining};
private _current = if (_due) then {_defaults} else {_stock};
private _delay = if (_due) then {_minutes} else {(_remaining - _offlineGameMinutes) max 0};
_fridge setVariable ["ACME_bf_stock",_current apply {+_x},true];
_fridge setVariable ["ACME_bf_default",_defaults apply {+_x},true];
_fridge setVariable ["ACME_bf_restock",_restock,true];
_fridge setVariable ["ACME_bf_regenMins",_interval,true];
_fridge setVariable ["ACME_bf_lastRestockGH",(dateToNumber date) * (365.25 * 24),true];
_fridge setVariable ["ACME_bf_restoreRestockDelayMins",_delay,false];
_fridge setVariable ["ACME_bf_restoreReceipt",_key,false];
true
