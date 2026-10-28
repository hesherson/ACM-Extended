/* Server persistence adapter. [] means busy/invalid, never an empty stock.
 * Restock progress is a remaining in-game duration, independent of mission date. */
if (canSuspend) exitWith {private _result = []; isNil {_result = _this call ACME_fnc_bloodFridgeSnapshot;}; _result};
params ["_fridge"];
if (!isServer || {isNull _fridge} || {!(_fridge getVariable ["ACME_bloodFridge",false])}) exitWith {[]};
if (count (_fridge getVariable ["ACME_bf_takers",createHashMap]) > 0) exitWith {[]};
if (((values (_fridge getVariable ["ACME_bf_grants",createHashMap])) findIf {(_x param [3,""]) == "pending"}) >= 0) exitWith {[]};
private _interval = _fridge getVariable ["ACME_bf_regenMins",-1];
if !(_interval isEqualType 0 && {finite _interval} && {_interval >= -1} && {_interval <= 1e9}) exitWith {[]};
private _minutes = _interval;
if (_minutes < 0) then {_minutes = (missionNamespace getVariable ["ACME_bf_regenHours",24]) * 60 + (missionNamespace getVariable ["ACME_bf_regenMinutes",0]);};
private _delay = _fridge getVariable ["ACME_bf_restoreRestockDelayMins",_minutes];
if !(_minutes isEqualType 0 && {finite _minutes} && {_minutes >= 0} && {_delay isEqualType 0} && {finite _delay} && {_delay >= 0}) exitWith {[]};
private _now = (dateToNumber date) * (365.25 * 24);
private _last = _fridge getVariable ["ACME_bf_lastRestockGH",-1];
if !(_last isEqualType 0 && {finite _last}) exitWith {[]};
private _elapsed = if (_last < 0 || {_now < _last}) then {0} else {(_now - _last) * 60};
private _remaining = (_delay - _elapsed) max 0;
private _snapshot = [1,_fridge getVariable ["ACME_bf_stock",[]],_fridge getVariable ["ACME_bf_default",[]],_fridge getVariable ["ACME_bf_restock",true],_interval,_remaining];
if !([_snapshot] call ACME_fnc_bloodFridgeSnapshotValid) exitWith {[]};
[_snapshot select 0,(_snapshot select 1) apply {+_x},(_snapshot select 2) apply {+_x},_snapshot select 3,_snapshot select 4,_snapshot select 5]
