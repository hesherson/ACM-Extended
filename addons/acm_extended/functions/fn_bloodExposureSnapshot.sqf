/* Loose blood only. Public ledger + physical class counts must agree. Every
 * same-class row retains its age; no native identity is invented for loose bags. */
params ["_holder"];
if (isNull _holder) exitWith {[]};
if (count (_holder getVariable ["ACME_bloodExposurePending",[]]) > 0
    || {count (_holder getVariable ["ACME_bloodSeedPending",createHashMap]) > 0}) exitWith {[]};
private _items = if (_holder isKindOf "CAManBase") then {(uniformItems _holder) + (vestItems _holder) + (backpackItems _holder)} else {itemCargo _holder};
private _bags = _items select {([_x] call ACME_fnc_coolerBagVolume) > 0};
if (_bags isEqualTo []) exitWith {[1,[]]};
private _live = _holder getVariable ["ACME_bloodExposure",[]];
if !(_live isEqualType [] && {count _live == 2}) exitWith {[]};
_live params ["_rows","_sampled"];
if !(_rows isEqualType [] && {_sampled isEqualType 0} && {finite _sampled} && {_sampled <= serverTime}) exitWith {[]};
if (count _rows > 1024 || {(_rows findIf {
    !(_x isEqualType []) || {count _x != 3} || {isNil {_x select 0}} || {isNil {_x select 1}} || {isNil {_x select 2}}
        || {!((_x select 0) isEqualType "")} || {!((_x select 1) isEqualType 0)} || {!finite (_x select 1)}
        || {!((_x select 2) isEqualType 0)} || {!finite (_x select 2)} || {(_x select 2) < 0}
}) >= 0}) exitWith {[]};
private _classes = _rows apply {_x select 0};
_bags sort true;
_classes sort true;
if (_bags isNotEqualTo _classes) exitWith {[]};
private _elapsed = (serverTime - _sampled) max 0;
private _snapshot = [1,_rows apply {[_x select 0,(_x select 2) + _elapsed]}];
if !([_snapshot] call ACME_fnc_bloodExposureSnapshotValid) exitWith {[]};
_snapshot
