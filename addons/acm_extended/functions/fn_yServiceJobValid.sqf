/* Validate persisted/replicated service arithmetic before any volume or priming mutation.
 * The original 13-field job remains readable; B228 appends a cancellation identity. */
params [["_job", [], [[]]], ["_key", "", [""]]];
if !(count _job in [13,14]) exitWith {false};
if !((_job select 0) isEqualType "" && {(_job select 1) isEqualType true} && {(_job select 3) isEqualType ""}) exitWith {false};
if !((_job select 0) in ["head","body","leftarm","rightarm","leftleg","rightleg"]) exitWith {false};
if (([2,4,5,6,8,11,12] findIf {!((_job select _x) isEqualType 0) || {!finite (_job select _x)}}) >= 0) exitWith {false};
if !((_job select 2) in (if (_job select 1) then {[0,1,2]} else {[0]})) exitWith {false};
if (_key != toLowerANSI format ["%1#%2#%3",_job select 0,_job select 1,_job select 2]) exitWith {false};
if ((_job select 3) == "" || {(_job select 4) < 0} || {(_job select 5) <= 0} || {(_job select 5) > 500}
    || {(_job select 8) < 0} || {(_job select 12) < 0}) exitWith {false};
if !((_job select 9) isEqualType [] && {count (_job select 9) <= 100} && {(_job select 10) in ["prime","flush"]}) exitWith {false};
if (((_job select 9) findIf {!(_x isEqualType 0) || {!finite _x} || {_x != 50}}) >= 0) exitWith {false};
private _total = _job select 11;
if !(_total in (if ((_job select 10) == "prime") then {[25]} else {[25,50]})) exitWith {false};
if ((_job select 10) == "prime" && {(_job select 9) isNotEqualTo []}) exitWith {false};
if (abs (((_job select 4) + (_job select 12)) - _total) > 0.001) exitWith {false};
if (count _job == 14 && {!((_job select 13) isEqualType "") || {count (_job select 13) > 128}}) exitWith {false};
true
